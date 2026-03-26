"""LLM-based parser for freeform inventory input."""

from __future__ import annotations

import json
import re
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b"

CONVERSION_MAP = {
    "teaspoon": ("teaspoon", 1),
    "tablespoon": ("tablespoon", 1),
    "cup": ("cup", 1),
    "ounce": ("g", 30),
    "pound": ("g", 500),
    "g": ("g", 1),
    "kg": ("kg", 1),
    "fluid_ounce": ("tablespoon", 2),
    "pint": ("cup", 2),
    "quart": ("cup", 4),
    "gallon": ("l", 4),
    "ml": ("ml", 1),
    "l": ("l", 1),
    "dash": ("ml", 0.5),
    "drop": ("drop", 1),
    "pinch": ("pinch", 1),
    "can": ("tin", 1),
    "packet": ("packet", 1),
    "bag": ("bag", 1),
    "box": ("box", 1),
    "jar": ("jar", 1),
    "bottle": ("bottle", 1),
    "sachet": ("sachet", 1),
    "tin": ("tin", 1),
    "carton": ("carton", 1),
    "piece": ("piece", 1),
    "slice": ("slice", 1),
    "clove": ("clove", 1),
    "bunch": ("bunch", 1),
    "stalk": ("stalk", 1),
    "sprig": ("sprig", 1),
    "leaf": ("leaf", 1),
    "cube": ("cube", 1),
    "dozen": ("dozen", 1),
    "handful": ("handful", 1),
    "scoop": ("scoop", 1),
    "serving": ("serving", 1),
}


def _format_inventory_context(inventory: list[dict]) -> str:
    """Format current inventory for LLM context."""
    if not inventory:
        return "Current inventory is empty."
    lines = ["Current inventory:"]
    for item in inventory:
        name = item.get("name", "unknown")
        qty = item.get("quantity", 0)
        unit = item.get("unit", "")
        lines.append(f"  - {name}: {qty} {unit}")
    return "\n".join(lines)


def _normalize_unit(unit: str | None) -> str | None:
    """Normalize unit using CONVERSION_MAP."""
    if not unit:
        return None
    normalized_unit = unit.lower().strip()
    if normalized_unit in CONVERSION_MAP:
        return CONVERSION_MAP[normalized_unit][0]
    return normalized_unit


INVENTORY_PARSE_SYSTEM_PROMPT_TEMPLATE = """You convert inventory update text into strict JSON.

This is the current inventory:
```
{inventory_context}
```

Return exactly one JSON array.
Each element must have exactly these keys:
{{
  "item": "string",
  "count": number,
  "unit": "string",
  "op": "+" | "-"
}}

Sample Inventory:

Current inventory:
  - egg: 13.0 piece
  - water: 20.0 L
  - onion: 6.0 piece
  - garlic: 1.0 kg
  - tomato: 12.0 piece
  - potato: 10.0 piece
  - rice: 2.0 kg
  - pasta: 500.0 g
  - milk: 2.0 L
  - butter: 200.0 g
  - olive oil: 500.0 ml
Input String:

I have 1 liter of water and 3 kilograms of rice. I also want to remove 2 pieces of egg.
Output:

[
  {{
    "item": "water",
    "count": 1.0,
    "unit": "L",
    "op": "+"
  }},
  {{
    "item": "rice",
    "count": 3.0,
    "unit": "kg",
    "op": "+"
  }},
  {{
    "item": "egg",
    "count": -2.0,
    "unit": "piece",
    "op": "-"
  }}
]

Rules:
- Never ever leave unit empty or give null use "piece", "nos.", "slice", "clove", "bunch", "stalk", "sprig", "leaf", "cube", "dozen" if there is no unit but the item is countable.
- Extract every ingredient mention into one array element.
- op is "+" for add intent and "-" for remove intent.
- If intent is unclear, use "+".
- Catch numbers carefully, including decimals and fractions (e.g. 1/2 -> 0.5, 2.5).
- count must always be a number. If missing, use 1.
- unit should be the normalized unit text (e.g., g, kg, ml, L, cup, cups, piece, nos., slice, clove, bunch, stalk, sprig, leaf, cube, dozen).
- Never return null/empty for unit. If not present in text and the item is countable, choose from: piece, nos., slice, clove, bunch, stalk, sprig, leaf, cube, dozen.
- If not present in text and not clearly countable, use "piece".
- item should be clean name without quantity or unit.
- Do not invent ingredients or quantities.
- Output JSON only, no markdown, no extra text.
- if the item already exists in the convert the unit to the one in inventrory before calculating the count change.
"""


