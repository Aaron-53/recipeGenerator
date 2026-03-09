"""
Multi-Model Recipe Recommendation System - Main Application

This is the primary orchestration module that brings together all components:
- Multi-Model Data Store (Vector + Metadata + Social)
- User Profile Engine (Inventory + Constraints + Behavioral)
- Retrieval & Recommendation Pipeline
- Feedback Loop System

Features:
- Interactive recipe recommendations with explanations
- User profile management and learning
- Real-time inventory tracking
- Social interaction processing
- Comprehensive analytics and insights

Usage:
    python main_application.py
"""

import json
import os
import sys
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import traceback

# Import all system components
from data_models import (
    UserProfile,
    EnhancedRecipe,
    UserInteraction,
    StructuredSearchObject,
    RecommendationResult,
    DataModelUtils,
)
from multi_model_data_store import MultiModelDataStore
from user_profile_engine import UserProfileEngine
from retrieval_pipeline import RetrievalPipeline
from feedback_loop import FeedbackLoopSystem


class RecipeRecommendationSystem:
    """Main orchestration class for the complete recommendation system"""

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        vector_collection: str = "recipe_embeddings",
    ):
        """Initialize the complete recommendation system"""

        print("🚀 Initializing Multi-Model Recipe Recommendation System")
        print("=" * 60)

        try:
            # Initialize core components
            print("📊 Initializing Multi-Model Data Store...")
            self.data_store = MultiModelDataStore(
                qdrant_host=qdrant_host,
                qdrant_port=qdrant_port,
                vector_collection=vector_collection,
            )

            print("👤 Initializing User Profile Engine...")
            self.user_engine = UserProfileEngine()

            print("🧠 Initializing Retrieval Pipeline...")
            self.pipeline = RetrievalPipeline(self.data_store, self.user_engine)

            print("🔄 Initializing Feedback Loop System...")
            self.feedback_system = FeedbackLoopSystem(self.data_store, self.user_engine)

            # System state
            self.current_user_id = None
            self.session_interactions = []

            print("✅ System initialization complete!")
            self._show_system_stats()

        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            raise

    def _show_system_stats(self):
        """Display current system statistics"""
        try:
            stats = self.data_store.get_collection_stats()
            print(f"📈 System Stats:")
            print(f"   Vector Database: {stats.get('vector_embeddings', 0)} recipes")
            print(f"   Metadata Records: {stats.get('metadata_records', 0)}")
            print(f"   Total Comments: {stats.get('total_comments', 0)}")
            print(f"   Average Rating: {stats.get('average_rating', 0.0):.2f}/5.0")

            users = self.user_engine.get_all_users()
            print(f"   Registered Users: {len(users)}")
            print()

        except Exception as e:
            print(f"⚠️ Could not load system stats: {e}")

    # User Management
    def create_user_account(self, username: str) -> str:
        """Create a new user account and return user_id"""
        try:
            profile = self.user_engine.create_user(username)
            user_id = profile.user_id

            print(f"✅ Created user account: {username} (ID: {user_id})")
            return user_id

        except Exception as e:
            print(f"❌ Failed to create user account: {e}")
            raise

    def login_user(self, username: str) -> Optional[str]:
        """Login an existing user (simplified - normally would use proper auth)"""
        try:
            users = self.user_engine.get_all_users()

            for user in users:
                if user["username"] == username:
                    self.current_user_id = user["user_id"]
                    print(f"✅ Logged in as {username} (ID: {self.current_user_id})")

                    # Show user summary
                    summary = self.user_engine.get_user_preferences_summary(
                        self.current_user_id
                    )
                    print(
                        f"📊 User Summary: {summary['total_interactions']} interactions, {summary['liked_recipes_count']} liked recipes"
                    )

                    return self.current_user_id

            print(f"❌ User '{username}' not found")
            return None

        except Exception as e:
            print(f"❌ Login failed: {e}")
            return None

    def logout_user(self):
        """Logout current user"""
        if self.current_user_id:
            print(f"👋 Logged out user {self.current_user_id}")
            self.current_user_id = None
            self.session_interactions = []
        else:
            print("No user currently logged in")

    # Inventory Management
    def update_user_inventory(self, ingredients: Dict[str, float]) -> bool:
        """Update user's kitchen inventory"""
        if not self._check_user_logged_in():
            return False

        try:
            self.user_engine.bulk_update_inventory(self.current_user_id, ingredients)
            print(f"✅ Updated inventory: {len(ingredients)} ingredients")
            return True

        except Exception as e:
            print(f"❌ Failed to update inventory: {e}")
            return False

    def add_allergy(self, allergen: str) -> bool:
        """Add an allergen to user's profile"""
        if not self._check_user_logged_in():
            return False

        try:
            self.user_engine.add_allergy(self.current_user_id, allergen)
            print(f"✅ Added allergy: {allergen}")
            return True

        except Exception as e:
            print(f"❌ Failed to add allergy: {e}")
            return False

    def set_dietary_preferences(self, preferences: List[str]) -> bool:
        """Set user's dietary preferences"""
        if not self._check_user_logged_in():
            return False

        try:
            profile = self.user_engine.get_user_profile(self.current_user_id)
            profile.constraints.always_items = preferences
            self.user_engine.update_constraints(
                self.current_user_id, profile.constraints
            )
            print(f"✅ Updated dietary preferences: {preferences}")
            return True

        except Exception as e:
            print(f"❌ Failed to update preferences: {e}")
            return False

    # Core Recommendation Functionality
    def get_recommendations(
        self, query: str, limit: int = 3
    ) -> Optional[RecommendationResult]:
        """Get recipe recommendations for the current user"""
        if not self._check_user_logged_in():
            return None

        try:
            print(f"🔍 Searching for: '{query}'")

            # Get recommendations from pipeline
            result = self.pipeline.recommend_recipes(
                query=query, user_id=self.current_user_id, limit=limit
            )

            # Log the search interaction
            search_interaction = UserInteraction(
                interaction_id=f"search_{self.current_user_id}_{time.time()}",
                user_id=self.current_user_id,
                recipe_id="search_query",  # Special case for search queries
                interaction_type="view",
                query_context=query,
                timestamp=datetime.now(),
            )
            self.session_interactions.append(search_interaction)

            # Display results
            self._display_recommendations(result)

            return result

        except Exception as e:
            print(f"❌ Recommendation failed: {e}")
            return None

    def _display_recommendations(self, result: RecommendationResult):
        """Display recommendations in a user-friendly format"""

        if not result.scored_recipes:
            print("😔 No recipes found matching your criteria")
            print("💡 Try:")
            print("   - Broadening your search terms")
            print("   - Checking your dietary restrictions")
            print("   - Adding more ingredients to your inventory")
            return

        print(f"\n🎯 Found {len(result.scored_recipes)} recommendations:")
        print("=" * 50)

        for i, (scored_recipe, explanation) in enumerate(
            zip(result.scored_recipes, result.why_recommended)
        ):
            recipe = scored_recipe.recipe
            score = scored_recipe.total_score

            print(f"\n{i + 1}. {recipe.title}")
            print(f"   Overall Score: {score:.3f}/1.0")
            print(f"   {explanation}")

            # Show recipe details
            print(
                f"   🕒 Cooking Time: {recipe.metadata.cooking_time_minutes or 'Unknown'} minutes"
            )
            print(f"   📊 Difficulty: {recipe.metadata.difficulty_level}")
            print(f"   🍽️ Cuisine: {recipe.metadata.cuisine_type}")

            # Show social data if available
            if recipe.social and recipe.social.total_ratings > 0:
                print(
                    f"   ⭐ Rating: {recipe.social.average_rating:.1f}/5 ({recipe.social.total_ratings} reviews)"
                )

            # Show inventory match
            missing = result.missing_ingredients.get(recipe.recipe_id, [])
            if missing:
                print(f"   🛒 Need to buy: {', '.join(missing[:3])}")
            else:
                print(f"   ✅ You have all ingredients!")

            print()

        print(f"⚡ Search completed in {result.retrieval_time_ms:.1f}ms")
        print(f"📊 Analyzed {result.total_recipes_considered} recipes")

    # User Interaction Processing
    def rate_recipe(self, recipe_index: int, rating: float, comment: str = "") -> bool:
        """Rate a recipe from current recommendations"""
        if not self._check_user_logged_in():
            return False

        if not hasattr(self, "_last_recommendations") or not self._last_recommendations:
            print("❌ No recent recommendations to rate")
            return False

        try:
            if recipe_index < 1 or recipe_index > len(
                self._last_recommendations.scored_recipes
            ):
                print(
                    f"❌ Invalid recipe index. Choose 1-{len(self._last_recommendations.scored_recipes)}"
                )
                return False

            recipe = self._last_recommendations.scored_recipes[recipe_index - 1].recipe

            # Create rating interaction
            interaction = UserInteraction(
                interaction_id=f"rate_{self.current_user_id}_{recipe.recipe_id}_{time.time()}",
                user_id=self.current_user_id,
                recipe_id=recipe.recipe_id,
                interaction_type="rate",
                rating=rating,
                comment=comment,
                timestamp=datetime.now(),
            )

            # Process through feedback system
            result = self.feedback_system.process_interaction(interaction)

            if not result["errors"]:
                print(f"✅ Rated '{recipe.title}': {rating}/5.0 stars")
                if comment:
                    print(f"💬 Comment: {comment}")
                return True
            else:
                print(f"❌ Rating failed: {result['errors']}")
                return False

        except Exception as e:
            print(f"❌ Rating failed: {e}")
            return False

    def cook_recipe(
        self, recipe_index: int, ingredients_used: Optional[List[str]] = None
    ) -> bool:
        """Mark a recipe as cooked (consumes inventory)"""
        if not self._check_user_logged_in():
            return False

        if not hasattr(self, "_last_recommendations") or not self._last_recommendations:
            print("❌ No recent recommendations to cook")
            return False

        try:
            if recipe_index < 1 or recipe_index > len(
                self._last_recommendations.scored_recipes
            ):
                print(
                    f"❌ Invalid recipe index. Choose 1-{len(self._last_recommendations.scored_recipes)}"
                )
                return False

            recipe = self._last_recommendations.scored_recipes[recipe_index - 1].recipe

            # Use provided ingredients or all recipe ingredients
            used_ingredients = ingredients_used or recipe.metadata.ingredients

            # Create cooking interaction
            interaction = UserInteraction(
                interaction_id=f"cook_{self.current_user_id}_{recipe.recipe_id}_{time.time()}",
                user_id=self.current_user_id,
                recipe_id=recipe.recipe_id,
                interaction_type="cook",
                ingredients_used=used_ingredients,
                timestamp=datetime.now(),
            )

            # Process through feedback system
            result = self.feedback_system.process_interaction(interaction)

            if not result["errors"]:
                print(f"🍳 Cooked '{recipe.title}'!")
                print(
                    f"📦 Used ingredients: {', '.join(used_ingredients[:5])}{'...' if len(used_ingredients) > 5 else ''}"
                )
                print("🧠 Your taste profile has been updated")
                return True
            else:
                print(f"❌ Cooking record failed: {result['errors']}")
                return False

        except Exception as e:
            print(f"❌ Cooking record failed: {e}")
            return False

    # Analytics and Insights
    def show_user_insights(self) -> bool:
        """Show user's learning progress and insights"""
        if not self._check_user_logged_in():
            return False

        try:
            # Get user profile
            profile = self.user_engine.get_user_profile(self.current_user_id)
            if not profile:
                print("❌ Could not load user profile")
                return False

            # Get learning progress
            progress = self.feedback_system.get_user_learning_progress(
                self.current_user_id
            )

            print(f"\n📊 Insights for {profile.username}")
            print("=" * 40)

            # Engagement metrics
            print(f"🎯 Engagement Score: {progress['engagement_score']:.1f}/10")
            print(f"📈 Activity (Last 30 Days):")
            print(f"   👀 Recipe Views: {progress['total_views']}")
            print(f"   ⭐ Ratings Given: {progress['total_ratings']}")
            print(f"   🍳 Recipes Cooked: {progress['total_cooks']}")

            # Profile completeness
            print(f"\n👤 Profile Completeness:")
            print(
                f"   🧠 Taste Profile: {'✅ Active' if progress['has_taste_profile'] else '❌ Learning'}"
            )
            print(f"   ❤️ Liked Recipes: {progress['total_liked_recipes']}")
            print(f"   🥘 Inventory Items: {progress['inventory_items']}")
            print(f"   🚫 Dietary Restrictions: {progress['dietary_constraints']}")

            # Recommendations
            print(f"\n💡 Recommendations:")
            if progress["total_views"] < 10:
                print("   - Explore more recipes to improve recommendations")
            if progress["total_ratings"] < 5:
                print("   - Rate recipes to help us learn your preferences")
            if progress["inventory_items"] < 10:
                print("   - Add more ingredients to your inventory for better matches")
            if not progress["has_taste_profile"]:
                print("   - Rate a few recipes to build your taste profile")

            return True

        except Exception as e:
            print(f"❌ Failed to load insights: {e}")
            return False

    def show_system_analytics(self) -> bool:
        """Show system-wide analytics (admin view)"""
        try:
            print(f"\n📊 System Analytics")
            print("=" * 30)

            # Data store stats
            stats = self.data_store.get_collection_stats()
            print(f"🗄️ Data Store:")
            print(f"   Recipes: {stats.get('vector_embeddings', 0)}")
            print(f"   Comments: {stats.get('total_comments', 0)}")
            print(f"   Avg Rating: {stats.get('average_rating', 0.0):.2f}/5.0")

            # User stats
            users = self.user_engine.get_all_users()
            active_users = [
                u
                for u in users
                if (datetime.now() - datetime.fromisoformat(u["last_active"])).days < 7
            ]

            print(f"👥 Users:")
            print(f"   Total Registered: {len(users)}")
            print(f"   Active (7 days): {len(active_users)}")

            # Top users by activity
            if users:
                top_users = sorted(
                    users,
                    key=lambda x: x["summary"]["total_interactions"],
                    reverse=True,
                )[:3]
                print(f"   Most Active:")
                for i, user in enumerate(top_users, 1):
                    print(
                        f"     {i}. {user['username']}: {user['summary']['total_interactions']} interactions"
                    )

            return True

        except Exception as e:
            print(f"❌ Failed to load analytics: {e}")
            return False

    # Utility Methods
    def _check_user_logged_in(self) -> bool:
        """Check if a user is currently logged in"""
        if not self.current_user_id:
            print("❌ No user logged in. Please login first.")
            return False
        return True

    def quick_demo(self) -> bool:
        """Run a quick demonstration of the system"""
        print("\n🎭 Quick Demo Mode")
        print("=" * 20)

        try:
            # Create demo user if needed
            demo_username = "demo_user_" + str(int(time.time()))
            demo_user_id = self.create_user_account(demo_username)
            self.current_user_id = demo_user_id

            # Add demo inventory
            demo_inventory = {
                "chicken": 2.0,
                "rice": 3.0,
                "onions": 1.0,
                "garlic": 1.0,
                "oil": 1.0,
            }
            self.update_user_inventory(demo_inventory)

            # Add demo allergies
            self.add_allergy("nuts")

            # Set demo preferences
            self.set_dietary_preferences(["healthy", "low_carb"])

            # Get recommendations
            demo_queries = ["quick chicken recipe", "healthy dinner with rice"]

            for query in demo_queries:
                print(f"\n🔍 Demo Query: '{query}'")
                result = self.get_recommendations(query, limit=2)

                if result and result.scored_recipes:
                    # Demo rating
                    print(f"🎭 [Demo] Rating first recipe: 4.5 stars")
                    self.rate_recipe(1, 4.5, "Great demo recipe!")

                    # Demo cooking
                    if len(result.scored_recipes) > 1:
                        print(f"🎭 [Demo] Cooking second recipe")
                        self.cook_recipe(2)

                print()

            # Show insights
            self.show_user_insights()

            print("\n✅ Demo completed successfully!")
            return True

        except Exception as e:
            print(f"❌ Demo failed: {e}")
            traceback.print_exc()
            return False


