import os
import sys
from pathlib import Path
from langchain_chroma import Chroma

# Set up sys.path for importing app modules when running directly
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from app.core.embeddings import get_embeddings

def get_db_path() -> str:
    """
    Resolves the absolute path to the 'data/processed_index' directory.
    vector_store.py is at: rag-web-app/backend/app/database/vector_store.py
    """
    current_file = Path(__file__).resolve()
    workspace_root = current_file.parent.parent.parent.parent
    db_path = workspace_root / "data" / "processed_index"
    return str(db_path.resolve())

def get_vector_store(collection_name: str = "candidates") -> Chroma:
    """
    Returns the Chroma vector store instance.
    Automatically connects to the local database stored in data/processed_index/.
    """
    embeddings = get_embeddings()
    persist_dir = get_db_path()
    
    print(f"Connecting to ChromaDB at: {persist_dir}")
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_dir
    )
