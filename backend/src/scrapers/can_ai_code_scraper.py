"""
HF Can-AI-Code Leaderboard Scraper
Scrapes real coding performance data from Can-AI-Code leaderboard using headless browser automation
URL: https://huggingface.co/spaces/can-ai-code/leaderboard
"""

import asyncio
from playwright.async_api import async_playwright
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

class CanAICodeLeaderboardScraper:
    """Headless browser scraper for Can-AI-Code Leaderboard"""
    
    def __init__(self):
        # Try multiple Can-AI-Code URLs
        self.urls = [
            "https://huggingface.co/spaces/mike-ravkine/can-ai-code-results",
            "https://huggingface.co/spaces/can-ai-code/leaderboard"
        ]
        self.timeout = 60000  # 60 seconds
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
    def scrape_with_requests(self) -> List[Dict]:
        """Try scraping with simple requests first"""
        for url in self.urls:
            try:
                logger.info(f"Trying requests-based scraping for {url}")
                response = requests.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for tables
                tables = soup.find_all('table')
                logger.info(f"Found {len(tables)} tables with requests for {url}")
                
                extracted_data = []
                
                for table_index, table in enumerate(tables):
                    # Get headers
                    headers = table.find_all(['th', 'td'])[:10]  # First row likely headers
                    header_texts = [h.get_text().strip().lower() for h in headers]
                    logger.info(f"Table {table_index} headers: {header_texts}")
                    
                    # Find model and score columns
                    model_col = None
                    score_cols = []
                    
                    for i, header in enumerate(header_texts):
                        if any(keyword in header for keyword in ['model', 'name']):
                            model_col = i
                        elif any(keyword in header for keyword in ['score', 'pass', 'percentage', 'accuracy', 'results', '%']):
                            score_cols.append((i, header))
                    
                    if model_col is None or not score_cols:
                        continue
                    
                    # Extract rows
                    rows = table.find_all('tr')[1:]  # Skip header row
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) <= max([model_col] + [col for col, _ in score_cols]):
                            continue
                        
                        model_name = cells[model_col].get_text().strip()
                        if not model_name or model_name.lower() in ['model', 'name']:
                            continue
                        
                        for score_col, score_header in score_cols:
                            if len(cells) <= score_col:
                                continue
                            
                            score_text = cells[score_col].get_text().strip()
                            score_match = re.search(r'(\d+\.?\d*)', score_text)
                            if not score_match:
                                continue
                            
                            score = float(score_match.group(1))
                            if score <= 1 and '%' not in score_text:
                                score = score * 100
                            
                            normalized_name = self.normalize_model_name(model_name)
                            
                            extracted_data.append({
                                'model_name': normalized_name,
                                'raw_model_name': model_name,
                                'score': score,
                                'metric': score_header,
                                'benchmark': 'Can-AI-Code Leaderboard',
                                'source_url': url
                            })
                            
                            logger.info(f"Extracted: {normalized_name} = {score}% ({score_header})")
                            break
                    
                    if extracted_data:
                        break
                
                if extracted_data:
                    return self._deduplicate_models(extracted_data)
                
            except Exception as e:
                logger.error(f"Requests-based scraping failed for {url}: {e}")
                continue
        
        return []
        
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
    
    async def scrape_leaderboard_data(self) -> List[Dict]:
        """Scrape Can-AI-Code leaderboard - try requests first, then browser"""
        
        # Try simple requests first
        logger.info("Attempting requests-based scraping first...")
        extracted_data = self.scrape_with_requests()
        if extracted_data:
            logger.info(f"✅ Successfully extracted {len(extracted_data)} models with requests")
            return extracted_data
        
        # Fall back to browser scraping
        logger.info("Requests failed, falling back to browser scraping...")
        logger.warning("Browser scraping not implemented for Can-AI-Code yet")
        return []
                    # Look for other data containers like divs or custom components
                    data_containers = await page.query_selector_all('[class*="leaderboard"], [class*="table"], [id*="leaderboard"]')
                    logger.info(f"Found {len(data_containers)} potential data containers")
                else:
                    logger.info(f"Found {len(tables)} tables on the page")
                
                # Look for embedded JSON data first
                page_content = await page.content()
                json_data = self._extract_json_from_content(page_content)
                if json_data:
                    extracted_data = self._process_json_data(json_data)
                    await browser.close()
                    return extracted_data
                
                # If no JSON data, try to extract from tables
                for table_index, table in enumerate(tables):
                    # Get table headers
                    headers = await table.query_selector_all('thead th, thead td, tr:first-child th, tr:first-child td')
                    header_texts = []
                    for header in headers:
                        text = await header.inner_text()
                        header_texts.append(text.strip().lower())
                    
                    logger.info(f"Table {table_index} headers: {header_texts}")
                    
                    # Look for model/score columns
                    model_col = None
                    score_col = None
                    
                    for i, header in enumerate(header_texts):
                        if any(keyword in header for keyword in ['model', 'name']):
                            model_col = i
                        elif any(keyword in header for keyword in ['score', 'pass', 'percentage', 'accuracy', 'results']):
                            score_col = i
                            break
                    
                    if model_col is None or score_col is None:
                        logger.info(f"Table {table_index}: Could not identify model/score columns")
                        continue
                    
                    # Extract data rows
                    rows = await table.query_selector_all('tbody tr, tr')
                    valid_rows = []
                    for row in rows:
                        cells = await row.query_selector_all('td, th')
                        if len(cells) > max(model_col, score_col):
                            valid_rows.append(row)
                    
                    logger.info(f"Table {table_index}: Found {len(valid_rows)} data rows")
                    
                    for row in valid_rows:
                        cells = await row.query_selector_all('td, th')
                        if len(cells) <= max(model_col, score_col):
                            continue
                            
                        model_cell = cells[model_col]
                        score_cell = cells[score_col]
                        
                        model_name = await model_cell.inner_text()
                        score_text = await score_cell.inner_text()
                        
                        model_name = model_name.strip()
                        score_text = score_text.strip()
                        
                        if not model_name or not score_text or model_name.lower() in ['model', 'name']:
                            continue
                        
                        # Extract numeric score
                        score_match = re.search(r'(\\d+\\.?\\d*)', score_text)
                        if not score_match:
                            continue
                            
                        score = float(score_match.group(1))
                        
                        # Normalize model name
                        normalized_name = self.normalize_model_name(model_name)
                        
                        extracted_data.append({
                            'model_name': normalized_name,
                            'raw_model_name': model_name,
                            'score': score,
                            'metric': 'coding_score',
                            'benchmark': 'Can-AI-Code Leaderboard',
                            'source_table': table_index
                        })
                    
                    if extracted_data:
                        logger.info(f"Successfully extracted data from table {table_index}")
                        break
                
                await browser.close()
                
                if not extracted_data:
                    logger.warning("No data extracted from any table")
                    return []
                
                # Deduplicate models
                deduplicated_data = self._deduplicate_models(extracted_data)
                
                logger.info(f"Successfully extracted {len(extracted_data)} model scores")
                logger.info(f"After deduplication: {len(deduplicated_data)} unique models")
                return deduplicated_data
                
            except Exception as e:
                logger.error(f"Failed to scrape Can-AI-Code leaderboard: {e}")
                if 'browser' in locals():
                    await browser.close()
                return []
    
    def _extract_json_from_content(self, content: str) -> Optional[Dict]:
        """Extract JSON data from page content"""
        patterns = [
            r'window\\.__gradio_config__\\s*=\\s*({.*?});',
            r'window\\.__LEADERBOARD__\\s*=\\s*({.*?});',
            r'const\\s+leaderboard\\s*=\\s*({.*?});',
            r'"data":\\s*(\\[.*?\\])',
            r'"leaderboard":\\s*(\\[.*?\\])'
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
    
    def _process_json_data(self, data: Dict) -> List[Dict]:
        """Process extracted JSON data"""
        extracted_data = []
        
        try:
            # Handle different JSON structures
            leaderboard_data = data
            if isinstance(data, dict):
                for key in ['data', 'leaderboard', 'models', 'results']:
                    if key in data and isinstance(data[key], list):
                        leaderboard_data = data[key]
                        break
            
            if not isinstance(leaderboard_data, list):
                return []
            
            for item in leaderboard_data:
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
                
                # Extract scores
                score = None
                for key, value in item.items():
                    if key.lower() in ['model', 'name', 'model_name']:
                        continue
                    if isinstance(value, (int, float)) and value > 0:
                        score = value
                        break
                
                if score is None:
                    continue
                
                # Normalize model name
                normalized_name = self.normalize_model_name(model_name)
                
                extracted_data.append({
                    'model_name': normalized_name,
                    'raw_model_name': model_name,
                    'score': score,
                    'metric': 'coding_score',
                    'benchmark': 'Can-AI-Code Leaderboard'
                })
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error processing JSON data: {e}")
            return []
    
    def _deduplicate_models(self, data: List[Dict]) -> List[Dict]:
        """Deduplicate models by normalized name, keeping highest score"""
        model_groups = {}
        
        for model_data in data:
            normalized_name = model_data['model_name']
            if normalized_name not in model_groups:
                model_groups[normalized_name] = []
            model_groups[normalized_name].append(model_data)
        
        deduplicated = []
        for normalized_name, models in model_groups.items():
            if len(models) == 1:
                deduplicated.append(models[0])
            else:
                best_model = max(models, key=lambda x: x['score'])
                logger.info(f"Deduplicated {normalized_name}: kept score {best_model['score']} from {len(models)} variants")
                deduplicated.append(best_model)
        
        return deduplicated
    
    def save_to_json(self, data: List[Dict], filename: str = None) -> str:
        """Save scraped data to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"can_ai_code_leaderboard_{timestamp}.json"
        
        output_data = {
            'source': 'huggingface.co/spaces/can-ai-code/leaderboard',
            'scraped_at': datetime.now().isoformat(),
            'total_models': len(data),
            'benchmark_info': {
                'name': 'Can-AI-Code Leaderboard',
                'description': 'AI coding capability evaluation',
                'metric': 'Coding performance score'
            },
            'models': data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(data)} model scores to {filename}")
        return filename

async def main():
    """Main function to run the scraper"""
    scraper = CanAICodeLeaderboardScraper()
    
    # Scrape the data
    data = await scraper.scrape_leaderboard_data()
    
    if data:
        # Save to JSON file
        filename = scraper.save_to_json(data)
        
        # Print summary
        print(f"\\n✅ Successfully scraped Can-AI-Code leaderboard!")
        print(f"📊 Found {len(data)} models")
        print(f"💾 Saved to: {filename}")
        print(f"\\nTop 5 models:")
        
        # Sort by score and show top 5
        sorted_data = sorted(data, key=lambda x: x['score'], reverse=True)
        for i, model in enumerate(sorted_data[:5], 1):
            print(f"  {i}. {model['model_name']}: {model['score']}%")
    else:
        print("❌ Failed to scrape any data from Can-AI-Code leaderboard")

if __name__ == "__main__":
    asyncio.run(main())