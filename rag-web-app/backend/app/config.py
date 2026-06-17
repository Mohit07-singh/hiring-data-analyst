import os
from pathlib import Path
from dotenv import load_dotenv

# config.py is located at backend/app/config.py
# backend/ is two levels up
base_dir = Path(__file__).resolve().parent.parent
env_path = base_dir / ".env"

# Load environment variables
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    CHROMA_DB_DIR: str = os.getenv("CHROMA_DB_DIR", "../../data/processed_index")

    @property
    def db_absolute_path(self) -> str:
        """
        Returns the absolute path to the database directory.
        Resolves path relative to the app/ directory.
        """
        app_dir = Path(__file__).resolve().parent
        return str((app_dir / self.CHROMA_DB_DIR).resolve())

settings = Settings()
