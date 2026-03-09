# Multi-Model Recipe Recommendation System

A sophisticated recipe recommendation system implementing a **Composite Indexing Strategy** with three distinct data views, user profiling, and intelligent learning capabilities.

## 🏗️ System Architecture

### 1. The Multi-Model Data Store
A comprehensive three-layer architecture that goes beyond standard vector databases:

#### **Vector Embedding Layer** 
- High-dimensional representations capturing the "soul" of recipes
- Powered by BGE (BAAI General Embedding) model
- Stored in Qdrant vector database for efficient semantic similarity

#### **Metadata Layer**
- Structured, searchable fields for hard filtering
- Allergies, ingredients, dietary tags, cuisine types, cooking times
- Enables SQL-like "Safety Gate" filtering before AI processing

#### **Social Graph Layer**
- Comments, ratings, and popularity scoring
- Linked by recipe_id for comprehensive social data
- Calculates dynamic popularity scores to break ties

### 2. The User Profile Engine
The "Brain" that stays outside the Vector DB, tracking users across three dimensions:

#### **Inventory Snapshot**
- Real-time kitchen inventory with quantities
- Automatic consumption tracking when recipes are made  
- Ingredient freshness decay simulation

#### **Constraint Profile** 
- "Never" items (allergies) for safety filtering
- "Always" items (dietary preferences)
- Cooking time and difficulty preferences

#### **Behavioral Vector**
- Dynamic taste profile from 4+ star recipe ratings
- Averages embeddings of liked recipes
- Continuously refined with user interactions

### 3. The 4-Step Retrieval Pipeline

#### **Step A: Query Transformation**
- LLM converts natural language → Structured Search Object
- Extracts time constraints, ingredients, cuisine preferences
- Generates query embedding for semantic matching

#### **Step B: Hard Filtering (Safety Gate)**
- Database-level allergen exclusion (100% safety guarantee)
- Time, difficulty, and cuisine constraints
- Applied before vector search for efficiency

#### **Step C: Semantic Retrieval & Scoring**
Comprehensive scoring formula with 5 weighted components:
- **Similarity Score** (25%): Semantic match to query + user taste profile
- **Inventory Match** (25%): Percentage of ingredients user owns
- **Quality Score** (20%): Average rating from social data
- **Popularity Score** (15%): Social engagement metrics
- **Behavioral Match** (15%): Cosine similarity to user's taste vector

#### **Step D: RAG "Chef" Generation**
- Top 3 recipes with context sent to LLM
- Generates explanations with ingredient analysis
- Suggests substitutions for missing ingredients
- Incorporates user comments and ratings

### 4. The Feedback Loop System
Continuous learning from every interaction:

#### **Inventory Updates**
- Automatic ingredient consumption when cooking
- Freshness decay over time
- Smart quantity tracking

#### **Profile Learning**
- 4+ star ratings strengthen taste profile
- Recipe vectors averaged into behavioral embedding
- Ingredient preferences detected from patterns

#### **Social Updates**
- New ratings affect recipe popularity scores
- Comment sentiment influences recommendations  
- Community learning benefits all users

## 📊 Mathematical Foundation

### Scoring Formula
```
Total Score = Σ(Component_i × Weight_i)

Where:
- Similarity: cosine(query_vector, recipe_vector) 
- Inventory: |user_ingredients ∩ recipe_ingredients| / |recipe_ingredients|
- Quality: (average_rating - 1) / 4 × confidence_factor
- Popularity: f(ratings_count, comments_count, recent_activity)
- Behavioral: cosine(user_taste_vector, recipe_vector)
```

### Learning Rate
```
New_Taste_Vector = (1-α) × Old_Vector + α × Recipe_Vector
Where α = 0.1 (configurable learning rate)
```

## 🚀 Quick Start

### Prerequisites
1. **Python 3.8+**
2. **Qdrant Vector Database** 
   ```bash
   # Start Qdrant (Docker)
   docker run -p 6333:6333 qdrant/qdrant
   ```

### Installation
```bash
# Install dependencies 
pip install -r requirements.txt

# Setup Qdrant
python qdrant_setup.py start

# Process your recipe dataset
python embedding.py  # Embeds recipes into vector database
```

### Usage

#### Interactive Mode
```bash
python main_application.py
```

#### Quick Demo  
```bash
python main_application.py demo
```

## 🎮 Interactive Commands

### User Management
```bash
create_user <username>    # Create new account
login <username>          # Login existing user
logout                    # Logout current user
```

### Recipe Discovery
```bash  
search <query>           # "quick chicken dinner"
rate <index> <stars>     # rate 1 4.5
cook <index>             # Mark as cooked, updates inventory
```

### Profile Management
```bash
inventory               # Add ingredients with quantities
allergy <allergen>      # Add allergen (nuts, dairy, etc.)
insights               # View learning progress & recommendations
```

## 🎯 Business Logic Summary

