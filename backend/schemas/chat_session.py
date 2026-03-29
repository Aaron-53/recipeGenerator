from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class RankedSuggestionEntry(BaseModel):
    title: str = ""
    recipe_id: str = ""
    point_id: str = ""
    ingredients: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    tips: str = ""


class ChatMessage(BaseModel):
    id: str = ""
    role: Literal["user", "assistant"]
    content: str = ""
    msg_type: Optional[str] = None
    recipe_id: Optional[str] = None
    point_id: Optional[str] = None
    ranked_suggestions: List[RankedSuggestionEntry] = Field(default_factory=list)


class ChatSessionCreate(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=120)


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=120)
    messages: List[ChatMessage] = Field(default_factory=list)
    meta: Optional[Dict[str, Any]] = None


class ChatSessionPatch(BaseModel):
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
    meta: Dict[str, Any] = Field(default_factory=dict)
