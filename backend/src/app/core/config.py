import os

# Use SQLite database for development - supports our existing meta_llm.db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meta_llm.db") 