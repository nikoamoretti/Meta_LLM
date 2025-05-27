#!/usr/bin/env python3
"""
Test the Chatbot Arena scraper
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers.chatbot_arena_scraper import ChatbotArenaScraper
import json

def main():
    print("🔍 Testing Chatbot Arena Scraper...")
    print("=" * 60)
    
    scraper = ChatbotArenaScraper()
    
    try:
        # Get the scraped data
        all_data = scraper.scrape_all()
        arena_models = all_data.get('chatbot_arena', [])
        
        print(f"📊 Found {len(arena_models)} models from Chatbot Arena:")
        print("=" * 60)
        
        if arena_models:
            # Sort by arena score (highest first)
            sorted_models = sorted(arena_models, 
                                 key=lambda x: x['scores'].get('arena_score', 0), 
                                 reverse=True)
            
            print(f"\n🏆 CHATBOT ARENA LEADERBOARD:")
            print("-" * 60)
            print(f"{'Rank':<4} {'Model':<35} {'Arena Score':<12} {'Source'}")
            print("-" * 60)
            
            for i, model in enumerate(sorted_models[:25], 1):  # Top 25
                model_name = model['model']
                arena_score = model['scores'].get('arena_score', 'N/A')
                source = model['source']
                
                # Truncate long model names
                if len(model_name) > 33:
                    model_name = model_name[:30] + "..."
                
                print(f"{i:<4} {model_name:<35} {arena_score:<12} {source}")
            
            # Statistics
            scores = [m['scores'].get('arena_score', 0) for m in arena_models if m['scores'].get('arena_score')]
            if scores:
                print(f"\n📈 STATISTICS:")
                print("-" * 40)
                print(f"Total models: {len(arena_models)}")
                print(f"Models with scores: {len(scores)}")
                print(f"Highest score: {max(scores):.1f}")
                print(f"Lowest score: {min(scores):.1f}")
                print(f"Average score: {sum(scores)/len(scores):.1f}")
            
            # Show score distribution
            print(f"\n📊 SCORE DISTRIBUTION:")
            print("-" * 40)
            score_ranges = {
                "1400+": len([s for s in scores if s >= 1400]),
                "1300-1399": len([s for s in scores if 1300 <= s < 1400]),
                "1200-1299": len([s for s in scores if 1200 <= s < 1300]),
                "1100-1199": len([s for s in scores if 1100 <= s < 1200]),
                "1000-1099": len([s for s in scores if 1000 <= s < 1100]),
                "Below 1000": len([s for s in scores if s < 1000])
            }
            
            for range_name, count in score_ranges.items():
                if count > 0:
                    print(f"{range_name:<12}: {count:>3} models")
        
        else:
            print("❌ No models found. Let's debug...")
            
            # Debug information
            print("\n🔍 DEBUG INFO:")
            print("-" * 40)
            print("Checking if we can access the page...")
            
        # Save detailed data
        with open('arena_data.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        print(f"\n💾 Raw data saved to arena_data.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 