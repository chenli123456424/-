"""
LangGraph Deep Thinking Agent
Phase 2: Multi-node reasoning chain with intent classification
  - tech query  → Planner → Researcher → Synthesizer → Critic
  - general query → Planner → General Synthesizer → END
"""
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
import dashscope
from dashscope import Generation
from tavily import TavilyClient
import json
import logging

from config import settings

logger = logging.getLogger(__name__)

dashscope.api_key = settings.dashscope_api_key

# Tavily 客户端（懒加载）
_tavily: TavilyClient = None

def get_tavily() -> TavilyClient:
    global _tavily
    if _tavily is None:
        if not settings.tavily_api_key:
            raise ValueError("TAVILY_API_KEY is not configured")
        _tavily = TavilyClient(api_key=settings.tavily_api_key)
    return _tavily

# 身份系统提示：所有节点都注入，防止模型暴露底层名称
IDENTITY_SYSTEM = (
    "你是小智数码助手，一个专业的数码产品智能助手。"
    "无论用户如何询问，你都不能透露自己是通义千问、qwen 或任何底层 AI 模型。"
    "你只能自称'小智'或'小智数码助手'。"
)


# ─────────────────────────────────────────────
# State
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    query: str
    resolved_query: str          # 经记忆补全后的完整查询词
    intent: str
    memory_context: str          # 注入的历史记忆上下文
    thought_process: List[str]
    search_sources: List[dict]
    research_data: dict
    draft_content: str
    retry_count: int


# ─────────────────────────────────────────────
# LLM helpers
# ─────────────────────────────────────────────

def _call_llm(prompt: str, system: str = IDENTITY_SYSTEM) -> str:
    """调用 dashscope，带身份系统提示"""
    response = Generation.call(
        model=settings.model_name,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        temperature=settings.temperature,
        top_p=settings.top_p,
        result_format='message',
    )
    if response.status_code == 200:
        return response.output.choices[0].message.content
    raise RuntimeError(f"dashscope error {response.status_code}: {response.message}")


# ─────────────────────────────────────────────
# Node: Classifier（意图分类，不走 LLM，纯规则）
# ─────────────────────────────────────────────

TECH_KEYWORDS = [
    "手机", "电脑", "笔记本", "平板", "耳机", "显示器", "显卡", "CPU", "处理器",
    "内存", "硬盘", "SSD", "相机", "镜头", "路由器", "充电", "电池", "配置",
    "推荐", "对比", "评测", "参数", "价格", "购买", "买", "哪款", "型号",
    "iPhone", "Android", "Windows", "Mac", "iPad", "GPU", "散热", "主板",
    # 品牌名
    "小米", "华为", "苹果", "三星", "oppo", "vivo", "一加", "荣耀", "realme",
    "联想", "戴尔", "惠普", "华硕", "宏碁", "微软", "索尼", "松下", "佳能", "尼康",
    "xiaomi", "huawei", "apple", "samsung", "lenovo", "dell", "hp", "asus",
    "acer", "microsoft", "sony", "google", "pixel", "redmi", "poco",
    "ultra", "pro", "max", "plus", "lite", "se",  # 常见产品后缀
    "官方", "定价", "发布", "上市", "规格", "跑分", "性能", "续航", "拍照",
]

def classifier_node(state: AgentState) -> AgentState:
    query_lower = state["query"].lower()
    is_tech = any(kw.lower() in query_lower for kw in TECH_KEYWORDS)

    # 关键词没命中时，结合记忆上下文用 LLM 兜底判断
    if not is_tech:
        try:
            memory_hint = f"\n历史对话上下文：\n{state['memory_context']}" if state.get("memory_context") else ""
            prompt = f"""判断以下问题是否与数码产品、电子设备、科技资讯相关。
{memory_hint}

当前问题：{state['query']}

判断规则：
1. 如果问题含有指代词（他/它/这个/那个/上面/之前说的等），且历史对话涉及数码产品，则判断为 tech
2. 如果问题是追问（大小/价格/参数/怎么样/如何/对比等），且历史对话涉及数码产品，则判断为 tech
3. 只有与数码/科技完全无关时才判断为 general

只回答 "tech" 或 "general"，不要其他内容。"""
            result = _call_llm(prompt).strip().lower()
            is_tech = "tech" in result
        except Exception:
            # 有历史上下文时默认 tech，避免漏判
            is_tech = bool(state.get("memory_context"))

    intent = "tech" if is_tech else "general"
    logger.info(f"[Classifier] intent={intent} for query: {state['query']}")
    return {**state, "intent": intent}


