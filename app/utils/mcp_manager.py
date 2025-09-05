#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MCP (Model Context Protocol) Manager
"""

import time
from typing import List, Dict, Optional, Any
from app.core.config import settings
from app.utils.helpers import debug_log


class MCPManager:
    """Manager for MCP servers and tool servers"""
    
    def __init__(self):
        self._last_health_check = 0
        self._health_check_interval = 60  # 60 seconds
        self._server_health_status = {}
    
    def get_mcp_servers_for_request(
        self, 
        model: str, 
        is_search: bool = False, 
        has_tools: bool = False
    ) -> List[str]:
        """Get appropriate MCP servers for the request"""
        mcp_servers = []
        
        # Add search server if search is enabled
        if is_search and settings.is_mcp_server_enabled("deep-web-search"):
            if self._is_server_healthy("deep-web-search"):
                mcp_servers.append("deep-web-search")
                debug_log("添加搜索MCP服务器: deep-web-search")
            else:
                debug_log("搜索MCP服务器不健康，跳过: deep-web-search")
        
        # Add file manager if tools are present and enabled
        if has_tools and settings.is_mcp_server_enabled("file-manager"):
            if self._is_server_healthy("file-manager"):
                mcp_servers.append("file-manager")
                debug_log("添加文件管理MCP服务器: file-manager")
            else:
                debug_log("文件管理MCP服务器不健康，跳过: file-manager")
        
        # Add code executor for specific models if enabled
        if (model in [settings.PRIMARY_MODEL, settings.THINKING_MODEL] and 
            settings.is_mcp_server_enabled("code-executor")):
            if self._is_server_healthy("code-executor"):
                mcp_servers.append("code-executor")
                debug_log("添加代码执行MCP服务器: code-executor")
            else:
                debug_log("代码执行MCP服务器不健康，跳过: code-executor")
        
        # Always include enabled servers from configuration
        enabled_servers = settings.get_enabled_mcp_servers()
        for server in enabled_servers:
            if server not in mcp_servers and self._is_server_healthy(server):
                mcp_servers.append(server)
                debug_log(f"添加配置启用的MCP服务器: {server}")
        
        debug_log(f"最终MCP服务器列表: {mcp_servers}")
        return mcp_servers
    
    def get_tool_servers_for_request(self, tools: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """Get appropriate tool servers for the request"""
        tool_servers = []
        
        if not tools:
            return tool_servers
        
        # Analyze tools to determine required servers
        for tool in tools:
            if not isinstance(tool, dict):
                continue
                
            tool_type = tool.get("type", "")
            function_info = tool.get("function", {})
            function_name = function_info.get("name", "")
            
            # Map function names to tool servers
            if function_name.startswith(("search_", "web_")):
                if "search-tools" not in tool_servers:
                    tool_servers.append("search-tools")
            elif function_name.startswith(("file_", "read_", "write_")):
                if "file-tools" not in tool_servers:
                    tool_servers.append("file-tools")
            elif function_name.startswith(("code_", "execute_", "run_")):
                if "code-tools" not in tool_servers:
                    tool_servers.append("code-tools")
        
        # Add configured tool servers
        configured_servers = getattr(settings, 'TOOL_SERVERS', [])
        for server in configured_servers:
            if server not in tool_servers:
                tool_servers.append(server)
        
        debug_log(f"工具服务器列表: {tool_servers}")
        return tool_servers
    
    def _is_server_healthy(self, server_name: str) -> bool:
        """Check if MCP server is healthy"""
        if not settings.MCP_HEALTH_CHECK_ENABLED:
            return True
        
        current_time = time.time()
        
        # Perform health check if needed
        if (current_time - self._last_health_check) > self._health_check_interval:
            self._perform_health_checks()
            self._last_health_check = current_time
        
        # Return cached health status
        return self._server_health_status.get(server_name, True)
    
    def _perform_health_checks(self):
        """Perform health checks on all configured MCP servers"""
        debug_log("执行MCP服务器健康检查")
        
        for server_name, config in settings.MCP_SERVERS.items():
            if config.get("enabled", "false").lower() != "true":
                continue
            
            try:
                # Simulate health check (in real implementation, this would ping the server)
                # For now, we assume all configured servers are healthy
                is_healthy = self._check_server_health(server_name, config)
                self._server_health_status[server_name] = is_healthy
                
                if is_healthy:
                    debug_log(f"MCP服务器健康: {server_name}")
                else:
                    debug_log(f"MCP服务器不健康: {server_name}")
                    
            except Exception as e:
                debug_log(f"MCP服务器健康检查失败 {server_name}: {e}")
                self._server_health_status[server_name] = False
    
    def _check_server_health(self, server_name: str, config: Dict[str, str]) -> bool:
        """Check individual server health"""
        # In a real implementation, this would:
        # 1. Send a ping/health check request to the MCP server
        # 2. Check response time and status
        # 3. Validate server capabilities
        
        # For now, simulate based on server type
        server_type = config.get("type", "")
        
        # Simulate different health check results
        if server_type == "search":
            # Search servers are usually reliable
            return True
        elif server_type == "file":
            # File servers might have permission issues
            return True  # Assume healthy for demo
        elif server_type == "code":
            # Code execution servers might be resource-constrained
            return True  # Assume healthy for demo
        else:
            # Unknown server types are assumed healthy
            return True
    
    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all MCP servers"""
        status = {}
        
        for server_name, config in settings.MCP_SERVERS.items():
            status[server_name] = {
                "name": server_name,
                "description": config.get("description", ""),
                "type": config.get("type", ""),
                "enabled": config.get("enabled", "false").lower() == "true",
                "healthy": self._server_health_status.get(server_name, True),
                "last_check": self._last_health_check
            }
        
        return status
    
    def enable_server(self, server_name: str) -> bool:
        """Enable MCP server"""
        if server_name in settings.MCP_SERVERS:
            settings.MCP_SERVERS[server_name]["enabled"] = "true"
            debug_log(f"启用MCP服务器: {server_name}")
            return True
        return False
    
    def disable_server(self, server_name: str) -> bool:
        """Disable MCP server"""
        if server_name in settings.MCP_SERVERS:
            settings.MCP_SERVERS[server_name]["enabled"] = "false"
            debug_log(f"禁用MCP服务器: {server_name}")
            return True
        return False
