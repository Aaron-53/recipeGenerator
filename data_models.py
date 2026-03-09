"""
Enhanced Data Models for Multi-Model Recipe Recommendation System

This module defines the comprehensive data structures for:
- Recipe storage with vector embeddings, metadata, and social data
- User profiles with inventory, constraints, and behavioral vectors  
- Social interactions (ratings, comments)
- Retrieval and recommendation data structures
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import numpy as np


@dataclass
class RecipeMetadata:
    """Structured metadata for hard filtering"""
    allergies: List[str] = field(default_factory=list)  # ["nuts", "dairy", "gluten"]
    ingredients: List[str] = field(default_factory=list)  # ["chicken", "milk", "flour"]
    dietary_tags: List[str] = field(default_factory=list)  # ["vegetarian", "low-carb", "keto"]
    cuisine_type: str = ""  # "italian", "mexican", "asian"
    cooking_time_minutes: Optional[int] = None
    difficulty_level: str = "medium"  # "easy", "medium", "hard"
    serving_size: Optional[int] = None
    calories_per_serving: Optional[int] = None


@dataclass
class SocialData:
    """Social graph data for popularity scoring"""
    recipe_id: str
    average_rating: float = 0.0
    total_ratings: int = 0
    total_comments: int = 0
    popularity_score: float = 0.0  # Calculated field
    recent_ratings: List[float] = field(default_factory=list)  # Last 10 ratings
    
    def calculate_popularity_score(self) -> float:
        """Calculate popularity score based on ratings and engagement"""
        if self.total_ratings == 0:
            return 0.0
        
        # Weighted average with recency bias
        rating_score = self.average_rating / 5.0  # Normalize to 0-1
        engagement_score = min(1.0, (self.total_ratings + self.total_comments) / 50.0)
        
        # Recent activity bonus
        recent_bonus = 0.0
        if len(self.recent_ratings) >= 3:
            recent_avg = sum(self.recent_ratings[-10:]) / len(self.recent_ratings[-10:])
            if recent_avg >= 4.0:
                recent_bonus = 0.1
        
        self.popularity_score = (rating_score * 0.6) + (engagement_score * 0.3) + recent_bonus
        return self.popularity_score


@dataclass
class Comment:
    """Individual comment data"""
    comment_id: str
    recipe_id: str
    user_id: str
    text: str
    rating: float  # 1-5 stars
    timestamp: datetime
    helpful_votes: int = 0


@dataclass
class EnhancedRecipe:
    """Complete recipe with all three data views"""
    # Core data
    recipe_id: str
    title: str
    text: str  # Full recipe text for embedding
    original_index: Optional[int] = None
    
    # Vector view
    embedding: Optional[List[float]] = None
    
    # Metadata view (for hard filtering)
    metadata: RecipeMetadata = field(default_factory=RecipeMetadata)
    
    # Social graph view
    social: Optional[SocialData] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class UserInventory:
    """User's current kitchen inventory"""
    user_id: str
    ingredients: Dict[str, float] = field(default_factory=dict)  # ingredient -> quantity
    last_updated: datetime = field(default_factory=datetime.now)
    
    def has_ingredient(self, ingredient: str, required_amount: float = 1.0) -> bool:
        """Check if user has enough of an ingredient"""
        available = self.ingredients.get(ingredient.lower(), 0.0)
        return available >= required_amount
    
    def calculate_inventory_match(self, required_ingredients: List[str]) -> float:
        """Calculate percentage of ingredients user has (0.0 to 1.0)"""
        if not required_ingredients:
            return 1.0
        
        available_count = sum(1 for ing in required_ingredients if self.has_ingredient(ing))
        return available_count / len(required_ingredients)


@dataclass
class UserConstraints:
    """User's dietary constraints and preferences"""
    user_id: str
    never_items: List[str] = field(default_factory=list)  # Allergies/dislikes
    always_items: List[str] = field(default_factory=list)  # Dietary preferences
    cuisine_preferences: List[str] = field(default_factory=list)
    max_cooking_time: Optional[int] = None
    difficulty_preference: str = "any"  # "easy", "medium", "hard", "any"
    calorie_limit: Optional[int] = None


@dataclass
class UserBehavioralVector:
    """User's taste profile from past interactions"""
    user_id: str
    taste_vector: Optional[List[float]] = None  # Average of liked recipe vectors
    liked_recipe_ids: List[str] = field(default_factory=list)
    disliked_recipe_ids: List[str] = field(default_factory=list)
    total_interactions: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_taste_profile(self, recipe_embedding: List[float], rating: float):
        """Update taste profile based on new rating"""
        if rating >= 4.0:  # Liked recipe
            if self.taste_vector is None:
                self.taste_vector = recipe_embedding.copy()
            else:
                # Weighted average with existing profile
                weight = 0.1  # How much new recipes influence the profile
                self.taste_vector = [
                    (1 - weight) * old + weight * new 
                    for old, new in zip(self.taste_vector, recipe_embedding)
                ]
            
        self.total_interactions += 1
        self.last_updated = datetime.now()


@dataclass
class UserProfile:
    """Complete user profile encompassing all dimensions"""
    user_id: str
    username: str
    
    # Three key dimensions
    inventory: UserInventory
    constraints: UserConstraints  
    behavioral: UserBehavioralVector
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)


