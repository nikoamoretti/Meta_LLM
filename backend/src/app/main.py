from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import leaderboards, leaderboards_v3, composite_scoring_v3

app = FastAPI(title="Meta-LLM API", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://meta-llm.ai", "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leaderboards.router, prefix="/api")
app.include_router(leaderboards_v3.router, prefix="/api/v3")
app.include_router(composite_scoring_v3.router, prefix="/api/v3")

@app.get("/")
def root():
    return {"message": "Meta-LLM API running"} 