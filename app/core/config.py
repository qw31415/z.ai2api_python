#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Application configuration
"""

import os
from typing import Dict, List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Basic settings
    AUTH_TOKEN: str = "sk-your-api-key"
    API_ENDPOINT: str = "https://chat.z.ai/api/chat/completions"
    LISTEN_PORT: int = 8080
    DEBUG_LOGGING: bool = True
    
    # Model settings
    PRIMARY_MODEL: str = "GLM-4.5"
    THINKING_MODEL: str = "GLM-4.5-Thinking"
    SEARCH_MODEL: str = "GLM-4.5-Search"
    AIR_MODEL: str = "GLM-4.5-Air"
    
    # Feature settings
    THINKING_PROCESSING: str = "think"  # think, strip, raw
    ANONYMOUS_MODE: bool = True
    TOOL_SUPPORT: bool = True
    SKIP_AUTH_TOKEN: bool = False
    SCAN_LIMIT: int = 200000
    
    # Z.ai token
    BACKUP_TOKEN: str = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWV9.TJVA95OrM7E2cBab30RMHrHDcEfxjoYZgeFONFh7HgQ"
    
    # MCP Server Configuration
    MCP_SERVERS: Dict[str, Dict[str, str]] = {
        "deep-web-search": {
            "name": "deep-web-search",
            "description": "Deep web search functionality",
            "type": "search",
            "enabled": "true"
        },
        "file-manager": {
            "name": "file-manager", 
            "description": "File management operations",
            "type": "file",
            "enabled": "false"
        },
        "code-executor": {
            "name": "code-executor",
            "description": "Code execution environment", 
            "type": "code",
            "enabled": "false"
        }
    }
    
    # Tool Server Configuration
    TOOL_SERVERS: List[str] = []
    
    # MCP Server Health Check
    MCP_HEALTH_CHECK_ENABLED: bool = True
    MCP_HEALTH_CHECK_TIMEOUT: int = 5
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
    def get_enabled_mcp_servers(self) -> List[str]:
        """Get list of enabled MCP servers"""
        return [
            server_name for server_name, config in self.MCP_SERVERS.items()
            if config.get("enabled", "false").lower() == "true"
        ]
    
    def get_mcp_server_config(self, server_name: str) -> Optional[Dict[str, str]]:
        """Get configuration for specific MCP server"""
        return self.MCP_SERVERS.get(server_name)
    
    def is_mcp_server_enabled(self, server_name: str) -> bool:
        """Check if MCP server is enabled"""
        config = self.get_mcp_server_config(server_name)
        return config and config.get("enabled", "false").lower() == "true"


settings = Settings()
