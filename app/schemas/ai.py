from pydantic import BaseModel, Field
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色: system/user/assistant")
    content: str = Field(..., description="消息内容")

class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="对话消息列表")
    model: Optional[str] = Field(default=None, description="模型名称, 使用默认配置")
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2, description="创造性, 0-2")
    max_tokens: Optional[int] = Field(default=1000, ge=1, le=4000, description="最大输出长度")

class ChatResponse(BaseModel):
    content: str = Field(..., description="模型回复内容")
    model: str = Field(..., description="使用的模型")
    usage: Optional[dict] = Field(default=None, description="Token消耗信息")
