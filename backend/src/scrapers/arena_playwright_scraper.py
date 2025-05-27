"""
Arena Playwright Scraper
Uses Playwright for full browser automation to scrape Chatbot Arena
"""
import asyncio
import logging
import re
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Page, Browser
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ArenaPlaywrightScraper:
    """Scraper for Chatbot Arena using Playwright browser automation"""
    
    def __init__(self):
        # Direct URL to the Gradio app (iframe content)
        self.direct_url = "https://lmarena-ai-chatbot-arena-leaderboard.hf.space"
        
        # Categories to scrape
        self.categories = {
            "overall": "Overall",
            "coding": "Coding", 
            "hard_prompts": "Hard Prompts",
            "math": "Math",
            "instruction_following": "Instruction Following",
            "creative_writing": "Creative Writing",
            "multi_turn": "Multi-Turn",
            "english": "English",
            "chinese": "Chinese"
        }
        
        self.browser: Optional[Browser] = None
        self.debug_mode = True  # Enable for screenshots and detailed logging
    
    async def initialize_browser(self):
        """Initialize Playwright browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,  # Set to False for debugging
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        logger.info("Browser initialized")
    
    async def close_browser(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
            logger.info("Browser closed")
    
    async def scrape_category(self, page: Page, category_key: str, category_name: str) -> List[Dict]:
        """Scrape a specific category"""
        logger.info(f"Scraping category: {category_name}")
        models = []
        
        try:
            # Take initial screenshot for debugging
            if self.debug_mode:
                screenshot_path = f"arena_debug_{category_key}_before_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"Before screenshot saved: {screenshot_path}")
            
            # Step 1: Find and click the dropdown INPUT element
            logger.info("Looking for dropdown INPUT element...")
            
            # The dropdown is an INPUT element with value "Overall" or current category
            dropdown_clicked = False
            
            # Method 1: Find INPUT element with value "Overall"
            try:
                dropdown_input = page.locator('input[value="Overall"]').first
                if await dropdown_input.count() > 0:
                    await dropdown_input.click()
                    dropdown_clicked = True
                    logger.info("Clicked dropdown INPUT with value='Overall'")
            except:
                pass
            
            if not dropdown_clicked:
                # Method 2: Find any INPUT that might be the dropdown
                try:
                    # Look for input elements that might contain category text
                    inputs = await page.query_selector_all('input[type="text"], input:not([type])')
                    for inp in inputs:
                        value = await inp.get_attribute('value')
                        if value and ('Overall' in value or 'Category' in value or category_name in value):
                            await inp.click()
                            dropdown_clicked = True
                            logger.info(f"Clicked dropdown INPUT with value='{value}'")
                            break
                except:
                    pass
            
            if not dropdown_clicked:
                # Method 3: Use the class we found
                try:
                    dropdown_by_class = page.locator('input.border-none').first
                    if await dropdown_by_class.count() > 0:
                        await dropdown_by_class.click()
                        dropdown_clicked = True
                        logger.info("Clicked dropdown using class selector")
                except:
                    pass
            
            if not dropdown_clicked:
                logger.error("Could not find/click dropdown INPUT element")
                return models
            
            # Wait for dropdown menu to appear
            await page.wait_for_timeout(2000)
            
            # Take screenshot after clicking dropdown
            if self.debug_mode:
                screenshot_path = f"arena_debug_{category_key}_dropdown_open_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"Dropdown open screenshot saved: {screenshot_path}")
            
            # Step 2: Click on the desired category from the dropdown menu
            logger.info(f"Selecting category: {category_name}")
            
            # The dropdown options might appear as list items or divs
            try:
                # Try different selectors for the dropdown options
                option_selectors = [
                    f'li:has-text("{category_name}")',
                    f'div[role="option"]:has-text("{category_name}")',
                    f'span:has-text("{category_name}")',
                    f'text="{category_name}"'
                ]
                
                option_clicked = False
                for selector in option_selectors:
                    try:
                        option = page.locator(selector).first
                        if await option.count() > 0 and await option.is_visible():
                            await option.click()
                            option_clicked = True
                            logger.info(f"Clicked category option using selector: {selector}")
                            break
                    except:
                        continue
                
                if not option_clicked:
                    logger.error(f"Could not find/click option for: {category_name}")
                    return models
                    
            except Exception as e:
                logger.error(f"Error selecting category: {e}")
                return models
            
            # Step 3: Wait for data to reload
            logger.info("Waiting for data to load...")
            await page.wait_for_timeout(5000)
            
            # Take screenshot after selection
            if self.debug_mode:
                screenshot_path = f"arena_debug_{category_key}_after_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"After screenshot saved: {screenshot_path}")
            
            # Step 4: Extract table data
            logger.info("Extracting table data...")
            models = await self._extract_table_data(page, category_key)
            
            if models:
                logger.info(f"✅ Extracted {len(models)} models from {category_name}")
                # Log first few models as verification
                for i, model in enumerate(models[:3]):
                    logger.info(f"  Model {i+1}: {model['model']} - Score: {model['scores'].get(f'{category_key}_score', 'N/A')}")
            else:
                logger.warning(f"❌ No models found for {category_name}")
                
                # Try alternative extraction
                models = await self._extract_data_alternative(page, category_key)
                if models:
                    logger.info(f"✅ Alternative extraction found {len(models)} models")
            
        except Exception as e:
            logger.error(f"Error scraping {category_name}: {e}")
            import traceback
            traceback.print_exc()
        
        return models
    
    async def _is_category_dropdown(self, page: Page, element) -> bool:
        """Check if element is the category dropdown"""
        try:
            # Check for options that match our categories
            if await element.evaluate('el => el.tagName') == 'SELECT':
                options = await element.query_selector_all('option')
                option_texts = []
                for option in options:
                    text = await option.text_content()
                    if text:
                        option_texts.append(text.strip().lower())
                
                # Check if options contain our category names
                category_names = [name.lower() for name in self.categories.values()]
                matches = sum(1 for cat in category_names if any(cat in opt for opt in option_texts))
                
                return matches >= 3  # At least 3 category matches
            
            return False
        except:
            return False
    
    async def _extract_table_data(self, page: Page, category_key: str) -> List[Dict]:
        """Extract data from tables on the page"""
        models = []
        
        # Wait for tables to be present - prioritize regular table elements
        table_selectors = ['table', 'div[class*="table"]', '.dataframe', '.gradio-dataframe']
        
        for selector in table_selectors:
            try:
                # Don't wait too long for each selector
                try:
                    await page.wait_for_selector(selector, timeout=2000)
                except:
                    pass
                    
                tables = await page.query_selector_all(selector)
                logger.info(f"Found {len(tables)} elements with selector: {selector}")
                
                for table in tables:
                    # Get all rows
                    rows = await table.query_selector_all('tr')
                    
                    if len(rows) < 2:  # Need header + data
                        continue
                    
                    logger.info(f"Processing table with {len(rows)} rows")
                    
                    # Process data rows
                    for i, row in enumerate(rows[1:], 1):  # Skip header
                        cells = await row.query_selector_all('td, th')
                        
                        if len(cells) >= 4:  # Need at least rank, delta, model, score
                            try:
                                # Extract rank (usually 1st column)
                                rank_text = await cells[0].text_content()
                                if rank_text:
                                    rank_text = rank_text.strip()
                                    # Skip if it's a header row
                                    if 'Rank' in rank_text:
                                        continue
                                
                                # Extract model name (usually 3rd column after rank and delta)
                                model_name = await cells[2].text_content()
                                if model_name:
                                    model_name = model_name.strip()
                                
                                # Extract score (usually 4th column)
                                score = None
                                score_text = await cells[3].text_content()
                                if score_text:
                                    # Look for Arena score pattern
                                    score_match = re.search(r'(\d{3,4}\.?\d*)', score_text.strip())
                                    if score_match:
                                        potential_score = float(score_match.group(1))
                                        if 800 <= potential_score <= 1600:  # Arena score range
                                            score = potential_score
                                
                                # Validate this is real data
                                if model_name and score and self._is_valid_model_name(model_name):
                                    models.append({
                                        'rank': rank_text,
                                        'model': model_name,
                                        'scores': {f'{category_key}_score': score},
                                        'source': f'Arena Playwright ({category_key})',
                                        'category': category_key,
                                        'scraped_at': datetime.now().isoformat()
                                    })
                                    
                            except Exception as e:
                                logger.debug(f"Error processing row: {e}")
                                continue
                
                if models:
                    logger.info(f"✅ Extracted {len(models)} models from {selector}")
                    break  # Found data, no need to try other selectors
                    
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        return models
    
    async def _extract_data_alternative(self, page: Page, category_key: str) -> List[Dict]:
        """Alternative data extraction method using page evaluation"""
        try:
            # Execute JavaScript to extract data directly
            data = await page.evaluate("""
                () => {
                    const models = [];
                    
                    // Find all table rows
                    const rows = document.querySelectorAll('tr');
                    
                    for (let i = 1; i < rows.length; i++) {  // Skip header
                        const cells = rows[i].querySelectorAll('td, th');
                        if (cells.length >= 2) {
                            const modelName = cells[1]?.textContent?.trim() || cells[0]?.textContent?.trim();
                            
                            // Look for score
                            let score = null;
                            for (let j = 2; j < Math.min(cells.length, 6); j++) {
                                const cellText = cells[j]?.textContent?.trim() || '';
                                const scoreMatch = cellText.match(/(\d{3,4}\.?\d*)/);
                                if (scoreMatch) {
                                    const potentialScore = parseFloat(scoreMatch[1]);
                                    if (potentialScore >= 800 && potentialScore <= 1600) {
                                        score = potentialScore;
                                        break;
                                    }
                                }
                            }
                            
                            if (modelName && score) {
                                models.push({
                                    model: modelName,
                                    score: score,
                                    rank: i
                                });
                            }
                        }
                    }
                    
                    return models;
                }
            """)
            
            # Convert to our format
            models = []
            for item in data:
                if self._is_valid_model_name(item['model']):
                    models.append({
                        'rank': item['rank'],
                        'model': item['model'],
                        'scores': {f'{category_key}_score': item['score']},
                        'source': f'Arena Playwright Alt ({category_key})',
                        'category': category_key,
                        'scraped_at': datetime.now().isoformat()
                    })
            
            return models
            
        except Exception as e:
            logger.error(f"Alternative extraction failed: {e}")
            return []
    
    def _is_valid_model_name(self, name: str) -> bool:
        """Validate that this is a real model name, not placeholder data"""
        if not name or len(name) < 3:
            return False
        
        # Check for known placeholder patterns
        placeholder_patterns = [
            r'^model[-_]?\d+$',  # model1, model_1, etc
            r'^test',
            r'^example',
            r'^placeholder',
            r'^gpt-3\.5-turbo$'  # This was in our fallback data
        ]
        
        name_lower = name.lower()
        for pattern in placeholder_patterns:
            if re.match(pattern, name_lower):
                return False
        
        # Check for realistic model names (should contain letters and possibly numbers)
        if not re.search(r'[a-zA-Z]{2,}', name):
            return False
        
        return True
    
    async def scrape_all_categories(self) -> Dict[str, List[Dict]]:
        """Scrape all categories"""
        all_data = {}
        
        try:
            await self.initialize_browser()
            
            # Create a new page
            page = await self.browser.new_page()
            
            # Set viewport size
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Navigate to the Arena
            logger.info(f"Navigating to: {self.direct_url}")
            await page.goto(self.direct_url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for initial load with multiple strategies
            logger.info("Waiting for Gradio app to initialize...")
            
            # Wait for the page to fully load
            await page.wait_for_timeout(10000)
            
            # Look for signs that the page has loaded
            try:
                # Wait for table or dataframe to be present
                await page.wait_for_selector('table, .dataframe, [role="grid"]', timeout=10000)
                logger.info("Found table/dataframe element")
            except:
                logger.warning("No table element found, continuing anyway...")
            
            # Take a full page screenshot to see what loaded
            if self.debug_mode:
                screenshot_path = f"arena_debug_initial_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"Initial page screenshot saved: {screenshot_path}")
            
            # TEST WITH JUST ONE CATEGORY FIRST (Math)
            test_categories = {
                "math": "Math"  # Start with just Math as specified in the plan
            }
            
            logger.info("Testing with Math category first...")
            
            # Try to scrape the test category
            for category_key, category_name in test_categories.items():
                models = await self.scrape_category(page, category_key, category_name)
                if models:
                    all_data[category_key] = models
                    logger.info(f"✅ SUCCESS! Extracted {len(models)} models from {category_name}")
                    
                    # If Math works, try all categories
                    logger.info("Math category successful, now trying all categories...")
                    
                    # Reset to Overall first
                    await self.scrape_category(page, "overall", "Overall")
                    
                    # Now try all categories
                    for cat_key, cat_name in self.categories.items():
                        if cat_key not in all_data:  # Skip if already done
                            models = await self.scrape_category(page, cat_key, cat_name)
                            if models:
                                all_data[cat_key] = models
                            
                            # Small delay between categories
                            await page.wait_for_timeout(2000)
                else:
                    logger.error("❌ Failed to extract data from Math category - stopping here")
            
            await page.close()
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close_browser()
        
        return all_data
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Main entry point for scraping (sync wrapper)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            data = loop.run_until_complete(self.scrape_all_categories())
            
            if data:
                logger.info(f"✅ Successfully scraped {len(data)} categories")
                return {"chatbot_arena_playwright": data}
            else:
                logger.warning("❌ No data scraped")
                return {}
        finally:
            loop.close() 