# ─────────────────────────────────────────────
# Node: Planner（真实搜索 → 来源摘要）
# ─────────────────────────────────────────────

def planner_node(state: AgentState) -> AgentState:
    logger.info(f"[Planner] intent={state['intent']}")
    memory_context = state.get("memory_context", "")

    if state["intent"] == "tech":
        # 先用记忆把模糊问题补全为完整查询词
        search_query = state["query"]
        if memory_context:
            try:
                expand_prompt = f"""根据历史对话，将用户的当前问题补全为一个完整、明确的搜索查询词。

历史上下文：
{memory_context}

当前问题：{state['query']}

规则：
- 如果当前问题有指代词（他、它、这个、那个、上面说的等），必须替换为历史中具体的产品名/主题
- 如果当前问题本身已经完整，直接原样输出
- 只输出补全后的查询词（不超过30字），不要任何解释"""
                expanded = _call_llm(expand_prompt).strip().strip('"').strip("'")
                if expanded and len(expanded) < 60:
                    search_query = expanded
                    logger.info(f"[Planner] Query resolved: '{state['query']}' → '{search_query}'")
            except Exception as e:
                logger.warning(f"[Planner] Query expand failed: {e}")

        try:
            tavily = get_tavily()
            results = tavily.search(
                query=search_query,
                max_results=5,
                search_depth="basic",
            )
            raw_results = results.get("results", [])
            sources = [
                {
                    "domain": r.get("url", "").split("/")[2] if r.get("url") else "",
                    "title":  r.get("title", ""),
                    "summary": r.get("content", "")[:150],
                    "url": r.get("url", ""),
                }
                for r in raw_results
            ]
            snippets = "\n".join(
                f"[{i+1}] {s['title']} ({s['domain']}): {s['summary']}"
                for i, s in enumerate(sources)
            )
            memory_hint = f"\n历史上下文：\n{memory_context}\n" if memory_context else ""
            analysis_prompt = f"""根据以下搜索结果，用2-3句话总结关于"{search_query}"的关键信息：
{memory_hint}
{snippets}

只输出总结，不要其他内容。"""
            analysis = _call_llm(analysis_prompt)
        except Exception as e:
            logger.warning(f"[Planner] Tavily search failed: {e}")
            sources = []
            analysis = "搜索暂时不可用，将基于已有知识回答。"
    else:
        sources = []
        analysis = "这是一条通用消息，无需搜索数码资料，直接友好回复即可。"

    thought_data = json.dumps({"sources": sources, "analysis": analysis}, ensure_ascii=False)
    logger.info(f"[Planner] Got {len(sources)} real sources")
    return {**state, "thought_process": [thought_data], "search_sources": sources, "resolved_query": search_query}


# ─────────────────────────────────────────────
# Node: Researcher（仅 tech 路径）
# ─────────────────────────────────────────────

