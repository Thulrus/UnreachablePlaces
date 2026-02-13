"""
Configuration management for unreachable mapper.
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configuration manager for the unreachable mapper project."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to YAML config file. If None, uses default config.yaml
        """
        if config_path is None:
            # Get project root directory
            self.project_root = Path(__file__).parent.parent
            config_path = self.project_root / "config.yaml"
        else:
            self.project_root = Path(config_path).parent
            
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
            
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Convert relative paths to absolute paths
        config['paths'] = self._resolve_paths(config.get('paths', {}))
        
        return config
    
    def _resolve_paths(self, paths: Dict[str, str]) -> Dict[str, Path]:
        """Convert relative paths to absolute paths."""
        resolved = {}
        for key, path in paths.items():
            if not os.path.isabs(path):
                resolved[key] = self.project_root / path
            else:
                resolved[key] = Path(path)
        return resolved
    
    def get(self, key: str, default=None):
        """Get configuration value by key (supports dot notation)."""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
                
        return value
    
    def get_path(self, key: str) -> Path:
        """Get a path from configuration and ensure it's a Path object."""
        path = self.get(f'paths.{key}')
        if path is None:
            raise KeyError(f"Path '{key}' not found in configuration")
        return Path(path)
    
    def ensure_directories(self):
        """Create all configured directories if they don't exist."""
        for path in self.config['paths'].values():
            Path(path).mkdir(parents=True, exist_ok=True)
    
    @property
    def state_name(self) -> str:
        """Get the state name."""
        return self.get('state.name', 'Utah')
    
    @property
    def fips_code(self) -> str:
        """Get the state FIPS code."""
        return self.get('state.fips_code', '49')
    
    @property
    def crs(self) -> str:
        """Get the projection CRS."""
        return self.get('projection.crs', 'EPSG:5070')
    
    @property
    def resolution(self) -> int:
        """Get the raster resolution in meters."""
        return self.get('raster.resolution', 250)
    
    @property
    def road_types(self) -> list:
        """Get the list of road types to include."""
        return self.get('data.road_types', [])
    
    def __repr__(self):
        return f"Config(state={self.state_name}, crs={self.crs}, resolution={self.resolution}m)"


# Global configuration instance
_config = None


def get_config(config_path: str = None) -> Config:
    """Get or create the global configuration instance."""
    global _config
    if _config is None or config_path is not None:
        _config = Config(config_path)
    return _config


def set_config(config: Config):
    """Set the global configuration instance."""
    global _config
    _config = config
