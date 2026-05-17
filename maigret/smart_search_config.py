"""
Smart Search Configuration Management
Provides flexible, centralized configuration for enhanced search capabilities
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class MatchingStrategy(Enum):
    """Matching strategies for smart search"""
    EXACT = "exact"
    FUZZY = "fuzzy"
    PHONETIC = "phonetic"
    HYBRID = "hybrid"


@dataclass
class SmartMatchingConfig:
    """Configuration for smart matching"""
    enabled: bool = True
    strategy: str = MatchingStrategy.HYBRID.value
    fuzzy_threshold: float = 85.0
    minimum_score: float = 50.0
    phonetic_enabled: bool = True
    case_insensitive: bool = True
    normalize_special_chars: bool = True
    max_distance: int = 2


@dataclass
class AdvancedSearchConfig:
    """Configuration for advanced search features"""
    enabled: bool = True
    max_variants: int = 50
    include_separators: bool = True
    include_phonetic: bool = True
    include_numbers: bool = True
    include_case_variations: bool = True
    number_suffix_range: tuple = field(default_factory=lambda: (1, 10))
    custom_patterns: List[str] = field(default_factory=list)


@dataclass
class AdvancedFilteringConfig:
    """Configuration for result filtering"""
    enabled: bool = True
    filter_low_confidence: bool = True
    confidence_threshold: float = 70.0
    deduplicate_results: bool = True
    group_by_platform: bool = True
    remove_false_positives: bool = True
    min_metadata_fields: int = 2


@dataclass
class RecursionConfig:
    """Configuration for recursive searching"""
    enabled: bool = True
    max_depth: int = 3
    follow_links: bool = True
    extract_emails: bool = True
    extract_usernames: bool = True
    extract_ids: bool = True
    deduplicate_searches: bool = True
    timeout_per_level: int = 300


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization"""
    parallel_workers: int = 12
    request_timeout: int = 30
    batch_size: int = 100
    cache_results: bool = True
    cache_ttl: int = 3600
    rate_limit_delay: float = 0.5
    max_retries: int = 3
    retry_backoff: float = 1.5


@dataclass
class OutputConfig:
    """Configuration for output formatting"""
    format: str = "json"
    include_metadata: bool = True
    include_relationships: bool = True
    include_confidence_scores: bool = True
    detailed_timestamps: bool = True
    export_formats: List[str] = field(default_factory=lambda: ["json", "csv", "html"])
    pretty_print: bool = True


