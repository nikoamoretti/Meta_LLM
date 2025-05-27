# Meta-LLM API Documentation

## Overview
The Meta-LLM API provides programmatic access to aggregated LLM benchmark data.

## Endpoints

### GET /models
Returns all models with their scores across categories.

### GET /models/{model_id}
Returns detailed information for a specific model.

### GET /benchmarks
Returns all available benchmarks and their metadata.

### GET /leaderboards
Returns all tracked leaderboards and their status.

## Authentication
Currently public. Pro tier will require API keys.

## Rate Limits
- Anonymous: 100 requests/hour
- Authenticated: 1000 requests/hour
- Pro: 10000 requests/hour
