"""
chat_service.py
---------------
Builds the system prompt with injected past ratings and calls Ollama.
"""

import json
import urllib.request
from .qdrant_storage import get_relevant_ratings

# ── Config ────────────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:1b"

# ── System prompt ─────────────────────────────────────────────────────────────

BASE_SYSTEM_PROMPT = """You are a personal recipe assistant.

When generating a recipe, always respond in this JSON format:
{{
  "recipe_name": "...",
  "ingredients": ["..."],
  "steps": ["..."],
  "tips": "..."
}}

When NOT generating a recipe (e.g. answering questions, acknowledging ratings),
respond in plain conversational text.

Use the user's past ratings below to:
- Read the review text carefully — it tells you exactly what the user liked or disliked
- If rating is 4 or 5, replicate those specific flavours, techniques, or ingredients mentioned in the review
- If rating is 1 or 2, avoid anything mentioned in the review
- If rating is 3, note what they said and try to improve on it
- You MUST start your response with one sentence explaining how the user's past ratings influenced this recipe. Example: "Based on your love of roasted vegetables, I chose..."

{ratings_context}
"""


def build_system_prompt(query: str, user_id: str) -> dict:
    """
    Fetch relevant past ratings from Qdrant and inject into system prompt.
    """
    ratings_context = get_relevant_ratings(query=query, user_id=user_id)

    filled = BASE_SYSTEM_PROMPT.format(
        ratings_context=ratings_context if ratings_context else "No past ratings yet for this user."
    )
    print("\n===== SYSTEM PROMPT =====")  # ← add this
    print(filled)                          # ← add this
    print("=========================\n")   # ← add this
    return {"role": "system", "content": filled}


# ── Ollama call ───────────────────────────────────────────────────────────────

def call_ollama(system_message: dict, history: list[dict]) -> str:
    """
    Call Ollama with system prompt prepended to conversation history.
    """
    messages = [system_message] + history

    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    response = urllib.request.urlopen(req).read()
    return json.loads(response)["message"]["content"]


# ── Recipe detection ──────────────────────────────────────────────────────────

def is_recipe_response(reply: str) -> bool:
    """
    Returns True if the reply contains a recipe (triggers rating UI).
    """
    return "recipe_name" in reply and "ingredients" in reply