@dataclass
class SmartSearchFullConfig:
    """Complete configuration for smart search system"""
    smart_matching: SmartMatchingConfig = field(default_factory=SmartMatchingConfig)
    advanced_search: AdvancedSearchConfig = field(default_factory=AdvancedSearchConfig)
    advanced_filtering: AdvancedFilteringConfig = field(default_factory=AdvancedFilteringConfig)
    recursion: RecursionConfig = field(default_factory=RecursionConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'SmartSearchFullConfig':
        """Create configuration from dictionary"""
        return cls(
            smart_matching=SmartMatchingConfig(**config_dict.get('smart_matching', {})),
            advanced_search=AdvancedSearchConfig(**config_dict.get('advanced_search', {})),
            advanced_filtering=AdvancedFilteringConfig(**config_dict.get('advanced_filtering', {})),
            recursion=RecursionConfig(**config_dict.get('recursion', {})),
            performance=PerformanceConfig(**config_dict.get('performance', {})),
            output=OutputConfig(**config_dict.get('output', {}))
        )


class ConfigManager:
    """Manage smart search configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager"""
        self.config_path = Path(config_path) if config_path else Path('config/smart_search_config.json')
        self.config = self._load_config()
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self) -> SmartSearchFullConfig:
        """Load configuration from file or create default"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config_dict = json.load(f)
                self.logger.info(f"Loaded configuration from {self.config_path}")
                return SmartSearchFullConfig.from_dict(config_dict)
            except Exception as e:
                self.logger.error(f"Error loading configuration: {e}")
                return self._get_default_config()
        else:
            self.logger.warning(f"Configuration file not found: {self.config_path}")
            return self._get_default_config()
    
    def _get_default_config(self) -> SmartSearchFullConfig:
        """Get default configuration"""
        return SmartSearchFullConfig(
            smart_matching=SmartMatchingConfig(
                enabled=True,
                strategy=MatchingStrategy.HYBRID.value,
                fuzzy_threshold=85.0,
                minimum_score=50.0,
                phonetic_enabled=True,
                case_insensitive=True
            ),
            advanced_search=AdvancedSearchConfig(
                enabled=True,
                max_variants=50,
                include_separators=True,
                include_phonetic=True,
                include_numbers=True
            ),
            advanced_filtering=AdvancedFilteringConfig(
                enabled=True,
                filter_low_confidence=True,
                confidence_threshold=70.0,
                deduplicate_results=True
            ),
            recursion=RecursionConfig(
                enabled=True,
                max_depth=3,
                follow_links=True,
                extract_usernames=True
            ),
            performance=PerformanceConfig(
                parallel_workers=12,
                request_timeout=30,
                cache_results=True
            ),
            output=OutputConfig(
                format="json",
                include_metadata=True,
                include_relationships=True
            )
        )
    
    def save_config(self, config: Optional[SmartSearchFullConfig] = None) -> bool:
        """Save configuration to file"""
        try:
            config_to_save = config or self.config
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config_to_save.to_dict(), f, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """Update specific configuration values"""
        try:
            config_dict = self.config.to_dict()
            self._recursive_update(config_dict, updates)
            self.config = SmartSearchFullConfig.from_dict(config_dict)
            return self.save_config()
        except Exception as e:
            self.logger.error(f"Error updating configuration: {e}")
            return False
    
    def _recursive_update(self, d: Dict, u: Dict) -> Dict:
        """Recursively update nested dictionaries"""
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = self._recursive_update(d.get(k, {}), v)
            else:
                d[k] = v
        return d
    
    def get_config(self) -> SmartSearchFullConfig:
        """Get current configuration"""
        return self.config
    
    def get_matching_config(self) -> SmartMatchingConfig:
        """Get matching configuration"""
        return self.config.smart_matching
    
    def get_search_config(self) -> AdvancedSearchConfig:
        """Get advanced search configuration"""
        return self.config.advanced_search
    
    def get_filtering_config(self) -> AdvancedFilteringConfig:
        """Get filtering configuration"""
        return self.config.advanced_filtering
    
    def get_recursion_config(self) -> RecursionConfig:
        """Get recursion configuration"""
        return self.config.recursion
    
    def get_performance_config(self) -> PerformanceConfig:
        """Get performance configuration"""
        return self.config.performance
    
    def get_output_config(self) -> OutputConfig:
        """Get output configuration"""
        return self.config.output
    
    def validate_config(self) -> bool:
        """Validate configuration values"""
        try:
            # Validate fuzzy threshold
            if not 0 <= self.config.smart_matching.fuzzy_threshold <= 100:
                self.logger.error("Fuzzy threshold must be between 0 and 100")
                return False
            
            # Validate maximum variants
            if self.config.advanced_search.max_variants < 1:
                self.logger.error("Max variants must be at least 1")
                return False
            
            # Validate recursion depth
            if self.config.recursion.max_depth < 1:
                self.logger.error("Max recursion depth must be at least 1")
                return False
            
            # Validate workers
            if self.config.performance.parallel_workers < 1:
                self.logger.error("Parallel workers must be at least 1")
                return False
            
            self.logger.info("Configuration validation passed")
            return True
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
    
    def print_config(self) -> None:
        """Print configuration in readable format"""
        print(json.dumps(self.config.to_dict(), indent=2))


# Export configuration classes
__all__ = [
    'ConfigManager',
    'SmartSearchFullConfig',
    'SmartMatchingConfig',
    'AdvancedSearchConfig',
    'AdvancedFilteringConfig',
    'RecursionConfig',
    'PerformanceConfig',
    'OutputConfig',
    'MatchingStrategy'
]
