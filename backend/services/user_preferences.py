from __future__ import annotations

from typing import Any, Dict, List, Optional

from bson import ObjectId
from configs.database import get_collection
from schemas.recipe import ingredient_keys_from_payload, normalize_key

PREF_MIN = -3
PREF_MAX = 10

LIKE_DELTA = 2
SELECT_DELTA = 1
DISLIKE_DELTA = -1
RATING_HIGH_DELTA = 2
RATING_LOW_DELTA = -1


def _rating_preference_delta(rating_value: int) -> float:
    rv = int(rating_value)
    if rv >= 4:
        return float(RATING_HIGH_DELTA)
    if rv <= 2:
        return float(RATING_LOW_DELTA)
    return 0.0


def _cap(val: float) -> float:
    return max(PREF_MIN, min(PREF_MAX, val))


def empty_preferences() -> Dict[str, Dict[str, float]]:
    return {"ingredients": {}, "tags": {}, "cuisine": {}}


async def get_user_preferences(user_id: str) -> Dict[str, Dict[str, float]]:
    coll = await get_collection("users")
    try:
        oid = ObjectId(user_id)
    except Exception as exc:
        print(f"[user_preferences] get_user_preferences invalid user_id={user_id!r} err={exc!r}")
        return empty_preferences()
    doc = await coll.find_one({"_id": oid})
    if not doc:
        print(f"[user_preferences] get_user_preferences: no user {user_id=}")
        return empty_preferences()
    raw = doc.get("preferences") or {}
    out = empty_preferences()
    for bucket in ("ingredients", "tags", "cuisine"):
        b = raw.get(bucket) or {}
        if isinstance(b, dict):
            out[bucket] = {normalize_key(k): float(v) for k, v in b.items() if k}
    print(
        f"[user_preferences] loaded prefs for user_id={user_id}: "
        f"ing_keys={len(out['ingredients'])} tag_keys={len(out['tags'])} "
        f"cuisine_keys={len(out['cuisine'])}"
    )
    return out


