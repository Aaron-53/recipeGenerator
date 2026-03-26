"""
Chat + Ollama: retrieval context, past ratings, and optional save_rating tool.
Rating prompt is triggered only by explicit session-end phrases (handled in router preflight).
"""

from __future__ import annotations

import json
import re
import urllib.request

from configs import settings
from rating.qdrant_storage import get_relevant_ratings, save_rating
from schemas.recipe import RecipeRetrieveItem

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b"

MAX_HISTORY_MESSAGES = 28
RATING_PROMPT = "⭐ Please rate this recipe (1–5) and optionally add a review."

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_rating",
            "description": (
                "Save the user's star rating (1-5) for the recipe you last gave them. "
                "Call ONLY when the user clearly gives a numeric rating after you asked for one."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "recipe_text": {
                        "type": "string",
                        "description": "The JSON recipe text you output earlier (copy verbatim if possible).",
                    },
                    "rating": {"type": "integer", "minimum": 1, "maximum": 5},
                    "review": {"type": "string"},
                },
                "required": ["rating"],
            },
        },
    }
]

BASE_SYSTEM_PROMPT = """You are a personal recipe assistant.

=== USER PANTRY (authoritative — obey this) ===
{pantry_block}

Hard rules:
- Recipe ingredients MUST come from this pantry (plus basic prep: heat, boiling, mixing). Water = liquid for boiling or thinning. Egg = any normal egg preparation.
- Do NOT output beef, wine, canned soup, chuck roast, or other items not in the pantry unless you first say in plain text that they must buy those, and still prefer a recipe using ONLY pantry items.
- If the pantry is very small (e.g. only egg and water), say so briefly, then give the best possible dish using ONLY those items (boiled egg, scrambled egg, simple egg-drop soup with water), not an unrelated pot roast.

Full recipe format: one JSON object (no markdown fences), optionally one short plain sentence before it:
{{
  "recipe_name": "...",
  "ingredients": ["..."],
  "steps": ["..."],
  "tips": "..."
}}

Ingredients list (mandatory — every line must have quantity + unit):
- **No abbreviations or short forms** in ingredient lines. Write full words: e.g. "3 tablespoons extra virgin olive oil" — never "EVOO", "tbsp", "tsp", "veg", "parm", "AP flour". Spell out **tablespoon(s)** and **teaspoon(s)**. Ingredient names must be plain English ("extra virgin olive oil", "Parmesan cheese", "all-purpose flour"). Metric amounts may use **g**, **kg**, **ml**, **L** with the number, or spell out units — both are fine as long as names are not abbreviated.
- RETRIEVED RECIPES below come from your recipe database (Qdrant). When you use a retrieval, keep the **amounts** the same but **rewrite** any abbreviated wording from the database into full words before putting lines in your JSON.
- When your recipe is clearly based on one of those retrievals (especially the top match with good pantry_coverage), match quantities and ingredients closely; only skip or swap an item if it is not in USER PANTRY (mention briefly in plain text or "tips").
- If you are NOT closely following a retrieval, compose lines yourself with full words only.
- Examples: "200 grams basmati rice", "2 tablespoons vegetable oil", "0.5 teaspoon fine salt", "4 cups water", "2 large eggs".

Small clarifications without a full recipe: plain text only.

Use RETRIEVED RECIPES below; prefer high pantry_coverage. Expand any abbreviations from the database into full words in your output. Apply the same no-abbreviation rule in **steps** and **tips** when naming foods or oils.

PAST RATINGS:
- 4–5 stars → similar style
- 1–2 stars → avoid
- 3 stars → improve

Do not ask for a rating.

---

RETRIEVED RECIPES (vector DB):
{retrieval_block}

---

PAST RATINGS CONTEXT:
{ratings_context}
"""


def _format_pantry_block(inventory: list[str]) -> str:
    if not inventory:
        return "No ingredients on file — suggest general ideas and say what to buy."
    return "The user has these ingredients at home: " + ", ".join(inventory)


def _format_retrieval_block(items: list[RecipeRetrieveItem]) -> str:
    if not items:
        return "No close database matches — still obey the USER PANTRY list above; do not invent unrelated shopping-heavy dishes."
    lines: list[str] = []
    for i, it in enumerate(items, 1):
        pay = it.payload or {}
        desc = (pay.get("description") or pay.get("desc_embedding_text") or "")[:280]
        ings = pay.get("ingredients") or pay.get("ingredients_normalized") or []
        if isinstance(ings, list):
            # One line per ingredient so the model can copy Qdrant strings verbatim (same units as stored).
            ing_block = "\n".join(f"      • {str(x)}" for x in ings[:24])
        else:
            ing_block = f"      • {str(ings)[:200]}"
        lines.append(
            f"{i}. {it.title or '(untitled)'} — match={it.final_score:.3f}, "
            f"pantry_coverage={it.ingredient_coverage:.2f}\n"
            f"   Ingredients (exact strings from database — copy verbatim when using this recipe):\n"
            f"{ing_block}\n"
            f"   Description: {desc}"
        )
    return "\n".join(lines)


def build_system_prompt(
    query: str,
    user_id: str,
    retrieval_items: list[RecipeRetrieveItem],
    inventory: list[str],
) -> dict:
    ratings_context = get_relevant_ratings(query=query, user_id=user_id)
    if ratings_context:
        ratings_context = ratings_context[:900]
    else:
        ratings_context = "No past ratings yet."

    pantry_block = _format_pantry_block(inventory)
    retrieval_block = _format_retrieval_block(retrieval_items)
    content = BASE_SYSTEM_PROMPT.format(
        pantry_block=pantry_block,
        retrieval_block=retrieval_block,
        ratings_context=ratings_context,
    )
    return {"role": "system", "content": content}


