"""
Enhanced search module for Snoopify with smart matching and wider coverage.
Provides advanced intelligence gathering capabilities beyond basic username search.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum
import difflib
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence scoring for matches"""
    VERY_HIGH = 95
    HIGH = 85
    MEDIUM = 70
    LOW = 50
    VERY_LOW = 30


@dataclass
class SearchResult:
    """Enhanced search result with metadata"""
    username: str
    site: str
    url: str
    confidence_score: float
    found: bool
    account_age: Optional[str] = None
    followers: Optional[int] = None
    is_verified: bool = False
    metadata: Dict = None
    links: List[str] = None
    
    def to_dict(self):
        return {
            'username': self.username,
            'site': self.site,
            'url': self.url,
            'confidence_score': self.confidence_score,
            'found': self.found,
            'account_age': self.account_age,
            'followers': self.followers,
            'is_verified': self.is_verified,
            'metadata': self.metadata or {},
            'links': self.links or []
        }


class UsernameVariantGenerator:
    """Generate intelligent username variants for fuzzy matching"""
    
    @staticmethod
    def generate_variants(username: str, max_variants: int = 50) -> List[str]:
        """Generate common username variations"""
        variants = set([username])
        
        # Case variations
        variants.add(username.lower())
        variants.add(username.upper())
        variants.add(username.title())
        
        # Separator variations
        if '_' in username:
            variants.add(username.replace('_', ''))
            variants.add(username.replace('_', '-'))
            variants.add(username.replace('_', '.'))
        
        if '-' in username:
            variants.add(username.replace('-', ''))
            variants.add(username.replace('-', '_'))
            variants.add(username.replace('-', '.'))
        
        if '.' in username:
            variants.add(username.replace('.', ''))
            variants.add(username.replace('.', '_'))
            variants.add(username.replace('.', '-'))
        
        # Number suffix variations
        for i in range(1, 10):
            variants.add(f"{username}{i}")
            variants.add(f"{username}_{i}")
            variants.add(f"{username}{i:02d}")
        
        # Common prefixes/suffixes
        common_additions = ['', '_official', '_real', '_actual', '_admin', '_pro']
        for addition in common_additions:
            if len(username) + len(addition) <= 30:
                variants.add(f"{username}{addition}")
        
        # Phonetic variations (simple)
        phonetic_variants = {
            'i': ['1', 'l', '!'],
            'e': ['3'],
            'a': ['4'],
            's': ['5', '$'],
            'b': ['8'],
            'g': ['9'],
            'o': ['0'],
        }
        
        for char, replacements in phonetic_variants.items():
            for replacement in replacements:
                if char in username.lower():
                    variants.add(username.replace(char, replacement))
                    variants.add(username.replace(char.upper(), replacement))
        
        # Language-specific variations (common patterns)
        # Russian keyboard layout
        if any(c.isalpha() for c in username):
            variants.add(username.lower())
        
        # Take up to max_variants
        return list(variants)[:max_variants]


class SmartMatcher:
    """Intelligent matching with fuzzy logic and confidence scoring"""
    
    @staticmethod
    def calculate_confidence(expected: str, actual: str, 
                            threshold: float = 85) -> float:
        """Calculate match confidence using fuzzy matching"""
        if expected.lower() == actual.lower():
            return 100.0
        
        # Normalize strings
        exp_normalized = ''.join(c.lower() for c in expected if c.isalnum())
        act_normalized = ''.join(c.lower() for c in actual if c.isalnum())
        
        # Calculate similarity
        similarity = difflib.SequenceMatcher(None, exp_normalized, 
                                          act_normalized).ratio() * 100
        
        return similarity
    
    @staticmethod
    def get_confidence_level(score: float) -> ConfidenceLevel:
        """Convert score to confidence level"""
        if score >= ConfidenceLevel.VERY_HIGH.value:
            return ConfidenceLevel.VERY_HIGH
        elif score >= ConfidenceLevel.HIGH.value:
            return ConfidenceLevel.HIGH
        elif score >= ConfidenceLevel.MEDIUM.value:
            return ConfidenceLevel.MEDIUM
        elif score >= ConfidenceLevel.LOW.value:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW


