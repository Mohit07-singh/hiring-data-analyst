from langchain_community.embeddings import HuggingFaceEmbeddings

# Global cache for the embedding model to avoid reloading it multiple times
_embeddings_instance = None

def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Loads and returns the local SentenceTransformers embedding model.
    Uses 'all-MiniLM-L6-v2' (384 dimensions) running on CPU.
    """
    global _embeddings_instance
    if _embeddings_instance is None:
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        print(f"Loading local embedding model '{model_name}' (this may take a moment on first run)...")
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}  # Standardizes vectors for cosine similarity
        )
        print("Embedding model loaded successfully.")
    return _embeddings_instance

if __name__ == "__main__":
    # Test script to verify embedding generation works
    model = get_embeddings()
    test_text = "React developer with 3 years of experience from BITS Goa."
    
    print(f"\nEncoding test sentence: '{test_text}'")
    vector = model.embed_query(test_text)
    
    print("\n--- Embedding Vector Metadata ---")
    print(f"Vector Dimensions: {len(vector)}")
    print(f"First 10 values: {vector[:10]}")
    print("...")
