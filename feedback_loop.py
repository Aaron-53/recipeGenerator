"""
Feedback Loop System - The Learning Process

This module implements the comprehensive feedback loop that learns from user interactions:
1. Inventory Updates: Automatically adjust user inventory based on cooking activities
2. Profile Shift: Update user's taste profile vector based on ratings and interactions
3. Social Updates: Index new ratings/comments to influence future recommendations
4. Behavioral Learning: Continuous improvement of recommendation accuracy

The system processes four types of interactions:
- View: User looked at a recipe
- Rate: User rated a recipe (1-5 stars)
- Cook: User made a recipe (consumes ingredients)
- Save: User bookmarked a recipe for later
"""

import json
import sqlite3
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import numpy as np
from dataclasses import asdict

from data_models import (
    UserInteraction,
    EnhancedRecipe,
    Comment,
    UserProfile,
    ScoredRecipe,
    DataModelUtils,
)
from multi_model_data_store import MultiModelDataStore
from user_profile_engine import UserProfileEngine
from retrieval_pipeline import RetrievalPipeline


class FeedbackLoopSystem:
    """Manages all learning and adaptation from user interactions"""

    def __init__(
        self,
        data_store: MultiModelDataStore,
        user_engine: UserProfileEngine,
        analytics_db_path: str = "feedback_analytics.db",
    ):
        """Initialize the feedback loop system"""

        self.data_store = data_store
        self.user_engine = user_engine
        self.analytics_db_path = analytics_db_path

        # Learning parameters
        self.taste_profile_learning_rate = (
            0.1  # How much new ratings affect taste profile
        )
        self.inventory_decay_rate = 0.95  # Daily decay for ingredient freshness
        self.engagement_threshold = 3  # Minimum interactions for reliable patterns

        self._init_analytics_database()
        print("✅ Feedback loop system initialized")

    def _init_analytics_database(self):
        """Initialize analytics database for tracking learning metrics"""
        conn = sqlite3.connect(self.analytics_db_path)
        cursor = conn.cursor()

        # Interaction patterns analysis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interaction_patterns (
                user_id TEXT,
                interaction_date DATE,
                total_views INTEGER DEFAULT 0,
                total_ratings INTEGER DEFAULT 0,
                total_cooks INTEGER DEFAULT 0,
                average_rating REAL DEFAULT 0.0,
                preferred_cuisine TEXT,
                preferred_difficulty TEXT,
                avg_cooking_time INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, interaction_date)
            )
        """)

        # Learning effectiveness tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_metrics (
                user_id TEXT,
                measurement_date DATE,
                taste_profile_confidence REAL DEFAULT 0.0,
                recommendation_accuracy REAL DEFAULT 0.0,
                inventory_match_improvement REAL DEFAULT 0.0,
                engagement_score REAL DEFAULT 0.0,
                total_interactions INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, measurement_date)
            )
        """)

        # Recipe performance tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_performance (
                recipe_id TEXT,
                measurement_date DATE,
                total_views INTEGER DEFAULT 0,
                total_ratings INTEGER DEFAULT 0,
                average_rating REAL DEFAULT 0.0,
                cook_rate REAL DEFAULT 0.0,
                repeat_rate REAL DEFAULT 0.0,
                PRIMARY KEY (recipe_id, measurement_date)
            )
        """)

        conn.commit()
        conn.close()

    # Main Interaction Processing
    def process_interaction(self, interaction: UserInteraction) -> Dict[str, Any]:
        """Process a user interaction and update all relevant systems"""

        start_time = datetime.now()
        results = {
            "interaction_id": interaction.interaction_id,
            "processed_at": start_time.isoformat(),
            "updates_made": [],
            "errors": [],
        }

        try:
            # Log the interaction
            self.user_engine.log_interaction(interaction)
            results["updates_made"].append("interaction_logged")

            # Process based on interaction type
            if interaction.interaction_type == "view":
                self._process_view_interaction(interaction, results)

            elif interaction.interaction_type == "rate":
                self._process_rating_interaction(interaction, results)

            elif interaction.interaction_type == "cook":
                self._process_cooking_interaction(interaction, results)

            elif interaction.interaction_type == "save":
                self._process_save_interaction(interaction, results)

            # Update daily pattern analytics
            self._update_interaction_patterns(interaction)
            results["updates_made"].append("analytics_updated")

            # Check for learning opportunities
            learning_updates = self._check_learning_opportunities(interaction.user_id)
            results["updates_made"].extend(learning_updates)

            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            results["processing_time_ms"] = processing_time

            print(
                f"✅ Processed {interaction.interaction_type} interaction in {processing_time:.1f}ms"
            )

        except Exception as e:
            error_msg = f"Failed to process interaction: {e}"
            results["errors"].append(error_msg)
            print(f"❌ {error_msg}")

        return results

    def _process_view_interaction(self, interaction: UserInteraction, results: Dict):
        """Process a recipe view - lightweight analytics only"""
        # Views are passive - just track for engagement patterns
        # No immediate profile updates needed
        pass

    def _process_rating_interaction(self, interaction: UserInteraction, results: Dict):
        """Process a recipe rating - major learning opportunity"""

        if interaction.rating is None:
            results["errors"].append("Rating interaction missing rating value")
            return

        try:
            # Get recipe for embedding
            recipe = self.data_store.get_enhanced_recipe(interaction.recipe_id)
            if not recipe or not recipe.embedding:
                results["errors"].append(
                    f"Recipe {interaction.recipe_id} not found or missing embedding"
                )
                return

            # Update user's taste profile
            self.user_engine.update_taste_profile(
                interaction.user_id,
                recipe.embedding,
                interaction.rating,
                interaction.recipe_id,
            )
            results["updates_made"].append("taste_profile_updated")

            # Add rating to social data
            comment = Comment(
                comment_id=f"rating_{interaction.interaction_id}",
                recipe_id=interaction.recipe_id,
                user_id=interaction.user_id,
                text=interaction.comment or f"Rated {interaction.rating} stars",
                rating=interaction.rating,
                timestamp=interaction.timestamp,
            )

            self.data_store.add_comment(comment)
            results["updates_made"].append("social_data_updated")

            # Check for ingredient preference learning
            if interaction.rating >= 4.0:
                self._learn_ingredient_preferences(interaction.user_id, recipe)
                results["updates_made"].append("ingredient_preferences_learned")

            print(f"📊 Processed rating: {interaction.rating} stars for {recipe.title}")

        except Exception as e:
            results["errors"].append(f"Rating processing error: {e}")

    def _process_cooking_interaction(self, interaction: UserInteraction, results: Dict):
        """Process a cooking interaction - inventory and engagement updates"""

        try:
            # Get recipe to determine ingredient usage
            recipe = self.data_store.get_enhanced_recipe(interaction.recipe_id)
            if not recipe:
                results["errors"].append(f"Recipe {interaction.recipe_id} not found")
                return

            # Use provided ingredients or recipe ingredients
            ingredients_used = (
                interaction.ingredients_used or recipe.metadata.ingredients
            )

            # Update inventory (remove used ingredients)
            self.user_engine.consume_ingredients(
                interaction.user_id, ingredients_used, interaction.recipe_id
            )
            results["updates_made"].append("inventory_updated")

            # If user cooked it, assume they liked it (implicit positive feedback)
            implied_rating = 4.0  # Cooking implies satisfaction

            if recipe.embedding:
                self.user_engine.update_taste_profile(
                    interaction.user_id,
                    recipe.embedding,
                    implied_rating,
                    interaction.recipe_id,
                )
                results["updates_made"].append("implicit_preference_learned")

            # Track cooking success
            self._track_recipe_success(interaction.recipe_id, "cooked")
            results["updates_made"].append("recipe_performance_tracked")

            print(
                f"🍳 Processed cooking: {recipe.title} (used {len(ingredients_used)} ingredients)"
            )

        except Exception as e:
            results["errors"].append(f"Cooking processing error: {e}")

    def _process_save_interaction(self, interaction: UserInteraction, results: Dict):
        """Process a save/bookmark interaction - mild positive signal"""

        try:
            # Get recipe for mild taste profile update
            recipe = self.data_store.get_enhanced_recipe(interaction.recipe_id)
            if recipe and recipe.embedding:
                # Saving implies mild interest (weaker than cooking/high rating)
                implied_rating = 3.5

                self.user_engine.update_taste_profile(
                    interaction.user_id,
                    recipe.embedding,
                    implied_rating,
                    interaction.recipe_id,
                )
                results["updates_made"].append("mild_preference_learned")

            print(
                f"💾 Processed save: {recipe.title if recipe else interaction.recipe_id}"
            )

        except Exception as e:
            results["errors"].append(f"Save processing error: {e}")

    # Learning and Pattern Detection
    def _learn_ingredient_preferences(self, user_id: str, recipe: EnhancedRecipe):
        """Learn user's ingredient preferences from highly rated recipes"""

        # Get user profile
        profile = self.user_engine.get_user_profile(user_id)
        if not profile:
            return

        # Add ingredients to user's "always_items" if they appear frequently in liked recipes
        liked_count = len(profile.behavioral.liked_recipe_ids)

        if liked_count >= self.engagement_threshold:
            # Check if any ingredients appear in majority of liked recipes
            # This would require analyzing all liked recipes - simplified for now
            common_ingredients = recipe.metadata.ingredients[
                :2
            ]  # Take first 2 as preference indicators

            for ingredient in common_ingredients:
                if ingredient not in profile.constraints.always_items:
                    # Add with low probability to avoid over-learning
                    if (
                        len(profile.constraints.always_items) < 10
                    ):  # Limit preference list
                        profile.constraints.always_items.append(ingredient)

            self.user_engine.update_constraints(user_id, profile.constraints)

    def _check_learning_opportunities(self, user_id: str) -> List[str]:
        """Check for opportunities to improve user's experience"""

        updates = []

        try:
            profile = self.user_engine.get_user_profile(user_id)
            if not profile:
                return updates

            # Check if taste profile needs confidence boost
            if (
                profile.behavioral.total_interactions >= self.engagement_threshold
                and profile.behavioral.taste_vector is not None
            ):
                # Analyze recent interaction patterns for profile refinement
                self._refine_taste_profile(user_id)
                updates.append("taste_profile_refined")

            # Check inventory freshness (decay old ingredients)
            if self._should_decay_inventory(user_id):
                self._apply_inventory_decay(user_id)
                updates.append("inventory_decayed")

            # Check for new dietary preferences to suggest
            new_preferences = self._detect_emerging_preferences(user_id)
            if new_preferences:
                updates.append("emerging_preferences_detected")

        except Exception as e:
            print(f"❌ Learning opportunity check failed: {e}")

        return updates

    def _refine_taste_profile(self, user_id: str):
        """Refine user's taste profile based on recent interactions"""

        # Get recent interactions
        conn = sqlite3.connect(self.user_engine.db_path)
        cursor = conn.cursor()

        try:
            # Get recent ratings (last 30 days)
            cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()

            cursor.execute(
                """
                SELECT recipe_id, rating FROM user_interactions 
                WHERE user_id = ? AND interaction_type = 'rate' 
                AND timestamp > ? 
                ORDER BY timestamp DESC LIMIT 10
            """,
                (user_id, cutoff_date),
            )

            recent_ratings = cursor.fetchall()

            if len(recent_ratings) >= 3:
                # Analyze if taste has shifted
                high_rated_recipes = [
                    recipe_id for recipe_id, rating in recent_ratings if rating >= 4.0
                ]

                if len(high_rated_recipes) >= 2:
                    # Get embeddings for recent favorites
                    recent_vectors = []
                    for recipe_id in high_rated_recipes[:5]:
                        recipe = self.data_store.get_enhanced_recipe(recipe_id)
                        if recipe and recipe.embedding:
                            recent_vectors.append(recipe.embedding)

                    if len(recent_vectors) >= 2:
                        # Calculate average of recent favorites
                        recent_average = np.mean(recent_vectors, axis=0).tolist()

                        # Update taste profile with recent trend
                        profile = self.user_engine.get_user_profile(user_id)
                        if profile.behavioral.taste_vector:
                            # Blend current profile with recent trend
                            blended_vector = [
                                0.8 * current + 0.2 * recent
                                for current, recent in zip(
                                    profile.behavioral.taste_vector, recent_average
                                )
                            ]

                            # Update behavioral data directly in database
                            cursor.execute(
                                """
                                UPDATE user_behavioral SET taste_vector = ?, last_updated = ?
                                WHERE user_id = ?
                            """,
                                (
                                    json.dumps(blended_vector),
                                    datetime.now().isoformat(),
                                    user_id,
                                ),
                            )

                            conn.commit()
                            print(f"🧠 Refined taste profile for user {user_id}")

        finally:
            conn.close()

    def _should_decay_inventory(self, user_id: str) -> bool:
        """Check if inventory needs freshness decay"""

        profile = self.user_engine.get_user_profile(user_id)
        if not profile:
            return False

        # Check if last update was more than 7 days ago
        days_since_update = (datetime.now() - profile.inventory.last_updated).days
        return days_since_update >= 7

    def _apply_inventory_decay(self, user_id: str):
        """Apply decay to inventory to simulate ingredient freshness"""

        profile = self.user_engine.get_user_profile(user_id)
        if not profile:
            return

        decayed_inventory = {}
        for ingredient, quantity in profile.inventory.ingredients.items():
            # Apply decay based on ingredient type (simplified)
            decay_rate = self.inventory_decay_rate

            # Fresh ingredients decay faster
            if any(
                fresh in ingredient for fresh in ["vegetable", "fruit", "meat", "fish"]
            ):
                decay_rate = 0.85

            new_quantity = quantity * decay_rate
            if new_quantity > 0.1:  # Keep if still meaningful amount
                decayed_inventory[ingredient] = new_quantity

        # Update inventory
        self.user_engine.bulk_update_inventory(user_id, decayed_inventory)
        print(f"🥬 Applied inventory decay for user {user_id}")

    def _detect_emerging_preferences(self, user_id: str) -> List[str]:
        """Detect new dietary preferences from user behavior"""

        # Get recent interactions to detect patterns
        conn = sqlite3.connect(self.user_engine.db_path)
        cursor = conn.cursor()

        try:
            # Get recent high-rated recipes
            cursor.execute(
                """
                SELECT recipe_id FROM user_interactions 
                WHERE user_id = ? AND interaction_type = 'rate' 
                AND rating >= 4.0 AND timestamp > ?
                ORDER BY timestamp DESC LIMIT 20
            """,
                (user_id, (datetime.now() - timedelta(days=60)).isoformat()),
            )

            recent_favorites = [row[0] for row in cursor.fetchall()]

            if len(recent_favorites) >= 5:
                # Analyze dietary patterns in favorites
                dietary_counts = {}
                cuisine_counts = {}

                for recipe_id in recent_favorites:
                    recipe = self.data_store.get_enhanced_recipe(recipe_id)
                    if recipe:
                        # Count dietary tags
                        for tag in recipe.metadata.dietary_tags:
                            dietary_counts[tag] = dietary_counts.get(tag, 0) + 1

                        # Count cuisine types
                        if recipe.metadata.cuisine_type:
                            cuisine_counts[recipe.metadata.cuisine_type] = (
                                cuisine_counts.get(recipe.metadata.cuisine_type, 0) + 1
                            )

                # Detect emerging patterns (appearing in 60%+ of recent favorites)
                threshold = len(recent_favorites) * 0.6
                emerging = []

                for tag, count in dietary_counts.items():
                    if count >= threshold:
                        emerging.append(f"dietary:{tag}")

                for cuisine, count in cuisine_counts.items():
                    if count >= threshold:
                        emerging.append(f"cuisine:{cuisine}")

                if emerging:
                    print(
                        f"🎯 Detected emerging preferences for user {user_id}: {emerging}"
                    )

                return emerging

        finally:
            conn.close()

        return []

    # Analytics and Performance Tracking
    def _update_interaction_patterns(self, interaction: UserInteraction):
        """Update daily interaction pattern analytics"""

        conn = sqlite3.connect(self.analytics_db_path)
        cursor = conn.cursor()

        try:
            today = interaction.timestamp.date().isoformat()

            # Get or create today's pattern record
            cursor.execute(
                "SELECT * FROM interaction_patterns WHERE user_id = ? AND interaction_date = ?",
                (interaction.user_id, today),
            )

            existing = cursor.fetchone()

            if existing:
                # Update existing record
                if interaction.interaction_type == "view":
                    cursor.execute(
                        "UPDATE interaction_patterns SET total_views = total_views + 1 WHERE user_id = ? AND interaction_date = ?",
                        (interaction.user_id, today),
                    )
                elif interaction.interaction_type == "rate":
                    cursor.execute(
                        "UPDATE interaction_patterns SET total_ratings = total_ratings + 1 WHERE user_id = ? AND interaction_date = ?",
                        (interaction.user_id, today),
                    )
                elif interaction.interaction_type == "cook":
                    cursor.execute(
                        "UPDATE interaction_patterns SET total_cooks = total_cooks + 1 WHERE user_id = ? AND interaction_date = ?",
                        (interaction.user_id, today),
                    )
            else:
                # Create new record
                views = 1 if interaction.interaction_type == "view" else 0
                ratings = 1 if interaction.interaction_type == "rate" else 0
                cooks = 1 if interaction.interaction_type == "cook" else 0

                cursor.execute(
                    """
                    INSERT INTO interaction_patterns 
                    (user_id, interaction_date, total_views, total_ratings, total_cooks)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (interaction.user_id, today, views, ratings, cooks),
                )

            conn.commit()

        finally:
            conn.close()

    def _track_recipe_success(self, recipe_id: str, success_type: str):
        """Track recipe performance metrics"""

        conn = sqlite3.connect(self.analytics_db_path)
        cursor = conn.cursor()

        try:
            today = datetime.now().date().isoformat()

            # Get or create today's performance record
            cursor.execute(
                "SELECT * FROM recipe_performance WHERE recipe_id = ? AND measurement_date = ?",
                (recipe_id, today),
            )

            if cursor.fetchone():
                # Update existing
                if success_type == "viewed":
                    cursor.execute(
                        "UPDATE recipe_performance SET total_views = total_views + 1 WHERE recipe_id = ? AND measurement_date = ?",
                        (recipe_id, today),
                    )
                elif success_type == "cooked":
                    cursor.execute(
                        "UPDATE recipe_performance SET total_ratings = total_ratings + 1 WHERE recipe_id = ? AND measurement_date = ?",
                        (recipe_id, today),
                    )
            else:
                # Create new
                views = 1 if success_type == "viewed" else 0
                cooks = 1 if success_type == "cooked" else 0

                cursor.execute(
                    """
                    INSERT INTO recipe_performance (recipe_id, measurement_date, total_views, total_ratings)
                    VALUES (?, ?, ?, ?)
                """,
                    (recipe_id, today, views, cooks),
                )

            conn.commit()

        finally:
            conn.close()

    # Batch Processing
    def process_interaction_batch(
        self, interactions: List[UserInteraction]
    ) -> Dict[str, Any]:
        """Process multiple interactions efficiently"""

        start_time = datetime.now()
        results = {
            "total_interactions": len(interactions),
            "successful": 0,
            "failed": 0,
            "processing_time_ms": 0,
            "updates_summary": {},
            "errors": [],
        }

        for interaction in interactions:
            try:
                result = self.process_interaction(interaction)
                if result["errors"]:
                    results["failed"] += 1
                    results["errors"].extend(result["errors"])
                else:
                    results["successful"] += 1

                # Aggregate update types
                for update_type in result["updates_made"]:
                    results["updates_summary"][update_type] = (
                        results["updates_summary"].get(update_type, 0) + 1
                    )

            except Exception as e:
                results["failed"] += 1
                results["errors"].append(
                    f"Interaction {interaction.interaction_id}: {e}"
                )

        results["processing_time_ms"] = (
            datetime.now() - start_time
        ).total_seconds() * 1000

        print(
            f"📊 Batch processed: {results['successful']}/{results['total_interactions']} successful in {results['processing_time_ms']:.1f}ms"
        )

        return results

    # Analytics Queries
    def get_user_learning_progress(
        self, user_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """Get user's learning and engagement progress"""

        conn = sqlite3.connect(self.analytics_db_path)
        cursor = conn.cursor()

        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).date().isoformat()

            # Get interaction patterns
            cursor.execute(
                """
                SELECT SUM(total_views), SUM(total_ratings), SUM(total_cooks)
                FROM interaction_patterns 
                WHERE user_id = ? AND interaction_date >= ?
            """,
                (user_id, cutoff_date),
            )

            interaction_totals = cursor.fetchone()

            # Get user profile for additional insights
            profile = self.user_engine.get_user_profile(user_id)

            return {
                "user_id": user_id,
                "period_days": days,
                "total_views": interaction_totals[0] or 0,
                "total_ratings": interaction_totals[1] or 0,
                "total_cooks": interaction_totals[2] or 0,
                "engagement_score": self._calculate_engagement_score(
                    interaction_totals
                ),
                "has_taste_profile": profile.behavioral.taste_vector is not None
                if profile
                else False,
                "total_liked_recipes": len(profile.behavioral.liked_recipe_ids)
                if profile
                else 0,
                "inventory_items": len(profile.inventory.ingredients) if profile else 0,
                "dietary_constraints": len(profile.constraints.never_items)
                if profile
                else 0,
            }

        finally:
            conn.close()

    def _calculate_engagement_score(self, interaction_totals: Tuple) -> float:
        """Calculate user engagement score from interaction patterns"""

        views, ratings, cooks = [x or 0 for x in interaction_totals]

        # Weight different interaction types
        score = (views * 0.1) + (ratings * 0.4) + (cooks * 0.5)

        # Normalize to 0-10 scale
        return min(10.0, score / 10.0)


