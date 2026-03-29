import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RecipeListItem(BaseModel):
    """Recipe payload returned from Qdrant with id."""
    id: str
    payload: Dict[str, Any]


class PaginatedRecipesResponse(BaseModel):
    """Cursor-paginated recipes response."""

    items: List[RecipeListItem]
    limit: int
    next_offset: Optional[str] = None
    has_more: bool


class RecipeRetrieveRequest(BaseModel):
    """Input payload for dual-vector recipe retrieval."""

    prompt: str = Field(..., min_length=1)
    inventory: List[str] = Field(default_factory=list)
    top_k: int = Field(5, ge=1, le=50)
    fetch_k: int = Field(30, ge=1, le=200)


class RecipeRetrieveItem(BaseModel):
    """Scored recipe result from retrieval."""

    id: str
    recipe_id: Optional[str] = None
    title: str = ""
    final_score: float
    desc_score: float
    ing_score: float
    ingredient_coverage: float
    preference_01: float = 0.0
    payload: Dict[str, Any]


class RecipeRetrieveResponse(BaseModel):
    items: List[RecipeRetrieveItem]


def normalize_key(x: str) -> str:
    return str(x or "").lower().strip()


def _prose_from_desc_embedding_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    low = text.lower()
    marker = "description:"
    idx = low.find(marker)
    if idx < 0:
        return ""
    rest = text[idx + len(marker) :].lstrip()
    tail = " this recipe includes"
    c = rest.lower().find(tail)
    if c >= 0:
        rest = rest[:c]
    return rest.strip()


def display_description_from_payload(payload: Dict[str, Any], *, max_len: int = 900) -> str:
    for key in ("description", "summary", "desc"):
        v = payload.get(key)
        if isinstance(v, str):
            s = v.strip()
            if s:
                return s[:max_len]
    emb = payload.get("desc_embedding_text")
    if isinstance(emb, str) and emb.strip():
        inner = _prose_from_desc_embedding_text(emb)
        if inner:
            return inner[:max_len]
    return ""


def _dedupe_preserve_order(keys: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def keys_from_ing_embedding_text(text: str) -> List[str]:
    if not text or not isinstance(text, str):
        return []
    s = text.strip()
    low = s.lower()
    if low.startswith("ingredients:"):
        s = s[12:].lstrip()
    elif low.startswith("ingredients "):
        s = s[12:].lstrip()
    if not s:
        return []
    parts = re.split(r",\s*", s)
    keys = [normalize_key(p) for p in parts if p and str(p).strip()]
    return _dedupe_preserve_order(keys)


def ingredient_keys_from_payload(payload: Dict[str, Any]) -> List[str]:
    emb = payload.get("ing_embedding_text")
    if isinstance(emb, str) and emb.strip():
        keys = keys_from_ing_embedding_text(emb)
        if keys:
            return keys

    raw = payload.get("ingredients_normalized", payload.get("ingredients", []))
    if not isinstance(raw, list):
        return []
    return _dedupe_preserve_order(
        [normalize_key(x) for x in raw if str(x).strip()]
    )
