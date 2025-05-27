import sys
sys.path.append('/app/src')
from datasets import load_dataset
import json

print("Fetching live HuggingFace Open LLM Leaderboard data...\n")

try:
    # Load the dataset
    dataset = load_dataset("open-llm-leaderboard/contents", split="train", streaming=False)
    print(f"Total models in leaderboard: {len(dataset)}\n")
    
    # Get first 5 entries to see the structure
    print("Sample entries:")
    for i, entry in enumerate(list(dataset)[:5]):
        print(f"\nEntry {i+1}:")
        print(f"  Model: {entry.get('fullname', entry.get('Model', 'N/A'))}")
        print(f"  Average: {entry.get('Average ⬆️', entry.get('Average', 'N/A'))}")
        print(f"  Type: {entry.get('Type', 'N/A')}")
        print(f"  Available fields: {list(entry.keys())}")
        
        # Check for individual benchmark scores
        benchmarks = ['ARC', 'HellaSwag', 'MMLU', 'TruthfulQA', 'Winogrande', 'GSM8K']
        print("  Benchmark scores:")
        for bench in benchmarks:
            if bench in entry:
                print(f"    {bench}: {entry[bench]}")
    
    # Find top models by average score
    print("\n\nTop 10 models by average score:")
    sorted_models = sorted(dataset, key=lambda x: float(x.get('Average ⬆️', 0)), reverse=True)
    
    for i, model in enumerate(sorted_models[:10]):
        avg_score = model.get('Average ⬆️', 0)
        model_name = model.get('fullname', model.get('Model', 'Unknown'))
        print(f"{i+1}. {model_name}: {avg_score}")
        
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc() 