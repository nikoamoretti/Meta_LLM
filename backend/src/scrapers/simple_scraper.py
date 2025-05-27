"""
Simple scraper - just the ones that actually work
"""
import requests
from datasets import load_dataset
import logging

logger = logging.getLogger(__name__)

class SimpleScraper:
    """Just the scrapers that actually work"""
    
    def scrape_all(self):
        """Get data from all working sources"""
        all_results = {}
        
        # 1. HuggingFace - WORKS
        try:
            logger.info("Scraping HuggingFace...")
            dataset = load_dataset(
                "open-llm-leaderboard/contents",
                split="train",
                cache_dir=None
            )
            
            results = []
            for item in dataset:
                model_data = {
                    'model': item.get('fullname', 'Unknown'),
                    'scores': {
                        'arc': item.get('ARC', 0),
                        'hellaswag': item.get('HellaSwag', 0),
                        'mmlu': item.get('MMLU', 0),
                        'truthfulqa': item.get('TruthfulQA', 0),
                        'winogrande': item.get('Winogrande', 0),
                        'gsm8k': item.get('GSM8K', 0),
                        'average': item.get('Average', 0)
                    },
                    'source': 'HuggingFace Open LLM'
                }
                results.append(model_data)
            
            all_results['huggingface'] = results
            logger.info(f"HuggingFace: {len(results)} models")
            
        except Exception as e:
            logger.error(f"HuggingFace failed: {e}")
            all_results['huggingface'] = []
        
        # 2. OpenRouter - WORKS
        try:
            logger.info("Scraping OpenRouter...")
            response = requests.get('https://openrouter.ai/api/v1/models')
            if response.status_code == 200:
                data = response.json()
                
                results = []
                for model in data.get('data', []):
                    # Only include models with pricing
                    if model.get('pricing'):
                        model_data = {
                            'model': model['id'],
                            'scores': {
                                'context_length': model.get('context_length', 0),
                                'cost_per_million': float(model['pricing'].get('prompt', 0)) * 1000
                            },
                            'source': 'OpenRouter'
                        }
                        results.append(model_data)
                
                all_results['openrouter'] = results
                logger.info(f"OpenRouter: {len(results)} models")
            else:
                all_results['openrouter'] = []
                
        except Exception as e:
            logger.error(f"OpenRouter failed: {e}")
            all_results['openrouter'] = []
        
        # 3. LMSYS - WORKS (but limited)
        try:
            logger.info("Scraping LMSYS...")
            dataset = load_dataset(
                "lmsys/lmsys-arena-human-preference-55k",
                split="train",
                streaming=True
            )
            
            # Just get win rates from first 10k battles
            model_wins = {}
            model_battles = {}
            
            for i, item in enumerate(dataset):
                if i >= 10000:  # Limit to 10k for speed
                    break
                    
                model_a = item.get('model_a', '')
                model_b = item.get('model_b', '')
                winner = item.get('winner', '')
                
                # Initialize
                for model in [model_a, model_b]:
                    if model and model not in model_battles:
                        model_battles[model] = 0
                        model_wins[model] = 0
                
                # Count battles
                if model_a:
                    model_battles[model_a] += 1
                if model_b:
                    model_battles[model_b] += 1
                
                # Count wins
                if winner == 'model_a' and model_a:
                    model_wins[model_a] += 1
                elif winner == 'model_b' and model_b:
                    model_wins[model_b] += 1
            
            # Calculate win rates
            results = []
            for model, battles in model_battles.items():
                if battles >= 50:  # Only include models with 50+ battles
                    win_rate = (model_wins[model] / battles) * 100
                    model_data = {
                        'model': model,
                        'scores': {
                            'win_rate': win_rate,
                            'total_battles': battles
                        },
                        'source': 'LMSYS Arena'
                    }
                    results.append(model_data)
            
            all_results['lmsys'] = results
            logger.info(f"LMSYS: {len(results)} models")
            
        except Exception as e:
            logger.error(f"LMSYS failed: {e}")
            all_results['lmsys'] = []
        
        return all_results 