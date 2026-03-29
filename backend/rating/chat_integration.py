from __future__ import annotations

import json
import os
import urllib.request
from typing import Callable, Optional

from configs import settings
from rating.qdrant_storage import get_relevant_ratings, save_rating
from schemas.recipe import RecipeRetrieveItem, display_description_from_payload

OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434").rstrip("/")
OLLAMA_CHAT_COMPLETIONS_URL = f"{OLLAMA_BASE}/v1/chat/completions"
MODEL = "qwen2.5:7b"

MAX_HISTORY_MESSAGES = 28

_DISH_OR_INGREDIENT_WORDS = frozenset(
    {
        "chicken",
        "beef",
        "pork",
        "fish",
        "salmon",
        "tuna",
        "cod",
        "shrimp",
        "prawn",
        "prawns",
        "crab",
        "lobster",
        "lamb",
        "mutton",
        "turkey",
        "duck",
        "tofu",
        "tempeh",
        "egg",
        "eggs",
        "rice",
        "noodle",
        "noodles",
        "pasta",
        "spaghetti",
        "lasagna",
        "gnocchi",
        "couscous",
        "quinoa",
        "oatmeal",
        "pancakes",
        "waffles",
        "pizza",
        "burger",
        "burgers",
        "tacos",
        "burrito",
        "quesadilla",
        "steak",
        "ribs",
        "wings",
        "meatballs",
        "sausage",
        "bacon",
        "ham",
        "biryani",
        "dosa",
        "idli",
        "sambar",
        "rasam",
        "payasam",
        "kheer",
        "curry",
        "dal",
        "lentils",
        "chickpea",
        "chickpeas",
        "beans",
        "broccoli",
        "spinach",
        "mushroom",
        "mushrooms",
        "potato",
        "potatoes",
        "cauliflower",
        "paneer",
        "halloumi",
    }
)


def _debug_print_retrieval_from_system(system_content: str) -> None:
    if not settings.DEBUG:
        return
    n = len(system_content or "")
    print(f"\n[ollama_debug] system prompt length={n} chars\n")


