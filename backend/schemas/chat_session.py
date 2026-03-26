from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    id: str = ""
    role: Literal["user", "assistant"]
    content: str = ""


class ChatSessionCreate(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=120)


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=120)
    messages: List[ChatMessage] = Field(default_factory=list)


class ChatSessionPatch(BaseModel):
    """Partial update (rename / pin) without sending full messages."""

    title: Optional[str] = Field(None, min_length=1, max_length=120)
    pinned: Optional[bool] = None


class ChatSessionListItem(BaseModel):
    id: str
    title: str
    updated_at: datetime
    pinned: bool = False


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    messages: List[ChatMessage]
    updated_at: datetime
    created_at: datetime
    pinned: bool = False
