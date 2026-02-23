# Recipe Vector Search System

A complete system for generating recipe embeddings and performing semantic search using Qdrant vector database.

## 🚀 Quick Start Guide

### Step 1: Create Conda Environment

```bash
# Create a new empty conda environment
conda create -n recipe-search python=3.10 -y

# Activate the environment
conda activate recipe-search
```

### Step 2: Install Dependencies

```bash
# Install all required Python packages
pip install -r requirements.txt
```

**Required packages:**

- `requests>=2.25.1` - HTTP client
- `sentence-transformers>=2.2.2` - Text embeddings
- `torch>=2.0.0` - Deep learning framework
- `qdrant-client>=1.7.0` - Vector database client
- `tqdm>=4.64.0` - Progress bars
- `numpy>=1.21.0` - Numerical computing

### Step 3: Start Qdrant Database

```bash
# Start Qdrant using Docker
python qdrant_setup.py start
```

This will:

- ✅ Check if Docker is installed
- ✅ Start Qdrant container on port 6333
- ✅ Create persistent storage directory: `qdrant_storage/`
- ✅ Set up vector database
- 🌐 Dashboard available at: http://localhost:6333/dashboard

### Step 4: Generate Embeddings

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
