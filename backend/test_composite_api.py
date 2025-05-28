"""
Test Script for Composite Scoring API - Task 5.2
Validates all API endpoints for the composite scoring system
"""

import sys
import requests
import json
from pathlib import Path

def test_composite_api_endpoints():
    """Test all composite scoring API endpoints"""
    
    print("=" * 70)
    print("TESTING COMPOSITE SCORING API ENDPOINTS - TASK 5.2")
    print("=" * 70)
    
    base_url = "http://localhost:8000/api/v3"
    
    print("\n1. TESTING SCORING PROFILES ENDPOINT")
    print("-" * 40)
    
    try:
        response = requests.get(f"{base_url}/composite/profiles")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total_profiles']} scoring profiles:")
            for profile in data['profiles']:
                print(f"  • {profile['name']}: {profile['description']}")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n2. TESTING COMPOSITE LEADERBOARDS")
    print("-" * 40)
    
    profiles = ["General", "Developer", "Academic", "Healthcare", "Legal"]
    
    for profile in profiles:
        try:
            response = requests.get(f"{base_url}/composite/leaderboard/{profile}?limit=3")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {profile} leaderboard ({data['total_models']} models):")
                for i, model in enumerate(data['leaderboard'][:3], 1):
                    print(f"  {i}. {model['model_name']}: {model['composite_score']:.1f}")
            else:
                print(f"❌ {profile} failed: {response.status_code}")
        except Exception as e:
            print(f"❌ {profile} error: {e}")
    
    print("\n3. TESTING MODEL DETAIL ENDPOINT")
    print("-" * 40)
    
    try:
        # Test with a top model
        test_model = "OpenAI / o3-mini (2025-01-31)"
        response = requests.get(f"{base_url}/composite/model/{test_model}?profile_name=General")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Model details for {test_model}:")
            print(f"  Composite Score: {data['composite_score']:.1f}")
            print(f"  Confidence: {data['confidence_score']:.2f}")
            print(f"  Domain Coverage: {data['domain_coverage']}")
            print(f"  Domain Breakdown:")
            for domain, details in data['domain_breakdown'].items():
                print(f"    • {domain}: {details['domain_score']:.1f} (weight: {details['weight_in_profile']:.0%})")
        else:
            print(f"❌ Model details failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Model details error: {e}")
    
    print("\n4. TESTING STATISTICS ENDPOINT")
    print("-" * 40)
    
    try:
        response = requests.get(f"{base_url}/composite/statistics")
        if response.status_code == 200:
            data = response.json()
            overview = data['system_overview']
            print(f"✅ Composite scoring statistics:")
            print(f"  Total composite scores: {overview['total_composite_scores']}")
            print(f"  Unique models: {overview['unique_models']}")
            print(f"  Active profiles: {overview['active_profiles']}")
            print(f"  Average composite score: {overview['avg_composite_score']:.1f}")
            print(f"  Average confidence: {overview['avg_confidence']:.2f}")
        else:
            print(f"❌ Statistics failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Statistics error: {e}")
    
    print("\n5. TESTING PROFILE COMPARISON")
    print("-" * 40)
    
    try:
        response = requests.get(f"{base_url}/composite/leaderboard/compare?limit=3")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Profile comparison ({data['total_models']} models):")
            for model in data['comparison'][:3]:
                print(f"  {model['model_name']}:")
                for profile in ['general', 'developer', 'academic']:
                    if model.get(profile):
                        print(f"    {profile}: {model[profile]['score']:.1f}")
        else:
            print(f"❌ Comparison failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Comparison error: {e}")
    
    print("\n6. TESTING METHODOLOGY ENDPOINT")
    print("-" * 40)
    
    try:
        response = requests.get(f"{base_url}/composite/methodology")
        if response.status_code == 200:
            data = response.json()
            methodology = data['composite_scoring_methodology']
            print(f"✅ Methodology explanation available:")
            print(f"  Overview: {methodology['overview']}")
            print(f"  Profiles: {len(methodology['professional_profiles'])} defined")
            print(f"  Process steps: {len(methodology['scoring_process'])} steps")
        else:
            print(f"❌ Methodology failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Methodology error: {e}")
    
    print("\n" + "=" * 70)
    print("✅ COMPOSITE SCORING API TEST COMPLETED!")
    print("=" * 70)

if __name__ == "__main__":
    print("Note: Make sure the API server is running on localhost:8000")
    print("Run: cd backend/src && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print()
    
    try:
        # Quick connectivity test
        response = requests.get("http://localhost:8000/")
        if response.status_code == 200:
            test_composite_api_endpoints()
        else:
            print("❌ API server not responding properly")
    except Exception as e:
        print(f"❌ Cannot connect to API server: {e}")
        print("Please start the server first") 