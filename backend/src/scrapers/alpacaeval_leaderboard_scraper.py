"""
AlpacaEval Leaderboard Scraper
Scrapes instruction-following quality evaluation data from Stanford AlpacaEval
"""

import requests
import json
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from .base import BaseScraper

logger = logging.getLogger(__name__)

class AlpacaEvalLeaderboardScraper(BaseScraper):
    """Scraper for AlpacaEval Leaderboard - Instruction-Following Quality"""
    
    def __init__(self):
        super().__init__(
            name="AlpacaEval Leaderboard",
            url="https://tatsu-lab.github.io/alpaca_eval"
        )
        
        # Try GitHub data source first
        self.data_url = "https://raw.githubusercontent.com/tatsu-lab/alpaca_eval/main/docs/leaderboard.csv"
        self.api_base = "https://api.github.com/repos/tatsu-lab/alpaca_eval"
        
        # Benchmark mapping for our system
        self.benchmark_mapping = {
            'alpaca_eval': 'AlpacaEval Win Rate',
            'win_rate': 'AlpacaEval Win Rate',
            'length_controlled_winrate': 'Length-Controlled Win Rate',
            'avg_length': 'Average Response Length',
            'standard_error': 'Standard Error',
            'n_total': 'Total Evaluations',
            'response_length': 'Response Length',
            'price_per_1000_tokens': 'Price per 1K Tokens'
        }
    
    def scrape(self) -> List[Dict]:
        """Scrape the AlpacaEval leaderboard"""
        try:
            logger.info(f"Scraping {self.name}")
            
            # First try to get CSV data directly
            csv_data = self._try_csv_source()
            if csv_data:
                return csv_data
            
            # Try GitHub API for latest data
            github_data = self._try_github_api()
            if github_data:
                return github_data
            
            # Fallback to web scraping
            return self._scrape_web_page()
            
        except Exception as e:
            logger.error(f"Error scraping AlpacaEval leaderboard: {e}")
            return []
    
    def _try_csv_source(self) -> Optional[List[Dict]]:
        """Try to fetch CSV data directly"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/csv'
            }
            
            response = self.session.get(self.data_url, headers=headers, timeout=10)
            if response.status_code == 200:
                return self._process_csv_data(response.text)
        except Exception as e:
            logger.warning(f"CSV source failed: {e}")
        
        return None
    
    def _process_csv_data(self, csv_content: str) -> List[Dict]:
        """Process CSV data"""
        models = []
        
        try:
            import csv
            import io
            
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            for i, row in enumerate(csv_reader):
                # Extract model name
                model_name = None
                for key in ['model', 'name', 'Model Name', 'model_name']:
                    if key in row and row[key]:
                        model_name = row[key].strip()
                        break
                
                if not model_name:
                    continue
                
                # Clean model name (remove common prefixes)
                if '/' in model_name:
                    clean_name = model_name.split('/')[-1]
                else:
                    clean_name = model_name
                
                # Extract scores
                scores = {}
                scores['Leaderboard Rank'] = i + 1  # Position in CSV
                
                for csv_key, value in row.items():
                    if not value or csv_key.lower() in ['model', 'name']:
                        continue
                    
                    try:
                        # Convert to float if possible
                        if isinstance(value, str):
                            # Handle percentage values
                            if '%' in value:
                                numeric_value = float(value.replace('%', ''))
                            else:
                                numeric_value = float(value)
                        else:
                            numeric_value = float(value)
                        
                        # Map to our benchmark names
                        benchmark_name = self.benchmark_mapping.get(csv_key.lower(), csv_key.replace('_', ' ').title())
                        scores[benchmark_name] = numeric_value
                        
                    except (ValueError, TypeError):
                        continue
                
                if scores:
                    models.append({
                        'model': clean_name,
                        'original_name': model_name,
                        'scores': scores,
                        'scraped_at': datetime.now().isoformat()
                    })
            
            logger.info(f"Extracted {len(models)} models from CSV data")
            return models
            
        except Exception as e:
            logger.error(f"Error processing CSV data: {e}")
            return []
    
    def _try_github_api(self) -> Optional[List[Dict]]:
        """Try to get data from GitHub API"""
        try:
            # Look for data files in the repository
            api_endpoints = [
                f"{self.api_base}/contents/results",
                f"{self.api_base}/contents/docs",
                f"{self.api_base}/contents/data"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            for endpoint in api_endpoints:
                try:
                    response = self.session.get(endpoint, headers=headers, timeout=10)
                    if response.status_code == 200:
                        files = response.json()
                        for file_info in files:
                            if file_info['name'].endswith('.json') and 'leaderboard' in file_info['name'].lower():
                                # Try to get the file content
                                file_response = self.session.get(file_info['download_url'], headers=headers)
                                if file_response.status_code == 200:
                                    data = file_response.json()
                                    return self._process_json_data(data)
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"GitHub API failed: {e}")
        
        return None
    
    def _process_json_data(self, data: Dict) -> List[Dict]:
        """Process JSON data from GitHub"""
        models = []
        
        try:
            # Handle different JSON structures
            leaderboard_data = data
            if isinstance(data, dict):
                for key in ['leaderboard', 'results', 'models', 'data']:
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
                for key in ['model', 'name', 'model_name', 'generator']:
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
                
                # Extract scores
                scores = {}
                scores['Leaderboard Rank'] = i + 1
                
                # Look for various metrics
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
            
            return models
            
        except Exception as e:
            logger.error(f"Error processing JSON data: {e}")
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
                return self._process_json_data(json_data)
            
            # Fallback to HTML table extraction
            return self._extract_from_html(content)
            
        except Exception as e:
            logger.error(f"Error scraping web page: {e}")
            return []
    
    def _extract_json_from_page(self, content: str) -> Optional[Dict]:
        """Extract JSON data from script tags"""
        patterns = [
            r'window\.__LEADERBOARD_DATA__\s*=\s*({.*?});',
            r'const\s+leaderboardData\s*=\s*({.*?});',
            r'var\s+leaderboardData\s*=\s*({.*?});',
            r'"leaderboard":\s*(\[.*?\])',
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
                for header in ['Model', 'Name', 'Generator']:
                    if header in row_data and row_data[header]:
                        model_name = row_data[header]
                        break
                
                if not model_name:
                    continue
                
                # Extract numeric scores
                scores = {'Leaderboard Rank': i}
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
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Scrape all data and return in expected format"""
        models = self.scrape()
        return {
            "alpacaeval_leaderboard": models
        }

if __name__ == "__main__":
    scraper = AlpacaEvalLeaderboardScraper()
    data = scraper.scrape_all()
    print(f"Scraped {len(data.get('alpacaeval_leaderboard', []))} models from AlpacaEval")
    
    if data.get('alpacaeval_leaderboard'):
        print("Sample model:")
        print(json.dumps(data['alpacaeval_leaderboard'][0], indent=2))