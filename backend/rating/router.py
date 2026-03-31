from __future__ import annotations

import asyncio
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from configs.database import get_collection
from dual_retrieval_bridge import get_payload_by_point_id, retrieve_three_diverse_recipes
from schemas.recipe import display_description_from_payload
from rating.chat_integration import (
    WRAPUP_SESSION_SYSTEM_SUFFIX,
    WRAPUP_USER_FACING_REPLY,
    build_recipe_tool_system_prompt,
    call_ollama,
    compose_retrieval_query,
    is_recipe_response,
    is_wrapup_rating_turn,
    supplement_rating_trigger_if_wrapup,
)
from rating.qdrant_storage import save_rating
from services.user_preferences import apply_feedback, get_user_preferences
from schemas.chat_session import RankedSuggestionEntry
from utils.auth_utils import get_current_user_from_token

router = APIRouter(prefix="/chat", tags=["chat"])


def _steps_from_payload_field(raw_steps: object) -> list[str]:
    if isinstance(raw_steps, str) and raw_steps.strip():
        return [raw_steps.strip()]
    if isinstance(raw_steps, list):
        return [str(x).strip() for x in raw_steps if str(x).strip()][:48]
    if isinstance(raw_steps, dict) and raw_steps:
        def _sort_key(k: object) -> tuple[int, str]:
            ks = str(k).strip()
            try:
                return (int(ks), ks)
            except ValueError:
                return (10**9, ks)

        keys = sorted(raw_steps.keys(), key=_sort_key)
        out = [
            str(raw_steps[k]).strip()
            for k in keys
            if str(raw_steps.get(k, "")).strip()
        ]
        return out[:48]
    return []


def _recipe_card_fields_from_payload(pay: dict) -> tuple[list[str], list[str], str]:
    raw_ing = pay.get("ingredients_normalized") or pay.get("ingredients") or []
    if isinstance(raw_ing, list):
        ingredients = [str(x) for x in raw_ing if str(x).strip()][:48]
    else:
        ingredients = []
    raw_steps = pay.get("steps") or pay.get("instructions") or pay.get("directions") or []
    steps = _steps_from_payload_field(raw_steps)
    tips = str(pay.get("tips") or "").strip()
    if not tips:
        tips = display_description_from_payload(pay, max_len=900)
    return ingredients, steps, tips[:900]


class MessageRequest(BaseModel):
    message: str
    history: list[dict] = Field(default_factory=list)
    inventory: list[str] = Field(default_factory=list)
    # Client sends which ranked option is active (pickRef); history.point_id can lag as #1.
    selected_point_id: Optional[str] = None
    selected_recipe_id: Optional[str] = None


class MessageResponse(BaseModel):
    reply: str
    is_recipe: bool
    rating_saved: bool = False
    trigger_rating_ui: bool = False
    inventory_used: Optional[list[str]] = Field(default=None)
    ranked_recipe_ids: list[str] = Field(default_factory=list)
    ranked_point_ids: list[str] = Field(default_factory=list)
    ranked_suggestions: list[RankedSuggestionEntry] = Field(default_factory=list)


class RatingRequest(BaseModel):
    recipe_text: str
    rating: int = Field(..., ge=1, le=5)
    review: str = Field(default="", max_length=500)
    point_id: Optional[str] = Field(default=None)


class RatingResponse(BaseModel):
    message: str


class FeedbackRequest(BaseModel):
    action: Literal["like", "dislike", "selected", "rating"]
    point_id: str = Field(..., min_length=1)
    recipe_id: Optional[str] = Field(default=None)
    rating_value: Optional[int] = Field(default=None, ge=1, le=5)


class FeedbackResponse(BaseModel):
    ok: bool
    detail: str = ""


class MetricsRequest(BaseModel):
    event: str = Field(..., min_length=1, max_length=120)
    recipe_id: str = Field(..., min_length=1)
    extra: dict[str, Any] = Field(default_factory=dict)


class MetricsResponse(BaseModel):
    ok: bool = True


def _last_ranked_selection_from_prior(prior: list[dict]) -> tuple[str, str] | None:
    for m in reversed(prior or []):
        if not isinstance(m, dict) or m.get("role") != "assistant":
            continue
        pid = str(m.get("point_id") or "").strip()
        sug = m.get("ranked_suggestions")
        if not pid or not isinstance(sug, list) or len(sug) == 0:
            continue
        title = ""
        for s in sug:
            if isinstance(s, dict) and str(s.get("point_id") or "").strip() == pid:
                title = str(s.get("title") or "").strip()
                break
        return (pid, title)
    return None


def _database_anchor_block(point_id: str, payload: dict) -> str:
    ing, _, _ = _recipe_card_fields_from_payload(payload)
    name = (payload.get("title") or "").strip() or "(untitled)"
    preview = ", ".join(ing[:16]) if ing else "(ingredients in database)"
    return (
        "\n\n=== DATABASE ANCHOR (mandatory) ===\n"
        f"Selected recipe point_id={point_id!r}; canonical title={name!r}.\n"
        f"Ingredient preview: {preview}\n"
        "Any recipe JSON you output for this thread must describe THIS dish — not the first "
        "row of a new search_recipe_database result unless that row is this same point_id.\n"
    )


