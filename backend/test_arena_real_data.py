#!/usr/bin/env python3
"""
Test if Arena scraper is getting real data or fallback data
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers.arena_categories_scraper import ArenaCategoriesScraper
import asyncio

async def test_arena_data():
    print("🔍 Testing Arena Data Sources...")
    print("=" * 50)
    
    scraper = ArenaCategoriesScraper()
    
    # Test Math category specifically
    print("📊 Testing Math Category:")
    print("-" * 30)
    
    # Try API first
    api_data = await scraper._try_category_api('math')
    print(f"API data length: {len(api_data)}")
    
    if api_data:
        print("✅ Got real API data!")
        print("Top 5 from API:")
        for i, model in enumerate(api_data[:5], 1):
            model_name = model.get('model', 'Unknown')
            score = model.get('scores', {}).get('math_score', 'N/A')
            print(f"  {i}. {model_name}: {score}")
    else:
        print("❌ No API data - checking fallback...")
        fallback = scraper._get_category_fallback('math')
        print("Top 5 from fallback:")
        for i, model in enumerate(fallback[:5], 1):
            model_name = model.get('model', 'Unknown')
            score = model.get('scores', {}).get('math_score', 'N/A')
            print(f"  {i}. {model_name}: {score}")
    
    print("\n" + "=" * 50)
    print("🔍 Testing Overall Category:")
    print("-" * 30)
    
    # Test Overall category
    overall_data = await scraper._try_category_api('overall')
    print(f"Overall API data length: {len(overall_data)}")
    
    if overall_data:
        print("✅ Got real API data!")
        print("Top 5 from API:")
        for i, model in enumerate(overall_data[:5], 1):
            model_name = model.get('model', 'Unknown')
            score = model.get('scores', {}).get('overall_score', 'N/A')
            print(f"  {i}. {model_name}: {score}")
    else:
        print("❌ No API data - using fallback")

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_arena_data())
    finally:
        loop.close()

if __name__ == "__main__":
    main() 