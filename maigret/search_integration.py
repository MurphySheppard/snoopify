"""
Enhanced Search Integration Layer
Integrates smart search features with core Maigret search engine
"""

import asyncio
import logging
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import difflib

from .smart_search_engine import (
    SmartSearchEngine, UsernameVariantGenerator,
    SmartMatcher, SearchResult, RelationshipMapper
)
from .smart_search_config import ConfigManager, PerformanceConfig

logger = logging.getLogger(__name__)


class ResultConfidence(Enum):
    """Result confidence levels"""
    VERIFIED = 100
    VERY_HIGH = 95
    HIGH = 85
    MEDIUM = 70
    LOW = 50
    UNVERIFIED = 0


@dataclass
class EnrichedSearchResult:
    """Enhanced search result with relationships and confidence"""
    username: str
    site: str
    url: str
    found: bool
    confidence: float
    verified: bool = False
    account_metadata: Dict = field(default_factory=dict)
    related_accounts: List[str] = field(default_factory=list)
    extraction_tags: List[str] = field(default_factory=list)
    risk_level: str = "unknown"
    last_updated: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'username': self.username,
            'site': self.site,
            'url': self.url,
            'found': self.found,
            'confidence': self.confidence,
            'verified': self.verified,
            'account_metadata': self.account_metadata,
            'related_accounts': self.related_accounts,
            'extraction_tags': self.extraction_tags,
            'risk_level': self.risk_level,
            'last_updated': self.last_updated
        }


class SearchResultProcessor:
    """Process and enrich search results"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager.get_config()
        self.filtering_config = config_manager.get_filtering_config()
    
    def filter_results(self, results: List[EnrichedSearchResult]) -> List[EnrichedSearchResult]:
        """Filter results based on configuration"""
        if not self.filtering_config.enabled:
            return results
        
        filtered = results
        
        # Filter by confidence threshold
        if self.filtering_config.filter_low_confidence:
            filtered = [r for r in filtered 
                       if r.confidence >= self.filtering_config.confidence_threshold]
        
        # Deduplicate
        if self.filtering_config.deduplicate_results:
            filtered = self._deduplicate(filtered)
        
        # Remove false positives
        if self.filtering_config.remove_false_positives:
            filtered = self._remove_false_positives(filtered)
        
        return filtered
    
    def _deduplicate(self, results: List[EnrichedSearchResult]) -> List[EnrichedSearchResult]:
        """Remove duplicate results"""
        seen = set()
        deduplicated = []
        
        for result in results:
            key = (result.username.lower(), result.site.lower(), result.url)
            if key not in seen:
                seen.add(key)
                deduplicated.append(result)
        
        return deduplicated
    
    def _remove_false_positives(self, results: List[EnrichedSearchResult]) -> List[EnrichedSearchResult]:
        """Remove likely false positives"""
        filtered = []
        
        for result in results:
            # Keep if found and has sufficient metadata
            if result.found:
                metadata_count = len([v for v in result.account_metadata.values() if v])
                if metadata_count >= self.filtering_config.min_metadata_fields or result.verified:
                    filtered.append(result)
            elif result.confidence >= 90:
                # Very high confidence even if not found
                filtered.append(result)
        
        return filtered
    
    def enrich_result(self, result: EnrichedSearchResult, 
                     additional_data: Dict) -> EnrichedSearchResult:
        """Enrich result with additional data"""
        result.account_metadata.update(additional_data)
        
        # Update risk level based on metadata
        result.risk_level = self._assess_risk(result)
        
        return result
    
    def _assess_risk(self, result: EnrichedSearchResult) -> str:
        """Assess risk level based on result data"""
        if not result.found:
            return "not_found"
        
        # Check for risk indicators
        risk_score = 0
        
        # High visibility
        if result.account_metadata.get('followers', 0) > 10000:
            risk_score += 20
        
        # Verified account
        if result.verified:
            risk_score += 10
        
        # Recent activity
        if result.account_metadata.get('last_activity_recent'):
            risk_score += 15
        
        # Multiple related accounts
        if len(result.related_accounts) > 3:
            risk_score += 15
        
        if risk_score >= 60:
            return "critical"
        elif risk_score >= 40:
            return "high"
        elif risk_score >= 20:
            return "medium"
        else:
            return "low"


class RecursiveSearchCoordinator:
    """Coordinate recursive searches across discovered identifiers"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager.get_config()
        self.recursion_config = config_manager.get_recursion_config()
        self.search_history: Set[str] = set()
        self.logger = logging.getLogger(__name__)
    
    async def coordinate_recursive_search(
        self,
        initial_username: str,
        search_function,
        sites: Optional[List[str]] = None,
        current_depth: int = 0
    ) -> Dict:
        """Coordinate recursive searching"""
        
        if not self.recursion_config.enabled:
            return await search_function(initial_username, sites)
        
        if current_depth >= self.recursion_config.max_depth:
            self.logger.info(f"Max recursion depth reached: {current_depth}")
            return {}
        
        # Check if already searched
        search_key = f"{initial_username}_{current_depth}"
        if search_key in self.search_history:
            self.logger.debug(f"Already searched: {search_key}")
            return {}
        
        self.search_history.add(search_key)
        
        # Perform search
        results = await search_function(initial_username, sites)
        
        # Extract new identifiers for recursive search
        if current_depth < self.recursion_config.max_depth - 1:
            new_identifiers = self._extract_identifiers(results)
            
            # Search for new identifiers
            for identifier in new_identifiers:
                if identifier not in self.search_history:
                    self.logger.info(f"Recursive search for: {identifier}")
                    recursive_results = await self.coordinate_recursive_search(
                        identifier,
                        search_function,
                        sites,
                        current_depth + 1
                    )
                    results.update(recursive_results)
        
        return results
    
    def _extract_identifiers(self, results: Dict) -> List[str]:
        """Extract identifiers from results for recursive search"""
        identifiers = set()
        
        for result_list in results.values():
            if isinstance(result_list, list):
                for result in result_list:
                    if isinstance(result, dict):
                        # Extract emails
                        if self.recursion_config.extract_emails:
                            if 'email' in result and result['email']:
                                email_parts = result['email'].split('@')[0]
                                identifiers.add(email_parts)
                        
                        # Extract usernames
                        if self.recursion_config.extract_usernames:
                            if 'username' in result and result['username']:
                                identifiers.add(result['username'])
                        
                        # Extract IDs
                        if self.recursion_config.extract_ids:
                            if 'user_id' in result and result['user_id']:
                                identifiers.add(str(result['user_id']))
        
        return list(identifiers)


