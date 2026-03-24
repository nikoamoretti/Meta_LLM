"""
Comprehensive HuggingFace Hub Scraper
Monitors models, spaces, and CSV feeds for exhaustive coverage
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import json
import csv
from io import StringIO
import re

logger = logging.getLogger(__name__)

class HuggingFaceHubScraper:
    """
    Comprehensive scraper for HuggingFace Hub data sources:
    1. Model Hub API (text-generation models)
    2. Spaces API (leaderboard-tagged spaces)
    3. CSV datasets (Open-LLM leaderboard, etc.)
    """
    
    def __init__(self):
        self.base_url = "https://huggingface.co"
        self.api_url = "https://huggingface.co/api"
        self.session = None
        
        # Known leaderboard CSV sources
        self.csv_sources = [
            "https://huggingface.co/datasets/open-llm-leaderboard/contents/main/requests/results_2024-12-06T00-00-00.000Z.json",
            "https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard/raw/main/src/leaderboard/read_evals.py"
        ]
        
    async def scrape_async(self) -> Dict:
        """
        Main async scraping method
        """
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            # Scrape all HF sources in parallel
            tasks = [
                self._scrape_model_hub(),
                self._scrape_leaderboard_spaces(),
                self._scrape_csv_datasets(),
                self._discover_new_leaderboards()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            combined_data = {
                "models": [],
                "leaderboard": {"entries": [], "headers": []},
                "spaces": [],
                "metadata": {
                    "source": "huggingface_hub",
                    "scraped_at": datetime.utcnow().isoformat(),
                    "total_sources": len(tasks)
                }
            }
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"HF scraping task {i} failed: {str(result)}")
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
                    
                    # Merge spaces
                    if "spaces" in result:
                        combined_data["spaces"].extend(result["spaces"])
            
            # Deduplicate
            combined_data = self._deduplicate_data(combined_data)
            
            logger.info(f"HuggingFace Hub scraping complete: {len(combined_data['models'])} models, "
                       f"{len(combined_data['leaderboard']['entries'])} leaderboard entries")
            
            return combined_data
    
    async def _scrape_model_hub(self) -> Dict:
        """
        Scrape HuggingFace Model Hub for text-generation models
        """
        logger.info("Scraping HuggingFace Model Hub...")
        
        models = []
        page = 0
        per_page = 100
        
        while True:
            try:
                # Get models with text-generation tag
                url = f"{self.api_url}/models"
                params = {
                    "pipeline_tag": "text-generation",
                    "limit": per_page,
                    "skip": page * per_page,
                    "sort": "downloads",
                    "direction": "-1"
                }
                
                async with self.session.get(url, params=params) as response:
                    if response.status != 200:
                        break
                    
                    data = await response.json()
                    
                    if not data:
                        break
                    
                    for model in data:
                        try:
                            model_data = {
                                "name": model["id"],
                                "metadata": {
                                    "provider": "HuggingFace",
                                    "huggingface_id": model["id"],
                                    "downloads": model.get("downloads", 0),
                                    "likes": model.get("likes", 0),
                                    "created_at": model.get("createdAt"),
                                    "last_modified": model.get("lastModified"),
                                    "license": self._extract_license(model),
                                    "params_b": self._extract_parameter_count(model),
                                    "tags": model.get("tags", []),
                                    "official_url": f"https://huggingface.co/{model['id']}"
                                }
                            }
                            models.append(model_data)
                            
                        except Exception as e:
                            logger.warning(f"Failed to process model {model.get('id', 'unknown')}: {str(e)}")
                    
                    page += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
                    # Stop if we got less than a full page
                    if len(data) < per_page:
                        break
                        
                    # Safety limit
                    if page > 100:  # Max 10,000 models
                        break
                        
            except Exception as e:
                logger.error(f"Error scraping HF models page {page}: {str(e)}")
                break
        
        logger.info(f"Found {len(models)} models from HuggingFace Hub")
        
        return {"models": models}
    
    async def _scrape_leaderboard_spaces(self) -> Dict:
        """
        Scrape HuggingFace Spaces tagged with 'leaderboard'
        """
        logger.info("Scraping HuggingFace Spaces for leaderboards...")
        
        spaces = []
        leaderboard_entries = []
        headers = set()
        
        try:
            # Get spaces with leaderboard tag
            url = f"{self.api_url}/spaces"
            params = {
                "search": "leaderboard",
                "limit": 100,
                "sort": "trending"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for space in data:
                        space_id = space["id"]
                        
                        # Try to extract leaderboard data from space
                        try:
                            space_data = await self._scrape_space_leaderboard(space_id)
                            if space_data:
                                spaces.append({
                                    "space_id": space_id,
                                    "name": space.get("title", space_id),
                                    "author": space.get("author"),
                                    "likes": space.get("likes", 0),
                                    "models": space_data.get("models", []),
                                    "url": f"https://huggingface.co/spaces/{space_id}"
                                })
                                
                                # Extract leaderboard entries
                                if "leaderboard" in space_data:
                                    leaderboard_entries.extend(space_data["leaderboard"]["entries"])
                                    headers.update(space_data["leaderboard"]["headers"])
                                    
                        except Exception as e:
                            logger.debug(f"Could not extract data from space {space_id}: {str(e)}")
                            continue
                        
                        # Rate limiting
                        await asyncio.sleep(0.2)
                        
        except Exception as e:
            logger.error(f"Error scraping HF spaces: {str(e)}")
        
        logger.info(f"Found {len(spaces)} leaderboard spaces, {len(leaderboard_entries)} entries")
        
        return {
            "spaces": spaces,
            "leaderboard": {
                "entries": leaderboard_entries,
                "headers": list(headers)
            }
        }
    
    async def _scrape_space_leaderboard(self, space_id: str) -> Optional[Dict]:
        """
        Try to extract leaderboard data from a specific space
        """
        try:
            # Try common leaderboard file locations
            endpoints_to_try = [
                f"https://huggingface.co/spaces/{space_id}/raw/main/leaderboard.json",
                f"https://huggingface.co/spaces/{space_id}/raw/main/data.json",
                f"https://huggingface.co/spaces/{space_id}/raw/main/results.json",
                f"https://huggingface.co/spaces/{space_id}/raw/main/leaderboard.csv"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    async with self.session.get(endpoint) as response:
                        if response.status == 200:
                            content_type = response.headers.get('content-type', '')
                            
                            if 'json' in content_type:
                                data = await response.json()
                                return self._parse_space_json_data(data, space_id)
                            elif 'csv' in content_type or endpoint.endswith('.csv'):
                                text = await response.text()
                                return self._parse_space_csv_data(text, space_id)
                                
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Error scraping space {space_id}: {str(e)}")
            return None
    
    def _parse_space_json_data(self, data: Dict, space_id: str) -> Dict:
        """
        Parse JSON data from a leaderboard space
        """
        result = {"models": [], "leaderboard": {"entries": [], "headers": []}}
        
        # Handle different JSON structures
        if isinstance(data, list):
            # List of model entries
            for entry in data:
                if isinstance(entry, dict) and "model" in entry:
                    model_name = entry["model"]
                    result["models"].append({"name": model_name})
                    
                    # Extract scores
                    scores = {}
                    for key, value in entry.items():
                        if key != "model" and isinstance(value, (int, float)):
                            scores[key] = value
                            result["leaderboard"]["headers"].append(key)
                    
                    if scores:
                        result["leaderboard"]["entries"].append({
                            "model": model_name,
                            "scores": scores
                        })
        
        elif isinstance(data, dict):
            # Dictionary structure
            if "leaderboard" in data or "results" in data:
                leaderboard_data = data.get("leaderboard", data.get("results", []))
                if isinstance(leaderboard_data, list):
                    for entry in leaderboard_data:
                        if isinstance(entry, dict) and any(k in entry for k in ["model", "Model", "name"]):
                            model_key = next((k for k in ["model", "Model", "name"] if k in entry), None)
                            if model_key:
                                model_name = entry[model_key]
                                result["models"].append({"name": model_name})
                                
                                scores = {}
                                for key, value in entry.items():
                                    if key != model_key and isinstance(value, (int, float)):
                                        scores[key] = value
                                        result["leaderboard"]["headers"].append(key)
                                
                                if scores:
                                    result["leaderboard"]["entries"].append({
                                        "model": model_name,
                                        "scores": scores
                                    })
        
        result["leaderboard"]["headers"] = list(set(result["leaderboard"]["headers"]))
        return result
    
    def _parse_space_csv_data(self, csv_text: str, space_id: str) -> Dict:
        """
        Parse CSV data from a leaderboard space
        """
        result = {"models": [], "leaderboard": {"entries": [], "headers": []}}
        
        try:
            reader = csv.DictReader(StringIO(csv_text))
            headers = reader.fieldnames or []
            
            # Find model column
            model_col = None
            for col in headers:
                if col.lower() in ["model", "name", "model_name"]:
                    model_col = col
                    break
            
            if not model_col:
                return result
            
            # Extract numeric columns as benchmark headers
            numeric_headers = []
            for header in headers:
                if header != model_col:
                    numeric_headers.append(header)
            
            result["leaderboard"]["headers"] = numeric_headers
            
            # Process rows
            for row in reader:
                model_name = row.get(model_col)
                if model_name:
                    result["models"].append({"name": model_name})
                    
                    scores = {}
                    for header in numeric_headers:
                        try:
                            value = float(row.get(header, 0))
                            scores[header] = value
                        except (ValueError, TypeError):
                            continue
                    
                    if scores:
                        result["leaderboard"]["entries"].append({
                            "model": model_name,
                            "scores": scores
                        })
            
        except Exception as e:
            logger.debug(f"Error parsing CSV from {space_id}: {str(e)}")
        
        return result
    
    async def _scrape_csv_datasets(self) -> Dict:
        """
        Scrape known CSV dataset sources
        """
        logger.info("Scraping HuggingFace CSV datasets...")
        
        all_entries = []
        all_headers = set()
        
        # Open LLM Leaderboard - try to get latest results
        try:
            # First try to get the dynamic leaderboard data
            url = "https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard"
            
            # Try the API endpoint that powers the leaderboard
            api_url = "https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard/api/predict"
            
            # This is a more complex extraction that would require understanding
            # the gradio interface - for now, use a simplified approach
            
            # Try to access raw data files if available
            raw_data_urls = [
                "https://huggingface.co/datasets/open-llm-leaderboard/open_llm_leaderboard/raw/main/data.json",
                "https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard/raw/main/src/backend/envs.py"
            ]
            
            for data_url in raw_data_urls:
                try:
                    async with self.session.get(data_url) as response:
                        if response.status == 200 and 'json' in response.headers.get('content-type', ''):
                            data = await response.json()
                            parsed = self._parse_open_llm_data(data)
                            if parsed:
                                all_entries.extend(parsed["entries"])
                                all_headers.update(parsed["headers"])
                                break
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Could not scrape Open LLM Leaderboard: {str(e)}")
        
        logger.info(f"Found {len(all_entries)} entries from CSV datasets")
        
        return {
            "leaderboard": {
                "entries": all_entries,
                "headers": list(all_headers)
            }
        }
    
    def _parse_open_llm_data(self, data: Dict) -> Optional[Dict]:
        """
        Parse Open LLM Leaderboard data format
        """
        if not isinstance(data, (list, dict)):
            return None
        
        entries = []
        headers = set()
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # Look for model identifier
                    model_name = None
                    for key in ["model", "Model", "model_name", "name"]:
                        if key in item:
                            model_name = item[key]
                            break
                    
                    if model_name:
                        scores = {}
                        for key, value in item.items():
                            if key not in ["model", "Model", "model_name", "name"] and isinstance(value, (int, float)):
                                scores[key] = value
                                headers.add(key)
                        
                        if scores:
                            entries.append({
                                "model": model_name,
                                "scores": scores
                            })
        
        return {
            "entries": entries,
            "headers": list(headers)
        } if entries else None
    
    async def _discover_new_leaderboards(self) -> Dict:
        """
        Discover new leaderboards by searching for trending spaces
        """
        logger.info("Discovering new leaderboards...")
        
        discovered = []
        
        try:
            # Search for spaces with keywords that suggest leaderboards
            search_terms = ["benchmark", "eval", "evaluation", "ranking", "competition"]
            
            for term in search_terms:
                try:
                    url = f"{self.api_url}/spaces"
                    params = {
                        "search": term,
                        "limit": 20,
                        "sort": "trending"
                    }
                    
                    async with self.session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for space in data:
                                space_id = space["id"]
                                
                                # Check if this looks like a leaderboard
                                if self._is_likely_leaderboard(space):
                                    discovered.append({
                                        "space_id": space_id,
                                        "name": space.get("title", space_id),
                                        "discovery_term": term,
                                        "likes": space.get("likes", 0),
                                        "url": f"https://huggingface.co/spaces/{space_id}"
                                    })
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.debug(f"Error searching for '{term}': {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in leaderboard discovery: {str(e)}")
        
        logger.info(f"Discovered {len(discovered)} potential new leaderboards")
        
        return {"discovered_leaderboards": discovered}
    
    def _is_likely_leaderboard(self, space: Dict) -> bool:
        """
        Heuristic to determine if a space is likely a leaderboard
        """
        title = space.get("title", "").lower()
        space_id = space["id"].lower()
        
        # Positive indicators
        positive_terms = [
            "leaderboard", "ranking", "benchmark", "eval", "competition",
            "arena", "comparison", "performance", "sota"
        ]
        
        # Negative indicators (exclude these)
        negative_terms = [
            "demo", "playground", "chat", "generator", "creator"
        ]
        
        # Check positive terms
        has_positive = any(term in title or term in space_id for term in positive_terms)
        
        # Check negative terms
        has_negative = any(term in title or term in space_id for term in negative_terms)
        
        return has_positive and not has_negative
    
    def _extract_license(self, model_data: Dict) -> Optional[str]:
        """
        Extract license information from model data
        """
        # Check model card info
        if "cardData" in model_data:
            card_data = model_data["cardData"]
            if isinstance(card_data, dict) and "license" in card_data:
                return card_data["license"]
        
        # Check tags
        tags = model_data.get("tags", [])
        for tag in tags:
            if isinstance(tag, str) and ("license:" in tag or "apache" in tag.lower() or "mit" in tag.lower()):
                return tag.replace("license:", "").strip()
        
        return None
    
    def _extract_parameter_count(self, model_data: Dict) -> Optional[float]:
        """
        Extract parameter count from model data
        """
        model_id = model_data.get("id", "")
        
        # Common patterns in model names
        patterns = [
            r"(\d+\.?\d*)b",  # 7b, 13b, 70b
            r"(\d+\.?\d*)B",  # 7B, 13B, 70B
            r"(\d+\.?\d*)-?billion",
            r"(\d+\.?\d*)-?B"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, model_id)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _deduplicate_data(self, data: Dict) -> Dict:
        """
        Remove duplicate models and leaderboard entries
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