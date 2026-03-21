import json, os, urllib.request
from pathlib import Path

MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
URL = "http://localhost:11434/api/chat"
HISTORY = Path(__file__).with_name("chat_history.json")
messages = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []

print(f"Model: {MODEL} | /exit to quit | /new to clear history")
while True:
    text = input("You: ").strip()
    if not text:
        continue
    if text == "/exit":
        break
    if text == "/new":
        messages = []
        HISTORY.write_text("[]", encoding="utf-8")
        print("Started a new chat.")
        continue
    messages.append({"role": "user", "content": text})
    req = urllib.request.Request(
        URL,
        data=json.dumps({"model": MODEL, "messages": messages, "stream": False}).encode(
            "utf-8"
        ),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    reply = json.loads(urllib.request.urlopen(req).read())["message"]["content"]
    print("Assistant:", reply)
    messages.append({"role": "assistant", "content": reply})
    HISTORY.write_text(json.dumps(messages, indent=2), encoding="utf-8")
