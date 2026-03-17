"""
User Profile Engine - The "Brain" outside the Vector DB

This module manages user profiles across three key dimensions:
1. Inventory Snapshot: Real-time kitchen inventory tracking
2. Constraint Profile: Allergies, dietary preferences, and restrictions
3. Behavioral Vector: Dynamic taste profile from past interactions

The engine provides intelligent updates, recommendations, and learning.
"""

import json
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

from data_models import (
    UserProfile,
    UserInventory,
    UserConstraints,
    UserBehavioralVector,
    UserInteraction,
    EnhancedRecipe,
    DataModelUtils,
)


class UserProfileEngine:
    """Manages all user profile operations and learning"""

    def __init__(self, db_path: str = "user_profiles.db"):
        """Initialize the user profile engine with SQLite storage"""
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database for user profiles"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # User inventory table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_inventory (
                user_id TEXT,
                ingredient TEXT,
                quantity REAL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, ingredient),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # User constraints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_constraints (
                user_id TEXT PRIMARY KEY,
                never_items TEXT,  -- JSON list
                always_items TEXT,  -- JSON list
                cuisine_preferences TEXT,  -- JSON list
                max_cooking_time INTEGER,
                difficulty_preference TEXT,
                calorie_limit INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # User behavioral data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_behavioral (
                user_id TEXT PRIMARY KEY,
                taste_vector TEXT,  -- JSON list of floats
                liked_recipe_ids TEXT,  -- JSON list
                disliked_recipe_ids TEXT,  -- JSON list
                total_interactions INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # User interactions log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_interactions (
                interaction_id TEXT PRIMARY KEY,
                user_id TEXT,
                recipe_id TEXT,
                interaction_type TEXT,
                rating REAL,
                comment TEXT,
                ingredients_used TEXT,  -- JSON list
                query_context TEXT,
                recommendation_rank INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        conn.commit()
        conn.close()

    # User Management
    def create_user(self, username: str, user_id: Optional[str] = None) -> UserProfile:
        """Create a new user profile"""
        if user_id is None:
            user_id = DataModelUtils.generate_user_id()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Create user record
            cursor.execute(
                "INSERT INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username),
            )

            # Initialize empty constraints
            cursor.execute(
                "INSERT INTO user_constraints (user_id, never_items, always_items, "
                "cuisine_preferences, difficulty_preference) VALUES (?, ?, ?, ?, ?)",
                (user_id, "[]", "[]", "[]", "any"),
            )

            # Initialize empty behavioral data
            cursor.execute(
                "INSERT INTO user_behavioral (user_id, liked_recipe_ids, "
                "disliked_recipe_ids) VALUES (?, ?, ?)",
                (user_id, "[]", "[]"),
            )

            conn.commit()
            print(f"✅ Created user profile for {username} (ID: {user_id})")

            return self.get_user_profile(user_id)

        except sqlite3.IntegrityError:
            conn.rollback()
            raise ValueError(f"User ID {user_id} already exists")
        finally:
            conn.close()

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Retrieve complete user profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get user basic info
            cursor.execute(
                "SELECT username, created_at, last_active FROM users WHERE user_id = ?",
                (user_id,),
            )
            user_data = cursor.fetchone()

            if not user_data:
                return None

            username, created_at, last_active = user_data

            # Build complete profile
            inventory = self._get_user_inventory(cursor, user_id)
            constraints = self._get_user_constraints(cursor, user_id)
            behavioral = self._get_user_behavioral(cursor, user_id)

            return UserProfile(
                user_id=user_id,
                username=username,
                inventory=inventory,
                constraints=constraints,
                behavioral=behavioral,
                created_at=datetime.fromisoformat(created_at),
                last_active=datetime.fromisoformat(last_active),
            )

        finally:
            conn.close()

    def _get_user_inventory(self, cursor, user_id: str) -> UserInventory:
        """Get user's inventory from database"""
        cursor.execute(
            "SELECT ingredient, quantity FROM user_inventory WHERE user_id = ?",
            (user_id,),
        )

        ingredients = {}
        for ingredient, quantity in cursor.fetchall():
            ingredients[ingredient] = quantity

        return UserInventory(user_id=user_id, ingredients=ingredients)

    def _get_user_constraints(self, cursor, user_id: str) -> UserConstraints:
        """Get user's constraints from database"""
        cursor.execute(
            "SELECT never_items, always_items, cuisine_preferences, max_cooking_time, "
            "difficulty_preference, calorie_limit FROM user_constraints WHERE user_id = ?",
            (user_id,),
        )

        data = cursor.fetchone()
        if not data:
            return UserConstraints(user_id=user_id)

        never_items, always_items, cuisine_prefs, max_time, difficulty, cal_limit = data

        return UserConstraints(
            user_id=user_id,
            never_items=json.loads(never_items or "[]"),
            always_items=json.loads(always_items or "[]"),
            cuisine_preferences=json.loads(cuisine_prefs or "[]"),
            max_cooking_time=max_time,
            difficulty_preference=difficulty or "any",
            calorie_limit=cal_limit,
        )

    def _get_user_behavioral(self, cursor, user_id: str) -> UserBehavioralVector:
        """Get user's behavioral data from database"""
        cursor.execute(
            "SELECT taste_vector, liked_recipe_ids, disliked_recipe_ids, "
            "total_interactions, last_updated FROM user_behavioral WHERE user_id = ?",
            (user_id,),
        )

        data = cursor.fetchone()
        if not data:
            return UserBehavioralVector(user_id=user_id)

        taste_vector, liked_ids, disliked_ids, total_interactions, last_updated = data

        return UserBehavioralVector(
            user_id=user_id,
            taste_vector=json.loads(taste_vector) if taste_vector else None,
            liked_recipe_ids=json.loads(liked_ids or "[]"),
            disliked_recipe_ids=json.loads(disliked_ids or "[]"),
            total_interactions=total_interactions or 0,
            last_updated=datetime.fromisoformat(last_updated)
            if last_updated
            else datetime.now(),
        )

    # Inventory Management
    def update_inventory(self, user_id: str, ingredient: str, quantity: float):
        """Update a single ingredient quantity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT OR REPLACE INTO user_inventory (user_id, ingredient, quantity) "
                "VALUES (?, ?, ?)",
                (
                    user_id,
                    DataModelUtils.normalize_ingredient_name(ingredient),
                    quantity,
                ),
            )
            cursor.execute(
                "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,),
            )
            conn.commit()

        finally:
            conn.close()

    def bulk_update_inventory(self, user_id: str, ingredients: Dict[str, float]):
        """Update multiple ingredients at once"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            for ingredient, quantity in ingredients.items():
                normalized_ingredient = DataModelUtils.normalize_ingredient_name(
                    ingredient
                )
                cursor.execute(
                    "INSERT OR REPLACE INTO user_inventory (user_id, ingredient, quantity) "
                    "VALUES (?, ?, ?)",
                    (user_id, normalized_ingredient, quantity),
                )

            cursor.execute(
                "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,),
            )
            conn.commit()
            print(f"✅ Updated {len(ingredients)} ingredients for user {user_id}")

        finally:
            conn.close()

    def consume_ingredients(
        self, user_id: str, ingredients_used: List[str], recipe_id: str
    ):
        """Reduce inventory based on ingredients used in cooking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            consumed = []
            for ingredient in ingredients_used:
                normalized_ingredient = DataModelUtils.normalize_ingredient_name(
                    ingredient
                )
                cursor.execute(
                    "SELECT quantity FROM user_inventory WHERE user_id = ? AND ingredient = ?",
                    (user_id, normalized_ingredient),
                )
                result = cursor.fetchone()

                if result and result[0] > 0:
                    # Reduce quantity (assuming 1 unit per recipe for simplicity)
                    new_quantity = max(0, result[0] - 1)
                    cursor.execute(
                        "UPDATE user_inventory SET quantity = ? WHERE user_id = ? AND ingredient = ?",
                        (new_quantity, user_id, normalized_ingredient),
                    )
                    consumed.append(ingredient)

            # Log the cooking interaction
            cooking_interaction = UserInteraction(
                interaction_id=f"cook_{user_id}_{recipe_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                recipe_id=recipe_id,
                interaction_type="cook",
                ingredients_used=consumed,
            )
            self.log_interaction(cooking_interaction)

            conn.commit()
            print(f"✅ Consumed ingredients for recipe {recipe_id}: {consumed}")

        finally:
            conn.close()

    # Constraints Management
    def update_constraints(self, user_id: str, constraints: UserConstraints):
        """Update user's dietary constraints and preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE user_constraints SET never_items = ?, always_items = ?, "
                "cuisine_preferences = ?, max_cooking_time = ?, difficulty_preference = ?, "
                "calorie_limit = ? WHERE user_id = ?",
                (
                    json.dumps(constraints.never_items),
                    json.dumps(constraints.always_items),
                    json.dumps(constraints.cuisine_preferences),
                    constraints.max_cooking_time,
                    constraints.difficulty_preference,
                    constraints.calorie_limit,
                    user_id,
                ),
            )
            conn.commit()
            print(f"✅ Updated constraints for user {user_id}")

        finally:
            conn.close()

    def add_allergy(self, user_id: str, allergen: str):
        """Add an allergen to user's never-items list"""
        profile = self.get_user_profile(user_id)
        if profile and allergen not in profile.constraints.never_items:
            profile.constraints.never_items.append(allergen.lower())
            self.update_constraints(user_id, profile.constraints)
            print(f"✅ Added allergy {allergen} for user {user_id}")

    def remove_allergy(self, user_id: str, allergen: str):
        """Remove an allergen from user's never-items list"""
        profile = self.get_user_profile(user_id)
        if profile and allergen.lower() in profile.constraints.never_items:
            profile.constraints.never_items.remove(allergen.lower())
            self.update_constraints(user_id, profile.constraints)
            print(f"✅ Removed allergy {allergen} for user {user_id}")

    # Behavioral Learning
    def update_taste_profile(
        self, user_id: str, recipe_embedding: List[float], rating: float, recipe_id: str
    ):
        """Update user's taste profile based on recipe interaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get current behavioral data
            behavioral = self._get_user_behavioral(cursor, user_id)

            # Update the taste profile
            behavioral.update_taste_profile(recipe_embedding, rating)

            # Update liked/disliked lists
            if rating >= 4.0 and recipe_id not in behavioral.liked_recipe_ids:
                behavioral.liked_recipe_ids.append(recipe_id)
                # Remove from disliked if it was there
                if recipe_id in behavioral.disliked_recipe_ids:
                    behavioral.disliked_recipe_ids.remove(recipe_id)

            elif rating <= 2.0 and recipe_id not in behavioral.disliked_recipe_ids:
                behavioral.disliked_recipe_ids.append(recipe_id)
                # Remove from liked if it was there
                if recipe_id in behavioral.liked_recipe_ids:
                    behavioral.liked_recipe_ids.remove(recipe_id)

            # Save updated behavioral data
            cursor.execute(
                "UPDATE user_behavioral SET taste_vector = ?, liked_recipe_ids = ?, "
                "disliked_recipe_ids = ?, total_interactions = ?, last_updated = ? "
                "WHERE user_id = ?",
                (
                    json.dumps(behavioral.taste_vector)
                    if behavioral.taste_vector
                    else None,
                    json.dumps(behavioral.liked_recipe_ids),
                    json.dumps(behavioral.disliked_recipe_ids),
                    behavioral.total_interactions,
                    behavioral.last_updated.isoformat(),
                    user_id,
                ),
            )

            conn.commit()
            print(f"✅ Updated taste profile for user {user_id} (rating: {rating})")

        finally:
            conn.close()

    # Interaction Logging
    def log_interaction(self, interaction: UserInteraction):
        """Log a user interaction for analytics and learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO user_interactions (interaction_id, user_id, recipe_id, "
                "interaction_type, rating, comment, ingredients_used, query_context, "
                "recommendation_rank, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    interaction.interaction_id,
                    interaction.user_id,
                    interaction.recipe_id,
                    interaction.interaction_type,
                    interaction.rating,
                    interaction.comment,
                    json.dumps(interaction.ingredients_used)
                    if interaction.ingredients_used
                    else None,
                    interaction.query_context,
                    interaction.recommendation_rank,
                    interaction.timestamp.isoformat(),
                ),
            )

            # If this is a rating, update the taste profile
            if interaction.rating is not None and interaction.interaction_type in [
                "rate",
                "cook",
            ]:
                # We'd need the recipe embedding here - this would come from the main system
                pass

            conn.commit()

        finally:
            conn.close()

    # Analytics and Insights
    def get_user_preferences_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user's preferences and activity"""
        profile = self.get_user_profile(user_id)
        if not profile:
            return {}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get interaction stats
            cursor.execute(
                "SELECT interaction_type, COUNT(*) FROM user_interactions "
                "WHERE user_id = ? GROUP BY interaction_type",
                (user_id,),
            )
            interaction_stats = dict(cursor.fetchall())

            # Get recent activity
            cursor.execute(
                "SELECT interaction_type, recipe_id, rating, timestamp "
                "FROM user_interactions WHERE user_id = ? "
                "ORDER BY timestamp DESC LIMIT 10",
                (user_id,),
            )
            recent_activity = cursor.fetchall()

            return {
                "user_id": user_id,
                "username": profile.username,
                "total_ingredients": len(profile.inventory.ingredients),
                "allergies_count": len(profile.constraints.never_items),
                "liked_recipes_count": len(profile.behavioral.liked_recipe_ids),
                "total_interactions": profile.behavioral.total_interactions,
                "interaction_stats": interaction_stats,
                "recent_activity": recent_activity,
                "has_taste_profile": profile.behavioral.taste_vector is not None,
            }

        finally:
            conn.close()

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get summary of all users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT user_id, username, created_at, last_active FROM users "
                "ORDER BY last_active DESC"
            )

            users = []
            for user_id, username, created_at, last_active in cursor.fetchall():
                summary = self.get_user_preferences_summary(user_id)
                users.append(
                    {
                        "user_id": user_id,
                        "username": username,
                        "created_at": created_at,
                        "last_active": last_active,
                        "summary": summary,
                    }
                )

            return users

        finally:
            conn.close()


