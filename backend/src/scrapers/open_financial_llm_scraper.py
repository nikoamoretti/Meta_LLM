"""
Open Financial LLM Leaderboard Scraper
Scrapes financial NLP tasks evaluation data from HuggingFace FinLLM leaderboard
"""

import requests
import json
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from .base import BaseScraper

logger = logging.getLogger(__name__)

class OpenFinancialLLMScraper(BaseScraper):
    """Scraper for Open Financial LLM Leaderboard - Financial NLP Tasks"""
    
    def __init__(self):
        super().__init__(
            name="Open Financial LLM Leaderboard",
            url="https://huggingface.co/spaces/ChanceFocus/open-finllm-leaderboard"
        )
        
        # HuggingFace Spaces API endpoints
        self.hf_api_base = "https://huggingface.co/api/spaces/ChanceFocus/open-finllm-leaderboard"
        self.hf_datasets_api = "https://datasets-server.huggingface.co/rows"
        
        # Alternative data sources
        self.alternative_urls = [
            "https://huggingface.co/datasets/ChanceFocus/open-finllm-leaderboard",
            "https://github.com/chancefocus/PIXIU",
            "https://raw.githubusercontent.com/chancefocus/PIXIU/main/leaderboard.json"
        ]
        
        # GitHub repository for FinLLM data
        self.github_api = "https://api.github.com/repos/chancefocus/PIXIU"
        self.github_raw = "https://raw.githubusercontent.com/chancefocus/PIXIU/main"
        
        # Benchmark mapping for our system
        self.benchmark_mapping = {
            'flare_ner': 'FLARE NER',
            'flare_sm': 'FLARE Sentiment',
            'flare_fpb': 'FLARE FPB',
            'flare_fiqasa': 'FLARE FiQASA',
            'flare_headlines': 'FLARE Headlines',
            'flare_fomc': 'FLARE FOMC',
            'finqa': 'FinQA',
            'tatqa': 'TAT-QA',
            'convfinqa': 'ConvFinQA',
            'fineval': 'FinEval',
            'cfleb': 'CFLEB',
            'financial_phrasebank': 'Financial Phrasebank',
            'financial_sentiment': 'Financial Sentiment',
            'earnings_call_analysis': 'Earnings Call Analysis',
            'credit_scoring': 'Credit Scoring',
            'fraud_detection': 'Fraud Detection',
            'market_prediction': 'Market Prediction',
            'risk_assessment': 'Risk Assessment',
            'portfolio_optimization': 'Portfolio Optimization',
            'average_score': 'Average Score',
            'overall': 'Overall Score'
        }
    
    def scrape(self) -> List[Dict]:
        """Scrape the Open Financial LLM leaderboard"""
        try:
            logger.info(f"Scraping {self.name}")
            
            # Try HuggingFace Spaces API first
            hf_data = self._try_huggingface_api()
            if hf_data:
                return hf_data
            
            # Try direct dataset access
            dataset_data = self._try_dataset_api()
            if dataset_data:
                return dataset_data
            
            # Try GitHub sources
            github_data = self._try_github_sources()
            if github_data:
                return github_data
            
            # Fallback to web scraping
            return self._scrape_web_page()
            
        except Exception as e:
            logger.error(f"Error scraping Open Financial LLM leaderboard: {e}")
            return []
    
    def _try_huggingface_api(self) -> Optional[List[Dict]]:
        """Try to get data from HuggingFace Spaces API"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            # Try different API endpoints
            api_endpoints = [
                f"{self.hf_api_base}/api/leaderboard",
                f"{self.hf_api_base}/api/data",
                f"{self.hf_api_base}/gradio_api/call/get_leaderboard",
                "https://chancefocus-open-finllm-leaderboard.hf.space/api/leaderboard",
                "https://huggingface.co/api/spaces/ChanceFocus/open-finllm-leaderboard/runtime"
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = self.session.get(endpoint, headers=headers, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        processed = self._process_finllm_data(data)
                        if processed:
                            logger.info(f"Successfully got data from HF API: {endpoint}")
                            return processed
                except Exception as e:
                    logger.debug(f"HF API endpoint {endpoint} failed: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"HuggingFace API approach failed: {e}")
        
        return None
    
    def _try_dataset_api(self) -> Optional[List[Dict]]:
        """Try to get data from HuggingFace Datasets API"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            # Try to access the dataset directly
            dataset_params = {
                'dataset': 'ChanceFocus/open-finllm-leaderboard',
                'config': 'default',
                'split': 'train',
                'offset': 0,
                'length': 100
            }
            
            response = self.session.get(self.hf_datasets_api, params=dataset_params, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return self._process_dataset_data(data)
        
        except Exception as e:
            logger.warning(f"Dataset API failed: {e}")
        
        return None
    
    def _try_github_sources(self) -> Optional[List[Dict]]:
        """Try to get data from GitHub repositories"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            github_sources = [
                f"{self.github_raw}/leaderboard.json",
                f"{self.github_raw}/results.json",
                f"{self.github_raw}/finllm_leaderboard.json",
                f"{self.github_raw}/data/leaderboard.json",
                f"{self.github_raw}/evaluation/results.json"
            ]
            
            for source in github_sources:
                try:
                    response = self.session.get(source, headers=headers, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        processed = self._process_finllm_data(data)
                        if processed:
                            logger.info(f"Successfully got data from GitHub: {source}")
                            return processed
                            
                except Exception as e:
                    logger.debug(f"GitHub source {source} failed: {e}")
                    continue
            
            # Try repository contents API
            contents_response = self.session.get(f"{self.github_api}/contents", headers=headers, timeout=10)
            if contents_response.status_code == 200:
                contents = contents_response.json()
                for item in contents:
                    if item['name'].endswith('.json') and any(keyword in item['name'].lower() for keyword in ['leaderboard', 'results', 'finllm']):
                        try:
                            file_response = self.session.get(item['download_url'], headers=headers)
                            if file_response.status_code == 200:
                                data = file_response.json()
                                processed = self._process_finllm_data(data)
                                if processed:
                                    return processed
                        except Exception:
                            continue
        
        except Exception as e:
            logger.warning(f"GitHub sources failed: {e}")
        
        return None
    
    def _process_finllm_data(self, data: Dict) -> List[Dict]:
        """Process data from any source"""
        models = []
        
        try:
            # Handle different API response structures
            leaderboard_data = data
            if isinstance(data, dict):
                for key in ['data', 'leaderboard', 'models', 'results', 'finllm_results']:
                    if key in data and isinstance(data[key], list):
                        leaderboard_data = data[key]
                        break
            
            if not isinstance(leaderboard_data, list):
                return []
            
            for i, item in enumerate(leaderboard_data):
                if not isinstance(item, dict):
                    continue
                
                # Extract model name
                model_name = None
                for key in ['model', 'model_name', 'name', 'Model']:
                    if key in item and item[key]:
                        model_name = str(item[key])
                        break
                
                if not model_name:
                    continue
                
                # Clean model name
                if '/' in model_name and model_name.count('/') == 1:
                    # Keep organization/model format for financial models
                    clean_name = model_name
                else:
                    clean_name = model_name.split('/')[-1] if '/' in model_name else model_name
                
                # Extract scores
                scores = {}
                scores['FinLLM Rank'] = i + 1
                
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
                        'organization': model_name.split('/')[0] if '/' in model_name else '',
                        'domain': 'finance',
                        'scraped_at': datetime.now().isoformat()
                    })
            
            return models
            
        except Exception as e:
            logger.error(f"Error processing FinLLM data: {e}")
            return []
    
    def _process_dataset_data(self, data: Dict) -> List[Dict]:
        """Process data from HuggingFace Datasets API"""
        models = []
        
        try:
            rows = data.get('rows', [])
            
            for i, row in enumerate(rows):
                row_data = row.get('row', {})
                
                model_name = row_data.get('model') or row_data.get('model_name') or row_data.get('name')
                if not model_name:
                    continue
                
                # Clean model name
                if '/' in model_name and model_name.count('/') == 1:
                    clean_name = model_name
                else:
                    clean_name = model_name.split('/')[-1] if '/' in model_name else model_name
                
                scores = {}
                scores['FinLLM Rank'] = i + 1
                
                for key, value in row_data.items():
                    if key.lower() in ['model', 'name', 'model_name'] or not isinstance(value, (int, float)):
                        continue
                    
                    benchmark_name = self.benchmark_mapping.get(key.lower(), key.replace('_', ' ').title())
                    scores[benchmark_name] = value
                
                if scores:
                    models.append({
                        'model': clean_name,
                        'original_name': model_name,
                        'scores': scores,
                        'domain': 'finance',
                        'scraped_at': datetime.now().isoformat()
                    })
            
            return models
            
        except Exception as e:
            logger.error(f"Error processing dataset data: {e}")
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
            
            # Look for embedded data in script tags
            json_data = self._extract_json_from_page(content)
            if json_data:
                return self._process_finllm_data(json_data)
            
            # Fallback to HTML table extraction
            return self._extract_from_html(content)
            
        except Exception as e:
            logger.error(f"Error scraping web page: {e}")
            return []
    
    def _extract_json_from_page(self, content: str) -> Optional[Dict]:
        """Extract JSON data from script tags"""
        patterns = [
            r'window\.__gradio_config__\s*=\s*({.*?});',
            r'window\.__LEADERBOARD__\s*=\s*({.*?});',
            r'const\s+leaderboard\s*=\s*({.*?});',
            r'"data":\s*(\[.*?\])',
            r'"leaderboard":\s*(\[.*?\])',
            r'"finllm_results":\s*(\[.*?\])'
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
                scores = {'FinLLM Rank': i}
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
                        'domain': 'finance',
                        'scraped_at': datetime.now().isoformat()
                    })
            
            return models
            
        except Exception as e:
            logger.error(f"Error processing table: {e}")
            return []
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Scrape all data and return in expected format"""
        models = self.scrape()
        return {
            "open_financial_llm": models
        }

if __name__ == "__main__":
    scraper = OpenFinancialLLMScraper()
    data = scraper.scrape_all()
    print(f"Scraped {len(data.get('open_financial_llm', []))} models from Open Financial LLM")
    
    if data.get('open_financial_llm'):
        print("Sample model:")
        print(json.dumps(data['open_financial_llm'][0], indent=2))