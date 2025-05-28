#!/usr/bin/env python3
"""
HuggingFace Open LLM Leaderboard Scraper
Scrapes the new Open LLM Leaderboard with updated benchmarks (IFEval, BBH, MATH, GPQA, MUSR, MMLU-PRO)

Based on successful iframe analysis showing:
- Table with ~200+ models
- Headers: Rank, Type, Model, Average, IFEval, BBH, MATH, GPQA, MUSR, MMLU-PRO, CO₂ Cost
- Iframe URL: https://open-llm-leaderboard-open-llm-leaderboard.hf.space/
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from playwright.async_api import async_playwright

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HuggingFaceOpenLLMScraper:
    def __init__(self):
        self.source_name = "HuggingFace Open LLM Leaderboard"
        self.base_url = "https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard"
        self.iframe_url = "https://open-llm-leaderboard-open-llm-leaderboard.hf.space/"
        
        # Expected benchmarks in the new leaderboard
        self.expected_benchmarks = {
            'IFEval': 'Instruction Following Evaluation',
            'BBH': 'BIG-Bench Hard',
            'MATH': 'Mathematics',
            'GPQA': 'Graduate-Level Google-Proof Q&A',
            'MUSR': 'Multistep Soft Reasoning',
            'MMLU-PRO': 'Massive Multitask Language Understanding Pro'
        }
        
        # Model type emojis
        self.model_types = {
            '🔶': 'fine-tuned',
            '💬': 'chat',
            '🟢': 'pretrained',
            '🟩': 'continuously-pretrained',
            '🌸': 'multimodal',
            '🤝': 'merge'
        }
    
    async def scrape_leaderboard(self) -> List[Dict]:
        """
        Scrape the HuggingFace Open LLM Leaderboard
        Returns list of model entries with scores
        """
        logger.info(f"🤗 Starting HuggingFace Open LLM Leaderboard scraping...")
        logger.info(f"Target URL: {self.base_url}")
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        
        scraped_data = []
        
        try:
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Navigate to the main page
            logger.info("Navigating to HuggingFace Space...")
            await page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for iframe to load
            logger.info("Waiting for iframe to load...")
            await page.wait_for_timeout(10000)
            
            # Find and access the iframe
            frames = page.frames
            target_frame = None
            
            for frame in frames:
                if frame != page.main_frame and self.iframe_url in frame.url:
                    target_frame = frame
                    logger.info(f"✅ Found target iframe: {frame.url}")
                    break
            
            if not target_frame:
                # Try to find iframe by content analysis
                for frame in frames:
                    if frame != page.main_frame:
                        try:
                            frame_content = await frame.evaluate("document.body ? document.body.textContent : ''")
                            if 'Average' in frame_content and 'MMLU' in frame_content:
                                target_frame = frame
                                logger.info(f"✅ Found target iframe by content: {frame.url}")
                                break
                        except:
                            continue
            
            if not target_frame:
                raise Exception("Could not find leaderboard iframe")
            
            # Wait for content to fully load in iframe
            logger.info("Waiting for leaderboard content to load...")
            await asyncio.sleep(15)  # Give more time for dynamic content
            
            # Extract table data from iframe
            logger.info("Extracting leaderboard table data...")
            table_data = await target_frame.evaluate("""
                () => {
                    const results = [];
                    const tables = document.querySelectorAll('table');
                    
                    console.log(`Found ${tables.length} tables in iframe`);
                    
                    for (let tableIndex = 0; tableIndex < tables.length; tableIndex++) {
                        const table = tables[tableIndex];
                        const rows = table.querySelectorAll('tr');
                        
                        if (rows.length > 5) {  // Must have header + at least 4 data rows
                            // Get headers
                            const headerRow = rows[0];
                            const headers = Array.from(headerRow.querySelectorAll('th, td')).map(cell => 
                                cell.textContent.trim()
                            );
                            
                            console.log(`Table ${tableIndex} headers:`, headers);
                            
                            // Check if this is the leaderboard table
                            const hasModel = headers.some(h => h.toLowerCase().includes('model'));
                            const hasAverage = headers.some(h => h.toLowerCase().includes('average'));
                            const hasIFEval = headers.some(h => h.toLowerCase().includes('ifeval'));
                            const hasMMLU = headers.some(h => h.toLowerCase().includes('mmlu'));
                            
                            if (hasModel && hasAverage && (hasIFEval || hasMMLU)) {
                                console.log(`✅ Found leaderboard table ${tableIndex}`);
                                
                                const tableResult = {
                                    tableIndex: tableIndex,
                                    headers: headers,
                                    rows: [],
                                    timestamp: new Date().toISOString()
                                };
                                
                                // Extract all data rows
                                for (let i = 1; i < rows.length; i++) {
                                    const cells = rows[i].querySelectorAll('td, th');
                                    const rowData = Array.from(cells).map(cell => cell.textContent.trim());
                                    
                                    if (rowData.length >= headers.length - 1) {  // Allow for slight variation
                                        tableResult.rows.push({
                                            rowIndex: i,
                                            data: rowData
                                        });
                                    }
                                }
                                
                                console.log(`Extracted ${tableResult.rows.length} model entries`);
                                return tableResult;  // Return the first valid table
                            }
                        }
                    }
                    
                    return null;
                }
            """)
            
            if not table_data:
                raise Exception("No valid leaderboard table found")
                
            logger.info(f"✅ Successfully extracted table with {len(table_data['rows'])} models")
            logger.info(f"Headers: {table_data['headers']}")
            
            # Process the extracted data
            processed_data = self.process_table_data(table_data)
            scraped_data.extend(processed_data)
            
            logger.info(f"🎯 Successfully processed {len(scraped_data)} model entries")
            
        except Exception as e:
            logger.error(f"❌ Error during scraping: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        finally:
            await browser.close()
            await playwright.stop()
        
        return scraped_data
    
    def process_table_data(self, table_data: Dict) -> List[Dict]:
        """Process the raw table data into structured format"""
        processed_models = []
        headers = table_data['headers']
        
        # Map headers to expected positions
        header_map = {}
        for i, header in enumerate(headers):
            header_lower = header.lower()
            if 'rank' in header_lower:
                header_map['rank'] = i
            elif 'model' in header_lower:
                header_map['model'] = i
            elif 'type' in header_lower:
                header_map['type'] = i
            elif 'average' in header_lower:
                header_map['average'] = i
            elif 'ifeval' in header_lower:
                header_map['ifeval'] = i
            elif 'bbh' in header_lower:
                header_map['bbh'] = i
            elif 'math' in header_lower:
                header_map['math'] = i
            elif 'gpqa' in header_lower:
                header_map['gpqa'] = i
            elif 'musr' in header_lower:
                header_map['musr'] = i
            elif 'mmlu' in header_lower:
                header_map['mmlu_pro'] = i
            elif 'co' in header_lower and 'cost' in header_lower:
                header_map['co2_cost'] = i
        
        logger.info(f"Header mapping: {header_map}")
        
        for row in table_data['rows']:
            try:
                row_data = row['data']
                
                # Skip rows that don't have a model name
                if 'model' not in header_map or len(row_data) <= header_map['model']:
                    continue
                
                model_name = row_data[header_map['model']].strip()
                if not model_name or model_name == '-':
                    continue
                
                # Extract model info
                model_entry = {
                    'model': model_name,
                    'source': self.source_name,
                    'timestamp': datetime.now().isoformat(),
                    'rank': self._safe_extract(row_data, header_map.get('rank'), int),
                    'model_type': self._parse_model_type(self._safe_extract(row_data, header_map.get('type'))),
                    'scores': {},
                    'metadata': {}
                }
                
                # Extract scores
                if 'average' in header_map:
                    avg_score = self._parse_percentage(self._safe_extract(row_data, header_map['average']))
                    if avg_score is not None:
                        model_entry['scores']['Average'] = avg_score
                
                # Extract individual benchmark scores
                benchmark_mappings = {
                    'ifeval': 'IFEval',
                    'bbh': 'BBH', 
                    'math': 'MATH',
                    'gpqa': 'GPQA',
                    'musr': 'MUSR',
                    'mmlu_pro': 'MMLU-PRO'
                }
                
                for key, benchmark_name in benchmark_mappings.items():
                    if key in header_map:
                        score = self._parse_percentage(self._safe_extract(row_data, header_map[key]))
                        if score is not None:
                            model_entry['scores'][benchmark_name] = score
                
                # Extract CO₂ cost
                if 'co2_cost' in header_map:
                    co2_cost = self._safe_extract(row_data, header_map['co2_cost'])
                    if co2_cost:
                        model_entry['metadata']['co2_cost'] = co2_cost
                
                # Only include if we have at least some scores
                if model_entry['scores']:
                    processed_models.append(model_entry)
                    
            except Exception as e:
                logger.warning(f"Error processing row {row.get('rowIndex', 'unknown')}: {e}")
                continue
        
        return processed_models
    
    def _safe_extract(self, row_data: List[str], index: Optional[int], convert_func=None):
        """Safely extract data from row with optional conversion"""
        if index is None or index >= len(row_data):
            return None
        
        value = row_data[index].strip()
        if not value or value == '-':
            return None
        
        if convert_func:
            try:
                return convert_func(value)
            except:
                return None
        
        return value
    
    def _parse_percentage(self, value: Optional[str]) -> Optional[float]:
        """Parse percentage string to float"""
        if not value:
            return None
        
        try:
            # Remove percentage sign and convert
            clean_value = value.replace('%', '').strip()
            return float(clean_value)
        except:
            return None
    
    def _parse_model_type(self, type_emoji: Optional[str]) -> str:
        """Parse model type emoji to readable string"""
        if not type_emoji:
            return 'unknown'
        
        return self.model_types.get(type_emoji.strip(), type_emoji.strip())

async def main():
    """Test the scraper"""
    scraper = HuggingFaceOpenLLMScraper()
    
    try:
        models = await scraper.scrape_leaderboard()
        
        print(f"\n🎯 SCRAPING RESULTS:")
        print(f"Total models extracted: {len(models)}")
        
        if models:
            print(f"\n📊 Top 5 Models:")
            for i, model in enumerate(models[:5]):
                print(f"{i+1}. {model['model']} ({model.get('model_type', 'unknown')})")
                print(f"   Average: {model['scores'].get('Average', 'N/A')}%")
                print(f"   Benchmarks: {len(model['scores'])} metrics")
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"huggingface_open_llm_data_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(models, f, indent=2)
        
        print(f"\n💾 Data saved to: {filename}")
        print(f"✅ HuggingFace Open LLM scraping completed successfully!")
        
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 