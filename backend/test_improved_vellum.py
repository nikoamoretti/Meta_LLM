#!/usr/bin/env python3
"""
Test the improved Vellum AI scraper
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers.vellum_improved import VellumImprovedScraper
import json

def main():
    print("🔍 Testing Improved Vellum AI Scraper...")
    print("=" * 60)
    
    scraper = VellumImprovedScraper()
    
    try:
        # Get the scraped data
        all_data = scraper.scrape_all()
        vellum_models = all_data.get('vellum', [])
        
        print(f"📊 Found {len(vellum_models)} models from Vellum AI:")
        print("=" * 60)
        
        # Group by benchmark for better display
        benchmarks = {}
        for model in vellum_models:
            for benchmark, score in model['scores'].items():
                if benchmark not in benchmarks:
                    benchmarks[benchmark] = []
                benchmarks[benchmark].append({
                    'model': model['model'],
                    'score': score
                })
        
        # Display results by benchmark
        for benchmark, models in benchmarks.items():
            print(f"\n🏆 {benchmark.upper().replace('_', ' ')} BENCHMARK:")
            print("-" * 50)
            
            # Sort by score (highest first)
            sorted_models = sorted(models, key=lambda x: x['score'], reverse=True)
            
            for i, model_data in enumerate(sorted_models[:10], 1):  # Top 10
                model_name = model_data['model']
                score = model_data['score']
                print(f"{i:2d}. {model_name:<25} {score:>6.1f}%")
        
        # Overall summary
        print(f"\n📈 SUMMARY:")
        print("-" * 50)
        print(f"Total models: {len(vellum_models)}")
        print(f"Benchmarks found: {len(benchmarks)}")
        print(f"Benchmark categories: {', '.join(benchmarks.keys())}")
        
        # Save detailed data
        with open('vellum_improved_data.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        print(f"\n💾 Detailed data saved to vellum_improved_data.json")
        
        # Show top performers across all benchmarks
        print(f"\n🌟 TOP PERFORMERS BY BENCHMARK:")
        print("-" * 50)
        for benchmark, models in benchmarks.items():
            if models:
                top_model = max(models, key=lambda x: x['score'])
                print(f"{benchmark.replace('_', ' ').title():<20}: {top_model['model']:<25} ({top_model['score']:.1f}%)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 