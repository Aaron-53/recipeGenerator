from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from sentence_transformers import SentenceTransformer
import torch

from configs.qdrant import QDRANT_COLLECTION_NAME, get_qdrant_client
from schemas.recipe import (
    PaginatedRecipesResponse,
    RecipeListItem,
    RecipeRetrieveRequest,
    RecipeRetrieveResponse,
    RecipeRetrieveItem,
)

router = APIRouter(prefix="/recipes", tags=["recipes"])

MODEL_NAME = "BAAI/bge-base-en-v1.5"
W_DESC = 0.55
W_ING = 0.25
W_COVERAGE = 0.20


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return SentenceTransformer(MODEL_NAME, device=device)


def _points(response: Any) -> List[Any]:
    return response.points if hasattr(response, "points") else response


def _ingredients_from_payload(payload: Dict[str, Any]) -> List[str]:
    value = payload.get("ingredients_normalized", payload.get("ingredients", []))
    if isinstance(value, list):
        return [str(x).strip().lower() for x in value if str(x).strip()]
    return []


def _coverage(user_inventory: List[str], recipe_ingredients: List[str]) -> float:
    if not recipe_ingredients:
        return 0.0
    inv = {x.strip().lower() for x in user_inventory if x and str(x).strip()}
    matched = sum(1 for ing in recipe_ingredients if ing in inv)
    return matched / len(recipe_ingredients)


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
    """Warm up retrieval dependencies during server startup."""
    model = _get_model()
    client = get_qdrant_client()

    # Avoid strict collection-config parsing on startup; a tiny scroll validates
    # connectivity and collection accessibility for actual retrieval endpoints.
    client.scroll(
        collection_name=QDRANT_COLLECTION_NAME,
        limit=1,
        with_payload=False,
        with_vectors=False,
    )

    # Touch encode once to avoid first-request latency spikes.
    model.encode("startup warmup", convert_to_numpy=True, normalize_embeddings=True)


@router.get("", response_model=PaginatedRecipesResponse)
async def list_recipes(
    limit: int = Query(10, ge=1, le=100),
    offset: Optional[str] = Query(None, description="Cursor from previous response"),
):
    """List recipes from Qdrant with cursor pagination."""
    try:
        client = get_qdrant_client()
        points, next_offset = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
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
    """Retrieve recipes using prompt-description and inventory-ingredients matching."""
    try:
        model = _get_model()
        client = get_qdrant_client()

        desc_query = model.encode(
            body.prompt, convert_to_numpy=True, normalize_embeddings=True
        ).tolist()
        ing_query_text = "available ingredients: " + ", ".join(body.inventory)
        ing_query = model.encode(
            ing_query_text, convert_to_numpy=True, normalize_embeddings=True
        ).tolist()

        desc_res = client.query_points(
            collection_name=QDRANT_COLLECTION_NAME,
            query=desc_query,
            using="desc_vector",
            limit=body.fetch_k,
            with_payload=True,
        )
        ing_res = client.query_points(
            collection_name=QDRANT_COLLECTION_NAME,
            query=ing_query,
            using="ing_vector",
            limit=body.fetch_k,
            with_payload=True,
        )

        merged: Dict[str, Dict[str, Any]] = {}

        for p in _points(desc_res):
            key = str(p.id)
            merged[key] = {
                "id": p.id,
                "payload": p.payload or {},
                "desc_score": float(p.score),
                "ing_score": 0.0,
            }

        for p in _points(ing_res):
            key = str(p.id)
            if key not in merged:
                merged[key] = {
                    "id": p.id,
                    "payload": p.payload or {},
                    "desc_score": 0.0,
                    "ing_score": float(p.score),
                }
            else:
                merged[key]["ing_score"] = float(p.score)

        ranked: List[RecipeRetrieveItem] = []
        for item in merged.values():
            recipe_ings = _ingredients_from_payload(item["payload"])
            coverage = _coverage(body.inventory, recipe_ings)
            final_score = (
                W_DESC * item["desc_score"]
                + W_ING * item["ing_score"]
                + W_COVERAGE * coverage
            )

            ranked.append(
                RecipeRetrieveItem(
                    id=str(item["id"]),
                    recipe_id=item["payload"].get("recipe_id"),
                    title=item["payload"].get("title", ""),
                    final_score=final_score,
                    desc_score=item["desc_score"],
                    ing_score=item["ing_score"],
                    ingredient_coverage=coverage,
                    payload=item["payload"],
                )
            )

        ranked.sort(key=lambda x: x.final_score, reverse=True)
        return RecipeRetrieveResponse(items=ranked[: body.top_k])
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve recipes: {exc}"
        )
