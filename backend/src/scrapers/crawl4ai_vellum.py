"""
Real Vellum AI Leaderboard Scraper using crawl4ai
No more hardcoded data - scrapes actual JavaScript-heavy site
"""
import asyncio
import logging
import re
from typing import List, Dict
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class Crawl4aiVellumScraper:
    """Real scraper for Vellum AI LLM Leaderboard using crawl4ai"""
    
    def __init__(self):
        self.base_url = "https://www.vellum.ai/llm-leaderboard"
    
    async def scrape_vellum_data(self) -> List[Dict]:
        """Scrape model performance data from Vellum AI leaderboard"""
        try:
            logger.info("Scraping Vellum AI leaderboard with crawl4ai...")
            
            async with AsyncWebCrawler(verbose=True) as crawler:
                # Crawl the page and wait for JavaScript to load
                result = await crawler.arun(
                    url=self.base_url,
                    wait_for="css:.chart, .leaderboard, .model, .score",  # Wait for content to load
                    delay=3,  # Wait 3 seconds for JS to execute
                    js_code="""
                    // Scroll down to load all content
                    window.scrollTo(0, document.body.scrollHeight);
                    // Wait a bit more
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    """
                )
                
                if not result.success:
                    logger.error(f"Failed to crawl Vellum: {result.error_message}")
                    return []
                
                # Parse the HTML content
                soup = BeautifulSoup(result.html, 'html.parser')
                
                # Extract model data from the page
                models_data = []
                
                # Look for different patterns that might contain model data
                patterns_to_try = [
                    self._extract_from_charts(soup),
                    self._extract_from_tables(soup),
                    self._extract_from_divs(soup),
                    self._extract_from_text(result.html)
                ]
                
                for pattern_result in patterns_to_try:
                    if pattern_result:
                        models_data.extend(pattern_result)
                        break
                
                if not models_data:
                    logger.warning("No model data found, trying text extraction...")
                    models_data = self._extract_from_raw_text(result.html)
                
                logger.info(f"Vellum AI: {len(models_data)} models extracted")
                return models_data
                
        except Exception as e:
            logger.error(f"Vellum AI scraping failed: {e}")
            return []
    
    def _extract_from_charts(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract data from chart elements"""
        models = []
        
        # Look for chart containers
        charts = soup.find_all(['div', 'section'], class_=lambda x: x and any(
            term in x.lower() for term in ['chart', 'graph', 'leaderboard', 'ranking']
        ))
        
        for chart in charts:
            # Look for model names and scores
            model_elements = chart.find_all(text=re.compile(r'(gpt|claude|gemini|llama|grok|o3|o4)', re.I))
            score_elements = chart.find_all(text=re.compile(r'\d+\.?\d*'))
            
            for model_text in model_elements:
                model_name = model_text.strip()
                if len(model_name) > 3:  # Filter out short matches
                    # Try to find associated score
                    parent = model_text.parent
                    if parent:
                        score_text = parent.find(text=re.compile(r'\d+\.?\d*'))
                        if score_text:
                            try:
                                score = float(score_text.strip())
                                models.append({
                                    'model': model_name,
                                    'scores': {'extracted_score': score},
                                    'source': 'Vellum AI'
                                })
                            except ValueError:
                                pass
        
        return models
    
    def _extract_from_tables(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract data from table elements"""
        models = []
        
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # First cell might be model name, second might be score
                    model_text = cells[0].get_text(strip=True)
                    score_text = cells[1].get_text(strip=True)
                    
                    if any(term in model_text.lower() for term in ['gpt', 'claude', 'gemini', 'llama', 'grok']):
                        try:
                            score = float(re.search(r'\d+\.?\d*', score_text).group())
                            models.append({
                                'model': model_text,
                                'scores': {'table_score': score},
                                'source': 'Vellum AI'
                            })
                        except (ValueError, AttributeError):
                            pass
        
        return models
    
    def _extract_from_divs(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract data from div elements with model info"""
        models = []
        
        # Look for divs that might contain model data
        divs = soup.find_all('div', text=re.compile(r'(gpt|claude|gemini|llama|grok)', re.I))
        
        for div in divs:
            model_name = div.get_text(strip=True)
            
            # Look for nearby score elements
            siblings = div.find_next_siblings()
            parent = div.parent
            
            for element in [div] + siblings + ([parent] if parent else []):
                score_match = re.search(r'(\d+\.?\d+)', element.get_text() if element else '')
                if score_match:
                    try:
                        score = float(score_match.group(1))
                        models.append({
                            'model': model_name,
                            'scores': {'div_score': score},
                            'source': 'Vellum AI'
                        })
                        break
                    except ValueError:
                        pass
        
        return models
    
    def _extract_from_text(self, html: str) -> List[Dict]:
        """Extract data using regex patterns on raw HTML"""
        models = []
        
        # Pattern to match model names followed by scores
        patterns = [
            r'((?:GPT|Claude|Gemini|Llama|Grok|OpenAI|o3|o4)[\w\s\-\.]*?)\s*[:\s]*(\d+\.?\d*)',
            r'"([^"]*(?:gpt|claude|gemini|llama|grok)[^"]*)"[^}]*"score"[^:]*:\s*(\d+\.?\d*)',
            r'model["\s]*:["\s]*([^"]*(?:gpt|claude|gemini|llama|grok)[^"]*)[^}]*score["\s]*:["\s]*(\d+\.?\d*)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE)
            for match in matches:
                model_name = match.group(1).strip()
                try:
                    score = float(match.group(2))
                    models.append({
                        'model': model_name,
                        'scores': {'regex_score': score},
                        'source': 'Vellum AI'
                    })
                except ValueError:
                    pass
        
        return models
    
    def _extract_from_raw_text(self, html: str) -> List[Dict]:
        """Last resort: extract from visible text content"""
        models = []
        
        # Remove HTML tags and get plain text
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        # Look for model names and nearby numbers
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if any(term in line.lower() for term in ['gpt', 'claude', 'gemini', 'llama', 'grok', 'o3', 'o4']):
                model_name = line.strip()
                
                # Look for scores in nearby lines
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    score_match = re.search(r'(\d+\.?\d+)', lines[j])
                    if score_match:
                        try:
                            score = float(score_match.group(1))
                            # More restrictive score validation
                            if 10 <= score <= 100 and score != 2.5 and score != 3.7:  # Filter out version numbers
                                models.append({
                                    'model': model_name,
                                    'scores': {'text_score': score},
                                    'source': 'Vellum AI'
                                })
                                break
                        except ValueError:
                            pass
        
        return models
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Get all data from Vellum AI"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            data = loop.run_until_complete(self.scrape_vellum_data())
            return {"vellum": data}
        finally:
            loop.close() 