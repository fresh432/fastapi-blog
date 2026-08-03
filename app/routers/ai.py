from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openai import APIError, APITimeoutError

from app.schemas.ai import ChatRequest, ChatResponse
from app.services.llm import get_llm_client
from app.core.config import settings

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """非流式对话接口"""
    client = get_llm_client()
    model = request.model or settings.LLM_MODEL

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        return ChatResponse(
            content=response.choices[0].message.content,
            model=model,
            usage=response.usage.model_dump() if response.usage else None
        )

    except APITimeoutError:
        raise HTTPException(status_code=504, detail="LLM请求超时")
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM服务错误: {e}")
    except Exception:
        raise HTTPException(status_code=500, detail="服务暂不可用")

async def _stream_generator(client, model, messages, temperature, max_tokens):
    """流式生成器"""
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield f"data: {chunk.choices[0].delta.content}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"

@router.post("/chat/stream")
async  def chat_stream(request:ChatRequest):
    """流式对话接口 (SSE)"""
    client = get_llm_client()
    model = request.model or settings.LLM_MODEL
    message = [{"role": m.role, "content": m.content} for m in request.messages]

    return StreamingResponse(
        _stream_generator(client, model, message, request.temperature, request.max_tokens),
        media_type="text/event-stream",
    )