# Interactive Command Line Interface
def run_interactive_cli():
    """Run interactive command-line interface"""

    print("🍳 Multi-Model Recipe Recommendation System")
    print("Interactive Mode - Type 'help' for commands")
    print("=" * 50)

    try:
        # Initialize system
        system = RecipeRecommendationSystem()

        print("\nType 'help' for available commands, 'quit' to exit")

        while True:
            try:
                command = input("\n> ").strip().lower()

                if command == "quit" or command == "exit":
                    print("👋 Goodbye!")
                    break

                elif command == "help":
                    print_help()

                elif command == "demo":
                    system.quick_demo()

                elif command.startswith("create_user"):
                    parts = command.split(" ", 1)
                    username = parts[1] if len(parts) > 1 else input("Username: ")
                    system.create_user_account(username)

                elif command.startswith("login"):
                    parts = command.split(" ", 1)
                    username = parts[1] if len(parts) > 1 else input("Username: ")
                    system.login_user(username)

                elif command == "logout":
                    system.logout_user()

                elif command.startswith("search"):
                    parts = command.split(" ", 1)
                    query = parts[1] if len(parts) > 1 else input("Search query: ")
                    result = system.get_recommendations(query)
                    system._last_recommendations = result  # Store for rating/cooking

                elif command.startswith("rate"):
                    parts = command.split()
                    if len(parts) >= 3:
                        index = int(parts[1])
                        rating = float(parts[2])
                        comment = " ".join(parts[3:]) if len(parts) > 3 else ""
                        system.rate_recipe(index, rating, comment)
                    else:
                        print("Usage: rate <recipe_index> <rating> [comment]")

                elif command.startswith("cook"):
                    parts = command.split()
                    if len(parts) >= 2:
                        index = int(parts[1])
                        system.cook_recipe(index)
                    else:
                        print("Usage: cook <recipe_index>")

                elif command == "insights":
                    system.show_user_insights()

                elif command == "analytics":
                    system.show_system_analytics()

                elif command.startswith("inventory"):
                    print("Add ingredients to your inventory:")
                    print("Format: ingredient_name:quantity (e.g., chicken:2)")
                    print("Type 'done' to finish")

                    inventory = {}
                    while True:
                        item = input("Add item: ").strip()
                        if item.lower() == "done":
                            break
                        if ":" in item:
                            name, qty = item.split(":", 1)
                            inventory[name.strip()] = float(qty.strip())

                    if inventory:
                        system.update_user_inventory(inventory)

                elif command.startswith("allergy"):
                    parts = command.split(" ", 1)
                    allergen = parts[1] if len(parts) > 1 else input("Allergen: ")
                    system.add_allergy(allergen)

                elif command == "":
                    continue  # Empty command

                else:
                    print("❓ Unknown command. Type 'help' for available commands.")

            except KeyboardInterrupt:
                print("\n👋 Interrupted. Type 'quit' to exit safely.")
            except Exception as e:
                print(f"❌ Command failed: {e}")

    except Exception as e:
        print(f"❌ System startup failed: {e}")
        traceback.print_exc()