def _make_system_prompt(inventory: list[dict]) -> str:
    """Build system prompt with current inventory context."""
    inventory_context = _format_inventory_context(inventory)
    return INVENTORY_PARSE_SYSTEM_PROMPT_TEMPLATE.format(
        inventory_context=inventory_context
    )


COUNTABLE_ITEM_KEYWORDS = {
    "egg": "piece",
    "eggs": "piece",
    "garlic": "clove",
    "clove": "clove",
    "onion": "piece",
    "onions": "piece",
    "tomato": "piece",
    "tomatoes": "piece",
    "banana": "piece",
    "bananas": "piece",
    "apple": "piece",
    "apples": "piece",
    "lemon": "piece",
    "lemons": "piece",
    "lime": "piece",
    "limes": "piece",
    "bread": "slice",
    "carrot": "piece",
    "carrots": "piece",
    "chili": "piece",
    "chillies": "piece",
    "potato": "piece",
    "potatoes": "piece",
}


UNIT_ALIASES = {
    "pieces": "piece",
    "pc": "piece",
    "pcs": "piece",
    "nos": "nos.",
    "no": "nos.",
    "number": "nos.",
    "tsp": "teaspoon",
    "tbsp": "tablespoon",
}


def _default_unit_for_item(item: str) -> str:
    name = (item or "").strip().lower()
    if not name:
        return "piece"
    for token in re.split(r"[^a-zA-Z]+", name):
        if token in COUNTABLE_ITEM_KEYWORDS:
            return COUNTABLE_ITEM_KEYWORDS[token]
    return "piece"


def _ensure_unit(item: str, unit: str | None) -> str:
    normalized = _normalize_unit(unit)
    if normalized:
        return UNIT_ALIASES.get(normalized, normalized)
    return _default_unit_for_item(item)


def _extract_json_value(text: str):
    content = text.strip()

    if content.startswith("```"):
        lines = content.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    arr_start = content.find("[")
    arr_end = content.rfind("]")
    if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
        return json.loads(content[arr_start : arr_end + 1])

    obj_start = content.find("{")
    obj_end = content.rfind("}")
    if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
        return json.loads(content[obj_start : obj_end + 1])

    raise ValueError("No JSON found in LLM output")


def _parse_quantity(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s:
        return None

    frac = re.fullmatch(r"(\d+)\s*/\s*(\d+)", s)
    if frac:
        num = int(frac.group(1))
        den = int(frac.group(2))
        if den != 0:
            return num / den
        return None

    try:
        return float(s)
    except ValueError:
        return None


def _normalize_change(change: dict) -> dict | None:
    if not isinstance(change, dict):
        return None

    item = str(change.get("item") or change.get("ingredient") or "").strip()
    if not item:
        return None

    raw_op = str(change.get("op") or change.get("operation") or "").strip().lower()
    op = "-" if raw_op in {"-", "remove", "removed", "delete", "used"} else "+"

    count = _parse_quantity(change.get("count"))
    if count is None:
        count = _parse_quantity(change.get("quantity"))
    if count is None:
        count = 1.0

    unit_raw = change.get("unit")
    unit = str(unit_raw).strip() if unit_raw is not None else None
    if unit == "":
        unit = None
    unit = _ensure_unit(item, unit)

    return {
        "item": item,
        "count": count,
        "unit": unit,
        "op": op,
    }


def parse_inventory_input_with_llm(user_text: str, current_inventory: list[dict] | None = None) -> list[dict]:
    if current_inventory is None:
        current_inventory = []
    
    system_prompt = _make_system_prompt(current_inventory)
    print(f"[parser] System prompt: {system_prompt}")
    payload = {
        "model": MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    }

    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = json.loads(urllib.request.urlopen(req).read())
    except Exception as e:
        print(f"[parser] LLM connection error: {e}")
        raise ValueError(f"Failed to connect to Ollama at {OLLAMA_URL}: {e}") from e
    
    content = response.get("message", {}).get("content", "")
    if not content:
        print(f"[parser] Empty response from Ollama: {response}")
        raise ValueError("Ollama returned empty content")
    
    try:
        parsed = _extract_json_value(content)
    except Exception as e:
        print(f"[parser] Failed to extract JSON from: {content[:200]}")
        raise ValueError(f"Could not parse LLM response as JSON: {e}") from e

    raw_changes = parsed
    if isinstance(parsed, dict):
        raw_changes = parsed.get("changes")

    normalized_changes: list[dict] = []
    if isinstance(raw_changes, list):
        for item in raw_changes:
            normalized = _normalize_change(item)
            if normalized is not None:
                normalized_changes.append(normalized)

    return normalized_changes
