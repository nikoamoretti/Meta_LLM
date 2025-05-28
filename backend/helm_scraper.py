#!/usr/bin/env python3
"""
Stanford HELM (Holistic Evaluation of Language Models) Scraper
Production-ready scraper for extracting academic evaluation data

Target: https://crfm.stanford.edu/helm/classic/latest/#/leaderboard
Expected: 68 models across 17 comprehensive benchmarks

Based on successful analysis showing:
- Structured table with complete model evaluations
- 1,224 data cells of authentic academic research
- Top models: Llama 2 (70B) 0.944, LLaMA (65B) 0.908, text-davinci-002 0.905
"""
import asyncio
import logging
import json
from datetime import datetime
from playwright.async_api import async_playwright
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HELMScraper:
    def __init__(self):
        self.leaderboard_url = "https://crfm.stanford.edu/helm/classic/latest/#/leaderboard"
        self.models_data = []
        
    async def scrape_helm_leaderboard(self) -> List[Dict[str, Any]]:
        """
        Scrape the Stanford HELM leaderboard to extract model evaluation data
        
        Returns:
            List of dictionaries containing model data with scores
        """
        print("🎓 Scraping Stanford HELM Leaderboard...")
        print(f"Target: {self.leaderboard_url}")
        print("Expected: 68 models with 17 benchmark evaluations")
        print("=" * 70)
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        
        try:
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Navigate to HELM leaderboard
            logger.info("Loading HELM leaderboard...")
            await page.goto(self.leaderboard_url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for SPA content to load
            await page.wait_for_timeout(15000)
            
            # Extract the leaderboard table data
            table_data = await page.evaluate("""
                () => {
                    const table = document.querySelector('table');
                    if (!table) {
                        return { error: 'No table found' };
                    }
                    
                    const rows = table.querySelectorAll('tr');
                    if (rows.length < 2) {
                        return { error: 'No data rows found' };
                    }
                    
                    // Extract headers
                    const headerRow = rows[0];
                    const headers = Array.from(headerRow.querySelectorAll('th, td')).map(cell => cell.textContent.trim());
                    
                    // Extract all data rows
                    const models = [];
                    for (let i = 1; i < rows.length; i++) {
                        const cells = rows[i].querySelectorAll('td, th');
                        const rowData = Array.from(cells).map(cell => cell.textContent.trim());
                        
                        if (rowData.length >= headers.length) {
                            const modelData = {};
                            headers.forEach((header, index) => {
                                modelData[header] = rowData[index] || null;
                            });
                            models.push(modelData);
                        }
                    }
                    
                    return {
                        headers: headers,
                        models: models,
                        totalModels: models.length,
                        totalBenchmarks: headers.length - 2  // Excluding 'Model' and 'Mean win rate'
                    };
                }
            """)
            
            if 'error' in table_data:
                logger.error(f"Error extracting table: {table_data['error']}")
                return []
            
            # Process the extracted data
            self.models_data = table_data['models']
            
            # Print extraction summary
            print(f"\n✅ HELM DATA EXTRACTION SUCCESSFUL!")
            print(f"📊 Models extracted: {table_data['totalModels']}")
            print(f"📈 Benchmarks per model: {table_data['totalBenchmarks']}")
            print(f"📋 Headers: {table_data['headers'][:5]}... (+{len(table_data['headers'])-5} more)")
            
            # Show top 5 models as verification
            print(f"\n🏆 TOP 5 MODELS (by Mean win rate):")
            for i, model in enumerate(self.models_data[:5]):
                model_name = model.get('Model', 'Unknown')
                win_rate = model.get('Mean win rate', 'N/A')
                print(f"  {i+1}. {model_name}: {win_rate}")
            
            # Validate data quality
            valid_models = [m for m in self.models_data if m.get('Model') and m.get('Mean win rate')]
            print(f"\n🔍 Data Quality Check:")
            print(f"  Valid models with complete data: {len(valid_models)}/{len(self.models_data)}")
            print(f"  Data completeness: {len(valid_models)/len(self.models_data)*100:.1f}%")
            
            # Save raw data for verification
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            raw_data_file = f"helm_raw_data_{timestamp}.json"
            with open(raw_data_file, 'w') as f:
                json.dump({
                    'extraction_info': {
                        'timestamp': datetime.now().isoformat(),
                        'source_url': self.leaderboard_url,
                        'total_models': table_data['totalModels'],
                        'total_benchmarks': table_data['totalBenchmarks'],
                        'headers': table_data['headers']
                    },
                    'models_data': self.models_data
                }, f, indent=2)
            
            logger.info(f"Raw data saved to: {raw_data_file}")
            
            # Wait to see the browser
            print(f"\n⏳ Keeping browser open for 10 seconds...")
            await page.wait_for_timeout(10000)
            
            return self.models_data
            
        except Exception as e:
            logger.error(f"Error during HELM scraping: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        finally:
            await browser.close()
            await playwright.stop()
    
    def transform_helm_data(self) -> List[Dict[str, Any]]:
        """
        Transform raw HELM data into our standardized format
        
        Returns:
            List of model entries with standardized benchmark scores
        """
        if not self.models_data:
            logger.warning("No HELM data to transform")
            return []
        
        print(f"\n🔄 Transforming HELM data into standardized format...")
        
        transformed_models = []
        
        for model_data in self.models_data:
            model_name = model_data.get('Model')
            if not model_name:
                continue
                
            # Create base model entry
            model_entry = {
                'model_name': model_name.strip(),
                'mean_win_rate': self._parse_score(model_data.get('Mean win rate')),
                'benchmarks': {}
            }
            
            # Map HELM benchmarks to our format
            benchmark_mapping = {
                'MMLU - EM': 'mmlu',
                'BoolQ - EM': 'boolq', 
                'NarrativeQA - F1': 'narrativeqa',
                'NaturalQuestions (closed) - F1': 'naturalquestions_closed',
                'NaturalQuestions (open) - F1': 'naturalquestions_open',
                'QuAC - F1': 'quac',
                'HellaSwag - EM': 'hellaswag',
                'OpenbookQA - EM': 'openbookqa',
                'TruthfulQA - EM': 'truthfulqa',
                'MS MARCO (regular) - RR@10': 'ms_marco_regular',
                'MS MARCO (TREC) - NDCG@10': 'ms_marco_trec',
                'CNN/DailyMail - ROUGE-2': 'cnn_dailymail',
                'XSUM - ROUGE-2': 'xsum',
                'IMDB - EM': 'imdb',
                'CivilComments - EM': 'civilcomments',
                'RAFT - EM': 'raft'
            }
            
            # Extract benchmark scores
            for helm_name, standard_name in benchmark_mapping.items():
                score = self._parse_score(model_data.get(helm_name))
                if score is not None:
                    model_entry['benchmarks'][standard_name] = score
            
            # Only include models with at least some benchmark data
            if model_entry['benchmarks']:
                transformed_models.append(model_entry)
        
        print(f"✅ Transformed {len(transformed_models)} models successfully")
        print(f"📊 Average benchmarks per model: {sum(len(m['benchmarks']) for m in transformed_models) / len(transformed_models):.1f}")
        
        return transformed_models
    
    def _parse_score(self, score_str: str) -> float:
        """Parse score string to float, handling dashes and empty values"""
        if not score_str or score_str.strip() in ['-', '', 'N/A']:
            return None
        
        try:
            return float(score_str.strip())
        except (ValueError, TypeError):
            return None
    
    def save_transformed_data(self, transformed_data: List[Dict[str, Any]], filename: str = None):
        """Save transformed data to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"helm_transformed_data_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                'extraction_info': {
                    'timestamp': datetime.now().isoformat(),
                    'source': 'Stanford HELM Classic',
                    'url': self.leaderboard_url,
                    'total_models': len(transformed_data),
                    'description': 'Holistic Evaluation of Language Models - Academic benchmark data'
                },
                'models': transformed_data
            }, f, indent=2)
        
        logger.info(f"Transformed data saved to: {filename}")
        return filename

async def main():
    """Main function to run HELM scraping"""
    scraper = HELMScraper()
    
    # Step 1: Scrape raw data
    raw_models = await scraper.scrape_helm_leaderboard()
    
    if raw_models:
        # Step 2: Transform data
        transformed_models = scraper.transform_helm_data()
        
        # Step 3: Save transformed data
        if transformed_models:
            filename = scraper.save_transformed_data(transformed_models)
            
            print(f"\n🎉 HELM SCRAPING COMPLETED SUCCESSFULLY!")
            print(f"📁 Raw data: helm_raw_data_*.json")
            print(f"📁 Transformed data: {filename}")
            print(f"📊 Ready for database integration!")
            print("=" * 70)
            
        else:
            print("❌ No data could be transformed")
    else:
        print("❌ No data could be scraped")

if __name__ == "__main__":
    asyncio.run(main()) 