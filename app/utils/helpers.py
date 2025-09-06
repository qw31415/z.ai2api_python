"""
Utility functions for the application
"""

import json
import re
import time
import random
from typing import Dict, List, Optional, Any, Tuple, Generator
import requests
from fake_useragent import UserAgent

from app.core.config import settings

# 全局 UserAgent 实例，避免每次调用都创建新实例
_user_agent_instance = None

def get_user_agent_instance() -> UserAgent:
    """获取或创建 UserAgent 实例（单例模式）"""
    global _user_agent_instance
    if _user_agent_instance is None:
        _user_agent_instance = UserAgent()
    return _user_agent_instance


def debug_log(message: str, *args) -> None:
    """Log debug message if debug mode is enabled"""
    if settings.DEBUG_LOGGING:
        if args:
            print(f"[DEBUG] {message % args}")
        else:
            print(f"[DEBUG] {message}")


def generate_request_ids() -> Tuple[str, str]:
    """Generate unique IDs for chat and message"""
    timestamp = int(time.time())
    chat_id = f"{timestamp * 1000}-{timestamp}"
    msg_id = str(timestamp * 1000000)
    return chat_id, msg_id


def is_special_key_format(key: str) -> bool:
    """检查是否为特殊格式的key（32位hex.随机字符串格式）"""
    if not key or len(key) < 35:  # 至少32+1+2字符
        return False
    
    # 检查是否包含点号分隔符
    if '.' not in key:
        return False
    
    parts = key.split('.')
    if len(parts) != 2:
        return False
    
    hex_part, suffix_part = parts
    
    # 检查第一部分是否为32位十六进制
    if len(hex_part) != 32:
        return False
    
    try:
        int(hex_part, 16)  # 验证是否为有效十六进制
    except ValueError:
        return False
    
    # 检查第二部分是否有足够长度（至少2个字符）
    if len(suffix_part) < 2:
        return False
    
    return True


def get_browser_headers(referer_chat_id: str = "") -> Dict[str, str]:
    """Get browser headers for API requests with dynamic User-Agent"""
    
    # 获取 UserAgent 实例
    ua = get_user_agent_instance()
    
    # 随机选择一个浏览器类型，偏向使用 Chrome 和 Edge
    browser_choices = ['chrome', 'chrome', 'chrome', 'edge', 'edge', 'firefox', 'safari']
    browser_type = random.choice(browser_choices)
    
    try:
        # 根据浏览器类型获取 User-Agent
        if browser_type == 'chrome':
            user_agent = ua.chrome
        elif browser_type == 'edge':
            user_agent = ua.edge
        elif browser_type == 'firefox':
            user_agent = ua.firefox
        elif browser_type == 'safari':
            user_agent = ua.safari
        else:
            user_agent = ua.random
    except:
        # 如果获取失败，使用随机 User-Agent
        user_agent = ua.random
    
    # 提取浏览器版本信息
    chrome_version = "139"  # 默认版本
    edge_version = "139"
    
    if "Chrome/" in user_agent:
        try:
            chrome_version = user_agent.split("Chrome/")[1].split(".")[0]
        except:
            pass
    
    if "Edg/" in user_agent:
        try:
            edge_version = user_agent.split("Edg/")[1].split(".")[0]
            # Edge 基于 Chromium，使用 Edge 特定的 sec-ch-ua
            sec_ch_ua = f'"Microsoft Edge";v="{edge_version}", "Chromium";v="{chrome_version}", "Not_A Brand";v="24"'
        except:
            sec_ch_ua = f'"Not;A=Brand";v="8", "Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"'
    elif "Firefox/" in user_agent:
        # Firefox 不使用 sec-ch-ua
        sec_ch_ua = None
    else:
        # Chrome 或其他基于 Chromium 的浏览器
        sec_ch_ua = f'"Not;A=Brand";v="8", "Chromium";v="{chrome_version}", "Google Chrome";v="{chrome_version}"'
    
    # 构建动态 Headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": user_agent,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "X-FE-Version": "prod-fe-1.0.70",
        "Origin": settings.CLIENT_HEADERS["Origin"],
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    
    # 只有基于 Chromium 的浏览器才添加 sec-ch-ua
    if sec_ch_ua:
        headers["sec-ch-ua"] = sec_ch_ua
    
    # 添加 Referer
    if referer_chat_id:
        headers["Referer"] = f"{settings.CLIENT_HEADERS['Origin']}/c/{referer_chat_id}"
    
    # 调试日志
    if settings.DEBUG_LOGGING:
        debug_log(f"使用 User-Agent: {user_agent[:100]}...")
    
    return headers


def get_anonymous_token() -> str:
    """Get anonymous token for authentication"""
    headers = get_browser_headers()
    headers.update({
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": f"{settings.CLIENT_HEADERS['Origin']}/",
    })
    
    try:
        response = requests.get(
            f"{settings.CLIENT_HEADERS['Origin']}/api/v1/auths/",
            headers=headers,
            timeout=10.0
        )
        
        if response.status_code != 200:
            raise Exception(f"anon token status={response.status_code}")
        
        data = response.json()
        token = data.get("token")
        if not token:
            raise Exception("anon token empty")
        
        return token
    except Exception as e:
        debug_log(f"获取匿名token失败: {e}")
        raise


