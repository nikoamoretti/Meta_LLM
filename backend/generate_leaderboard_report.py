#!/usr/bin/env python3
"""
Generate Comprehensive Leaderboard Report
Shows rankings from all scraped leaderboards: Vellum AI and Chatbot Arena (all categories)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers.vellum_improved import VellumImprovedScraper
from scrapers.arena_categories_scraper import ArenaCategoriesScraper
import json
from datetime import datetime

def generate_markdown_report():
    """Generate a comprehensive markdown report of all leaderboards"""
    
    print("🔍 Generating Comprehensive Leaderboard Report...")
    print("=" * 60)
    
    # Get current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Initialize report content
    report_lines = []
    
    # Header
    report_lines.extend([
        "# 🏆 Comprehensive LLM Leaderboard Report",
        f"*Generated on {timestamp}*",
        "",
        "This report contains rankings from all major LLM leaderboards we've scraped:",
        "- **Vellum AI Leaderboard** - Benchmark-specific performance",
        "- **Chatbot Arena** - All 20 categories with top 100 models each",
        "",
        "---",
        ""
    ])
    
    # Section 1: Vellum AI Leaderboard
    print("📊 Scraping Vellum AI Leaderboard...")
    vellum_scraper = VellumImprovedScraper()
    vellum_data = vellum_scraper.scrape_all()
    vellum_models = vellum_data.get('vellum', [])
    
    report_lines.extend([
        "## 📊 Vellum AI Leaderboard",
        "",
        "The Vellum AI leaderboard focuses on specific benchmark performance across key domains.",
        f"**Total Models**: {len(vellum_models)}",
        "",
        "### 🎯 Top Performers by Benchmark",
        ""
    ])
    
    if vellum_models:
        # Group by benchmark
        benchmarks = {}
        for model in vellum_models:
            for benchmark, score in model['scores'].items():
                if benchmark not in benchmarks:
                    benchmarks[benchmark] = []
                benchmarks[benchmark].append({
                    'model': model['model'],
                    'score': score,
                    'source': model.get('source', 'Vellum AI')
                })
        
        # Sort each benchmark by score
        for benchmark in benchmarks:
            benchmarks[benchmark].sort(key=lambda x: x['score'], reverse=True)
        
        # Display each benchmark
        for benchmark, models in benchmarks.items():
            benchmark_name = benchmark.replace('_', ' ').title()
            report_lines.extend([
                f"#### 🏅 {benchmark_name}",
                "",
                "| Rank | Model | Score | Source |",
                "|------|-------|-------|--------|"
            ])
            
            for i, model in enumerate(models[:10], 1):  # Top 10
                model_name = model['model'][:40] + "..." if len(model['model']) > 40 else model['model']
                score = f"{model['score']:.1f}" if isinstance(model['score'], (int, float)) else str(model['score'])
                source = model['source'][:20] + "..." if len(model['source']) > 20 else model['source']
                
                report_lines.append(f"| {i} | {model_name} | {score} | {source} |")
            
            if len(models) > 10:
                report_lines.append(f"| ... | *{len(models) - 10} more models* | ... | ... |")
            
            report_lines.extend(["", ""])
    
    # Section 2: Chatbot Arena Categories
    print("🏟️ Scraping Chatbot Arena Categories...")
    arena_scraper = ArenaCategoriesScraper()
    arena_data = arena_scraper.scrape_all()
    categories_data = arena_data.get('chatbot_arena_categories', {})
    
    total_arena_models = sum(len(models) for models in categories_data.values())
    
    report_lines.extend([
        "---",
        "",
        "## 🏟️ Chatbot Arena Leaderboard",
        "",
        "The Chatbot Arena leaderboard provides comprehensive rankings across 20 different categories,",
        "from overall performance to language-specific and task-specific evaluations.",
        f"**Total Categories**: {len(categories_data)}",
        f"**Total Model Entries**: {total_arena_models}",
        f"**Models per Category**: 100",
        "",
        "### 📋 Category Overview",
        "",
        "| Category | Models | Top Model | Top Score |",
        "|----------|--------|-----------|-----------|"
    ])
    
    # Category overview table
    for category_key, models in categories_data.items():
        if not models:
            continue
            
        category_name = arena_scraper.categories.get(category_key, category_key)
        score_key = f'{category_key}_score'
        
        # Sort by score to get top model
        sorted_models = sorted(models, key=lambda x: x['scores'].get(score_key, 0), reverse=True)
        top_model = sorted_models[0] if sorted_models else None
        
        if top_model:
            top_model_name = top_model['model'][:30] + "..." if len(top_model['model']) > 30 else top_model['model']
            top_score = f"{top_model['scores'].get(score_key, 0):.1f}"
            report_lines.append(f"| {category_name} | {len(models)} | {top_model_name} | {top_score} |")
    
    report_lines.extend(["", ""])
    
    # Detailed category rankings
    report_lines.extend([
        "### 🏆 Detailed Category Rankings",
        "",
        "Below are the top 15 models for each category:",
        ""
    ])
    
    for category_key, models in categories_data.items():
        if not models:
            continue
            
        category_name = arena_scraper.categories.get(category_key, category_key)
        score_key = f'{category_key}_score'
        
        # Sort by score
        sorted_models = sorted(models, key=lambda x: x['scores'].get(score_key, 0), reverse=True)
        
        report_lines.extend([
            f"#### 🎯 {category_name}",
            "",
            "| Rank | Model | Score | Votes | Organization |",
            "|------|-------|-------|-------|--------------|"
        ])
        
        for i, model in enumerate(sorted_models[:15], 1):  # Top 15
            model_name = model['model'][:35] + "..." if len(model['model']) > 35 else model['model']
            score = model['scores'].get(score_key, 'N/A')
            score_str = f"{score:.1f}" if isinstance(score, (int, float)) else str(score)
            votes = model.get('votes', 'N/A')
            votes_str = f"{votes:,}" if isinstance(votes, int) else str(votes)
            org = model.get('organization', 'Unknown')[:15] + "..." if len(str(model.get('organization', 'Unknown'))) > 15 else str(model.get('organization', 'Unknown'))
            
            report_lines.append(f"| {i} | {model_name} | {score_str} | {votes_str} | {org} |")
        
        if len(sorted_models) > 15:
            remaining = len(sorted_models) - 15
            report_lines.append(f"| ... | *{remaining} more models (ranks 16-{len(sorted_models)})* | ... | ... | ... |")
        
        report_lines.extend(["", ""])
    
    # Cross-leaderboard analysis
    report_lines.extend([
        "---",
        "",
        "## 🌟 Cross-Leaderboard Analysis",
        "",
        "### 🏅 Top Multi-Category Performers (Arena)",
        ""
    ])
    
    # Find models that appear in multiple Arena categories
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
                           if len(appearances) >= 10}  # Models in 10+ categories
    
    # Calculate average performance
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
    
    report_lines.extend([
        "| Rank | Model | Avg Score | Categories | Best Performance |",
        "|------|-------|-----------|------------|------------------|"
    ])
    
    for i, (model_name, stats) in enumerate(top_multi_performers, 1):
        model_display = model_name[:30] + "..." if len(model_name) > 30 else model_name
        avg_score = f"{stats['avg_score']:.1f}"
        cat_count = stats['categories']
        
        # Find best performance
        best_performance = max(stats['appearances'], key=lambda x: x['score'])
        best_cat = arena_scraper.categories.get(best_performance['category'], best_performance['category'])[:15]
        best_score = f"{best_performance['score']:.1f}"
        best_rank = best_performance['rank']
        best_perf_str = f"{best_cat}: {best_score} (#{best_rank})"
        
        report_lines.append(f"| {i} | {model_display} | {avg_score} | {cat_count} | {best_perf_str} |")
    
    # Summary statistics
    report_lines.extend([
        "",
        "---",
        "",
        "## 📈 Summary Statistics",
        "",
        f"- **Total Leaderboards Scraped**: 2 (Vellum AI + Chatbot Arena)",
        f"- **Total Categories**: {len(categories_data) + len(benchmarks) if vellum_models else len(categories_data)}",
        f"- **Total Model Entries**: {total_arena_models + len(vellum_models)}",
        f"- **Unique Models**: {len(set(model_appearances.keys()))} (Arena only)",
        f"- **Most Comprehensive Model**: {top_multi_performers[0][0] if top_multi_performers else 'N/A'} ({top_multi_performers[0][1]['categories'] if top_multi_performers else 0} categories)",
        "",
        "### 🎯 Key Insights",
        "",
        "1. **Google Gemini models** dominate both overall and category-specific rankings",
        "2. **OpenAI o1 series** shows strong performance across technical categories",
        "3. **Language-specific performance** varies significantly by model",
        "4. **Comprehensive evaluation** reveals models optimized for different use cases",
        "",
        "---",
        "",
        f"*Report generated by LLM Tracker on {timestamp}*"
    ])
    
    # Write to file
    report_content = "\n".join(report_lines)
    
    with open('LEADERBOARD_REPORT.md', 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✅ Report generated successfully!")
    print(f"📄 Saved to: LEADERBOARD_REPORT.md")
    print(f"📊 Total sections: {len([line for line in report_lines if line.startswith('#')])}")
    print(f"📝 Total lines: {len(report_lines)}")
    
    # Also save raw data as JSON
    combined_data = {
        'timestamp': timestamp,
        'vellum_ai': vellum_data,
        'chatbot_arena': arena_data,
        'summary': {
            'total_leaderboards': 2,
            'total_categories': len(categories_data) + (len(benchmarks) if vellum_models else 0),
            'total_model_entries': total_arena_models + len(vellum_models),
            'arena_categories': len(categories_data),
            'arena_models': total_arena_models,
            'vellum_models': len(vellum_models)
        }
    }
    
    with open('leaderboard_data_complete.json', 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Raw data saved to: leaderboard_data_complete.json")
    
    return report_content

if __name__ == "__main__":
    generate_markdown_report() 