"""
C-Eval Chinese Evaluation Scraper
Scrapes Chinese academic knowledge evaluation data from C-Eval leaderboard
"""

import requests
import json
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from .base import BaseScraper

logger = logging.getLogger(__name__)

class CEvalScraper(BaseScraper):
    """Scraper for C-Eval - Chinese Academic Knowledge Evaluation"""
    
    def __init__(self):
        super().__init__(
            name="C-Eval",
            url="https://ceval.ai"
        )
        
        # Alternative URLs to try
        self.alternative_urls = [
            "https://www.ceval.ai",
            "https://ceval.ai/leaderboard",
            "https://www.ceval.ai/leaderboard",
            "https://ceval.ai/static/leaderboard.html"
        ]
        
        # GitHub repository for C-Eval data
        self.github_api = "https://api.github.com/repos/SJTU-LIT/ceval"
        self.github_raw = "https://raw.githubusercontent.com/SJTU-LIT/ceval/main"
        
        # Benchmark mapping for our system
        self.benchmark_mapping = {
            'c_eval': 'C-Eval Score',
            'average': 'C-Eval Average',
            'hard': 'C-Eval Hard',
            'stem': 'STEM',
            'social_science': 'Social Science',
            'humanities': 'Humanities',
            'other': 'Other Subjects',
            'math': 'Mathematics',
            'physics': 'Physics',
            'chemistry': 'Chemistry',
            'biology': 'Biology',
            'history': 'History',
            'geography': 'Geography',
            'politics': 'Politics',
            'chinese': 'Chinese Language',
            'english': 'English',
            'overall': 'Overall Score'
        }
    
    def scrape(self) -> List[Dict]:
        """Scrape the C-Eval leaderboard"""
        try:
            logger.info(f"Scraping {self.name}")
            
            # First try GitHub data source
            github_data = self._try_github_source()
            if github_data:
                return github_data
            
            # Try different URLs
            for url in [self.url] + self.alternative_urls:
                try:
                    data = self._scrape_url(url)
                    if data:
                        return data
                except Exception as e:
                    logger.warning(f"Failed to scrape {url}: {e}")
                    continue
            
            logger.warning("All C-Eval sources failed, returning empty data")
            return []
            
        except Exception as e:
            logger.error(f"Error scraping C-Eval: {e}")
            return []
    
    def _try_github_source(self) -> Optional[List[Dict]]:
        """Try to get data from GitHub repository"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Try to find data files
            potential_files = [
                f"{self.github_raw}/leaderboard.json",
                f"{self.github_raw}/results.json",
                f"{self.github_raw}/data/leaderboard.json",
                f"{self.github_raw}/data/results.json"
            ]
            
            for file_url in potential_files:
                try:
                    response = self.session.get(file_url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        return self._process_ceval_data(data)
                except Exception:
                    continue
            
            # Try repository contents API
            contents_response = self.session.get(f"{self.github_api}/contents", headers=headers, timeout=10)
            if contents_response.status_code == 200:
                contents = contents_response.json()
                for item in contents:
                    if item['name'].endswith('.json') and any(keyword in item['name'].lower() for keyword in ['leaderboard', 'results', 'scores']):
                        try:
                            file_response = self.session.get(item['download_url'], headers=headers)
                            if file_response.status_code == 200:
                                data = file_response.json()
                                processed = self._process_ceval_data(data)
                                if processed:
                                    return processed
                        except Exception:
                            continue
        
        except Exception as e:
            logger.warning(f"GitHub source failed: {e}")
        
        return None
    
    def _scrape_url(self, url: str) -> Optional[List[Dict]]:
        """Scrape a specific URL"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = self.session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        content = response.text
        
        # Look for JSON data in script tags
        json_data = self._extract_json_from_page(content)
        if json_data:
            return self._process_ceval_data(json_data)
        
        # Try to find API endpoints
        api_data = self._try_find_api_endpoints(content, url)
        if api_data:
            return api_data
        
        # Fallback to HTML extraction
        return self._extract_from_html(content)
    
    def _extract_json_from_page(self, content: str) -> Optional[Dict]:
        """Extract JSON data from script tags"""
        patterns = [
            r'window\.__LEADERBOARD__\s*=\s*({.*?});',
            r'window\.__CEVAL_DATA__\s*=\s*({.*?});',
            r'const\s+leaderboard\s*=\s*({.*?});',
            r'var\s+cevalData\s*=\s*({.*?});',
            r'"leaderboard":\s*(\[.*?\])',
            r'"models":\s*(\[.*?\])',
            r'"results":\s*(\[.*?\])'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.DOTALL)
            for match in matches:
                try:
                    json_str = match.group(1)
                    # Clean up JavaScript
                    json_str = re.sub(r'//.*?\\n', '\\n', json_str)
                    json_str = re.sub(r'/\\*.*?\\*/', '', json_str, flags=re.DOTALL)
                    json_str = re.sub(r',\\s*}', '}', json_str)
                    json_str = re.sub(r',\\s*]', ']', json_str)
                    
                    data = json.loads(json_str)
                    if data:
                        return data
                except Exception:
                    continue
        
        return None
    
    def _try_find_api_endpoints(self, content: str, base_url: str) -> Optional[List[Dict]]:
        """Try to find and use API endpoints"""
        try:
            base_domain = '/'.join(base_url.split('/')[:3])
            
            api_endpoints = [
                f"{base_domain}/api/leaderboard",
                f"{base_domain}/api/results",
                f"{base_domain}/api/scores",
                f"{base_domain}/data/leaderboard.json",
                f"{base_domain}/leaderboard.json",
                f"{base_domain}/static/leaderboard.json"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            for endpoint in api_endpoints:
                try:
                    response = self.session.get(endpoint, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        return self._process_ceval_data(data)
                except Exception:
                    continue
        except Exception:
            pass
        
        return None
    
    def _process_ceval_data(self, data: Dict) -> List[Dict]:
        """Process the extracted C-Eval data"""
        models = []
        
        try:
            # Handle different data structures
            if isinstance(data, list):
                leaderboard_data = data
            elif isinstance(data, dict):
                leaderboard_data = data
                for key in ['leaderboard', 'models', 'results', 'data']:
                    if key in data and isinstance(data[key], list):
                        leaderboard_data = data[key]
                        break
            else:
                return []
            
            if isinstance(leaderboard_data, dict):
                # Handle object with model keys
                for model_key, model_data in leaderboard_data.items():
                    if not isinstance(model_data, dict):
                        continue
                    
                    model_name = model_data.get('name', model_key)
                    if not model_name:
                        continue
                    
                    # Clean model name
                    if '/' in model_name:
                        clean_name = model_name.split('/')[-1]
                    else:
                        clean_name = model_name
                    
                    scores = {}
                    for key, value in model_data.items():
                        if key.lower() in ['name', 'model'] or not isinstance(value, (int, float)):
                            continue
                        
                        benchmark_name = self.benchmark_mapping.get(key.lower(), key.replace('_', ' ').title())
                        scores[benchmark_name] = value
                    
                    if scores:
                        models.append({
                            'model': clean_name,
                            'original_name': model_name,
                            'scores': scores,
                            'scraped_at': datetime.now().isoformat()
                        })
            
            elif isinstance(leaderboard_data, list):
                # Handle array of models
                for i, item in enumerate(leaderboard_data):
                    if not isinstance(item, dict):
                        continue
                    
                    model_name = item.get('model') or item.get('name') or item.get('model_name')
                    if not model_name:
                        continue
                    
                    # Clean model name
                    if '/' in model_name:
                        clean_name = model_name.split('/')[-1]
                    else:
                        clean_name = model_name
                    
                    scores = {}
                    scores['C-Eval Rank'] = i + 1
                    
                    for key, value in item.items():
                        if key.lower() in ['model', 'name'] or not isinstance(value, (int, float)):
                            continue
                        
                        benchmark_name = self.benchmark_mapping.get(key.lower(), key.replace('_', ' ').title())
                        scores[benchmark_name] = value
                    
                    if scores:
                        models.append({
                            'model': clean_name,
                            'original_name': model_name,
                            'scores': scores,
                            'scraped_at': datetime.now().isoformat()
                        })
            
            logger.info(f"Extracted {len(models)} models from C-Eval data")
            return models
            
        except Exception as e:
            logger.error(f"Error processing C-Eval data: {e}")
            return []
    
    def _extract_from_html(self, content: str) -> List[Dict]:
        """Extract data from HTML tables"""
        models = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for tables with leaderboard data
            tables = soup.find_all('table')
            for table in tables:
                models.extend(self._process_table(table))
            
            # Also look for div-based leaderboards
            leaderboard_divs = soup.find_all('div', class_=re.compile(r'leaderboard|ranking|score'))
            for div in leaderboard_divs:
                models.extend(self._process_leaderboard_div(div))
            
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
                for header in ['Model', 'Name', 'LLM', 'AI Model', '模型']:
                    if header in row_data and row_data[header]:
                        model_name = row_data[header]
                        break
                
                if not model_name:
                    continue
                
                # Extract numeric scores
                scores = {'C-Eval Rank': i}
                for header, value in row_data.items():
                    if header in ['Model', 'Name', 'LLM', '模型'] or not value:
                        continue
                    
                    try:
                        if '%' in value:
                            scores[header] = float(value.replace('%', ''))
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
    
    def _process_leaderboard_div(self, div) -> List[Dict]:
        """Process div-based leaderboard elements"""
        models = []
        
        try:
            # Look for structured data within the div
            items = div.find_all(['div', 'li'], class_=re.compile(r'item|entry|model'))
            
            for i, item in enumerate(items, 1):
                model_name = None
                scores = {}
                
                # Try to extract model name
                name_elem = item.find(['span', 'div', 'h3', 'h4'], class_=re.compile(r'name|model|title'))
                if name_elem:
                    model_name = name_elem.get_text(strip=True)
                
                if not model_name:
                    continue
                
                # Try to extract scores
                score_elems = item.find_all(['span', 'div'], class_=re.compile(r'score|value|rating'))
                for score_elem in score_elems:
                    score_text = score_elem.get_text(strip=True)
                    try:
                        score_value = float(score_text.replace('%', ''))
                        scores['C-Eval Score'] = score_value
                        break
                    except ValueError:
                        continue
                
                if not scores:
                    scores['C-Eval Rank'] = i
                
                if scores:
                    models.append({
                        'model': model_name,
                        'scores': scores,
                        'scraped_at': datetime.now().isoformat()
                    })
            
            return models
            
        except Exception as e:
            logger.error(f"Error processing leaderboard div: {e}")
            return []
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Scrape all data and return in expected format"""
        models = self.scrape()
        return {
            "ceval": models
        }

if __name__ == "__main__":
    scraper = CEvalScraper()
    data = scraper.scrape_all()
    print(f"Scraped {len(data.get('ceval', []))} models from C-Eval")
    
    if data.get('ceval'):
        print("Sample model:")
        print(json.dumps(data['ceval'][0], indent=2))