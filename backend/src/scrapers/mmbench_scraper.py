"""
MMBench Multimodal Scraper
Scrapes vision-language model evaluation data from MMBench leaderboard
"""

import requests
import json
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from .base import BaseScraper

logger = logging.getLogger(__name__)

class MMBenchScraper(BaseScraper):
    """Scraper for MMBench - Multimodal Vision-Language Models"""
    
    def __init__(self):
        super().__init__(
            name="MMBench",
            url="https://mmbench.opencompass.org.cn"
        )
        
        # Alternative URLs to try
        self.alternative_urls = [
            "https://opencompass.org.cn/mmbench",
            "https://mmbench.opencompass.org.cn/leaderboard",
            "https://opencompass.org.cn/leaderboard/multimodal"
        ]
        
        # GitHub and public data sources
        self.github_sources = [
            "https://github.com/open-compass/MMBench",
            "https://raw.githubusercontent.com/open-compass/MMBench/main/results.json",
            "https://api.github.com/repos/open-compass/MMBench"
        ]
        
        # Benchmark mapping for our system
        self.benchmark_mapping = {
            'mmbench': 'MMBench',
            'mmbench_en': 'MMBench English',
            'mmbench_cn': 'MMBench Chinese',
            'ccbench': 'CCBench',
            'mmmu': 'MMMU',
            'mathvista': 'MathVista',
            'scienceqa': 'ScienceQA',
            'ai2d': 'AI2D',
            'chartqa': 'ChartQA',
            'seed_bench': 'SEED-Bench',
            'pope': 'POPE',
            'mme': 'MME',
            'gqa': 'GQA',
            'okvqa': 'OK-VQA',
            'textvqa': 'TextVQA',
            'vqav2': 'VQAv2',
            'vizwiz': 'VizWiz',
            'visual_reasoning': 'Visual Reasoning',
            'visual_perception': 'Visual Perception',
            'logical_reasoning': 'Logical Reasoning',
            'text_recognition': 'Text Recognition',
            'fine_grained_perception': 'Fine-grained Perception',
            'coarse_grained_perception': 'Coarse-grained Perception',
            'multimodal_reasoning': 'Multimodal Reasoning',
            'vision_language_understanding': 'Vision-Language Understanding',
            'overall_score': 'Overall Score',
            'average_score': 'Average Score'
        }
    
    def scrape(self) -> List[Dict]:
        """Scrape the MMBench leaderboard"""
        try:
            logger.info(f"Scraping {self.name}")
            
            # Try OpenCompass API endpoints first
            api_data = self._try_opencompass_api()
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
            
            logger.warning("All MMBench sources failed, returning empty data")
            return []
            
        except Exception as e:
            logger.error(f"Error scraping MMBench: {e}")
            return []
    
    def _try_opencompass_api(self) -> Optional[List[Dict]]:
        """Try to get data from OpenCompass API endpoints"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            # Try different API endpoints
            api_endpoints = [
                "https://opencompass.org.cn/api/leaderboard/multimodal",
                "https://mmbench.opencompass.org.cn/api/leaderboard",
                "https://opencompass.org.cn/api/mmbench",
                "https://mmbench.opencompass.org.cn/api/data",
                "https://api.opencompass.org.cn/mmbench/leaderboard"
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = self.session.get(endpoint, headers=headers, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        processed = self._process_mmbench_data(data)
                        if processed:
                            logger.info(f"Successfully got data from OpenCompass API: {endpoint}")
                            return processed
                except Exception as e:
                    logger.debug(f"OpenCompass API endpoint {endpoint} failed: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"OpenCompass API approach failed: {e}")
        
        return None
    
    def _try_github_sources(self) -> Optional[List[Dict]]:
        """Try to get data from GitHub repositories"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            github_sources = [
                "https://raw.githubusercontent.com/open-compass/MMBench/main/results.json",
                "https://raw.githubusercontent.com/open-compass/MMBench/main/leaderboard.json",
                "https://raw.githubusercontent.com/open-compass/MMBench/main/data/leaderboard.json",
                "https://raw.githubusercontent.com/open-compass/VLMEvalKit/main/results/mmbench.json"
            ]
            
            for source in github_sources:
                try:
                    response = self.session.get(source, headers=headers, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        processed = self._process_mmbench_data(data)
                        if processed:
                            logger.info(f"Successfully got data from GitHub: {source}")
                            return processed
                            
                except Exception as e:
                    logger.debug(f"GitHub source {source} failed: {e}")
                    continue
            
            # Try GitHub API to find files
            try:
                api_response = self.session.get("https://api.github.com/repos/open-compass/MMBench/contents", headers=headers, timeout=10)
                if api_response.status_code == 200:
                    contents = api_response.json()
                    for item in contents:
                        if item['name'].endswith('.json') and any(keyword in item['name'].lower() for keyword in ['result', 'leaderboard', 'mmbench']):
                            try:
                                file_response = self.session.get(item['download_url'], headers=headers)
                                if file_response.status_code == 200:
                                    data = file_response.json()
                                    processed = self._process_mmbench_data(data)
                                    if processed:
                                        return processed
                            except Exception:
                                continue
            except Exception:
                pass
        
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
            return self._process_mmbench_data(json_data)
        
        # Try to find API endpoints
        api_data = self._try_find_api_endpoints(content, url)
        if api_data:
            return api_data
        
        # Fallback to HTML extraction
        return self._extract_from_html(content)
    
    def _extract_json_from_page(self, content: str) -> Optional[Dict]:
        """Extract JSON data from script tags"""
        patterns = [
            r'window\.__MMBENCH_DATA__\s*=\s*({.*?});',
            r'window\.__LEADERBOARD__\s*=\s*({.*?});',
            r'const\s+leaderboard\s*=\s*({.*?});',
            r'var\s+mmbenchData\s*=\s*({.*?});',
            r'"leaderboard":\s*(\[.*?\])',
            r'"results":\s*(\[.*?\])',
            r'"mmbench_results":\s*(\[.*?\])',
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
                f"{base_domain}/api/mmbench",
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
                        return self._process_mmbench_data(data)
                except Exception:
                    continue
        except Exception:
            pass
        
        return None
    
    def _process_mmbench_data(self, data: Dict) -> List[Dict]:
        """Process the extracted MMBench data"""
        models = []
        
        try:
            # Handle different data structures
            if isinstance(data, list):
                leaderboard_data = data
            elif isinstance(data, dict):
                leaderboard_data = data
                for key in ['leaderboard', 'results', 'models', 'data', 'mmbench_results']:
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
                            'domain': 'multimodal',
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
                    scores['MMBench Rank'] = i + 1
                    
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
                            'domain': 'multimodal',
                            'scraped_at': datetime.now().isoformat()
                        })
            
            logger.info(f"Extracted {len(models)} models from MMBench data")
            return models
            
        except Exception as e:
            logger.error(f"Error processing MMBench data: {e}")
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
                scores = {'MMBench Rank': i}
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
                        'domain': 'multimodal',
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
                        scores['MMBench Score'] = score_value
                        break
                    except ValueError:
                        continue
                
                if not scores:
                    scores['MMBench Rank'] = i
                
                if scores:
                    models.append({
                        'model': model_name,
                        'scores': scores,
                        'domain': 'multimodal',
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
            "mmbench": models
        }

if __name__ == "__main__":
    scraper = MMBenchScraper()
    data = scraper.scrape_all()
    print(f"Scraped {len(data.get('mmbench', []))} models from MMBench")
    
    if data.get('mmbench'):
        print("Sample model:")
        print(json.dumps(data['mmbench'][0], indent=2))