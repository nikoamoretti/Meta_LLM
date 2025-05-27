"""
Base scraper class with common functionality
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a session with retry logic"""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    @abstractmethod
    def scrape(self) -> List[Dict]:
        """Scrape the leaderboard and return results"""
        pass
    
    def validate_results(self, results: List[Dict]) -> List[Dict]:
        """Validate and clean scraped results"""
        validated = []
        for result in results:
            if self._is_valid_result(result):
                validated.append(result)
            else:
                logger.warning(f"Invalid result from {self.name}: {result}")
        return validated
    
    def _is_valid_result(self, result: Dict) -> bool:
        """Check if a result is valid"""
        return (
            'model' in result and 
            'scores' in result and 
            isinstance(result['scores'], dict) and
            len(result['scores']) > 0
        )
