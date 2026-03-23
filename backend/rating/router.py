"""
rating/router.py
-----------------
FastAPI router for recipe chat and rating endpoints.

Add to main.py:
    from rating.router import router as rating_router
    app.include_router(rating_router)

    from rating import ensure_collection
    @app.on_event("startup")
    async def startup():
        ensure_collection()
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from utils.auth_utils import get_current_user_from_token
from .chat_integration import build_system_prompt, call_ollama, is_recipe_response
from .qdrant_storage import save_rating

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class MessageRequest(BaseModel):
    message: str
    history: list[dict] = Field(
        default=[],
        description="Conversation history as [{role, content}, ...]"
    )


class MessageResponse(BaseModel):
    reply: str
    is_recipe: bool


class RatingRequest(BaseModel):
    recipe_text: str
    rating: int = Field(..., ge=1, le=5)
    review: str = Field(default="", max_length=500)


class RatingResponse(BaseModel):
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/message", response_model=MessageResponse)
async def send_message(
    body: MessageRequest,
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Send a chat message. Past ratings are automatically injected
    into the system prompt before calling Ollama.
    """
    user_id = current_user["user_id"]

    system_message = build_system_prompt(
        query=body.message,
        user_id=user_id,
    )

    history = body.history + [{"role": "user", "content": body.message}]
    reply = call_ollama(system_message=system_message, history=history)

    return MessageResponse(
        reply=reply,
        is_recipe=is_recipe_response(reply),
    )


@router.post("/rate", response_model=RatingResponse)
async def rate_recipe(
    body: RatingRequest,
    current_user: dict = Depends(get_current_user_from_token),
):
    """
    Save a rating and review for a recipe into Qdrant.
    """
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
