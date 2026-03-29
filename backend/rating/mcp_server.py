from mcp.server import Server
from qdrant_client import QdrantClient
from datetime import datetime
import asyncio

server = Server("recipe-rating-server")

qdrant = QdrantClient(host="localhost", port=6333)
COLLECTION = "recipe_ratings"


@server.tool()
async def request_rating() -> str:
    return "Please rate this recipe from 1 to 5 and share your feedback."


@server.tool()
async def save_rating(recipe_text: str, rating: int, review: str = "", user_id: str = "") -> str:
    point = {
        "recipe_text": recipe_text,
        "rating": rating,
        "review": review,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }

    qdrant.upsert(
        collection_name=COLLECTION,
        points=[
            {
                "id": int(datetime.now().timestamp() * 1000),
                "vector": [0.0] * 384,
                "payload": point
            }
        ]
    )

    return "Rating saved successfully!"


if __name__ == "__main__":
    asyncio.run(server.run())