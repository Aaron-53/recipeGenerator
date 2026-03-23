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
    payload: Dict[str, Any]


class RecipeRetrieveResponse(BaseModel):
    """Response wrapper for retrieval endpoint."""

    items: List[RecipeRetrieveItem]
