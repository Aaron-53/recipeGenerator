"""
ollama_chat.py
--------------
Terminal chatbot that calls the FastAPI backend.
The backend handles Ollama + Qdrant + personalisation.

Commands:
  /exit   — quit
  /new    — clear history
  /rate   — rate the last recipe
"""

import json
import urllib.request
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8000"
HISTORY = Path(__file__).with_name("chat_history.json")

# ── Auth ──────────────────────────────────────────────────────────────────────

def login(username: str, password: str) -> str:
    payload = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    response = json.loads(urllib.request.urlopen(req).read())
    return response["access_token"]


# ── API calls ─────────────────────────────────────────────────────────────────

def send_message(token: str, message: str, history: list) -> dict:
    payload = json.dumps({"message": message, "history": history}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/chat/message",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req).read())


def submit_rating(token: str, recipe_text: str, rating: int, review: str):
    payload = json.dumps({
        "recipe_text": recipe_text,
        "rating": rating,
        "review": review,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/chat/rate",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req).read())


# ── Main loop ─────────────────────────────────────────────────────────────────

print("=== Recipe Chatbot ===")
username = input("Username: ").strip()
password = input("Password: ").strip()

try:
    token = login(username, password)
    print(f"✅ Logged in as {username}\n")
except Exception as e:
    print(f"❌ Login failed: {e}")
    exit(1)

messages = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []
last_recipe = None

print("Commands: /exit | /new | /rate")
print("-" * 40)

while True:
    text = input("\nYou: ").strip()

    if not text:
        continue

    if text == "/exit":
        print("Bye!")
        break

    if text == "/new":
        messages = []
        last_recipe = None
        HISTORY.write_text("[]", encoding="utf-8")
        print("✅ Started a new chat.")
        continue

    if text == "/rate":
        if not last_recipe:
            print("⚠️  No recipe to rate yet. Ask for a recipe first.")
            continue

        print("\nLast recipe snippet:")
        print(f"  {last_recipe[:80]}...")

        while True:
            r = input("Rating (1-5): ").strip()
            if r.isdigit() and 1 <= int(r) <= 5:
                rating = int(r)
                break
            print("Please enter a number between 1 and 5.")

        review = input("Review (or press Enter to skip): ").strip()

        try:
            result = submit_rating(token, last_recipe, rating, review)
            print(f"✅ {result['message']}")
            print("📊 Rating saved to Qdrant. Next recipe will use this.")
        except Exception as e:
            print(f"❌ Failed to save rating: {e}")
        continue

    # Send to FastAPI
    print("⏳ Thinking...")
    try:
        response = send_message(token, text, messages)
    except Exception as e:
        print(f"❌ Error: {e}")
        continue

    reply = response["reply"]
    is_recipe = response["is_recipe"]

    print(f"\nAssistant: {reply}")

    if is_recipe:
        last_recipe = reply
        print("\n💡 Type /rate to rate this recipe")

    # Update history
    messages.append({"role": "user", "content": text})
    messages.append({"role": "assistant", "content": reply})
    HISTORY.write_text(json.dumps(messages, indent=2), encoding="utf-8")