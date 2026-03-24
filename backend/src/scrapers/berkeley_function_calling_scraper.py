"""
Berkeley Function-Calling Leaderboard Scraper  
Scrapes tool use and API integration evaluation data from Gorilla/Berkeley
"""

import requests
import json
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from .base import BaseScraper

logger = logging.getLogger(__name__)

class BerkeleyFunctionCallingScraper(BaseScraper):
    """Scraper for Berkeley Function-Calling Leaderboard - Tool Use & API Integration"""
    
    def __init__(self):
        super().__init__(
            name="Berkeley Function-Calling Leaderboard",
            url="https://gorilla.cs.berkeley.edu"
        )
        
        # Alternative URLs to try
        self.alternative_urls = [
            "https://gorilla.cs.berkeley.edu/leaderboard.html",
            "https://gorilla.cs.berkeley.edu/blogs/4_open_functions.html",
            "https://huggingface.co/spaces/gorilla-llm/berkeley-function-calling-leaderboard"
        ]
        
        # GitHub repository for BFCL data
        self.github_api = "https://api.github.com/repos/ShishirPatil/gorilla"
        self.github_raw = "https://raw.githubusercontent.com/ShishirPatil/gorilla/main"
        
        # Benchmark mapping for our system
        self.benchmark_mapping = {
            'overall': 'Overall Accuracy',
            'simple': 'Simple Function Calling',
            'multiple': 'Multiple Function Calling',
            'parallel': 'Parallel Function Calling',
            'parallel_multiple': 'Parallel Multiple Function Calling',
            'executable': 'Executable Accuracy',
            'ast_summary': 'AST Summary',
            'exec_summary': 'Execution Summary',
            'relevance_detection': 'Relevance Detection',
            'irrelevance_detection': 'Irrelevance Detection',
            'bfcl_score': 'BFCL Score',
            'function_calling_accuracy': 'Function Calling Accuracy',
            'tool_use_accuracy': 'Tool Use Accuracy',
            'api_integration_score': 'API Integration Score'
        }
    
    def scrape(self) -> List[Dict]:
        """Scrape the Berkeley Function-Calling leaderboard"""
        try:
            logger.info(f"Scraping {self.name}")
            
            # Try HuggingFace Space first (most likely to have fresh data)
            hf_data = self._try_huggingface_space()
            if hf_data:
                return hf_data
            
            # Try GitHub data source
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
            
            logger.warning("All Berkeley Function-Calling sources failed, returning empty data")
            return []
            
        except Exception as e:
            logger.error(f"Error scraping Berkeley Function-Calling leaderboard: {e}")
            return []
    
    def _try_huggingface_space(self) -> Optional[List[Dict]]:
        """Try to get data from HuggingFace Space"""
        try:
            hf_url = "https://huggingface.co/spaces/gorilla-llm/berkeley-function-calling-leaderboard"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            # Try HF Spaces API endpoints
            api_endpoints = [
                "https://huggingface.co/api/spaces/gorilla-llm/berkeley-function-calling-leaderboard/runtime",
                "https://huggingface.co/spaces/gorilla-llm/berkeley-function-calling-leaderboard/api/leaderboard",
                "https://gorilla-llm-berkeley-function-calling-leaderboard.hf.space/api/leaderboard"
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = self.session.get(endpoint, headers=headers, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        processed = self._process_bfcl_data(data)
                        if processed:
                            logger.info(f"Successfully got data from HF Space: {endpoint}")
                            return processed
                except Exception as e:
                    logger.debug(f"HF Space endpoint {endpoint} failed: {e}")
                    continue
            
            # Try scraping the HF Space page directly
            response = self.session.get(hf_url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}, timeout=30)
            if response.status_code == 200:
                json_data = self._extract_json_from_page(response.text)
                if json_data:
                    return self._process_bfcl_data(json_data)
        
        except Exception as e:
            logger.warning(f"HuggingFace Space failed: {e}")
        
        return None
    
    def _try_github_source(self) -> Optional[List[Dict]]:
        """Try to get data from GitHub repository"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            # Try to find data files
            potential_files = [
                f"{self.github_raw}/berkeley-function-call-leaderboard/leaderboard.json",
                f"{self.github_raw}/leaderboard.json",
                f"{self.github_raw}/results.json",
                f"{self.github_raw}/function_calling_results.json",
                f"{self.github_raw}/bfcl/leaderboard.json"
            ]
            
            for file_url in potential_files:
                try:
                    response = self.session.get(file_url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        processed = self._process_bfcl_data(data)
                        if processed:
                            logger.info(f"Successfully got data from GitHub: {file_url}")
                            return processed
                except Exception:
                    continue
            
            # Try repository contents API
            contents_response = self.session.get(f"{self.github_api}/contents", headers=headers, timeout=10)
            if contents_response.status_code == 200:
                contents = contents_response.json()
                for item in contents:
                    if 'function' in item['name'].lower() or 'leaderboard' in item['name'].lower():
                        if item['type'] == 'dir':
                            # Explore subdirectory
                            subdir_response = self.session.get(item['url'], headers=headers)
                            if subdir_response.status_code == 200:
                                subdir_contents = subdir_response.json()
                                for subitem in subdir_contents:
                                    if subitem['name'].endswith('.json'):
                                        try:
                                            file_response = self.session.get(subitem['download_url'], headers=headers)
                                            if file_response.status_code == 200:
                                                data = file_response.json()
                                                processed = self._process_bfcl_data(data)
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
            return self._process_bfcl_data(json_data)
        
        # Try to find API endpoints
        api_data = self._try_find_api_endpoints(content, url)
        if api_data:
            return api_data
        
        # Fallback to HTML extraction
        return self._extract_from_html(content)
    
    def _extract_json_from_page(self, content: str) -> Optional[Dict]:
        """Extract JSON data from script tags"""
        patterns = [
            r'window\.__gradio_config__\s*=\s*({.*?});',
            r'window\.__LEADERBOARD__\s*=\s*({.*?});',
            r'const\s+leaderboard\s*=\s*({.*?});',
            r'var\s+bfclData\s*=\s*({.*?});',
            r'"leaderboard":\s*(\[.*?\])',
            r'"results":\s*(\[.*?\])',
            r'"data":\s*(\[.*?\])'
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
                f"{base_domain}/api/function-calling",
                f"{base_domain}/leaderboard.json",
                f"{base_domain}/data/leaderboard.json"
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
                        return self._process_bfcl_data(data)
                except Exception:
                    continue
        except Exception:
            pass
        
        return None
    
    def _process_bfcl_data(self, data: Dict) -> List[Dict]:
        """Process the extracted Berkeley Function-Calling data"""
        models = []
        
        try:
            # Handle different data structures
            if isinstance(data, list):
                leaderboard_data = data
            elif isinstance(data, dict):
                leaderboard_data = data
                for key in ['leaderboard', 'models', 'results', 'data', 'function_calling_results']:
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
                    if '/' in model_name and model_name.count('/') == 1:
                        clean_name = model_name
                    else:
                        clean_name = model_name.split('/')[-1] if '/' in model_name else model_name
                    
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
                    if '/' in model_name and model_name.count('/') == 1:
                        clean_name = model_name
                    else:
                        clean_name = model_name.split('/')[-1] if '/' in model_name else model_name
                    
                    scores = {}
                    scores['BFCL Rank'] = i + 1
                    
                    for key, value in item.items():
                        if key.lower() in ['model', 'name', 'model_name'] or not isinstance(value, (int, float)):
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
            
            logger.info(f"Extracted {len(models)} models from Berkeley Function-Calling data")
            return models
            
        except Exception as e:
            logger.error(f"Error processing Berkeley Function-Calling data: {e}")
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
                for header in ['Model', 'Name', 'model']:
                    if header in row_data and row_data[header]:
                        model_name = row_data[header]
                        break
                
                if not model_name:
                    continue
                
                # Extract numeric scores
                scores = {'BFCL Rank': i}
                for header, value in row_data.items():
                    if header in ['Model', 'Name'] or not value:
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
                        scores['BFCL Score'] = score_value
                        break
                    except ValueError:
                        continue
                
                if not scores:
                    scores['BFCL Rank'] = i
                
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
            "berkeley_function_calling": models
        }

if __name__ == "__main__":
    scraper = BerkeleyFunctionCallingScraper()
    data = scraper.scrape_all()
    print(f"Scraped {len(data.get('berkeley_function_calling', []))} models from Berkeley Function-Calling")
    
    if data.get('berkeley_function_calling'):
        print("Sample model:")
        print(json.dumps(data['berkeley_function_calling'][0], indent=2))