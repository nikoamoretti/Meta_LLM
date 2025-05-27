#!/usr/bin/env python3
"""
Test the Playwright-based Arena scraper
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers.arena_playwright_scraper import ArenaPlaywrightScraper
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("🎭 Testing Playwright Arena Scraper...")
    print("=" * 70)
    
    scraper = ArenaPlaywrightScraper()
    
    try:
        # Get the scraped data
        all_data = scraper.scrape_all()
        arena_data = all_data.get('chatbot_arena_playwright', {})
        
        if not arena_data:
            print("❌ NO DATA FOUND - Playwright scraper returned empty results")
            print("Check the debug screenshots for more information")
            return
        
        print(f"📊 Found data for {len(arena_data)} categories:")
        print("=" * 70)
        
        # Summary first
        total_models = 0
        for category_key, models in arena_data.items():
            total_models += len(models)
            category_name = scraper.categories.get(category_key, category_key)
            print(f"  {category_name}: {len(models)} models")
        
        print(f"\nTotal model entries: {total_models}")
        print("=" * 70)
        
        # Show top 10 for each category
        for category_key, models in arena_data.items():
            if not models:
                continue
                
            category_name = scraper.categories.get(category_key, category_key)
            
            # Sort by score (highest first)
            score_key = f'{category_key}_score'
            sorted_models = sorted(models, 
                                 key=lambda x: x['scores'].get(score_key, 0), 
                                 reverse=True)
            
            print(f"\n🏆 {category_name.upper()} - TOP 10 MODELS:")
            print("-" * 70)
            print(f"{'Rank':<4} {'Model':<40} {'Score':<8} {'Source'}")
            print("-" * 70)
            
            for i, model in enumerate(sorted_models[:10], 1):
                model_name = model['model'][:39]  # Truncate long names
                score = model['scores'].get(score_key, 'N/A')
                source = model.get('source', 'Unknown')
                
                print(f"{i:<4} {model_name:<40} {score:<8} {source}")
        
        # Save raw data for inspection
        with open('arena_playwright_data.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        
        print(f"\n💾 Raw data saved to: arena_playwright_data.json")
        print("=" * 70)
        print("✅ PLAYWRIGHT SCRAPING COMPLETE")
        
        # Validate data quality
        print("\n🔍 Data Quality Check:")
        print("-" * 70)
        
        # Check for known model names
        known_models = ['gpt-4', 'claude', 'gemini', 'llama', 'mistral']
        found_known = False
        
        for category_key, models in arena_data.items():
            for model in models:
                model_name_lower = model['model'].lower()
                if any(known in model_name_lower for known in known_models):
                    found_known = True
                    break
            if found_known:
                break
        
        if found_known:
            print("✅ Found known model names - data appears to be real!")
        else:
            print("⚠️  No known model names found - data might be placeholder")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 