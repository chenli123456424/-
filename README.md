# 小智数码助手

基于 React + FastAPI + LangGraph 构建的 AI 数码助手，支持深度搜索、方言朗读和持久化对话记忆。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + Vite + Tailwind CSS |
| 后端 | FastAPI + LangGraph + Dashscope |
| 搜索 | Tavily Search API |
| TTS  | 火山引擎语音合成 |
| 部署 | Docker + Nginx |

---

## 快速开始（Docker，推荐）

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd xiaozhi-digital-assistant
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```env
# 通义千问（必填）
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Tavily 搜索（必填，深度搜索功能需要）
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 火山引擎 TTS（选填，不填则关闭朗读功能）
VOLC_APP_ID=your_app_id
VOLC_ACCESS_KEY=your_access_key
VOLC_SECRET_KEY=your_secret_key
VOLC_TOKEN=your_token
```

### 3. 启动服务

```bash
docker compose up --build
```

启动完成后访问：**http://localhost:3000**

> 后端 API 运行在 http://localhost:8000，前端通过 Nginx 反代自动转发。

### 4. 停止服务

```bash
docker compose down
```

---

## 本地开发（不用 Docker）

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制并填写 key）
cp .env.example .env

# 启动后端
python run.py
# 或
uvicorn main:app --reload --port 8000
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
# 访问 http://localhost:5173
```

---

## 项目结构

```
├── backend/
│   ├── main.py                  # FastAPI 入口，WebSocket 端点
│   ├── config.py                # 环境变量配置
│   ├── requirements.txt         # Python 依赖
│   ├── Dockerfile
│   └── services/
│       ├── langgraph_agent.py   # LangGraph 多节点推理链
│       ├── memory_service.py    # 对话记忆（滑动窗口 + 摘要压缩）
│       └── tts_service.py       # 火山引擎 TTS
├── frontend/
│   ├── src/
│   │   ├── components/          # React 组件
│   │   ├── api/websocket.js     # WebSocket 客户端
│   │   ├── SpeakingContext.jsx  # 朗读状态管理
│   │   └── ThemeContext.jsx     # 主题管理
│   ├── public/                  # 静态资源（favicon 等）
│   ├── nginx.conf               # Nginx 反代配置
│   └── Dockerfile
├── docker-compose.yml
├── .env.example                 # 环境变量模板
└── README.md
```

---

## 功能说明

- **深度搜索**：通过 Tavily 实时搜索，LangGraph 多节点推理（Planner → Researcher → Synthesizer → Critic）
- **方言朗读**：支持普通话、闽南语、东北话、陕西话，火山引擎 TTS 合成
- **持久化记忆**：滑动窗口保留最近 10 轮对话，超出部分自动 LLM 压缩为摘要，跨轮次理解上下文
- **设置面板**：侧边栏滑出设置，支持方言切换和朗读开关
- **参考来源**：搜索来源以 favicon 标签形式展示在回复气泡底部

---

## API Key 获取

| 服务 | 获取地址 |
|------|---------|
| 通义千问 | https://dashscope.aliyun.com |
| Tavily | https://tavily.com |
| 火山引擎 TTS | https://www.volcengine.com/product/tts |
