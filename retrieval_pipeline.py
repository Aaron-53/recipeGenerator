"""
Retrieval & Recommendation Pipeline

This module implements the sophisticated 4-step execution flow for recipe recommendations:
Step A: Query Transformation - Convert natural language to structured search
Step B: Hard Filtering (Safety Gate) - Database-level safety filtering
Step C: Semantic Retrieval & Scoring - Multi-dimensional scoring system
Step D: RAG "Chef" Generation - LLM-powered final recommendations

The pipeline uses the composite scoring formula:
- Similarity Score: Semantic match to query and user taste profile
- Inventory Match: Percentage of ingredients user owns
- Quality Score: Average rating from social data
- Popularity Score: Social engagement metrics
"""

import json
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np

from sentence_transformers import SentenceTransformer
import torch

from data_models import (
    UserProfile,
    StructuredSearchObject,
    ScoredRecipe,
    RecommendationResult,
    EnhancedRecipe,
    DataModelUtils,
)
from multi_model_data_store import MultiModelDataStore
from user_profile_engine import UserProfileEngine


class RetrievalPipeline:
    """Orchestrates the complete recommendation pipeline"""

    def __init__(
        self,
        data_store: MultiModelDataStore,
        user_engine: UserProfileEngine,
        model_name: str = "BAAI/bge-base-en-v1.5",
    ):
        """Initialize the retrieval pipeline"""

        self.data_store = data_store
        self.user_engine = user_engine

        # Initialize embedding model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(model_name, device=device)
        print(f"🧠 Loaded embedding model on {device}")

        # Scoring weights (can be customized per user)
        self.default_weights = {
            "similarity": 0.25,
            "inventory": 0.25,
            "quality": 0.20,
            "popularity": 0.15,
            "behavioral": 0.15,
        }

        print("✅ Retrieval pipeline initialized")

    def recommend_recipes(
        self, query: str, user_id: str, limit: int = 3, **kwargs
    ) -> RecommendationResult:
        """Main entry point for recipe recommendations"""

        start_time = time.time()

        try:
            # Get user profile
            user_profile = self.user_engine.get_user_profile(user_id)
            if not user_profile:
                raise ValueError(f"User {user_id} not found")

            print(f"🎯 Generating recommendations for user {user_profile.username}")

            # Step A: Query Transformation
            structured_query = self._transform_query(query, user_profile)
            print(f"🔄 Query transformed: {structured_query.query_type}")

            # Step B & C: Hard Filtering + Semantic Retrieval
            scored_recipes = self._retrieve_and_score(
                structured_query, user_profile, limit * 4
            )
            print(f"📊 Retrieved and scored {len(scored_recipes)} candidate recipes")

            # Select top recipes
            top_recipes = scored_recipes[:limit]

            # Step D: Generate explanations
            result = self._generate_recommendations(
                top_recipes, structured_query, user_profile
            )

            result.retrieval_time_ms = (time.time() - start_time) * 1000
            result.total_recipes_considered = len(scored_recipes)

            print(f"✅ Recommendations generated in {result.retrieval_time_ms:.1f}ms")
            return result

        except Exception as e:
            print(f"❌ Recommendation pipeline error: {e}")
            return RecommendationResult(
                scored_recipes=[],
                user_query=StructuredSearchObject(
                    original_query=query, user_id=user_id
                ),
                retrieval_time_ms=(time.time() - start_time) * 1000,
            )

    # Step A: Query Transformation
    def _transform_query(
        self, query: str, user_profile: UserProfile
    ) -> StructuredSearchObject:
        """Transform natural language query into structured search object"""

        query_lower = query.lower()

        # Analyze query type and extract parameters
        query_type = "general"
        max_cooking_time = None
        difficulty_filter = None
        cuisine_filter = None
        preference_boost = []

        # Time-based queries
        if any(word in query_lower for word in ["quick", "fast", "minutes", "short"]):
            query_type = "quick"
            max_cooking_time = 30

        elif any(word in query_lower for word in ["slow", "long", "hours", "all day"]):
            max_cooking_time = 180

        # Difficulty detection
        if any(word in query_lower for word in ["easy", "simple", "beginner"]):
            difficulty_filter = "easy"
        elif any(word in query_lower for word in ["hard", "complex", "advanced"]):
            difficulty_filter = "hard"

        # Cuisine detection
        cuisines = [
            "italian",
            "mexican",
            "asian",
            "chinese",
            "indian",
            "french",
            "mediterranean",
            "american",
        ]
        for cuisine in cuisines:
            if cuisine in query_lower:
                cuisine_filter = cuisine
                query_type = "cuisine"
                break

        # Ingredient-based queries
        if any(word in query_lower for word in ["with", "using", "have"]):
            query_type = "specific_ingredient"
            # Extract potential ingredients (this could be enhanced with NER)
            for ingredient in user_profile.inventory.ingredients.keys():
                if ingredient.replace("_", " ") in query_lower:
                    preference_boost.append(ingredient)

        # Generate query embedding
        query_embedding = self.model.encode(
            query, convert_to_numpy=True, normalize_embeddings=True
        ).tolist()

        # Build structured query
        structured_query = StructuredSearchObject(
            original_query=query,
            user_id=user_profile.user_id,
            search_vector=query_embedding,
            exclusion_filter=user_profile.constraints.never_items.copy(),
            preference_boost=preference_boost,
            max_cooking_time=max_cooking_time,
            difficulty_filter=difficulty_filter,
            cuisine_filter=cuisine_filter,
            query_type=query_type,
        )

        return structured_query

    # Step B & C: Hard Filtering + Semantic Retrieval
    def _retrieve_and_score(
        self,
        structured_query: StructuredSearchObject,
        user_profile: UserProfile,
        retrieval_limit: int = 20,
    ) -> List[ScoredRecipe]:
        """Retrieve recipes with hard filtering and apply comprehensive scoring"""

        # Perform semantic search with hard filtering
        search_results = self.data_store.semantic_search(
            query_vector=structured_query.search_vector,
            user_profile=user_profile,
            limit=retrieval_limit,
            max_cooking_time=structured_query.max_cooking_time,
            cuisine_filter=structured_query.cuisine_filter,
            difficulty_filter=structured_query.difficulty_filter,
        )

        if not search_results:
            print("⚠️ No recipes found matching search criteria")
            return []

        # Score each recipe
        scored_recipes = []
        for result in search_results:
            # Use the actual Qdrant point ID for retrieval
            point_id = str(result.id)  # Convert point ID to string

            # Extract string recipe_id from payload for metadata lookup
            if "recipe_id" in result.payload:
                payload_recipe_id = result.payload["recipe_id"]
            elif "id" in result.payload:
                payload_recipe_id = result.payload["id"]
            else:
                print(
                    f"⚠️ No recipe identifier found in payload: {list(result.payload.keys())}"
                )
                continue

            # Get enhanced recipe using point ID, but pass payload recipe_id for metadata lookup
            enhanced_recipe = self.data_store.get_enhanced_recipe_by_point(
                point_id=point_id,
                payload_recipe_id=payload_recipe_id,
                point_data=result,
            )
            if not enhanced_recipe:
                continue

            # Create scored recipe
            scored_recipe = ScoredRecipe(
                recipe=enhanced_recipe, weights=self.default_weights.copy()
            )

            # Calculate individual scores
            self._calculate_similarity_score(
                scored_recipe, result.score, structured_query, user_profile
            )
            self._calculate_inventory_score(scored_recipe, user_profile)
            self._calculate_quality_score(scored_recipe)
            self._calculate_popularity_score(scored_recipe)
            self._calculate_behavioral_score(scored_recipe, user_profile)

            # Apply preference boosting
            if structured_query.preference_boost:
                self._apply_preference_boost(
                    scored_recipe, structured_query.preference_boost
                )

            # Calculate final score
            scored_recipe.calculate_total_score()
            scored_recipes.append(scored_recipe)

        # Sort by total score (highest first)
        scored_recipes.sort(key=lambda x: x.total_score, reverse=True)

        return scored_recipes

    def _calculate_similarity_score(
        self,
        scored_recipe: ScoredRecipe,
        base_similarity: float,
        structured_query: StructuredSearchObject,
        user_profile: UserProfile,
    ):
        """Calculate semantic similarity score"""
        # Base similarity from Qdrant search (already 0-1)
        scored_recipe.similarity_score = base_similarity

    def _calculate_inventory_score(
        self, scored_recipe: ScoredRecipe, user_profile: UserProfile
    ):
        """Calculate inventory match score"""
        required_ingredients = scored_recipe.recipe.metadata.ingredients
        if not required_ingredients:
            scored_recipe.inventory_match_score = 1.0
            return

        # Calculate percentage of ingredients user has
        match_score = user_profile.inventory.calculate_inventory_match(
            required_ingredients
        )
        scored_recipe.inventory_match_score = match_score

    def _calculate_quality_score(self, scored_recipe: ScoredRecipe):
        """Calculate quality score from social data"""
        social = scored_recipe.recipe.social
        if not social or social.total_ratings == 0:
            scored_recipe.quality_score = 0.5  # Neutral score for unrated recipes
            return

        # Normalize rating (1-5 scale to 0-1 scale)
        normalized_rating = (social.average_rating - 1) / 4

        # Apply confidence factor based on number of ratings
        confidence_factor = min(
            1.0, social.total_ratings / 10.0
        )  # Full confidence at 10+ ratings
        scored_recipe.quality_score = normalized_rating * confidence_factor

    def _calculate_popularity_score(self, scored_recipe: ScoredRecipe):
        """Calculate popularity score from social engagement"""
        social = scored_recipe.recipe.social
        if not social:
            scored_recipe.popularity_score = 0.0
            return

        # Use the pre-calculated popularity score from social data
        scored_recipe.popularity_score = social.popularity_score

    def _calculate_behavioral_score(
        self, scored_recipe: ScoredRecipe, user_profile: UserProfile
    ):
        """Calculate behavioral match score using user's taste profile"""
        behavioral = user_profile.behavioral

        if not behavioral.taste_vector or not scored_recipe.recipe.embedding:
            scored_recipe.behavioral_match_score = 0.5  # Neutral for new users
            return

        # Calculate cosine similarity between user taste profile and recipe
        taste_vector = np.array(behavioral.taste_vector)
        recipe_vector = np.array(scored_recipe.recipe.embedding)

        # Normalize vectors
        taste_norm = np.linalg.norm(taste_vector)
        recipe_norm = np.linalg.norm(recipe_vector)

        if taste_norm == 0 or recipe_norm == 0:
            scored_recipe.behavioral_match_score = 0.5
            return

        # Cosine similarity (result is -1 to 1, normalize to 0 to 1)
        cosine_sim = np.dot(taste_vector, recipe_vector) / (taste_norm * recipe_norm)
        normalized_sim = (cosine_sim + 1) / 2

        scored_recipe.behavioral_match_score = normalized_sim

    def _apply_preference_boost(
        self, scored_recipe: ScoredRecipe, preferred_ingredients: List[str]
    ):
        """Boost score for recipes containing preferred ingredients"""
        recipe_ingredients = [
            ing.lower() for ing in scored_recipe.recipe.metadata.ingredients
        ]

        matches = sum(
            1 for pref in preferred_ingredients if pref.lower() in recipe_ingredients
        )
        if matches > 0:
            boost = min(0.15, matches * 0.05)  # Up to 15% boost
            scored_recipe.total_score = min(1.0, scored_recipe.total_score + boost)

    # Step D: RAG "Chef" Generation
    def _generate_recommendations(
        self,
        scored_recipes: List[ScoredRecipe],
        structured_query: StructuredSearchObject,
        user_profile: UserProfile,
    ) -> RecommendationResult:
        """Generate final recommendations with explanations"""

        recommendations = []
        missing_ingredients = {}
        substitution_suggestions = {}

        for i, scored_recipe in enumerate(scored_recipes):
            recipe = scored_recipe.recipe

            # Generate explanation
            explanation_parts = []

            # Primary reason for recommendation
            if scored_recipe.similarity_score > 0.8:
                explanation_parts.append("excellent match for your search")
            elif scored_recipe.behavioral_match_score > 0.7:
                explanation_parts.append("fits your taste preferences perfectly")
            elif scored_recipe.inventory_match_score > 0.8:
                explanation_parts.append("you have most of the ingredients")
            else:
                explanation_parts.append("good overall match")

            # Inventory analysis
            missing_ings = []
            for ingredient in recipe.metadata.ingredients:
                if not user_profile.inventory.has_ingredient(ingredient):
                    missing_ings.append(ingredient)

            if missing_ings:
                missing_ingredients[recipe.recipe_id] = missing_ings
                if len(missing_ings) == 1:
                    explanation_parts.append(f"you only need to get {missing_ings[0]}")
                elif len(missing_ings) <= 3:
                    explanation_parts.append(
                        f"you need {', '.join(missing_ings[:2])} {'and ' + missing_ings[2] if len(missing_ings) == 3 else ''}"
                    )
            else:
                explanation_parts.append("you have all the ingredients")

            # Quality indicators
            if recipe.social and recipe.social.average_rating >= 4.5:
                explanation_parts.append("highly rated by other users")
            elif recipe.social and recipe.social.recent_ratings:
                recent_avg = sum(recipe.social.recent_ratings[-5:]) / len(
                    recipe.social.recent_ratings[-5:]
                )
                if recent_avg >= 4.5:
                    explanation_parts.append("getting great recent reviews")

            # Time considerations
            if (
                recipe.metadata.cooking_time_minutes
                and recipe.metadata.cooking_time_minutes <= 20
            ):
                explanation_parts.append("quick to make")
            elif (
                structured_query.query_type == "quick"
                and recipe.metadata.cooking_time_minutes
                and recipe.metadata.cooking_time_minutes <= 30
            ):
                explanation_parts.append("fits your time constraint")

            # Create combined explanation
            explanation = (
                f"I suggest {recipe.title} because it's "
                + ", ".join(explanation_parts[:3])
                + "."
            )

            # Add comments insight if available
            comments = self.data_store.get_recipe_comments(recipe.recipe_id, limit=3)
            if comments:
                positive_comments = [c for c in comments if c.rating >= 4.0]
                if positive_comments:
                    comment_text = positive_comments[0].text[:100]
                    explanation += f" Users mention: '{comment_text}...'"

            recommendations.append(explanation)

        return RecommendationResult(
            scored_recipes=scored_recipes,
            user_query=structured_query,
            why_recommended=recommendations,
            missing_ingredients=missing_ingredients,
            substitution_suggestions=substitution_suggestions,
        )

    # Utility Methods
    def explain_scoring(self, scored_recipe: ScoredRecipe) -> Dict[str, Any]:
        """Get detailed scoring breakdown for debugging"""
        return {
            "recipe_title": scored_recipe.recipe.title,
            "total_score": round(scored_recipe.total_score, 4),
            "similarity_score": round(scored_recipe.similarity_score, 4),
            "inventory_match_score": round(scored_recipe.inventory_match_score, 4),
            "quality_score": round(scored_recipe.quality_score, 4),
            "popularity_score": round(scored_recipe.popularity_score, 4),
            "behavioral_match_score": round(scored_recipe.behavioral_match_score, 4),
            "weights": scored_recipe.weights,
            "ingredient_count": len(scored_recipe.recipe.metadata.ingredients),
            "social_data": {
                "average_rating": scored_recipe.recipe.social.average_rating
                if scored_recipe.recipe.social
                else None,
                "total_ratings": scored_recipe.recipe.social.total_ratings
                if scored_recipe.recipe.social
                else 0,
            },
        }

    def batch_recommend(
        self, queries: List[str], user_id: str, limit: int = 3
    ) -> List[RecommendationResult]:
        """Process multiple queries efficiently"""

        results = []
        for query in queries:
            result = self.recommend_recipes(query, user_id, limit)
            results.append(result)

        return results


