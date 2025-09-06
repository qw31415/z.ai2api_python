"""
Response handlers for streaming and non-streaming responses
"""

import json
import time
from typing import Generator, Optional
import requests
from fastapi import HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.config import settings
from app.models.schemas import (
    Message, Delta, Choice, Usage, OpenAIResponse, 
    UpstreamRequest, UpstreamData, UpstreamError, ModelItem
)
from app.utils.helpers import debug_log, call_upstream_api, transform_thinking_content
from app.utils.sse_parser import SSEParser
from app.utils.tools import extract_tool_invocations, remove_tool_json_content


def create_openai_response_chunk(
    model: str,
    delta: Optional[Delta] = None,
    finish_reason: Optional[str] = None
) -> OpenAIResponse:
    """Create OpenAI response chunk for streaming"""
    return OpenAIResponse(
        id=f"chatcmpl-{int(time.time())}",
        object="chat.completion.chunk",
        created=int(time.time()),
        model=model,
        choices=[Choice(
            index=0,
            delta=delta or Delta(),
            finish_reason=finish_reason
        )]
    )


def handle_upstream_error(error: UpstreamError) -> Generator[str, None, None]:
    """Handle upstream error response"""
    debug_log(f"上游错误: code={error.code}, detail={error.detail}")
    
    # Send error chunk
    error_chunk = create_openai_response_chunk(
        model=settings.PRIMARY_MODEL,
        delta=Delta(content=f"Error: {error.detail}"),
        finish_reason="stop"
    )
    yield f"data: {error_chunk.model_dump_json()}\n\n"
    yield "data: [DONE]\n\n"


class ResponseHandler:
    """Base class for response handling"""
    
    def __init__(self, upstream_req: UpstreamRequest, chat_id: str, auth_token: str, downstream_key: Optional[str] = None):
        self.upstream_req = upstream_req
        self.chat_id = chat_id
        self.auth_token = auth_token
        self.downstream_key = downstream_key
    
    def _call_upstream(self) -> requests.Response:
        """Call upstream API with error handling"""
        try:
            return call_upstream_api(self.upstream_req, self.chat_id, self.auth_token, self.downstream_key)
        except Exception as e:
            debug_log(f"调用上游失败: {e}")
            raise
    
    def _handle_upstream_error(self, response: requests.Response) -> None:
        """Handle upstream error response"""
        debug_log(f"上游返回错误状态: {response.status_code}")
        if settings.DEBUG_LOGGING:
            debug_log(f"上游错误响应: {response.text}")


