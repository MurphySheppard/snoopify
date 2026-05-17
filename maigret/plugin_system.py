"""
Plugin System for Snoopify
Extensible architecture for adding custom search and analysis plugins
"""

import logging
import importlib
from typing import Dict, List, Any, Callable, Optional, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Plugin metadata"""
    name: str
    version: str
    author: str
    description: str
    plugin_type: str
    dependencies: List[str] = None


class PluginBase(ABC):
    """Base class for all plugins"""
    
    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata
        self.logger = logging.getLogger(f"plugin.{metadata.name}")
        self.config: Dict[str, Any] = {}
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute plugin logic
        
        Args:
            input_data: Input data dictionary
        
        Returns:
            Result dictionary
        """
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data"""
        pass
    
    def set_config(self, config: Dict[str, Any]) -> None:
        """Set plugin configuration"""
        self.config = config
    
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata"""
        return self.metadata


class SearchPlugin(PluginBase):
    """Base class for search plugins"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search"""
        username = input_data.get('username')
        sites = input_data.get('sites')
        
        if not self.validate_input(input_data):
            return {'error': 'Invalid input'}
        
        return await self.search(username, sites)
    
    @abstractmethod
    async def search(self, username: str, sites: Optional[List[str]]) -> Dict[str, Any]:
        """Perform search"""
        pass


class AnalysisPlugin(PluginBase):
    """Base class for analysis plugins"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analysis"""
        if not self.validate_input(input_data):
            return {'error': 'Invalid input'}
        
        return await self.analyze(input_data)
    
    @abstractmethod
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform analysis"""
        pass


class EnhancedMatchingPlugin(SearchPlugin):
    """Built-in plugin for enhanced username matching"""
    
    def __init__(self):
        metadata = PluginMetadata(
            name="EnhancedMatchingPlugin",
            version="1.0.0",
            author="Snoopify Team",
            description="Enhanced fuzzy matching for username discovery",
            plugin_type="search"
        )
        super().__init__(metadata)
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input"""
        return 'username' in input_data
    
    async def search(self, username: str, sites: Optional[List[str]]) -> Dict[str, Any]:
        """Perform enhanced matching search"""
        from .smart_search_engine import UsernameVariantGenerator, SmartMatcher
        
        variants = UsernameVariantGenerator.generate_variants(username, 20)
        matcher = SmartMatcher()
        
        results = {
            'original': username,
            'variants': variants,
            'matches': []
        }
        
        for variant in variants:
            confidence = matcher.calculate_confidence(username, variant)
            if confidence >= self.config.get('min_confidence', 75):
                results['matches'].append({
                    'variant': variant,
                    'confidence': confidence
                })
        
        self.logger.info(f"Found {len(results['matches'])} matching variants")
        return results