def _user_wants_fresh_search(message: str) -> bool:
    """User explicitly wants new options / a different meal — allow search_recipe_database again."""
    t = (message or "").lower()
    phrases = (
        "different dish",
        "different recipe",
        "something else",
        "something different",
        "another recipe",
        "other recipe",
        "other dishes",
        "other options",
        "new search",
        "new ideas",
        "three new",
        "more options",
        "show me other",
        "pick again",
        "choose again",
        "start over",
        "not this",
        "dont want this",
        "don't want this",
        "another cuisine",
        "completely different",
    )
    return any(p in t for p in phrases)


def _title_for_point_in_prior(prior: list[dict], pid: str) -> str:
    for m in reversed(prior or []):
        if m.get("role") != "assistant":
            continue
        sug = m.get("ranked_suggestions")
        if not isinstance(sug, list):
            continue
        for s in sug:
            if (
                isinstance(s, dict)
                and str(s.get("point_id") or "").strip() == pid
            ):
                return str(s.get("title") or "").strip()
    return ""


async def _selection_system_suffix(
    prior: list[dict],
    selected_point_id: Optional[str] = None,
    selected_recipe_id: Optional[str] = None,
) -> str:
    """Prefer explicit client selection so we never anchor to ranked option #1 by mistake."""
    _ = selected_recipe_id  # optional; anchor uses point_id + payload
    explicit = (selected_point_id or "").strip()
    if explicit:
        pid = explicit
        title = _title_for_point_in_prior(prior, pid)
    else:
        got = _last_ranked_selection_from_prior(prior)
        if not got:
            return ""
        pid, title = got

    pay = await asyncio.to_thread(get_payload_by_point_id, pid)
    if pay and not title:
        title = str(pay.get("title") or "").strip()
    if not title:
        title = "(untitled)"

    out = (
        "\n\n=== USER SELECTION (from client) ===\n"
        f"The user chose **this** database recipe (not necessarily the first ranked row): "
        f"point_id={pid!r}, title={title!r}.\n"
        "Their latest message (e.g. allergy, swap, or tweak) applies to **THIS dish only**. "
        "Do **not** adapt or rename a different option from the ranked list (e.g. do not jump to row #1).\n"
        "Your JSON **recipe_name** and ingredients/steps must describe **this** title / dish family, "
        "adapted as requested — never copy another option’s dish name.\n"
        "\n"
        "=== SELECTED DISH — FOLLOW-UPS (mandatory) ===\n"
        "The user **already picked** this option in the app. They are not browsing the list anymore.\n"
        "- If they say they **don’t have**, **ran out of**, **no X**, **substitute**, **swap**, **allergy**, "
        "**less spicy**, scale, timing, or any **tweak to this same dish**: respond with **one** JSON recipe "
        "(adapted). **Do not** call `search_recipe_database`. **Do not** write “1. … 2. … 3. …”, "
        "“updated options”, “here are three…”, or “Select your choice” — that was for the **first** search only.\n"
        "- **Only** if they clearly ask for **other** recipes, **new** ideas, or a **different** meal "
        "(e.g. “show me different dishes”, “something else entirely”) may you run a **new** database search.\n"
    )
    if pay:
        out += _database_anchor_block(pid, pay)
    return out


async def get_user_inventory_names(user_id: str) -> list[str]:
    coll = await get_collection("inventory")
    cursor = coll.find({"user_id": user_id})
    items = await cursor.to_list(length=500)
    return [str(i["name"]).strip() for i in items if i.get("name")]


