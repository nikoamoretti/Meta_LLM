"""
Safety and Alignment Benchmark Scraper
Scrapes AI safety and alignment evaluation data from Phare and other sources
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

class SafetyAlignmentScraper:
    """Scraper for AI safety and alignment benchmarks"""
    
    def __init__(self):
        self.sources = {
            'phare_benchmark': {
                'url': 'https://phare.giskard.ai/',
                'name': 'Phare LLM Safety Benchmark'
            },
            'hf_safety_leaderboard': {
                'url': 'https://huggingface.co/spaces/AI-Secure/llm-trustworthy-leaderboard',
                'name': 'LLM Safety Leaderboard'
            }
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def scrape_phare_benchmark(self) -> List[Dict]:
        """Scrape Phare LLM safety benchmark"""
        logger.info("Scraping Phare LLM safety benchmark...")
        models = []
        
        try:
            response = requests.get(self.sources['phare_benchmark']['url'], headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for leaderboard tables
            tables = soup.find_all('table')
            
            for table in tables:
                # Look for header row to identify the right table
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                    
                    # Check if this looks like the main safety leaderboard
                    if any('Model' in h for h in headers) and any('Safety' in h for h in headers):
                        
                        # Process data rows
                        rows = table.find_all('tr')[1:]  # Skip header
                        
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 5:  # Expect: Rank, Model, Provider, Overall Safety, etc.
                                try:
                                    # Extract model information
                                    rank_text = cells[0].get_text(strip=True) if cells[0] else ""
                                    model_text = cells[1].get_text(strip=True) if cells[1] else ""
                                    provider_text = cells[2].get_text(strip=True) if cells[2] else ""
                                    overall_safety_text = cells[3].get_text(strip=True) if cells[3] else ""
                                    hallucination_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                                    harm_text = cells[5].get_text(strip=True) if len(cells) > 5 else ""
                                    bias_text = cells[6].get_text(strip=True) if len(cells) > 6 else ""
                                    
                                    # Skip empty or header rows
                                    if not model_text or 'Model' in model_text:
                                        continue
                                    
                                    # Extract numeric scores (remove % and convert to float)
                                    def extract_score(text):
                                        if not text or text == '-':
                                            return None
                                        match = re.search(r'(\d+\.?\d*)%', text)
                                        return float(match.group(1)) if match else None
                                    
                                    overall_safety = extract_score(overall_safety_text)
                                    hallucination_resistance = extract_score(hallucination_text)
                                    harm_resistance = extract_score(harm_text)
                                    bias_resistance = extract_score(bias_text)
                                    
                                    # Clean model name (remove links, extra whitespace)
                                    model_name = re.sub(r'\[.*?\]', '', model_text).strip()
                                    
                                    # Only include if we have the main safety score
                                    if overall_safety is not None and model_name:
                                        scores = {
                                            'phare_overall_safety': overall_safety,
                                        }
                                        
                                        if hallucination_resistance is not None:
                                            scores['phare_hallucination_resistance'] = hallucination_resistance
                                        if harm_resistance is not None:
                                            scores['phare_harm_resistance'] = harm_resistance
                                        if bias_resistance is not None:
                                            scores['phare_bias_resistance'] = bias_resistance
                                        
                                        models.append({
                                            'model': model_name,
                                            'organization': provider_text if provider_text else 'Unknown',
                                            'scores': scores,
                                            'source': 'Phare LLM Safety Benchmark',
                                            'category': 'safety_alignment',
                                            'scraped_at': datetime.now().isoformat()
                                        })
                                        
                                except (ValueError, IndexError, AttributeError) as e:
                                    logger.debug(f"Error parsing Phare row: {e}")
                                    continue
                        
                        break  # Found the main table, stop looking
            
            logger.info(f"✅ Scraped {len(models)} models from Phare")
            return models
            
        except Exception as e:
            logger.error(f"❌ Error scraping Phare: {e}")
            return []
    
    def get_static_safety_data(self) -> List[Dict]:
        """Fallback static data based on research"""
        logger.info("Using static safety benchmark data as fallback...")
        
        # Based on Phare benchmark results from research
        static_models = [
            {
                'model': 'Gemini 1.5 Pro',
                'organization': 'Google',
                'scores': {
                    'phare_overall_safety': 87.29,
                    'phare_hallucination_resistance': 87.06,
                    'phare_harm_resistance': 96.84,
                    'phare_bias_resistance': 77.96
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'Claude 3.5 Haiku',
                'organization': 'Anthropic',
                'scores': {
                    'phare_overall_safety': 82.72,
                    'phare_hallucination_resistance': 86.97,
                    'phare_harm_resistance': 95.36,
                    'phare_bias_resistance': 65.81
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'Llama 3.1 405B',
                'organization': 'Meta',
                'scores': {
                    'phare_overall_safety': 77.59,
                    'phare_hallucination_resistance': 75.54,
                    'phare_harm_resistance': 86.49,
                    'phare_bias_resistance': 70.74
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'Llama 4 Maverick',
                'organization': 'Meta',
                'scores': {
                    'phare_overall_safety': 76.72,
                    'phare_hallucination_resistance': 77.02,
                    'phare_harm_resistance': 89.25,
                    'phare_bias_resistance': 63.89
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'Claude 3.5 Sonnet',
                'organization': 'Anthropic',
                'scores': {
                    'phare_overall_safety': 75.62,
                    'phare_hallucination_resistance': 91.09,
                    'phare_harm_resistance': 95.40,
                    'phare_bias_resistance': 40.37
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'Claude 3.7 Sonnet',
                'organization': 'Anthropic',
                'scores': {
                    'phare_overall_safety': 75.53,
                    'phare_hallucination_resistance': 89.26,
                    'phare_harm_resistance': 95.52,
                    'phare_bias_resistance': 41.82
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'Gemma 3 27B',
                'organization': 'Google',
                'scores': {
                    'phare_overall_safety': 75.23,
                    'phare_hallucination_resistance': 69.90,
                    'phare_harm_resistance': 91.36,
                    'phare_bias_resistance': 64.44
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'Gemini 2.0 Flash',
                'organization': 'Google',
                'scores': {
                    'phare_overall_safety': 74.89,
                    'phare_hallucination_resistance': 78.13,
                    'phare_harm_resistance': 94.30,
                    'phare_bias_resistance': 52.22
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'DeepSeek V3 (0324)',
                'organization': 'DeepSeek',
                'scores': {
                    'phare_overall_safety': 73.92,
                    'phare_hallucination_resistance': 77.86,
                    'phare_harm_resistance': 92.80,
                    'phare_bias_resistance': 51.11
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'GPT-4o',
                'organization': 'OpenAI',
                'scores': {
                    'phare_overall_safety': 72.80,
                    'phare_hallucination_resistance': 83.89,
                    'phare_harm_resistance': 92.66,
                    'phare_bias_resistance': 41.85
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'Qwen 2.5 Max',
                'organization': 'Alibaba',
                'scores': {
                    'phare_overall_safety': 72.71,
                    'phare_hallucination_resistance': 77.12,
                    'phare_harm_resistance': 89.89,
                    'phare_bias_resistance': 51.11
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'DeepSeek V3',
                'organization': 'DeepSeek',
                'scores': {
                    'phare_overall_safety': 70.77,
                    'phare_hallucination_resistance': 77.91,
                    'phare_harm_resistance': 89.00,
                    'phare_bias_resistance': 45.39
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'Llama 3.3 70B',
                'organization': 'Meta',
                'scores': {
                    'phare_overall_safety': 67.97,
                    'phare_hallucination_resistance': 73.41,
                    'phare_harm_resistance': 86.04,
                    'phare_bias_resistance': 44.44
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'Mistral Small 3.1 24B',
                'organization': 'Mistral',
                'scores': {
                    'phare_overall_safety': 67.88,
                    'phare_hallucination_resistance': 77.72,
                    'phare_harm_resistance': 90.91,
                    'phare_bias_resistance': 35.00
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'Mistral Large',
                'organization': 'Mistral',
                'scores': {
                    'phare_overall_safety': 66.00,
                    'phare_hallucination_resistance': 79.72,
                    'phare_harm_resistance': 89.38,
                    'phare_bias_resistance': 28.89
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'Grok 2',
                'organization': 'xAI',
                'scores': {
                    'phare_overall_safety': 65.15,
                    'phare_hallucination_resistance': 77.35,
                    'phare_harm_resistance': 91.44,
                    'phare_bias_resistance': 26.67
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            },
            {
                'model': 'GPT-4o Mini',
                'organization': 'OpenAI',
                'scores': {
                    'phare_overall_safety': 63.93,
                    'phare_hallucination_resistance': 74.50,
                    'phare_harm_resistance': 77.29,
                    'phare_bias_resistance': 40.00
                },
                'source': 'Phare LLM Safety Benchmark (Static)',
                'category': 'safety_alignment'
            }
        ]
        
        # Add timestamp
        for model in static_models:
            model['scraped_at'] = datetime.now().isoformat()
        
        logger.info(f"✅ Loaded {len(static_models)} static safety models")
        return static_models
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Main scraping method"""
        logger.info("🛡️ Starting Safety & Alignment Benchmark scraping...")
        
        all_models = []
        
        # Try scraping Phare first
        phare_models = self.scrape_phare_benchmark()
        if phare_models:
            all_models.extend(phare_models)
        
        # Add small delay between requests
        time.sleep(2)
        
        # If no dynamic data was scraped, use static fallback
        if not all_models:
            logger.warning("⚠️  No dynamic data scraped, using static fallback")
            all_models = self.get_static_safety_data()
        
        # Deduplicate models by name
        seen_models = set()
        unique_models = []
        
        for model in all_models:
            model_key = model['model'].lower().replace(' ', '').replace('-', '')
            if model_key not in seen_models:
                seen_models.add(model_key)
                unique_models.append(model)
        
        logger.info(f"✅ Safety & alignment benchmark scraping complete: {len(unique_models)} unique models")
        
        return {
            'safety_alignment': unique_models
        }

def main():
    """Test the scraper"""
    logging.basicConfig(level=logging.INFO)
    
    scraper = SafetyAlignmentScraper()
    data = scraper.scrape_all()
    
    print(f"\n🛡️ SAFETY & ALIGNMENT BENCHMARK SCRAPING RESULTS")
    print("=" * 50)
    
    if 'safety_alignment' in data:
        models = data['safety_alignment']
        print(f"Total Models: {len(models)}")
        
        print(f"\n🏆 Top 10 Models by Overall Safety:")
        for i, model in enumerate(models[:10], 1):
            score = model['scores'].get('phare_overall_safety', 'N/A')
            print(f"{i:2d}. {model['model']:<30} {score}%")
        
        # Save to file
        with open('safety_alignment_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n💾 Data saved to safety_alignment_data.json")

if __name__ == "__main__":
    main() 