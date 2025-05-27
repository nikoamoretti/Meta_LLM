#!/usr/bin/env python3
"""
Quick status check after cleanup
"""
import sys
sys.path.append('src')

from scrapers.universal_scraper_v2 import UniversalScraperV2
from scrapers.scraper_config_v2 import WORKING_LEADERBOARDS

print("🔍 Meta-LLM Status Check")
print("=" * 50)

# Check scrapers
print("\n📊 Available Scrapers:")
scraper = UniversalScraperV2()
for key, config in WORKING_LEADERBOARDS.items():
    print(f"  - {config['name']}")

# Test a quick scrape
print("\n🧪 Testing HuggingFace scraper...")
try:
    results = scraper.scrape_leaderboard('huggingface_open_llm')
    if results:
        print(f"  ✅ Success! Found {len(results)} models")
        print(f"  Sample: {results[0]['model'] if results else 'None'}")
    else:
        print("  ⚠️  No results returned")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Check database connection
print("\n💾 Database Status:")
try:
    from app.database import SessionLocal
    db = SessionLocal()
    from db.db_models import Model
    model_count = db.query(Model).count()
    print(f"  ✅ Connected! {model_count} models in database")
    db.close()
except Exception as e:
    print(f"  ❌ Database error: {e}")

# Check API
print("\n🌐 API Status:")
try:
    import requests
    response = requests.get("http://localhost:8000/health", timeout=2)
    if response.status_code == 200:
        print("  ✅ API is running")
    else:
        print(f"  ⚠️  API returned status {response.status_code}")
except:
    print("  ❌ API is not running (start with: cd backend && uvicorn src.main:app --reload)")

print("\n✅ Status check complete!")
print("\n📋 Next steps:")
print("  1. Start the API: cd backend && uvicorn src.main:app --reload")
print("  2. Start the frontend: cd frontend && npm run dev")
print("  3. Run scrapers: cd backend && python src/jobs/nightly_v4.py") 