class QueryAnalyzer:
    """Advanced query analysis and transformation utilities"""

    @staticmethod
    def extract_ingredients(query: str) -> List[str]:
        """Extract ingredient names from natural language query"""
        # This is a simplified version - could be enhanced with NER models
        common_ingredients = [
            "chicken",
            "beef",
            "pork",
            "fish",
            "shrimp",
            "rice",
            "pasta",
            "noodles",
            "tomato",
            "onion",
            "garlic",
            "potato",
            "carrot",
            "cheese",
            "milk",
            "egg",
            "oil",
            "butter",
            "salt",
            "pepper",
            "herb",
            "spice",
        ]

        query_lower = query.lower()
        found_ingredients = []

        for ingredient in common_ingredients:
            if ingredient in query_lower:
                found_ingredients.append(ingredient)

        return found_ingredients

    @staticmethod
    def detect_dietary_intent(query: str) -> List[str]:
        """Detect dietary preferences/restrictions in query"""
        dietary_map = {
            "vegetarian": ["vegetarian", "veggie", "no meat"],
            "vegan": ["vegan", "plant based", "no dairy"],
            "gluten_free": ["gluten free", "no gluten", "celiac"],
            "dairy_free": ["dairy free", "no dairy", "lactose free"],
            "low_carb": ["low carb", "keto", "no carbs"],
            "healthy": ["healthy", "nutritious", "clean eating"],
        }

        query_lower = query.lower()
        detected = []

        for dietary, keywords in dietary_map.items():
            if any(keyword in query_lower for keyword in keywords):
                detected.append(dietary)

        return detected

    @staticmethod
    def estimate_urgency(query: str) -> str:
        """Estimate how quickly user needs the recipe"""
        query_lower = query.lower()

        urgent_keywords = ["quick", "fast", "now", "urgent", "minutes"]
        relaxed_keywords = ["slow", "weekend", "leisure", "hours"]

        if any(keyword in query_lower for keyword in urgent_keywords):
            return "urgent"
        elif any(keyword in query_lower for keyword in relaxed_keywords):
            return "relaxed"
        else:
            return "normal"


