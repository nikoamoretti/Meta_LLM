"""
Arena Universal Scraper
Uses the universal framework to scrape Chatbot Arena with iframe strategy
"""
import asyncio
import logging
from typing import Dict, List
from .universal_scraping_framework import UniversalScraper

logger = logging.getLogger(__name__)

class ArenaUniversalScraper:
    """Specialized Arena scraper using universal framework"""
    
    def __init__(self):
        self.base_url = "https://huggingface.co/spaces/lmarena-ai/chatbot-arena-leaderboard"
        self.direct_url = "https://lmarena-ai-chatbot-arena-leaderboard.hf.space"
        
        # Categories we want to scrape
        self.categories = {
            "overall": "Overall",
            "math": "Math", 
            "instruction_following": "Instruction Following",
            "multi_turn": "Multi-Turn",
            "creative_writing": "Creative Writing", 
            "coding": "Coding",
            "hard_prompts": "Hard Prompts",
            "english": "English",
            "chinese": "Chinese"
        }
        
        self.universal_scraper = UniversalScraper()
    
    async def scrape_all_categories(self) -> Dict[str, List[Dict]]:
        """Scrape all Arena categories using universal framework"""
        logger.info("Starting Arena universal scraping...")
        
        all_data = {}
        
        # Strategy 1: Try direct iframe URL first
        logger.info("Trying direct iframe URL...")
        direct_result = await self.universal_scraper.scrape(
            self.direct_url, 
            categories=self.categories
        )
        
        if direct_result and direct_result.get('models'):
            logger.info(f"✅ Direct iframe strategy worked: {len(direct_result['models'])} models")
            # Group models by category
            for model in direct_result['models']:
                category = model.get('category', 'overall')
                if category not in all_data:
                    all_data[category] = []
                all_data[category].append(model)
            return all_data
        
        # Strategy 2: Try wrapper URL with iframe detection
        logger.info("Trying wrapper URL with iframe detection...")
        wrapper_result = await self.universal_scraper.scrape(
            self.base_url,
            categories=self.categories
        )
        
        if wrapper_result and wrapper_result.get('models'):
            logger.info(f"✅ Wrapper iframe strategy worked: {len(wrapper_result['models'])} models")
            # Group models by category
            for model in wrapper_result['models']:
                category = model.get('category', 'overall')
                if category not in all_data:
                    all_data[category] = []
                all_data[category].append(model)
            return all_data
        
        # Strategy 3: Try individual category URLs
        logger.info("Trying individual category scraping...")
        for category_key, category_name in self.categories.items():
            logger.info(f"Scraping category: {category_name}")
            
            category_url = f"{self.direct_url}?category={category_key}"
            category_result = await self.universal_scraper.scrape(
                category_url,
                categories={category_key: category_name}
            )
            
            if category_result and category_result.get('models'):
                logger.info(f"✅ Got {len(category_result['models'])} models for {category_name}")
                all_data[category_key] = category_result['models']
            else:
                logger.warning(f"❌ No data for {category_name}")
        
        return all_data
    
    def scrape_all(self) -> Dict[str, List[Dict]]:
        """Main entry point for scraping"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            data = loop.run_until_complete(self.scrape_all_categories())
            
            if data:
                return {"chatbot_arena_universal": data}
            else:
                logger.warning("No Arena data found with universal scraper")
                return {}
        finally:
            loop.close() 