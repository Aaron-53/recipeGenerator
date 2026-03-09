"""
Multi-Model Data Store with Composite Indexing

This module implements the sophisticated data storage architecture with three distinct views:
1. Vector Embedding: High-dimensional representations in Qdrant
2. Metadata Layer: Structured, searchable fields for hard filtering
3. Social Graph: Comments, ratings, and popularity scoring

The system provides composite indexing strategy for efficient retrieval and filtering.
"""

import json
import sqlite3
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    Range,
)
from qdrant_client.http.exceptions import ResponseHandlingException

from data_models import (
    EnhancedRecipe,
    RecipeMetadata,
    SocialData,
    Comment,
    UserProfile,
    ScoredRecipe,
    DataModelUtils,
)


class MultiModelDataStore:
    """Manages the three-layer data architecture for recipes"""

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        vector_collection: str = "recipe_embeddings",
        social_db_path: str = "social_graph.db",
    ):
        """Initialize the multi-model data store"""

        # Qdrant configuration
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.vector_collection = vector_collection
        self.embedding_size = 768  # BGE base model size

        # SQLite configuration for social graph
        self.social_db_path = social_db_path

        # Initialize connections
        self.qdrant_client = self._init_qdrant()
        self._init_social_database()

        print("✅ Multi-model data store initialized")

    def _init_qdrant(self) -> QdrantClient:
        """Initialize Qdrant client and collection"""
        try:
            client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)

            # Test connection
            collections = client.get_collections()
            print(f"✅ Connected to Qdrant at {self.qdrant_host}:{self.qdrant_port}")

            # Setup collection if it doesn't exist
            try:
                collection_info = client.get_collection(
                    collection_name=self.vector_collection
                )
                print(
                    f"📁 Using existing collection '{self.vector_collection}' with {collection_info.points_count} points"
                )
            except Exception:
                # Create collection
                client.create_collection(
                    collection_name=self.vector_collection,
                    vectors_config=VectorParams(
                        size=self.embedding_size, distance=Distance.COSINE
                    ),
                )
                print(f"🔨 Created new collection '{self.vector_collection}'")

            return client

        except Exception as e:
            print(f"❌ Failed to connect to Qdrant: {e}")
            raise

    def _init_social_database(self):
        """Initialize SQLite database for social graph data"""
        conn = sqlite3.connect(self.social_db_path)
        cursor = conn.cursor()

        # Recipe metadata table (for hard filtering)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_metadata (
                recipe_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                allergies TEXT,  -- JSON list
                ingredients TEXT,  -- JSON list
                dietary_tags TEXT,  -- JSON list
                cuisine_type TEXT,
                cooking_time_minutes INTEGER,
                difficulty_level TEXT,
                serving_size INTEGER,
                calories_per_serving INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Social data aggregation table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_social (
                recipe_id TEXT PRIMARY KEY,
                average_rating REAL DEFAULT 0.0,
                total_ratings INTEGER DEFAULT 0,
                total_comments INTEGER DEFAULT 0,
                popularity_score REAL DEFAULT 0.0,
                recent_ratings TEXT,  -- JSON list of recent ratings
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recipe_id) REFERENCES recipe_metadata(recipe_id)
            )
        """)

        # Individual comments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_comments (
                comment_id TEXT PRIMARY KEY,
                recipe_id TEXT,
                user_id TEXT,
                text_content TEXT NOT NULL,
                rating REAL NOT NULL,
                helpful_votes INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recipe_id) REFERENCES recipe_metadata(recipe_id)
            )
        """)

        # Indexes for performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_recipe_cuisine ON recipe_metadata(cuisine_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_recipe_time ON recipe_metadata(cooking_time_minutes)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_recipe_difficulty ON recipe_metadata(difficulty_level)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_social_rating ON recipe_social(average_rating)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_social_popularity ON recipe_social(popularity_score)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_comments_recipe ON recipe_comments(recipe_id)"
        )

        conn.commit()
        conn.close()
        print("✅ Social graph database initialized")

    # Recipe Storage Operations
    def store_enhanced_recipe(self, recipe: EnhancedRecipe) -> bool:
        """Store recipe across all three data views"""
        try:
            # 1. Store vector embedding in Qdrant
            if not self._store_vector_embedding(recipe):
                return False

            # 2. Store metadata for hard filtering
            if not self._store_recipe_metadata(recipe):
                return False

            # 3. Initialize social data
            if not self._initialize_social_data(recipe):
                return False

            print(f"✅ Stored complete recipe: {recipe.title}")
            return True

        except Exception as e:
            print(f"❌ Failed to store recipe {recipe.recipe_id}: {e}")
            return False

    def _store_vector_embedding(self, recipe: EnhancedRecipe) -> bool:
        """Store recipe embedding in Qdrant with metadata payload"""
        try:
            # Prepare payload with essential metadata for vector search
            payload = {
                "recipe_id": recipe.recipe_id,
                "title": recipe.title,
                "text": recipe.text[:500],  # Truncated for payload size
                "cuisine_type": recipe.metadata.cuisine_type,
                "difficulty_level": recipe.metadata.difficulty_level,
                "cooking_time_minutes": recipe.metadata.cooking_time_minutes,
                "dietary_tags": recipe.metadata.dietary_tags,
                "allergies": recipe.metadata.allergies,
                "ingredients_count": len(recipe.metadata.ingredients),
                "created_at": recipe.created_at.isoformat(),
            }

            # Create point
            point = PointStruct(
                id=recipe.recipe_id, vector=recipe.embedding, payload=payload
            )

            # Upload to Qdrant
            self.qdrant_client.upsert(
                collection_name=self.vector_collection, points=[point], wait=True
            )

            return True

        except Exception as e:
            print(f"❌ Failed to store vector embedding: {e}")
            return False

    def _store_recipe_metadata(self, recipe: EnhancedRecipe) -> bool:
        """Store recipe metadata in SQLite for hard filtering"""
        conn = sqlite3.connect(self.social_db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO recipe_metadata 
                (recipe_id, title, allergies, ingredients, dietary_tags, cuisine_type,
                 cooking_time_minutes, difficulty_level, serving_size, calories_per_serving,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    recipe.recipe_id,
                    recipe.title,
                    json.dumps(recipe.metadata.allergies),
                    json.dumps(recipe.metadata.ingredients),
                    json.dumps(recipe.metadata.dietary_tags),
                    recipe.metadata.cuisine_type,
                    recipe.metadata.cooking_time_minutes,
                    recipe.metadata.difficulty_level,
                    recipe.metadata.serving_size,
                    recipe.metadata.calories_per_serving,
                    recipe.created_at.isoformat(),
                    recipe.updated_at.isoformat(),
                ),
            )

            conn.commit()
            return True

        except Exception as e:
            print(f"❌ Failed to store metadata: {e}")
            return False
        finally:
            conn.close()

    def _initialize_social_data(self, recipe: EnhancedRecipe) -> bool:
        """Initialize social data entry for recipe"""
        conn = sqlite3.connect(self.social_db_path)
        cursor = conn.cursor()

        try:
            # Use existing social data if provided, otherwise initialize empty
            social = recipe.social or SocialData(recipe_id=recipe.recipe_id)

            cursor.execute(
                """
                INSERT OR REPLACE INTO recipe_social
                (recipe_id, average_rating, total_ratings, total_comments,
                 popularity_score, recent_ratings, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    social.recipe_id,
                    social.average_rating,
                    social.total_ratings,
                    social.total_comments,
                    social.popularity_score,
                    json.dumps(social.recent_ratings),
                    datetime.now().isoformat(),
                ),
            )

            conn.commit()
            return True

        except Exception as e:
            print(f"❌ Failed to initialize social data: {e}")
            return False
        finally:
            conn.close()

    # Hard Filtering (Safety Gate)
    def get_safe_recipe_ids(self, user_profile: UserProfile) -> List[str]:
        """Get recipe IDs that are safe for user (pass allergy filter)"""
        if not user_profile.constraints.never_items:
            return []  # No restrictions, return all

        conn = sqlite3.connect(self.social_db_path)
        cursor = conn.cursor()

        try:
            # Get all recipes
            cursor.execute("SELECT recipe_id, allergies FROM recipe_metadata")
            safe_recipe_ids = []

            for recipe_id, allergies_json in cursor.fetchall():
                allergies = json.loads(allergies_json or "[]")

                # Check if recipe contains any allergens
                has_allergen = any(
                    allergen in allergies
                    for allergen in user_profile.constraints.never_items
                )

                if not has_allergen:
                    safe_recipe_ids.append(recipe_id)

            print(f"🔒 Safety filter: {len(safe_recipe_ids)} safe recipes for user")
            return safe_recipe_ids

        except Exception as e:
            print(f"❌ Safety filter error: {e}")
            return []
        finally:
            conn.close()

    def apply_constraint_filters(
        self,
        user_profile: UserProfile,
        max_cooking_time: Optional[int] = None,
        cuisine_filter: Optional[str] = None,
        difficulty_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply hard filtering constraints and return Qdrant filter"""

        # Get safe recipe IDs (allergy filter)
        safe_recipe_ids = self.get_safe_recipe_ids(user_profile)

        must_conditions = []

        # Safety filter (most important)
        if safe_recipe_ids:
            # For very large lists, we might need to use a different strategy
            # For now, use match_any on recipe_id
            if len(safe_recipe_ids) < 1000:  # Qdrant limit consideration
                must_conditions.append(
                    FieldCondition(key="recipe_id", match=MatchAny(any=safe_recipe_ids))
                )

        # Time constraint
        cooking_time_limit = (
            max_cooking_time or user_profile.constraints.max_cooking_time
        )
        if cooking_time_limit:
            must_conditions.append(
                FieldCondition(
                    key="cooking_time_minutes", range=Range(lte=cooking_time_limit)
                )
            )

        # Cuisine filter
        target_cuisine = cuisine_filter or (
            user_profile.constraints.cuisine_preferences[0]
            if user_profile.constraints.cuisine_preferences
            else None
        )
        if target_cuisine:
            must_conditions.append(
                FieldCondition(
                    key="cuisine_type", match=MatchValue(value=target_cuisine)
                )
            )

        # Difficulty filter
        target_difficulty = (
            difficulty_filter or user_profile.constraints.difficulty_preference
        )
        if target_difficulty and target_difficulty != "any":
            must_conditions.append(
                FieldCondition(
                    key="difficulty_level", match=MatchValue(value=target_difficulty)
                )
            )

        # Dietary preferences (should have these tags)
        if user_profile.constraints.always_items:
            for item in user_profile.constraints.always_items:
                must_conditions.append(
                    FieldCondition(key="dietary_tags", match=MatchAny(any=[item]))
                )

        return {
            "filter": Filter(must=must_conditions) if must_conditions else None,
            "safe_recipe_count": len(safe_recipe_ids),
        }

    # Vector Search with Hard Filtering
    def semantic_search(
        self,
        query_vector: List[float],
        user_profile: UserProfile,
        limit: int = 20,
        **filter_kwargs,
    ) -> List[Dict[str, Any]]:
        """Perform semantic search with hard filtering applied"""

        try:
            # Apply constraint filtering
            filter_result = self.apply_constraint_filters(user_profile, **filter_kwargs)
            search_filter = filter_result["filter"]

            # Perform vector search in Qdrant
            search_results = self.qdrant_client.query_points(
                collection_name=self.vector_collection,
                query=query_vector,
                query_filter=search_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,  # Don't need vectors back
            )

            # Extract points from QueryResponse
            if hasattr(search_results, "points"):
                points = search_results.points
            else:
                points = search_results

            print(f"🔍 Found {len(points)} recipes matching search criteria")
            return points

        except Exception as e:
            print(f"❌ Semantic search error: {e}")
            return []

    # Social Data Management
    def add_comment(self, comment: Comment) -> bool:
        """Add a comment and update social data"""
        conn = sqlite3.connect(self.social_db_path)
        cursor = conn.cursor()

        try:
            # Insert comment
            cursor.execute(
                """
                INSERT INTO recipe_comments
                (comment_id, recipe_id, user_id, text_content, rating, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    comment.comment_id,
                    comment.recipe_id,
                    comment.user_id,
                    comment.text,
                    comment.rating,
                    comment.timestamp.isoformat(),
                ),
            )

            # Update social aggregation
            self._update_social_aggregation(cursor, comment.recipe_id, comment.rating)

            conn.commit()
            print(f"✅ Added comment for recipe {comment.recipe_id}")
            return True

        except Exception as e:
            print(f"❌ Failed to add comment: {e}")
            return False
        finally:
            conn.close()

    def _update_social_aggregation(self, cursor, recipe_id: str, new_rating: float):
        """Update social aggregation data after new rating"""

        # Get current social data
        cursor.execute(
            "SELECT average_rating, total_ratings, recent_ratings FROM recipe_social WHERE recipe_id = ?",
            (recipe_id,),
        )
        result = cursor.fetchone()

        if result:
            current_avg, total_ratings, recent_ratings_json = result
            recent_ratings = json.loads(recent_ratings_json or "[]")
        else:
            current_avg, total_ratings, recent_ratings = 0.0, 0, []

        # Update running average
        new_total = total_ratings + 1
        new_average = ((current_avg * total_ratings) + new_rating) / new_total

        # Update recent ratings (keep last 10)
        recent_ratings.append(new_rating)
        if len(recent_ratings) > 10:
            recent_ratings = recent_ratings[-10:]

        # Calculate popularity score
        social_data = SocialData(
            recipe_id=recipe_id,
            average_rating=new_average,
            total_ratings=new_total,
            recent_ratings=recent_ratings,
        )
        popularity_score = social_data.calculate_popularity_score()

        # Get comment count
        cursor.execute(
            "SELECT COUNT(*) FROM recipe_comments WHERE recipe_id = ?", (recipe_id,)
        )
        comment_count = cursor.fetchone()[0]

        # Update social data
        cursor.execute(
            """
            UPDATE recipe_social SET
                average_rating = ?, total_ratings = ?, total_comments = ?,
                popularity_score = ?, recent_ratings = ?, last_activity = ?
            WHERE recipe_id = ?
        """,
            (
                new_average,
                new_total,
                comment_count,
                popularity_score,
                json.dumps(recent_ratings),
                datetime.now().isoformat(),
                recipe_id,
            ),
        )

    def get_recipe_social_data(self, recipe_id: str) -> Optional[SocialData]:
        """Get social data for a recipe"""
        conn = sqlite3.connect(self.social_db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT average_rating, total_ratings, total_comments, "
                "popularity_score, recent_ratings FROM recipe_social WHERE recipe_id = ?",
                (recipe_id,),
            )
            result = cursor.fetchone()

            if result:
                (
                    avg_rating,
                    total_ratings,
                    total_comments,
                    popularity_score,
                    recent_ratings_json,
                ) = result
                return SocialData(
                    recipe_id=recipe_id,
                    average_rating=avg_rating,
                    total_ratings=total_ratings,
                    total_comments=total_comments,
                    popularity_score=popularity_score,
                    recent_ratings=json.loads(recent_ratings_json or "[]"),
                )
            return None

        finally:
            conn.close()

    def get_recipe_comments(self, recipe_id: str, limit: int = 10) -> List[Comment]:
        """Get recent comments for a recipe"""
        conn = sqlite3.connect(self.social_db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT comment_id, recipe_id, user_id, text_content, rating, 
                       helpful_votes, timestamp
                FROM recipe_comments 
                WHERE recipe_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """,
                (recipe_id, limit),
            )

            comments = []
            for row in cursor.fetchall():
                (
                    comment_id,
                    recipe_id,
                    user_id,
                    text_content,
                    rating,
                    helpful_votes,
                    timestamp,
                ) = row
                comments.append(
                    Comment(
                        comment_id=comment_id,
                        recipe_id=recipe_id,
                        user_id=user_id,
                        text=text_content,
                        rating=rating,
                        helpful_votes=helpful_votes,
                        timestamp=datetime.fromisoformat(timestamp),
                    )
                )

            return comments

        finally:
            conn.close()

    # Enhanced Recipe Retrieval
    def get_enhanced_recipe(self, recipe_id: str) -> Optional[EnhancedRecipe]:
        """Get complete enhanced recipe with all data views"""

        # Handle different ID formats - could be recipe_id string or numeric point ID
        try:
            # First try treating recipe_id as actual point ID (integers)
            if recipe_id.isdigit():
                point_id = int(recipe_id)
                points = self.qdrant_client.retrieve(
                    collection_name=self.vector_collection,
                    ids=[point_id],
                    with_payload=True,
                    with_vectors=True,
                )
            else:
                # If not numeric, search for the recipe by payload field
                search_result = self.qdrant_client.scroll(
                    collection_name=self.vector_collection,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(key="id", match=MatchValue(value=recipe_id))
                        ]
                    ),
                    limit=1,
                    with_payload=True,
                    with_vectors=True,
                )
                points = search_result[0] if search_result and search_result[0] else []

            if not points:
                return None

            point = points[0]
            payload = point.payload

            # Get full metadata from SQLite
            conn = sqlite3.connect(self.social_db_path)
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "SELECT title, allergies, ingredients, dietary_tags, cuisine_type, "
                    "cooking_time_minutes, difficulty_level, serving_size, calories_per_serving, "
                    "created_at FROM recipe_metadata WHERE recipe_id = ?",
                    (recipe_id,),
                )
                metadata_result = cursor.fetchone()

                if not metadata_result:
                    # Handle legacy data - create basic recipe from Qdrant payload only
                    print(
                        f"⚠️ No metadata found for {recipe_id}, using legacy data structure"
                    )

                    # Extract what we can from the payload
                    title = payload.get("title", "Unknown Recipe")
                    text = payload.get("text", "")

                    # Create basic metadata from available payload data
                    metadata = RecipeMetadata(
                        allergies=payload.get("allergies", []),
                        ingredients=[],  # Legacy data doesn't have structured ingredients
                        dietary_tags=payload.get("dietary_tags", []),
                        cuisine_type=payload.get("cuisine_type", ""),
                        cooking_time_minutes=payload.get("cooking_time_minutes"),
                        difficulty_level=payload.get("difficulty_level", "unknown"),
                        serving_size=payload.get("serving_size"),
                        calories_per_serving=payload.get("calories_per_serving"),
                    )

                    # Create basic enhanced recipe without social data
                    return EnhancedRecipe(
                        recipe_id=recipe_id,
                        title=title,
                        text=text,
                        embedding=point.vector,
                        metadata=metadata,
                        social=None,  # No social data for legacy recipes
                        created_at=datetime.now(),
                    )

                (
                    title,
                    allergies_json,
                    ingredients_json,
                    dietary_tags_json,
                    cuisine_type,
                    cooking_time,
                    difficulty,
                    serving_size,
                    calories,
                    created_at,
                ) = metadata_result

                # Build metadata object
                metadata = RecipeMetadata(
                    allergies=json.loads(allergies_json or "[]"),
                    ingredients=json.loads(ingredients_json or "[]"),
                    dietary_tags=json.loads(dietary_tags_json or "[]"),
                    cuisine_type=cuisine_type,
                    cooking_time_minutes=cooking_time,
                    difficulty_level=difficulty,
                    serving_size=serving_size,
                    calories_per_serving=calories,
                )

                # Get social data
                social_data = self.get_recipe_social_data(recipe_id)

                # Build enhanced recipe
                return EnhancedRecipe(
                    recipe_id=recipe_id,
                    title=title,
                    text=payload.get("text", ""),
                    embedding=point.vector,
                    metadata=metadata,
                    social=social_data,
                    created_at=datetime.fromisoformat(created_at),
                )

            finally:
                conn.close()

        except Exception as e:
            print(f"❌ Error retrieving recipe {recipe_id}: {e}")
            return None

    def get_enhanced_recipe_by_point(
        self, point_id: str, payload_recipe_id: str, point_data=None
    ) -> Optional[EnhancedRecipe]:
        """Get enhanced recipe using Qdrant point ID with fallback payload data"""

        try:
            # If point_data is already provided, use it
            if point_data:
                point = point_data
                payload = point.payload
            else:
                # Retrieve using numeric point ID
                point_id_int = int(point_id) if point_id.isdigit() else None
                if point_id_int is None:
                    print(f"❌ Invalid point ID: {point_id}")
                    return None

                points = self.qdrant_client.retrieve(
                    collection_name=self.vector_collection,
                    ids=[point_id_int],
                    with_payload=True,
                    with_vectors=True,
                )

                if not points:
                    return None

                point = points[0]
                payload = point.payload

            # Get full metadata from SQLite using payload_recipe_id for lookup
            conn = sqlite3.connect(self.social_db_path)
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "SELECT title, allergies, ingredients, dietary_tags, cuisine_type, "
                    "cooking_time_minutes, difficulty_level, serving_size, calories_per_serving, "
                    "created_at FROM recipe_metadata WHERE recipe_id = ?",
                    (payload_recipe_id,),
                )
                metadata_result = cursor.fetchone()

                if not metadata_result:
                    # Handle legacy data - parse recipe from text content
                    print(
                        f"⚠️ No metadata found for {payload_recipe_id}, parsing legacy data structure"
                    )

                    text = payload.get("text", "")

                    # Parse recipe name, ingredients, and instructions from text
                    parsed_recipe = self._parse_legacy_recipe_text(text)

                    # Extract what we can from the payload and parsed text
                    title = parsed_recipe.get("name", f"Recipe {payload_recipe_id}")
                    ingredients = parsed_recipe.get("ingredients", [])
                    instructions = parsed_recipe.get("instructions", [])

                    # Create basic metadata from parsed data
                    metadata = RecipeMetadata(
                        allergies=[],  # Can't determine from legacy data
                        ingredients=ingredients,
                        dietary_tags=[],  # Can't determine from legacy data
                        cuisine_type="",  # Can't determine from legacy data
                        cooking_time_minutes=None,  # Can't determine from legacy data
                        difficulty_level="unknown",
                        serving_size=None,  # Can't determine from legacy data
                        calories_per_serving=None,  # Can't determine from legacy data
                    )

                    # Create basic enhanced recipe without social data
                    return EnhancedRecipe(
                        recipe_id=payload_recipe_id,  # Use the payload recipe_id
                        title=title,
                        text=text,
                        embedding=getattr(point, "vector", None),
                        metadata=metadata,
                        social=None,  # No social data for legacy recipes
                        created_at=datetime.now(),
                    )

                (
                    title,
                    allergies_json,
                    ingredients_json,
                    dietary_tags_json,
                    cuisine_type,
                    cooking_time,
                    difficulty,
                    serving_size,
                    calories,
                    created_at_str,
                ) = metadata_result

                # Parse JSON fields
                allergies = json.loads(allergies_json) if allergies_json else []
                ingredients = json.loads(ingredients_json) if ingredients_json else []
                dietary_tags = (
                    json.loads(dietary_tags_json) if dietary_tags_json else []
                )

                # Get social data
                social = self.get_recipe_social_data(payload_recipe_id)

                # Create metadata object
                metadata = RecipeMetadata(
                    allergies=allergies,
                    ingredients=ingredients,
                    dietary_tags=dietary_tags,
                    cuisine_type=cuisine_type or "",
                    cooking_time_minutes=cooking_time,
                    difficulty_level=difficulty or "unknown",
                    serving_size=serving_size,
                    calories_per_serving=calories,
                )

                # Create enhanced recipe
                return EnhancedRecipe(
                    recipe_id=payload_recipe_id,  # Use the payload recipe_id
                    title=title or f"Recipe {payload_recipe_id}",
                    text=payload.get("text", ""),
                    embedding=getattr(point, "vector", None),
                    metadata=metadata,
                    social=social,
                    created_at=datetime.fromisoformat(created_at_str)
                    if created_at_str
                    else datetime.now(),
                )

            except Exception as e:
                print(
                    f"❌ Error retrieving recipe metadata for {payload_recipe_id}: {e}"
                )
                return None

            finally:
                conn.close()

        except Exception as e:
            print(f"❌ Error retrieving recipe by point {point_id}: {e}")
            return None

    def _parse_legacy_recipe_text(self, text: str) -> Dict[str, Any]:
        """Parse legacy RecipeNLG format text to extract recipe components"""
        import re

        parsed = {"name": "Unknown Recipe", "ingredients": [], "instructions": []}

        try:
            # Extract recipe name using regex
            name_match = re.search(r"Recipe Name:\s*(.+?)\.", text)
            if name_match:
                parsed["name"] = name_match.group(1).strip()

            # Extract ingredients JSON array
            ingredients_match = re.search(
                r"Ingredients used in this recipe include\s*(\[.+?\])", text, re.DOTALL
            )
            if ingredients_match:
                try:
                    ingredients_json = ingredients_match.group(1)
                    # Clean up the JSON (sometimes has extra whitespace/formatting issues)
                    ingredients_json = re.sub(r"\s+", " ", ingredients_json)
                    parsed["ingredients"] = json.loads(ingredients_json)
                except json.JSONDecodeError:
                    print(
                        f"⚠️ Failed to parse ingredients JSON: {ingredients_match.group(1)[:100]}..."
                    )

            # Extract instructions JSON array
            instructions_match = re.search(
                r"follow these steps:\s*(\[.+?\])", text, re.DOTALL
            )
            if instructions_match:
                try:
                    instructions_json = instructions_match.group(1)
                    # Clean up the JSON
                    instructions_json = re.sub(r"\s+", " ", instructions_json)
                    parsed["instructions"] = json.loads(instructions_json)
                except json.JSONDecodeError:
                    print(
                        f"⚠️ Failed to parse instructions JSON: {instructions_match.group(1)[:100]}..."
                    )

        except Exception as e:
            print(f"⚠️ Error parsing legacy recipe text: {e}")

        return parsed

    # Bulk Operations
    def bulk_store_recipes(
        self, recipes: List[EnhancedRecipe], batch_size: int = 100
    ) -> int:
        """Store multiple recipes efficiently"""
        stored_count = 0
        total = len(recipes)

        print(f"📦 Bulk storing {total} recipes in batches of {batch_size}")

        for i in range(0, total, batch_size):
            batch = recipes[i : i + batch_size]
            batch_stored = 0

            for recipe in batch:
                if self.store_enhanced_recipe(recipe):
                    batch_stored += 1

            stored_count += batch_stored
            print(
                f"✅ Batch {i // batch_size + 1}: Stored {batch_stored}/{len(batch)} recipes"
            )

        print(f"🎉 Bulk operation complete: {stored_count}/{total} recipes stored")
        return stored_count

    # Analytics and Statistics
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the data store"""
        try:
            # Qdrant stats
            collection_info = self.qdrant_client.get_collection(
                collection_name=self.vector_collection
            )
            vector_count = collection_info.points_count

            # SQLite stats
            conn = sqlite3.connect(self.social_db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM recipe_metadata")
            metadata_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM recipe_comments")
            total_comments = cursor.fetchone()[0]

            cursor.execute(
                "SELECT AVG(average_rating) FROM recipe_social WHERE total_ratings > 0"
            )
            avg_rating_result = cursor.fetchone()
            avg_rating = avg_rating_result[0] if avg_rating_result[0] else 0.0

            cursor.execute("SELECT AVG(popularity_score) FROM recipe_social")
            avg_popularity_result = cursor.fetchone()
            avg_popularity = (
                avg_popularity_result[0] if avg_popularity_result[0] else 0.0
            )

            conn.close()

            return {
                "vector_embeddings": vector_count,
                "metadata_records": metadata_count,
                "total_comments": total_comments,
                "average_rating": round(avg_rating, 2),
                "average_popularity_score": round(avg_popularity, 3),
                "collection_name": self.vector_collection,
            }

        except Exception as e:
            print(f"❌ Error getting collection stats: {e}")
            return {}


# Utility functions
def demo_social_interactions(data_store: MultiModelDataStore):
    """Add some demo social interactions for testing"""

    # Get a few recipe IDs from the collection
    try:
        scroll_result = data_store.qdrant_client.scroll(
            collection_name=data_store.vector_collection,
            limit=3,
            with_payload=True,
            with_vectors=False,
        )

        if not scroll_result or not scroll_result[0]:
            print("No recipes found for demo interactions")
            return

        recipe_ids = [point.payload["recipe_id"] for point in scroll_result[0]]

        # Add demo comments
        for i, recipe_id in enumerate(recipe_ids):
            comment = Comment(
                comment_id=f"demo_comment_{i}",
                recipe_id=recipe_id,
                user_id=f"demo_user_{i % 2}",
                text=f"This recipe was {'amazing' if i % 2 == 0 else 'pretty good'}! Would definitely make again.",
                rating=5.0 if i % 2 == 0 else 4.0,
                timestamp=datetime.now(),
            )

            data_store.add_comment(comment)

        print(f"✅ Added demo comments to {len(recipe_ids)} recipes")

    except Exception as e:
        print(f"❌ Error adding demo interactions: {e}")


if __name__ == "__main__":
    # Demo the multi-model data store
    print("🚀 Testing Multi-Model Data Store")

    try:
        # Initialize data store
        data_store = MultiModelDataStore()

        # Show stats
        stats = data_store.get_collection_stats()
        print(f"📊 Collection Stats: {stats}")

        # Add demo social interactions if there are recipes
        if stats.get("vector_embeddings", 0) > 0:
            demo_social_interactions(data_store)

            # Show updated stats
            updated_stats = data_store.get_collection_stats()
            print(f"📊 Updated Stats: {updated_stats}")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
