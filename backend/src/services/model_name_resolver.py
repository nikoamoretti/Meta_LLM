"""
Model Name Resolver Service
Handles model name normalization, fuzzy matching, and alias resolution
"""

import sqlite3
import re
from typing import Optional, List, Dict, Tuple
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)

class ModelNameResolver:
    """Centralized service for resolving model name variations to canonical names"""
    
    def __init__(self, db_path: str = "meta_llm.db"):
        self.db_path = db_path
        self._cache = {}  # Cache for resolved names
        self._load_aliases()
    
    def _load_aliases(self):
        """Load all aliases into memory for fast lookup"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load all aliases
            cursor.execute("""
                SELECT alias, canonical_name, confidence_score 
                FROM model_aliases 
                ORDER BY confidence_score DESC
            """)
            
            self.aliases = {}
            for alias, canonical_name, confidence in cursor.fetchall():
                self.aliases[alias] = (canonical_name, confidence)
                # Also store lowercase version for case-insensitive matching
                self.aliases[alias.lower()] = (canonical_name, confidence)
            
            # Load canonical models
            cursor.execute("SELECT canonical_name FROM canonical_models")
            self.canonical_models = {row[0] for row in cursor.fetchall()}
            
            conn.close()
            logger.info(f"Loaded {len(self.aliases)} aliases for {len(self.canonical_models)} canonical models")
            
        except Exception as e:
            logger.error(f"Failed to load aliases: {e}")
            self.aliases = {}
            self.canonical_models = set()
    
    def resolve(self, raw_name: str, threshold: float = 0.85) -> str:
        """
        Resolve a raw model name to its canonical form
        
        Args:
            raw_name: The raw model name to resolve
            threshold: Minimum similarity score for fuzzy matching (0.0-1.0)
            
        Returns:
            The canonical model name
        """
        if not raw_name:
            return raw_name
        
        # Check cache first
        if raw_name in self._cache:
            return self._cache[raw_name]
        
        # 1. Exact match in aliases
        if raw_name in self.aliases:
            canonical_name = self.aliases[raw_name][0]
            self._cache[raw_name] = canonical_name
            return canonical_name
        
        # 2. Case-insensitive match
        if raw_name.lower() in self.aliases:
            canonical_name = self.aliases[raw_name.lower()][0]
            self._cache[raw_name] = canonical_name
            return canonical_name
        
        # 3. Normalized match (remove spaces, hyphens, underscores)
        normalized = self._normalize_for_matching(raw_name)
        for alias, (canonical_name, _) in self.aliases.items():
            if self._normalize_for_matching(alias) == normalized:
                self._cache[raw_name] = canonical_name
                return canonical_name
        
        # 4. Fuzzy matching
        best_match = self._fuzzy_match(raw_name, threshold)
        if best_match:
            self._cache[raw_name] = best_match
            # Also add this as a new alias for future use
            self._add_alias(raw_name, best_match, source='fuzzy_match', confidence=threshold)
            return best_match
        
        # 5. Pattern matching for known formats
        pattern_match = self._pattern_match(raw_name)
        if pattern_match:
            self._cache[raw_name] = pattern_match
            self._add_alias(raw_name, pattern_match, source='pattern_match', confidence=0.9)
            return pattern_match
        
        # 6. If no match found, check if it's already canonical
        if raw_name in self.canonical_models:
            return raw_name
        
        # 7. Create new canonical model (or return as-is for now)
        logger.warning(f"No match found for model name: {raw_name}")
        self._cache[raw_name] = raw_name
        return raw_name
    
    def _normalize_for_matching(self, name: str) -> str:
        """Normalize name for matching by removing spaces, hyphens, underscores, and lowercasing"""
        return re.sub(r'[\s\-_]+', '', name.lower())
    
    def _fuzzy_match(self, raw_name: str, threshold: float) -> Optional[str]:
        """Find the best fuzzy match for a model name"""
        best_score = 0
        best_match = None
        
        # Try matching against all canonical models
        for canonical_name in self.canonical_models:
            # Compare normalized versions
            score = SequenceMatcher(None, 
                                    self._normalize_for_matching(raw_name),
                                    self._normalize_for_matching(canonical_name)).ratio()
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = canonical_name
        
        # Also try matching against all aliases
        for alias, (canonical_name, _) in self.aliases.items():
            score = SequenceMatcher(None, 
                                    self._normalize_for_matching(raw_name),
                                    self._normalize_for_matching(alias)).ratio()
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = canonical_name
        
        if best_match:
            logger.info(f"Fuzzy matched '{raw_name}' to '{best_match}' with score {best_score:.2f}")
        
        return best_match
    
    def _pattern_match(self, raw_name: str) -> Optional[str]:
        """Match known patterns in model names"""
        patterns = [
            # GPT patterns
            (r'^gpt[\s\-_]?4\.1', 'GPT 4.1'),
            (r'^gpt[\s\-_]?4(?![\.\d])', 'GPT-4'),  # GPT-4 but not GPT-4.1
            (r'^gpt[\s\-_]?4o', 'GPT-4o'),
            
            # Claude patterns
            (r'claude[\s\-_]?(?:opus[\s\-_]?)?4', 'Claude 4 Opus'),
            (r'claude[\s\-_]?(?:sonnet[\s\-_]?)?4', 'Claude 4 Sonnet'),
            (r'claude[\s\-_]?3\.5[\s\-_]?sonnet', 'Claude 3.5 Sonnet'),
            
            # o3 patterns
            (r'^o3(?:[\s\-_]?mini)?', lambda m: 'o3-mini' if 'mini' in m.group(0).lower() else 'o3'),
        ]
        
        for pattern, replacement in patterns:
            match = re.match(pattern, raw_name, re.IGNORECASE)
            if match:
                if callable(replacement):
                    return replacement(match)
                return replacement
        
        return None
    
    def _add_alias(self, alias: str, canonical_name: str, source: str = 'auto', confidence: float = 0.9):
        """Add a new alias to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR IGNORE INTO model_aliases (canonical_name, alias, source, confidence_score)
                VALUES (?, ?, ?, ?)
            """, (canonical_name, alias, source, confidence))
            
            conn.commit()
            conn.close()
            
            # Update cache
            self.aliases[alias] = (canonical_name, confidence)
            self.aliases[alias.lower()] = (canonical_name, confidence)
            
            logger.info(f"Added new alias: '{alias}' -> '{canonical_name}' (confidence: {confidence})")
            
        except Exception as e:
            logger.error(f"Failed to add alias: {e}")
    
    def get_all_aliases(self, canonical_name: str) -> List[str]:
        """Get all aliases for a canonical model name"""
        aliases = []
        for alias, (canon_name, _) in self.aliases.items():
            if canon_name == canonical_name and alias != alias.lower():  # Avoid duplicates
                aliases.append(alias)
        return sorted(set(aliases))
    
    def get_canonical_models(self) -> List[str]:
        """Get all canonical model names"""
        return sorted(self.canonical_models)
    
    def resolve_batch(self, names: List[str]) -> Dict[str, str]:
        """Resolve multiple names at once"""
        return {name: self.resolve(name) for name in names}
    
    def add_canonical_model(self, canonical_name: str, model_family: str = None, organization: str = None):
        """Add a new canonical model"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR IGNORE INTO canonical_models (canonical_name, model_family, organization)
                VALUES (?, ?, ?)
            """, (canonical_name, model_family, organization))
            
            conn.commit()
            conn.close()
            
            self.canonical_models.add(canonical_name)
            logger.info(f"Added new canonical model: {canonical_name}")
            
        except Exception as e:
            logger.error(f"Failed to add canonical model: {e}")

# Global instance for convenience
_resolver = None

def get_resolver() -> ModelNameResolver:
    """Get the global resolver instance"""
    global _resolver
    if _resolver is None:
        _resolver = ModelNameResolver()
    return _resolver

def resolve_model_name(raw_name: str) -> str:
    """Convenience function to resolve a model name"""
    return get_resolver().resolve(raw_name)

if __name__ == "__main__":
    # Test the resolver
    resolver = ModelNameResolver()
    
    test_names = [
        "gpt-4.1",
        "GPT 4.1",
        "claude-opus-4-20250514",
        "Claude 4 Opus",
        "o3 (high)",
        "o3-mini",
        "gpt-4",
        "GPT 4",  # Should resolve to GPT-4, not GPT 4.1
        "chatgpt-4o-latest",
        "claude-3-5-sonnet-20241022"
    ]
    
    print("Testing Model Name Resolver:")
    print("=" * 60)
    for name in test_names:
        resolved = resolver.resolve(name)
        print(f"{name:30} -> {resolved}")
    
    print("\n\nAliases for 'GPT 4.1':")
    for alias in resolver.get_all_aliases('GPT 4.1'):
        print(f"  - {alias}")