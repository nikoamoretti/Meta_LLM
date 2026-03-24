"""
OpenRouter LLM Rankings Scraper
Scrapes real-world usage data and popularity rankings from OpenRouter
"""

import requests
import json
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from .base import BaseScraper

logger = logging.getLogger(__name__)

class OpenRouterRankingsScraper(BaseScraper):
    """Scraper for OpenRouter LLM Usage Rankings"""
    
    def __init__(self):
        super().__init__(
            name="OpenRouter LLM Rankings",
            url="https://openrouter.ai/rankings"
        )
        
        # Try to find API endpoints
        self.api_base = "https://openrouter.ai/api"
        
    def scrape(self) -> List[Dict]:
        """Scrape OpenRouter rankings"""
        try:
            logger.info(f"Scraping {self.name}")
            
            # First try to find an API endpoint
            api_data = self._try_api_endpoints()
            if api_data:
                return api_data
            
            # Fallback to web scraping
            return self._scrape_web_page()
            
        except Exception as e:
            logger.error(f"Error scraping OpenRouter rankings: {e}")
            return []
    
    def _try_api_endpoints(self) -> Optional[List[Dict]]:
        """Try to find and use API endpoints"""
        potential_endpoints = [
            "https://openrouter.ai/api/v1/rankings",
            "https://openrouter.ai/api/rankings",
            "https://openrouter.ai/api/stats",
            "https://openrouter.ai/api/models/rankings"
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        for endpoint in potential_endpoints:
            try:
                response = self.session.get(endpoint, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, (list, dict)) and data:
                        logger.info(f"Found API endpoint: {endpoint}")
                        return self._process_api_data(data)
            except Exception:
                continue
        
        return None
    
    def _process_api_data(self, data: Dict) -> List[Dict]:
        """Process data from API endpoint"""
        models = []
        
        try:
            # Handle different API response structures
            rankings_data = data
            if isinstance(data, dict):
                # Look for rankings in various keys
                for key in ['rankings', 'models', 'data', 'results']:
                    if key in data and isinstance(data[key], list):
                        rankings_data = data[key]
                        break
            
            if not isinstance(rankings_data, list):
                return []
            
            for item in rankings_data:
                if not isinstance(item, dict):
                    continue
                
                model_name = item.get('id') or item.get('name') or item.get('model')
                if not model_name:
                    continue
                
                # Clean up model name (remove provider prefix if present)
                if '/' in model_name:
                    clean_name = model_name.split('/')[-1]
                else:
                    clean_name = model_name
                
                # Extract usage metrics
                scores = {}
                
                # Token usage
                if 'tokens' in item:
                    scores['Total Tokens'] = item['tokens']
                if 'prompt_tokens' in item:
                    scores['Prompt Tokens'] = item['prompt_tokens']
                if 'completion_tokens' in item:
                    scores['Completion Tokens'] = item['completion_tokens']
                
                # Usage counts
                if 'usage_count' in item:
                    scores['Usage Count'] = item['usage_count']
                if 'requests' in item:
                    scores['Requests'] = item['requests']
                
                # Popularity metrics
                if 'rank' in item:
                    scores['Popularity Rank'] = item['rank']
                if 'percentage' in item:
                    scores['Usage Percentage'] = item['percentage']
                
                # Weekly/monthly data
                if 'weekly_tokens' in item:
                    scores['Weekly Tokens'] = item['weekly_tokens']
                if 'monthly_tokens' in item:
                    scores['Monthly Tokens'] = item['monthly_tokens']
                
                if scores:
                    models.append({
                        'model': clean_name,
                        'original_name': model_name,
                        'scores': scores,
                        'provider': item.get('provider', ''),
                        'scraped_at': datetime.now().isoformat()
                    })
            
            return models
            
        except Exception as e:
            logger.error(f"Error processing API data: {e}")
            return []
    
    def _scrape_web_page(self) -> List[Dict]:
        """Scrape the web page directly"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = self.session.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            
            content = response.text
            
            # Look for JSON data in script tags
            json_data = self._extract_json_from_page(content)
            if json_data:
                return self._process_page_data(json_data)
            
            # Fallback to HTML table extraction
            return self._extract_from_html(content)
            
        except Exception as e:
            logger.error(f"Error scraping web page: {e}")
            return []
    
    def _extract_json_from_page(self, content: str) -> Optional[Dict]:
        """Extract JSON data from script tags"""
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.__RANKINGS__\s*=\s*({.*?});',
            r'const\s+rankings\s*=\s*({.*?});',
            r'var\s+rankings\s*=\s*({.*?});',
            r'"rankings":\s*(\[.*?\])',
            r'"models":\s*(\[.*?\])'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group(1)
                    # Clean up JavaScript
                    json_str = re.sub(r'//.*?\n', '\n', json_str)
                    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    
                    data = json.loads(json_str)
                    if data:
                        return data
                except Exception:
                    continue
        
        return None
    
    def _process_page_data(self, data: Dict) -> List[Dict]:
        """Process extracted page data"""
        models = []
        
        try:
            # Navigate through different data structures
            rankings_list = data
            if isinstance(data, dict):
                for key in ['rankings', 'models', 'data', 'leaderboard']:
                    if key in data:
                        rankings_list = data[key]
                        break
            
            if not isinstance(rankings_list, list):
                return []
            
            for i, item in enumerate(rankings_list):
                if not isinstance(item, dict):
                    continue
                
                # Extract model name
                model_name = None
                for key in ['name', 'model', 'id', 'model_name']:
                    if key in item and item[key]:
                        model_name = str(item[key])
                        break
                
                if not model_name:
                    continue
                
                # Clean model name
                if '/' in model_name:
                    clean_name = model_name.split('/')[-1]
                else:
                    clean_name = model_name
                
                # Extract metrics
                scores = {}
                scores['Popularity Rank'] = i + 1  # Position in list
                
                # Look for various metrics
                metric_keys = [
                    'tokens', 'total_tokens', 'usage', 'requests', 'count',
                    'weekly_tokens', 'monthly_tokens', 'percentage', 'share'
                ]
                
                for key in metric_keys:
                    if key in item and isinstance(item[key], (int, float)):
                        metric_name = key.replace('_', ' ').title()
                        scores[metric_name] = item[key]
                
                if scores:
                    models.append({
                        'model': clean_name,
                        'original_name': model_name,
                        'scores': scores,
                        'scraped_at': datetime.now().isoformat()
                    })
            
            return models
            
        except Exception as e:
            logger.error(f"Error processing page data: {e}")
            return []
    
    def _extract_from_html(self, content: str) -> List[Dict]:
        """Extract data from HTML tables"""
        models = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for tables or list items with ranking data
            tables = soup.find_all('table')
            for table in tables:
                models.extend(self._process_table(table))
            
            # Also look for div-based rankings
            ranking_divs = soup.find_all('div', class_=re.compile(r'rank|model|leaderboard'))
            for div in ranking_divs:
                models.extend(self._process_ranking_div(div))
            
            return models
            
        except Exception as e:
            logger.error(f"Error extracting from HTML: {e}")
            return []
    
    def _process_table(self, table) -> List[Dict]:
        """Process HTML table data"""
        models = []
        
        try:
            rows = table.find_all('tr')
            if len(rows) < 2:
                return []
            
            # Get headers
            headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
            
            for i, row in enumerate(rows[1:], 1):
                cells = row.find_all(['td', 'th'])
                if len(cells) != len(headers):
                    continue
                
                row_data = {}
                for j, cell in enumerate(cells):
                    if j < len(headers):
                        row_data[headers[j]] = cell.get_text(strip=True)
                
                # Find model name
                model_name = None
                for header in ['Model', 'Name', 'ID']:
                    if header in row_data and row_data[header]:
                        model_name = row_data[header]
                        break
                
                if not model_name:
                    continue
                
                # Extract numeric scores
                scores = {'Popularity Rank': i}
                for header, value in row_data.items():
                    if header == 'Model' or not value:
                        continue
                    
                    try:
                        if '%' in value:
                            scores[header] = float(value.replace('%', ''))
                        elif 'M' in value:  # Millions
                            scores[header] = float(value.replace('M', '')) * 1000000
                        elif 'K' in value:  # Thousands
                            scores[header] = float(value.replace('K', '')) * 1000
                        else:
                            scores[header] = float(value)
                    except ValueError:
                        continue
                
                if scores:
                    models.append({
                        'model': model_name,
                        'scores': scores,
                        'scraped_at': datetime.now().isoformat()
                    })
            
            return models
            
        except Exception as e:
            logger.error(f"Error processing table: {e}")
            return []
    
    def _process_ranking_div(self, div) -> List[Dict]:
        """Process ranking div elements"""
        # Implementation for div-based rankings
        # This would be specific to OpenRouter's HTML structure
        return []
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Scrape all data and return in expected format"""
        models = self.scrape()
        return {
            "openrouter_rankings": models
        }

if __name__ == "__main__":
    scraper = OpenRouterRankingsScraper()
    data = scraper.scrape_all()
    print(f"Scraped {len(data.get('openrouter_rankings', []))} models from OpenRouter")
    
    if data.get('openrouter_rankings'):
        print("Sample model:")
        print(json.dumps(data['openrouter_rankings'][0], indent=2))