class StreamResponseHandler(ResponseHandler):
    """Handler for streaming responses"""
    
    def __init__(self, upstream_req: UpstreamRequest, chat_id: str, auth_token: str, has_tools: bool = False, downstream_key: Optional[str] = None):
        super().__init__(upstream_req, chat_id, auth_token, downstream_key)
        self.has_tools = has_tools
        self.buffered_content = ""
        self.tool_calls = None
    
    def handle(self) -> Generator[str, None, None]:
        """Handle streaming response"""
        debug_log(f"开始处理流式响应 (chat_id={self.chat_id})")
        
        try:
            response = self._call_upstream()
        except Exception:
            error_chunk = create_openai_response_chunk(
                model=settings.PRIMARY_MODEL,
                delta=Delta(content="Failed to call upstream"),
                finish_reason="stop"
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
            return
        
        if response.status_code != 200:
            self._handle_upstream_error(response)
            # 将上游错误摘要返回给客户端，便于排查
            snippet = response.text[:200] if hasattr(response, 'text') else ''
            msg = f"Upstream {response.status_code}: {snippet}"
            error_chunk = create_openai_response_chunk(
                model=settings.PRIMARY_MODEL,
                delta=Delta(content=msg),
                finish_reason="stop"
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
            return
        
        # Send initial role chunk
        first_chunk = create_openai_response_chunk(
            model=settings.PRIMARY_MODEL,
            delta=Delta(role="assistant")
        )
        yield f"data: {first_chunk.model_dump_json()}\n\n"
        
        # OpenAI 兼容模式：直接按 OpenAI 流式数据透传解析
        if settings.UPSTREAM_TYPE == "openai":
            debug_log("以 OpenAI 兼容流式格式解析")
            try:
                with SSEParser(response, debug_mode=settings.DEBUG_LOGGING) as parser:
                    for event in parser.iter_events():
                        if event["type"] != "data":
                            continue
                        data = event["data"]
                        # 处理 [DONE]
                        if isinstance(data, str):
                            if data.strip() == "[DONE]":
                                end_chunk = create_openai_response_chunk(
                                    model=settings.PRIMARY_MODEL,
                                    finish_reason="stop"
                                )
                                yield f"data: {end_chunk.model_dump_json()}\n\n"
                                yield "data: [DONE]\n\n"
                                debug_log("OpenAI流结束")
                                break
                            else:
                                continue
                        # 正常 JSON 数据
                        choices = data.get("choices", [])
                        if not choices:
                            continue
                        ch = choices[0]
                        delta_dict = ch.get("delta", {}) or {}
                        out_delta = Delta()
                        if delta_dict.get("content"):
                            out_delta.content = delta_dict["content"]
                        if delta_dict.get("reasoning_content"):
                            out_delta.reasoning_content = delta_dict["reasoning_content"]
                        if delta_dict.get("tool_calls"):
                            out_delta.tool_calls = delta_dict["tool_calls"]

                        if out_delta.content or out_delta.reasoning_content or out_delta.tool_calls:
                            chunk = create_openai_response_chunk(
                                model=settings.PRIMARY_MODEL,
                                delta=out_delta
                            )
                            yield f"data: {chunk.model_dump_json()}\n\n"
            except Exception as e:
                debug_log(f"处理OpenAI流时发生错误: {e}")
                error_chunk = create_openai_response_chunk(
                    model=settings.PRIMARY_MODEL,
                    delta=Delta(content=f"Stream processing error: {str(e)}"),
                    finish_reason="stop"
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
            return
        
        # Process stream
        debug_log("开始读取上游SSE流")
        sent_initial_answer = False
        
        try:
            with SSEParser(response, debug_mode=settings.DEBUG_LOGGING) as parser:
                for event in parser.iter_json_data(UpstreamData):
                    upstream_data = event['data']
                    
                    # Check for errors
                    if self._has_error(upstream_data):
                        error = self._get_error(upstream_data)
                        yield from handle_upstream_error(error)
                        break
                    
                    debug_log(f"解析成功 - 类型: {upstream_data.type}, 阶段: {upstream_data.data.phase}, "
                             f"内容长度: {len(upstream_data.data.delta_content)}, 完成: {upstream_data.data.done}")
                    
                    # Process content
                    yield from self._process_content(upstream_data, sent_initial_answer)
                    
                    # Check if done
                    if upstream_data.data.done or upstream_data.data.phase == "done":
                        debug_log("检测到流结束信号")
                        yield from self._send_end_chunk()
                        break
        except Exception as e:
            debug_log(f"处理流时发生错误: {e}")
            error_chunk = create_openai_response_chunk(
                model=settings.PRIMARY_MODEL,
                delta=Delta(content=f"Stream processing error: {str(e)}"),
                finish_reason="stop"
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
    
    def _has_error(self, upstream_data: UpstreamData) -> bool:
        """Check if upstream data contains error"""
        return bool(
            upstream_data.error or 
            upstream_data.data.error or 
            (upstream_data.data.inner and upstream_data.data.inner.error)
        )
    
    def _get_error(self, upstream_data: UpstreamData) -> UpstreamError:
        """Get error from upstream data"""
        return (
            upstream_data.error or 
            upstream_data.data.error or 
            (upstream_data.data.inner.error if upstream_data.data.inner else None)
        )
    
    def _process_content(
        self, 
        upstream_data: UpstreamData, 
        sent_initial_answer: bool
    ) -> Generator[str, None, None]:
        """Process content from upstream data"""
        content = upstream_data.data.delta_content or upstream_data.data.edit_content
        
        if not content:
            return
        
        # Transform thinking content
        if upstream_data.data.phase == "thinking":
            content = transform_thinking_content(content)
        
        # Buffer content if tools are enabled
        if self.has_tools:
            self.buffered_content += content
        else:
            # Handle initial answer content
            if (not sent_initial_answer and 
                upstream_data.data.edit_content and 
                upstream_data.data.phase == "answer"):
                
                content = self._extract_edit_content(upstream_data.data.edit_content)
                if content:
                    debug_log(f"发送普通内容: {content}")
                    chunk = create_openai_response_chunk(
                        model=settings.PRIMARY_MODEL,
                        delta=Delta(content=content)
                    )
                    yield f"data: {chunk.model_dump_json()}\n\n"
                    sent_initial_answer = True
            
            # Handle delta content
            if upstream_data.data.delta_content:
                if content:
                    if upstream_data.data.phase == "thinking":
                        debug_log(f"发送思考内容: {content}")
                        chunk = create_openai_response_chunk(
                            model=settings.PRIMARY_MODEL,
                            delta=Delta(reasoning_content=content)
                        )
                    else:
                        debug_log(f"发送普通内容: {content}")
                        chunk = create_openai_response_chunk(
                            model=settings.PRIMARY_MODEL,
                            delta=Delta(content=content)
                        )
                    yield f"data: {chunk.model_dump_json()}\n\n"
    
    def _extract_edit_content(self, edit_content: str) -> str:
        """Extract content from edit_content field"""
        parts = edit_content.split("</details>")
        return parts[1] if len(parts) > 1 else ""
    
    def _send_end_chunk(self) -> Generator[str, None, None]:
        """Send end chunk and DONE signal"""
        finish_reason = "stop"
        
        if self.has_tools:
            # Try to extract tool calls from buffered content
            self.tool_calls = extract_tool_invocations(self.buffered_content)
            
            if self.tool_calls:
                # Send tool calls with proper format
                for i, tc in enumerate(self.tool_calls):
                    tool_call_delta = {
                        "index": i,
                        "id": tc.get("id"),
                        "type": tc.get("type", "function"),
                        "function": tc.get("function", {}),
                    }
                    
                    out_chunk = create_openai_response_chunk(
                        model=settings.PRIMARY_MODEL,
                        delta=Delta(tool_calls=[tool_call_delta])
                    )
                    yield f"data: {out_chunk.model_dump_json()}\n\n"
                
                finish_reason = "tool_calls"
            else:
                # Send regular content
                trimmed_content = remove_tool_json_content(self.buffered_content)
                if trimmed_content:
                    content_chunk = create_openai_response_chunk(
                        model=settings.PRIMARY_MODEL,
                        delta=Delta(content=trimmed_content)
                    )
                    yield f"data: {content_chunk.model_dump_json()}\n\n"
        
        # Send final chunk
        end_chunk = create_openai_response_chunk(
            model=settings.PRIMARY_MODEL,
            finish_reason=finish_reason
        )
        yield f"data: {end_chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
        debug_log("流式响应完成")


class NonStreamResponseHandler(ResponseHandler):
    """Handler for non-streaming responses"""
    
    def __init__(self, upstream_req: UpstreamRequest, chat_id: str, auth_token: str, has_tools: bool = False, downstream_key: Optional[str] = None):
        super().__init__(upstream_req, chat_id, auth_token, downstream_key)
        self.has_tools = has_tools
    
    def handle(self) -> JSONResponse:
        """Handle non-streaming response"""
        debug_log(f"开始处理非流式响应 (chat_id={self.chat_id})")
        
        try:
            response = self._call_upstream()
        except Exception as e:
            debug_log(f"调用上游失败: {e}")
            raise HTTPException(status_code=502, detail="Failed to call upstream")
        
        if response.status_code != 200:
            self._handle_upstream_error(response)
            raise HTTPException(status_code=502, detail="Upstream error")
        
        # OpenAI 兼容模式：直接透传完整响应
        if settings.UPSTREAM_TYPE == "openai":
            try:
                return JSONResponse(content=response.json())
            except Exception:
                raise HTTPException(status_code=502, detail="Invalid upstream response")

        # Collect full response
        full_content = []
        debug_log("开始收集完整响应内容")
        
        try:
            with SSEParser(response, debug_mode=settings.DEBUG_LOGGING) as parser:
                for event in parser.iter_json_data(UpstreamData):
                    upstream_data = event['data']
                    
                    if upstream_data.data.delta_content:
                        content = upstream_data.data.delta_content
                        
                        if upstream_data.data.phase == "thinking":
                            content = transform_thinking_content(content)
                        
                        if content:
                            full_content.append(content)
                    
                    if upstream_data.data.done or upstream_data.data.phase == "done":
                        debug_log("检测到完成信号，停止收集")
                        break
        except Exception as e:
            debug_log(f"收集响应内容时发生错误: {e}")
            raise HTTPException(status_code=502, detail="Failed to process upstream response")
        
        final_content = "".join(full_content)
        debug_log(f"内容收集完成，最终长度: {len(final_content)}")
        
        # Handle tool calls for non-streaming
        tool_calls = None
        finish_reason = "stop"
        message_content = final_content
        
        if self.has_tools:
            tool_calls = extract_tool_invocations(final_content)
            if tool_calls:
                # Content must be null when tool_calls are present (OpenAI spec)
                message_content = None
                finish_reason = "tool_calls"
                debug_log(f"提取到工具调用: {json.dumps(tool_calls, ensure_ascii=False)}")
            else:
                # Remove tool JSON from content
                message_content = remove_tool_json_content(final_content)
                if not message_content:
                    message_content = final_content  # 保留原内容如果清理后为空
        
        # Build response
        response_data = OpenAIResponse(
            id=f"chatcmpl-{int(time.time())}",
            object="chat.completion",
            created=int(time.time()),
            model=settings.PRIMARY_MODEL,
            choices=[Choice(
                index=0,
                message=Message(
                    role="assistant",
                    content=message_content,
                    tool_calls=tool_calls
                ),
                finish_reason=finish_reason
            )],
            usage=Usage()
        )
        
        debug_log("非流式响应发送完成")
        return JSONResponse(content=response_data.model_dump(exclude_none=True))
