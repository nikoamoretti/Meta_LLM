#!/usr/bin/env python3
"""
Standalone test of Vellum AI scraper - shows scores without database
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers.crawl4ai_vellum_fixed import Crawl4aiVellumScraper
import json

def main():
    print("🔍 Testing Vellum AI Scraper...")
    print("=" * 50)
    
    scraper = Crawl4aiVellumScraper()
    
    try:
        # Get the scraped data
        all_data = scraper.scrape_all()
        vellum_models = all_data.get('vellum', [])
        
        print(f"📊 Found {len(vellum_models)} models from Vellum AI:")
        print("=" * 50)
        
        # Sort by score (highest first)
        sorted_models = sorted(vellum_models, 
                             key=lambda x: x['scores'].get('benchmark_score', 0), 
                             reverse=True)
        
        for i, model in enumerate(sorted_models, 1):
            model_name = model['model']
            scores = model['scores']
            score = scores.get('benchmark_score', 'N/A')
            
            print(f"{i:2d}. {model_name}")
            print(f"    Score: {score}")
            print(f"    Source: {model['source']}")
            print()
        
        # Summary stats
        if vellum_models:
            scores = [m['scores'].get('benchmark_score', 0) for m in vellum_models if m['scores'].get('benchmark_score')]
            if scores:
                print("📈 Score Statistics:")
                print(f"   Highest: {max(scores):.1f}")
                print(f"   Lowest:  {min(scores):.1f}")
                print(f"   Average: {sum(scores)/len(scores):.1f}")
        
        # Save raw data for inspection
        with open('vellum_raw_data.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        print(f"\n💾 Raw data saved to vellum_raw_data.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 