#!/usr/bin/env python3
"""
Test the comprehensive Arena Categories scraper
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers.arena_categories_scraper import ArenaCategoriesScraper
import json

def main():
    print("🔍 Testing Comprehensive Arena Categories Scraper...")
    print("=" * 80)
    
    scraper = ArenaCategoriesScraper()
    
    try:
        # Get the scraped data
        all_data = scraper.scrape_all()
        categories_data = all_data.get('chatbot_arena_categories', {})
        
        print(f"📊 Found data for {len(categories_data)} categories:")
        print("=" * 80)
        
        # Display summary first
        total_models = 0
        for category_key, models in categories_data.items():
            total_models += len(models)
            category_name = scraper.categories.get(category_key, category_key)
            print(f"  {category_name:<25}: {len(models):>3} models")
        
        print(f"\nTotal model entries across all categories: {total_models}")
        print("=" * 80)
        
        # Display top 20 for each category (since we now have 100)
        for category_key, models in categories_data.items():
            if not models:
                continue
                
            category_name = scraper.categories.get(category_key, category_key)
            
            # Sort by score (highest first)
            score_key = f'{category_key}_score'
            sorted_models = sorted(models, 
                                 key=lambda x: x['scores'].get(score_key, 0), 
                                 reverse=True)
            
            print(f"\n🏆 {category_name.upper()} - TOP 20 (of {len(sorted_models)}):")
            print("-" * 70)
            print(f"{'Rank':<4} {'Model':<35} {'Score':<8} {'Votes':<8} {'Org'}")
            print("-" * 70)
            
            for i, model in enumerate(sorted_models[:20], 1):
                model_name = model['model']
                score = model['scores'].get(score_key, 'N/A')
                votes = model.get('votes', 'N/A')
                org = model.get('organization', 'Unknown')
                
                # Truncate long names
                if len(model_name) > 33:
                    model_name = model_name[:30] + "..."
                if len(org) > 10:
                    org = org[:8] + ".."
                
                print(f"{i:<4} {model_name:<35} {score:<8} {votes:<8} {org}")
            
            # Show summary of remaining models
            if len(sorted_models) > 20:
                remaining = len(sorted_models) - 20
                print(f"     ... and {remaining} more models (ranks 21-{len(sorted_models)})")
                
                # Show score range of remaining models
                if remaining > 0:
                    lowest_score = sorted_models[-1]['scores'].get(score_key, 0)
                    rank_21_score = sorted_models[20]['scores'].get(score_key, 0) if len(sorted_models) > 20 else 0
                    print(f"     Score range: {rank_21_score} (rank 21) to {lowest_score} (rank {len(sorted_models)})")
        
        # Cross-category analysis
        print(f"\n🌟 CROSS-CATEGORY ANALYSIS:")
        print("=" * 80)
        
        # Find models that appear in multiple categories
        model_appearances = {}
        for category_key, models in categories_data.items():
            for model in models:
                model_name = model['model']
                if model_name not in model_appearances:
                    model_appearances[model_name] = []
                model_appearances[model_name].append({
                    'category': category_key,
                    'score': model['scores'].get(f'{category_key}_score', 0),
                    'rank': models.index(model) + 1
                })
        
        # Find top performers across categories
        multi_category_models = {name: appearances for name, appearances in model_appearances.items() 
                               if len(appearances) >= 3}  # Models in 3+ categories
        
        print(f"\n🎯 TOP MULTI-CATEGORY PERFORMERS:")
        print("-" * 60)
        
        # Calculate average performance across categories
        model_avg_scores = {}
        for model_name, appearances in multi_category_models.items():
            avg_score = sum(app['score'] for app in appearances) / len(appearances)
            model_avg_scores[model_name] = {
                'avg_score': avg_score,
                'categories': len(appearances),
                'appearances': appearances
            }
        
        # Sort by average score
        top_multi_performers = sorted(model_avg_scores.items(), 
                                    key=lambda x: x[1]['avg_score'], 
                                    reverse=True)[:10]
        
        for i, (model_name, stats) in enumerate(top_multi_performers, 1):
            avg_score = stats['avg_score']
            cat_count = stats['categories']
            
            # Truncate model name
            display_name = model_name[:30] + "..." if len(model_name) > 30 else model_name
            
            print(f"{i:2d}. {display_name:<35} Avg: {avg_score:>6.1f} ({cat_count} categories)")
            
            # Show top 3 category performances
            top_cats = sorted(stats['appearances'], key=lambda x: x['score'], reverse=True)[:3]
            for cat in top_cats:
                cat_name = scraper.categories.get(cat['category'], cat['category'])[:15]
                print(f"     • {cat_name:<15}: {cat['score']:>6.1f} (#{cat['rank']})")
        
        # Category difficulty analysis
        print(f"\n📊 CATEGORY DIFFICULTY ANALYSIS:")
        print("-" * 50)
        
        category_stats = {}
        for category_key, models in categories_data.items():
            if models:
                scores = [model['scores'].get(f'{category_key}_score', 0) for model in models]
                category_stats[category_key] = {
                    'avg_score': sum(scores) / len(scores),
                    'max_score': max(scores),
                    'min_score': min(scores),
                    'model_count': len(models)
                }
        
        # Sort by average score (highest = easier, lower = harder)
        sorted_categories = sorted(category_stats.items(), 
                                 key=lambda x: x[1]['avg_score'], 
                                 reverse=True)
        
        print(f"{'Category':<20} {'Avg Score':<10} {'Max':<8} {'Models':<8} {'Difficulty'}")
        print("-" * 60)
        
        for category_key, stats in sorted_categories:
            category_name = scraper.categories.get(category_key, category_key)[:18]
            avg_score = stats['avg_score']
            max_score = stats['max_score']
            model_count = stats['model_count']
            
            # Determine difficulty based on average score
            if avg_score >= 1380:
                difficulty = "Easy"
            elif avg_score >= 1320:
                difficulty = "Medium"
            elif avg_score >= 1260:
                difficulty = "Hard"
            else:
                difficulty = "Very Hard"
            
            print(f"{category_name:<20} {avg_score:>8.1f}  {max_score:>6.1f}  {model_count:>6}   {difficulty}")
        
        # Save detailed data
        with open('arena_categories_data.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        print(f"\n💾 Detailed data saved to arena_categories_data.json")
        
        # Summary statistics
        print(f"\n📈 SUMMARY STATISTICS:")
        print("-" * 40)
        print(f"Total categories scraped: {len(categories_data)}")
        print(f"Total model entries: {total_models}")
        print(f"Average models per category: {total_models/len(categories_data):.1f}")
        print(f"Categories with 50+ models: {len([c for c in categories_data.values() if len(c) >= 50])}")
        print(f"Categories with 100 models: {len([c for c in categories_data.values() if len(c) >= 100])}")
        
        # Model distribution analysis
        model_counts = [len(models) for models in categories_data.values()]
        if model_counts:
            print(f"Model count range: {min(model_counts)} to {max(model_counts)} per category")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 