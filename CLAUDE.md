# Claude Memory - Meta LLM Project

## Project Overview
Meta LLM is a comprehensive leaderboard aggregator that consolidates AI model performance data from multiple sources into a unified platform. It serves as a "Bloomberg Terminal for AI Models" with advanced composite scoring and professional profiles.

## Key Components
- **Backend**: FastAPI with PostgreSQL database
- **Frontend**: Next.js with TypeScript
- **Database**: PostgreSQL with comprehensive model and benchmark data
- **Scrapers**: Multiple data source integrators (Arena, OpenRouter, HELM, etc.)

## Recent Major Achievements
1. **Task 5.2**: Weighted Composite Scoring - 1,325 composite scores across 5 professional profiles
2. **Task 4.2**: Stanford HELM Classic Integration - 67 models, 943 entries
3. **Task 3.1**: Arena Playwright scraper implementation - 477 model entries

## Development Commands
- Start services: `docker-compose up -d`
- Backend development: `cd backend && uvicorn src.app.main:app --reload`
- Frontend development: `cd frontend && npm run dev`
- Database migrations: `cd backend && alembic upgrade head`

## Current Status
- System fully operational with multiple data sources integrated
- Composite scoring algorithm implemented with statistical validation
- 8 API endpoints for comprehensive data access
- Professional profiles: Coding, Research, Writing, Analysis, General
- **CODING BENCHMARK STATUS**: ✅ FULLY OPERATIONAL
  - Fresh Aider.chat data scraped (47 models with latest scores)
  - All composite scores cleared for clean restart
  - New simple coding API endpoints created and tested
  - NEW FRONTEND: `/simple-models` page displays working coding leaderboard
  - Homepage updated to link to new coding rankings
  - Available endpoints:
    - `/api/v3/coding/raw` - All coding benchmarks (Aider, SWE-Bench, Can-AI-Code)
    - `/api/v3/coding/aider` - Aider.chat leaderboard specifically 
    - `/api/v3/coding/swe-bench` - SWE-Bench Verified leaderboard
    - `/api/v3/coding/model/{name}` - All coding scores for specific model
    - `/api/v3/coding/benchmarks` - Legacy endpoint (still works)
  - Database contains 435 unique models across 3 coding leaderboards
  - Top Aider performers: gemini-2.5-pro (83.1%), o3 (81.3%), Gemini 2.5 Pro (76.9%)

## Architecture Notes
- Modular scraper system with individual adapters
- Automated normalization and quality monitoring
- Research-grade implementation with academic credibility
- Docker containerization for easy deployment