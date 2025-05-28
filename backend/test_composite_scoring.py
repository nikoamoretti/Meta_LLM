"""
Test Script for Composite Scoring System - Task 5.2
Validates composite scoring functionality before processing all scores
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from services.composite_scoring_service import CompositeScoringService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_composite_scoring_system():
    """Test the composite scoring system with real data"""
    
    print("=" * 70)
    print("TESTING COMPOSITE SCORING SYSTEM - TASK 5.2")
    print("=" * 70)
    
    # Initialize service
    service = CompositeScoringService()
    
    print("\n1. TESTING SCORING PROFILES")
    print("-" * 40)
    
    profiles = service.get_scoring_profiles()
    print(f"✅ Found {len(profiles)} scoring profiles:")
    
    for profile in profiles:
        print(f"  • {profile['name']}: {profile['description']}")
        weights = profile['weights']
        print(f"    Weights: Reasoning({weights['reasoning']:.0%}), Academic({weights['academic']:.0%}), " +
              f"Coding({weights['software_engineering']:.0%}), Medical({weights['medical']:.0%}), " +
              f"Legal({weights['legal']:.0%}), Comprehensive({weights['comprehensive']:.0%})")
    
    print("\n2. TESTING MODEL DOMAIN SCORE RETRIEVAL")
    print("-" * 40)
    
    model_domain_scores = service.get_model_domain_scores()
    print(f"✅ Retrieved domain scores for {len(model_domain_scores)} models")
    
    # Show sample model with domain breakdown
    if model_domain_scores:
        sample_model = list(model_domain_scores.keys())[0]
        sample_domains = model_domain_scores[sample_model]
        print(f"  Sample model '{sample_model}' has scores in {len(sample_domains)} domains:")
        
        for domain, domain_score in sample_domains.items():
            print(f"    • {domain}: {domain_score.normalized_score:.1f} " +
                  f"(confidence: {domain_score.confidence:.2f}, " +
                  f"benchmarks: {domain_score.benchmark_count})")
    
    print("\n3. TESTING COMPOSITE SCORE CALCULATION")
    print("-" * 40)
    
    # Test with General profile first
    general_results = service.calculate_all_composite_scores(profile_id=1)  # General profile
    
    if general_results:
        profile_name = list(general_results.keys())[0]
        results = general_results[profile_name]
        print(f"✅ Calculated {len(results)} composite scores for {profile_name} profile")
        
        # Show top 5 models
        print(f"  Top 5 models ({profile_name} profile):")
        for i, result in enumerate(results[:5], 1):
            print(f"    {i}. {result.model_name}: {result.composite_score:.1f} " +
                  f"(confidence: {result.confidence_score:.2f}, " +
                  f"coverage: {result.domain_coverage}/6 domains)")
            
            # Show domain breakdown for #1
            if i == 1:
                print("       Domain breakdown:")
                for domain, domain_score in result.domain_breakdown.items():
                    print(f"         • {domain}: {domain_score.normalized_score:.1f}")
                if result.missing_domains:
                    print(f"         Missing: {', '.join(result.missing_domains)}")
    
    print("\n4. TESTING FULL PROCESSING PIPELINE")
    print("-" * 40)
    
    print("⏳ Processing all composite scores (this may take a moment)...")
    report = service.process_all_composite_scores()
    
    if report.get("success"):
        print("✅ Full processing completed successfully!")
        stats = report["statistics"]["overview"]
        print(f"  • Total composite scores: {stats['total_composite_scores']}")
        print(f"  • Unique models: {stats['unique_models']}")
        print(f"  • Active profiles: {stats['active_profiles']}")
        print(f"  • Average composite score: {stats['avg_composite_score']:.1f}")
        print(f"  • Average confidence: {stats['avg_confidence']:.2f}")
        print(f"  • Average domain coverage: {stats['avg_domain_coverage']:.1f}/6 domains")
        
        print("\n  Profile-specific statistics:")
        for profile_stat in report["statistics"]["profiles"]:
            print(f"    • {profile_stat['profile_name']}: " +
                  f"avg {profile_stat['avg_score']:.1f}, " +
                  f"range {profile_stat['min_score']:.1f}-{profile_stat['max_score']:.1f}")
    else:
        print(f"❌ Processing failed: {report.get('error', 'Unknown error')}")
        return False
    
    print("\n5. TESTING COMPOSITE LEADERBOARDS")
    print("-" * 40)
    
    for profile_name in ["General", "Developer", "Academic"]:
        leaderboard = service.get_composite_leaderboard(profile_name, limit=3)
        if leaderboard:
            print(f"  {profile_name} leaderboard (top 3):")
            for i, model in enumerate(leaderboard, 1):
                print(f"    {i}. {model['model_name']}: {model['composite_score']:.1f}")
    
    print("\n" + "=" * 70)
    print("✅ COMPOSITE SCORING SYSTEM TEST COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    test_composite_scoring_system() 