"""
火山引擎豆包语音合成服务 (TTS)
使用 HTTP POST 接口，返回 Base64 编码的 MP3 音频
文档: https://www.volcengine.com/docs/6561/79820
"""
import base64
import json
import logging
import re
import uuid
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

TTS_HTTP_URL = "https://openspeech.bytedance.com/api/v1/tts"

# 语言 → 音色映射（使用免费音色）
VOICE_MAP = {
    "zh":     "BV700_streaming",   # 普通话女声（免费）
    "minnan": "BV005_streaming",   # 闽南语
    "cantonese": "BV021_streaming", # 粤语
    "sichuan":   "BV026_streaming", # 四川话
    "dongbei":   "BV025_streaming", # 东北话
}

DEFAULT_VOICE = VOICE_MAP["zh"]


def _clean_text(text: str) -> str:
    """去除 Markdown 符号，只保留纯文本"""
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'\|[^\n]+\|', '', text)
    text = re.sub(r'\n{2,}', '。', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def generate_audio_async(text: str, lang: str = "zh") -> Optional[str]:
    """
    异步生成语音，返回 Base64 编码的 MP3 数据
    长文本自动分段合成后拼接
    """
    if not settings.volc_app_id or not settings.volc_token:
        logger.warning("[TTS] 火山引擎凭证未配置")
        return None

    clean = _clean_text(text)
    if not clean:
        logger.warning("[TTS] 清理后文本为空")
        return None

    voice = VOICE_MAP.get(lang, DEFAULT_VOICE)
    token = settings.volc_token

    # 按句子分段，每段不超过 800 字节
    segments = _split_text(clean, max_bytes=800)
    logger.info(f"[TTS] 分 {len(segments)} 段合成，voice={voice}")

    audio_parts = []
    for i, seg in enumerate(segments):
        part = await _synthesize_segment(seg, voice, token)
        if part:
            audio_parts.append(part)
        else:
            logger.warning(f"[TTS] 第 {i+1} 段合成失败，跳过")

    if not audio_parts:
        return None

    # 合并所有 MP3 片段
    combined = b"".join(base64.b64decode(p) for p in audio_parts)
    logger.info(f"[TTS] 合成完成，总大小: {len(combined)} bytes")
    return base64.b64encode(combined).decode()


def _split_text(text: str, max_bytes: int = 800) -> list:
    """按句子边界分段，每段不超过 max_bytes 字节"""
    import re
    # 按句子标点分割
    sentences = re.split(r'(?<=[。！？；\n])', text)
    segments = []
    current = ""
    for sent in sentences:
        if not sent.strip():
            continue
        candidate = current + sent
        if len(candidate.encode('utf-8')) <= max_bytes:
            current = candidate
        else:
            if current:
                segments.append(current.strip())
            # 单句超长则强制截断
            if len(sent.encode('utf-8')) > max_bytes:
                encoded = sent.encode('utf-8')
                while encoded:
                    chunk = encoded[:max_bytes].decode('utf-8', errors='ignore')
                    segments.append(chunk.strip())
                    encoded = encoded[max_bytes:]
            else:
                current = sent
    if current.strip():
        segments.append(current.strip())
    return segments or [text[:100]]


async def _synthesize_segment(text: str, voice: str, token: str) -> Optional[str]:
    """合成单段文本，返回 Base64 MP3"""
    headers = {
        "Authorization": f"Bearer;{token}",
        "Content-Type": "application/json",
    }
    payload = {
        "app": {"appid": settings.volc_app_id, "token": token, "cluster": "volcano_tts"},
        "user": {"uid": "xiaozhi_user"},
        "audio": {
            "voice_type": voice,
            "encoding": "mp3",
            "speed_ratio": 1.0,
            "volume_ratio": 1.0,
            "pitch_ratio": 1.0,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "text_type": "plain",
            "operation": "query",
        },
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(TTS_HTTP_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error(f"[TTS] 段合成失败: {resp.status_code}, {resp.text[:200]}")
                return None
            data = resp.json()
            if data.get("code") != 3000:
                logger.error(f"[TTS] 段合成错误: code={data.get('code')}, msg={data.get('message')}")
                return None
            return data.get("data")
    except Exception as e:
        logger.error(f"[TTS] 段合成异常: {e}")
        return None


def generate_audio(text: str, lang: str = "zh") -> Optional[str]:
    """同步包装"""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(generate_audio_async(text, lang))
    finally:
        loop.close()
