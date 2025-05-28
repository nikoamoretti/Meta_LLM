"""
Test Script for Universal Normalization Engine - Task 5.1
Validates normalization functionality before processing all scores
"""

import asyncio
import logging
from src.services.normalization_engine import UniversalNormalizationEngine
from src.services.normalization_service import NormalizationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_normalization_engine():
    """Test the normalization engine with sample data"""
    
    print("=" * 60)
    print("TESTING UNIVERSAL NORMALIZATION ENGINE")
    print("=" * 60)
    
    engine = UniversalNormalizationEngine()
    
    # Test cases representing our actual data types
    test_cases = [
        # Arena ELO Scores
        {"value": 1446.0, "metric": "math_score", "benchmark": "Arena Math", "leaderboard": "Chatbot Arena", "category": "math", "expected_type": "elo_rating"},
        {"value": 1200.0, "metric": "overall_score", "benchmark": "Arena Overall", "leaderboard": "Chatbot Arena", "category": "general", "expected_type": "elo_rating"},
        
        # Academic scores (HELM)
        {"value": 0.944, "metric": "mean_win_rate", "benchmark": "Overall Performance", "leaderboard": "Stanford HELM Classic", "category": "academic", "expected_type": "academic_score"},
        {"value": 0.822, "metric": "Exact Match", "benchmark": "HellaSwag", "leaderboard": "Stanford HELM Classic", "category": "academic", "expected_type": "academic_score"},
        
        # Percentage scores (Medical, Legal, SWE-Bench)
        {"value": 83.6, "metric": "accuracy", "benchmark": "LegalBench Legal Reasoning", "leaderboard": "LegalBench Legal Reasoning", "category": "legal", "expected_type": "percentage"},
        {"value": 90.01, "metric": "accuracy", "benchmark": "Average ⬆️", "leaderboard": "Medical Expertise Leaderboard", "category": "medical", "expected_type": "percentage"},
        {"value": 68.2, "metric": "percentage_resolved", "benchmark": "Software Engineering Issues", "leaderboard": "SWE-Bench Verified", "category": "software_engineering", "expected_type": "percentage"},
        
        # Cost and time metrics (Strawberry Bench)
        {"value": 0.01109, "metric": "cost", "benchmark": "Cost Efficiency", "leaderboard": "Strawberry Bench", "category": "reasoning", "expected_type": "cost_metric"},
        {"value": 58.0, "metric": "response_time_seconds", "benchmark": "Speed", "leaderboard": "Strawberry Bench", "category": "reasoning", "expected_type": "time_metric"},
        {"value": 411.0, "metric": "tokens", "benchmark": "Token Efficiency", "leaderboard": "Strawberry Bench", "category": "reasoning", "expected_type": "token_count"},
    ]
    
    print(f"\nTesting {len(test_cases)} normalization cases:\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['leaderboard']} - {test_case['benchmark']}")
        print(f"  Raw Value: {test_case['value']} ({test_case['metric']})")
        
        result = engine.normalize_score(
            value=test_case['value'],
            metric=test_case['metric'],
            benchmark=test_case['benchmark'],
            leaderboard_name=test_case['leaderboard'],
            category=test_case['category']
        )
        
        print(f"  Normalized: {result.normalized_value:.2f}/100")
        print(f"  Confidence: {result.confidence_score:.3f}")
        print(f"  Method: {result.normalization_method}")
        print(f"  Detected Type: {result.score_type.value}")
        
        # Validation
        if 0 <= result.normalized_value <= 100:
            print(f"  ✅ Valid range (0-100)")
        else:
            print(f"  ❌ Invalid range: {result.normalized_value}")
        
        if result.confidence_score >= 0.7:
            print(f"  ✅ High confidence")
        elif result.confidence_score >= 0.5:
            print(f"  ⚠️  Medium confidence")
        else:
            print(f"  ❌ Low confidence")
        
        print()
    
    print("=" * 60)
    print("NORMALIZATION ENGINE TEST COMPLETE")
    print("=" * 60)

def test_normalization_service():
    """Test the normalization service database functions"""
    
    print("\n" + "=" * 60)
    print("TESTING NORMALIZATION SERVICE")
    print("=" * 60)
    
    try:
        service = NormalizationService()
        
        # Test statistics function
        print("\nTesting statistics function...")
        stats = service.get_normalization_statistics()
        
        if 'error' in stats:
            print(f"Statistics test failed: {stats['error']}")
        else:
            print(f"✅ Statistics function working")
            print(f"  Current normalized scores: {stats.get('total_normalized_scores', 0)}")
        
        # Test validation function  
        print("\nTesting validation function...")
        validation = service.validate_normalization_quality()
        
        if 'error' in validation:
            print(f"Validation test failed: {validation['error']}")
        else:
            print(f"✅ Validation function working")
            print(f"  Validation samples: {validation.get('total_validated', 0)}")
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
    
    print("\n" + "=" * 60)
    print("NORMALIZATION SERVICE TEST COMPLETE")  
    print("=" * 60)

def main():
    """Main test function"""
    
    print("TASK 5.1 UNIVERSAL NORMALIZATION FRAMEWORK")
    print("Testing Implementation Before Full Processing")
    print("=" * 80)
    
    # Test the normalization engine
    test_normalization_engine()
    
    # Test the normalization service
    test_normalization_service()
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)
    
    # Summary
    print("\nNext Steps:")
    print("1. Review test results above")
    print("2. If tests pass, run: python -c 'from src.services.normalization_service import NormalizationService; service = NormalizationService(); report = service.normalize_all_scores(); print(report)'")
    print("3. Validate results with API endpoints")
    print("4. Test frontend integration")

if __name__ == "__main__":
    main() 