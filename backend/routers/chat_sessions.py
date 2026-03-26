"""
Persist recipe chat threads per user in MongoDB (`chat_sessions` collection).
"""

from datetime import datetime
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from configs.database import get_collection
from schemas.chat_session import (
    ChatMessage,
    ChatSessionCreate,
    ChatSessionListItem,
    ChatSessionPatch,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from utils.auth_utils import get_current_user_from_token

router = APIRouter(prefix="/chat-sessions", tags=["chat-sessions"])

COLLECTION = "chat_sessions"


def _oid(s: str) -> ObjectId:
    try:
        return ObjectId(s)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session id",
        ) from exc


def _sort_sessions_for_list(docs: list) -> list:
    """Pinned first, then by updated_at descending."""

    def key(doc):
        pinned = bool(doc.get("pinned", False))
        ua = doc.get("updated_at")
        ts = ua.timestamp() if hasattr(ua, "timestamp") else 0.0
        return (not pinned, -ts)

    return sorted(docs, key=key)


@router.get("", response_model=List[ChatSessionListItem])
async def list_sessions(current_user: dict = Depends(get_current_user_from_token)):
    """List chat sessions for the current user: pinned first, then newest."""
    coll = await get_collection(COLLECTION)
    user_id = current_user["user_id"]
    cursor = coll.find({"user_id": user_id}).limit(100)
    items = await cursor.to_list(length=100)
    items = _sort_sessions_for_list(items)
    return [
        ChatSessionListItem(
            id=str(doc["_id"]),
            title=doc.get("title") or "Chat",
            updated_at=doc["updated_at"],
            pinned=bool(doc.get("pinned", False)),
        )
        for doc in items
    ]


@router.get("/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user_from_token),
):
    coll = await get_collection(COLLECTION)
    doc = await coll.find_one(
        {"_id": _oid(session_id), "user_id": current_user["user_id"]}
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    msgs = doc.get("messages") or []
    normalized = []
    for m in msgs:
        if isinstance(m, dict):
            normalized.append(
                {
                    "id": m.get("id") or "",
                    "role": m.get("role", "user"),
                    "content": m.get("content", ""),
                }
            )
    return ChatSessionResponse(
        id=str(doc["_id"]),
        title=doc.get("title") or "Chat",
        messages=[ChatMessage(**m) for m in normalized],
        updated_at=doc["updated_at"],
        created_at=doc["created_at"],
        pinned=bool(doc.get("pinned", False)),
    )


@router.post("", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: ChatSessionCreate,
    current_user: dict = Depends(get_current_user_from_token),
):
    now = datetime.utcnow()
    coll = await get_collection(COLLECTION)
    doc = {
        "user_id": current_user["user_id"],
        "title": body.title.strip() or "New chat",
        "messages": [],
        "pinned": False,
        "created_at": now,
        "updated_at": now,
    }
    result = await coll.insert_one(doc)
    doc["_id"] = result.inserted_id
    return ChatSessionResponse(
        id=str(doc["_id"]),
        title=doc["title"],
        messages=[],
        updated_at=doc["updated_at"],
        created_at=doc["created_at"],
        pinned=False,
    )


@router.put("/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: str,
    body: ChatSessionUpdate,
    current_user: dict = Depends(get_current_user_from_token),
):
    """Replace messages and/or title (full save from client)."""
    coll = await get_collection(COLLECTION)
    oid = _oid(session_id)
    user_id = current_user["user_id"]

    existing = await coll.find_one({"_id": oid, "user_id": user_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    now = datetime.utcnow()
    update_doc: dict = {"updated_at": now}
    if body.title is not None:
        t = body.title.strip()
        if t:
            update_doc["title"] = t
    messages = [m.model_dump() for m in body.messages]
    update_doc["messages"] = messages

    await coll.update_one({"_id": oid, "user_id": user_id}, {"$set": update_doc})
    doc = await coll.find_one({"_id": oid})
    raw = doc.get("messages") or []
    msgs = [
        ChatMessage(
            id=str(m.get("id") or ""),
            role=m.get("role", "user"),
            content=m.get("content", ""),
        )
        for m in raw
        if isinstance(m, dict)
    ]
    return ChatSessionResponse(
        id=str(doc["_id"]),
        title=doc.get("title") or "Chat",
        messages=msgs,
        updated_at=doc["updated_at"],
        created_at=doc["created_at"],
        pinned=bool(doc.get("pinned", False)),
    )


def _doc_to_response(doc: dict) -> ChatSessionResponse:
    raw = doc.get("messages") or []
    msgs = [
        ChatMessage(
            id=str(m.get("id") or ""),
            role=m.get("role", "user"),
            content=m.get("content", ""),
        )
        for m in raw
        if isinstance(m, dict)
    ]
    return ChatSessionResponse(
        id=str(doc["_id"]),
        title=doc.get("title") or "Chat",
        messages=msgs,
        updated_at=doc["updated_at"],
        created_at=doc["created_at"],
        pinned=bool(doc.get("pinned", False)),
    )


@router.patch("/{session_id}", response_model=ChatSessionResponse)
async def patch_session(
    session_id: str,
    body: ChatSessionPatch,
    current_user: dict = Depends(get_current_user_from_token),
):
    """Rename and/or toggle pin without replacing messages."""
    coll = await get_collection(COLLECTION)
    oid = _oid(session_id)
    user_id = current_user["user_id"]

    existing = await coll.find_one({"_id": oid, "user_id": user_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if body.title is None and body.pinned is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide title and/or pinned",
        )

    now = datetime.utcnow()
    update_doc: dict = {"updated_at": now}
    if body.title is not None:
        t = body.title.strip()
        if not t:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title cannot be empty",
            )
        update_doc["title"] = t
    if body.pinned is not None:
        update_doc["pinned"] = body.pinned

    await coll.update_one({"_id": oid, "user_id": user_id}, {"$set": update_doc})
    doc = await coll.find_one({"_id": oid})
    return _doc_to_response(doc)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user_from_token),
):
    coll = await get_collection(COLLECTION)
    result = await coll.delete_one(
        {"_id": _oid(session_id), "user_id": current_user["user_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
