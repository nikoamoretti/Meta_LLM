"""
Improved Vellum AI Leaderboard Scraper
Extracts structured benchmark data from the actual HTML
"""
import asyncio
import logging
import re
from typing import List, Dict
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class VellumImprovedScraper:
    """Improved scraper for Vellum AI LLM Leaderboard"""
    
    def __init__(self):
        self.base_url = "https://www.vellum.ai/llm-leaderboard"
    
    async def scrape_vellum_data(self) -> List[Dict]:
        """Scrape model performance data from Vellum AI leaderboard"""
        try:
            logger.info("Scraping Vellum AI leaderboard with improved parser...")
            
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(
                    url=self.base_url,
                    wait_for="css:.graph_collection-item",
                    delay=5,
                    js_code="""
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(resolve => setTimeout(resolve, 3000));
                    """
                )
                
                if not result.success:
                    logger.error(f"Failed to crawl Vellum: {result.error_message}")
                    return []
                
                # Parse the HTML content
                soup = BeautifulSoup(result.html, 'html.parser')
                
                # Extract model data using the actual HTML structure
                models_data = self._extract_structured_data(soup)
                
                logger.info(f"Vellum AI: {len(models_data)} models extracted")
                return models_data
                
        except Exception as e:
            logger.error(f"Vellum AI scraping failed: {e}")
            return []
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract data from the structured HTML"""
        models = {}
        
        # Find all graph collection items
        graph_items = soup.find_all('div', class_='graph_collection-item')
        
        for item in graph_items:
            try:
                # Extract model name
                model_text_elem = item.find('div', class_='graph_block-text')
                if not model_text_elem:
                    continue
                
                model_name = model_text_elem.get_text(strip=True)
                if not model_name or len(model_name) < 3:
                    continue
                
                # Extract score from tooltip
                tooltip = item.find('div', class_='tooltip')
                if tooltip:
                    height_elem = tooltip.find('div', class_='height_percentage')
                    if height_elem:
                        score_text = height_elem.get_text(strip=True)
                        try:
                            score = float(score_text)
                            
                            # Find the benchmark category by looking at parent elements
                            benchmark_name = self._find_benchmark_name(item)
                            
                            # Initialize model if not exists
                            if model_name not in models:
                                models[model_name] = {
                                    'model': model_name,
                                    'scores': {},
                                    'source': 'Vellum AI'
                                }
                            
                            # Add score with benchmark name
                            if benchmark_name:
                                models[model_name]['scores'][benchmark_name] = score
                            else:
                                models[model_name]['scores']['general'] = score
                                
                        except ValueError:
                            continue
            
            except Exception as e:
                logger.debug(f"Error processing graph item: {e}")
                continue
        
        return list(models.values())
    
    def _find_benchmark_name(self, item) -> str:
        """Find the benchmark name by traversing up the DOM"""
        current = item
        
        # Look for benchmark headers in parent elements
        for _ in range(10):  # Limit traversal depth
            if current is None:
                break
                
            # Look for model_header class
            header = current.find('div', class_='model_header')
            if header:
                header_text = header.get_text(strip=True)
                # Clean up the header text
                if 'Best in' in header_text:
                    return self._normalize_benchmark_name(header_text)
                elif 'Best Overall' in header_text:
                    return 'overall'
                elif 'Fastest' in header_text:
                    return 'speed'
                elif 'Cheapest' in header_text:
                    return 'cost'
                elif 'Latency' in header_text:
                    return 'latency'
            
            current = current.parent
        
        return 'general'
    
    def _normalize_benchmark_name(self, header_text: str) -> str:
        """Normalize benchmark names"""
        header_lower = header_text.lower()
        
        if 'agentic coding' in header_lower or 'swe' in header_lower:
            return 'swe_bench'
        elif 'tool use' in header_lower or 'bfcl' in header_lower:
            return 'tool_use'
        elif 'adaptive reasoning' in header_lower or 'grind' in header_lower:
            return 'adaptive_reasoning'
        elif 'high school math' in header_lower or 'aime' in header_lower:
            return 'math'
        elif 'reasoning' in header_lower or 'gpqa' in header_lower:
            return 'reasoning'
        elif 'overall' in header_lower or 'humanity' in header_lower:
            return 'overall'
        else:
            # Extract key words
            words = re.findall(r'\b\w+\b', header_lower)
            key_words = [w for w in words if w not in ['best', 'in', 'the', 'and', 'or', 'of']]
            return '_'.join(key_words[:2]) if key_words else 'general'
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Get all data from Vellum AI"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            data = loop.run_until_complete(self.scrape_vellum_data())
            return {"vellum": data}
        finally:
            loop.close() 