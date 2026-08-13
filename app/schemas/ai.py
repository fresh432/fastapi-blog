from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色: system/user/assistant")
    content: str = Field(..., min_length=1, max_length=8000, description="消息内容, 消息最多8000字符")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ('system', 'user', 'assistant'):
            raise ValueError("role必须是 system/user/assistant 之一")
        return v

class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="对话消息列表")
    use_history: bool = Field(default=False, description="是否使用历史对话")
    clear_history: bool = Field(default=False, description="是否清空对话记录")
    model: Optional[str] = Field(default=None, description="模型名称, 使用默认配置")
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2, description="创造性, 0-2")
    max_tokens: Optional[int] = Field(default=1000, ge=1, le=4000, description="最大输出长度")

    @field_validator('messages')
    @classmethod
    def validate_messages(cls, v):
        if not v:
            raise ValueError("messages不能为空")
        return v

class ChatResponse(BaseModel):
    content: str = Field(..., description="模型回复内容")
    model: str = Field(..., description="使用的模型")
    usage: Optional[dict] = Field(default=None, description="Token消耗信息")

class SummarizeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="文章标题")
    content: str = Field(..., min_length=10, max_length=20000, description="文章正文, 最多20000字符")
    max_length: Optional[int] = Field(default=200, ge=50, le=1000, description="摘要最大长度")

class SummarizeResponse(BaseModel):
    title: str = Field(..., description="文章标题")
    summary: str = Field(..., description="文章摘要")
    keywords: List[str] = Field(..., description="关键词列表")
    category: Optional[str] = Field(default=None, description="推荐分类")

class AgentRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="对话消息列表")
    thread_id: Optional[str] = Field(default=None, description="对话线程ID, 用于关联历史")
    clear_memory: bool = Field(default=False, description="是否清空历史记忆")
    model: Optional[str] = Field(default=None, description="模型名称")
    temperature: Optional[float] = Field(default=0.3, ge=0, le=2)

class AgentResponse(BaseModel):
    content: str = Field(..., description="Agent 最终回复")
    model: str = Field(..., description="使用的模型")

