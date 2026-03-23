from qdrant_client import QdrantClient

from configs import settings


QDRANT_COLLECTION_NAME = settings.QDRANT_COLLECTION_NAME


def get_qdrant_client() -> QdrantClient:
    """Create a Qdrant client using centralized configuration."""
    return QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        timeout=settings.QDRANT_TIMEOUT_SECONDS,
    )
