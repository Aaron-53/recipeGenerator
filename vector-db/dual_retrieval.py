#!/usr/bin/env python3
"""
Dual-vector retrieval: description + ingredient embeddings vs Qdrant (recipe_embeddings_dual).

Used by:
  - this file's CLI (`python dual_retrieval.py`)
  - FastAPI via `backend/dual_retrieval_bridge.py` (loads this module by path)

Config: QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION_NAME (optional .env in backend/).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_VEC_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _VEC_DIR.parent
_BACKEND = _PROJECT_ROOT / "backend"
if _BACKEND.is_dir() and str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
try:
    from schemas.recipe import ingredient_keys_from_payload as _ingredient_keys_for_payload
except ImportError:
    _ingredient_keys_for_payload = None  # type: ignore[misc, assignment]
import torch
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

try:
    from dotenv import load_dotenv

    _env = Path(__file__).resolve().parents[1] / "backend" / ".env"
    if _env.is_file():
        load_dotenv(_env)
except Exception:
    pass

QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION_NAME", "recipe_embeddings_dual")
MODEL_NAME = "BAAI/bge-base-en-v1.5"

W_DESC = 0.6
W_ING = 0.3
W_PREF = 0.1
W_COVERAGE_LEGACY = 0.0

device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer(MODEL_NAME, device=device)
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def _points(response: Any) -> List[Any]:
    return response.points if hasattr(response, "points") else response


def _ingredients_from_payload(payload: Dict[str, Any]) -> List[str]:
    if _ingredient_keys_for_payload is not None:
        return _ingredient_keys_for_payload(payload)
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


def _default_preference_fn(_payload: Dict[str, Any]) -> float:
    return 0.0


def _point_id_lookup_variants(raw: str) -> List[Any]:
    s = str(raw).strip()
    out: List[Any] = []
    if s.isdigit():
        out.append(int(s))
    out.append(s)
    seen: set[Any] = set()
    uniq: List[Any] = []
    for x in out:
        key = (type(x).__name__, str(x))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(x)
    return uniq


def get_payload_by_point_id(point_id: str) -> Optional[Dict[str, Any]]:
    print(f"[dual_retrieval] get_payload_by_point_id point_id={point_id!r}")
    last_err: Optional[Exception] = None
    for vid in _point_id_lookup_variants(point_id):
        try:
            res = client.retrieve(
                collection_name=COLLECTION_NAME,
                ids=[vid],
                with_payload=True,
                with_vectors=False,
            )
            pts = getattr(res, "points", None) or res
            if not pts:
                print(
                    f"[dual_retrieval] get_payload_by_point_id: empty result for variant={vid!r}"
                )
                continue
            p0 = pts[0]
            pl = getattr(p0, "payload", None) or {}
            print(
                f"[dual_retrieval] get_payload_by_point_id ok variant={vid!r} "
                f"title={pl.get('title', '')!r}"
            )
            return dict(pl) if pl else {}
        except Exception as exc:
            last_err = exc
            print(
                f"[dual_retrieval] get_payload_by_point_id variant={vid!r} "
                f"failed: {exc!r}"
            )
            continue
    print(f"[dual_retrieval] get_payload_by_point_id all variants failed last_err={last_err!r}")
    return None


def retrieve(
    prompt: str,
    inventory: List[str],
    top_k: int = 5,
    fetch_k: int = 30,
    preference_score_fn: Optional[Callable[[Dict[str, Any]], float]] = None,
) -> List[Dict[str, Any]]:
    pref_fn = preference_score_fn or _default_preference_fn
    print(
        f"[dual_retrieval] retrieve start prompt_len={len(prompt)} inventory_n={len(inventory)} "
        f"top_k={top_k} fetch_k={fetch_k} has_pref_fn={preference_score_fn is not None}"
    )
    desc_prompt = prompt.strip()

    desc_query = model.encode(
        desc_prompt, convert_to_numpy=True, normalize_embeddings=True
    ).tolist()
    ing_query_text = (
        "available ingredients: " + ", ".join(inventory)
        if inventory
        else "available ingredients: (none listed)"
    )
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
        pay = item["payload"]
        pref01 = float(pref_fn(pay))
        final_score = (
            W_DESC * item["desc_score"]
            + W_ING * item["ing_score"]
            + W_PREF * pref01
        )
        rid = pay.get("recipe_id")
        point_id_str = str(item["id"])
        global_rid = str(rid) if rid is not None else point_id_str
        print(
            f"[dual_retrieval] row point_id={point_id_str} recipe_id={global_rid!r} "
            f"desc={item['desc_score']:.4f} ing={item['ing_score']:.4f} "
            f"coverage={coverage:.4f} pref01={pref01:.4f} final={final_score:.4f}"
        )
        ranked.append(
            {
                "id": item["id"],
                "recipe_id": global_rid,
                "title": pay.get("title", ""),
                "final_score": final_score,
                "desc_score": item["desc_score"],
                "ing_score": item["ing_score"],
                "ingredient_coverage": coverage,
                "preference_01": pref01,
                "payload": pay,
            }
        )

    ranked.sort(key=lambda x: (x["desc_score"], x["final_score"]), reverse=True)
    out = ranked[:top_k]
    print(f"[dual_retrieval] retrieve done returning n={len(out)}")
    return out


def warmup_retrieval() -> None:
    client.scroll(
        collection_name=COLLECTION_NAME,
        limit=1,
        with_payload=False,
        with_vectors=False,
    )
    model.encode(
        "startup warmup", convert_to_numpy=True, normalize_embeddings=True
    )


if __name__ == "__main__":
    user_prompt = "I want something spicy and quick for dinner"
    user_inventory = ["onion", "garlic", "tomato", "chickpea", "rice"]

    results = retrieve(user_prompt, user_inventory, top_k=5, fetch_k=30)
    for i, r in enumerate(results, start=1):
        print(
            f"{i}. {r['title']} | score={r['final_score']:.4f} | recipe_id={r['recipe_id']}"
        )