# Demo and Testing Functions
def demo_pipeline_with_user():
    """Comprehensive demo of the retrieval pipeline"""

    print("🎭 Demo: Recipe Recommendation Pipeline")
    print("=" * 50)

    try:
        # Initialize components
        data_store = MultiModelDataStore()
        user_engine = UserProfileEngine()
        pipeline = RetrievalPipeline(data_store, user_engine)

        # Check if we have data
        stats = data_store.get_collection_stats()
        if stats.get("vector_embeddings", 0) == 0:
            print("❌ No recipes found in database. Please run embedding script first.")
            return

        # Create or get demo user
        try:
            demo_user = user_engine.get_user_profile("demo_chef_001")
            if not demo_user:
                from user_profile_engine import demo_user_setup

                demo_user_id = demo_user_setup()
                demo_user = user_engine.get_user_profile(demo_user_id)
        except:
            demo_user_id = user_engine.create_user("pipeline_demo_user").user_id
            demo_user = user_engine.get_user_profile(demo_user_id)

        # Test queries
        test_queries = [
            "I want something quick for dinner",
            "What can I make with chicken and rice?",
            "Suggest a healthy vegetarian meal",
            "Easy Italian recipe for tonight",
            "Something sweet for dessert",
        ]

        print(f"👤 Testing with user: {demo_user.username} (ID: {demo_user.user_id})")
        print(f"🥘 Available ingredients: {len(demo_user.inventory.ingredients)}")
        print(f"🚫 Allergies: {demo_user.constraints.never_items}")
        print()

        # Process each query
        for i, query in enumerate(test_queries, 1):
            print(f"Query {i}: '{query}'")
            print("-" * 30)

            result = pipeline.recommend_recipes(query, demo_user.user_id, limit=2)

            if result.scored_recipes:
                for j, explanation in enumerate(result.why_recommended):
                    recipe = result.scored_recipes[j].recipe
                    score = result.scored_recipes[j].total_score

                    print(f"  {j + 1}. {recipe.title} (Score: {score:.3f})")
                    print(f"     {explanation}")

                    # Show missing ingredients
                    missing = result.missing_ingredients.get(recipe.recipe_id, [])
                    if missing:
                        print(f"     Missing: {', '.join(missing[:3])}")
                    print()
            else:
                print("  No recommendations found for this query")
                print()

            print(f"  ⏱️ Generated in {result.retrieval_time_ms:.1f}ms")
            print(f"  📊 Considered {result.total_recipes_considered} recipes")
            print()

        print("✅ Demo completed successfully!")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    demo_pipeline_with_user()
