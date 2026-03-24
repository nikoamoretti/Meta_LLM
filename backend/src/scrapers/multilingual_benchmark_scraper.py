"""
Multilingual Benchmark Scraper
Scrapes multilingual AI model evaluation data from C-Eval and other sources
"""
import requests
from bs4 import BeautifulSoup
import json
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)

class MultilingualBenchmarkScraper:
    """Scraper for multilingual AI model benchmarks"""
    
    def __init__(self):
        self.sources = {
            'c_eval': {
                'url': 'https://cevalbenchmark.com/static/leaderboard.html',
                'name': 'C-Eval Chinese Benchmark'
            },
            'multilingual_mmlu_hf': {
                'url': 'https://huggingface.co/spaces/StarscreamDeceptions/Multilingual-MMLU-Benchmark-Leaderboard',
                'name': 'Multilingual MMLU Leaderboard'
            }
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def scrape_c_eval_benchmark(self) -> List[Dict]:
        """Scrape C-Eval Chinese benchmark"""
        logger.info("Scraping C-Eval Chinese benchmark...")
        models = []
        
        try:
            response = requests.get(self.sources['c_eval']['url'], headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for leaderboard tables
            tables = soup.find_all('table')
            
            for table in tables:
                # Look for header row to identify the right table
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                    
                    # Check if this looks like the main leaderboard
                    if any('Model' in h for h in headers) and any('Avg' in h for h in headers):
                        
                        # Process data rows
                        rows = table.find_all('tr')[1:]  # Skip header
                        
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 6:  # Expect: #, Model, Creator, Access, Date, Avg, Avg(Hard), STEM, Social, Humanities, Others
                                try:
                                    # Extract model information
                                    rank_text = cells[0].get_text(strip=True) if cells[0] else ""
                                    model_text = cells[1].get_text(strip=True) if cells[1] else ""
                                    creator_text = cells[2].get_text(strip=True) if cells[2] else ""
                                    avg_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                                    avg_hard_text = cells[5].get_text(strip=True) if len(cells) > 5 else ""
                                    stem_text = cells[6].get_text(strip=True) if len(cells) > 6 else ""
                                    social_text = cells[7].get_text(strip=True) if len(cells) > 7 else ""
                                    humanities_text = cells[8].get_text(strip=True) if len(cells) > 8 else ""
                                    others_text = cells[9].get_text(strip=True) if len(cells) > 9 else ""
                                    
                                    # Skip empty or header rows
                                    if not model_text or 'Model' in model_text:
                                        continue
                                    
                                    # Extract numeric scores
                                    def extract_score(text):
                                        if not text or text == '-':
                                            return None
                                        match = re.search(r'(\d+\.?\d*)%?', text)
                                        return float(match.group(1)) if match else None
                                    
                                    avg_score = extract_score(avg_text)
                                    avg_hard_score = extract_score(avg_hard_text)
                                    stem_score = extract_score(stem_text)
                                    social_score = extract_score(social_text)
                                    humanities_score = extract_score(humanities_text)
                                    others_score = extract_score(others_text)
                                    
                                    # Only include if we have at least the average score
                                    if avg_score is not None and model_text:
                                        scores = {
                                            'c_eval_average': avg_score,
                                        }
                                        
                                        if avg_hard_score is not None:
                                            scores['c_eval_hard'] = avg_hard_score
                                        if stem_score is not None:
                                            scores['c_eval_stem'] = stem_score
                                        if social_score is not None:
                                            scores['c_eval_social_science'] = social_score
                                        if humanities_score is not None:
                                            scores['c_eval_humanities'] = humanities_score
                                        if others_score is not None:
                                            scores['c_eval_others'] = others_score
                                        
                                        models.append({
                                            'model': model_text,
                                            'organization': creator_text if creator_text else 'Unknown',
                                            'scores': scores,
                                            'source': 'C-Eval Chinese Benchmark',
                                            'category': 'multilingual',
                                            'scraped_at': datetime.now().isoformat()
                                        })
                                        
                                except (ValueError, IndexError, AttributeError) as e:
                                    logger.debug(f"Error parsing C-Eval row: {e}")
                                    continue
                        
                        break  # Found the main table, stop looking
            
            logger.info(f"✅ Scraped {len(models)} models from C-Eval")
            return models
            
        except Exception as e:
            logger.error(f"❌ Error scraping C-Eval: {e}")
            return []
    
    def get_static_multilingual_data(self) -> List[Dict]:
        """Fallback static data based on research"""
        logger.info("Using static multilingual benchmark data as fallback...")
        
        # Based on C-Eval benchmark results from research
        static_models = [
            {
                'model': 'GPT-4',
                'organization': 'OpenAI',
                'scores': {
                    'c_eval_average': 66.4,
                    'c_eval_stem': 65.2,
                    'c_eval_social_science': 74.7,
                    'c_eval_humanities': 62.5,
                    'c_eval_others': 64.7
                },
                'source': 'C-Eval Chinese Benchmark (Static)',
                'category': 'multilingual'
            },
            {
                'model': 'ChatGPT',
                'organization': 'OpenAI',
                'scores': {
                    'c_eval_average': 51.0,
                    'c_eval_stem': 49.0,
                    'c_eval_social_science': 58.0,
                    'c_eval_humanities': 48.8,
                    'c_eval_others': 50.4
                },
                'source': 'C-Eval Chinese Benchmark (Static)',
                'category': 'multilingual'
            },
            {
                'model': 'Claude-v1.3',
                'organization': 'Anthropic',
                'scores': {
                    'c_eval_average': 50.5,
                    'c_eval_stem': 48.5,
                    'c_eval_social_science': 58.6,
                    'c_eval_humanities': 47.3,
                    'c_eval_others': 50.1
                },
                'source': 'C-Eval Chinese Benchmark (Static)',
                'category': 'multilingual'
            },
            {
                'model': 'Bloomz-mt-176B',
                'organization': 'BigScience',
                'scores': {
                    'c_eval_average': 44.3,
                    'c_eval_stem': 39.1,
                    'c_eval_social_science': 53.0,
                    'c_eval_humanities': 47.7,
                    'c_eval_others': 42.7
                },
                'source': 'C-Eval Chinese Benchmark (Static)',
                'category': 'multilingual'
            },
            {
                'model': 'GLM-130B',
                'organization': 'Tsinghua',
                'scores': {
                    'c_eval_average': 44.0,
                    'c_eval_stem': 36.7,
                    'c_eval_social_science': 55.8,
                    'c_eval_humanities': 47.7,
                    'c_eval_others': 43.0
                },
                'source': 'C-Eval Chinese Benchmark (Static)',
                'category': 'multilingual'
            },
            {
                'model': 'Claude-instant-v1.0',
                'organization': 'Anthropic',
                'scores': {
                    'c_eval_average': 40.6,
                    'c_eval_stem': 38.6,
                    'c_eval_social_science': 47.6,
                    'c_eval_humanities': 39.5,
                    'c_eval_others': 39.0
                },
                'source': 'C-Eval Chinese Benchmark (Static)',
                'category': 'multilingual'
            },
            {
                'model': 'ChatGLM-6B',
                'organization': 'Tsinghua',
                'scores': {
                    'c_eval_average': 38.9,
                    'c_eval_stem': 33.3,
                    'c_eval_social_science': 48.3,
                    'c_eval_humanities': 41.3,
                    'c_eval_others': 38.0
                },
                'source': 'C-Eval Chinese Benchmark (Static)',
                'category': 'multilingual'
            },
            {
                'model': 'LLaMA-65B',
                'organization': 'Meta',
                'scores': {
                    'c_eval_average': 34.7,
                    'c_eval_stem': 32.6,
                    'c_eval_social_science': 41.2,
                    'c_eval_humanities': 34.1,
                    'c_eval_others': 33.0
                },
                'source': 'C-Eval Chinese Benchmark (Static)',
                'category': 'multilingual'
            },
            {
                'model': 'MOSS',
                'organization': 'Fudan',
                'scores': {
                    'c_eval_average': 33.1,
                    'c_eval_stem': 31.6,
                    'c_eval_social_science': 37.0,
                    'c_eval_humanities': 33.4,
                    'c_eval_others': 32.1
                },
                'source': 'C-Eval Chinese Benchmark (Static)',
                'category': 'multilingual'
            },
            {
                'model': 'Chinese-Alpaca-13B',
                'organization': 'Chinese-LLaMA-Alpaca',
                'scores': {
                    'c_eval_average': 30.9,
                    'c_eval_stem': 27.4,
                    'c_eval_social_science': 39.2,
                    'c_eval_humanities': 32.5,
                    'c_eval_others': 28.0
                },
                'source': 'C-Eval Chinese Benchmark (Static)',
                'category': 'multilingual'
            },
            {
                'model': 'Chinese-LLaMA-13B',
                'organization': 'Chinese-LLaMA-Alpaca',
                'scores': {
                    'c_eval_average': 29.6,
                    'c_eval_stem': 28.8,
                    'c_eval_social_science': 32.9,
                    'c_eval_humanities': 29.7,
                    'c_eval_others': 28.0
                },
                'source': 'C-Eval Chinese Benchmark (Static)',
                'category': 'multilingual'
            }
        ]
        
        # Add timestamp
        for model in static_models:
            model['scraped_at'] = datetime.now().isoformat()
        
        logger.info(f"✅ Loaded {len(static_models)} static multilingual models")
        return static_models
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Main scraping method"""
        logger.info("🌍 Starting Multilingual Benchmark scraping...")
        
        all_models = []
        
        # Try scraping C-Eval first
        c_eval_models = self.scrape_c_eval_benchmark()
        if c_eval_models:
            all_models.extend(c_eval_models)
        
        # Add small delay between requests
        time.sleep(2)
        
        # If no dynamic data was scraped, use static fallback
        if not all_models:
            logger.warning("⚠️  No dynamic data scraped, using static fallback")
            all_models = self.get_static_multilingual_data()
        
        # Deduplicate models by name
        seen_models = set()
        unique_models = []
        
        for model in all_models:
            model_key = model['model'].lower().replace(' ', '').replace('-', '')
            if model_key not in seen_models:
                seen_models.add(model_key)
                unique_models.append(model)
        
        logger.info(f"✅ Multilingual benchmark scraping complete: {len(unique_models)} unique models")
        
        return {
            'multilingual_evaluation': unique_models
        }

def main():
    """Test the scraper"""
    logging.basicConfig(level=logging.INFO)
    
    scraper = MultilingualBenchmarkScraper()
    data = scraper.scrape_all()
    
    print(f"\n🌍 MULTILINGUAL BENCHMARK SCRAPING RESULTS")
    print("=" * 50)
    
    if 'multilingual_evaluation' in data:
        models = data['multilingual_evaluation']
        print(f"Total Models: {len(models)}")
        
        print(f"\n🏆 Top 10 Models:")
        for i, model in enumerate(models[:10], 1):
            score = model['scores'].get('c_eval_average', 'N/A')
            print(f"{i:2d}. {model['model']:<30} {score}%")
        
        # Save to file
        with open('multilingual_benchmark_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n💾 Data saved to multilingual_benchmark_data.json")

if __name__ == "__main__":
    main() 