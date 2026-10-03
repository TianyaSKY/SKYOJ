"""通用消息响应。"""

from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str
