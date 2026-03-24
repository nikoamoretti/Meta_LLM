"""
Math Benchmark Scraper
Scrapes mathematical reasoning benchmark data from multiple sources
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

class MathBenchmarkScraper:
    """Scraper for mathematical reasoning benchmarks"""
    
    def __init__(self):
        self.sources = {
            'vals_ai_math500': {
                'url': 'https://www.vals.ai/benchmarks/math500-03-24-2025',
                'name': 'VALS.AI MATH 500'
            },
            'paperswithcode_math': {
                'url': 'https://paperswithcode.com/sota/math-word-problem-solving-on-math',
                'name': 'Papers with Code MATH'
            }
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def scrape_vals_ai_math500(self) -> List[Dict]:
        """Scrape VALS.AI MATH 500 benchmark"""
        logger.info("Scraping VALS.AI MATH 500 benchmark...")
        models = []
        
        try:
            response = requests.get(self.sources['vals_ai_math500']['url'], headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for model data in tables or structured content
            # Based on the web search results, there should be a leaderboard table
            
            # Try to find table rows with model data
            table_rows = soup.find_all('tr')
            
            for row in table_rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 4:  # Expecting at least rank, model, accuracy, cost/latency
                    try:
                        # Extract model information
                        rank_text = cells[0].get_text(strip=True) if cells[0] else ""
                        model_text = cells[1].get_text(strip=True) if cells[1] else ""
                        accuracy_text = cells[2].get_text(strip=True) if cells[2] else ""
                        
                        # Skip header rows
                        if 'Model' in model_text or 'Rank' in rank_text:
                            continue
                        
                        # Extract rank
                        rank_match = re.search(r'(\d+)', rank_text)
                        if not rank_match:
                            continue
                        rank = int(rank_match.group(1))
                        
                        # Extract model name (remove badges/icons)
                        model_name = re.sub(r'[★⚡︎$]', '', model_text).strip()
                        if not model_name or len(model_name) < 2:
                            continue
                        
                        # Extract accuracy percentage
                        accuracy_match = re.search(r'(\d+\.?\d*)%', accuracy_text)
                        if not accuracy_match:
                            continue
                        accuracy = float(accuracy_match.group(1))
                        
                        models.append({
                            'model': model_name,
                            'scores': {
                                'math500_accuracy': accuracy,
                                'math500_rank': rank
                            },
                            'source': 'VALS.AI MATH 500',
                            'category': 'mathematical_reasoning',
                            'scraped_at': datetime.now().isoformat()
                        })
                        
                    except (ValueError, IndexError, AttributeError) as e:
                        logger.debug(f"Error parsing row: {e}")
                        continue
            
            # If table parsing didn't work, try alternative methods
            if not models:
                models = self._scrape_vals_ai_alternative(soup)
            
            logger.info(f"✅ Scraped {len(models)} models from VALS.AI MATH 500")
            return models
            
        except Exception as e:
            logger.error(f"❌ Error scraping VALS.AI MATH 500: {e}")
            return []
    
    def _scrape_vals_ai_alternative(self, soup: BeautifulSoup) -> List[Dict]:
        """Alternative parsing method for VALS.AI"""
        models = []
        
        try:
            # Look for model names and scores in the text content
            # From the search results, we know there are models like:
            # DeepSeek R1: 92.2%, o3 Mini: 91.8%, etc.
            
            page_text = soup.get_text()
            
            # Look for model performance patterns
            model_patterns = [
                r'DeepSeek.*?(\d+\.?\d*)%',
                r'o3.*?Mini.*?(\d+\.?\d*)%', 
                r'Claude.*?(\d+\.?\d*)%',
                r'o1.*?(\d+\.?\d*)%',
                r'Gemini.*?(\d+\.?\d*)%',
                r'Grok.*?(\d+\.?\d*)%',
                r'GPT.*?(\d+\.?\d*)%'
            ]
            
            rank = 1
            for pattern in model_patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    model_name = match.group(0).split(match.group(1))[0].strip().rstrip('%')
                    accuracy = float(match.group(1))
                    
                    # Clean up model name
                    model_name = re.sub(r'[^\w\s\-\.]', ' ', model_name).strip()
                    model_name = re.sub(r'\s+', ' ', model_name)
                    
                    if len(model_name) >= 3 and accuracy > 0:
                        models.append({
                            'model': model_name,
                            'scores': {
                                'math500_accuracy': accuracy,
                                'math500_rank': rank
                            },
                            'source': 'VALS.AI MATH 500',
                            'category': 'mathematical_reasoning',
                            'scraped_at': datetime.now().isoformat()
                        })
                        rank += 1
            
            # Remove duplicates based on model name
            seen_models = set()
            unique_models = []
            for model in models:
                model_key = model['model'].lower().replace(' ', '')
                if model_key not in seen_models:
                    seen_models.add(model_key)
                    unique_models.append(model)
            
            return unique_models[:20]  # Limit to top 20 models
            
        except Exception as e:
            logger.error(f"Alternative parsing failed: {e}")
            return []
    
    def scrape_paperswithcode_math(self) -> List[Dict]:
        """Scrape Papers with Code MATH benchmark"""
        logger.info("Scraping Papers with Code MATH benchmark...")
        models = []
        
        try:
            response = requests.get(self.sources['paperswithcode_math']['url'], headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for leaderboard or results table
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows[1:]:  # Skip header
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        try:
                            # Typical format: Model, Score, Paper/Date
                            model_cell = cells[0]
                            score_cell = cells[1]
                            
                            # Extract model name
                            model_name = model_cell.get_text(strip=True)
                            
                            # Extract score
                            score_text = score_cell.get_text(strip=True)
                            score_match = re.search(r'(\d+\.?\d*)', score_text)
                            
                            if model_name and score_match:
                                score = float(score_match.group(1))
                                
                                models.append({
                                    'model': model_name,
                                    'scores': {
                                        'math_dataset_score': score
                                    },
                                    'source': 'Papers with Code MATH',
                                    'category': 'mathematical_reasoning',
                                    'scraped_at': datetime.now().isoformat()
                                })
                                
                        except (ValueError, IndexError, AttributeError) as e:
                            logger.debug(f"Error parsing Papers with Code row: {e}")
                            continue
            
            logger.info(f"✅ Scraped {len(models)} models from Papers with Code MATH")
            return models
            
        except Exception as e:
            logger.error(f"❌ Error scraping Papers with Code MATH: {e}")
            return []
    
    def get_static_math_data(self) -> List[Dict]:
        """Fallback static data based on research"""
        logger.info("Using static math benchmark data as fallback...")
        
        # Based on the web search results from VALS.AI MATH 500
        static_models = [
            {
                'model': 'DeepSeek R1',
                'scores': {'math500_accuracy': 92.2, 'math500_rank': 1},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'OpenAI o3 Mini',
                'scores': {'math500_accuracy': 91.8, 'math500_rank': 2},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'Claude 3.7 Sonnet (Thinking)',
                'scores': {'math500_accuracy': 91.6, 'math500_rank': 3},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'OpenAI o1',
                'scores': {'math500_accuracy': 90.4, 'math500_rank': 4},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'Gemini 2.0 Flash (001)',
                'scores': {'math500_accuracy': 88.0, 'math500_rank': 5},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'Gemini 2.0 Flash Thinking Exp',
                'scores': {'math500_accuracy': 84.6, 'math500_rank': 6},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'Gemini 1.5 Pro (002)',
                'scores': {'math500_accuracy': 82.8, 'math500_rank': 7},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'Gemini 1.5 Flash (002)',
                'scores': {'math500_accuracy': 78.8, 'math500_rank': 8},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'Grok 2',
                'scores': {'math500_accuracy': 78.4, 'math500_rank': 9},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'Claude 3.7 Sonnet (Nonthinking)',
                'scores': {'math500_accuracy': 76.8, 'math500_rank': 10},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'GPT-4o',
                'scores': {'math500_accuracy': 74.0, 'math500_rank': 11},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'Claude 3.5 Sonnet',
                'scores': {'math500_accuracy': 72.6, 'math500_rank': 12},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'GPT-4o Mini',
                'scores': {'math500_accuracy': 69.2, 'math500_rank': 13},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'Llama 3.3 70B',
                'scores': {'math500_accuracy': 65.8, 'math500_rank': 14},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            },
            {
                'model': 'Claude 3.5 Haiku',
                'scores': {'math500_accuracy': 62.4, 'math500_rank': 15},
                'source': 'VALS.AI MATH 500 (Static)',
                'category': 'mathematical_reasoning'
            }
        ]
        
        # Add timestamp
        for model in static_models:
            model['scraped_at'] = datetime.now().isoformat()
        
        logger.info(f"✅ Loaded {len(static_models)} static math models")
        return static_models
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Main scraping method"""
        logger.info("🔢 Starting Math Benchmark scraping...")
        
        all_models = []
        
        # Try scraping VALS.AI first
        vals_models = self.scrape_vals_ai_math500()
        if vals_models:
            all_models.extend(vals_models)
        
        # Add small delay between requests
        time.sleep(2)
        
        # Try Papers with Code
        pwc_models = self.scrape_paperswithcode_math()
        if pwc_models:
            all_models.extend(pwc_models)
        
        # If no dynamic data was scraped, use static fallback
        if not all_models:
            logger.warning("⚠️  No dynamic data scraped, using static fallback")
            all_models = self.get_static_math_data()
        
        # Deduplicate models by name
        seen_models = set()
        unique_models = []
        
        for model in all_models:
            model_key = model['model'].lower().replace(' ', '').replace('-', '')
            if model_key not in seen_models:
                seen_models.add(model_key)
                unique_models.append(model)
        
        logger.info(f"✅ Math benchmark scraping complete: {len(unique_models)} unique models")
        
        return {
            'math_reasoning': unique_models
        }

def main():
    """Test the scraper"""
    logging.basicConfig(level=logging.INFO)
    
    scraper = MathBenchmarkScraper()
    data = scraper.scrape_all()
    
    print(f"\n📊 MATH BENCHMARK SCRAPING RESULTS")
    print("=" * 50)
    
    if 'math_reasoning' in data:
        models = data['math_reasoning']
        print(f"Total Models: {len(models)}")
        
        print(f"\n🏆 Top 10 Models:")
        for i, model in enumerate(models[:10], 1):
            score = model['scores'].get('math500_accuracy', 'N/A')
            print(f"{i:2d}. {model['model']:<30} {score}%")
        
        # Save to file
        with open('math_benchmark_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n💾 Data saved to math_benchmark_data.json")

if __name__ == "__main__":
    main() 