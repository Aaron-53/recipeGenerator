#!/usr/bin/env python3
"""Build dual embeddings from JSON records and store them in Qdrant.

Input requirement:
- JSON file containing an array of objects
- every object must include `desc_embedding_text` and `ing_embedding_text`

Behavior:
- embed `desc_embedding_text` into `desc_vector`
- embed `ing_embedding_text` into `ing_vector`
- store all other keys unchanged in payload
"""

import json
import os
import sys
import time
from typing import Any, Dict, Iterable, List

import torch
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer


MODEL_NAME = "BAAI/bge-base-en-v1.5"
EMBEDDING_SIZE = 768

DEFAULT_QDRANT_HOST = "localhost"
DEFAULT_QDRANT_PORT = 6333
DEFAULT_COLLECTION = "recipe_embeddings_dual"

MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 2
MAX_BACKOFF_SECONDS = 20





def load_records(path: str, limit: int = 0) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON input must be a list of objects")

    if limit > 0:
        data = data[:limit]
    return data


def make_client(host: str, port: int) -> QdrantClient:
    return QdrantClient(host=host, port=port, timeout=60)


def ensure_collection(client: QdrantClient, collection: str) -> None:
    try:
        client.scroll(
            collection_name=collection,
            limit=1,
            with_payload=False,
            with_vectors=False,
        )
        print(f"Collection '{collection}' already exists")
        return
    except Exception:
        pass

    print(f"Creating collection '{collection}' with named vectors")
    client.create_collection(
        collection_name=collection,
        vectors_config={
            "desc_vector": VectorParams(size=EMBEDDING_SIZE, distance=Distance.COSINE),
            "ing_vector": VectorParams(size=EMBEDDING_SIZE, distance=Distance.COSINE),
        },
    )


def upsert_with_retry(
    client: QdrantClient, collection: str, points: List[PointStruct]
) -> None:
    backoff = RETRY_DELAY_SECONDS
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            client.upsert(collection_name=collection, points=points, wait=True)
            return
        except (ResponseHandlingException, Exception) as exc:
            if attempt == MAX_RETRIES:
                raise
            print(
                f"Upsert failed (attempt {attempt}/{MAX_RETRIES}): {exc}. "
                f"Retrying in {backoff}s..."
            )
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)


def batch_iter(items: List[Dict[str, Any]], batch_size: int) -> Iterable[List[Dict[str, Any]]]:
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def main() -> int:
    # Hardcoded configuration
    INPUT_FILE = "/Users/elena/MINI/ratings/recipeGenerator/vector db/test3.json"
    COLLECTION_NAME = "recipe_embeddings_dual"
    QDRANT_HOST = "localhost"
    QDRANT_PORT = 6333
    BATCH_SIZE = 512
    LIMIT = 0  # 0 = process all records

    if not os.path.exists(INPUT_FILE):
        print(f"Input file not found: {INPUT_FILE}")
        return 1

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME, device=device)

    print(f"Loading records from: {INPUT_FILE}")
    records = load_records(INPUT_FILE, limit=LIMIT)
    print(f"Loaded {len(records)} records")
    if not records:
        print("No records found. Nothing to process.")
        return 0

    client = make_client(QDRANT_HOST, QDRANT_PORT)
    ensure_collection(client, COLLECTION_NAME)

    total_upserted = 0

    for batch_index, batch in enumerate(batch_iter(records, BATCH_SIZE), start=1):
        desc_texts: List[str] = []
        ing_texts: List[str] = []
        prepared_payloads: List[Dict[str, Any]] = []
        point_ids: List[Any] = []

        for local_idx, record in enumerate(batch):
            if not isinstance(record, dict):
                raise ValueError("Each item in input array must be a JSON object")

            if "desc_embedding_text" not in record or "ing_embedding_text" not in record:
                raise ValueError(
                    "Each record must contain 'desc_embedding_text' and 'ing_embedding_text'"
                )

            desc_text = str(record["desc_embedding_text"])
            ing_text = str(record["ing_embedding_text"])

            absolute_idx = total_upserted + local_idx
            point_id = record.get("id")
            if point_id is None or str(point_id).strip() == "":
                point_id = absolute_idx

            payload = dict(record)

            point_ids.append(point_id)
            prepared_payloads.append(payload)
            desc_texts.append(desc_text)
            ing_texts.append(ing_text)

        desc_vectors = model.encode(
            desc_texts,
            batch_size=min(128, BATCH_SIZE),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        ing_vectors = model.encode(
            ing_texts,
            batch_size=min(128, BATCH_SIZE),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        points: List[PointStruct] = []
        for i, payload in enumerate(prepared_payloads):
            point = PointStruct(
                id=point_ids[i],
                vector={
                    "desc_vector": desc_vectors[i].tolist(),
                    "ing_vector": ing_vectors[i].tolist(),
                },
                payload=payload,
            )
            points.append(point)

        upsert_with_retry(client, COLLECTION_NAME, points)
        total_upserted += len(points)
        print(
            f"Batch {batch_index}: upserted {len(points)} points "
            f"(total: {total_upserted}/{len(records)})"
        )

        del desc_vectors
        del ing_vectors

    # Use scroll as a lightweight compatibility-safe check after upsert.
    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=1,
        with_payload=False,
        with_vectors=False,
    )
    print("Done")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Upserted in this run: {total_upserted}")
    print(f"Collection reachable: {points is not None}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
