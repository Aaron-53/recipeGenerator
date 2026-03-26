"""
FastAPI router for recipe chat and rating endpoints.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from configs.database import get_collection
from rating.chat_integration import (
    build_system_prompt,
    call_ollama,
    is_recipe_response,
    try_preflight_end_session,
    try_preflight_rating_digit,
)
from rating.qdrant_storage import save_rating
from dual_retrieval_bridge import retrieve_ranked_recipes
from utils.auth_utils import get_current_user_from_token

router = APIRouter(prefix="/chat", tags=["chat"])


class MessageRequest(BaseModel):
    message: str
    history: list[dict] = Field(
        default_factory=list,
        description="[{role, content}, ...] prior turns only (current message is separate).",
    )
    inventory: list[str] = Field(
        default_factory=list,
        description="Ingredient names; if empty, loaded from MongoDB for this user.",
    )


class MessageResponse(BaseModel):
    reply: str
    is_recipe: bool
    rating_saved: bool = False
    trigger_rating_ui: bool = False
    inventory_used: Optional[list[str]] = Field(
        default=None,
        description="Set only when vector retrieval ran; merged request + Mongo inventory.",
    )


class RatingRequest(BaseModel):
    recipe_text: str
    rating: int = Field(..., ge=1, le=5)
    review: str = Field(default="", max_length=500)


class RatingResponse(BaseModel):
    message: str


async def get_user_inventory_names(user_id: str) -> list[str]:
    coll = await get_collection("inventory")
    cursor = coll.find({"user_id": user_id})
    items = await cursor.to_list(length=500)
    return [str(i["name"]).strip() for i in items if i.get("name")]


def merge_inventory_for_retrieval(
    client_names: list[str], server_names: list[str]
) -> list[str]:
    """
    Dedupe case-insensitively; prefer order: client first, then server-only items.
    Ensures the logged-in user's Mongo inventory is always included in vector search.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in (client_names or []) + (server_names or []):
        name = str(raw).strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(name)
    return out


@router.post("/message", response_model=MessageResponse)
async def send_message(
    body: MessageRequest,
    current_user: dict = Depends(get_current_user_from_token),
):
    user_id = current_user["user_id"]
    prior = body.history
    msg = body.message

    digit = try_preflight_rating_digit(msg, prior, user_id)
    if digit:
        reply, saved = digit
        return MessageResponse(
            reply=reply,
            is_recipe=False,
            rating_saved=saved,
            trigger_rating_ui=False,
        )

    end_reply = try_preflight_end_session(msg, prior)
    if end_reply:
        return MessageResponse(
            reply=end_reply,
            is_recipe=False,
            rating_saved=False,
            trigger_rating_ui=True,
        )

    server_inv = await get_user_inventory_names(user_id)
    inventory = merge_inventory_for_retrieval(body.inventory, server_inv)
    items = await asyncio.to_thread(
        retrieve_ranked_recipes,
        body.message,
        inventory,
        5,
        30,
    )
    system_message = build_system_prompt(body.message, user_id, items, inventory)
    full_history = prior + [{"role": "user", "content": msg}]
    reply, saved, trigger = await asyncio.to_thread(
        call_ollama,
        system_message,
        full_history,
        user_id,
    )
    return MessageResponse(
        reply=reply,
        is_recipe=is_recipe_response(reply),
        rating_saved=saved,
        trigger_rating_ui=trigger,
        inventory_used=inventory,
    )


@router.post("/rate", response_model=RatingResponse)
async def rate_recipe(
    body: RatingRequest,
    current_user: dict = Depends(get_current_user_from_token),
):
    """Manual rating if the user prefers not to type a number in chat."""
    user_id = current_user["user_id"]

    save_rating(
        recipe_text=body.recipe_text,
        rating=body.rating,
        review=body.review,
        user_id=user_id,
    )

    return RatingResponse(
        message=f"Rating {body.rating}/5 saved. I'll use this next time!"
    )
