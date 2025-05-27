"""
Universal Scraping Framework
A strategic, scalable approach to scraping different website types
"""
import asyncio
import logging
import re
import json
import requests
from typing import List, Dict, Optional, Callable
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

logger = logging.getLogger(__name__)

class ScrapingStrategy:
    """Base class for different scraping strategies"""
    
    def __init__(self, name: str):
        self.name = name
    
    async def can_handle(self, url: str, initial_html: str = None) -> bool:
        """Check if this strategy can handle the given URL/content"""
        raise NotImplementedError
    
    async def scrape(self, url: str, **kwargs) -> List[Dict]:
        """Execute the scraping strategy"""
        raise NotImplementedError

class APIStrategy(ScrapingStrategy):
    """Strategy for API-based scraping"""
    
    def __init__(self):
        super().__init__("API")
        self.common_api_patterns = [
            "/api/",
            "/data/",
            "/leaderboard",
            "/models",
            "/rankings"
        ]
    
    async def can_handle(self, url: str, initial_html: str = None) -> bool:
        """Check for API endpoints"""
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        
        # Try common API patterns
        for pattern in self.common_api_patterns:
            test_url = urljoin(base_url, pattern)
            try:
                response = requests.head(test_url, timeout=5)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'json' in content_type:
                        return True
            except:
                continue
        return False
    
    async def scrape(self, url: str, **kwargs) -> List[Dict]:
        """Scrape via API endpoints"""
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        models = []
        
        for pattern in self.common_api_patterns:
            test_url = urljoin(base_url, pattern)
            try:
                response = requests.get(test_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        models.extend(self._process_api_data(data))
                        break
            except:
                continue
        
        return models
    
    def _process_api_data(self, data: List[Dict]) -> List[Dict]:
        """Process API response data"""
        models = []
        for item in data:
            if isinstance(item, dict):
                # Extract model info from various API formats
                model_name = item.get('model', item.get('name', item.get('model_name')))
                score = item.get('score', item.get('rating', item.get('elo', item.get('arena_score'))))
                
                if model_name and score is not None:
                    models.append({
                        'model': model_name,
                        'scores': {'api_score': float(score)},
                        'source': 'API',
                        'raw_data': item
                    })
        return models

class IframeStrategy(ScrapingStrategy):
    """Strategy for iframe-embedded content"""
    
    def __init__(self):
        super().__init__("Iframe")
    
    async def can_handle(self, url: str, initial_html: str = None) -> bool:
        """Check if content is in iframe"""
        if initial_html:
            soup = BeautifulSoup(initial_html, 'html.parser')
            iframes = soup.find_all('iframe')
            return len(iframes) > 0
        return False
    
    async def scrape(self, url: str, **kwargs) -> List[Dict]:
        """Scrape iframe content directly"""
        models = []
        
        # First get the wrapper page to find iframe URLs
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url, delay=5)
            if result.success:
                soup = BeautifulSoup(result.html, 'html.parser')
                iframes = soup.find_all('iframe')
                
                for iframe in iframes:
                    iframe_src = iframe.get('src')
                    if iframe_src:
                        # Make URL absolute
                        if iframe_src.startswith('//'):
                            iframe_src = f"{urlparse(url).scheme}:{iframe_src}"
                        elif iframe_src.startswith('/'):
                            iframe_src = urljoin(url, iframe_src)
                        
                        logger.info(f"Found iframe: {iframe_src}")
                        
                        # Scrape the iframe content
                        iframe_models = await self._scrape_iframe_content(iframe_src)
                        models.extend(iframe_models)
        
        return models
    
    async def _scrape_iframe_content(self, iframe_url: str) -> List[Dict]:
        """Scrape content from iframe URL"""
        models = []
        
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(
                url=iframe_url,
                wait_for="css:table, .dataframe, .leaderboard",
                delay=15,
                js_code="""
                // Wait for dynamic content
                await new Promise(resolve => setTimeout(resolve, 10000));
                
                // Scroll to load all content
                window.scrollTo(0, document.body.scrollHeight);
                await new Promise(resolve => setTimeout(resolve, 3000));
                """
            )
            
            if result.success:
                soup = BeautifulSoup(result.html, 'html.parser')
                models = self._extract_table_data(soup, 'iframe')
        
        return models
    
    def _extract_table_data(self, soup: BeautifulSoup, source: str) -> List[Dict]:
        """Extract data from HTML tables"""
        models = []
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:  # Need header + data
                continue
                
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    try:
                        model_name = cells[1].get_text(strip=True) if len(cells) > 1 else cells[0].get_text(strip=True)
                        
                        # Look for numeric scores
                        score = None
                        for cell in cells[2:]:
                            cell_text = cell.get_text(strip=True)
                            score_match = re.search(r'(\d+\.?\d*)', cell_text)
                            if score_match:
                                potential_score = float(score_match.group(1))
                                if 0 <= potential_score <= 2000:  # Reasonable range
                                    score = potential_score
                                    break
                        
                        if model_name and score is not None:
                            models.append({
                                'model': model_name,
                                'scores': {f'{source}_score': score},
                                'source': f'Table ({source})'
                            })
                    except (ValueError, AttributeError):
                        continue
        
        return models