def _extract_last_recipe_json(history: list[dict]) -> str | None:
    for m in reversed(history):
        if m.get("role") != "assistant":
            continue
        c = m.get("content") or ""
        if "recipe_name" in c and "ingredients" in c:
            return c
    return None


def session_has_recipe(history: list[dict]) -> bool:
    return _extract_last_recipe_json(history) is not None


_END_SESSION_RE = re.compile(
    r"(?i)\b("
    r"i[' ]?m done|i am done|that'?s all|that is all|no more changes|"
    r"finished|all done|we[' ]?re done|we are done|"
    r"rate (this|the recipe|now)|please rate|"
    r"end (of )?(session|chat)|goodbye|bye$"
    r")\b"
)


def user_wants_end_session(text: str) -> bool:
    t = text.strip()
    if len(t) <= 2 and t.lower() == "done":
        return True
    return bool(_END_SESSION_RE.search(t))


def assistant_asked_rating(prior_history: list[dict]) -> bool:
    for m in reversed(prior_history):
        if m.get("role") == "assistant":
            c = m.get("content") or ""
            return "⭐" in c or "Please rate" in c
    return False


def try_preflight_rating_digit(
    message: str, prior_history: list[dict], user_id: str
) -> tuple[str, bool] | None:
    """If user sends a lone 1-5 after a rating prompt, save and return reply."""
    if not re.match(r"^\s*([1-5])\s*$", message.strip()):
        return None
    if not assistant_asked_rating(prior_history):
        return None
    recipe = _extract_last_recipe_json(prior_history)
    if not recipe:
        return None
    rating = int(message.strip())
    save_rating(recipe[:2000], rating, "", user_id)
    return ("✅ Your rating has been saved! I'll use it to personalize future recipes.", True)


def try_preflight_end_session(message: str, prior_history: list[dict]) -> str | None:
    """User explicitly ends — ask for rating only if a recipe exists in the thread."""
    if not user_wants_end_session(message):
        return None
    if not session_has_recipe(prior_history):
        return None
    return RATING_PROMPT


def call_ollama(
    system_message: dict,
    history: list[dict],
    user_id: str,
) -> tuple[str, bool, bool]:
    """
    history must include the latest user message as the last item.
    Returns: reply, rating_saved, trigger_rating_ui (latter always False here).
    """
    history = history[-MAX_HISTORY_MESSAGES:]
    messages = [system_message] + history

    payload = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
            "stream": False,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    response = json.loads(urllib.request.urlopen(req).read())

    if settings.DEBUG:
        print("\n==== OLLAMA RAW (DEBUG) ====")
        print(json.dumps(response, indent=2)[:4000])
        print("============================\n")

    message = response.get("message", {})
    reply = message.get("content") or ""
    tool_calls = message.get("tool_calls") or []

    rating_was_saved = False
    trigger_rating_ui = False

    if tool_calls:
        for tool in tool_calls:
            fn = tool.get("function", {})
            name = fn.get("name")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}

            if name == "save_rating":
                rating = int(args.get("rating") or 0)
                review = str(args.get("review") or "")
                recipe_text = args.get("recipe_text") or _extract_last_recipe_json(
                    history
                ) or (history[-2]["content"] if len(history) >= 2 else "")
                if 1 <= rating <= 5 and recipe_text:
                    save_rating(str(recipe_text)[:2000], rating, review, user_id)
                    rating_was_saved = True

        messages.append({"role": "assistant", "content": reply})
        tool_msg = "Rating saved." if rating_was_saved else "No rating saved."
        messages.append({"role": "tool", "content": tool_msg})

        followup_payload = json.dumps(
            {"model": MODEL, "messages": messages, "stream": False}
        ).encode("utf-8")
        followup_req = urllib.request.Request(
            OLLAMA_URL,
            data=followup_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            followup_response = json.loads(urllib.request.urlopen(followup_req).read())
            followup_reply = followup_response.get("message", {}).get("content") or ""
        except Exception:
            followup_reply = ""

        if rating_was_saved:
            reply = "✅ Your rating has been saved!"
        elif followup_reply and "save_rating" not in followup_reply.lower():
            reply = followup_reply
        else:
            reply = reply or "Thanks!"

    else:
        user_text = history[-1].get("content", "") if history else ""
        # Optional: "rate it 4" style
        match = re.search(
            r"(?:^|\s)(?:rate|rating|give it|i give|stars?)[^\d]{0,12}([1-5])(?:\s|$|/5)",
            user_text.lower(),
        )
        if not match:
            match = re.search(r"\b([1-5])\s*/\s*5\b", user_text)
        if match and session_has_recipe(history[:-1]):
            rating = int(match.group(1))
            recipe = _extract_last_recipe_json(history[:-1])
            if recipe and assistant_asked_rating(history[:-1]):
                save_rating(recipe[:2000], rating, "", user_id)
                rating_was_saved = True
                reply = "✅ Your rating has been saved!"

    return reply, rating_was_saved, trigger_rating_ui


def is_recipe_response(reply: str) -> bool:
    return "recipe_name" in reply and "ingredients" in reply