# Utility functions for user management
def demo_user_setup():
    """Create a demo user with sample data for testing"""
    engine = UserProfileEngine()

    # Create demo user
    profile = engine.create_user("demo_chef")
    user_id = profile.user_id

    # Add sample inventory
    sample_inventory = {
        "chicken": 2.0,
        "rice": 5.0,
        "onions": 3.0,
        "garlic": 1.0,
        "olive_oil": 1.0,
        "salt": 1.0,
        "pepper": 1.0,
        "tomatoes": 4.0,
        "cheese": 1.0,
    }
    engine.bulk_update_inventory(user_id, sample_inventory)

    # Add constraints
    constraints = UserConstraints(
        user_id=user_id,
        never_items=["nuts", "shellfish"],  # Allergies
        always_items=["vegetables"],  # Dietary preference
        cuisine_preferences=["italian", "mediterranean"],
        max_cooking_time=45,
        difficulty_preference="easy",
    )
    engine.update_constraints(user_id, constraints)

    print(f"✅ Demo user created: {user_id}")
    return user_id


if __name__ == "__main__":
    # Demo the user profile engine
    demo_user_id = demo_user_setup()

    engine = UserProfileEngine()
    profile = engine.get_user_profile(demo_user_id)

    if profile:
        print(f"\nUser Profile: {profile.username}")
        print(f"Inventory items: {len(profile.inventory.ingredients)}")
        print(f"Never items: {profile.constraints.never_items}")
        print(f"Always items: {profile.constraints.always_items}")
        print(f"Total interactions: {profile.behavioral.total_interactions}")

    # Get summary
    summary = engine.get_user_preferences_summary(demo_user_id)
    print(f"\nUser Summary: {summary}")
