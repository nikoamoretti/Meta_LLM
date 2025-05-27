"""
Real Chatbot Arena Scraper - NO FALLBACK DATA
Only returns actual scraped data from the live leaderboard
"""
import asyncio
import logging
import re
import json
from typing import List, Dict
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ArenaRealScraper:
    """Real scraper for Chatbot Arena - NO FALLBACK DATA"""
    
    def __init__(self):
        self.base_url = "https://huggingface.co/spaces/lmarena-ai/chatbot-arena-leaderboard"
        
        # Categories from the dropdown - we'll try to scrape each one
        self.categories = {
            "overall": "Overall",
            "math": "Math", 
            "instruction_following": "Instruction Following",
            "multi_turn": "Multi-Turn",
            "creative_writing": "Creative Writing", 
            "coding": "Coding",
            "hard_prompts": "Hard Prompts",
            "hard_prompts_english": "Hard Prompts (English)",
            "longer_query": "Longer Query",
            "english": "English",
            "chinese": "Chinese", 
            "french": "French",
            "german": "German",
            "spanish": "Spanish",
            "russian": "Russian",
            "japanese": "Japanese",
            "korean": "Korean"
        }
    
    async def scrape_all_categories(self) -> Dict[str, List[Dict]]:
        """Scrape REAL data from all Arena categories - NO FALLBACK"""
        try:
            logger.info("Scraping REAL Chatbot Arena data - NO FALLBACK")
            
            all_data = {}
            
            # Try to scrape each category
            for category_key, category_name in self.categories.items():
                logger.info(f"Attempting to scrape REAL data for: {category_name}")
                
                # Try web scraping for this category
                real_data = await self._scrape_category_real(category_key, category_name)
                
                if real_data:
                    logger.info(f"✅ Got {len(real_data)} REAL models for {category_name}")
                    all_data[category_key] = real_data
                else:
                    logger.warning(f"❌ No REAL data found for {category_name}")
                    # NO FALLBACK - just skip this category
            
            logger.info(f"Total categories with REAL data: {len(all_data)}")
            return all_data
                
        except Exception as e:
            logger.error(f"Real scraping failed: {e}")
            return {}  # Return empty dict, NO FALLBACK
    
    async def _scrape_category_real(self, category_key: str, category_name: str) -> List[Dict]:
        """Scrape REAL data for a specific category"""
        try:
            async with AsyncWebCrawler(verbose=True) as crawler:
                # First, load the main page
                result = await crawler.arun(
                    url=self.base_url,
                    wait_for="css:table, .dataframe, .gradio-container, select",
                    delay=15,  # Give it time to load
                    js_code=f"""
                    console.log('Starting to scrape category: {category_name}');
                    
                    // Wait for page to fully load
                    await new Promise(resolve => setTimeout(resolve, 10000));
                    
                    // Look for category selector
                    let categorySelected = false;
                    
                    // Try different selectors for the dropdown
                    const selectors = [
                        'select',
                        '.dropdown select',
                        '[role="combobox"]',
                        'input[type="text"]',
                        '.gradio-dropdown'
                    ];
                    
                    for (let selector of selectors) {{
                        const elements = document.querySelectorAll(selector);
                        console.log(`Found ${{elements.length}} elements for selector: ${{selector}}`);
                        
                        for (let element of elements) {{
                            console.log('Element:', element.tagName, element.className, element.id);
                            
                            if (element.tagName === 'SELECT') {{
                                // Handle select dropdown
                                const options = element.querySelectorAll('option');
                                console.log(`Found ${{options.length}} options`);
                                
                                for (let option of options) {{
                                    console.log('Option:', option.textContent, option.value);
                                    if (option.textContent.toLowerCase().includes('{category_name.lower()}') ||
                                        option.value.toLowerCase().includes('{category_key}')) {{
                                        console.log('Selecting option:', option.textContent);
                                        element.value = option.value;
                                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        categorySelected = true;
                                        break;
                                    }}
                                }}
                            }} else if (element.type === 'text' || element.role === 'combobox') {{
                                // Handle text input dropdown
                                element.click();
                                await new Promise(resolve => setTimeout(resolve, 1000));
                                
                                // Look for dropdown options
                                const dropdownOptions = document.querySelectorAll('[role="option"], .dropdown-option, .option');
                                for (let option of dropdownOptions) {{
                                    if (option.textContent.toLowerCase().includes('{category_name.lower()}')) {{
                                        console.log('Clicking dropdown option:', option.textContent);
                                        option.click();
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
                        console.log('Category selected, waiting for table update...');
                        await new Promise(resolve => setTimeout(resolve, 8000));
                    }} else {{
                        console.log('Could not select category, using default view');
                    }}
                    
                    // Scroll to ensure table is visible
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    console.log('Scraping complete for {category_name}');
                    """
                )
                
                if result.success:
                    # Save debug HTML
                    with open(f'arena_debug_{category_key}.html', 'w', encoding='utf-8') as f:
                        f.write(result.html)
                    
                    soup = BeautifulSoup(result.html, 'html.parser')
                    return self._extract_real_data(soup, category_key)
                else:
                    logger.error(f"Failed to load page for {category_name}")
                    return []
        
        except Exception as e:
            logger.error(f"Real scraping failed for {category_name}: {e}")
            return []
    
    def _extract_real_data(self, soup: BeautifulSoup, category_key: str) -> List[Dict]:
        """Extract REAL data from HTML - NO FALLBACK"""
        models = []
        
        logger.info(f"Extracting real data for {category_key}")
        
        # Look for tables with leaderboard data
        tables = soup.find_all('table')
        logger.info(f"Found {len(tables)} tables")
        
        for i, table in enumerate(tables):
            logger.info(f"Processing table {i+1}")
            
            rows = table.find_all('tr')
            logger.info(f"Found {len(rows)} rows in table {i+1}")
            
            # Skip header row
            for j, row in enumerate(rows[1:], 1):
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 2:
                    try:
                        # Extract model name and score
                        model_cell = cells[1] if len(cells) > 1 else cells[0]
                        model_name = model_cell.get_text(strip=True)
                        
                        # Look for score in various cells
                        score = None
                        for cell in cells[2:]:
                            cell_text = cell.get_text(strip=True)
                            # Look for numbers that could be scores
                            score_match = re.search(r'(\d{3,4}\.?\d*)', cell_text)
                            if score_match:
                                potential_score = float(score_match.group(1))
                                # Arena scores are typically 800-1600
                                if 800 <= potential_score <= 1600:
                                    score = potential_score
                                    break
                        
                        if model_name and score is not None:
                            # This looks like real data
                            model_data = {
                                'model': model_name,
                                'scores': {f'{category_key}_score': score},
                                'source': f'Chatbot Arena REAL ({category_key})',
                                'category': category_key
                            }
                            
                            # Try to extract additional info
                            if len(cells) > 3:
                                # Look for votes/organization
                                for cell in cells[3:]:
                                    cell_text = cell.get_text(strip=True)
                                    votes_match = re.search(r'(\d+)', cell_text)
                                    if votes_match and int(votes_match.group(1)) > 100:
                                        model_data['votes'] = int(votes_match.group(1))
                                        break
                            
                            models.append(model_data)
                            logger.info(f"Extracted: {model_name} = {score}")
                            
                    except (ValueError, AttributeError) as e:
                        logger.debug(f"Error processing row {j}: {e}")
                        continue
        
        logger.info(f"Extracted {len(models)} real models for {category_key}")
        
        # Only return if we have real data
        if models:
            return models[:100]  # Top 100
        else:
            logger.warning(f"No real data extracted for {category_key}")
            return []
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Get all REAL category data - NO FALLBACK"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            data = loop.run_until_complete(self.scrape_all_categories())
            
            # Only return categories that have real data
            if data:
                return {"chatbot_arena_real": data}
            else:
                logger.warning("No real Arena data found")
                return {}
        finally:
            loop.close() 