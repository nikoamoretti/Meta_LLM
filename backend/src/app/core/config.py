import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://meta_llm:meta_llm@localhost:5432/meta_llm") 