#!/usr/bin/env python3
"""Minimal dual-vector retrieval for recipe recommendations."""

from typing import Any, Dict, List

import torch
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer


QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "recipe_embeddings_dual"
MODEL_NAME = "BAAI/bge-base-en-v1.5"

# Same scoring architecture discussed earlier
W_DESC = 0.55
W_ING = 0.25
W_COVERAGE = 0.20


device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer(MODEL_NAME, device=device)
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


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


def retrieve(
    prompt: str, inventory: List[str], top_k: int = 5, fetch_k: int = 30
) -> List[Dict[str, Any]]:
    desc_query = model.encode(
        prompt, convert_to_numpy=True, normalize_embeddings=True
    ).tolist()
    ing_query_text = "available ingredients: " + ", ".join(inventory)
    ing_query = model.encode(
        ing_query_text, convert_to_numpy=True, normalize_embeddings=True
    ).tolist()

    desc_res = client.query_points(
        collection_name=COLLECTION_NAME,
        query=desc_query,
        using="desc_vector",
        limit=fetch_k,
        with_payload=True,
    )
    ing_res = client.query_points(
        collection_name=COLLECTION_NAME,
        query=ing_query,
        using="ing_vector",
        limit=fetch_k,
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

    ranked: List[Dict[str, Any]] = []
    for item in merged.values():
        recipe_ings = _ingredients_from_payload(item["payload"])
        coverage = _coverage(inventory, recipe_ings)
        final_score = (
            W_DESC * item["desc_score"]
            + W_ING * item["ing_score"]
            + W_COVERAGE * coverage
        )
        ranked.append(
            {
                "id": item["id"],
                "recipe_id": item["payload"].get("recipe_id"),
                "title": item["payload"].get("title", ""),
                "final_score": final_score,
                "desc_score": item["desc_score"],
                "ing_score": item["ing_score"],
                "ingredient_coverage": coverage,
                "payload": item["payload"],
            }
        )

    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    return ranked[:top_k]


if __name__ == "__main__":
    user_prompt = "I want something spicy and quick for dinner"
    user_inventory = ["onion", "garlic", "tomato", "chickpea", "rice"]

    results = retrieve(user_prompt, user_inventory, top_k=5, fetch_k=30)
    for i, r in enumerate(results, start=1):
        print(
            f"{i}. {r['title']} | score={r['final_score']:.4f} | recipe_id={r['recipe_id']}"
        )