def _string_list_from_value(val: Any) -> List[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


def _dedupe_keys(keys: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def extract_tags_and_cuisines_from_payload(
    payload: Dict[str, Any],
) -> tuple[List[str], List[str]]:
    tag_keys: List[str] = []
    cuisine_keys: List[str] = []

    raw_tags = payload.get("tags")
    if isinstance(raw_tags, dict):
        for cat, val in raw_tags.items():
            cat_l = str(cat).lower().strip()
            for s in _string_list_from_value(val):
                if cat_l == "cuisine":
                    cuisine_keys.append(normalize_key(s))
                else:
                    tag_keys.append(normalize_key(s))
    elif isinstance(raw_tags, list):
        for x in raw_tags:
            if str(x).strip():
                tag_keys.append(normalize_key(x))
    elif isinstance(raw_tags, str) and raw_tags.strip():
        tag_keys.append(normalize_key(raw_tags))

    for top in ("cuisine", "cuisines"):
        raw_c = payload.get(top)
        if isinstance(raw_c, list):
            for x in raw_c:
                if str(x).strip():
                    cuisine_keys.append(normalize_key(x))
        elif isinstance(raw_c, str) and raw_c.strip():
            cuisine_keys.append(normalize_key(raw_c))

    return _dedupe_keys(tag_keys), _dedupe_keys(cuisine_keys)


def preference_score_01(prefs: Dict[str, Dict[str, float]], payload: Dict[str, Any]) -> float:
    ing_list = ingredient_keys_from_payload(payload)

    tags, cuisines = extract_tags_and_cuisines_from_payload(payload)

    pi = prefs.get("ingredients") or {}
    pt = prefs.get("tags") or {}
    pc = prefs.get("cuisine") or {}

    total = 0.0
    for k in ing_list:
        total += float(pi.get(k, 0.0))
    for k in tags:
        total += float(pt.get(k, 0.0))
    for k in cuisines:
        total += float(pc.get(k, 0.0))

    denom = 20.0 + 1e-9
    norm = max(-1.0, min(1.0, total / denom))
    print(
        f"[user_preferences] preference_score_01 total={total:.4f} norm={norm:.4f} "
        f"ing_hits={len(ing_list)} tags={len(tags)} cuisines={len(cuisines)}"
    )
    return norm


def _tag_keys_from_payload(payload: Dict[str, Any]) -> List[str]:
    t, _ = extract_tags_and_cuisines_from_payload(payload)
    return t


def _cuisine_keys_from_payload(payload: Dict[str, Any]) -> List[str]:
    _, c = extract_tags_and_cuisines_from_payload(payload)
    return c


async def apply_feedback(
    user_id: str,
    action: str,
    payload: Dict[str, Any],
    rating_value: Optional[int] = None,
    point_id: Optional[str] = None,
) -> Dict[str, Any]:
    print(
        f"[user_preferences] apply_feedback user_id={user_id!r} action={action!r} "
        f"rating_value={rating_value}"
    )
    ing_keys = ingredient_keys_from_payload(payload)
    tag_keys = _tag_keys_from_payload(payload)
    cuisine_keys = _cuisine_keys_from_payload(payload)
    print(
        f"[user_preferences] keys ing={ing_keys[:12]!r} (n={len(ing_keys)}) "
        f"tags={tag_keys[:16]!r} (n={len(tag_keys)}) "
        f"cuisine={cuisine_keys!r}"
    )

    coll = await get_collection("users")
    try:
        oid = ObjectId(user_id)
    except Exception as exc:
        print(f"[user_preferences] apply_feedback bad user_id={user_id!r} {exc!r}")
        return {"ok": False, "error": "invalid_user_id"}
    prefs = await get_user_preferences(user_id)

    def add_to_bucket(bucket: str, keys: List[str], delta: float) -> None:
        if not keys:
            return
        b = prefs.setdefault(bucket, {})
        for k in keys:
            b[k] = _cap(float(b.get(k, 0.0)) + delta)

    if action == "like":
        add_to_bucket("ingredients", ing_keys, LIKE_DELTA)
        add_to_bucket("tags", tag_keys, LIKE_DELTA)
        add_to_bucket("cuisine", cuisine_keys, LIKE_DELTA)
    elif action == "dislike":
        add_to_bucket("ingredients", ing_keys, DISLIKE_DELTA)
        add_to_bucket("tags", tag_keys, DISLIKE_DELTA)
        add_to_bucket("cuisine", cuisine_keys, DISLIKE_DELTA)
    elif action == "selected":
        add_to_bucket("ingredients", ing_keys, SELECT_DELTA)
        add_to_bucket("tags", tag_keys, SELECT_DELTA)
        add_to_bucket("cuisine", cuisine_keys, SELECT_DELTA)
    elif action == "rating" and rating_value is not None:
        rv = int(rating_value)
        pid = str(point_id).strip() if point_id else ""
        if pid:
            doc = await coll.find_one({"_id": oid}, {"recipe_point_ratings": 1}) or {}
            rmap: Dict[str, int] = {}
            raw = doc.get("recipe_point_ratings")
            if isinstance(raw, dict):
                for k, v in raw.items():
                    try:
                        rmap[str(k)] = int(v)
                    except (TypeError, ValueError):
                        continue
            prev = rmap.get(pid)
            old_d = _rating_preference_delta(prev) if prev is not None else 0.0
            net = _rating_preference_delta(rv) - old_d
            add_to_bucket("ingredients", ing_keys, net)
            add_to_bucket("tags", tag_keys, net)
            add_to_bucket("cuisine", cuisine_keys, net)
            rmap[pid] = rv
            await coll.update_one(
                {"_id": oid},
                {"$set": {"preferences": prefs, "recipe_point_ratings": rmap}},
            )
            print(f"[user_preferences] apply_feedback rating replace point_id={pid!r} net_delta={net}")
            return {"ok": True, "preferences": prefs}
        if rv >= 4:
            add_to_bucket("ingredients", ing_keys, RATING_HIGH_DELTA)
            add_to_bucket("tags", tag_keys, RATING_HIGH_DELTA)
            add_to_bucket("cuisine", cuisine_keys, RATING_HIGH_DELTA)
        elif rv <= 2:
            add_to_bucket("ingredients", ing_keys, RATING_LOW_DELTA)
            add_to_bucket("tags", tag_keys, RATING_LOW_DELTA)
            add_to_bucket("cuisine", cuisine_keys, RATING_LOW_DELTA)
    else:
        print(f"[user_preferences] apply_feedback: unknown action or missing rating")

    await coll.update_one(
        {"_id": oid},
        {"$set": {"preferences": prefs}},
    )
    print(f"[user_preferences] apply_feedback saved preferences for user_id={user_id}")
    return {"ok": True, "preferences": prefs}
