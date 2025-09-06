"""
OpenAI API endpoints
"""

import time
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.models.schemas import (
    OpenAIRequest, Message, UpstreamRequest, ModelItem, 
    ModelsResponse, Model
)
from app.utils.helpers import debug_log, generate_request_ids, get_auth_token
from app.utils.tools import process_messages_with_tools, content_to_string
from app.core.response_handlers import StreamResponseHandler, NonStreamResponseHandler

router = APIRouter()


@router.get("/v1/models")
async def list_models():
    """List available models"""
    current_time = int(time.time())
    response = ModelsResponse(
        data=[
            Model(
                id=settings.PRIMARY_MODEL,
                created=current_time,
                owned_by="z.ai"
            ),
            Model(
                id=settings.THINKING_MODEL,
                created=current_time,
                owned_by="z.ai"
            ),
            Model(
                id=settings.SEARCH_MODEL,
                created=current_time,
                owned_by="z.ai"
            ),
            Model(
                id=settings.AIR_MODEL,
                created=current_time,
                owned_by="z.ai"
            ),
        ]
    )
    return response


@router.post("/v1/chat/completions")
async def chat_completions(
    request: OpenAIRequest,
    authorization: str = Header(...)
):
    """Handle chat completion requests"""
    debug_log("收到chat completions请求")
    
    try:
        # 提取下游key
        downstream_key = None
        if authorization.startswith("Bearer "):
            downstream_key = authorization[7:]  # 去掉"Bearer "前缀
            debug_log(f"提取到key: {downstream_key[:10]}...")
        
        # 验证API key（如果SKIP_AUTH_TOKEN未启用且不是特殊格式key）
        if not settings.SKIP_AUTH_TOKEN:
            if not authorization.startswith("Bearer "):
                debug_log("缺少或无效的Authorization头")
                raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
            
            # 检查是否为特殊格式key，如果不是则验证固定token
            from app.utils.helpers import is_special_key_format
            if not is_special_key_format(downstream_key):
                if downstream_key != settings.AUTH_TOKEN:
                    debug_log(f"无效的API key: {downstream_key}")
                    raise HTTPException(status_code=401, detail="Invalid API key")
                debug_log(f"API key验证通过，AUTH_TOKEN={downstream_key[:8]}......")
            else:
                debug_log(f"检测到特殊格式key，跳过固定token验证: {downstream_key[:10]}...")
        else:
            debug_log("SKIP_AUTH_TOKEN已启用，跳过API key验证")
        
        debug_log(f"请求解析成功 - 模型: {request.model}, 流式: {request.stream}, 消息数: {len(request.messages)}")
        
        # Generate IDs
        chat_id, msg_id = generate_request_ids()
        
        # Process messages with tools
        processed_messages = process_messages_with_tools(
            [m.model_dump() for m in request.messages],
            request.tools,
            request.tool_choice
        )
        
        # Convert back to Message objects
        upstream_messages: List[Message] = []
        for msg in processed_messages:
            content = content_to_string(msg.get("content"))
            
            upstream_messages.append(Message(
                role=msg["role"],
                content=content,
                reasoning_content=msg.get("reasoning_content")
            ))
        
        # Determine model features
        is_thinking = request.model == settings.THINKING_MODEL
        is_search = request.model == settings.SEARCH_MODEL
        is_air = request.model == settings.AIR_MODEL
        search_mcp = "deep-web-search" if is_search else ""
        
        # Determine upstream model based on requested model
        if is_air:
            upstream_model_id = "0727-106B-API"  # for zai upstream
            upstream_model_name = "GLM-4.5-Air"  # for openai upstream
        else:
            upstream_model_id = "0727-360B-API"
            upstream_model_name = "GLM-4.5"

        # Build upstream request by mode
        if settings.UPSTREAM_TYPE == "openai":
            # 官方 OpenAI 兼容上游所需最小字段
            upstream_req = {
                "model": upstream_model_name,
                "messages": [m.model_dump(exclude_none=True) for m in upstream_messages],
                "stream": bool(request.stream),
            }
            if request.tools:
                upstream_req["tools"] = request.tools
            if request.tool_choice is not None:
                upstream_req["tool_choice"] = request.tool_choice
        else:
            upstream_req = UpstreamRequest(
                stream=True,  # Always use streaming from zai upstream
                chat_id=chat_id,
                id=msg_id,
                model=upstream_model_id,  # Dynamic upstream model ID
                messages=upstream_messages,
                params={},
                features={
                    "enable_thinking": is_thinking,
                    "web_search": is_search,
                    "auto_web_search": is_search,
                },
                background_tasks={
                    "title_generation": False,
                    "tags_generation": False,
                },
                mcp_servers=[search_mcp] if search_mcp else [],
                model_item=ModelItem(
                    id=upstream_model_id,
                    name=upstream_model_name,
                    owned_by="openai"
                ),
                tool_servers=[],
                variables={
                    "{{USER_NAME}}": "User",
                    "{{USER_LOCATION}}": "Unknown",
                    "{{CURRENT_DATETIME}}": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        
        # Get authentication token (pass downstream_key if available)
        auth_token = get_auth_token(downstream_key)
        
        # Check if tools are enabled and present
        has_tools = (settings.TOOL_SUPPORT and 
                    request.tools and 
                    len(request.tools) > 0 and 
                    request.tool_choice != "none")
        
        # Handle response based on stream flag
        if request.stream:
            handler = StreamResponseHandler(upstream_req, chat_id, auth_token, has_tools, downstream_key)
            return StreamingResponse(
                handler.handle(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            handler = NonStreamResponseHandler(upstream_req, chat_id, auth_token, has_tools, downstream_key)
            return handler.handle()
            
    except HTTPException:
        raise
    except Exception as e:
        debug_log(f"处理请求时发生错误: {str(e)}")
        import traceback
        debug_log(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
