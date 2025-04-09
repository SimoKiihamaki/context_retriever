import os
import yaml
import logging.config
from typing import Dict, Any, Optional


class Config:
    """
    Configuration manager for Code Context Retriever.
    Handles loading from YAML files and environment variables.
    """
    DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/default_config.yaml")
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to custom config YAML file. If None, uses default.
        """
        self.config = self._load_default_config()
        
        # Override with custom config if provided
        if config_path:
            custom_config = self._load_config_from_file(config_path)
            self._update_nested_dict(self.config, custom_config)
            
        # Override with environment variables
        self._override_from_env()
        
        # Setup logging
        self._configure_logging()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return self._load_config_from_file(self.DEFAULT_CONFIG_PATH)
    
    def _load_config_from_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from a YAML file."""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config from {file_path}: {e}")
            return {}
    
    def _update_nested_dict(self, d: Dict, u: Dict) -> Dict:
        """Recursively update a nested dictionary."""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._update_nested_dict(d[k], v)
            else:
                d[k] = v
        return d
    
    def _override_from_env(self):
        """Override config with environment variables."""
        # Example: CCR_EMBEDDER_MODEL overrides config['embedder']['model']
        prefix = "CCR_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                parts = key[len(prefix):].lower().split('_')
                self._set_nested_config(self.config, parts, value)
    
    def _set_nested_config(self, config: Dict, keys: list, value: Any):
        """Set a value in a nested dictionary using a list of keys."""
        if len(keys) == 1:
            config[keys[0]] = value
        else:
            if keys[0] not in config:
                config[keys[0]] = {}
            self._set_nested_config(config[keys[0]], keys[1:], value)
    
    def _configure_logging(self):
        """Configure logging based on the loaded configuration."""
        if 'logging' in self.config:
            logging.config.dictConfig(self.config['logging'])
        else:
            logging.basicConfig(level=logging.INFO)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