def merge_inventory_for_retrieval(
    client_names: list[str], server_names: list[str]
) -> list[str]:
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
    print(f"[chat/message] user_id={user_id!r} msg_len={len(body.message)}")
    prior = body.history
    msg = body.message

    server_inv = await get_user_inventory_names(user_id)
    inventory = merge_inventory_for_retrieval(body.inventory, server_inv)

    prefs = await get_user_preferences(user_id)
    print(f"[chat/message] recipe mode inventory_n={len(inventory)} prefs_buckets loaded")

    def run_recipe_search(query: str):
        return retrieve_three_diverse_recipes(query, inventory, prefs)

    default_search_query = compose_retrieval_query(msg, prior)
    system_message = build_recipe_tool_system_prompt(body.message, user_id, inventory)
    wrapup_turn = is_wrapup_rating_turn(msg, prior)
    if wrapup_turn:
        sc = system_message.get("content") or ""
        system_message = {**system_message, "content": sc + WRAPUP_SESSION_SYSTEM_SUFFIX}
    sel_suffix = await _selection_system_suffix(
        prior,
        selected_point_id=body.selected_point_id,
        selected_recipe_id=body.selected_recipe_id,
    )
    if sel_suffix:
        sc = system_message.get("content") or ""
        system_message = {**system_message, "content": sc + sel_suffix}
    # After a tap selection, block DB search unless they explicitly want new options (prevents “1.2.3. pick again”).
    lock_search_for_selection_anchor = bool(sel_suffix) and not _user_wants_fresh_search(msg)
    full_history = prior + [{"role": "user", "content": msg}]
    reply, saved, trigger, items = await asyncio.to_thread(
        call_ollama,
        system_message,
        full_history,
        user_id,
        run_recipe_search=run_recipe_search,
        default_search_query=default_search_query,
        wrapup_after_recipe=wrapup_turn,
        lock_search_for_selection_anchor=lock_search_for_selection_anchor,
    )
    trigger = supplement_rating_trigger_if_wrapup(msg, prior, trigger)
    if wrapup_turn:
        trigger = True
        reply = WRAPUP_USER_FACING_REPLY
    ranked_recipe_ids: list[str] = []
    ranked_point_ids: list[str] = []
    for it in items:
        pid = str(it.id)
        ranked_point_ids.append(pid)
        rid = it.recipe_id
        ranked_recipe_ids.append(str(rid) if rid is not None else pid)
    print(
        f"[chat/message] ranked (from tool) n={len(items)} recipe_ids={ranked_recipe_ids!r} "
        f"point_ids={ranked_point_ids!r}"
    )
    ranked_suggestions: list[RankedSuggestionEntry] = []
    for it in items[:3]:
        pay = it.payload or {}
        ing, st, _tip = _recipe_card_fields_from_payload(pay)
        ranked_suggestions.append(
            RankedSuggestionEntry(
                title=(it.title or pay.get("title") or "").strip() or "(untitled)",
                recipe_id=str(it.recipe_id) if it.recipe_id is not None else str(it.id),
                point_id=str(it.id),
                ingredients=ing,
                steps=st,
                tips="",
            )
        )
    print(f"[chat/message] ranked_suggestions n={len(ranked_suggestions)} titles={[x.title for x in ranked_suggestions]!r}")
    print(
        f"[chat/message] ollama done is_recipe={is_recipe_response(reply)} "
        f"rating_saved={saved} trigger_rating_ui={trigger}"
    )
    return MessageResponse(
        reply=reply,
        is_recipe=is_recipe_response(reply),
        rating_saved=saved,
        trigger_rating_ui=trigger,
        inventory_used=inventory,
        ranked_recipe_ids=ranked_recipe_ids,
        ranked_point_ids=ranked_point_ids,
        ranked_suggestions=ranked_suggestions,
    )


@router.post("/rate", response_model=RatingResponse)
async def rate_recipe(
    body: RatingRequest,
    current_user: dict = Depends(get_current_user_from_token),
):
    user_id = current_user["user_id"]
    print(f"[chat/rate] user_id={user_id!r} rating={body.rating}")

    save_rating(
        recipe_text=body.recipe_text,
        rating=body.rating,
        review=body.review,
        user_id=user_id,
        point_id=body.point_id,
    )

    return RatingResponse(
        message=f"Rating {body.rating}/5 saved. I'll use this next time!"
    )


@router.post("/feedback", response_model=FeedbackResponse)
async def post_feedback(
    body: FeedbackRequest,
    current_user: dict = Depends(get_current_user_from_token),
):
    user_id = current_user["user_id"]
    print(
        f"[chat/feedback] user_id={user_id!r} action={body.action!r} "
        f"point_id={body.point_id!r} recipe_id={body.recipe_id!r} rating_value={body.rating_value}"
    )
    if body.action == "rating" and body.rating_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rating_value required for action=rating",
        )

    payload = await asyncio.to_thread(get_payload_by_point_id, body.point_id)
    if not payload:
        print("[chat/feedback] payload missing for point_id")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown retrieval point_id",
        )
    pl_rid = payload.get("recipe_id")
    if body.recipe_id and pl_rid is not None and str(pl_rid) != str(body.recipe_id):
        print(
            f"[chat/feedback] recipe_id mismatch client={body.recipe_id!r} payload={pl_rid!r} "
            "(continuing with payload)"
        )

    result = await apply_feedback(
        user_id,
        body.action,
        payload,
        rating_value=body.rating_value,
        point_id=body.point_id,
    )
    if result.get("ok") is False:
        return FeedbackResponse(ok=False, detail=str(result.get("error", "failed")))
    return FeedbackResponse(ok=True, detail="preferences_updated")


@router.post("/metrics", response_model=MetricsResponse)
async def post_metrics(
    body: MetricsRequest,
    current_user: dict = Depends(get_current_user_from_token),
):
    user_id = current_user["user_id"]
    print(
        f"[chat/metrics] user_id={user_id!r} event={body.event!r} "
        f"recipe_id={body.recipe_id!r} extra_keys={list(body.extra.keys())}"
    )
    return MetricsResponse(ok=True)
