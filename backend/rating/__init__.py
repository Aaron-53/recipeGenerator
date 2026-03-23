"""
Rating and Review System
------------------------
Manages recipe ratings, reviews, and embeddings via Qdrant.

Modules:
  - qdrant_storage: Vector DB operations (save/retrieve ratings)
  - chat_integration: System prompt injection with past ratings
  - router: FastAPI endpoints for ratings
"""

from .qdrant_storage import save_rating, get_relevant_ratings, ensure_collection
from .chat_integration import build_system_prompt, is_recipe_response

__all__ = [
    "save_rating",
    "get_relevant_ratings",
    "ensure_collection",
    "build_system_prompt",
    "is_recipe_response",
]