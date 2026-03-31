"""
Xiaozhi Digital Assistant - FastAPI Backend
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import logging
import json
import asyncio
import queue
import threading

from config import settings
from llm_wrapper import get_llm
from services.langgraph_agent import run_agent, stream_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Xiaozhi Digital Assistant API",
    description="AI Digital Assistant powered by Tongyi LLM",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    conversation_id: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    conversation_id: str
    tokens_used: Optional[int] = None


# Health Check Endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Xiaozhi Digital Assistant API",
        "version": "0.1.0"
    }


# Chat Endpoint
@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Chat endpoint for sending messages to the LLM
    """
    if not request.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        logger.info(f"Processing chat request: {request.message}")
        
        # Get LLM instance
        try:
            llm = get_llm()
        except ValueError as e:
            error_msg = f"LLM initialization failed: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Call LLM with user message
        try:
            response = llm.chat(request.message)
            logger.info(f"Generated response: {response[:100] if response else 'No response'}...")
        except Exception as llm_error:
            error_msg = f"LLM call failed: {str(llm_error)}"
            logger.error(error_msg, exc_info=True)
            raise HTTPException(status_code=500, detail=error_msg)
        
        return ChatResponse(
            response=response,
            conversation_id=request.conversation_id or "default"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/", tags=["Info"])
async def root():
    """Root endpoint"""
    return {
        "message": "Xiaozhi Digital Assistant API",
        "docs": "/docs"
    }


# Streaming Chat Endpoint
@app.post("/chat/stream", tags=["Chat"])
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint - returns response as stream
    Uses Server-Sent Events (SSE) format
    """
    if not request.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    async def event_generator():
        """Generate streaming events"""
        import json
        try:
            logger.info(f"Processing streaming chat request: {request.message}")
            
            # Get LLM instance
            try:
                llm = get_llm()
            except ValueError as e:
                error_msg = f"LLM initialization failed: {str(e)}"
                logger.error(error_msg)
                yield f'data: {json.dumps({"error": error_msg})}\n\n'
                return
            
            # Stream the response
            try:
                full_response = ""
                
                for chunk in llm.chat_stream(request.message):
                    if chunk:
                        full_response += chunk
                        # Send chunk as SSE data (json.dumps handles all escaping)
                        yield f'data: {json.dumps({"chunk": chunk})}\n\n'
                
                # Send completion message
                yield f'data: {json.dumps({"done": True, "total": full_response})}\n\n'
                logger.info(f"Streaming completed. Length: {len(full_response)}")
                
            except Exception as llm_error:
                error_msg = f"LLM call failed: {str(llm_error)}"
                logger.error(error_msg, exc_info=True)
                yield f'data: {json.dumps({"error": error_msg})}\n\n'
                
        except Exception as e:
            logger.error(f"Error in streaming: {str(e)}", exc_info=True)
            yield f'data: {json.dumps({"error": str(e)})}\n\n'
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )




# Deep Thinking Endpoint (LangGraph)
@app.post("/chat/deep", tags=["Chat"])
async def chat_deep(request: ChatRequest):
    """
    SSE event types:
      - {"type": "searching", "count": N, "source": {...}}   每找到一个来源实时推送
      - {"type": "thought_summary", "content": "分析结论"}   搜索完成后的总结
      - {"type": "research", "data": {...}}                  结构化产品数据
      - {"type": "chunk", "content": "..."}                  最终回答流式文字
      - {"type": "done", "retry_count": N}
      - {"type": "error", "content": "..."}
    """
    if not request.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    async def event_generator():
        import json
        import asyncio
        try:
            logger.info(f"[Deep] Streaming agent for: {request.message}")
            loop = asyncio.get_event_loop()

            # stream_agent 是同步生成器，放线程池里跑
            # 用 queue 桥接同步生成器和异步 SSE
            import queue
            import threading

            q = queue.Queue()

            def run_in_thread():
                try:
                    for node_name, node_state in stream_agent(request.message):
                        q.put(("node", node_name, node_state))
                    q.put(("done", None, None))
                except Exception as e:
                    q.put(("error", str(e), None))

            thread = threading.Thread(target=run_in_thread, daemon=True)
            thread.start()

            source_count = 0  # 已推送的来源数量

            while True:
                try:
                    item = await loop.run_in_executor(None, lambda: q.get(timeout=60))
                except Exception:
                    yield f'data: {json.dumps({"type": "error", "content": "timeout"})}\n\n'
                    break

                kind, node_name, node_state = item

                if kind == "error":
                    yield f'data: {json.dumps({"type": "error", "content": node_name})}\n\n'
                    break

                if kind == "done":
                    break

                # ── planner 节点：搜索来源逐条推送 ──
                if node_name == "planner" and node_state.get("thought_process"):
                    try:
                        thought_parsed = json.loads(node_state["thought_process"][0])
                        sources = thought_parsed.get("sources", [])
                        analysis = thought_parsed.get("analysis", "")

                        # 逐条推送来源（模拟边搜索边显示）
                        for i, src in enumerate(sources):
                            source_count = i + 1
                            yield f'data: {json.dumps({"type": "searching", "count": source_count, "source": src})}\n\n'
                            await asyncio.sleep(0.15)  # 视觉上有节奏感

                        # 推送分析总结
                        if analysis:
                            yield f'data: {json.dumps({"type": "thought_summary", "content": analysis})}\n\n'
                    except Exception:
                        pass

                # ── researcher 节点：推送结构化数据 ──
                elif node_name == "researcher" and node_state.get("research_data"):
                    yield f'data: {json.dumps({"type": "research", "data": node_state["research_data"]})}\n\n'

                # ── synthesizer 节点：流式推送最终回答 ──
                elif node_name == "synthesizer" and node_state.get("draft_content"):
                    answer = node_state["draft_content"]
                    chunk_size = 8
                    for i in range(0, len(answer), chunk_size):
                        yield f'data: {json.dumps({"type": "chunk", "content": answer[i:i+chunk_size]})}\n\n'
                        await asyncio.sleep(0.01)

                # ── general_synthesizer：流式推送通用回答 ──
                elif node_name == "general_synthesizer" and node_state.get("draft_content"):
                    answer = node_state["draft_content"]
                    chunk_size = 8
                    for i in range(0, len(answer), chunk_size):
                        yield f'data: {json.dumps({"type": "chunk", "content": answer[i:i+chunk_size]})}\n\n'
                        await asyncio.sleep(0.01)

                # ── critic 节点：推送重试信息 ──
                elif node_name == "critic":
                    retry_count = node_state.get("retry_count", 0)
                    if retry_count > 0:
                        yield f'data: {json.dumps({"type": "retry", "count": retry_count})}\n\n'

            yield f'data: {json.dumps({"type": "done", "retry_count": 0})}\n\n'
            logger.info("[Deep] Streaming completed")

        except Exception as e:
            logger.error(f"[Deep] Error: {str(e)}", exc_info=True)
            yield f'data: {json.dumps({"type": "error", "content": str(e)})}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─────────────────────────────────────────────
# WebSocket Chat Endpoint
# ─────────────────────────────────────────────

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    logger.info("[WS] Client connected")
    stop_flag = {"stopped": False}

    async def listen_for_stop():
        """并发监听客户端消息，收到 stop 立即设置标志"""
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    payload = json.loads(raw)
                    if payload.get("type") == "stop":
                        logger.info("[WS] Stop signal received")
                        stop_flag["stopped"] = True
                except Exception:
                    pass
        except Exception:
            pass

    try:
        while True:
            # 等待用户发送消息
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except Exception:
                await websocket.send_text(json.dumps({"type": "error", "data": "Invalid JSON"}))
                continue

            if payload.get("type") == "stop":
                continue  # 没有正在运行的任务，忽略

            message = payload.get("message", "").strip()
            if not message:
                await websocket.send_text(json.dumps({"type": "error", "data": "Empty message"}))
                continue

            logger.info(f"[WS] Received: {message}")
            stop_flag["stopped"] = False

            q = queue.Queue()
            loop = asyncio.get_event_loop()

            def run_in_thread():
                try:
                    for node_name, node_state in stream_agent(message):
                        if stop_flag["stopped"]:
                            break
                        q.put(("node", node_name, node_state))
                    q.put(("done", None, None))
                except Exception as e:
                    q.put(("error", str(e), None))

            thread = threading.Thread(target=run_in_thread, daemon=True)
            thread.start()

            # 启动并发监听停止信号的任务
            stop_listener = asyncio.create_task(listen_for_stop())

            try:
                while True:
                    if stop_flag["stopped"]:
                        await websocket.send_text(json.dumps({"type": "stopped", "data": None}))
                        break

                    try:
                        item = await loop.run_in_executor(
                            None, lambda: q.get(timeout=0.2)
                        )
                    except Exception:
                        # timeout，继续检查 stop_flag
                        continue

                    kind, node_name, node_state = item

                    if kind == "error":
                        await websocket.send_text(json.dumps({"type": "error", "data": node_name}))
                        break

                    if kind == "done":
                        await websocket.send_text(json.dumps({"type": "done", "data": None}))
                        break

                    if node_name == "planner" and node_state.get("thought_process"):
                        try:
                            thought_parsed = json.loads(node_state["thought_process"][0])
                            sources = thought_parsed.get("sources", [])
                            analysis = thought_parsed.get("analysis", "")
                            for i, src in enumerate(sources):
                                if stop_flag["stopped"]: break
                                await websocket.send_text(json.dumps({
                                    "type": "thought",
                                    "data": {"count": i + 1, "source": src}
                                }))
                                await asyncio.sleep(0.15)
                            if analysis and not stop_flag["stopped"]:
                                await websocket.send_text(json.dumps({
                                    "type": "thought_summary", "data": analysis
                                }))
                        except Exception:
                            pass

                    elif node_name == "researcher" and node_state.get("research_data"):
                        if not stop_flag["stopped"]:
                            await websocket.send_text(json.dumps({
                                "type": "search", "data": node_state["research_data"]
                            }))

                    elif node_name in ("synthesizer", "general_synthesizer") and node_state.get("draft_content"):
                        answer = node_state["draft_content"]
                        for i in range(0, len(answer), 8):
                            if stop_flag["stopped"]: break
                            await websocket.send_text(json.dumps({
                                "type": "content_patch", "data": answer[i:i + 8]
                            }))
                            await asyncio.sleep(0.01)

                    elif node_name == "critic":
                        retry_count = node_state.get("retry_count", 0)
                        if retry_count > 0 and not stop_flag["stopped"]:
                            await websocket.send_text(json.dumps({
                                "type": "retry", "data": retry_count
                            }))
            finally:
                stop_listener.cancel()

    except WebSocketDisconnect:
        logger.info("[WS] Client disconnected")
    except Exception as e:
        logger.error(f"[WS] Error: {str(e)}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({"type": "error", "data": str(e)}))
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