def get_auth_token(downstream_key: Optional[str] = None) -> str:
    """Get authentication token (downstream key, anonymous or fixed)"""
    # 如果提供了下游key，检查是否为特殊格式
    if downstream_key:
        if is_special_key_format(downstream_key):
            debug_log(f"检测到特殊格式key，使用下游key: {downstream_key[:10]}...")
            return downstream_key
        else:
            debug_log(f"key格式不匹配特殊格式，回退到默认模式: {downstream_key[:10]}...")
            # 不匹配特殊格式，回退到默认处理
    
    # 如果启用了匿名模式，尝试获取匿名token
    if settings.ANONYMOUS_MODE:
        try:
            token = get_anonymous_token()
            debug_log(f"匿名token获取成功: {token[:10]}...")
            return token
        except Exception as e:
            debug_log(f"匿名token获取失败，回退固定token: {e}")
    
    # 默认使用备份token
    return settings.BACKUP_TOKEN


def get_fallback_token() -> str:
    """获取回退token：优先尝试匿名token，失败则使用备份token"""
    # 总是优先尝试匿名token（即使未开启 ANONYMOUS_MODE）
    try:
        token = get_anonymous_token()
        debug_log(f"回退：匿名token获取成功: {token[:10]}...")
        return token
    except Exception as e:
        debug_log(f"回退：匿名token获取失败，使用备份token: {e}")
    
    # 使用备份token
    debug_log(f"回退：使用备份token: {settings.BACKUP_TOKEN[:10]}...")
    return settings.BACKUP_TOKEN


def transform_thinking_content(content: str) -> str:
    """Transform thinking content according to configuration"""
    # Remove summary tags
    content = re.sub(r'(?s)<summary>.*?</summary>', '', content)
    # Clean up remaining tags
    content = content.replace("</thinking>", "").replace("<Full>", "").replace("</Full>", "")
    content = content.strip()
    
    if settings.THINKING_PROCESSING == "think":
        content = re.sub(r'<details[^>]*>', '<span>', content)
        content = content.replace("</details>", "</span>")
    elif settings.THINKING_PROCESSING == "strip":
        content = re.sub(r'<details[^>]*>', '', content)
        content = content.replace("</details>", "")
    
    # Remove line prefixes
    content = content.lstrip("> ")
    content = content.replace("\\n> ", "\\n")
    
    return content.strip()


def call_upstream_api(
    upstream_req: Any,
    chat_id: str,
    auth_token: str,
    downstream_key: Optional[str] = None
) -> requests.Response:
    """Call upstream API with proper headers and fallback logic.

    - zai: 使用站点端点与浏览器头；必要时回退匿名token
    - openai: 使用标准OpenAI兼容头；不进行匿名回退
    """
    # 构造请求体
    if hasattr(upstream_req, "model_dump"):
        payload = upstream_req.model_dump(exclude_none=True)
        try:
            payload_dbg = upstream_req.model_dump_json()[:2000]
        except Exception:
            payload_dbg = str(payload)[:2000]
    else:
        payload = upstream_req
        try:
            import json as _json
            payload_dbg = _json.dumps(payload, ensure_ascii=False)[:2000]
        except Exception:
            payload_dbg = str(payload)[:2000]

    # 构造headers
    if settings.UPSTREAM_TYPE == "openai":
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "zai2api-proxy/1.0",
        }
    else:
        headers = get_browser_headers(chat_id)

    # Authorization
    headers["Authorization"] = f"Bearer {auth_token}"

    debug_log(f"调用上游API: {settings.API_ENDPOINT}")
    debug_log(f"上游请求体: {payload_dbg}")
    debug_log(f"使用认证token: {auth_token[:20]}...")

    response = requests.post(
        settings.API_ENDPOINT,
        json=payload,
        headers=headers,
        timeout=60.0,
        stream=True
    )

    debug_log(f"上游响应状态: {response.status_code}")

    # 仅 zai 模式下做匿名回退
    if (
        settings.UPSTREAM_TYPE == "zai"
        and response.status_code in (401, 403)
        and downstream_key
        and is_special_key_format(downstream_key)
    ):
        debug_log("特殊格式key认证失败，尝试使用回退token重试")

        # 获取回退token
        fallback_token = get_fallback_token()

        # 更新headers
        headers["Authorization"] = f"Bearer {fallback_token}"

        # 重试请求
        debug_log("使用回退token重新调用上游API")
        debug_log(f"回退token: {fallback_token[:20]}...")
        response = requests.post(
            settings.API_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=60.0,
            stream=True
        )

        debug_log(f"回退token上游响应状态: {response.status_code}")

    return response
