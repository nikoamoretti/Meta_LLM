"""
EvalPlus Leaderboard Scraper
Scrapes real coding performance data from EvalPlus leaderboard
URL: https://evalplus.github.io/leaderboard
"""

import requests
from bs4 import BeautifulSoup
import json
import logging
import re
from typing import List, Dict, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EvalPlusLeaderboardScraper:
    """Simple scraper for EvalPlus Leaderboard"""
    
    def __init__(self):
        self.base_url = "https://evalplus.github.io/leaderboard"
        self.json_url = "https://evalplus.github.io/results.json"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
    def normalize_model_name(self, raw_name: str) -> str:
        """Normalize model names to match our database format"""
        name = raw_name.strip()
        
        # Handle special cases for model name normalization
        if name.lower().startswith('o3'):
            if 'mini' in name.lower():
                return 'o3-mini'
            else:
                return 'o3'
        
        # Handle Claude variants
        if 'claude-opus-4' in name.lower() or 'claude opus 4' in name.lower():
            return 'Claude 4 Opus'
        elif 'claude-sonnet-4' in name.lower() or 'claude sonnet 4' in name.lower():
            return 'Claude 4 Sonnet'
        elif 'claude-3-5-sonnet' in name.lower():
            return 'Claude 3.5 Sonnet'
        
        # Handle common model variations
        name_mappings = {
            'gpt-4o': 'GPT-4o',
            'gpt-4o-mini': 'GPT-4o mini', 
            'gpt-4-turbo': 'GPT-4 Turbo',
            'gpt-4': 'GPT-4',
            'codestral': 'Codestral',
            'deepseek-coder': 'DeepSeek Coder',
            'gemini-1.5-pro': 'Gemini 1.5 Pro',
            'gemini-2.0-flash': 'Gemini 2.0 Flash',
            'llama-3.1': 'Llama 3.1'
        }
        
        lower_name = name.lower()
        for key, normalized in name_mappings.items():
            if key in lower_name:
                return normalized
                
        # Clean up formatting
        name = re.sub(r'-(\\d+)', r' \\1', name)
        name = re.sub(r'_', ' ', name)
        name = re.sub(r'\\s+', ' ', name)
        
        # Capitalize appropriately
        words = name.split()
        capitalized_words = []
        for word in words:
            if word.lower() in ['gpt', 'llm', 'ai', 'api']:
                capitalized_words.append(word.upper())
            elif any(char.isdigit() for char in word):
                capitalized_words.append(word)
            else:
                capitalized_words.append(word.capitalize())
                
        return ' '.join(capitalized_words)
    
    def scrape_json_data(self) -> List[Dict]:
        """Scrape data directly from JSON file"""
        extracted_data = []
        
        try:
            logger.info(f"Fetching JSON data from {self.json_url}")
            response = requests.get(self.json_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully loaded JSON data from {self.json_url}")
            
            # Process EvalPlus JSON structure
            # Expected structure: {"model_name": {"humaneval": {"base": score, "plus": score}, "mbpp": {"base": score, "plus": score}}}
            for model_name, model_data in data.items():
                if not isinstance(model_data, dict):
                    continue
                
                normalized_name = self.normalize_model_name(model_name)
                
                # Extract scores for different benchmarks and test types
                for benchmark, benchmark_data in model_data.items():
                    if not isinstance(benchmark_data, dict):
                        continue
                    
                    # Handle different test types (base, plus)
                    for test_type, score in benchmark_data.items():
                        if isinstance(score, (int, float)):
                            # Convert to percentage if needed (EvalPlus uses 0-1 scale)
                            if score <= 1:
                                score = score * 100
                            
                            metric_name = f"{benchmark}_{test_type}"
                            
                            extracted_data.append({
                                'model_name': normalized_name,
                                'raw_model_name': model_name,
                                'score': float(score),
                                'metric': metric_name,
                                'benchmark': 'EvalPlus',
                                'source_url': self.json_url
                            })
                            
                            logger.info(f"Extracted: {normalized_name} = {score:.1f}% ({metric_name})")
            
            logger.info(f"Extracted {len(extracted_data)} entries from JSON")
            return self._deduplicate_models(extracted_data)
            
        except Exception as e:
            logger.error(f"Failed to fetch JSON from {self.json_url}: {e}")
            return []
    
    def scrape_with_requests(self) -> List[Dict]:
        """Fallback to HTML scraping if JSON fails"""
        try:
            logger.info(f"Trying HTML scraping for {self.base_url}")
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for tables
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables")
            
            extracted_data = []
            
            for table_index, table in enumerate(tables):
                # Get all rows
                rows = table.find_all('tr')
                if len(rows) < 2:  # Need at least header + 1 data row
                    continue
                
                # Try to identify header row
                header_row = rows[0]
                header_cells = header_row.find_all(['th', 'td'])
                header_texts = [cell.get_text().strip().lower() for cell in header_cells]
                
                logger.info(f"Table {table_index} headers: {header_texts}")
                
                # Find model and score columns
                model_col = None
                score_cols = []
                
                for i, header in enumerate(header_texts):
                    if any(keyword in header for keyword in ['model', 'name']):
                        model_col = i
                    elif any(keyword in header for keyword in ['humaneval', 'mbpp', 'pass@1', 'score', '%']):
                        score_cols.append((i, header))
                
                if model_col is None or not score_cols:
                    continue
                
                logger.info(f"Found model column at {model_col}, score columns: {score_cols}")
                
                # Extract data rows
                data_rows = rows[1:]  # Skip header
                for row_index, row in enumerate(data_rows):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) <= max([model_col] + [col for col, _ in score_cols]):
                        continue
                    
                    # Get model name
                    model_cell = cells[model_col]
                    model_name = model_cell.get_text().strip()
                    
                    # Skip empty or header-like entries
                    if not model_name or model_name.lower() in ['model', 'name', 'rank']:
                        continue
                    
                    # Extract scores
                    for score_col, score_header in score_cols:
                        if len(cells) <= score_col:
                            continue
                        
                        score_cell = cells[score_col]
                        score_text = score_cell.get_text().strip()
                        
                        # Extract numeric score
                        score_match = re.search(r'(\d+\.?\d*)', score_text)
                        if not score_match:
                            continue
                        
                        score = float(score_match.group(1))
                        
                        # Convert to percentage if needed
                        if score <= 1 and '%' not in score_text:
                            score = score * 100
                        
                        normalized_name = self.normalize_model_name(model_name)
                        
                        extracted_data.append({
                            'model_name': normalized_name,
                            'raw_model_name': model_name,
                            'score': score,
                            'metric': score_header,
                            'benchmark': 'EvalPlus',
                            'source_url': self.base_url
                        })
                        
                        logger.info(f"Extracted: {normalized_name} = {score}% ({score_header})")
                        break  # Only take first valid score per model
                
                if extracted_data:
                    break
            
            return self._deduplicate_models(extracted_data)
            
        except Exception as e:
            logger.error(f"HTML scraping failed: {e}")
            return []
    
    def scrape_leaderboard_data(self) -> List[Dict]:
        """Scrape EvalPlus leaderboard data"""
        
        # Try JSON data first
        logger.info("Attempting to fetch JSON data directly...")
        json_data = self.scrape_json_data()
        if json_data:
            logger.info(f"✅ Successfully extracted {len(json_data)} models from JSON")
            return json_data
        
        # Fallback to HTML scraping
        logger.info("JSON failed, falling back to HTML scraping...")
        html_data = self.scrape_with_requests()
        if html_data:
            logger.info(f"✅ Successfully extracted {len(html_data)} models from HTML")
            return html_data
        
        logger.error("Failed to scrape any EvalPlus leaderboard data")
        return []
    
    def _deduplicate_models(self, data: List[Dict]) -> List[Dict]:
        """Deduplicate models by normalized name, keeping highest score per metric"""
        model_groups = {}
        
        for model_data in data:
            key = (model_data['model_name'], model_data['metric'])
            if key not in model_groups:
                model_groups[key] = []
            model_groups[key].append(model_data)
        
        deduplicated = []
        for (model_name, metric), models in model_groups.items():
            if len(models) == 1:
                deduplicated.append(models[0])
            else:
                best_model = max(models, key=lambda x: x['score'])
                logger.info(f"Deduplicated {model_name} ({metric}): kept score {best_model['score']} from {len(models)} variants")
                deduplicated.append(best_model)
        
        return deduplicated
    
    def save_to_json(self, data: List[Dict], filename: str = None) -> str:
        """Save scraped data to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evalplus_leaderboard_{timestamp}.json"
        
        output_data = {
            'source': 'evalplus.github.io/leaderboard',
            'scraped_at': datetime.now().isoformat(),
            'total_models': len(data),
            'benchmark_info': {
                'name': 'EvalPlus Leaderboard',
                'description': 'Enhanced coding evaluation with HumanEval+ and MBPP+',
                'metric': 'Pass@1 score on base and plus test sets'
            },
            'models': data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(data)} model scores to {filename}")
        return filename

def main():
    """Main function to run the scraper"""
    scraper = EvalPlusLeaderboardScraper()
    
    # Scrape the data
    data = scraper.scrape_leaderboard_data()
    
    if data:
        # Save to JSON file
        filename = scraper.save_to_json(data)
        
        # Print summary
        print(f"\\n✅ Successfully scraped EvalPlus leaderboard!")
        print(f"📊 Found {len(data)} model scores")
        print(f"💾 Saved to: {filename}")
        print(f"\\nTop 5 models:")
        
        # Sort by score and show top 5
        sorted_data = sorted(data, key=lambda x: x['score'], reverse=True)
        for i, model in enumerate(sorted_data[:5], 1):
            print(f"  {i}. {model['model_name']}: {model['score']:.1f}% ({model['metric']})")
    else:
        print("❌ Failed to scrape any data from EvalPlus leaderboard")

if __name__ == "__main__":
    main()