def _json_object_from_model_text(content: str) -> dict | None:
    t = (content or "").strip()
    if not t:
        return None
    try:
        o = json.loads(t)
        return o if isinstance(o, dict) else None
    except json.JSONDecodeError:
        pass
    lo, hi = t.find("{"), t.rfind("}")
    if lo >= 0 and hi > lo:
        try:
            o = json.loads(t[lo : hi + 1])
            return o if isinstance(o, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _ollama_extract_search_query_via_json_schema(model: str, last_user_text: str) -> str:
    u = (last_user_text or "").strip()
    if not u:
        return ""
    body: dict = {
        "model": model,
        "stream": False,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Output only valid JSON with one field: search_query (string). "
                    "The value is a short phrase to find recipes (dish name, cuisine, or key ingredients). "
                    "No markdown fences, no other keys, no explanation."
                ),
            },
            {"role": "user", "content": u},
        ],
        "format": {
            "type": "object",
            "properties": {"search_query": {"type": "string"}},
            "required": ["search_query"],
        },
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_CHAT_COMPLETIONS_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    raw = json.loads(urllib.request.urlopen(req).read())
    content = (raw.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    obj = _json_object_from_model_text(content)
    if not obj:
        return ""
    return str(obj.get("search_query") or "").strip()


def _debug_print_retrieval_from_tool(items: list[RecipeRetrieveItem]) -> None:
    if not settings.DEBUG:
        return
    print("\n==== RETRIEVAL FROM search_recipe_database TOOL (DEBUG) ====")
    if not items:
        print("  (empty result set)")
    else:
        for i, it in enumerate(items[:8], 1):
            print(f"  {i}. {it.title or '(untitled)'}")
    print("============================================================\n")


REQUEST_RATING_UI_TOOL = {
    "type": "function",
    "function": {
        "name": "request_rating_ui",
        "description": (
            "Open the in-app star-rating popup for the recipe you already gave in this chat. "
            "Call when the user wraps up with thanks, goodbye, or done — and only if you "
            "already output a recipe JSON earlier in this thread. Do not call for new "
            "cooking requests or when there was no recipe in the conversation."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

SAVE_RATING_TOOL = {
    "type": "function",
    "function": {
        "name": "save_rating",
        "description": (
            "Save the user's star rating (1-5) for the recipe you last gave them. "
            "Call when they clearly give a numeric rating (e.g. after the in-app rating flow or "
            "when they state a star rating in chat)."
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

SEARCH_RECIPE_DATABASE_TOOL = {
    "type": "function",
    "function": {
        "name": "search_recipe_database",
        "description": (
            "Search the user's recipe database. Returns one to three recipes that match the "
            "search_query by description similarity (weak matches are dropped). "
            "Call this **only** when the user clearly wants recipe help: a dish to make, meal ideas, "
            "what to cook, or a named food. Do not call for greetings (hi, hello, hey), small talk, "
            "thanks-only, meta chat, or messages with no cooking intent — reply in plain text instead. "
            "When you do call it, pass search_query (include user corrections on follow-up turns); "
            "do not answer those requests from memory alone. "
            "Never reply with only a status line like 'Searching for…' without calling this tool **when** "
            "a search-backed recipe reply is required. "
            "After results, keep any chat text to at most 2 lines — do not list recipes, ingredients, "
            "or steps in prose (the UI shows them)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": (
                        "What to look up, e.g. 'quick vegetarian pasta', 'chocolate dessert', "
                        "'sugar craving sweet snack'. Use the user's intent in your own words."
                    ),
                }
            },
            "required": ["search_query"],
        },
    },
}

TOOLS: list = [SAVE_RATING_TOOL]


def recipe_mode_tool_list() -> list:
    return [SEARCH_RECIPE_DATABASE_TOOL, REQUEST_RATING_UI_TOOL, SAVE_RATING_TOOL]


def recipe_mode_post_search_tool_list() -> list:
    return [REQUEST_RATING_UI_TOOL, SAVE_RATING_TOOL]


def recipe_mode_rating_only_tool_list() -> list:
    return [REQUEST_RATING_UI_TOOL, SAVE_RATING_TOOL]


WRAPUP_SESSION_SYSTEM_SUFFIX = """

=== SESSION WRAP-UP — THIS USER MESSAGE ONLY (mandatory) ===
The user is only wrapping up (thanks, goodbye, all set) after you **already** shared a recipe JSON in this chat.
- You **MUST** call the tool **request_rating_ui** once (no parameters). That opens the in-app star rating for the recipe they already have.
- **search_recipe_database is disabled on this turn** — you cannot search or suggest new dishes, titles, or numbered options.
- Reply in **at most one short sentence** of plain text (e.g. warm thanks). Do **not** output recipe JSON, ingredient lists, steps, or any numbered list of meals.
"""


WRAPUP_USER_FACING_REPLY = (
    "You're welcome! Use the stars above if you'd like to rate the recipe."
)


BASE_SYSTEM_PROMPT = """You are Kitchen Mate — a personalized meal planner and recipe assistant.

=== USER PANTRY (authoritative — obey this) ===
{pantry_block}

Hard rules:
- If the user only greets you or chats without a cooking or recipe request, reply in plain text only — do NOT output recipe JSON.
- If the user only says thanks, goodbye, or that they are done (no new cooking request), reply in plain text only — do NOT output a full recipe JSON.
- If the message is gibberish, nonsense, or too vague to interpret as a cooking request (unclear dish, diet, or question), reply in plain text only: say you are not sure what they meant and ask them to rephrase (e.g. what they want to make or which ingredients to use). Do NOT output recipe JSON until their request is clear.
- Recipe ingredients MUST come from this pantry (plus basic prep: heat, boiling, mixing). Water = liquid for boiling or thinning. Egg = any normal egg preparation.
- Do NOT output beef, wine, canned soup, chuck roast, or other items not in the pantry unless you first say in plain text that they must buy those, and still prefer a recipe using ONLY pantry items.
- If the pantry is very small (e.g. only egg and water), say so briefly, then give the best possible dish using ONLY those items (boiled egg, scrambled egg, simple egg-drop soup with water), not an unrelated pot roast.
- **Retrieval alignment:** When you use database rows (from a prior search_recipe_database tool result in this conversation), the numbered RETRIEVED RECIPES there are the only database-backed dishes the user can pick in the app. Your JSON recipe MUST clearly follow one of those numbered recipes (usually #1 or best pantry_coverage): same dish type, title, and ingredient structure. Do NOT invent a different meal (e.g. a fruit salad or generic dessert) when every retrieval is a savory main — say briefly in plain text that the closest database matches are savory, then base your JSON on the best-matching numbered retrieval anyway. Never output JSON for a dish that is not one of the listed retrievals unless you did not use the search tool.

Full recipe format: one JSON object (no markdown fences), at most **2 lines** of plain text before it (no numbered lists of options or full recipes in prose):
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

Do not paste a long in-chat star-rating questionnaire; the app may offer rating separately.

---

RETRIEVED RECIPES (vector DB):
{retrieval_block}

---

PAST RATINGS CONTEXT:
{ratings_context}
"""


RECIPE_TOOL_SYSTEM_PROMPT = """You are Kitchen Mate — a personalized meal planner and recipe assistant.

=== USER PANTRY (authoritative — obey this) ===
{pantry_block}

=== ALLERGIES, DISLIKES & TASTE (soft — you decide) ===
- The backend **does not** remove recipes from search based on allergies or “I don’t have X”. You see the user’s **messages** in this chat and the **RETRIEVED RECIPES** from the tool — **you** choose among them, substitute, or omit ingredients in JSON as needed.
- Treat a stated **allergy** or strong **dislike** like a **dislike / low rating**: prefer other options when possible, adapt the recipe (omit or replace), and say so briefly if the best DB row still conflicts.
- Longer-term taste is reflected in **Mongo preferences** from past thumbs/ratings (blended into retrieval). Align with **PAST RATINGS CONTEXT** below when it helps.

=== CHAT INTRO — STRICT (read before every reply) ===
- **At most 2 lines** of plain text before your JSON object (or before you stop typing if there is no JSON). A "line" means one visual row — no filler blank lines. If you need more than ~180 characters of setup, you are writing too much.
- **Forbidden in that intro:** any numbered list (`1.` `2.` `3.`), any bullet lists of ingredients, any "Ingredients:" / "Steps:" blocks, any full recipe prose, any multi-paragraph explanation, or **any recipe or dish names** (including names you invent or remember). When the app shows multiple matches, **real library titles appear on the options** — if you name different dishes in text, the user will see a broken mismatch.
- **Do not** send a user-visible reply that is only a status phrase ("Searching for…", "Looking up…") **when** you still owe a library-backed recipe — then you must **call `search_recipe_database`** in that turn. For greetings or non-cooking messages, **do not** call the tool and **do not** output recipe JSON.
- After **`search_recipe_database`** returns, read how many numbered RETRIEVED RECIPE rows you got:
  - **Exactly one row:** use a **generic** one-line intro **without** mentioning options, choosing, or picking — e.g. "Here is a library match below." Then output **one** JSON recipe. Do **not** say "use the options", "pick an option", or similar when there is only one match.
  - **Two or three rows:** you may mention choosing among **options**, e.g. "Here are library matches — tap an option below." or "Found a few matches in your collection below." Do **not** list dish titles. Then output **one** JSON recipe.
- If the tool returns **no** rows, say briefly that nothing close turned up (still obey pantry rules); do **not** pretend you are still searching, and do **not** mention options or choosing.
- **Never** invent a parallel "option 1 / option 2 / option 3" write-up with ingredients and steps in chat text. That duplicates the card and is wrong.
- Do **not** paste internal retrieval fields (no "match=", no "pantry_coverage="). The **options** (when several exist) and the card already show details.

=== DATABASE SEARCH (`search_recipe_database`) ===
- You have a function tool **search_recipe_database** with parameter **search_query**. Each successful call runs a **single** relevance-ranked search and returns **one to three** database recipes that match the query (fewer if only the top result is a strong match).

**You decide whether this message needs a search** — the backend does **not** force a recipe on the first message or on "hi". Use plain text for chitchat; use the tool only when the user is asking for food help.

**Mandatory — when there *is* a cooking/recipe request**
- If the user asks for **food**, **recipes**, **meals**, **cooking suggestions**, what to cook/make, ideas from their pantry, names a dish, or similar — you **MUST** call **search_recipe_database** **before** you answer with a recipe JSON or library-backed dish picks. A reply that is **only** "Searching for…" / "Looking up…" (with no tool call) in that situation is **wrong** — call the tool, then answer after results.
- On **follow-up** messages (e.g. they want a different style, less spice, vegetarian, or to tweak the last suggestion), call **search_recipe_database** again with an updated **search_query** that includes their correction — you will get a **new set** of up to three options.
- Do **NOT** answer those requests from your own knowledge alone. Do not invent standalone recipes from memory when a database search applies. Wait for the tool result, then base your reply on the numbered **RETRIEVED RECIPES** (adapt for USER PANTRY as already required below).

**Exceptions — do not call `search_recipe_database`**
- **Greetings and small talk** (hi, hello, hey, good morning, how are you, what's up) **without** a cooking ask — reply in **one or two short sentences** of plain text; invite them to say what they'd like to cook. **No tool call, no recipe JSON, no random library dump.**
- Pure thanks, goodbye, or wrap-up with **no** new food/recipe/cooking ask — plain text only (no new search). On those turns the backend **removes** the search tool and only allows **`request_rating_ui`** — never invent a numbered list of new dishes.
- Gibberish or messages too vague to treat as a cooking request (see Hard rules) — plain text only; no recipe JSON.

**Rating popup (`request_rating_ui`)**
- When the user is **only** wrapping up (thanks, bye, all set) **after** you already shared a recipe JSON in this thread, call **`request_rating_ui`** once on that turn (no parameters) so the app opens its star-rating dialog. Keep your reply to one or two warm sentences.
- Do **not** call `search_recipe_database` for that wrap-up message.
- Do **not** call `request_rating_ui` if this conversation never had a recipe from you.

- When **search_recipe_database** returns, it appends numbered **RETRIEVED RECIPES** — those rows are the database-backed dishes for your JSON in that turn. Your **user-visible prose** must still obey CHAT INTRO — STRICT: never dump them as a long written menu with ingredients/steps.

Hard rules:
- If the user only greets you or chats without a cooking or recipe request, reply in plain text only — do NOT call `search_recipe_database`, do NOT output recipe JSON.
- If the user only says thanks, goodbye, or that they are done (no new cooking request), reply in plain text only — do NOT output a full recipe JSON.
- If the message is gibberish, nonsense, or too vague to interpret as a cooking request (unclear dish, diet, or question), reply in plain text only: say you are not sure what they meant and ask them to rephrase (e.g. what they want to make or which ingredients to use). Do NOT output recipe JSON until their request is clear.
- Recipe ingredients MUST come from this pantry (plus basic prep: heat, boiling, mixing). Water = liquid for boiling or thinning. Egg = any normal egg preparation.
- Do NOT output beef, wine, canned soup, chuck roast, or other items not in the pantry unless you first say in plain text that they must buy those, and still prefer a recipe using ONLY pantry items.
- If the pantry is very small (e.g. only egg and water), say so briefly, then give the best possible dish using ONLY those items (boiled egg, scrambled egg, simple egg-drop soup with water), not an unrelated pot roast.
- **Retrieval alignment:** When **search_recipe_database** returns numbered RETRIEVED RECIPES, those are the only database-backed dishes. If the system message includes **USER SELECTION (from client)** with a point_id and title, your JSON must follow **that** recipe only (not option #1 by default). Otherwise prefer the best pantry_coverage row among the numbered retrievals. Same dish type, title, and ingredient structure. Do NOT invent a different meal (e.g. a fruit salad or generic dessert) when every retrieval is a savory main — say briefly in plain text that the closest database matches are savory, then base your JSON on the best-matching numbered retrieval anyway. For any food/recipe request, you should have called the tool first (see DATABASE SEARCH above); do not claim specific database recipe titles without a tool result.

Full recipe format: one JSON object (no markdown fences), plus **at most 2 lines** of plain text before it (see CHAT INTRO — STRICT above). No numbered options or ingredient lists in prose:
{{
  "recipe_name": "...",
  "ingredients": ["..."],
  "steps": ["..."],
  "tips": "..."
}}

Ingredients list (mandatory — every line must have quantity + unit):
- **No abbreviations or short forms** in ingredient lines. Write full words: e.g. "3 tablespoons extra virgin olive oil" — never "EVOO", "tbsp", "tsp", "veg", "parm", "AP flour". Spell out **tablespoon(s)** and **teaspoon(s)**. Ingredient names must be plain English ("extra virgin olive oil", "Parmesan cheese", "all-purpose flour"). Metric amounts may use **g**, **kg**, **ml**, **L** with the number, or spell out units — both are fine as long as names are not abbreviated.
- When your JSON is based on a **search_recipe_database** result, keep the **amounts** the same but **rewrite** any abbreviated wording from the database into full words before putting lines in your JSON.
- When your recipe is clearly based on one of those retrievals (especially the top match with good pantry_coverage), match quantities and ingredients closely; only skip or swap an item if it is not in USER PANTRY (mention briefly in plain text or "tips").
- If you are NOT closely following a retrieval, compose lines yourself with full words only.
- Examples: "200 grams basmati rice", "2 tablespoons vegetable oil", "0.5 teaspoon fine salt", "4 cups water", "2 large eggs".

Small clarifications without a full recipe: plain text only.

When tool results include RETRIEVED RECIPES, prefer high pantry_coverage unless **USER SELECTION** fixes one row. Expand any abbreviations from the database into full words in your output. Apply the same no-abbreviation rule in **steps** and **tips** when naming foods or oils. Write **tips** as practical cooking advice in your own words (never paste raw database tag lines).

PAST RATINGS & FEEDBACK (feeds retrieval via Mongo preferences):
- 4–5 stars / likes → similar style; stronger pull toward those ingredients/tags
- 1–2 stars / dislikes → downrank (same **soft** idea as allergies in chat — you still choose and adapt)
- 3 stars → improve

Do not paste a long in-chat star-rating questionnaire — use **`request_rating_ui`** when they wrap up after a recipe (see above).

---

PAST RATINGS CONTEXT:
{ratings_context}
"""


def build_recipe_tool_system_prompt(
    query: str,
    user_id: str,
    inventory: list[str],
) -> dict:
    ratings_context = get_relevant_ratings(query=query, user_id=user_id)
    if ratings_context:
        ratings_context = ratings_context[:900]
    else:
        ratings_context = "No past ratings yet."

    pantry_block = _format_pantry_block(inventory)
    content = RECIPE_TOOL_SYSTEM_PROMPT.format(
        pantry_block=pantry_block,
        ratings_context=ratings_context,
    )
    return {"role": "system", "content": content}


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
        desc = display_description_from_payload(pay, max_len=280) or "(no description)"
        ings = pay.get("ingredients") or pay.get("ingredients_normalized") or []
        if isinstance(ings, list):
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


def _format_retrieval_block_for_tool(items: list[RecipeRetrieveItem]) -> str:
    if not items:
        return (
            "No database rows matched after filters. Obey USER PANTRY and CONSTRAINTS; "
            "say so briefly in 1–2 sentences, then JSON or plain text only."
        )
    lines: list[str] = []
    for i, it in enumerate(items, 1):
        pay = it.payload or {}
        desc = display_description_from_payload(pay, max_len=140) or "(no description)"
        ings = pay.get("ingredients") or pay.get("ingredients_normalized") or []
        if isinstance(ings, list):
            ing_block = "\n".join(f"      • {str(x)}" for x in ings[:18])
        else:
            ing_block = f"      • {str(ings)[:200]}"
        lines.append(
            f"{i}. {it.title or '(untitled)'}\n"
            f"   Ingredients (database strings — copy verbatim when using this row):\n"
            f"{ing_block}\n"
            f"   Description: {desc}"
        )
    return "\n".join(lines)


def _tool_result_content_for_search(items: list[RecipeRetrieveItem]) -> str:
    return (
        "RETRIEVED RECIPES (vector DB) — ranked by match to search_query; "
        "use these numbered rows for database-backed JSON:\n\n"
        + _format_retrieval_block_for_tool(items)
    )


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


def _assistant_message_has_recipe_context(m: dict) -> bool:
    """True if the client sent evidence of a recipe card (JSON in text and/or ranked_suggestions / ids)."""
    if m.get("role") != "assistant":
        return False
    c = (m.get("content") or "")
    if "recipe_name" in c and "ingredients" in c:
        return True
    if m.get("point_id") or m.get("recipe_id"):
        return True
    rs = m.get("ranked_suggestions")
    if isinstance(rs, list) and len(rs) > 0:
        return True
    return False


def _prior_has_recipe_for_wrapup(prior: list[dict]) -> bool:
    for m in reversed(prior or []):
        if _assistant_message_has_recipe_context(m):
            return True
    return False


def _looks_like_session_wrapup(user_msg: str) -> bool:
    t = (user_msg or "").strip().lower()
    if not t:
        return False
    words = t.split()
    if len(words) > 14:
        return False
    markers = (
        "thanks",
        "thank you",
        "ty",
        "thx",
        "bye",
        "goodbye",
        "cheers",
        "all set",
        "that's all",
        "thats all",
        "appreciate it",
    )
    if any(m in t for m in markers):
        return True
    one_shot = {
        "ok",
        "okay",
        "k",
        "kk",
        "done",
        "good",
        "great",
        "perfect",
        "awesome",
        "nice",
        "yep",
        "yeah",
        "sure",
        "ok thanks",
        "okay thanks",
        "thanks!",
        "thank you!",
    }
    if t in one_shot or t.rstrip("!.") in one_shot:
        return True
    if len(words) <= 5 and any(
        w in ("great", "perfect", "awesome", "nice", "lovely", "good") for w in words
    ):
        return True
    return False


def _looks_like_recipe_search_intent(user_msg: str) -> bool:
    if _looks_like_session_wrapup(user_msg):
        return False
    t = (user_msg or "").strip().lower()
    if len(t) < 3:
        return False
    words = [w.rstrip("!.?,'\"") for w in t.split() if w]
    chat_only = frozenset(
        {
            "hi",
            "hey",
            "hello",
            "yo",
            "there",
            "morning",
            "afternoon",
            "evening",
            "thanks",
            "thank",
            "you",
            "thx",
            "ty",
            "ok",
            "okay",
            "k",
            "kk",
            "bye",
            "goodbye",
            "cheers",
            "great",
            "nice",
            "cool",
            "sure",
            "yes",
            "no",
            "sup",
            "doing",
            "fine",
            "good",
            "well",
            "how",
            "are",
            "whats",
            "what's",
            "up",
            "going",
        }
    )
    if words and len(words) <= 4 and all(w in chat_only for w in words):
        return False
    if words and any(w in _DISH_OR_INGREDIENT_WORDS for w in words):
        return True
    needles = (
        "recipe",
        "recipes",
        "cook",
        "cooking",
        "make",
        "made",
        "dinner",
        "lunch",
        "breakfast",
        "brunch",
        "meal",
        "meals",
        "snack",
        "dessert",
        "food",
        "eat",
        "eating",
        "dish",
        "dishes",
        "pantry",
        "ingredient",
        "ingredients",
        "bake",
        "baking",
        "grill",
        "fried",
        "fry",
        "roast",
        "soup",
        "salad",
        "pasta",
        "curry",
        "stew",
        "cake",
        "cookies",
        "pie",
        "payasam",
        "kheer",
        "sweet",
        "sweets",
        "savory",
        "vegetarian",
        "vegan",
        "spicy",
        "tonight",
        "today",
        "hungry",
        "craving",
        "suggest",
        "ideas",
        "idea",
        "something",
        "using",
        "from my",
        "with my",
        "i want",
        "want ",
        "want to",
        "wanna",
        "would like",
        "like to",
        "help me",
        "looking for",
        "need a",
        "give me",
        "show me",
        "any good",
    )
    if any(n in t for n in needles):
        return True
    return len(t) >= 36


def is_recipe_response(reply: str) -> bool:
    return "recipe_name" in reply and "ingredients" in reply


def is_wrapup_rating_turn(user_msg: str, prior: list[dict]) -> bool:
    if not _prior_has_recipe_for_wrapup(prior):
        return False
    return _looks_like_session_wrapup(user_msg)


def supplement_rating_trigger_if_wrapup(
    user_msg: str,
    prior: list[dict],
    model_triggered: bool,
) -> bool:
    if model_triggered:
        return True
    if not _prior_has_recipe_for_wrapup(prior):
        return False
    return _looks_like_session_wrapup(user_msg)


def _ollama_chat(payload: dict) -> dict:
    body: dict = {
        "model": payload["model"],
        "messages": payload["messages"],
        "stream": bool(payload.get("stream", False)),
    }
    if "temperature" in payload:
        body["temperature"] = payload["temperature"]
    if payload.get("format") is not None:
        body["format"] = payload["format"]
    tools = payload.get("tools")
    if tools:
        body["tools"] = tools
        if payload.get("tool_choice") is not None:
            body["tool_choice"] = payload["tool_choice"]
    if settings.DEBUG:
        print(
            f"[ollama_debug] POST {OLLAMA_CHAT_COMPLETIONS_URL} "
            f"n_messages={len(body.get('messages') or [])} "
            f"n_tools={len(body.get('tools') or [])} "
            f"tool_choice={body.get('tool_choice')!r} "
            f"temperature={body.get('temperature', 'default')!r}"
        )
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_CHAT_COMPLETIONS_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    raw = json.loads(urllib.request.urlopen(req).read())
    ch0 = (raw.get("choices") or [{}])[0]
    if settings.DEBUG:
        mdbg = ch0.get("message") or {}
        print(
            f"[ollama_debug] raw finish_reason={ch0.get('finish_reason')!r} "
            f"has_tool_calls={bool(mdbg.get('tool_calls'))} "
            f"has_function_call={bool(mdbg.get('function_call'))}"
        )
    msg = dict(ch0.get("message") or {})
    if msg.get("content") is None:
        msg["content"] = ""
    fc = msg.get("function_call")
    if fc and not msg.get("tool_calls"):
        fn = (fc.get("name") or "").strip()
        raw_args = fc.get("arguments")
        if raw_args is not None and not isinstance(raw_args, str):
            raw_args = json.dumps(raw_args)
        msg["tool_calls"] = [
            {
                "id": "call_legacy_0",
                "type": "function",
                "function": {"name": fn, "arguments": (raw_args or "{}").strip() or "{}"},
            }
        ]
    tcs = msg.get("tool_calls")
    if tcs:
        fixed: list[dict] = []
        for i, tc in enumerate(tcs):
            tc = dict(tc)
            if not tc.get("id"):
                tc["id"] = f"call_{i}"
            fixed.append(tc)
        msg["tool_calls"] = fixed
    return {"message": msg}


def compose_retrieval_query(
    user_message: str,
    prior_history: list[dict],
    max_len: int = 900,
) -> str:
    u = (user_message or "").strip()
    if not u:
        return ""

    for m in reversed(prior_history[-8:] or []):
        if m.get("role") != "assistant":
            continue
        c = (m.get("content") or "").strip()
        if len(c) < 50:
            continue
        if "recipe_name" in c and "ingredients" in c:
            continue
        merged = (
            f"{u}\n\nPrevious assistant reply (context for refinement):\n{c[:max_len // 2]}"
        )
        return merged[:max_len]
    return u[:max_len]


def call_ollama(
    system_message: dict,
    history: list[dict],
    user_id: str,
    *,
    tools: list | None = None,
    run_recipe_search: Optional[Callable[[str], list[RecipeRetrieveItem]]] = None,
    default_search_query: Optional[str] = None,
    wrapup_after_recipe: bool = False,
) -> tuple[str, bool, bool, list[RecipeRetrieveItem]]:
    history = history[-MAX_HISTORY_MESSAGES:]
    messages: list[dict] = [system_message] + history

    _debug_print_retrieval_from_system(system_message.get("content") or "")

    if wrapup_after_recipe:
        tool_list = recipe_mode_rating_only_tool_list()
    elif tools is not None and len(tools) == 0:
        tool_list: list = []
    elif run_recipe_search is not None:
        tool_list = recipe_mode_tool_list()
    elif tools is None:
        tool_list = TOOLS
    else:
        tool_list = tools

    collected_items: list[RecipeRetrieveItem] = []
    search_executed_this_request = False
    rating_was_saved = False
    trigger_rating_ui = False
    reply = ""
    max_rounds = 8

    for round_idx in range(max_rounds):
        payload: dict = {"model": MODEL, "messages": messages, "stream": False}
        if tool_list:
            if search_executed_this_request:
                payload["tools"] = recipe_mode_post_search_tool_list()
            else:
                payload["tools"] = tool_list

        response = _ollama_chat(payload)

        if settings.DEBUG and round_idx == 0:
            print("\n==== OLLAMA HTTP RESPONSE (DEBUG) round=1 ====")
            print(
                "Recipe mode: model chooses tools (no forced search); greetings stay plain text.\n"
            )
            print(json.dumps(response, indent=2)[:4000])
            print("========================================\n")

        msg = response.get("message") or {}
        reply = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []

        if (
            round_idx == 0
            and tool_list
            and not wrapup_after_recipe
            and run_recipe_search is not None
            and not tool_calls
            and not is_recipe_response(reply)
        ):
            last_u = (history[-1].get("content") or "").strip() if history else ""
            if _looks_like_recipe_search_intent(last_u):
                if settings.DEBUG:
                    print(
                        "[ollama_debug] recipe-like message without tool_calls — "
                        "retry with forced search_recipe_database (greetings skip this)."
                    )
                forced_payload: dict = {
                    "model": MODEL,
                    "messages": messages,
                    "stream": False,
                    "tools": [SEARCH_RECIPE_DATABASE_TOOL],
                    "tool_choice": {
                        "type": "function",
                        "function": {"name": "search_recipe_database"},
                    },
                    "temperature": 0,
                }
                response = _ollama_chat(forced_payload)
                msg = dict(response.get("message") or {})
                if msg.get("content") is None:
                    msg["content"] = ""
                tool_calls = msg.get("tool_calls") or []
                reply = msg.get("content") or ""

            if (
                not tool_calls
                and run_recipe_search is not None
                and _looks_like_recipe_search_intent(last_u)
            ):
                if settings.DEBUG:
                    print(
                        "[ollama_debug] forced search still missing tool_calls — "
                        "JSON-schema search_query extract + synthetic tool messages."
                    )
                q = _ollama_extract_search_query_via_json_schema(MODEL, last_u)
                if not q:
                    q = (default_search_query or last_u).strip()
                collected_items = run_recipe_search(q)
                search_executed_this_request = True
                _debug_print_retrieval_from_tool(collected_items)
                tool_content = _tool_result_content_for_search(collected_items)
                forced_id = "forced_search_0"
                messages.append(
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": forced_id,
                                "type": "function",
                                "function": {
                                    "name": "search_recipe_database",
                                    "arguments": json.dumps({"search_query": q}),
                                },
                            }
                        ],
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": forced_id,
                        "name": "search_recipe_database",
                        "content": tool_content,
                    }
                )
                continue

        if tool_calls:
            messages.append(msg)
            for tool in tool_calls:
                fn = tool.get("function") or {}
                name = fn.get("name")
                raw_args = fn.get("arguments")
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args) if (raw_args or "").strip() else {}
                    except json.JSONDecodeError:
                        args = {}
                else:
                    args = raw_args or {}

                if name == "search_recipe_database" and run_recipe_search is not None:
                    search_executed_this_request = True
                    q = str(args.get("search_query") or "").strip()
                    if not q:
                        q = (default_search_query or (history[-1].get("content") or "")).strip()
                    collected_items = run_recipe_search(q)
                    _debug_print_retrieval_from_tool(collected_items)
                    tool_content = _tool_result_content_for_search(collected_items)
                elif name == "request_rating_ui":
                    trigger_rating_ui = True
                    tool_content = (
                        "OK — the app will show the rating popup for the last recipe in this chat."
                    )
                elif name == "save_rating":
                    rating = int(args.get("rating") or 0)
                    review = str(args.get("review") or "")
                    recipe_text = args.get("recipe_text") or _extract_last_recipe_json(
                        history
                    ) or (history[-2]["content"] if len(history) >= 2 else "")
                    if 1 <= rating <= 5 and recipe_text:
                        save_rating(str(recipe_text)[:2000], rating, review, user_id)
                        rating_was_saved = True
                    tool_content = "Rating saved." if rating_was_saved else "No rating saved."
                else:
                    tool_content = f"Unknown or unavailable tool: {name!r}."

                tool_msg: dict = {"role": "tool", "content": tool_content}
                tc_id = tool.get("id")
                if tc_id:
                    tool_msg["tool_call_id"] = tc_id
                if name:
                    tool_msg["name"] = name
                messages.append(tool_msg)
            continue

        break

    if rating_was_saved:
        reply = "✅ Your rating has been saved!"

    return reply, rating_was_saved, trigger_rating_ui, collected_items
