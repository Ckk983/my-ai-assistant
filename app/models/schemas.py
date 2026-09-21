"""数据结构层：定义"进出的数据长什么样"。

数据流位置：网页发来的数据先在这里被"校验"。
    字段缺失 / 类型不对 → FastAPI 自动返回 422 错误，业务代码根本不会被调用。
    这一步的作用是"防止脏数据把后面的程序弄崩"。
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """网页发给我们的东西长什么样。"""

    session_id: str = Field(default="default", description="会话ID，用来区分不同人的对话")
    question: str = Field(..., min_length=1, description="用户的问题，不能为空")


class ChatResponse(BaseModel):
    """我们返回给网页的东西长什么样。"""

    answer: str
    session_id: str
    used_tokens: int = 0


class MessageOut(BaseModel):
    """一条历史消息。"""

    role: str
    content: str