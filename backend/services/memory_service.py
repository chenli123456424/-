"""
对话记忆管理服务 v2 — SQLite 持久化版
流程：
  1. 每轮对话开始前：load_memories → build_context_from_db（梳理历史 + 推理当前问题关联）
  2. 每轮对话结束后：LLM 提炼本轮摘要 → save_memory 写入 DB
"""
import logging
import json
from typing import List
import dashscope
from dashscope import Generation

from config import settings
from services.memory_db import save_memory, load_memories, get_turn_count, init_db

logger = logging.getLogger(__name__)
dashscope.api_key = settings.dashscope_api_key

# 每次注入 prompt 的最大历史条数（避免 token 过多）
MAX_CONTEXT_TURNS = 10


def _call_llm(prompt: str) -> str:
    resp = Generation.call(
        model=settings.model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        result_format="message",
    )
    if resp.status_code == 200:
        return resp.output.choices[0].message.content.strip()
    raise RuntimeError(f"LLM error {resp.status_code}")


# ─────────────────────────────────────────────
# 记忆写入：每轮对话结束后调用
# ─────────────────────────────────────────────

def save_turn_memory(session_id: str, user_query: str,
                     resolved_query: str, assistant_reply: str):
    """
    调用 LLM 对本轮对话提炼摘要和关键词，写入 DB。
    异步友好：调用方用 run_in_executor 包裹即可。
    """
    turn_index = get_turn_count(session_id) + 1

    prompt = f"""请对以下一轮对话进行关键信息提炼，输出 JSON。

用户问题：{user_query}
实际查询主题：{resolved_query}
AI 回复摘要（取前600字）：{assistant_reply[:600]}

输出 JSON（只输出 JSON，不要其他文字）：
{{
  "summary": "本轮对话的核心信息，不超过150字，保留产品名/价格/参数/结论等关键实体",
  "keywords": ["关键词1", "关键词2", "关键词3"]
}}"""

    try:
        raw = _call_llm(prompt)
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = json.loads(raw)
        summary = data.get("summary", "")
        keywords = data.get("keywords", [])
    except Exception as e:
        logger.warning(f"[Memory] LLM summarize failed: {e}, using fallback")
        summary = f"用户问：{user_query}。主题：{resolved_query}。"
        keywords = []

    save_memory(session_id, turn_index, user_query, resolved_query, summary, keywords)


# ─────────────────────────────────────────────
# 记忆读取：每轮对话开始前调用
# ─────────────────────────────────────────────

def build_memory_context(session_id: str, current_query: str) -> str:
    """
    从 DB 加载历史记忆，让 LLM 梳理后生成注入 prompt 的上下文字符串。
    包含：历史摘要列表 + 对当前问题的关联推理。
    """
    memories = load_memories(session_id, limit=MAX_CONTEXT_TURNS)
    if not memories:
        return ""

    # 构建历史摘要列表文本
    history_lines = []
    for m in memories:
        kw_str = "、".join(json.loads(m["keywords"])) if m.get("keywords") else ""
        line = f"第{m['turn_index']}轮 [{kw_str}]：{m['summary']}"
        history_lines.append(line)
    history_text = "\n".join(history_lines)

    # 让 LLM 推理当前问题与历史的关联，生成精炼上下文
    prompt = f"""以下是用户与小智数码助手的历史对话摘要列表：

{history_text}

用户当前提问：{current_query}

请完成两件事：
1. 判断当前问题是否与历史对话有关联（如指代词"他/它/那个"、追问、对比等）
2. 输出一段简洁的上下文说明（不超过200字），供 AI 理解当前问题的完整背景

只输出上下文说明文字，不要标题或编号。如果当前问题与历史完全无关，输出"无相关历史上下文"。"""

    try:
        context = _call_llm(prompt)
        if context == "无相关历史上下文":
            # 无关联时仍保留最近几轮的原始摘要，供 LLM 参考
            recent = memories[-3:]
            context = "近期对话摘要：\n" + "\n".join(
                f"第{m['turn_index']}轮：{m['summary']}" for m in recent
            )
        logger.info(f"[Memory] Context built for session {session_id[:8]}…")
        return context
    except Exception as e:
        logger.warning(f"[Memory] Context build failed: {e}")
        # 降级：直接返回最近3轮摘要
        recent = memories[-3:]
        return "近期对话摘要：\n" + "\n".join(
            f"第{m['turn_index']}轮：{m['summary']}" for m in recent
        )