class EnhancedSearchHandler:
    """Main handler for enhanced search operations"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize enhanced search handler"""
        self.config_manager = ConfigManager(config_path)
        self.smart_engine = SmartSearchEngine(config_path)
        self.result_processor = SearchResultProcessor(self.config_manager)
        self.recursive_coordinator = RecursiveSearchCoordinator(self.config_manager)
        self.matcher = SmartMatcher()
        self.relationship_mapper = RelationshipMapper()
        self.logger = logging.getLogger(__name__)
        self.results_cache: Dict[str, List[EnrichedSearchResult]] = {}
    
    async def enhanced_search(
        self,
        username: str,
        search_function,
        sites: Optional[List[str]] = None,
        use_variants: bool = True,
        recursive: bool = True,
        use_cache: bool = True
    ) -> Dict:
        """
        Perform enhanced search with all smart features
        
        Args:
            username: Target username
            search_function: Async function to perform actual search
            sites: Sites to search
            use_variants: Enable variant generation
            recursive: Enable recursive searching
            use_cache: Use result caching
        
        Returns:
            Dictionary of enhanced search results
        """
        
        # Check cache
        cache_key = f"{username}:{','.join(sites or [])}"
        if use_cache and cache_key in self.results_cache:
            self.logger.info(f"Using cached results for: {username}")
            return {'results': self.results_cache[cache_key]}
        
        self.logger.info(f"Starting enhanced search for: {username}")
        
        all_results = []
        
        # Generate variants if enabled
        search_terms = [username]
        if use_variants:
            search_config = self.config_manager.get_search_config()
            if search_config.enabled:
                variants = UsernameVariantGenerator.generate_variants(
                    username,
                    max_variants=search_config.max_variants
                )
                search_terms.extend(variants)
                self.logger.info(f"Generated {len(variants)} variants")
        
        # Perform searches
        for term in search_terms:
            try:
                if recursive:
                    results = await self.recursive_coordinator.coordinate_recursive_search(
                        term,
                        search_function,
                        sites
                    )
                else:
                    results = await search_function(term, sites)
                
                # Process results
                enriched = self._process_search_results(term, results)
                all_results.extend(enriched)
            
            except Exception as e:
                self.logger.error(f"Error searching for {term}: {e}")
                continue
        
        # Filter results
        filtered_results = self.result_processor.filter_results(all_results)
        
        # Extract relationships
        relationships = self.relationship_mapper.extract_relationships(
            [SearchResult(
                username=r.username,
                site=r.site,
                url=r.url,
                confidence_score=r.confidence,
                found=r.found,
                is_verified=r.verified,
                metadata=r.account_metadata
            ) for r in filtered_results]
        )
        
        # Cache results
        if use_cache:
            self.results_cache[cache_key] = filtered_results
        
        return {
            'results': filtered_results,
            'relationships': relationships,
            'total_found': len([r for r in filtered_results if r.found]),
            'verified_accounts': len([r for r in filtered_results if r.verified]),
            'average_confidence': sum(r.confidence for r in filtered_results) / len(filtered_results) if filtered_results else 0
        }
    
    def _process_search_results(self, search_term: str, 
                                results: Dict) -> List[EnrichedSearchResult]:
        """Process raw search results into enriched format"""
        enriched = []
        
        for site, site_results in results.items():
            if isinstance(site_results, list):
                for result in site_results:
                    if isinstance(result, dict):
                        confidence = self.matcher.calculate_confidence(
                            search_term,
                            result.get('username', search_term)
                        )
                        
                        enriched_result = EnrichedSearchResult(
                            username=result.get('username', search_term),
                            site=site,
                            url=result.get('url', ''),
                            found=result.get('found', False),
                            confidence=confidence,
                            verified=result.get('verified', False),
                            account_metadata=result.get('metadata', {})
                        )
                        
                        enriched.append(enriched_result)
        
        return enriched
    
    def clear_cache(self) -> None:
        """Clear results cache"""
        self.results_cache.clear()
        self.logger.info("Results cache cleared")
    
    def get_cache_size(self) -> int:
        """Get current cache size"""
        return len(self.results_cache)


# Export classes
__all__ = [
    'EnhancedSearchHandler',
    'SearchResultProcessor',
    'RecursiveSearchCoordinator',
    'EnrichedSearchResult',
    'ResultConfidence'
]
