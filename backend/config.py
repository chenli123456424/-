"""
Backend Configuration
"""
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

# 显式加载 .env 文件
load_dotenv()


class Settings(BaseSettings):
    """应用设置"""
    
    # API Configuration
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Tongyi API Configuration
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    model_name: str = "qwen-turbo"

    # Tavily Search API
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")

    # 火山引擎 TTS
    volc_app_id: str = os.getenv("VOLC_APP_ID", "")
    volc_access_key: str = os.getenv("VOLC_ACCESS_KEY", "")
    volc_secret_key: str = os.getenv("VOLC_SECRET_KEY", "")
    volc_token: str = os.getenv("VOLC_TOKEN", "")
    
    # Request Configuration
    request_timeout: int = 30
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 0.9
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create settings instance
settings = Settings()
