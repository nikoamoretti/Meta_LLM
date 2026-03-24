"""
Convex.dev Code LB Scraper
Scrapes real coding performance data from Convex LLM leaderboard
URL: https://www.convex.dev/llm-leaderboard
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

class ConvexLeaderboardScraper:
    """Simple scraper for Convex.dev LLM Leaderboard"""
    
    def __init__(self):
        self.base_url = "https://www.convex.dev/llm-leaderboard"
        self.github_url = "https://github.com/get-convex/convex-evals"
        self.potential_data_urls = [
            "https://www.convex.dev/api/leaderboard",
            "https://www.convex.dev/llm-leaderboard/data.json",
            "https://raw.githubusercontent.com/get-convex/convex-evals/main/results.json"
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
    
    def try_json_endpoints(self) -> List[Dict]:
        """Try to find JSON data from potential API endpoints"""
        extracted_data = []
        
        for url in self.potential_data_urls:
            try:
                logger.info(f"Trying JSON endpoint: {url}")
                response = requests.get(url, headers=self.headers, timeout=30)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        logger.info(f"Found JSON data at {url}")
                        
                        # Process different JSON structures
                        if isinstance(data, dict):
                            # Handle nested structures
                            for key, value in data.items():
                                if isinstance(value, list):
                                    for item in value:
                                        if isinstance(item, dict) and 'model' in item:
                                            extracted_data.extend(self._process_json_item(item, url))
                                elif isinstance(value, dict) and 'model' in value:
                                    extracted_data.extend(self._process_json_item(value, url))
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and 'model' in item:
                                    extracted_data.extend(self._process_json_item(item, url))
                        
                        if extracted_data:
                            return self._deduplicate_models(extracted_data)
                            
                    except json.JSONDecodeError:
                        logger.info(f"Response from {url} is not valid JSON")
                        continue
                        
            except Exception as e:
                logger.info(f"Failed to fetch {url}: {e}")
                continue
        
        return []
    
    def _process_json_item(self, item: Dict, source_url: str) -> List[Dict]:
        """Process a single JSON item and extract model data"""
        results = []
        
        model_name = item.get('model', item.get('name', ''))
        if not model_name:
            return results
        
        # Look for score fields
        score_fields = ['correctness', 'efficiency', 'understanding', 'instruction_following', 'score', 'average']
        
        for field in score_fields:
            if field in item and isinstance(item[field], (int, float)):
                score = float(item[field])
                
                # Convert to percentage if needed
                if score <= 1:
                    score = score * 100
                
                normalized_name = self.normalize_model_name(model_name)
                
                results.append({
                    'model_name': normalized_name,
                    'raw_model_name': model_name,
                    'score': score,
                    'metric': field,
                    'benchmark': 'Convex Code LB',
                    'source_url': source_url
                })
                
                logger.info(f"Extracted: {normalized_name} = {score}% ({field})")
        
        return results
    
    def scrape_with_requests(self) -> List[Dict]:
        """Fallback to HTML scraping"""
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
                    elif any(keyword in header for keyword in ['correctness', 'efficiency', 'understanding', 'instruction', 'score', '%']):
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
                    if not model_name or model_name.lower() in ['model', 'name']:
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
                            'benchmark': 'Convex Code LB',
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
        """Scrape Convex leaderboard data"""
        
        # Try JSON endpoints first
        logger.info("Attempting to fetch JSON data from potential endpoints...")
        json_data = self.try_json_endpoints()
        if json_data:
            logger.info(f"✅ Successfully extracted {len(json_data)} models from JSON")
            return json_data
        
        # Fallback to HTML scraping
        logger.info("JSON endpoints failed, trying HTML scraping...")
        html_data = self.scrape_with_requests()
        if html_data:
            logger.info(f"✅ Successfully extracted {len(html_data)} models from HTML")
            return html_data
        
        logger.warning("No leaderboard data found. The Convex leaderboard might be under development or require authentication.")
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
            filename = f"convex_leaderboard_{timestamp}.json"
        
        output_data = {
            'source': 'convex.dev/llm-leaderboard',
            'scraped_at': datetime.now().isoformat(),
            'total_models': len(data),
            'benchmark_info': {
                'name': 'Convex Code LB',
                'description': 'Convex backend code writing evaluation',
                'metrics': ['correctness', 'efficiency', 'understanding', 'instruction_following']
            },
            'models': data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(data)} model scores to {filename}")
        return filename

def main():
    """Main function to run the scraper"""
    scraper = ConvexLeaderboardScraper()
    
    # Scrape the data
    data = scraper.scrape_leaderboard_data()
    
    if data:
        # Save to JSON file
        filename = scraper.save_to_json(data)
        
        # Print summary
        print(f"\\n✅ Successfully scraped Convex leaderboard!")
        print(f"📊 Found {len(data)} model scores")
        print(f"💾 Saved to: {filename}")
        print(f"\\nTop 5 models:")
        
        # Sort by score and show top 5
        sorted_data = sorted(data, key=lambda x: x['score'], reverse=True)
        for i, model in enumerate(sorted_data[:5], 1):
            print(f"  {i}. {model['model_name']}: {model['score']:.1f}% ({model['metric']})")
    else:
        print("❌ No leaderboard data found from Convex.dev")
        print("💡 The leaderboard might be under development or require authentication")

if __name__ == "__main__":
    main()