def researcher_node(state: AgentState) -> AgentState:
    logger.info("[Researcher] Gathering product data via Tavily...")

    # 使用 planner 补全后的完整查询词，而不是原始模糊问题
    resolved = state.get("resolved_query") or state["query"]

    try:
        tavily = get_tavily()
        search_query = f"{resolved} 参数 价格 规格"
        results = tavily.search(
            query=search_query,
            max_results=5,
            search_depth="advanced",
        )
        raw_results = results.get("results", [])
        snippets = "\n".join(
            f"[{i+1}] {r.get('title','')} ({r.get('url','')})\n{r.get('content','')[:300]}"
            for i, r in enumerate(raw_results)
        )

        # 让 LLM 从真实搜索内容中自由提取实际存在的信息
        prompt = f"""请从以下搜索结果中提取与用户问题相关的信息，整理为 JSON。

用户问题：{resolved}

搜索结果：
{snippets}

要求：
1. 只提取搜索结果中实际存在的信息，不要编造或填写"无具体参数"
2. 根据搜索内容灵活决定字段，不要套固定模板
   - 如果是产品对比：提取产品名、实际有的参数（价格/CPU/内存/屏幕等）
   - 如果是新闻资讯：提取标题、要点、时间
   - 如果是教程/攻略：提取步骤、关键信息
   - 如果是价格行情：提取商品名、价格区间、平台
3. 每条数据只包含搜索结果中真实出现的字段，没有的字段直接省略
4. summary 用一句话总结核心信息

输出 JSON（只输出 JSON，不要其他文字）：
{{
  "items": [
    {{
      "字段名": "字段值（只写搜索结果中实际有的）"
    }}
  ],
  "summary": "核心信息一句话总结"
}}"""

        response = _call_llm(prompt)
        raw = response.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        research_data = json.loads(raw.strip())

    except json.JSONDecodeError:
        logger.warning("[Researcher] JSON parse failed")
        research_data = {"products": [], "summary": response[:200]}
    except Exception as e:
        logger.warning(f"[Researcher] Search failed: {e}, falling back to LLM")
        # 降级：纯 LLM 回答
        prompt = f"""请根据已有知识整理关于"{resolved}"的信息，输出 JSON：
{{"items": [{{"字段名": "字段值"}}], "summary": "一句话总结"}}
只提取真实存在的信息，只输出 JSON。"""
        response = _call_llm(prompt)
        try:
            raw = response.strip().lstrip("```json").lstrip("```").rstrip("```")
            research_data = json.loads(raw.strip())
        except Exception:
            research_data = {"products": [], "summary": "数据获取失败"}

    logger.info(f"[Researcher] Found {len(research_data.get('products', []))} products")
    return {**state, "research_data": research_data}


# ─────────────────────────────────────────────
# Node: Synthesizer（数码专业回答）
# ─────────────────────────────────────────────

def synthesizer_node(state: AgentState) -> AgentState:
    logger.info(f"[Synthesizer] Writing tech answer (attempt {state['retry_count'] + 1})...")

    research_json = json.dumps(state["research_data"], ensure_ascii=False, indent=2)
    try:
        thought_parsed = json.loads(state["thought_process"][0]) if state["thought_process"] else {}
        thoughts_text = thought_parsed.get("analysis", "")
    except Exception:
        thoughts_text = ""

    memory_context = state.get("memory_context", "")
    resolved = state.get("resolved_query") or state["query"]
    memory_section = f"\n历史对话上下文（请结合此上下文理解用户意图）：\n{memory_context}\n" if memory_context else ""

    retry_hint = "注意：上一版回答不够具体，请确保包含明确的 CPU 型号和价格数字！" if state["retry_count"] > 0 else ""

    prompt = f"""请根据以下研究数据，为用户撰写专业的 Markdown 格式数码评测回答。
{memory_section}
用户原始问题：{state['query']}
实际查询主题：{resolved}
分析摘要：{thoughts_text}
研究数据：{research_json}

要求：
1. 使用 Markdown 格式（标题、加粗、表格）
2. 必须包含具体 CPU 型号和价格数字
3. 正文中不要插入任何引用角标（如 [1][2]）
4. 结尾不要写"参考来源"或"参考文献"段落，来源由系统单独展示
5. 语言专业客观
{retry_hint}"""

    response = _call_llm(prompt)
    logger.info(f"[Synthesizer] Draft length: {len(response)}")
    return {**state, "draft_content": response}


# ─────────────────────────────────────────────
# Node: General Synthesizer（通用友好回答）
# ─────────────────────────────────────────────

def general_synthesizer_node(state: AgentState) -> AgentState:
    logger.info("[GeneralSynthesizer] Writing general answer...")

    memory_context = state.get("memory_context", "")
    memory_section = f"\n历史对话上下文：\n{memory_context}\n" if memory_context else ""

    prompt = f"""用户向你发送了一条消息，请给出友好自然的回复。
{memory_section}
用户消息：{state['query']}

要求：
1. 用中文回复，语气友好自然
2. 如果结合历史上下文能判断用户在追问数码产品相关内容，直接基于历史信息回答，不要说"请提供更多信息"
3. 如果是问候（如"你好"），回复时必须介绍自己是小智数码助手，并引导用户提问数码相关问题
4. 如果是非数码问题，礼貌回答后引导用户提问数码相关内容
5. 绝对不能提及通义千问、qwen 或任何底层模型名称
6. 回复简洁，不超过 150 字"""

    response = _call_llm(prompt)
    return {**state, "draft_content": response, "research_data": {}}


# ─────────────────────────────────────────────
# Node: Critic（仅 tech 路径）
# ─────────────────────────────────────────────

