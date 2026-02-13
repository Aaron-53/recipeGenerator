import json
import torch
from sentence_transformers import SentenceTransformer
import numpy as np
from tqdm import tqdm
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.models import Filter, FieldCondition, MatchValue
from typing import List, Dict, Any
import uuid
import time
import sys
import gc
from qdrant_client.http.exceptions import ResponseHandlingException

# ----------------------------
# Configuration
# ----------------------------
CHUNK_SIZE = 10000  # Process N recipes at a time
QDRANT_BATCH_SIZE = 1000  # Upload N recipes to Qdrant at a time
PROGRESS_FILE = "embedding_progress.json"

# Qdrant Configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "recipe_embeddings"
EMBEDDING_SIZE = 768  # BGE base model embedding dimension

# Connection and retry settings
CONNECTION_TIMEOUT = 60
MAX_RETRIES = 5
RETRY_DELAY = 2  # seconds
BATCH_RETRY_DELAY = 3  # seconds between batch retries
MAX_BACKOFF = 30  # maximum backoff delay

# ----------------------------
# Device setup
# ----------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# ----------------------------
# Load BGE model
# ----------------------------
model = SentenceTransformer("BAAI/bge-base-en-v1.5", device=device)


# ----------------------------
# Qdrant connection functions
# ----------------------------
def create_qdrant_client():
    """Create Qdrant client with timeout settings"""
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=CONNECTION_TIMEOUT)


