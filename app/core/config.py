"""
FastAPI application configuration module
"""

import os
from typing import Dict, Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_ENDPOINT: str = os.getenv("API_ENDPOINT", "https://chat.z.ai/api/chat/completions")
    AUTH_TOKEN: str = os.getenv("AUTH_TOKEN", "sk-your-api-key")
    BACKUP_TOKEN: str = os.getenv("BACKUP_TOKEN", "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjMxNmJjYjQ4LWZmMmYtNGExNS04NTNkLWYyYTI5YjY3ZmYwZiIsImVtYWlsIjoiR3Vlc3QtMTc1NTg0ODU4ODc4OEBndWVzdC5jb20ifQ.PktllDySS3trlyuFpTeIZf-7hl8Qu1qYF3BxjgIul0BrNux2nX9hVzIjthLXKMWAf9V0qM8Vm_iyDqkjPGsaiQ")
    
    # Model Configuration
    PRIMARY_MODEL: str = os.getenv("PRIMARY_MODEL", "GLM-4.5")
    THINKING_MODEL: str = os.getenv("THINKING_MODEL", "GLM-4.5-Thinking")
    SEARCH_MODEL: str = os.getenv("SEARCH_MODEL", "GLM-4.5-Search")
    AIR_MODEL: str = os.getenv("AIR_MODEL", "GLM-4.5-Air")
    
    # Server Configuration
    LISTEN_PORT: int = int(os.getenv("LISTEN_PORT", "8080"))
    DEBUG_LOGGING: bool = os.getenv("DEBUG_LOGGING", "true").lower() == "true"
    
    # Feature Configuration
    THINKING_PROCESSING: str = os.getenv("THINKING_PROCESSING", "think")  # strip: 去除<details>标签；think: 转为<span>标签；raw: 保留原样
    ANONYMOUS_MODE: bool = os.getenv("ANONYMOUS_MODE", "true").lower() == "true"
    TOOL_SUPPORT: bool = os.getenv("TOOL_SUPPORT", "true").lower() == "true"
    SCAN_LIMIT: int = int(os.getenv("SCAN_LIMIT", "200000"))
    SKIP_AUTH_TOKEN: bool = os.getenv("SKIP_AUTH_TOKEN", "false").lower() == "true"
    
    # Upstream/Deployment Configuration
    # UPSTREAM_TYPE: zai 使用站点流; openai 使用标准OpenAI兼容流（官方2API）
    UPSTREAM_TYPE: str = os.getenv("UPSTREAM_TYPE", "zai").lower()
    # Render Deployment Configuration - 已移除USE_DOWNSTREAM_KEYS，改为基于key格式自动检测
    RENDER_DEPLOYMENT: bool = os.getenv("RENDER_DEPLOYMENT", "true").lower() == "true"
    
    # Browser Headers
    CLIENT_HEADERS: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0",
        "Accept-Language": "zh-CN",
        "sec-ch-ua": '"Not;A=Brand";v="99", "Microsoft Edge";v="139", "Chromium";v="139"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "X-FE-Version": "prod-fe-1.0.70",
        "Origin": "https://chat.z.ai",
    }
    
    class Config:
        env_file = ".env"


settings = Settings()
