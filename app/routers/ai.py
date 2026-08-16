from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.params import Depends
from fastapi.responses import StreamingResponse
from langchain_classic.agents import initialize
from openai import APIError, APITimeoutError
import json
import traceback
import os
import uuid

from app.services.agent_memory import save_memory, load_memory, clear_memory
from app.services.agent import run_agent, graph
from app.services.rag import process_document, hybrid_search, UPLOAD_DIR
from app.schemas.ai import ChatRequest, ChatResponse, SummarizeResponse, SummarizeRequest, AgentRequest, AgentResponse
from app.services.llm import get_llm_client
from app.services.chat_history import get_history, add_to_history, clear_history
from app.routers.users import get_current_user # 复用用户认证1
from app.models import User
from app.core.config import settings

router = APIRouter(prefix="/ai", tags=["AI"])

MAX_FILE_SIZE = 5 * 1024 * 1024 # 5MB

def _build_messages(username: str, request: ChatRequest) -> list:
    """构建完整消息列表 (含历史) """
    messages = [{"role": "system", "content": "你是一个技术博客助手"}]

    if request.use_history:
        if request.clear_history:
            clear_history(username)
        else:
            messages.extend(get_history(username))

    for m in request.messages:
        messages.append({"role": m.role, "content": m.content})

    return messages

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user)):
    """非流式对话接口 (支持历史记录, 自动识别当前登录用户) """
    client = get_llm_client()
    model = request.model or settings.LLM_MODEL
    messages = _build_messages(current_user.username, request)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        content = response.choices[0].message.content

        if request.use_history:
            for m in request.messages:
                add_to_history(current_user.username, m.role, m.content)
            add_to_history(current_user.username, "assistant", content)

        return ChatResponse(
            content=content,
            model=model,
            usage=response.usage.model_dump() if response.usage else None
        )

    except APITimeoutError:
        raise HTTPException(status_code=504, detail="LLM请求超时")
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM服务错误: {e}")
    except Exception:
        raise HTTPException(status_code=500, detail="服务暂不可用")

async def _stream_generator(
        client, model, messages,
        temperature, max_tokens, username,
        request_messages, use_history
):
    """流式生成器"""
    content_parts = []

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
                part = chunk.choices[0].delta.content
                content_parts.append(part)
                yield f"data: {part}\n\n"
        yield "data: [DONE]\n\n"

        if use_history:
            for m in request_messages:
                add_to_history(username, m.role, m.content)
            add_to_history(username, "assistant", "".join(content_parts))

    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"

@router.post("/chat/stream")
async  def chat_stream(request:ChatRequest, current_user: User = Depends(get_current_user)):
    """流式对话接口 (SSE, 支持历史记录, 自动识别当前登录用户) """
    client = get_llm_client()
    model = request.model or settings.LLM_MODEL
    message = _build_messages(current_user.username, request)

    return StreamingResponse(
        _stream_generator(
            client, model, message,
            request.temperature, request.max_tokens,
            current_user.username, request.messages, request.use_history
        ),
        media_type="text/event-stream",
    )

@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_article(request: SummarizeRequest):
    """文章智能摘要 (结构化JSON输出) """
    client = get_llm_client()
    model = settings.LLM_MODEL

    system_prompt = f"""你是一个技术文章摘要助手。请为以下文章生成摘要、关键词和推荐分类。
要求：
1. 摘要长度不超过{request.max_length}字
2. 关键词3-5个
3. 推荐分类从以下中选择：前端、后端、数据库、DevOps、AI、其他

请严格按照以下JSON格式输出，不要输出其他内容：
{{
    "title": "文章标题",
    "summary": "摘要内容",
    "keywords": ["关键词1", "关键词2"],
    "category": "推荐分类"
}}"""

    user_prompt = f"标题: {request.title}\n\n正文: {request.content}"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1000,
        )

        result = json.loads(response.choices[0].message.content)
        return SummarizeResponse(**result)

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="LLM返回格式错误")
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="LLM请求超时")
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM服务错误: {e}")
    except Exception as e:
        print(f"❌ 接口报错详情: {e}")
        traceback.print_exc()
    raise HTTPException(status_code=500, detail="服务暂不可用")

