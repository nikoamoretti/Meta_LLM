"""
Aider.chat Leaderboard Scraper
Scrapes real coding performance data from aider.chat/docs/leaderboards/

This scraper extracts the "Percent correct" scores from Aider's polyglot benchmark
which tests LLM performance on code editing across 6 programming languages.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.model_name_resolver import ModelNameResolver

logger = logging.getLogger(__name__)

class AiderChatScraper:
    def __init__(self):
        self.base_url = "https://aider.chat/docs/leaderboards/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.resolver = ModelNameResolver()
        
    def normalize_model_name(self, raw_name: str) -> str:
        """
        Normalize model names using the centralized resolver
        """
        return self.resolver.resolve(raw_name)
    
    def scrape_leaderboard_data(self) -> List[Dict]:
        """
        Scrape the main leaderboard data from Aider.chat
        """
        try:
            logger.info(f"Fetching Aider.chat leaderboard from {self.base_url}")
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for the leaderboard table
            # The table should contain model names and percent correct scores
            tables = soup.find_all('table')
            
            extracted_data = []
            
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) < 2:  # Skip tables without data rows
                    continue
                    
                # Find header row to identify columns
                header_row = rows[0]
                headers = [th.get_text().strip().lower() for th in header_row.find_all(['th', 'td'])]
                
                # Look for specific Aider.chat columns based on known structure
                model_col = None
                score_col = None
                
                # Based on the known table structure:
                # Column 2: Model, Column 3: Percent correct, Column 6: Correct edit format
                for i, header in enumerate(headers):
                    if 'model' in header:
                        model_col = i
                    elif header == 'percent correct':  # Exact match for the right column
                        score_col = i
                        break
                
                # If exact match failed, try position-based (more reliable for Aider.chat)
                if model_col is None or score_col is None:
                    if len(headers) >= 4:  # Ensure we have enough columns
                        model_col = 1   # Model is typically column 2 (index 1)  
                        score_col = 2   # Percent correct is column 3 (index 2)
                        logger.info(f"Using position-based column detection: model_col={model_col}, score_col={score_col}")
                        logger.info(f"Headers: {headers}")
                
                if model_col is None or score_col is None:
                    continue  # Skip this table if we can't find the right columns
                
                logger.info(f"Found leaderboard table with {len(rows)-1} data rows")
                
                # Extract data rows
                for row in rows[1:]:  # Skip header row
                    cells = row.find_all(['td', 'th'])
                    if len(cells) <= max(model_col, score_col):
                        continue
                        
                    model_name = cells[model_col].get_text().strip()
                    score_text = cells[score_col].get_text().strip()
                    
                    if not model_name or not score_text:
                        continue
                    
                    # Extract numeric score
                    score_match = re.search(r'(\d+\.?\d*)', score_text)
                    if not score_match:
                        continue
                        
                    score = float(score_match.group(1))
                    
                    # Normalize model name
                    normalized_name = self.normalize_model_name(model_name)
                    
                    extracted_data.append({
                        'model_name': normalized_name,
                        'raw_model_name': model_name,
                        'score': score,
                        'metric': 'percent_correct',
                        'benchmark': 'Aider Polyglot Benchmark',
                        'total_exercises': 225,
                        'languages': ['C++', 'Go', 'Java', 'JavaScript', 'Python', 'Rust']
                    })
                
                if extracted_data:
                    break  # Found valid data, stop looking at other tables
            
            if not extracted_data:
                # If no table data found, try to parse from script tags or other elements
                logger.warning("No table data found, attempting alternative extraction methods")
                extracted_data = self._extract_from_page_content(soup)
            
            # Deduplicate models - keep the best score for each normalized model name
            deduplicated_data = self._deduplicate_models(extracted_data)
            
            logger.info(f"Successfully extracted {len(extracted_data)} model scores from Aider.chat")
            logger.info(f"After deduplication: {len(deduplicated_data)} unique models")
            return deduplicated_data
            
        except Exception as e:
            logger.error(f"Failed to scrape Aider.chat leaderboard: {e}")
            return []
    
    def _extract_from_page_content(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Alternative extraction method for pages without clear table structure
        """
        extracted_data = []
        
        # Look for JavaScript data or embedded JSON
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Look for data patterns in JavaScript
                model_score_pattern = r'[\'"]([\w\s\-\.]+)[\'"]:\s*(\d+\.?\d*)'
                matches = re.findall(model_score_pattern, script.string)
                
                for model_name, score in matches:
                    if any(keyword in model_name.lower() for keyword in ['gpt', 'claude', 'gemini', 'llama', 'o1', 'o3']):
                        normalized_name = self.normalize_model_name(model_name)
                        extracted_data.append({
                            'model_name': normalized_name,
                            'raw_model_name': model_name,
                            'score': float(score),
                            'metric': 'percent_correct',
                            'benchmark': 'Aider Polyglot Benchmark',
                            'total_exercises': 225,
                            'languages': ['C++', 'Go', 'Java', 'JavaScript', 'Python', 'Rust']
                        })
        
        return extracted_data
    
    def _deduplicate_models(self, data: List[Dict]) -> List[Dict]:
        """
        Deduplicate models by normalized name, keeping the highest scoring version
        For models with same scores, keeps the first one (assuming it's more recent)
        """
        model_groups = {}
        
        # Group models by normalized name
        for model_data in data:
            normalized_name = model_data['model_name']
            if normalized_name not in model_groups:
                model_groups[normalized_name] = []
            model_groups[normalized_name].append(model_data)
        
        # For each group, keep the highest scoring model
        deduplicated = []
        for normalized_name, models in model_groups.items():
            if len(models) == 1:
                deduplicated.append(models[0])
            else:
                # Sort by score (descending) and take the highest
                best_model = max(models, key=lambda x: x['score'])
                logger.info(f"Deduplicated {normalized_name}: kept score {best_model['score']} from {len(models)} variants")
                
                # Log what was deduplicated for transparency
                for model in models:
                    logger.debug(f"  - {model['raw_model_name']}: {model['score']}")
                
                deduplicated.append(best_model)
        
        return deduplicated
    
    def save_to_json(self, data: List[Dict], filename: str = None) -> str:
        """
        Save scraped data to JSON file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"aider_chat_leaderboard_{timestamp}.json"
        
        output_data = {
            'source': 'aider.chat/docs/leaderboards/',
            'scraped_at': datetime.now().isoformat(),
            'total_models': len(data),
            'benchmark_info': {
                'name': 'Aider Polyglot Benchmark',
                'description': 'Code editing performance across 6 programming languages',
                'total_exercises': 225,
                'languages': ['C++', 'Go', 'Java', 'JavaScript', 'Python', 'Rust'],
                'metric': 'Percent correct'
            },
            'models': data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(data)} model scores to {filename}")
        return filename

def main():
    """
    Main function to run the scraper
    """
    scraper = AiderChatScraper()
    
    # Scrape the data
    data = scraper.scrape_leaderboard_data()
    
    if data:
        # Save to JSON file
        filename = scraper.save_to_json(data)
        
        # Print summary
        print(f"\n✅ Successfully scraped Aider.chat leaderboard!")
        print(f"📊 Found {len(data)} models")
        print(f"💾 Saved to: {filename}")
        print(f"\nTop 5 models:")
        
        # Sort by score and show top 5
        sorted_data = sorted(data, key=lambda x: x['score'], reverse=True)
        for i, model in enumerate(sorted_data[:5], 1):
            print(f"  {i}. {model['model_name']}: {model['score']}%")
    else:
        print("❌ Failed to scrape any data from Aider.chat leaderboard")

if __name__ == "__main__":
    main()