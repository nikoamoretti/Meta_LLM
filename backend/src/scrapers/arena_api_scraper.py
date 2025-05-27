"""
Chatbot Arena API Scraper
Multiple strategies to get Arena leaderboard data
"""
import asyncio
import logging
import re
import json
import requests
from typing import List, Dict
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ArenaAPIScraper:
    """Advanced scraper for Chatbot Arena data using multiple strategies"""
    
    def __init__(self):
        self.base_url = "https://huggingface.co/spaces/lmarena-ai/chatbot-arena-leaderboard"
        self.api_endpoints = [
            "https://lmarena-ai-chatbot-arena-leaderboard.hf.space/api/leaderboard",
            "https://lmarena-ai-chatbot-arena-leaderboard.hf.space/api/data",
            "https://lmarena-ai-chatbot-arena-leaderboard.hf.space/gradio_api/call/get_leaderboard",
        ]
        
        # Fallback data based on the screenshot provided
        self.fallback_data = [
            {"model": "Gemini-Pro-Preview-05-06", "arena_score": 1446, "votes": 6115, "organization": "Google"},
            {"model": "Gemini-Flash-Preview-05-20", "arena_score": 1418, "votes": 3892, "organization": "Google"},
            {"model": "o1-16", "arena_score": 1409, "votes": 7921, "organization": "OpenAI"},
            {"model": "o1-latest (2025-03-26)", "arena_score": 1405, "votes": 10280, "organization": "OpenAI"},
            {"model": "o1-preview-02-24", "arena_score": 1399, "votes": 14840, "organization": "xAI"},
            {"model": "o1-preview", "arena_score": 1394, "votes": 15276, "organization": "OpenAI"},
            {"model": "Gemini-Flash-Preview-04-17", "arena_score": 1387, "votes": 6938, "organization": "Google"},
            {"model": "DeepSeek-V3-0324", "arena_score": 1368, "votes": 9741, "organization": "DeepSeek"},
            {"model": "GPT-4o-2025-04-14", "arena_score": 1365, "votes": 6094, "organization": "OpenAI"},
            {"model": "Qwen-Turbos-20250416", "arena_score": 1356, "votes": 5111, "organization": "Tencent"},
            {"model": "DeepSeek-R1", "arena_score": 1354, "votes": 19339, "organization": "DeepSeek"},
            {"model": "Gemini-Flash-001", "arena_score": 1351, "votes": 24928, "organization": "Google"},
            {"model": "Mistral-Medium-3", "arena_score": 1343, "votes": 3327, "organization": "Mistral"},
            {"model": "GPT-4o-2025-04-16", "arena_score": 1343, "votes": 6102, "organization": "OpenAI"},
            {"model": "Claude-3.5-Sonnet-17", "arena_score": 1346, "votes": 29041, "organization": "OpenAI"},
            {"model": "Gemini-3-27B-it", "arena_score": 1339, "votes": 12989, "organization": "Google"}
        ]
    
    async def scrape_arena_data(self) -> List[Dict]:
        """Scrape Arena data using multiple strategies"""
        try:
            logger.info("Trying multiple strategies to get Arena data...")
            
            # Strategy 1: Try API endpoints
            api_data = await self._try_api_endpoints()
            if api_data:
                logger.info(f"Got {len(api_data)} models from API")
                return api_data
            
            # Strategy 2: Try advanced web scraping
            web_data = await self._try_advanced_scraping()
            if web_data:
                logger.info(f"Got {len(web_data)} models from web scraping")
                return web_data
            
            # Strategy 3: Use fallback data
            logger.info("Using fallback data from screenshot")
            return self._get_fallback_data()
                
        except Exception as e:
            logger.error(f"Arena scraping failed: {e}")
            return self._get_fallback_data()
    
    async def _try_api_endpoints(self) -> List[Dict]:
        """Try various API endpoints"""
        for endpoint in self.api_endpoints:
            try:
                logger.info(f"Trying API endpoint: {endpoint}")
                
                # Try direct requests first
                response = requests.get(endpoint, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        return self._process_api_data(data)
                
                # Try with crawl4ai for JS-heavy endpoints
                async with AsyncWebCrawler() as crawler:
                    result = await crawler.arun(url=endpoint, delay=5)
                    if result.success:
                        try:
                            data = json.loads(result.html)
                            if isinstance(data, list) and len(data) > 0:
                                return self._process_api_data(data)
                        except json.JSONDecodeError:
                            continue
                            
            except Exception as e:
                logger.debug(f"API endpoint {endpoint} failed: {e}")
                continue
        
        return []
    
    async def _try_advanced_scraping(self) -> List[Dict]:
        """Try advanced web scraping with longer waits"""
        try:
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(
                    url=self.base_url,
                    wait_for="css:table, .dataframe, iframe",
                    delay=30,  # Much longer delay
                    js_code="""
                    // Wait for Gradio to fully load
                    await new Promise(resolve => setTimeout(resolve, 20000));
                    
                    // Look for iframe content
                    const iframes = document.querySelectorAll('iframe');
                    console.log('Found iframes:', iframes.length);
                    
                    // Try to access iframe content
                    for (let iframe of iframes) {
                        try {
                            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                            const tables = iframeDoc.querySelectorAll('table');
                            console.log('Tables in iframe:', tables.length);
                        } catch (e) {
                            console.log('Cannot access iframe content:', e.message);
                        }
                    }
                    
                    // Scroll and wait more
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    """
                )
                
                if result.success:
                    soup = BeautifulSoup(result.html, 'html.parser')
                    
                    # Look for iframe sources
                    iframes = soup.find_all('iframe')
                    for iframe in iframes:
                        src = iframe.get('src')
                        if src and 'gradio' in src:
                            logger.info(f"Found Gradio iframe: {src}")
                            # Try to scrape the iframe content
                            iframe_data = await self._scrape_iframe(src)
                            if iframe_data:
                                return iframe_data
                    
                    # Try to extract any data from the main page
                    return self._extract_from_html(soup, result.html)
        
        except Exception as e:
            logger.error(f"Advanced scraping failed: {e}")
        
        return []
    
    async def _scrape_iframe(self, iframe_url: str) -> List[Dict]:
        """Scrape data from Gradio iframe"""
        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(
                    url=iframe_url,
                    wait_for="css:table, .dataframe",
                    delay=20
                )
                
                if result.success:
                    soup = BeautifulSoup(result.html, 'html.parser')
                    return self._extract_from_html(soup, result.html)
        
        except Exception as e:
            logger.debug(f"Iframe scraping failed: {e}")
        
        return []
    
    def _extract_from_html(self, soup: BeautifulSoup, raw_html: str) -> List[Dict]:
        """Extract data from HTML content"""
        models = []
        
        # Look for tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:
                    try:
                        model_name = cells[1].get_text(strip=True)
                        score_text = cells[2].get_text(strip=True)
                        score = float(re.search(r'(\d+\.?\d*)', score_text).group(1))
                        
                        if model_name and 1000 <= score <= 2000:
                            models.append({
                                'model': model_name,
                                'scores': {'arena_score': score},
                                'source': 'Chatbot Arena'
                            })
                    except (ValueError, AttributeError):
                        continue
        
        # Look for JSON data in script tags
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                json_matches = re.finditer(r'\[.*?\]', script.string, re.DOTALL)
                for match in json_matches:
                    try:
                        data = json.loads(match.group())
                        if isinstance(data, list) and len(data) > 0:
                            processed = self._process_api_data(data)
                            if processed:
                                models.extend(processed)
                    except json.JSONDecodeError:
                        continue
        
        return models
    
    def _process_api_data(self, data: List) -> List[Dict]:
        """Process data from API responses"""
        models = []
        
        for item in data:
            if isinstance(item, dict):
                # Try different field names
                model_name = item.get('model', item.get('name', item.get('model_name', '')))
                score = item.get('arena_score', item.get('score', item.get('rating', item.get('elo'))))
                
                if model_name and score is not None:
                    try:
                        score = float(score)
                        if 500 <= score <= 2000:  # Reasonable Arena score range
                            models.append({
                                'model': model_name,
                                'scores': {'arena_score': score},
                                'source': 'Chatbot Arena API'
                            })
                    except ValueError:
                        continue
        
        return models
    
    def _get_fallback_data(self) -> List[Dict]:
        """Return fallback data based on screenshot"""
        models = []
        
        for item in self.fallback_data:
            models.append({
                'model': item['model'],
                'scores': {'arena_score': item['arena_score']},
                'source': 'Chatbot Arena (Fallback)',
                'votes': item.get('votes'),
                'organization': item.get('organization')
            })
        
        logger.info(f"Using fallback data with {len(models)} models")
        return models
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Get all data from Arena"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            data = loop.run_until_complete(self.scrape_arena_data())
            return {"chatbot_arena": data}
        finally:
            loop.close() 