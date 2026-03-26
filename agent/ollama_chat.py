"""
ollama_chat.py
--------------
Terminal chatbot that calls the FastAPI backend.
The backend handles Ollama + Qdrant + personalisation.

Usage:
  python ollama_chat.py [--token TOKEN]

If --token is not provided, it will login with hardcoded credentials.

Commands:
  /exit   — quit
  /new    — clear history
  /rate   — rate the last recipe (manual; uses your Mongo inventory via the API)

Flow:
  Ask for a recipe → refine in follow-up messages → when finished say
  "done", "that's all", or "please rate" → the app asks for 1–5 → reply with
  a single digit or use /rate.
"""

import json
import urllib.request
from pathlib import Path
import argparse

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8000"
HISTORY = Path(__file__).with_name("chat_history.json")

def verify_token(token: str) -> bool:
    req = urllib.request.Request(
        f"{API_BASE}/auth/verify-token",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="GET",
    )
    try:
        response = json.loads(urllib.request.urlopen(req).read())
        return response.get("valid", False)
    except Exception:
        return False


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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recipe Chatbot")
    parser.add_argument("--token", type=str, help="User access token")
    args = parser.parse_args()

    print("=== Recipe Chatbot ===")

    if args.token:
        token = args.token
        if not verify_token(token):
            print("❌ Invalid token provided")
            exit(1)
        print("✅ Using provided token\n")
    else:
        username = "elena"
        password = "Password1!"
        try:
            token = login(username, password)
            print(f"✅ Logged in as {username}\n")
        except Exception as e:
            print(f"❌ Login failed: {e}")
            exit(1)

    messages = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []
    last_recipe = None

    print("Commands: /exit | /new | /rate")
    print("(After a recipe: keep chatting to refine; say 'done' to rate.)")
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
        trigger_rating = response.get("trigger_rating_ui", False)
        rating_saved = response.get("rating_saved", False)

        print(f"\nAssistant: {reply}")

        if is_recipe or ("recipe_name" in reply and "ingredients" in reply):
            last_recipe = reply

        if rating_saved:
            print("\n📊 Rating saved — future recipes will use this feedback.")
        elif trigger_rating:
            print("\n💡 Reply with a single digit 1–5 to score the last recipe.")
        elif is_recipe:
            print("\n💡 Ask for changes, or say 'done' / 'that's all' when you want to rate.")

        # Update history
        messages.append({"role": "user", "content": text})
        messages.append({"role": "assistant", "content": reply})
        HISTORY.write_text(json.dumps(messages, indent=2), encoding="utf-8")