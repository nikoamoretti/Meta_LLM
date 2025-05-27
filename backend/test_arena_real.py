#!/usr/bin/env python3
"""
Test the REAL Arena scraper - NO FALLBACK DATA
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers.arena_real_scraper import ArenaRealScraper
import json

def main():
    print("🔍 Testing REAL Arena Scraper (NO FALLBACK)...")
    print("=" * 70)
    
    scraper = ArenaRealScraper()
    
    try:
        # Get the scraped data
        all_data = scraper.scrape_all()
        arena_data = all_data.get('chatbot_arena_real', {})
        
        if not arena_data:
            print("❌ NO REAL DATA FOUND - Scraper returned empty results")
            print("This means the scraping failed and NO fallback data was used")
            return
        
        print(f"📊 Found REAL data for {len(arena_data)} categories:")
        print("=" * 70)
        
        # Summary first
        total_models = 0
        for category_key, models in arena_data.items():
            total_models += len(models)
            category_name = scraper.categories.get(category_key, category_key)
            print(f"  {category_name}: {len(models)} models")
        
        print(f"\nTotal REAL model entries: {total_models}")
        print("=" * 70)
        
        # Show top 10 for each category with real data
        for category_key, models in arena_data.items():
            if not models:
                continue
                
            category_name = scraper.categories.get(category_key, category_key)
            
            # Sort by score (highest first)
            score_key = f'{category_key}_score'
            sorted_models = sorted(models, 
                                 key=lambda x: x['scores'].get(score_key, 0), 
                                 reverse=True)
            
            print(f"\n🏆 {category_name.upper()} - TOP 10 REAL MODELS:")
            print("-" * 70)
            print(f"{'Rank':<4} {'Model':<35} {'Score':<8} {'Votes':<8} {'Source'}")
            print("-" * 70)
            
            for i, model in enumerate(sorted_models[:10], 1):
                model_name = model['model'][:34]  # Truncate long names
                score = model['scores'].get(score_key, 'N/A')
                votes = model.get('votes', 'N/A')
                source = model.get('source', 'Unknown')
                
                print(f"{i:<4} {model_name:<35} {score:<8} {votes:<8} {source}")
        
        # Save raw data for inspection
        with open('arena_real_data.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        
        print(f"\n💾 Raw data saved to: arena_real_data.json")
        print("=" * 70)
        print("✅ REAL DATA EXTRACTION COMPLETE - NO FALLBACK USED")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 