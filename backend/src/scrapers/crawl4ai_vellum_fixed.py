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
                    wait_for="css:.chart, .leaderboard, .model, .score",
                    delay=3,
                    js_code="""
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    """
                )
                
                if not result.success:
                    logger.error(f"Failed to crawl Vellum: {result.error_message}")
                    return []
                
                # Parse the HTML content
                soup = BeautifulSoup(result.html, 'html.parser')
                
                # Extract model data from the page
                models_data = self._extract_from_raw_text(result.html)
                
                # Deduplicate models
                unique_models = {}
                for model in models_data:
                    key = model['model'].lower()
                    if key not in unique_models or model['scores'].get('text_score', 0) > unique_models[key]['scores'].get('text_score', 0):
                        unique_models[key] = model
                
                result_list = list(unique_models.values())
                logger.info(f"Vellum AI: {len(result_list)} unique models extracted")
                return result_list
                
        except Exception as e:
            logger.error(f"Vellum AI scraping failed: {e}")
            return []
    
    def _extract_from_raw_text(self, html: str) -> List[Dict]:
        """Extract from visible text content with better filtering"""
        models = []
        
        # Remove HTML tags and get plain text
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        # Look for model names and nearby numbers
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            # More specific model name patterns
            model_patterns = [
                r'(GPT-4[.\w]*)',
                r'(Claude [34][\w\s\[\]]*)',
                r'(Gemini [\d.]+[\w\s]*)',
                r'(Llama [\d.]+[\w\s]*)',
                r'(Grok [\d]+[\w\s\[\]]*)',
                r'(OpenAI o[34][\w-]*)',
                r'(DeepSeek[\w\s-]*)',
                r'(Nova [\w]+)',
                r'(Nemotron[\w\s]*)',
                r'(Qwen[\d.-]*[\w]*)'
            ]
            
            model_name = None
            for pattern in model_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    model_name = match.group(1).strip()
                    break
            
            if model_name and len(model_name) < 100:  # Reasonable length limit
                
                # Look for scores in nearby lines
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    score_match = re.search(r'(\d+\.?\d+)', lines[j])
                    if score_match:
                        try:
                            score = float(score_match.group(1))
                            # Better score validation - realistic benchmark scores
                            if 15 <= score <= 100 and score not in [2.5, 3.7, 4.0, 1.5]:
                                models.append({
                                    'model': model_name,
                                    'scores': {'benchmark_score': score},
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