@dataclass
class StructuredSearchObject:
    """Transformed user query for retrieval pipeline"""
    # Original query
    original_query: str
    user_id: str
    
    # Transformed components
    search_vector: Optional[List[float]] = None  # Embedding of query
    exclusion_filter: List[str] = field(default_factory=list)  # Hard exclusions
    preference_boost: List[str] = field(default_factory=list)  # Preferred ingredients/cuisines
    
    # Search parameters
    max_cooking_time: Optional[int] = None
    difficulty_filter: Optional[str] = None
    cuisine_filter: Optional[str] = None
    
    # Query metadata
    query_timestamp: datetime = field(default_factory=datetime.now)
    query_type: str = "general"  # "quick", "specific_ingredient", "cuisine", etc.


@dataclass
class ScoredRecipe:
    """Recipe with comprehensive scoring for ranking"""
    recipe: EnhancedRecipe
    
    # Individual score components
    similarity_score: float = 0.0  # Semantic similarity to query
    inventory_match_score: float = 0.0  # How many ingredients user has
    quality_score: float = 0.0  # Average rating from comments
    popularity_score: float = 0.0  # Social engagement score
    behavioral_match_score: float = 0.0  # Match to user's taste profile
    
    # Final combined score
    total_score: float = 0.0
    
    # Scoring weights (can be user-customized)
    weights: Dict[str, float] = field(default_factory=lambda: {
        'similarity': 0.25,
        'inventory': 0.25,
        'quality': 0.20,
        'popularity': 0.15,
        'behavioral': 0.15
    })
    
    def calculate_total_score(self) -> float:
        """Calculate weighted total score"""
        self.total_score = (
            self.similarity_score * self.weights['similarity'] +
            self.inventory_match_score * self.weights['inventory'] +
            self.quality_score * self.weights['quality'] +
            self.popularity_score * self.weights['popularity'] +
            self.behavioral_match_score * self.weights['behavioral']
        )
        return self.total_score


@dataclass
class RecommendationResult:
    """Final recommendation with explanation"""
    scored_recipes: List[ScoredRecipe]
    user_query: StructuredSearchObject
    
    # Explanation components
    why_recommended: List[str] = field(default_factory=list)
    missing_ingredients: Dict[str, List[str]] = field(default_factory=dict)  # recipe_id -> missing
    substitution_suggestions: Dict[str, List[str]] = field(default_factory=dict)
    
    # Metadata
    total_recipes_considered: int = 0
    retrieval_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class UserInteraction:
    """Track user interactions for feedback loop"""
    interaction_id: str
    user_id: str
    recipe_id: str
    interaction_type: str  # "view", "rate", "cook", "save", "share"
    
    # Interaction data
    rating: Optional[float] = None
    comment: Optional[str] = None
    ingredients_used: Optional[List[str]] = None  # For "cook" interactions
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Context
    query_context: Optional[str] = None  # What they searched for
    recommendation_rank: Optional[int] = None  # Where this recipe was in results


# Utility functions for data conversion and validation
class DataModelUtils:
    """Utility functions for working with the data models"""
    
    @staticmethod
    def recipe_to_dict(recipe: EnhancedRecipe) -> Dict[str, Any]:
        """Convert recipe to dictionary for storage"""
        return {
            'recipe_id': recipe.recipe_id,
            'title': recipe.title,
            'text': recipe.text,
            'original_index': recipe.original_index,
            'embedding': recipe.embedding,
            'allergies': recipe.metadata.allergies,
            'ingredients': recipe.metadata.ingredients,
            'dietary_tags': recipe.metadata.dietary_tags,
            'cuisine_type': recipe.metadata.cuisine_type,
            'cooking_time_minutes': recipe.metadata.cooking_time_minutes,
            'difficulty_level': recipe.metadata.difficulty_level,
            'serving_size': recipe.metadata.serving_size,
            'calories_per_serving': recipe.metadata.calories_per_serving,
            'created_at': recipe.created_at.isoformat(),
            'updated_at': recipe.updated_at.isoformat()
        }
    
    @staticmethod
    def dict_to_recipe(data: Dict[str, Any]) -> EnhancedRecipe:
        """Convert dictionary back to recipe object"""
        metadata = RecipeMetadata(
            allergies=data.get('allergies', []),
            ingredients=data.get('ingredients', []),
            dietary_tags=data.get('dietary_tags', []),
            cuisine_type=data.get('cuisine_type', ''),
            cooking_time_minutes=data.get('cooking_time_minutes'),
            difficulty_level=data.get('difficulty_level', 'medium'),
            serving_size=data.get('serving_size'),
            calories_per_serving=data.get('calories_per_serving')
        )
        
        return EnhancedRecipe(
            recipe_id=data['recipe_id'],
            title=data['title'],
            text=data['text'],
            original_index=data.get('original_index'),
            embedding=data.get('embedding'),
            metadata=metadata,
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        )
    
    @staticmethod
    def generate_recipe_id() -> str:
        """Generate unique recipe ID"""
        return f"recipe_{uuid.uuid4().hex[:12]}"
    
    @staticmethod
    def generate_user_id() -> str:
        """Generate unique user ID"""
        return f"user_{uuid.uuid4().hex[:8]}"
        
    @staticmethod
    def normalize_ingredient_name(ingredient: str) -> str:
        """Normalize ingredient names for consistent matching"""
        return ingredient.lower().strip().replace(' ', '_')