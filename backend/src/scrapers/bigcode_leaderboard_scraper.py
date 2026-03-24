"""
Simple BigCode Models Leaderboard Scraper
Scrapes real coding performance data from BigCode leaderboards
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

class BigCodeLeaderboardScraper:
    """Simple scraper for BigCode Models Leaderboard"""
    
    def __init__(self):
        # Direct JSON data URLs from BigCodeBench
        self.json_urls = [
            "https://bigcode-bench.github.io/results-hard.json",
            "https://bigcode-bench.github.io/results.json"
        ]
        self.fallback_urls = [
            "https://huggingface.co/spaces/bigcode/bigcodebench-leaderboard",
            "https://bigcode-bench.github.io/",
            "https://huggingface.co/spaces/bigcode/bigcode-models-leaderboard"
        ]
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
        """Scrape data directly from JSON files"""
        extracted_data = []
        
        for json_url in self.json_urls:
            try:
                logger.info(f"Fetching JSON data from {json_url}")
                response = requests.get(json_url, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Successfully loaded JSON data from {json_url}")
                
                # Process BigCodeBench JSON structure
                if isinstance(data, dict):
                    # Handle the structure: {"model_name": {"pass@1": {"instruct": score, "complete": score}, ...}}
                    for model_name, model_data in data.items():
                        if isinstance(model_data, dict):
                            # Extract pass@1 scores
                            if 'pass@1' in model_data and isinstance(model_data['pass@1'], dict):
                                pass_at_1_data = model_data['pass@1']
                                
                                # Extract instruct and complete scores
                                for metric, score in pass_at_1_data.items():
                                    if isinstance(score, (int, float)):
                                        normalized_name = self.normalize_model_name(model_name)
                                        
                                        extracted_data.append({
                                            'model_name': normalized_name,
                                            'raw_model_name': model_name,
                                            'score': float(score),
                                            'metric': f'pass@1_{metric}',
                                            'benchmark': 'BigCodeBench',
                                            'source_url': json_url
                                        })
                                        
                                        logger.info(f"Extracted: {normalized_name} = {score}% (pass@1_{metric})")
                            
                            # Also check for direct score fields
                            score_fields = ['score', 'average', 'complete', 'instruct']
                            for field in score_fields:
                                if field in model_data and isinstance(model_data[field], (int, float)):
                                    score = float(model_data[field])
                                    normalized_name = self.normalize_model_name(model_name)
                                    
                                    extracted_data.append({
                                        'model_name': normalized_name,
                                        'raw_model_name': model_name,
                                        'score': score,
                                        'metric': field,
                                        'benchmark': 'BigCodeBench',
                                        'source_url': json_url
                                    })
                                    
                                    logger.info(f"Extracted: {normalized_name} = {score}% ({field})")
                
                logger.info(f"Extracted {len(extracted_data)} entries from {json_url}")
                
            except Exception as e:
                logger.error(f"Failed to fetch JSON from {json_url}: {e}")
                continue
        
        return self._deduplicate_models(extracted_data)
    
    def scrape_leaderboard_data(self) -> List[Dict]:
        """Scrape BigCode leaderboard data"""
        
        # Try JSON data first
        logger.info("Attempting to fetch JSON data directly...")
        json_data = self.scrape_json_data()
        if json_data:
            logger.info(f"✅ Successfully extracted {len(json_data)} models from JSON")
            return json_data
        
        # Fallback to HTML scraping
        logger.info("JSON failed, falling back to HTML scraping...")
        for url in self.fallback_urls:
            try:
                logger.info(f"Trying to scrape {url}")
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                # Check if we got valid content
                if len(response.content) < 1000:
                    logger.warning(f"Response too small for {url}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for content that indicates this is a leaderboard
                text_content = soup.get_text().lower()
                if not any(keyword in text_content for keyword in ['leaderboard', 'model', 'score', 'benchmark']):
                    logger.warning(f"No leaderboard content found in {url}")
                    continue
                
                logger.info(f"Found leaderboard content in {url}")
                
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
                        elif any(keyword in header for keyword in ['pass@1', 'score', 'complete', 'instruct', '%', 'humaneval', 'mbpp']):
                            score_cols.append((i, header))
                    
                    if model_col is None:
                        logger.info(f"No model column found in table {table_index}")
                        continue
                    
                    if not score_cols:
                        logger.info(f"No score columns found in table {table_index}")
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
                        if not model_name or model_name.lower() in ['model', 'name', 'architecture']:
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
                                'benchmark': 'BigCode Leaderboard',
                                'source_url': url
                            })
                            
                            logger.info(f"Extracted: {normalized_name} = {score}% ({score_header})")
                            break  # Only take first valid score per model
                    
                    if extracted_data:
                        logger.info(f"Successfully extracted {len(extracted_data)} entries from {url}")
                        return self._deduplicate_models(extracted_data)
                
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
                continue
        
        logger.error("Failed to scrape any BigCode leaderboard")
        return []
    
    def _deduplicate_models(self, data: List[Dict]) -> List[Dict]:
        """Deduplicate models by normalized name, keeping highest score"""
        model_groups = {}
        
        for model_data in data:
            normalized_name = model_data['model_name']
            if normalized_name not in model_groups:
                model_groups[normalized_name] = []
            model_groups[normalized_name].append(model_data)
        
        deduplicated = []
        for normalized_name, models in model_groups.items():
            if len(models) == 1:
                deduplicated.append(models[0])
            else:
                best_model = max(models, key=lambda x: x['score'])
                logger.info(f"Deduplicated {normalized_name}: kept score {best_model['score']} from {len(models)} variants")
                deduplicated.append(best_model)
        
        return deduplicated
    
    def save_to_json(self, data: List[Dict], filename: str = None) -> str:
        """Save scraped data to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bigcode_leaderboard_{timestamp}.json"
        
        output_data = {
            'source': 'BigCode leaderboards (multiple sources)',
            'scraped_at': datetime.now().isoformat(),
            'total_models': len(data),
            'benchmark_info': {
                'name': 'BigCode Models Leaderboard',
                'description': 'Code generation performance evaluation',
                'metric': 'Pass@1 score'
            },
            'models': data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(data)} model scores to {filename}")
        return filename

def main():
    """Main function to run the scraper"""
    scraper = BigCodeLeaderboardScraper()
    
    # Scrape the data
    data = scraper.scrape_leaderboard_data()
    
    if data:
        # Save to JSON file
        filename = scraper.save_to_json(data)
        
        # Print summary
        print(f"\\n✅ Successfully scraped BigCode leaderboard!")
        print(f"📊 Found {len(data)} models")
        print(f"💾 Saved to: {filename}")
        print(f"\\nTop 5 models:")
        
        # Sort by score and show top 5
        sorted_data = sorted(data, key=lambda x: x['score'], reverse=True)
        for i, model in enumerate(sorted_data[:5], 1):
            print(f"  {i}. {model['model_name']}: {model['score']}%")
    else:
        print("❌ Failed to scrape any data from BigCode leaderboard")

if __name__ == "__main__":
    main()