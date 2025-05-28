"""
Strawberry Bench Scraper
Uses Playwright to scrape reasoning benchmark data from Strawberry Bench
Based on successful Arena scraper patterns but adapted for simpler table structure
"""
import asyncio
import logging
import re
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Page, Browser
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class StrawberryBenchScraper:
    """Scraper for Strawberry Bench reasoning benchmark"""
    
    def __init__(self):
        self.target_url = "https://multinear.github.io/strawberry-bench/#strawberry"
        self.browser: Optional[Browser] = None
        self.debug_mode = True  # Enable for screenshots and detailed logging
    
    async def initialize_browser(self):
        """Initialize Playwright browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,  # Set to False for debugging
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        logger.info("Browser initialized for Strawberry Bench scraping")
    
    async def close_browser(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
            logger.info("Browser closed")
    
    async def scrape_benchmark_data(self) -> List[Dict]:
        """Scrape all model data from Strawberry Bench"""
        logger.info("Starting Strawberry Bench scraping...")
        models = []
        
        try:
            await self.initialize_browser()
            
            # Create a new page
            page = await self.browser.new_page()
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Navigate to Strawberry Bench
            logger.info(f"Navigating to: {self.target_url}")
            await page.goto(self.target_url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for content to load (much simpler than Arena)
            logger.info("Waiting for page to load...")
            await page.wait_for_timeout(5000)
            
            # Wait for table to be present
            try:
                await page.wait_for_selector('table', timeout=10000)
                logger.info("Table found successfully")
            except:
                logger.warning("No table element found, continuing anyway...")
            
            # Take screenshot for debugging
            if self.debug_mode:
                screenshot_path = f"strawberry_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Extract data from the table
            models = await self._extract_table_data(page)
            
            if models:
                logger.info(f"✅ Successfully extracted {len(models)} models from Strawberry Bench")
                # Log first few models as verification
                for i, model in enumerate(models[:3]):
                    logger.info(f"  Model {i+1}: {model['model']} - Pass Rate: {model['metrics'].get('pass_rate', 'N/A')}")
            else:
                logger.warning("❌ No models found in Strawberry Bench")
            
            await page.close()
            
        except Exception as e:
            logger.error(f"Error during Strawberry Bench scraping: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close_browser()
        
        return models
    
    async def _extract_table_data(self, page: Page) -> List[Dict]:
        """Extract data from the Strawberry Bench table"""
        models = []
        
        try:
            # Execute JavaScript to extract structured data
            data = await page.evaluate("""
                () => {
                    const models = [];
                    
                    // Find the main table
                    const table = document.querySelector('table');
                    if (!table) {
                        return [];
                    }
                    
                    const rows = table.querySelectorAll('tr');
                    if (rows.length < 2) {
                        return [];  // No data rows
                    }
                    
                    // Get headers
                    const headerRow = rows[0];
                    const headers = Array.from(headerRow.querySelectorAll('th, td')).map(cell => cell.textContent.trim());
                    
                    // Expected headers: Model, Results, Pass Rate, Tokens, Cost, Response Time
                    console.log('Headers found:', headers);
                    
                    // Process data rows
                    for (let i = 1; i < rows.length; i++) {
                        const cells = rows[i].querySelectorAll('td, th');
                        if (cells.length >= 6) {  // All 6 columns expected
                            const rowData = Array.from(cells).map(cell => cell.textContent.trim());
                            
                            if (rowData[0] && rowData[0] !== '') {  // Has model name
                                models.push({
                                    model: rowData[0],
                                    results: rowData[1],
                                    passRate: rowData[2],
                                    tokens: rowData[3],
                                    cost: rowData[4],
                                    responseTime: rowData[5]
                                });
                            }
                        }
                    }
                    
                    return models;
                }
            """)
            
            # Process and clean the extracted data
            for item in data:
                try:
                    # Clean model name (remove ▶ symbol and extra whitespace)
                    model_name = item['model'].replace('▶', '').strip()
                    
                    # Parse pass rate (e.g., "10/10" -> 100%, "8/10" -> 80%)
                    pass_rate = self._parse_pass_rate(item['passRate'])
                    
                    # Parse tokens (e.g., "195 ±53%" -> 195)
                    tokens = self._parse_numeric_value(item['tokens'])
                    
                    # Parse cost (e.g., "$0.01109" -> 0.01109)
                    cost = self._parse_cost(item['cost'])
                    
                    # Parse response time (e.g., "58s ±92%" -> 58)
                    response_time = self._parse_response_time(item['responseTime'])
                    
                    # Validate this is real data
                    if model_name and self._is_valid_model_name(model_name):
                        models.append({
                            'model': model_name,
                            'metrics': {
                                'results': item['results'],
                                'pass_rate': pass_rate,
                                'tokens': tokens,
                                'cost': cost,
                                'response_time_seconds': response_time
                            },
                            'source': 'Strawberry Bench',
                            'benchmark_type': 'reasoning',
                            'scraped_at': datetime.now().isoformat()
                        })
                        
                except Exception as e:
                    logger.debug(f"Error processing model data: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error extracting table data: {e}")
            import traceback
            traceback.print_exc()
        
        return models
    
    def _parse_pass_rate(self, pass_rate_str: str) -> Optional[float]:
        """Parse pass rate string like '10/10' to percentage"""
        try:
            # Extract pattern like "10/10"
            match = re.search(r'(\d+)/(\d+)', pass_rate_str)
            if match:
                passed = int(match.group(1))
                total = int(match.group(2))
                return (passed / total) * 100.0
        except:
            pass
        return None
    
    def _parse_numeric_value(self, value_str: str) -> Optional[int]:
        """Parse numeric value with potential ± symbol (e.g., '195 ±53%')"""
        try:
            # Extract the main number before any ± symbol
            match = re.search(r'(\d+)', value_str)
            if match:
                return int(match.group(1))
        except:
            pass
        return None
    
    def _parse_cost(self, cost_str: str) -> Optional[float]:
        """Parse cost string like '$0.01109' to float"""
        try:
            # Remove $ symbol and convert to float
            match = re.search(r'\$?(\d+\.?\d*)', cost_str)
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def _parse_response_time(self, time_str: str) -> Optional[float]:
        """Parse response time like '58s ±92%' to seconds"""
        try:
            # Extract number before 's'
            match = re.search(r'(\d+\.?\d*)s', time_str)
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def _is_valid_model_name(self, model_name: str) -> bool:
        """Validate that this is a real model name and not placeholder data"""
        if not model_name or len(model_name.strip()) < 3:
            return False
        
        # Check for common AI model providers/names
        model_indicators = [
            'openai', 'gpt', 'claude', 'anthropic', 'google', 'gemini', 
            'meta', 'llama', 'mistral', 'cohere', 'ai21', 'o1', 'o3'
        ]
        
        model_lower = model_name.lower()
        return any(indicator in model_lower for indicator in model_indicators)
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Main entry point for scraping (sync wrapper)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            data = loop.run_until_complete(self.scrape_benchmark_data())
            
            if data:
                logger.info(f"✅ Successfully scraped {len(data)} models from Strawberry Bench")
                return {"strawberry_bench": data}
            else:
                logger.warning("❌ No data scraped from Strawberry Bench")
                return {}
        finally:
            loop.close()

# Test function for direct usage
async def test_scraper():
    """Test the scraper directly"""
    scraper = StrawberryBenchScraper()
    data = await scraper.scrape_benchmark_data()
    
    if data:
        print(f"✅ Found {len(data)} models")
        for model in data[:5]:  # Show first 5
            print(f"  {model['model']}: {model['metrics']['pass_rate']}% pass rate")
    else:
        print("❌ No data found")

if __name__ == "__main__":
    asyncio.run(test_scraper()) 