# Demo Functions
def demo_feedback_loop():
    """Demonstrate the feedback loop system with simulated interactions"""

    print("🔄 Demo: Feedback Loop System")
    print("=" * 40)

    try:
        # Initialize systems
        data_store = MultiModelDataStore()
        user_engine = UserProfileEngine()
        feedback_system = FeedbackLoopSystem(data_store, user_engine)

        # Get or create demo user
        demo_user = user_engine.get_user_profile("demo_chef_001")
        if not demo_user:
            demo_user = user_engine.create_user("feedback_demo_user")
            user_id = demo_user.user_id
        else:
            user_id = demo_user.user_id

        # Get some recipe IDs for simulation
        try:
            scroll_result = data_store.qdrant_client.scroll(
                collection_name=data_store.vector_collection,
                limit=5,
                with_payload=True,
                with_vectors=False,
            )

            if not scroll_result or not scroll_result[0]:
                print("❌ No recipes found for demo")
                return

            recipe_ids = [point.payload["recipe_id"] for point in scroll_result[0]]

        except Exception as e:
            print(f"❌ Could not get recipe IDs: {e}")
            return

        print(f"👤 Demo user: {user_id}")
        print(f"🥘 Using {len(recipe_ids)} recipes for simulation")
        print()

        # Simulate various interactions
        demo_interactions = []

        # Simulate viewing recipes
        for i, recipe_id in enumerate(recipe_ids):
            interaction = UserInteraction(
                interaction_id=f"demo_view_{i}",
                user_id=user_id,
                recipe_id=recipe_id,
                interaction_type="view",
                timestamp=datetime.now(),
            )
            demo_interactions.append(interaction)

        # Simulate rating some recipes
        ratings = [4.5, 5.0, 3.0, 4.0, 2.0]
        for i, (recipe_id, rating) in enumerate(zip(recipe_ids, ratings)):
            interaction = UserInteraction(
                interaction_id=f"demo_rate_{i}",
                user_id=user_id,
                recipe_id=recipe_id,
                interaction_type="rate",
                rating=rating,
                comment=f"Rating comment for recipe {i + 1}",
                timestamp=datetime.now(),
            )
            demo_interactions.append(interaction)

        # Simulate cooking a highly rated recipe
        interaction = UserInteraction(
            interaction_id="demo_cook_1",
            user_id=user_id,
            recipe_id=recipe_ids[1],  # Second recipe (rated 5.0)
            interaction_type="cook",
            ingredients_used=["chicken", "rice", "onions"],
            timestamp=datetime.now(),
        )
        demo_interactions.append(interaction)

        # Process all interactions
        print("Processing interactions...")
        batch_result = feedback_system.process_interaction_batch(demo_interactions)

        print(
            f"✅ Processed {batch_result['successful']}/{batch_result['total_interactions']} interactions"
        )
        print(f"📊 Updates made: {batch_result['updates_summary']}")

        if batch_result["errors"]:
            print(f"⚠️ Errors: {batch_result['errors'][:3]}...")  # Show first 3 errors

        # Show learning progress
        learning_progress = feedback_system.get_user_learning_progress(user_id)
        print(f"\n📈 Learning Progress:")
        print(f"   Engagement Score: {learning_progress['engagement_score']:.1f}/10")
        print(
            f"   Total Interactions: Views={learning_progress['total_views']}, Ratings={learning_progress['total_ratings']}, Cooks={learning_progress['total_cooks']}"
        )
        print(f"   Has Taste Profile: {learning_progress['has_taste_profile']}")
        print(f"   Liked Recipes: {learning_progress['total_liked_recipes']}")

        # Show updated user profile
        updated_profile = user_engine.get_user_profile(user_id)
        if updated_profile:
            print(f"\n👤 Updated Profile:")
            print(
                f"   Total Interactions: {updated_profile.behavioral.total_interactions}"
            )
            print(
                f"   Liked Recipe Count: {len(updated_profile.behavioral.liked_recipe_ids)}"
            )
            print(f"   Inventory Items: {len(updated_profile.inventory.ingredients)}")

        print("\n✅ Feedback loop demo completed!")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    demo_feedback_loop()
