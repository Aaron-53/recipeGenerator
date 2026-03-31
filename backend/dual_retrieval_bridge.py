from __future__ import annotations

import importlib.util
from pathlib import Path

from schemas.recipe import RecipeRetrieveItem
from services.user_preferences import empty_preferences, preference_score_01

_ROOT = Path(__file__).resolve().parent.parent
_VEC = _ROOT / "vector-db" / "dual_retrieval.py"

_spec = importlib.util.spec_from_file_location("dual_retrieval_vec", _VEC)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load dual retrieval from {_VEC}")

_dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dr)


def _dedupe_key(it: RecipeRetrieveItem) -> str:
    pay = it.payload or {}
    rid = it.recipe_id if it.recipe_id is not None else pay.get("recipe_id")
    if rid is not None and str(rid).strip():
        return f"rid:{str(rid).strip()}"
    title = (it.title or pay.get("title") or "").strip().lower()
    if title:
        return f"title:{title}"
    return f"pid:{it.id}"


def _normalized_title_dedupe_key(it: RecipeRetrieveItem) -> str:
    """Same user-visible title → one option (different point_ids may share a name)."""
    pay = it.payload or {}
    t = (it.title or pay.get("title") or "").strip().lower()
    if not t:
        return f"pid:{it.id}"
    return f"title:{t}"


def _dedupe_by_normalized_title(
    items: list[RecipeRetrieveItem],
) -> list[RecipeRetrieveItem]:
    seen: set[str] = set()
    out: list[RecipeRetrieveItem] = []
    for it in items:
        k = _normalized_title_dedupe_key(it)
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def _make_pref_fn(prefs: dict | None):
    base = prefs if prefs is not None else empty_preferences()

    def fn(payload: dict) -> float:
        return preference_score_01(base, payload)

    return fn


RETRIEVAL_MAX_OPTIONS = 3
RETRIEVAL_TOPK_SINGLE_PASS = 28
EXTRA_MATCH_MIN_DESC_VS_BEST = 0.97
EXTRA_MATCH_MAX_DESC_ABS_GAP = 0.035


def _dedupe_preserve_score_order(items: list[RecipeRetrieveItem]) -> list[RecipeRetrieveItem]:
    seen: set[str] = set()
    out: list[RecipeRetrieveItem] = []
    for it in items:
        k = _dedupe_key(it)
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def _relevance_trim(items: list[RecipeRetrieveItem], limit: int) -> list[RecipeRetrieveItem]:
    deduped = _dedupe_preserve_score_order(items)
    deduped = _dedupe_by_normalized_title(deduped)
    if not deduped:
        return []
    best_desc = float(deduped[0].desc_score)
    floor_ratio = best_desc * EXTRA_MATCH_MIN_DESC_VS_BEST
    floor_abs = best_desc - EXTRA_MATCH_MAX_DESC_ABS_GAP
    floor = max(floor_ratio, floor_abs)
    out = [deduped[0]]
    for it in deduped[1:]:
        if len(out) >= limit:
            break
        if float(it.desc_score) >= floor:
            out.append(it)
    return out


def retrieve_ranked_recipes(
    prompt: str,
    inventory: list[str],
    top_k: int = 5,
    fetch_k: int = 30,
    prefs: dict | None = None,
) -> list[RecipeRetrieveItem]:
    print(
        f"[dual_retrieval_bridge] retrieve_ranked_recipes top_k={top_k} fetch_k={fetch_k} "
        f"has_prefs={prefs is not None}"
    )
    pref_fn = _make_pref_fn(prefs)
    rows = _dr.retrieve(prompt, inventory, top_k, fetch_k, preference_score_fn=pref_fn)
    return [
        RecipeRetrieveItem(
            id=str(r["id"]),
            recipe_id=str(r["recipe_id"]) if r.get("recipe_id") is not None else None,
            title=r.get("title") or "",
            final_score=float(r["final_score"]),
            desc_score=float(r["desc_score"]),
            ing_score=float(r["ing_score"]),
            ingredient_coverage=float(r["ingredient_coverage"]),
            preference_01=float(r.get("preference_01") or 0.0),
            payload=r.get("payload") or {},
        )
        for r in rows
    ]


def retrieve_three_diverse_recipes(
    prompt: str,
    inventory: list[str],
    prefs: dict | None = None,
    *,
    top_k_each: int = 10,
    fetch_k: int = 30,
) -> list[RecipeRetrieveItem]:
    base = (prompt or "").strip()
    if not base:
        return []

    top_k = max(top_k_each, RETRIEVAL_TOPK_SINGLE_PASS)
    rows = retrieve_ranked_recipes(
        base, inventory, top_k=top_k, fetch_k=fetch_k, prefs=prefs
    )
    rows.sort(key=lambda it: (-it.desc_score, -it.final_score))
    trimmed = _relevance_trim(rows, RETRIEVAL_MAX_OPTIONS)
    if trimmed:
        print(
            f"[dual_retrieval_bridge] retrieve ranked n={len(rows)} "
            f"after_desc_relevance n={len(trimmed)} best_desc={trimmed[0].desc_score:.4f}"
        )
    else:
        print(
            f"[dual_retrieval_bridge] retrieve ranked n={len(rows)} after_desc_relevance n=0"
        )
    return trimmed


def get_payload_by_point_id(point_id: str) -> dict | None:
    print(f"[dual_retrieval_bridge] get_payload_by_point_id point_id={point_id!r}")
    return _dr.get_payload_by_point_id(point_id)


def warmup_retrieval() -> None:
    _dr.warmup_retrieval()
