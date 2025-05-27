"""
Chatbot Arena Leaderboard Scraper
Extracts data from all categories on HuggingFace Chatbot Arena
"""
import asyncio
import logging
import re
import json
from typing import List, Dict
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ChatbotArenaScraper:
    """Scraper for HuggingFace Chatbot Arena Leaderboard"""
    
    def __init__(self):
        self.base_url = "https://huggingface.co/spaces/lmarena-ai/chatbot-arena-leaderboard"
        
        # Categories from the dropdown
        self.categories = [
            "Overall",
            "Math", 
            "Instruction Following",
            "Multi-Turn",
            "Creative Writing", 
            "Coding",
            "Hard Prompts",
            "Hard Prompts (English)",
            "Longer Query",
            "English",
            "Chinese", 
            "French",
            "German",
            "Spanish",
            "Russian",
            "Japanese",
            "Korean",
            "Exclude Ties",
            "Exclude Short Query (< 5 tokens)",
            "Exclude Refusal"
        ]
    
    async def scrape_arena_data(self) -> List[Dict]:
        """Scrape model performance data from Chatbot Arena leaderboard"""
        try:
            logger.info("Scraping Chatbot Arena leaderboard...")
            
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(
                    url=self.base_url,
                    wait_for="css:table, .leaderboard, .dataframe",
                    delay=10,  # Longer delay for HF spaces to load
                    js_code="""
                    // Wait for the page to fully load
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    
                    // Scroll to make sure everything is loaded
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    // Try to click on different category options if they exist
                    const categoryDropdown = document.querySelector('select, .dropdown, [role="combobox"]');
                    if (categoryDropdown) {
                        console.log('Found category dropdown');
                    }
                    """
                )
                
                if not result.success:
                    logger.error(f"Failed to crawl Arena: {result.error_message}")
                    return []
                
                # Parse the HTML content
                soup = BeautifulSoup(result.html, 'html.parser')
                
                # Extract model data using multiple strategies
                models_data = self._extract_arena_data(soup, result.html)
                
                logger.info(f"Chatbot Arena: {len(models_data)} models extracted")
                return models_data
                
        except Exception as e:
            logger.error(f"Chatbot Arena scraping failed: {e}")
            return []
    
    def _extract_arena_data(self, soup: BeautifulSoup, raw_html: str) -> List[Dict]:
        """Extract data using multiple strategies"""
        models = {}
        
        # Strategy 1: Look for tables
        tables = soup.find_all('table')
        if tables:
            logger.info(f"Found {len(tables)} tables")
            for table in tables:
                self._extract_from_table(table, models)
        
        # Strategy 2: Look for JSON data in script tags
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and ('leaderboard' in script.string.lower() or 'arena' in script.string.lower()):
                self._extract_from_script(script.string, models)
        
        # Strategy 3: Look for specific HuggingFace components
        self._extract_from_hf_components(soup, models)
        
        # Strategy 4: Extract from raw HTML patterns
        self._extract_from_patterns(raw_html, models)
        
        return list(models.values())
    
    def _extract_from_table(self, table, models: Dict):
        """Extract data from HTML tables"""
        try:
            rows = table.find_all('tr')
            headers = []
            
            # Find header row
            header_row = rows[0] if rows else None
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            
            # Process data rows
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:  # At least rank, model, score
                    try:
                        # Extract model name (usually in 2nd column)
                        model_name = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        
                        # Extract score (look for numbers)
                        score = None
                        for cell in cells[2:]:
                            cell_text = cell.get_text(strip=True)
                            # Look for Arena Score pattern
                            score_match = re.search(r'(\d+\.?\d*)', cell_text)
                            if score_match:
                                score = float(score_match.group(1))
                                break
                        
                        if model_name and score is not None:
                            if model_name not in models:
                                models[model_name] = {
                                    'model': model_name,
                                    'scores': {},
                                    'source': 'Chatbot Arena'
                                }
                            models[model_name]['scores']['arena_score'] = score
                            
                    except (ValueError, IndexError) as e:
                        continue
                        
        except Exception as e:
            logger.debug(f"Error extracting from table: {e}")
    
    def _extract_from_script(self, script_content: str, models: Dict):
        """Extract data from JavaScript/JSON in script tags"""
        try:
            # Look for JSON data patterns
            json_patterns = [
                r'leaderboard["\']?\s*:\s*(\[.*?\])',
                r'data["\']?\s*:\s*(\[.*?\])',
                r'models["\']?\s*:\s*(\[.*?\])'
            ]
            
            for pattern in json_patterns:
                matches = re.finditer(pattern, script_content, re.DOTALL)
                for match in matches:
                    try:
                        json_data = json.loads(match.group(1))
                        if isinstance(json_data, list):
                            for item in json_data:
                                if isinstance(item, dict) and 'model' in item:
                                    model_name = item.get('model', '')
                                    score = item.get('score', item.get('arena_score', item.get('rating')))
                                    
                                    if model_name and score is not None:
                                        if model_name not in models:
                                            models[model_name] = {
                                                'model': model_name,
                                                'scores': {},
                                                'source': 'Chatbot Arena'
                                            }
                                        models[model_name]['scores']['arena_score'] = float(score)
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.debug(f"Error extracting from script: {e}")
    
    def _extract_from_hf_components(self, soup: BeautifulSoup, models: Dict):
        """Extract from HuggingFace specific components"""
        try:
            # Look for gradio components
            gradio_elements = soup.find_all(['div', 'span'], class_=lambda x: x and 'gradio' in x.lower())
            
            # Look for dataframe-like structures
            dataframe_elements = soup.find_all(['div', 'table'], class_=lambda x: x and any(
                term in x.lower() for term in ['dataframe', 'table', 'leaderboard']
            ))
            
            for element in gradio_elements + dataframe_elements:
                text = element.get_text()
                # Look for model names and scores in the text
                lines = text.split('\n')
                for line in lines:
                    # Pattern: model_name score
                    match = re.search(r'([\w\-\.]+(?:\s+[\w\-\.]+)*)\s+(\d+\.?\d*)', line.strip())
                    if match:
                        model_name = match.group(1).strip()
                        score = float(match.group(2))
                        
                        if len(model_name) > 2 and 500 <= score <= 2000:  # Arena scores typically in this range
                            if model_name not in models:
                                models[model_name] = {
                                    'model': model_name,
                                    'scores': {},
                                    'source': 'Chatbot Arena'
                                }
                            models[model_name]['scores']['arena_score'] = score
                            
        except Exception as e:
            logger.debug(f"Error extracting from HF components: {e}")
    
    def _extract_from_patterns(self, raw_html: str, models: Dict):
        """Extract using regex patterns on raw HTML"""
        try:
            # Pattern for model names followed by scores
            patterns = [
                r'(?:gpt|claude|gemini|llama|mistral|qwen|deepseek|o1|o3)[\w\-\.\s]*?(\d{3,4}\.?\d*)',
                r'"model"["\s]*:["\s]*"([^"]+)"[^}]*"score"["\s]*:["\s]*(\d+\.?\d*)',
                r'<td[^>]*>([^<]+(?:gpt|claude|gemini|llama)[^<]*)</td>[^<]*<td[^>]*>(\d+\.?\d*)</td>'
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, raw_html, re.IGNORECASE)
                for match in matches:
                    try:
                        if len(match.groups()) == 2:
                            model_name = match.group(1).strip()
                            score = float(match.group(2))
                        else:
                            # Handle single group patterns
                            text = match.group(0)
                            score_match = re.search(r'(\d{3,4}\.?\d*)', text)
                            if score_match:
                                score = float(score_match.group(1))
                                model_name = text.replace(score_match.group(1), '').strip()
                            else:
                                continue
                        
                        if model_name and 500 <= score <= 2000:
                            if model_name not in models:
                                models[model_name] = {
                                    'model': model_name,
                                    'scores': {},
                                    'source': 'Chatbot Arena'
                                }
                            models[model_name]['scores']['arena_score'] = score
                            
                    except (ValueError, IndexError):
                        continue
                        
        except Exception as e:
            logger.debug(f"Error extracting from patterns: {e}")
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Get all data from Chatbot Arena"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            data = loop.run_until_complete(self.scrape_arena_data())
            return {"chatbot_arena": data}
        finally:
            loop.close() 