class RelationshipMapper:
    """Map relationships between discovered accounts"""
    
    @staticmethod
    def extract_relationships(results: List[SearchResult]) -> Dict:
        """Extract relationships from search results"""
        relationships = {
            'verified_accounts': [],
            'connected_accounts': [],
            'account_clusters': [],
            'shared_metadata': {}
        }
        
        for result in results:
            if result.is_verified:
                relationships['verified_accounts'].append({
                    'site': result.site,
                    'username': result.username,
                    'confidence': result.confidence_score
                })
            
            if result.metadata:
                for key, value in result.metadata.items():
                    if key not in relationships['shared_metadata']:
                        relationships['shared_metadata'][key] = []
                    relationships['shared_metadata'][key].append(value)
        
        return relationships


class SmartSearchEngine:
    """Enhanced search engine with advanced features"""
    
    def __init__(self, config_path: str = 'config/smart_search_config.json'):
        """Initialize search engine with configuration"""
        self.config = self._load_config(config_path)
        self.results_cache: Dict[str, List[SearchResult]] = {}
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {config_path}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Return default configuration"""
        return {
            'search': {
                'smart_matching': {'enabled': True, 'fuzzy_threshold': 85},
                'recursion': {'enabled': True, 'max_depth': 3},
                'performance': {'parallel_workers': 12}
            }
        }
    
    async def search(self, username: str, sites: Optional[List[str]] = None,
                    use_variants: bool = True, recursive: bool = True) -> List[SearchResult]:
        """
        Perform smart search with variants and recursion
        
        Args:
            username: Target username to search for
            sites: Specific sites to search (None = all)
            use_variants: Enable username variant generation
            recursive: Enable recursive searching
        
        Returns:
            List of search results with confidence scoring
        """
        results = []
        
        # Generate variants if enabled
        search_terms = [username]
        if use_variants and self.config['search']['advanced_filtering']['enabled']:
            search_terms.extend(UsernameVariantGenerator.generate_variants(
                username,
                max_variants=self.config['search']['advanced_search']['max_variants']
            ))
        
        self.logger.info(f"Starting smart search for '{username}' with {len(search_terms)} variants")
        
        # Perform searches (this would integrate with actual Maigret search)
        # Placeholder for integration with main search logic
        
        return results
    
    def rank_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Rank results by confidence score and metadata quality"""
        ranked = sorted(
            results,
            key=lambda r: (r.confidence_score, r.is_verified, 
                          len(r.metadata or {})),
            reverse=True
        )
        return ranked
    
    def extract_intelligence(self, results: List[SearchResult]) -> Dict:
        """Extract actionable intelligence from results"""
        intelligence = {
            'primary_accounts': [],
            'secondary_accounts': [],
            'relationships': RelationshipMapper.extract_relationships(results),
            'confidence_summary': {
                'very_high': len([r for r in results if r.confidence_score >= 95]),
                'high': len([r for r in results if 85 <= r.confidence_score < 95]),
                'medium': len([r for r in results if 70 <= r.confidence_score < 85]),
                'low': len([r for r in results if r.confidence_score < 70])
            },
            'total_verified_accounts': len([r for r in results if r.is_verified]),
            'platforms_found': set([r.site for r in results if r.found])
        }
        
        # Categorize accounts
        for result in sorted(results, key=lambda r: r.confidence_score, reverse=True):
            if result.confidence_score >= 85 and result.found:
                intelligence['primary_accounts'].append(result.to_dict())
            elif result.found:
                intelligence['secondary_accounts'].append(result.to_dict())
        
        return intelligence


# Export main class
__all__ = [
    'SmartSearchEngine',
    'UsernameVariantGenerator',
    'SmartMatcher',
    'RelationshipMapper',
    'SearchResult',
    'ConfidenceLevel'
]