| Requirement | Architectural Component | Implementation |
|-------------|------------------------|----------------|
| **Allergies** | Metadata Filtering | Boolean exclusion at DB level |
| **Inventory** | Post-Retrieval Scoring | Mathematical overlap calculation (A ∩ B) |  
| **Taste/Vibe** | Vector Similarity | Cosine similarity between query + user vectors |
| **User Profile** | Relational Database | SQLite with interaction history |
| **Social Data** | Aggregation Layer | Comments → ratings → popularity scores |
| **Learning** | Feedback Loop | Vector averaging + constraint updating |

---

*Built with ❤️ for food lovers who want AI that truly understands their taste*

```bash
# Process recipes and create embeddings
python embedding.py
```

**What this does:**

- Loads recipe data from `rag_documents.json` or `RecipeNLG_dataset.csv`
- Generates 768-dimensional embeddings using BAAI/BGE model
- Uploads vectors to Qdrant in batches
- **Resumable**: Can continue if interrupted
- **Progress tracking**: Shows completion status

**Processing time estimates:**

- 1,000 recipes: ~2-5 minutes
- 10,000 recipes: ~20-30 minutes
- 100,000+ recipes: ~2-4 hours

### Step 5: Search Recipes

```bash
# Start interactive recipe search
python qdrant_query.py
```

**Example searches:**

- "spicy chicken curry"
- "chocolate dessert recipes"
- "healthy vegetarian meals"
- "quick 15-minute dinners"

### Step 6: Stop Everything

```bash
# Stop Qdrant container
python qdrant_setup.py stop
```

## 📁 Project Files

```
miniProj/
├── embedding.py                # Generate embeddings from recipe data
├── qdrant_query.py            # Interactive recipe search tool
├── qdrant_setup.py            # Docker container management (start/stop only)
├── requirements.txt           # Python dependencies
├── rag_documents.json         # Recipe data (JSON format)
├── RecipeNLG_dataset.csv      # Recipe data (CSV format)
├── qdrant_storage/            # Persistent vector database (auto-created)
└── embedding_progress.json    # Processing progress (auto-created)
```

## 🔄 Typical Workflow

```bash
# 1. Setup environment (one time)
conda create -n recipe-search python=3.10 -y
conda activate recipe-search
pip install -r requirements.txt

# 2. Start database
python qdrant_setup.py start

# 3. Process your recipe data
python embedding.py

# 4. Search recipes
python qdrant_query.py

# 5. Stop when done
python qdrant_setup.py stop
```

## 🔧 Configuration

### Embedding Settings (`embedding.py`)

```python
CHUNK_SIZE = 10000           # Process N recipes at a time
QDRANT_BATCH_SIZE = 1000    # Upload N vectors per batch
COLLECTION_NAME = "recipe_embeddings"
EMBEDDING_SIZE = 768        # BGE model dimension
```

### Search Settings (`qdrant_query.py`)

```python
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "recipe_embeddings"
```

## 💾 Data Persistence

- **Vectors**: Stored in `qdrant_storage/` directory
- **Progress**: Tracked in `embedding_progress.json`
- **Container restart**: Data persists automatically
- **Transfer**: Copy `qdrant_storage/` folder to move data

## ⚡ Performance Tips

**GPU Acceleration:**

- Install CUDA-compatible PyTorch for faster embedding generation
- Automatic GPU detection and usage

**Batch Size Tuning:**

- **Large RAM**: Increase `CHUNK_SIZE` to 20000+
- **Limited RAM**: Decrease `CHUNK_SIZE` to 5000
- **Slow uploads**: Decrease `QDRANT_BATCH_SIZE` to 500

**Resume Processing:**

- If interrupted, just run `python embedding.py` again
- Automatically continues from last successful batch

## 🐳 Docker Commands

```bash
# Manual Docker management (if needed)
docker ps                           # Check running containers
docker stop qdrant_local           # Stop Qdrant
docker start qdrant_local          # Start existing container
docker logs qdrant_local           # View container logs
```

## 🚨 Troubleshooting

### Docker Issues

```bash
# Check if Docker is running
docker --version

# Restart Docker Desktop (Windows/Mac)
# Or restart Docker service (Linux)
sudo systemctl restart docker
```

### Port Conflicts

```bash
# Check what's using port 6333
netstat -an | findstr 6333        # Windows
lsof -i :6333                     # Mac/Linux

# Use different port in scripts if needed
```

### Memory Issues

```bash
# Reduce batch sizes in embedding.py
CHUNK_SIZE = 5000
QDRANT_BATCH_SIZE = 500
```

### Connection Errors

```bash
# Verify Qdrant is running
curl http://localhost:6333/

# Check container status
docker ps | grep qdrant
```

## 📊 Expected Results

- **Collection**: `recipe_embeddings`
- **Vector size**: 768 dimensions
- **Distance metric**: Cosine similarity
- **Search speed**: <100ms per query
- **Storage**: ~3KB per recipe

## 🎯 Next Steps

1. **Custom Data**: Replace `rag_documents.json` with your recipe data
2. **Advanced Search**: Modify filters in `qdrant_query.py`
3. **Batch Processing**: Increase batch sizes for better performance
4. **Production**: Scale with Qdrant Cloud for larger datasets

---

**🍳 Happy recipe searching!** Your semantic recipe database is ready to use.
