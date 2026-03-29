"""
qdrant_service.py
-----------------
Handles all Qdrant operations for the recipe rating system.

Collection:  recipe_ratings  (separate from teammate's recipe_embeddings)
Embed model: BAAI/bge-base-en-v1.5  (same as teammate — consistency)
Vector size: 768
"""

import uuid
import torch
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

# ── Config ────────────────────────────────────────────────────────────────────

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "recipe_ratings"
EMBED_MODEL = "BAAI/bge-base-en-v1.5"
VECTOR_SIZE = 768

# ── Load embedding model once ─────────────────────────────────────────────────

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[qdrant_service] Loading embedding model on {device}...")
_model = SentenceTransformer(EMBED_MODEL, device=device)
print(f"[qdrant_service] Model ready.")

# ── Qdrant client ─────────────────────────────────────────────────────────────

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=60)


# ── Collection setup ──────────────────────────────────────────────────────────

def ensure_collection():
    """
    Create recipe_ratings collection if it doesn't exist.
    Call once at FastAPI startup.
    """
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )
        print(f"[Qdrant] Created collection: {COLLECTION_NAME}")
    else:
        print(f"[Qdrant] Collection already exists: {COLLECTION_NAME}")


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed(text: str) -> list[float]:
    """
    Embed text using BAAI/bge-base-en-v1.5.
    normalize_embeddings=True is required for BGE models.
    Returns a list of 768 floats.
    """
    vector = _model.encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return vector.tolist()


def _stable_rating_point_id(user_id: str, recipe_point_id: str) -> str:
    key = f"recipe-rating:{user_id}:{str(recipe_point_id).strip()}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def save_rating(
    recipe_text: str,
    rating: int,
    review: str,
    user_id: str,
    point_id: str | None = None,
):
    """
    Embed the recipe text and store it in recipe_ratings with metadata.
    """
    vector = embed(recipe_text)

    rid = (
        _stable_rating_point_id(user_id, point_id)
        if point_id and str(point_id).strip()
        else str(uuid.uuid4())
    )

    point = PointStruct(
        id=rid,
        vector=vector,
        payload={
            "recipe_text": recipe_text[:500],
            "rating": rating,
            "review": review,
            "user_id": user_id,
            **(
                {"recipe_point_id": str(point_id).strip()}
                if point_id and str(point_id).strip()
                else {}
            ),
        },
    )

    client.upsert(collection_name=COLLECTION_NAME, points=[point])
    print(f"[Qdrant] Saved rating {rating}/5 for user {user_id} point_id={point_id!r}")

# ── Fetch relevant ratings ────────────────────────────────────────────────────

def get_relevant_ratings(query: str, user_id: str, top_k: int = 3) -> str:
    vector = embed(query)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=top_k,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id),
                )
            ]
        ),
        with_payload=True,
    )

    points = results.points if hasattr(results, "points") else results[0]

    if not points:
        return ""

    lines = []
    for r in points:
        p = r.payload
        snippet = p.get("recipe_text", "")[:80].replace("\n", " ")
        rating = p.get("rating", "?")
        review = p.get("review", "")
        lines.append(f'- "{snippet}..." → {rating}/5 | "{review}"')

    return "User's past similar recipes and ratings:\n" + "\n".join(lines)