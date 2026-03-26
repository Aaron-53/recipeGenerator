from mcp.server import Server
from qdrant_client import QdrantClient
from datetime import datetime
import asyncio

server = Server("recipe-rating-server")

# Connect Qdrant
qdrant = QdrantClient(host="localhost", port=6333)
COLLECTION = "recipe_ratings"


# 🟡 Tool 1: Ask for rating
@server.tool()
async def request_rating() -> str:
    """Ask user to provide a rating (1–5) and optional review."""
    return "Please rate this recipe from 1 to 5 and share your feedback."


# 🟢 Tool 2: Save rating
@server.tool()
async def save_rating(recipe_text: str, rating: int, review: str = "", user_id: str = "") -> str:
    """Save user rating and review for a recipe."""

    point = {
        "recipe_text": recipe_text,
        "rating": rating,
        "review": review,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }

    # Store in Qdrant
    qdrant.upsert(
        collection_name=COLLECTION,
        points=[
            {
                "id": int(datetime.now().timestamp() * 1000),  # Better uniqueness
                "vector": [0.0] * 384,  # placeholder (or use embeddings later)
                "payload": point
            }
        ]
    )

    return "Rating saved successfully!"


if __name__ == "__main__":
    asyncio.run(server.run())