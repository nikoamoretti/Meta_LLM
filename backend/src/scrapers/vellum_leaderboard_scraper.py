"""
Vellum AI LLM Leaderboard 2025 Scraper
Scrapes cutting-edge model performance on advanced benchmarks (GPQA, AIME, etc.)
"""

import requests
import json
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from .base import BaseScraper

logger = logging.getLogger(__name__)

class VellumLeaderboardScraper(BaseScraper):
    """Scraper for Vellum AI LLM Leaderboard 2025"""
    
    def __init__(self):
        super().__init__(
            name="Vellum AI LLM Leaderboard 2025",
            url="https://www.vellum.ai/llm-leaderboard"
        )
        
        # Benchmark mapping for our system
        self.benchmark_mapping = {
            'gpqa_diamond': 'GPQA Diamond',
            'aime_2024': 'AIME 2024',
            'swe_bench': 'SWE-Bench',
            'bfcl': 'Berkeley Function Calling',
            'math_500': 'MATH 500',
            'alder_polyglot': 'Alder Polyglot',
            'grind': 'GRIND',
            'humanity_last_exam': 'Humanity Last Exam'
        }
    
    def scrape(self) -> List[Dict]:
        """Scrape the Vellum leaderboard"""
        try:
            logger.info(f"Scraping {self.name}")
            
            # Get the page content
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = self.session.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Extract JavaScript data object
            content = response.text
            
            # Look for dataModels object in the JavaScript
            data_pattern = r'const\s+dataModels\s*=\s*({.*?});'
            match = re.search(data_pattern, content, re.DOTALL)
            
            if not match:
                # Try alternative pattern
                data_pattern = r'dataModels\s*=\s*({.*?});'
                match = re.search(data_pattern, content, re.DOTALL)
            
            if not match:
                logger.warning("Could not find dataModels object, attempting table extraction")
                return self._extract_from_tables(content)
            
            # Parse the JavaScript object
            data_str = match.group(1)
            
            # Clean up JavaScript object to make it JSON-parseable
            data_str = self._clean_js_object(data_str)
            
            try:
                data = json.loads(data_str)
                return self._process_vellum_data(data)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JavaScript data: {e}")
                return self._extract_from_tables(content)
            
        except Exception as e:
            logger.error(f"Error scraping Vellum leaderboard: {e}")
            return []
    
    def _clean_js_object(self, js_str: str) -> str:
        """Clean JavaScript object to make it JSON-parseable"""
        # Remove comments
        js_str = re.sub(r'//.*?\n', '\n', js_str)
        js_str = re.sub(r'/\*.*?\*/', '', js_str, flags=re.DOTALL)
        
        # Fix unquoted keys
        js_str = re.sub(r'(\w+):', r'"\1":', js_str)
        
        # Fix trailing commas
        js_str = re.sub(r',\s*}', '}', js_str)
        js_str = re.sub(r',\s*]', ']', js_str)
        
        # Fix undefined/null values
        js_str = re.sub(r'\bundefined\b', 'null', js_str)
        
        return js_str
    
    def _process_vellum_data(self, data: Dict) -> List[Dict]:
        """Process the extracted Vellum data"""
        models = []
        
        try:
            for model_key, model_data in data.items():
                if not isinstance(model_data, dict):
                    continue
                
                model_name = model_data.get('name', model_key)
                if not model_name:
                    continue
                
                # Extract scores for each benchmark
                scores = {}
                
                # Common benchmark fields to look for
                benchmark_fields = [
                    'gpqa_diamond', 'gpqa', 'aime_2024', 'aime', 'swe_bench', 'swe',
                    'bfcl', 'berkeley_function_calling', 'math_500', 'math',
                    'alder_polyglot', 'alder', 'grind', 'humanity_last_exam'
                ]
                
                for field in benchmark_fields:
                    if field in model_data:
                        score_value = model_data[field]
                        if isinstance(score_value, (int, float)) and score_value > 0:
                            benchmark_name = self.benchmark_mapping.get(field, field.replace('_', ' ').title())
                            scores[benchmark_name] = score_value
                
                # Also check for nested score objects
                if 'scores' in model_data and isinstance(model_data['scores'], dict):
                    for bench, score in model_data['scores'].items():
                        if isinstance(score, (int, float)) and score > 0:
                            benchmark_name = self.benchmark_mapping.get(bench, bench.replace('_', ' ').title())
                            scores[benchmark_name] = score
                
                if scores:
                    models.append({
                        'model': model_name,
                        'scores': scores,
                        'provider': model_data.get('provider', ''),
                        'context_window': model_data.get('context_window', model_data.get('context', '')),
                        'cost_input': model_data.get('cost_input', model_data.get('input_cost', '')),
                        'cost_output': model_data.get('cost_output', model_data.get('output_cost', '')),
                        'scraped_at': datetime.now().isoformat()
                    })
            
            logger.info(f"Extracted {len(models)} models from Vellum leaderboard")
            return models
            
        except Exception as e:
            logger.error(f"Error processing Vellum data: {e}")
            return []
    
    def _extract_from_tables(self, content: str) -> List[Dict]:
        """Fallback: extract data from HTML tables if JavaScript parsing fails"""
        models = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for tables with benchmark data
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) < 2:
                    continue
                
                # Get headers
                header_row = rows[0]
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                
                if not any('model' in h.lower() for h in headers):
                    continue
                
                # Process data rows
                for row in rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) != len(headers):
                        continue
                    
                    row_data = {}
                    for i, cell in enumerate(cells):
                        if i < len(headers):
                            row_data[headers[i]] = cell.get_text(strip=True)
                    
                    # Extract model name
                    model_name = None
                    for header in headers:
                        if 'model' in header.lower():
                            model_name = row_data.get(header)
                            break
                    
                    if not model_name:
                        continue
                    
                    # Extract scores
                    scores = {}
                    for header, value in row_data.items():
                        if header.lower() == 'model' or not value:
                            continue
                        
                        try:
                            # Try to parse as number (percentage or decimal)
                            if '%' in value:
                                score = float(value.replace('%', ''))
                            else:
                                score = float(value)
                            
                            if 0 <= score <= 100:
                                scores[header] = score
                        except ValueError:
                            continue
                    
                    if scores:
                        models.append({
                            'model': model_name,
                            'scores': scores,
                            'scraped_at': datetime.now().isoformat()
                        })
            
            logger.info(f"Extracted {len(models)} models from HTML tables")
            return models
            
        except Exception as e:
            logger.error(f"Error extracting from HTML tables: {e}")
            return []
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Scrape all data and return in expected format"""
        models = self.scrape()
        return {
            "vellum_leaderboard": models
        }

if __name__ == "__main__":
    scraper = VellumLeaderboardScraper()
    data = scraper.scrape_all()
    print(f"Scraped {len(data.get('vellum_leaderboard', []))} models from Vellum")
    
    # Print sample data
    if data.get('vellum_leaderboard'):
        print("Sample model:")
        print(json.dumps(data['vellum_leaderboard'][0], indent=2))