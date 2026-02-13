import json
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
import torch

# Configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "recipe_embeddings"

# Setup
device = "cuda" if torch.cuda.is_available() else "cpu"
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
model = SentenceTransformer("BAAI/bge-base-en-v1.5", device=device)


def get_collection_stats():
    """Get basic statistics about the collection"""
    try:
        collection_info = qdrant_client.get_collection(collection_name=COLLECTION_NAME)
        print(f"Collection: {COLLECTION_NAME}")
        print(f"Total points: {collection_info.points_count}")
        print(f"Vector size: {collection_info.config.params.vectors.size}")
        print(f"Distance metric: {collection_info.config.params.vectors.distance}")
        return collection_info
    except Exception as e:
        print(f"Error getting collection info: {e}")
        return None


def search_recipes(query_text, limit=5):
    """Search for similar recipes using text query"""
    try:
        # Generate embedding for the query
        query_embedding = model.encode(
            query_text, convert_to_numpy=True, normalize_embeddings=True
        ).tolist()

        # Search in Qdrant
        search_results = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=limit,
            with_payload=True,
        )

        print(f"\nSearch results for: '{query_text}'")
        print("-" * 50)

        for i, result in enumerate(search_results, 1):
            score = result.score
            payload = result.payload

            # Extract recipe info
            recipe_text = payload.get("text", "No text available")[:100] + "..."
            recipe_title = payload.get("title", "No title")

            print(f"{i}. Score: {score:.4f}")
            print(f"   Title: {recipe_title}")
            print(f"   Text: {recipe_text}")
            print()

        return search_results

    except Exception as e:
        print(f"Error searching: {e}")
        return []


def get_random_recipes(limit=3):
    """Get random recipes from the collection"""
    try:
        # Scroll through some random points
        scroll_result = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        points = scroll_result[0]
        print(f"\nRandom {limit} recipes from collection:")
        print("-" * 50)

        for i, point in enumerate(points, 1):
            payload = point.payload
            recipe_text = payload.get("text", "No text available")[:150] + "..."
            recipe_title = payload.get("title", "No title")
            recipe_index = payload.get("recipe_index", "Unknown")

            print(f"{i}. Index: {recipe_index}")
            print(f"   Title: {recipe_title}")
            print(f"   Text: {recipe_text}")
            print()

    except Exception as e:
        print(f"Error getting random recipes: {e}")


if __name__ == "__main__":
    print("Qdrant Recipe Database Query Tool")
    print("=" * 40)

    # Show collection stats
    get_collection_stats()

    # Show some random recipes
    get_random_recipes(3)

    # Interactive search
    print("\nInteractive Search (press Enter to exit)")
    print("-" * 40)

    while True:
        query = input("\nEnter search query: ").strip()
        if not query:
            break

        search_recipes(query, limit=3)