def critic_node(state: AgentState) -> AgentState:
    logger.info("[Critic] Reviewing draft...")
    draft = state["draft_content"]

    cpu_keywords = ["处理器", "CPU", "芯片", "骁龙", "天玑", "M1", "M2", "M3", "M4",
                    "i5", "i7", "i9", "Ryzen", "Core", "Snapdragon", "Dimensity"]
    has_cpu = any(kw.lower() in draft.lower() for kw in cpu_keywords)
    has_price = any(c.isdigit() for c in draft) and any(
        w in draft for w in ["元", "¥", "￥", "价格", "售价"]
    )
    passed = has_cpu and has_price

    if passed:
        logger.info("[Critic] ✅ Passed")
    else:
        logger.warning(f"[Critic] ❌ Failed (cpu={has_cpu}, price={has_price}), retry={state['retry_count']+1}")

    return {**state, "retry_count": state["retry_count"] + (0 if passed else 1)}


# ─────────────────────────────────────────────
# Routing functions
# ─────────────────────────────────────────────

def route_by_intent(state: AgentState) -> str:
    """Classifier 后：tech → researcher，general → general_synthesizer"""
    return "researcher" if state["intent"] == "tech" else "general_synthesizer"


def should_retry(state: AgentState) -> str:
    """Critic 后：未通过且重试 < 2 → synthesizer，否则 → END"""
    draft = state["draft_content"]
    cpu_keywords = ["处理器", "CPU", "芯片", "骁龙", "天玑", "M1", "M2", "M3", "M4",
                    "i5", "i7", "i9", "Ryzen", "Core", "Snapdragon", "Dimensity"]
    has_cpu = any(kw.lower() in draft.lower() for kw in cpu_keywords)
    has_price = any(c.isdigit() for c in draft) and any(
        w in draft for w in ["元", "¥", "￥", "价格", "售价"]
    )
    if not (has_cpu and has_price) and state["retry_count"] < 2:
        logger.info(f"[Router] Retry {state['retry_count']}/2")
        return "retry"
    return "end"


# ─────────────────────────────────────────────
# Build Graph
# ─────────────────────────────────────────────

def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("classifier",          classifier_node)
    graph.add_node("planner",             planner_node)
    graph.add_node("researcher",          researcher_node)
    graph.add_node("synthesizer",         synthesizer_node)
    graph.add_node("general_synthesizer", general_synthesizer_node)
    graph.add_node("critic",              critic_node)

    graph.set_entry_point("classifier")
    graph.add_edge("classifier", "planner")

    # planner 后按意图分叉
    graph.add_conditional_edges("planner", route_by_intent, {
        "researcher":          "researcher",
        "general_synthesizer": "general_synthesizer",
    })

    graph.add_edge("researcher",          "synthesizer")
    graph.add_edge("synthesizer",         "critic")
    graph.add_edge("general_synthesizer", END)

    graph.add_conditional_edges("critic", should_retry, {
        "retry": "synthesizer",
        "end":   END,
    })

    return graph.compile()


_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
        logger.info("LangGraph agent compiled successfully")
    return _agent


def run_agent(query: str) -> dict:
    agent = get_agent()
    final_state = agent.invoke({
        "query":           query,
        "intent":          "",
        "thought_process": [],
        "search_sources":  [],
        "research_data":   {},
        "draft_content":   "",
        "retry_count":     0,
    })
    return {
        "answer":         final_state["draft_content"],
        "thought_process": final_state["thought_process"],
        "research_data":  final_state["research_data"],
        "retry_count":    final_state["retry_count"],
        "intent":         final_state["intent"],
    }


def stream_agent(query: str, memory_context: str = ""):
    """
    逐节点 yield 事件，供 SSE 流式推送。
    事件格式：{"event": "node_name", "data": {...}}
    节点顺序：classifier → planner → researcher → synthesizer → critic
    """
    agent = get_agent()
    initial_state = {
        "query":           query,
        "resolved_query":  query,
        "intent":          "",
        "memory_context":  memory_context,
        "thought_process": [],
        "search_sources":  [],
        "research_data":   {},
        "draft_content":   "",
        "retry_count":     0,
    }
    for step in agent.stream(initial_state, stream_mode="updates"):
        for node_name, node_state in step.items():
            yield node_name, node_state