def print_help():
    """Print available commands"""
    print("\n📋 Available Commands:")
    print("=" * 30)
    print("🔧 System:")
    print("  help                     - Show this help")
    print("  demo                     - Run quick demo")
    print("  quit/exit               - Exit the system")
    print()
    print("👤 User Management:")
    print("  create_user <username>  - Create new user account")
    print("  login <username>        - Login existing user")
    print("  logout                  - Logout current user")
    print()
    print("🔍 Recipe Search:")
    print("  search <query>          - Search for recipes")
    print("  rate <index> <rating>   - Rate a recipe (1-5 stars)")
    print("  cook <index>            - Mark recipe as cooked")
    print()
    print("🏠 Profile Management:")
    print("  inventory               - Add ingredients to inventory")
    print("  allergy <allergen>      - Add allergen to profile")
    print("  insights                - View your learning progress")
    print()
    print("📊 Analytics:")
    print("  analytics               - View system statistics")


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "demo":
            # Quick demo mode
            try:
                system = RecipeRecommendationSystem()
                system.quick_demo()
            except Exception as e:
                print(f"❌ Demo failed: {e}")

        elif sys.argv[1] == "stats":
            # Show stats only
            try:
                system = RecipeRecommendationSystem()
                system.show_system_analytics()
            except Exception as e:
                print(f"❌ Stats failed: {e}")

        else:
            print("Usage: python main_application.py [demo|stats]")

    else:
        # Interactive mode
        run_interactive_cli()