class GradioStrategy(ScrapingStrategy):
    """Strategy for Gradio apps"""
    
    def __init__(self):
        super().__init__("Gradio")
    
    async def can_handle(self, url: str, initial_html: str = None) -> bool:
        """Check if this is a Gradio app"""
        if initial_html:
            return 'gradio' in initial_html.lower()
        return 'gradio' in url or '.hf.space' in url
    
    async def scrape(self, url: str, **kwargs) -> List[Dict]:
        """Scrape Gradio app with category support"""
        models = []
        categories = kwargs.get('categories', {'overall': 'Overall'})
        
        for category_key, category_name in categories.items():
            category_models = await self._scrape_gradio_category(url, category_key, category_name)
            models.extend(category_models)
        
        return models
    
    async def _scrape_gradio_category(self, url: str, category_key: str, category_name: str) -> List[Dict]:
        """Scrape specific category from Gradio app"""
        models = []
        
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(
                url=url,
                wait_for="css:table, .dataframe, select, .dropdown",
                delay=20,
                js_code=f"""
                console.log('Scraping Gradio category: {category_name}');
                
                // Wait for app to load
                await new Promise(resolve => setTimeout(resolve, 15000));
                
                // Try to select category
                let categorySelected = false;
                
                // Look for dropdowns/selects
                const selectors = ['select', '[role="combobox"]', '.dropdown', 'input[type="text"]'];
                
                for (let selector of selectors) {{
                    const elements = document.querySelectorAll(selector);
                    
                    for (let element of elements) {{
                        if (element.tagName === 'SELECT') {{
                            const options = element.querySelectorAll('option');
                            for (let option of options) {{
                                if (option.textContent.toLowerCase().includes('{category_name.lower()}')) {{
                                    element.value = option.value;
                                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    categorySelected = true;
                                    break;
                                }}
                            }}
                        }}
                        if (categorySelected) break;
                    }}
                    if (categorySelected) break;
                }}
                
                if (categorySelected) {{
                    await new Promise(resolve => setTimeout(resolve, 10000));
                }}
                
                // Scroll to ensure content is loaded
                window.scrollTo(0, document.body.scrollHeight);
                await new Promise(resolve => setTimeout(resolve, 3000));
                """
            )
            
            if result.success:
                soup = BeautifulSoup(result.html, 'html.parser')
                models = self._extract_gradio_data(soup, category_key)
        
        return models
    
    def _extract_gradio_data(self, soup: BeautifulSoup, category_key: str) -> List[Dict]:
        """Extract data from Gradio interface"""
        models = []
        
        # Look for tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    try:
                        model_name = cells[1].get_text(strip=True) if len(cells) > 1 else cells[0].get_text(strip=True)
                        
                        # Look for score
                        score = None
                        for cell in cells[2:]:
                            cell_text = cell.get_text(strip=True)
                            score_match = re.search(r'(\d{3,4}\.?\d*)', cell_text)
                            if score_match:
                                potential_score = float(score_match.group(1))
                                if 800 <= potential_score <= 1600:  # Arena score range
                                    score = potential_score
                                    break
                        
                        if model_name and score is not None:
                            models.append({
                                'model': model_name,
                                'scores': {f'{category_key}_score': score},
                                'source': f'Gradio ({category_key})',
                                'category': category_key
                            })
                    except (ValueError, AttributeError):
                        continue
        
        return models

class StaticHTMLStrategy(ScrapingStrategy):
    """Strategy for static HTML content"""
    
    def __init__(self):
        super().__init__("StaticHTML")
    
    async def can_handle(self, url: str, initial_html: str = None) -> bool:
        """Always can handle as fallback"""
        return True
    
    async def scrape(self, url: str, **kwargs) -> List[Dict]:
        """Scrape static HTML content"""
        models = []
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=url,
                wait_for="css:table, .leaderboard",
                delay=10
            )
            
            if result.success:
                soup = BeautifulSoup(result.html, 'html.parser')
                models = self._extract_static_data(soup)
        
        return models
    
    def _extract_static_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract data from static HTML"""
        models = []
        
        # Look for tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    try:
                        model_name = cells[1].get_text(strip=True) if len(cells) > 1 else cells[0].get_text(strip=True)
                        
                        # Look for numeric values
                        score = None
                        for cell in cells[2:]:
                            cell_text = cell.get_text(strip=True)
                            score_match = re.search(r'(\d+\.?\d*)', cell_text)
                            if score_match:
                                score = float(score_match.group(1))
                                break
                        
                        if model_name and score is not None:
                            models.append({
                                'model': model_name,
                                'scores': {'static_score': score},
                                'source': 'Static HTML'
                            })
                    except (ValueError, AttributeError):
                        continue
        
        return models

class UniversalScraper:
    """Universal scraper that tries multiple strategies"""
    
    def __init__(self):
        self.strategies = [
            APIStrategy(),
            IframeStrategy(),
            GradioStrategy(),
            StaticHTMLStrategy()  # Always last as fallback
        ]
    
    async def scrape(self, url: str, **kwargs) -> Dict[str, List[Dict]]:
        """Scrape using the best available strategy"""
        logger.info(f"Starting universal scraping for: {url}")
        
        # Get initial page to analyze
        initial_html = await self._get_initial_html(url)
        
        # Try strategies in order
        for strategy in self.strategies:
            try:
                if await strategy.can_handle(url, initial_html):
                    logger.info(f"Using strategy: {strategy.name}")
                    models = await strategy.scrape(url, **kwargs)
                    
                    if models:  # Only return if we got real data
                        logger.info(f"✅ {strategy.name} found {len(models)} models")
                        return {
                            'strategy_used': strategy.name,
                            'models': models,
                            'url': url
                        }
                    else:
                        logger.warning(f"❌ {strategy.name} found no data")
            except Exception as e:
                logger.error(f"Strategy {strategy.name} failed: {e}")
                continue
        
        logger.warning(f"No strategy succeeded for {url}")
        return {}
    
    async def _get_initial_html(self, url: str) -> str:
        """Get initial HTML for analysis"""
        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url, delay=3)
                return result.html if result.success else ""
        except:
            return "" 