@router.post("/upload")
async def upload_document(
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user)
):
    """上传文档到知识库 (支持 txt/md, 限制5MB) """
    # 限制文件类型
    if not file.filename.endswith((".txt", ".md")):
        raise HTTPException(status_code=400, detail="仅支持 .txt 和 .md 文件")

    # 限制文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件大小超过5MB限制")

    # 保存文件
    ext = os.path.splitext(file.filename)[1]
    save_name = f"{current_user.username}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(UPLOAD_DIR, save_name)

    with open(file_path, "wb") as f:
        f.write(content)

    # 处理文档 (切分+Embedding+存储)
    try:
        chunk_count = process_document(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档处理失败: {e}")

    return {
        "message": "上传成功",
        "filename": file.filename,
        "chunks": chunk_count,
    }

@router.post("/ask")
async def ask_knowledge(
        request: ChatRequest,
        current_user: User = Depends(get_current_user)
):
    """
    基于知识库问答（Hybrid Search），无相关文档时降级为直接LLM回答
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 获取用户最后一条问题
    query = request.messages[-1].content

    # 混合检索
    try:
        contexts =hybrid_search(query, k=3)
    except Exception:
        raise HTTPException(status_code=500, detail="知识库检索失败")

    # 构造 RAG Prompt
    if contexts:
        context_text = "\n\n".join(contexts)
        prompt = f"""基于以下文档片段回答问题：
    
        {context_text}
    
        问题：{query}
        请用中文简洁回答，如果文档中没有相关信息，请明确说明。"""
    else:
        # 降级: 直接问LLM, 不强制404
        prompt = query

    # 调用 LLM
    client = get_llm_client()
    model = request.model or settings.LLM_MODEL

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个知识库问答助手"},
                {"role": "user", "content": prompt},
            ],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        return ChatResponse(
            content=response.choices[0].message.content,
            model=model,
            usage=response.usage.model_dump() if response.usage else None,
        )

    except APITimeoutError:
        raise HTTPException(status_code=504, detail="LLM请求超时")
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM服务错误: {e}")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="服务暂不可用")

@router.post("/agent", response_model=AgentResponse)
async def agent_chat(
        request: AgentRequest,
        current_user: User = Depends(get_current_user)
):
    """
    Agent 智能体对话接口（支持记忆持久化）
    - 传 thread_id 自动关联历史对话
    - 传 clear_memory=true 清空历史
    """
    model = request.model or settings.LLM_MODEL

    # 构建消息列表
    messages = []

    if request.thread_id:
        if request.clear_memory:
            clear_memory(request.thread_id)
        else:
            history = load_memory(request.thread_id)
            messages.extend(history)

    # 添加本次消息
    for m in request.messages:
        messages.append({"role": m.role, "content": m.content})

    try:
        # 运行 Agent
        result = graph.invoke({"messages": messages})
        final_msg = result["messages"][-1]
        content = final_msg.content if hasattr(final_msg, "content") else str(final_msg)

        # 保存完整对话到 Redis
        if request.thread_id:
            save_memory(request.thread_id, result["messages"])

        return AgentResponse(
            content=content,
            model=model,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 执行失败: {e}")

def _agent_stream_generator(messages: list):
    """Agent 流式生成器"""
    initial_state = {"messages": messages}

    for event in graph.stream(initial_state, stream_mode="values"):
        last_msg = event["messages"][-1]

        # 工具调用
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            for tc in last_msg.tool_calls:
                yield f"data: [调用工具] {tc['name']}({tc['args']})\n\n"

        elif hasattr(last_msg, "content") and last_msg.content:
            yield f"data: {last_msg.content}\n\n"

    yield "data: [DONE]\n\n"

@router.post("/agent/stream")
async def agent_chat_stream(
        request: AgentRequest,
        current_user: User = Depends(get_current_user)
):
    """
    Agent 智能体对话接口（SSE 流式，支持记忆持久化）
    """

    # 构建消息列表 (同非流式)
    messages = []

    if request.thread_id:
        if request.clear_memory:
            clear_memory(request.thread_id)
        else:
            history = load_memory(request.thread_id)
            messages.extend(history)

    for m in request.messages:
        messages.append({"role": m.role, "content": m.content})

    async def _stream():
        all_messages = list(messages) # 复制一份用于保存

        for event in graph.stream({"messages": messages}, stream_mode="values"):
            last_msg = event["messages"][-1]

            # 工具调用
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                for tc in last_msg.tool_calls:
                    yield f"data: [调用工具] {tc['name']}({tc['args']})\n\n"

            # 最终回答
            elif hasattr(last_msg, "content") and last_msg.content:
                yield f"data: {last_msg.content}\n\n"

            # 更新完整消息列表
            all_messages = event["messages"]

        yield "data: [DONE]\n\n"

        # 保存到 Redis
        if request.thread_id:
            save_memory(request.thread_id, all_messages)

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
    )