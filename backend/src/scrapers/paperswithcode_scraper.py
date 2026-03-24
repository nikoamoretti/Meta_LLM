"""
PapersWithCode SOTA Scraper
Comprehensive scraping of SOTA tables for academic benchmark coverage
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

class PapersWithCodeScraper:
    """
    Scrapes PapersWithCode for SOTA (State of the Art) results
    Focuses on language model benchmarks and leaderboards
    """
    
    def __init__(self):
        self.base_url = "https://paperswithcode.com"
        self.api_url = "https://paperswithcode.com/api/v1"
        self.session = None
        
        # Target datasets/benchmarks relevant to language models
        self.target_datasets = [
            "GLUE", "SuperGLUE", "MMLU", "HellaSwag", "ARC", "CommonsenseQA",
            "WinoGrande", "RACE", "SQuAD", "CoQA", "QuAC", "MS-MARCO",
            "Natural Questions", "TriviaQA", "WebQuestions", "HotpotQA",
            "DROP", "NewsQA", "SearchQA", "DuoRC", "QNLI", "QQP", "MNLI",
            "RTE", "WNLI", "SST-2", "CoLA", "STS-B", "MRPC", "BoolQ",
            "CB", "COPA", "MultiRC", "ReCoRD", "WiC", "WSC", "GSM8K",
            "MATH", "HumanEval", "MBPP", "CodeGen", "BigBench", "TruthfulQA"
        ]
        
    async def scrape_async(self) -> Dict:
        """
        Main async scraping method
        """
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            logger.info("Starting PapersWithCode SOTA scraping...")
            
            # Scrape different types of data
            tasks = [
                self._scrape_dataset_leaderboards(),
                self._discover_language_model_benchmarks(),
                self._scrape_trending_benchmarks(),
                self._scrape_evaluation_tables()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            combined_data = {
                "models": [],
                "leaderboard": {"entries": [], "headers": []},
                "benchmarks": [],
                "metadata": {
                    "source": "paperswithcode",
                    "scraped_at": datetime.utcnow().isoformat(),
                    "total_datasets_checked": len(self.target_datasets)
                }
            }
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"PwC scraping task {i} failed: {str(result)}")
                    continue
                
                if isinstance(result, dict):
                    # Merge models
                    if "models" in result:
                        combined_data["models"].extend(result["models"])
                    
                    # Merge leaderboard entries
                    if "leaderboard" in result:
                        combined_data["leaderboard"]["entries"].extend(
                            result["leaderboard"].get("entries", [])
                        )
                        combined_data["leaderboard"]["headers"].extend(
                            result["leaderboard"].get("headers", [])
                        )
                    
                    # Merge benchmarks
                    if "benchmarks" in result:
                        combined_data["benchmarks"].extend(result["benchmarks"])
            
            # Deduplicate
            combined_data = self._deduplicate_data(combined_data)
            
            logger.info(f"PapersWithCode scraping complete: {len(combined_data['models'])} models, "
                       f"{len(combined_data['benchmarks'])} benchmarks, "
                       f"{len(combined_data['leaderboard']['entries'])} SOTA entries")
            
            return combined_data
    
    async def _scrape_dataset_leaderboards(self) -> Dict:
        """
        Scrape leaderboards for known target datasets
        """
        logger.info("Scraping dataset leaderboards...")
        
        all_models = []
        all_entries = []
        all_headers = set()
        all_benchmarks = []
        
        for dataset in self.target_datasets:
            try:
                # Try API first
                dataset_data = await self._get_dataset_via_api(dataset)
                
                if not dataset_data:
                    # Fall back to web scraping
                    dataset_data = await self._scrape_dataset_webpage(dataset)
                
                if dataset_data:
                    all_models.extend(dataset_data.get("models", []))
                    all_entries.extend(dataset_data.get("leaderboard", {}).get("entries", []))
                    all_headers.update(dataset_data.get("leaderboard", {}).get("headers", []))
                    all_benchmarks.extend(dataset_data.get("benchmarks", []))
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.debug(f"Error scraping dataset {dataset}: {str(e)}")
                continue
        
        logger.info(f"Dataset leaderboards: {len(all_models)} models from {len(self.target_datasets)} datasets")
        
        return {
            "models": all_models,
            "leaderboard": {
                "entries": all_entries,
                "headers": list(all_headers)
            },
            "benchmarks": all_benchmarks
        }
    
    async def _get_dataset_via_api(self, dataset_name: str) -> Optional[Dict]:
        """
        Try to get dataset information via PapersWithCode API
        """
        try:
            # Search for the dataset
            search_url = f"{self.api_url}/datasets/"
            params = {"q": dataset_name}
            
            async with self.session.get(search_url, params=params) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                results = data.get("results", [])
                
                # Find exact or close match
                dataset_match = None
                for result in results:
                    if result["name"].lower() == dataset_name.lower():
                        dataset_match = result
                        break
                    elif dataset_name.lower() in result["name"].lower():
                        dataset_match = result
                
                if not dataset_match:
                    return None
                
                # Get SOTA results for this dataset
                dataset_id = dataset_match["id"]
                sota_url = f"{self.api_url}/datasets/{dataset_id}/sota/"
                
                async with self.session.get(sota_url) as sota_response:
                    if sota_response.status != 200:
                        return None
                    
                    sota_data = await sota_response.json()
                    return self._parse_api_sota_data(sota_data, dataset_name)
                    
        except Exception as e:
            logger.debug(f"API request failed for {dataset_name}: {str(e)}")
            return None
    
    def _parse_api_sota_data(self, sota_data: Dict, dataset_name: str) -> Dict:
        """
        Parse SOTA data from API response
        """
        models = []
        entries = []
        headers = set()
        benchmarks = []
        
        # Add the dataset as a benchmark
        benchmarks.append({
            "name": dataset_name,
            "source": "paperswithcode",
            "official_url": f"https://paperswithcode.com/dataset/{dataset_name.lower()}"
        })
        
        # Parse SOTA results
        results = sota_data.get("results", [])
        for result in results:
            try:
                # Extract model information
                paper = result.get("paper", {})
                method = result.get("method", {})
                
                model_name = method.get("name", paper.get("title", "Unknown"))
                if not model_name or model_name == "Unknown":
                    continue
                
                # Clean up model name
                model_name = self._clean_model_name(model_name)
                
                models.append({
                    "name": model_name,
                    "metadata": {
                        "paper_title": paper.get("title"),
                        "paper_url": paper.get("url_pdf"),
                        "method": method.get("name"),
                        "source_dataset": dataset_name
                    }
                })
                
                # Extract metrics
                metrics = result.get("metrics", {})
                scores = {}
                
                for metric_name, metric_value in metrics.items():
                    if isinstance(metric_value, (int, float)):
                        clean_metric = self._clean_metric_name(metric_name)
                        scores[clean_metric] = metric_value
                        headers.add(clean_metric)
                
                if scores:
                    entries.append({
                        "model": model_name,
                        "scores": scores
                    })
                    
            except Exception as e:
                logger.debug(f"Error parsing SOTA result: {str(e)}")
                continue
        
        return {
            "models": models,
            "leaderboard": {
                "entries": entries,
                "headers": list(headers)
            },
            "benchmarks": benchmarks
        }
    
    async def _scrape_dataset_webpage(self, dataset_name: str) -> Optional[Dict]:
        """
        Scrape dataset webpage for SOTA results
        """
        try:
            # Construct likely URL
            dataset_slug = dataset_name.lower().replace(" ", "-")
            url = f"{self.base_url}/sota/{dataset_slug}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                return self._parse_sota_webpage(soup, dataset_name)
                
        except Exception as e:
            logger.debug(f"Error scraping webpage for {dataset_name}: {str(e)}")
            return None
    
    def _parse_sota_webpage(self, soup: BeautifulSoup, dataset_name: str) -> Dict:
        """
        Parse SOTA webpage HTML
        """
        models = []
        entries = []
        headers = set()
        benchmarks = []
        
        # Add the dataset as a benchmark
        benchmarks.append({
            "name": dataset_name,
            "source": "paperswithcode"
        })
        
        # Look for SOTA tables
        tables = soup.find_all("table", class_=re.compile(r"sota|leaderboard|results"))
        
        if not tables:
            # Try more generic table search
            tables = soup.find_all("table")
        
        for table in tables:
            try:
                # Extract headers
                header_row = table.find("thead") or table.find("tr")
                if header_row:
                    header_cells = header_row.find_all(["th", "td"])
                    table_headers = [cell.get_text(strip=True) for cell in header_cells]
                    
                    # Find model column
                    model_col_idx = None
                    for i, header in enumerate(table_headers):
                        if any(term in header.lower() for term in ["model", "method", "paper"]):
                            model_col_idx = i
                            break
                    
                    if model_col_idx is None:
                        continue
                    
                    # Extract data rows
                    rows = table.find_all("tr")[1:]  # Skip header
                    
                    for row in rows:
                        cells = row.find_all(["td", "th"])
                        if len(cells) <= model_col_idx:
                            continue
                        
                        # Extract model name
                        model_cell = cells[model_col_idx]
                        model_name = model_cell.get_text(strip=True)
                        
                        if not model_name:
                            continue
                        
                        model_name = self._clean_model_name(model_name)
                        
                        models.append({
                            "name": model_name,
                            "metadata": {
                                "source_dataset": dataset_name
                            }
                        })
                        
                        # Extract scores
                        scores = {}
                        for i, cell in enumerate(cells):
                            if i == model_col_idx:
                                continue
                            
                            cell_text = cell.get_text(strip=True)
                            
                            # Try to parse as number
                            try:
                                score = float(cell_text.replace("%", ""))
                                header_name = table_headers[i] if i < len(table_headers) else f"metric_{i}"
                                clean_header = self._clean_metric_name(header_name)
                                scores[clean_header] = score
                                headers.add(clean_header)
                            except ValueError:
                                continue
                        
                        if scores:
                            entries.append({
                                "model": model_name,
                                "scores": scores
                            })
                            
            except Exception as e:
                logger.debug(f"Error parsing table: {str(e)}")
                continue
        
        return {
            "models": models,
            "leaderboard": {
                "entries": entries,
                "headers": list(headers)
            },
            "benchmarks": benchmarks
        }
    
    async def _discover_language_model_benchmarks(self) -> Dict:
        """
        Discover new language model benchmarks
        """
        logger.info("Discovering language model benchmarks...")
        
        benchmarks = []
        
        try:
            # Search for language model related datasets
            search_terms = [
                "language model", "natural language", "text generation",
                "question answering", "reading comprehension", "text classification",
                "sentiment analysis", "natural language inference"
            ]
            
            for term in search_terms:
                try:
                    url = f"{self.api_url}/datasets/"
                    params = {"q": term, "limit": 20}
                    
                    async with self.session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for dataset in data.get("results", []):
                                benchmarks.append({
                                    "name": dataset["name"],
                                    "description": dataset.get("description", ""),
                                    "source": "paperswithcode",
                                    "official_url": dataset.get("url", ""),
                                    "discovery_term": term
                                })
                    
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    logger.debug(f"Error searching for '{term}': {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in benchmark discovery: {str(e)}")
        
        logger.info(f"Discovered {len(benchmarks)} potential benchmarks")
        
        return {"benchmarks": benchmarks}
    
    async def _scrape_trending_benchmarks(self) -> Dict:
        """
        Scrape trending/popular benchmarks
        """
        logger.info("Scraping trending benchmarks...")
        
        benchmarks = []
        
        try:
            # Get trending datasets
            url = f"{self.api_url}/datasets/"
            params = {"ordering": "-stars", "limit": 50}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for dataset in data.get("results", []):
                        # Filter for language-related datasets
                        name = dataset["name"].lower()
                        description = dataset.get("description", "").lower()
                        
                        if any(term in name or term in description for term in [
                            "language", "text", "nlp", "natural", "qa", "question",
                            "reading", "comprehension", "generation", "classification"
                        ]):
                            benchmarks.append({
                                "name": dataset["name"],
                                "description": dataset.get("description", ""),
                                "source": "paperswithcode",
                                "official_url": dataset.get("url", ""),
                                "stars": dataset.get("stars", 0),
                                "is_trending": True
                            })
                            
        except Exception as e:
            logger.error(f"Error scraping trending benchmarks: {str(e)}")
        
        logger.info(f"Found {len(benchmarks)} trending benchmarks")
        
        return {"benchmarks": benchmarks}
    
    async def _scrape_evaluation_tables(self) -> Dict:
        """
        Scrape general evaluation/comparison tables
        """
        logger.info("Scraping evaluation tables...")
        
        # This would involve scraping pages that contain comparison tables
        # For now, return empty result as this requires more complex logic
        
        return {
            "models": [],
            "leaderboard": {"entries": [], "headers": []},
            "benchmarks": []
        }
    
    def _clean_model_name(self, name: str) -> str:
        """
        Clean and standardize model names
        """
        # Remove common prefixes/suffixes
        name = re.sub(r'^(the\s+)?', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*\([^)]*\)$', '', name)  # Remove trailing parentheses
        name = re.sub(r'\s*\[[^\]]*\]$', '', name)  # Remove trailing brackets
        
        # Clean up whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def _clean_metric_name(self, name: str) -> str:
        """
        Clean and standardize metric names
        """
        # Remove common suffixes
        name = re.sub(r'\s*\([^)]*\)$', '', name)
        name = re.sub(r'\s*%$', '', name)
        
        # Clean up whitespace and make consistent
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Convert to title case
        name = name.title()
        
        return name
    
    def _deduplicate_data(self, data: Dict) -> Dict:
        """
        Remove duplicate entries
        """
        # Deduplicate models by name
        seen_models = set()
        unique_models = []
        
        for model in data["models"]:
            model_name = model["name"]
            if model_name not in seen_models:
                seen_models.add(model_name)
                unique_models.append(model)
        
        data["models"] = unique_models
        
        # Deduplicate benchmarks by name
        seen_benchmarks = set()
        unique_benchmarks = []
        
        for benchmark in data["benchmarks"]:
            benchmark_name = benchmark["name"]
            if benchmark_name not in seen_benchmarks:
                seen_benchmarks.add(benchmark_name)
                unique_benchmarks.append(benchmark)
        
        data["benchmarks"] = unique_benchmarks
        
        # Deduplicate leaderboard entries by model name
        seen_entries = set()
        unique_entries = []
        
        for entry in data["leaderboard"]["entries"]:
            model_name = entry["model"]
            if model_name not in seen_entries:
                seen_entries.add(model_name)
                unique_entries.append(entry)
        
        data["leaderboard"]["entries"] = unique_entries
        
        # Deduplicate headers
        data["leaderboard"]["headers"] = list(set(data["leaderboard"]["headers"]))
        
        return data