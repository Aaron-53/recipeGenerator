"""
Load `vector-db/dual_retrieval.py` by path (hyphenated folder is not a Python package name).

Exposes `retrieve_ranked_recipes` / `warmup_retrieval` for FastAPI using `RecipeRetrieveItem`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from schemas.recipe import RecipeRetrieveItem

_ROOT = Path(__file__).resolve().parent.parent
_VEC = _ROOT / "vector-db" / "dual_retrieval.py"

_spec = importlib.util.spec_from_file_location("dual_retrieval_vec", _VEC)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load dual retrieval from {_VEC}")

_dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dr)


def retrieve_ranked_recipes(
    prompt: str,
    inventory: list[str],
    top_k: int = 5,
    fetch_k: int = 30,
) -> list[RecipeRetrieveItem]:
    rows = _dr.retrieve(prompt, inventory, top_k, fetch_k)
    return [
        RecipeRetrieveItem(
            id=str(r["id"]),
            recipe_id=r.get("recipe_id"),
            title=r.get("title") or "",
            final_score=float(r["final_score"]),
            desc_score=float(r["desc_score"]),
            ing_score=float(r["ing_score"]),
            ingredient_coverage=float(r["ingredient_coverage"]),
            payload=r.get("payload") or {},
        )
        for r in rows
    ]


def warmup_retrieval() -> None:
    _dr.warmup_retrieval()
