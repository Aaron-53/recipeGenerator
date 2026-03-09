# Test semantic search fix
from multi_model_data_store import MultiModelDataStore
import numpy as np

print("Testing semantic search fix...")
try:
    data_store = MultiModelDataStore()
    print("✅ Data store initialized successfully")

    # Test with dummy user profile and query vector
    class DummyProfile:
        class DummyConstraints:
            never_items = []
            max_cooking_time = None
            difficulty_preference = "any"
            cuisine_preferences = []
            always_items = []

        constraints = DummyConstraints()

    dummy_profile = DummyProfile()
    dummy_vector = np.random.random(768).tolist()

    print("Testing semantic search...")
    results = data_store.semantic_search(
        query_vector=dummy_vector, user_profile=dummy_profile, limit=2
    )

    print(f"✅ Semantic search completed, found {len(results)} results")
    if results:
        print(f"First result type: {type(results[0])}")
        print(f"First result has payload: {hasattr(results[0], 'payload')}")
        print(f"First result has score: {hasattr(results[0], 'score')}")
        if hasattr(results[0], "payload"):
            payload_keys = list(results[0].payload.keys())[:3]
            print(f"Sample payload keys: {payload_keys}")

except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback

    traceback.print_exc()
