#!/usr/bin/env python3
"""
Open Medical-LLM Leaderboard Scraper

Scrapes medical evaluation data from Open Medical-LLM Leaderboard.
Evaluates LLMs on medical question answering tasks across diverse healthcare datasets.

Website: https://huggingface.co/spaces/openlifescienceai/open_medical_llm_leaderboard
Focus: Medical domain expertise - MedQA (USMLE), MedMCQA, PubMedQA, MMLU Medical subsets
Data: 100+ medical models with healthcare-specific evaluation benchmarks

Medical Benchmarks:
- MedQA: United States Medical Licensing Examination (USMLE) questions
- MedMCQA: Indian medical entrance examinations (AIIMS/NEET)
- PubMedQA: Biomedical literature reasoning with PubMed abstracts
- MMLU Medical Subsets: Clinical Knowledge, Medical Genetics, Anatomy, Professional Medicine, College Biology, College Medicine
"""

import json
import time
import re
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalLLMScraper:
    def __init__(self):
        self.base_url = "https://huggingface.co/spaces/openlifescienceai/open_medical_llm_leaderboard"
        self.iframe_url = "https://openlifescienceai-open-medical-llm-leaderboard.hf.space/?__theme=system"
        self.medical_data = []
        
    def scrape_medical_leaderboard(self) -> List[Dict[str, Any]]:
        """
        Scrape medical model evaluation data from Open Medical-LLM Leaderboard
        
        Returns:
            List of dictionaries containing model medical evaluation data
        """
        logger.info("🩺 Starting Medical LLM Leaderboard scraping...")
        logger.info(f"Target URL: {self.base_url}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Set timeouts for medical content loading
                page.set_default_navigation_timeout(60000)
                page.set_default_timeout(60000)
                
                logger.info("🌐 Navigating to medical leaderboard...")
                page.goto(self.base_url, wait_until="domcontentloaded")
                
                # Wait for page to load
                time.sleep(10)
                logger.info("⏳ Waiting for medical content to load...")
                
                # Access iframe content
                iframe_element = page.frame_locator("iframe").first
                
                # Wait for medical leaderboard content to fully load
                time.sleep(15)
                logger.info("🔍 Accessing medical leaderboard iframe...")
                
                # Extract medical leaderboard tables
                tables = iframe_element.locator("table").all()
                logger.info(f"📊 Found {len(tables)} medical leaderboard tables")
                
                if not tables:
                    logger.error("❌ No medical leaderboard tables found")
                    browser.close()
                    return []
                
                # Extract data from the main medical leaderboard table
                medical_models = []
                
                for table_idx, table in enumerate(tables):
                    logger.info(f"🔬 Processing medical table {table_idx + 1}...")
                    
                    try:
                        # Extract table headers for medical benchmarks
                        headers = []
                        header_elements = table.locator("thead th").all()
                        
                        for header in header_elements:
                            header_text = header.inner_text().strip()
                            if header_text:
                                headers.append(header_text)
                        
                        logger.info(f"📋 Medical table headers: {headers}")
                        
                        # Skip if this doesn't look like a medical leaderboard table
                        medical_keywords = ["model", "medqa", "medmcqa", "pubmedqa", "clinical", "anatomy", "average"]
                        has_medical_content = any(keyword.lower() in ' '.join(headers).lower() for keyword in medical_keywords)
                        
                        if not has_medical_content:
                            logger.info(f"⏭️ Table {table_idx + 1} doesn't contain medical evaluation data, skipping...")
                            continue
                        
                        # Extract medical model data rows
                        rows = table.locator("tbody tr").all()
                        logger.info(f"🏥 Found {len(rows)} medical model entries in table {table_idx + 1}")
                        
                        for row_idx, row in enumerate(rows):
                            try:
                                cells = row.locator("td").all()
                                
                                if len(cells) < 2:  # Need at least model name and one score
                                    continue
                                
                                # Extract medical model data
                                model_data = {}
                                
                                for cell_idx, cell in enumerate(cells):
                                    if cell_idx < len(headers):
                                        header_name = headers[cell_idx]
                                        cell_text = cell.inner_text().strip()
                                        
                                        # Clean up cell text
                                        cell_text = re.sub(r'\s+', ' ', cell_text)
                                        model_data[header_name] = cell_text
                                
                                # Validate medical model entry
                                if self._is_valid_medical_entry(model_data):
                                    medical_models.append(model_data)
                                    logger.info(f"✅ Medical model {row_idx + 1}: {model_data.get('Model', 'Unknown')}")
                                
                            except Exception as e:
                                logger.warning(f"⚠️ Error processing medical model row {row_idx + 1}: {e}")
                                continue
                    
                    except Exception as e:
                        logger.warning(f"⚠️ Error processing medical table {table_idx + 1}: {e}")
                        continue
                
                browser.close()
                
                # Final validation and cleaning
                cleaned_models = self._clean_medical_data(medical_models)
                
                logger.info(f"🎯 Medical scraping complete: {len(cleaned_models)} medical models extracted")
                logger.info(f"📊 Sample medical model: {cleaned_models[0] if cleaned_models else 'None'}")
                
                self.medical_data = cleaned_models
                return cleaned_models
                
        except Exception as e:
            logger.error(f"❌ Medical leaderboard scraping failed: {e}")
            return []
    
    def _is_valid_medical_entry(self, model_data: Dict[str, Any]) -> bool:
        """
        Validate if a model entry contains valid medical evaluation data
        
        Args:
            model_data: Dictionary containing model data
            
        Returns:
            Boolean indicating if entry is valid
        """
        # Check for model name
        model_name = model_data.get('Model', '').strip()
        if not model_name or len(model_name) < 3:
            return False
        
        # Check for medical benchmark scores
        medical_benchmarks = ['MedQA', 'MedMCQA', 'PubMedQA', 'Clinical Knowledge', 
                             'Medical Genetics', 'Anatomy', 'Professional Medicine', 
                             'College Biology', 'College Medicine', 'Average']
        
        has_scores = False
        for benchmark in medical_benchmarks:
            for key in model_data.keys():
                if benchmark.lower() in key.lower():
                    score_text = model_data[key]
                    # Check for numeric score pattern
                    if re.search(r'\d+\.?\d*', score_text):
                        has_scores = True
                        break
            if has_scores:
                break
        
        return has_scores
    
    def _clean_medical_data(self, medical_models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean and standardize medical model data
        
        Args:
            medical_models: Raw medical model data
            
        Returns:
            Cleaned medical model data
        """
        cleaned_models = []
        seen_models = set()
        
        for model in medical_models:
            model_name = model.get('Model', '').strip()
            
            # Skip duplicates
            if model_name in seen_models:
                continue
            
            # Clean model name
            model_name = re.sub(r'^[^\w]+|[^\w]+$', '', model_name)
            
            if len(model_name) < 3:
                continue
            
            # Standardize the medical model entry
            cleaned_model = {
                'model_name': model_name,
                'source': 'Open Medical-LLM Leaderboard',
                'category': 'medical',
                'benchmarks': {}
            }
            
            # Extract medical benchmark scores
            for key, value in model.items():
                if key.lower() == 'model':
                    continue
                
                # Clean score value
                score_match = re.search(r'(\d+\.?\d*)', str(value))
                if score_match:
                    try:
                        score = float(score_match.group(1))
                        # Medical scores are typically accuracy percentages
                        if 0 <= score <= 100:
                            cleaned_model['benchmarks'][key] = score
                    except ValueError:
                        continue
            
            # Only include models with medical benchmark scores
            if cleaned_model['benchmarks']:
                cleaned_models.append(cleaned_model)
                seen_models.add(model_name)
        
        return cleaned_models
    
    def save_medical_data(self, filename: str = "medical_llm_data.json") -> bool:
        """
        Save medical leaderboard data to JSON file
        
        Args:
            filename: Output filename
            
        Returns:
            Boolean indicating success
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.medical_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Medical data saved to {filename}")
            logger.info(f"📊 Total medical models: {len(self.medical_data)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save medical data: {e}")
            return False

def main():
    """Main function to run medical leaderboard scraping"""
    scraper = MedicalLLMScraper()
    
    print("🩺 MEDICAL LLM LEADERBOARD SCRAPER")
    print("=" * 50)
    
    # Scrape medical leaderboard
    medical_models = scraper.scrape_medical_leaderboard()
    
    if medical_models:
        print(f"\n✅ SUCCESS: Scraped {len(medical_models)} medical models")
        
        # Display sample medical models
        print("\n📊 SAMPLE MEDICAL MODELS:")
        for i, model in enumerate(medical_models[:5], 1):
            model_name = model.get('model_name', 'Unknown')
            benchmark_count = len(model.get('benchmarks', {}))
            print(f"  {i}. {model_name} - {benchmark_count} medical benchmarks")
        
        # Save medical data
        if scraper.save_medical_data():
            print(f"\n💾 Medical data saved to medical_llm_data.json")
        
        # Display medical benchmark summary
        all_benchmarks = set()
        for model in medical_models:
            all_benchmarks.update(model.get('benchmarks', {}).keys())
        
        print(f"\n🏥 MEDICAL BENCHMARKS FOUND:")
        for benchmark in sorted(all_benchmarks):
            print(f"  • {benchmark}")
        
        print(f"\n🎯 MEDICAL SCRAPING SUMMARY:")
        print(f"  📊 Total Models: {len(medical_models)}")
        print(f"  🏥 Medical Benchmarks: {len(all_benchmarks)}")
        print(f"  📈 Total Scores: {sum(len(m.get('benchmarks', {})) for m in medical_models)}")
        
    else:
        print("\n❌ FAILED: No medical models extracted")
        print("Check log messages for error details")

if __name__ == "__main__":
    main() 