class SocialNetworkAnalysisPlugin(AnalysisPlugin):
    """Built-in plugin for social network analysis"""
    
    def __init__(self):
        metadata = PluginMetadata(
            name="SocialNetworkAnalysisPlugin",
            version="1.0.0",
            author="Snoopify Team",
            description="Analyze account relationships and social patterns",
            plugin_type="analysis"
        )
        super().__init__(metadata)
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input"""
        return 'results' in input_data
    
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze social networks"""
        results = data.get('results', [])
        
        analysis = {
            'total_accounts': len(results),
            'verified_accounts': 0,
            'accounts_by_platform': {},
            'network_density': 0.0,
            'key_platforms': [],
            'risk_profile': 'unknown'
        }
        
        # Count verified accounts
        for result in results:
            if isinstance(result, dict):
                if result.get('verified'):
                    analysis['verified_accounts'] += 1
                
                site = result.get('site', 'unknown')
                if site not in analysis['accounts_by_platform']:
                    analysis['accounts_by_platform'][site] = 0
                analysis['accounts_by_platform'][site] += 1
        
        # Identify key platforms
        sorted_platforms = sorted(
            analysis['accounts_by_platform'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        analysis['key_platforms'] = [p[0] for p in sorted_platforms[:5]]
        
        # Assess risk
        if analysis['verified_accounts'] >= 3:
            analysis['risk_profile'] = 'high'
        elif analysis['total_accounts'] >= 10:
            analysis['risk_profile'] = 'medium'
        else:
            analysis['risk_profile'] = 'low'
        
        self.logger.info(f"Social network analysis: {analysis['total_accounts']} accounts found")
        return analysis


class GeoIPEnrichmentPlugin(AnalysisPlugin):
    """Built-in plugin for GeoIP enrichment"""
    
    def __init__(self):
        metadata = PluginMetadata(
            name="GeoIPEnrichmentPlugin",
            version="1.0.0",
            author="Snoopify Team",
            description="Enrich results with geolocation data",
            plugin_type="analysis"
        )
        super().__init__(metadata)
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input"""
        return 'results' in input_data or 'ip_addresses' in input_data
    
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich with GeoIP data"""
        # This would integrate with actual GeoIP service
        results = data.get('results', [])
        
        enrichment = {
            'locations': [],
            'countries': set(),
            'timezone_info': []
        }
        
        for result in results:
            if isinstance(result, dict):
                # Extract location if available
                if 'location' in result:
                    enrichment['locations'].append(result['location'])
                    if 'country' in result:
                        enrichment['countries'].add(result['country'])
        
        enrichment['countries'] = list(enrichment['countries'])
        
        self.logger.info(f"GeoIP enrichment: Found {len(enrichment['locations'])} locations")
        return enrichment


class PluginManager:
    """Manage plugins"""
    
    def __init__(self):
        self.plugins: Dict[str, PluginBase] = {}
        self.search_plugins: List[str] = []
        self.analysis_plugins: List[str] = []
        self.logger = logging.getLogger(__name__)
        self._load_builtin_plugins()
    
    def _load_builtin_plugins(self) -> None:
        """Load built-in plugins"""
        builtin_plugins = [
            EnhancedMatchingPlugin(),
            SocialNetworkAnalysisPlugin(),
            GeoIPEnrichmentPlugin()
        ]
        
        for plugin in builtin_plugins:
            self.register_plugin(plugin)
    
    def register_plugin(self, plugin: PluginBase) -> bool:
        """Register a plugin"""
        try:
            plugin_name = plugin.metadata.name
            
            # Check if already registered
            if plugin_name in self.plugins:
                self.logger.warning(f"Plugin already registered: {plugin_name}")
                return False
            
            # Register plugin
            self.plugins[plugin_name] = plugin
            
            # Track by type
            if plugin.metadata.plugin_type == 'search':
                self.search_plugins.append(plugin_name)
            elif plugin.metadata.plugin_type == 'analysis':
                self.analysis_plugins.append(plugin_name)
            
            self.logger.info(f"Plugin registered: {plugin_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error registering plugin: {e}")
            return False
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """Unregister a plugin"""
        if plugin_name not in self.plugins:
            self.logger.warning(f"Plugin not found: {plugin_name}")
            return False
        
        plugin = self.plugins[plugin_name]
        del self.plugins[plugin_name]
        
        # Remove from type lists
        if plugin_name in self.search_plugins:
            self.search_plugins.remove(plugin_name)
        elif plugin_name in self.analysis_plugins:
            self.analysis_plugins.remove(plugin_name)
        
        self.logger.info(f"Plugin unregistered: {plugin_name}")
        return True
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """Get plugin by name"""
        return self.plugins.get(plugin_name)
    
    async def execute_plugin(self, plugin_name: str, 
                            input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute plugin"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return {'error': f'Plugin not found: {plugin_name}'}
        
        try:
            return await plugin.execute(input_data)
        except Exception as e:
            self.logger.error(f"Error executing plugin {plugin_name}: {e}")
            return {'error': str(e)}
    
    async def execute_search_plugins(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all search plugins"""
        results = {}
        
        for plugin_name in self.search_plugins:
            result = await self.execute_plugin(plugin_name, input_data)
            results[plugin_name] = result
        
        return results
    
    async def execute_analysis_plugins(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all analysis plugins"""
        results = {}
        
        for plugin_name in self.analysis_plugins:
            result = await self.execute_plugin(plugin_name, input_data)
            results[plugin_name] = result
        
        return results
    
    def list_plugins(self, plugin_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List plugins"""
        plugins_list = []
        
        for plugin_name, plugin in self.plugins.items():
            if plugin_type and plugin.metadata.plugin_type != plugin_type:
                continue
            
            plugins_list.append({
                'name': plugin.metadata.name,
                'version': plugin.metadata.version,
                'author': plugin.metadata.author,
                'description': plugin.metadata.description,
                'type': plugin.metadata.plugin_type
            })
        
        return plugins_list
    
    def configure_plugin(self, plugin_name: str, config: Dict[str, Any]) -> bool:
        """Configure plugin"""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            self.logger.warning(f"Plugin not found: {plugin_name}")
            return False
        
        try:
            plugin.set_config(config)
            self.logger.info(f"Plugin configured: {plugin_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error configuring plugin: {e}")
            return False


# Export classes
__all__ = [
    'PluginManager',
    'PluginBase',
    'SearchPlugin',
    'AnalysisPlugin',
    'PluginMetadata',
    'EnhancedMatchingPlugin',
    'SocialNetworkAnalysisPlugin',
    'GeoIPEnrichmentPlugin'
]