def test_qdrant_connection(client=None):
    """Test if Qdrant is accessible"""
    if client is None:
        client = create_qdrant_client()

    for attempt in range(MAX_RETRIES):
        try:
            # Simple health check
            collections = client.get_collections()
            print("✅ Qdrant connection successful")
            return True
        except Exception as e:
            print(f"❌ Connection attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"⏳ Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                print("❌ Failed to connect to Qdrant after all retries")
                print("💡 Make sure Qdrant is running: python qdrant_setup.py start")
                return False
    return False


def setup_collection(client):
    """Create collection if it doesn't exist"""
    for attempt in range(MAX_RETRIES):
        try:
            collection_info = client.get_collection(collection_name=COLLECTION_NAME)
            print(f"📁 Collection '{COLLECTION_NAME}' already exists")
            print(f"📊 Current points: {collection_info.points_count}")
            return True
        except Exception as e:
            if "not found" in str(e).lower():
                # Collection doesn't exist, create it
                try:
                    print(f"🔨 Creating collection '{COLLECTION_NAME}'...")
                    client.create_collection(
                        collection_name=COLLECTION_NAME,
                        vectors_config=VectorParams(
                            size=EMBEDDING_SIZE, distance=Distance.COSINE
                        ),
                    )
                    print(f"✅ Collection '{COLLECTION_NAME}' created successfully")
                    return True
                except Exception as create_error:
                    print(
                        f"❌ Failed to create collection (attempt {attempt + 1}): {create_error}"
                    )
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    continue
            else:
                print(f"❌ Error accessing collection (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                continue
    return False


# ----------------------------
# Qdrant client setup
# ----------------------------
print("🔌 Connecting to Qdrant...")
qdrant_client = create_qdrant_client()

# Test connection
if not test_qdrant_connection(qdrant_client):
    print("\n❌ Cannot proceed without Qdrant connection")
    print("Please start Qdrant and try again:")
    print("  python qdrant_setup.py start")
    sys.exit(1)

# Setup collection
if not setup_collection(qdrant_client):
    print("\n❌ Cannot proceed without collection setup")
    sys.exit(1)


# ----------------------------
# Helper functions
# ----------------------------
def save_progress(last_index: int, processed_count: int):
    """Save current progress to file"""
    progress_data = {
        "last_processed_index": last_index,
        "processed_count": processed_count,
    }
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress_data, f, indent=2)
    print(f"Progress saved: {processed_count} recipes processed")


def load_progress():
    """Load existing progress if available"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            progress_data = json.load(f)
        print(f"Resuming from index {progress_data['last_processed_index']}")
        print(f"Already processed: {progress_data['processed_count']} recipes")
        return progress_data["processed_count"], progress_data["last_processed_index"]

    # Check Qdrant for existing data
    try:
        collection_info = qdrant_client.get_collection(collection_name=COLLECTION_NAME)
        existing_count = collection_info.points_count
        if existing_count > 0:
            print(f"Found {existing_count} existing points in Qdrant collection")
            return existing_count, existing_count - 1
    except Exception:
        pass

    return 0, -1


def store_embeddings_to_qdrant(recipes_batch: List[Dict[Any, Any]], start_idx: int):
    """Store a batch of recipes with embeddings to Qdrant with retry logic and sub-batching"""
    global qdrant_client

    total_recipes = len(recipes_batch)
    print(
        f"📦 Processing {total_recipes} recipes in sub-batches of {QDRANT_BATCH_SIZE}..."
    )

    # Process in smaller sub-batches for Qdrant
    for batch_start in range(0, total_recipes, QDRANT_BATCH_SIZE):
        batch_end = min(batch_start + QDRANT_BATCH_SIZE, total_recipes)
        sub_batch = recipes_batch[batch_start:batch_end]

        points = []
        for i, recipe in enumerate(sub_batch):
            point_id = start_idx + batch_start + i
            vector = recipe["embedding"]

            # Create payload with recipe metadata (exclude embedding to save space)
            payload = {
                key: value for key, value in recipe.items() if key != "embedding"
            }
            payload["recipe_index"] = point_id

            point = PointStruct(id=point_id, vector=vector, payload=payload)
            points.append(point)

        # Upload this sub-batch with exponential backoff
        backoff_delay = BATCH_RETRY_DELAY
        for attempt in range(MAX_RETRIES):
            try:
                qdrant_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=points,
                    wait=True,  # Wait for operation to complete
                )
                print(
                    f"✅ Sub-batch {batch_start // QDRANT_BATCH_SIZE + 1}: Stored {len(points)} embeddings"
                )
                break  # Success, move to next sub-batch

            except (ResponseHandlingException, Exception) as e:
                print(
                    f"❌ Sub-batch upload attempt {attempt + 1}/{MAX_RETRIES} failed: {e}"
                )

                if attempt < MAX_RETRIES - 1:
                    print(f"⏳ Retrying in {backoff_delay} seconds...")
                    time.sleep(backoff_delay)

                    # Test and recreate connection if needed
                    if not test_qdrant_connection(qdrant_client):
                        print("🔄 Recreating client connection...")
                        qdrant_client = create_qdrant_client()
                        if not test_qdrant_connection(qdrant_client):
                            print("❌ Cannot re-establish Qdrant connection")
                            return False

                    # Exponential backoff
                    backoff_delay = min(backoff_delay * 2, MAX_BACKOFF)
                else:
                    print(f"❌ Failed to store sub-batch after {MAX_RETRIES} attempts")
                    return False

        # Small delay between sub-batches to prevent overwhelming
        if batch_end < total_recipes:
            time.sleep(0.5)

    print(f"✅ Successfully stored all {total_recipes} embeddings to Qdrant")
    return True


def format_recipe(text):
    """Optional cleanup if needed"""
    return text.strip()


# ----------------------------
# Load recipe dataset
# ----------------------------
print("Loading recipe dataset...")
with open("rag_documents.json", "r", encoding="utf-8") as f:
    recipes = json.load(f)

print(f"Total recipes loaded: {len(recipes)}")

# ----------------------------
# Load existing progress
# ----------------------------
processed_count, last_index = load_progress()
start_index = last_index + 1

if start_index >= len(recipes):
    print("All recipes already processed!")
    print(f"Total recipes in Qdrant: {processed_count}")
    exit()

print(f"Starting from index: {start_index}")
remaining_recipes = recipes[start_index:]
print(f"Remaining recipes to process: {len(remaining_recipes)}")

# ----------------------------
# Process in chunks
# ----------------------------
total_chunks = (len(remaining_recipes) + CHUNK_SIZE - 1) // CHUNK_SIZE
print(f"Processing in {total_chunks} chunks of {CHUNK_SIZE} recipes each")

try:
    for chunk_idx in range(total_chunks):
        chunk_start = chunk_idx * CHUNK_SIZE
        chunk_end = min(chunk_start + CHUNK_SIZE, len(remaining_recipes))
        chunk = remaining_recipes[chunk_start:chunk_end]

        current_index = start_index + chunk_start
        print(f"\n--- Processing chunk {chunk_idx + 1}/{total_chunks} ---")
        print(f"Recipes {current_index} to {current_index + len(chunk) - 1}")

        # Prepare texts for this chunk
        texts = [format_recipe(r["text"]) for r in chunk]

        # Generate embeddings for this chunk
        print("🧠 Generating embeddings...")
        embeddings = model.encode(
            texts,
            batch_size=32,  # Reduced batch size for stability
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        # Attach embeddings to recipes
        for i, recipe in enumerate(chunk):
            recipe["embedding"] = embeddings[i].tolist()

        # Clear embeddings array to free memory
        del embeddings
        gc.collect()

        # Store chunk to Qdrant
        print("📤 Storing embeddings to Qdrant...")
        if not store_embeddings_to_qdrant(chunk, current_index):
            print("❌ Failed to store batch, stopping processing")
            break

        # Update progress tracking (before clearing chunk)
        chunk_size = len(chunk)
        processed_count += chunk_size
        last_processed_index = current_index + chunk_size - 1
        save_progress(last_processed_index, processed_count)

        print(f"Chunk completed. Total processed: {processed_count}/{len(recipes)}")

        # Clear chunk data to free memory
        for recipe in chunk:
            if "embedding" in recipe:
                del recipe["embedding"]
        del chunk
        gc.collect()

    # ----------------------------
    # Final completion
    # ----------------------------
    print("\n=== All chunks completed! ===")

    # Get final stats from Qdrant
    collection_info = qdrant_client.get_collection(collection_name=COLLECTION_NAME)
    total_points = collection_info.points_count

    print(
        f"Successfully stored all embeddings to Qdrant collection '{COLLECTION_NAME}'"
    )
    print(f"Total recipes in Qdrant: {total_points}")
    print(f"Collection stats: {collection_info}")

    # Clean up progress file
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print("Progress file cleaned up")

except (ResponseHandlingException, ConnectionError, Exception) as e:
    error_type = type(e).__name__
    print(f"\n❌ {error_type} occurred: {e}")

    # Provide specific guidance based on error type
    if "connection" in str(e).lower() or "10053" in str(e):
        print("\n🔧 Connection Error Troubleshooting:")
        print("1. Check if Qdrant is running:")
        print("   python qdrant_setup.py status")
        print("2. Test connection:")
        print("   python test_qdrant_connection.py")
        print("3. Reduce batch sizes in script (edit embedding.py):")
        print("   - CHUNK_SIZE = 1000 (currently 10000)")
        print("   - QDRANT_BATCH_SIZE = 50 (currently 100)")
        print("4. Restart Qdrant:")
        print("   python qdrant_setup.py restart")
        print("5. Verify Docker is running and has enough resources")
        print("6. Check Windows Firewall settings")
        print("7. Try running PowerShell as Administrator")
    elif "timeout" in str(e).lower():
        print("\n🔧 Timeout Error Troubleshooting:")
        print("1. Reduce CHUNK_SIZE and QDRANT_BATCH_SIZE in the script")
        print("2. Check system resources (CPU/Memory usage)")
        print("3. Restart Qdrant to clear any locks")
        print("4. Increase Docker memory allocation")

    print(f"\n💾 Progress has been saved. You can resume by running the script again.")
    print(f"📊 Processed so far: {processed_count} recipes")

    # Try to save current progress one more time
    try:
        if "last_processed_index" in locals() and "processed_count" in locals():
            save_progress(last_processed_index, processed_count)
    except:
        pass

    sys.exit(1)
