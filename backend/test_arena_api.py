#!/usr/bin/env python3
"""
Test the improved Arena API scraper
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers.arena_api_scraper import ArenaAPIScraper
import json

def main():
    print("🔍 Testing Improved Arena API Scraper...")
    print("=" * 60)
    
    scraper = ArenaAPIScraper()
    
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
            
            print(f"\n🏆 CHATBOT ARENA LEADERBOARD (Top 20):")
            print("-" * 70)
            print(f"{'Rank':<4} {'Model':<35} {'Arena Score':<12} {'Votes':<8} {'Org'}")
            print("-" * 70)
            
            for i, model in enumerate(sorted_models[:20], 1):
                model_name = model['model']
                arena_score = model['scores'].get('arena_score', 'N/A')
                votes = model.get('votes', 'N/A')
                org = model.get('organization', 'Unknown')
                
                # Truncate long names
                if len(model_name) > 33:
                    model_name = model_name[:30] + "..."
                if len(org) > 10:
                    org = org[:8] + ".."
                
                print(f"{i:<4} {model_name:<35} {arena_score:<12} {votes:<8} {org}")
            
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
            
            # Show top performers by organization
            org_leaders = {}
            for model in sorted_models:
                org = model.get('organization', 'Unknown')
                if org not in org_leaders:
                    org_leaders[org] = model
            
            print(f"\n🌟 TOP MODEL BY ORGANIZATION:")
            print("-" * 50)
            for org, model in sorted(org_leaders.items(), 
                                   key=lambda x: x[1]['scores'].get('arena_score', 0), 
                                   reverse=True):
                score = model['scores'].get('arena_score', 'N/A')
                model_name = model['model']
                if len(model_name) > 25:
                    model_name = model_name[:22] + "..."
                print(f"{org:<12}: {model_name:<25} ({score})")
            
            # Show score tiers
            print(f"\n🏅 SCORE TIERS:")
            print("-" * 40)
            tiers = {
                "Elite (1400+)": [m for m in arena_models if m['scores'].get('arena_score', 0) >= 1400],
                "High (1350-1399)": [m for m in arena_models if 1350 <= m['scores'].get('arena_score', 0) < 1400],
                "Good (1300-1349)": [m for m in arena_models if 1300 <= m['scores'].get('arena_score', 0) < 1350],
                "Average (1200-1299)": [m for m in arena_models if 1200 <= m['scores'].get('arena_score', 0) < 1300],
            }
            
            for tier_name, tier_models in tiers.items():
                if tier_models:
                    print(f"{tier_name:<18}: {len(tier_models):>2} models")
                    # Show top 3 in each tier
                    top_in_tier = sorted(tier_models, 
                                       key=lambda x: x['scores'].get('arena_score', 0), 
                                       reverse=True)[:3]
                    for model in top_in_tier:
                        name = model['model'][:20] + "..." if len(model['model']) > 20 else model['model']
                        score = model['scores'].get('arena_score', 0)
                        print(f"                     • {name:<23} ({score})")
        
        else:
            print("❌ No models found")
            
        # Save detailed data
        with open('arena_api_data.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        print(f"\n💾 Detailed data saved to arena_api_data.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 