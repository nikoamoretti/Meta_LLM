"""
Scale AI SEAL Leaderboards Scraper
Scrapes expert-curated math and reasoning evaluation data from Scale AI SEAL
"""

import requests
import json
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from .base import BaseScraper

logger = logging.getLogger(__name__)

class ScaleSEALScraper(BaseScraper):
    """Scraper for Scale AI SEAL Leaderboards - Expert-Curated Math & Reasoning"""
    
    def __init__(self):
        super().__init__(
            name="Scale AI SEAL Leaderboards",
            url="https://scale.com/leaderboard"
        )
        
        # Alternative URLs to try
        self.alternative_urls = [
            "https://scale.com/seal",
            "https://scale.com/leaderboards",
            "https://leaderboard.scale.com",
            "https://api.scale.com/leaderboard"
        ]
        
        # GitHub and public data sources
        self.github_sources = [
            "https://github.com/ScaleAI/seal-leaderboard",
            "https://raw.githubusercontent.com/ScaleAI/seal-leaderboard/main/leaderboard.json"
        ]
        
        # Benchmark mapping for our system
        self.benchmark_mapping = {
            'seal_math': 'SEAL Math',
            'seal_reasoning': 'SEAL Reasoning',
            'seal_physics': 'SEAL Physics',
            'seal_chemistry': 'SEAL Chemistry',
            'seal_biology': 'SEAL Biology',
            'expert_math': 'Expert Math',
            'advanced_reasoning': 'Advanced Reasoning',
            'scientific_reasoning': 'Scientific Reasoning',
            'mathematical_proof': 'Mathematical Proof',
            'theorem_proving': 'Theorem Proving',
            'symbolic_reasoning': 'Symbolic Reasoning',
            'logical_reasoning': 'Logical Reasoning',
            'quantitative_reasoning': 'Quantitative Reasoning',
            'analytical_reasoning': 'Analytical Reasoning',
            'competition_math': 'Competition Math',
            'olympiad_problems': 'Olympiad Problems',
            'research_level_math': 'Research Level Math',
            'expert_verification': 'Expert Verification',
            'human_preference': 'Human Preference',
            'overall_score': 'Overall Score',
            'average_score': 'Average Score'
        }
    
    def scrape(self) -> List[Dict]:
        """Scrape the Scale AI SEAL leaderboards"""
        try:
            logger.info(f"Scraping {self.name}")
            
            # Try Scale AI API endpoints first
            api_data = self._try_scale_api()
            if api_data:
                return api_data
            
            # Try GitHub sources
            github_data = self._try_github_sources()
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
            
            logger.warning("All Scale AI SEAL sources failed, returning empty data")
            return []
            
        except Exception as e:
            logger.error(f"Error scraping Scale AI SEAL leaderboards: {e}")
            return []
    
    def _try_scale_api(self) -> Optional[List[Dict]]:
        """Try to get data from Scale AI API endpoints"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            # Try different API endpoints
            api_endpoints = [
                "https://api.scale.com/v1/leaderboard",
                "https://api.scale.com/leaderboard",
                "https://scale.com/api/leaderboard",
                "https://scale.com/api/seal/leaderboard",
                "https://leaderboard.scale.com/api/data",
                "https://scale.com/leaderboard/api/data"
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = self.session.get(endpoint, headers=headers, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        processed = self._process_seal_data(data)
                        if processed:
                            logger.info(f"Successfully got data from Scale API: {endpoint}")
                            return processed
                except Exception as e:
                    logger.debug(f"Scale API endpoint {endpoint} failed: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"Scale AI API approach failed: {e}")
        
        return None
    
    def _try_github_sources(self) -> Optional[List[Dict]]:
        """Try to get data from GitHub repositories"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            github_sources = [
                "https://raw.githubusercontent.com/ScaleAI/seal-leaderboard/main/leaderboard.json",
                "https://raw.githubusercontent.com/ScaleAI/seal-leaderboard/main/results.json",
                "https://raw.githubusercontent.com/ScaleAI/scale-leaderboard/main/data.json",
                "https://api.github.com/repos/ScaleAI/seal-leaderboard/contents/leaderboard.json"
            ]
            
            for source in github_sources:
                try:
                    response = self.session.get(source, headers=headers, timeout=15)
                    if response.status_code == 200:
                        if source.startswith('https://api.github.com'):
                            # GitHub API response
                            content = response.json()
                            if 'download_url' in content:
                                file_response = self.session.get(content['download_url'], headers=headers)
                                if file_response.status_code == 200:
                                    data = file_response.json()
                                else:
                                    continue
                            else:
                                continue
                        else:
                            # Direct file
                            data = response.json()
                        
                        processed = self._process_seal_data(data)
                        if processed:
                            logger.info(f"Successfully got data from GitHub: {source}")
                            return processed
                            
                except Exception as e:
                    logger.debug(f"GitHub source {source} failed: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"GitHub sources failed: {e}")
        
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
            return self._process_seal_data(json_data)
        
        # Try to find API endpoints
        api_data = self._try_find_api_endpoints(content, url)
        if api_data:
            return api_data
        
        # Fallback to HTML extraction
        return self._extract_from_html(content)
    
    def _extract_json_from_page(self, content: str) -> Optional[Dict]:
        """Extract JSON data from script tags"""
        patterns = [
            r'window\.__SEAL_DATA__\s*=\s*({.*?});',
            r'window\.__LEADERBOARD__\s*=\s*({.*?});',
            r'const\s+leaderboard\s*=\s*({.*?});',
            r'var\s+sealData\s*=\s*({.*?});',
            r'"leaderboard":\s*(\[.*?\])',
            r'"seal_results":\s*(\[.*?\])',
            r'"data":\s*(\[.*?\])',
            r'"models":\s*(\[.*?\])'
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
                f"{base_domain}/api/seal",
                f"{base_domain}/api/data",
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
                        return self._process_seal_data(data)
                except Exception:
                    continue
        except Exception:
            pass
        
        return None
    
    def _process_seal_data(self, data: Dict) -> List[Dict]:
        """Process the extracted Scale AI SEAL data"""
        models = []
        
        try:
            # Handle different data structures
            if isinstance(data, list):
                leaderboard_data = data
            elif isinstance(data, dict):
                leaderboard_data = data
                for key in ['leaderboard', 'models', 'results', 'data', 'seal_results', 'rankings']:
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
                            'domain': 'expert_reasoning',
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
                    scores['SEAL Rank'] = i + 1
                    
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
                            'domain': 'expert_reasoning',
                            'scraped_at': datetime.now().isoformat()
                        })
            
            logger.info(f"Extracted {len(models)} models from Scale AI SEAL data")
            return models
            
        except Exception as e:
            logger.error(f"Error processing Scale AI SEAL data: {e}")
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
                scores = {'SEAL Rank': i}
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
                        'domain': 'expert_reasoning',
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
                        scores['SEAL Score'] = score_value
                        break
                    except ValueError:
                        continue
                
                if not scores:
                    scores['SEAL Rank'] = i
                
                if scores:
                    models.append({
                        'model': model_name,
                        'scores': scores,
                        'domain': 'expert_reasoning',
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
            "scale_seal": models
        }

if __name__ == "__main__":
    scraper = ScaleSEALScraper()
    data = scraper.scrape_all()
    print(f"Scraped {len(data.get('scale_seal', []))} models from Scale AI SEAL")
    
    if data.get('scale_seal'):
        print("Sample model:")
        print(json.dumps(data['scale_seal'][0], indent=2))