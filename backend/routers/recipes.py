from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from configs import settings
from configs.qdrant import get_qdrant_client
from schemas.recipe import (
    PaginatedRecipesResponse,
    RecipeListItem,
    RecipeRetrieveRequest,
    RecipeRetrieveResponse,
)
from dual_retrieval_bridge import retrieve_ranked_recipes, warmup_retrieval

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _parse_offset(offset: Optional[str]) -> Any:
    if offset is None or offset == "":
        return None
    if offset.isdigit():
        return int(offset)
    return offset


def _serialize_offset(offset: Any) -> Optional[str]:
    if offset is None:
        return None
    return str(offset)


def initialize_recipe_retrieval() -> None:
    warmup_retrieval()


@router.get("", response_model=PaginatedRecipesResponse)
async def list_recipes(
    limit: int = Query(10, ge=1, le=200),
    offset: Optional[str] = Query(None),
):
    try:
        client = get_qdrant_client()
        points, next_offset = client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            limit=limit,
            offset=_parse_offset(offset),
            with_payload=True,
            with_vectors=False,
        )

        items = [
            RecipeListItem(id=str(point.id), payload=point.payload or {})
            for point in points
        ]

        return PaginatedRecipesResponse(
            items=items,
            limit=limit,
            next_offset=_serialize_offset(next_offset),
            has_more=next_offset is not None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recipes: {exc}")


@router.post("/retrieve", response_model=RecipeRetrieveResponse)
async def retrieve_recipes(body: RecipeRetrieveRequest):
    try:
        ranked = retrieve_ranked_recipes(
            body.prompt, body.inventory, top_k=body.top_k, fetch_k=body.fetch_k
        )
        return RecipeRetrieveResponse(items=ranked)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve recipes: {exc}"
        )
