import os
import yaml
from typing import Any, Dict, Optional
from functools import lru_cache
from app.utils.env_loader import load_env_from_file

# Load environment variables
load_env_from_file()

class ConfigProvider:
    """
    A unified provider for configuration values from multiple sources:
    1. Environment variables (highest priority)
    2. Config files (YAML)
    3. Default values (lowest priority)
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the config provider.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config = {}
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), 
            "../../config/config.yaml"
        )
        
        # Load configuration from file if it exists
        self._load_config_file()
    
    def _load_config_file(self) -> None:
        """Load configuration from YAML file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as file:
                    self.config = yaml.safe_load(file) or {}
        except Exception as e:
            print(f"Error loading config file: {e}")
    
    def get(self, key: str, default: Any = None, section: Optional[str] = None) -> Any:
        """
        Get a configuration value with priority:
        1. Environment variable
        2. Config file
        3. Default value
        
        Args:
            key: The configuration key
            default: Default value if not found
            section: Optional section in the config file
            
        Returns:
            The configuration value
        """
        # First check for environment variable (convert to upper case with underscores)
        env_key = key.upper().replace('.', '_')
        env_value = os.getenv(env_key)
        if env_value is not None:
            return self._convert_value(env_value)
        
        # Next check in config file
        if section:
            # Navigate through nested sections
            config_value = self.config
            for s in section.split('.'):
                if s in config_value:
                    config_value = config_value[s]
                else:
                    return default
            if key in config_value:
                return config_value[key]
        else:
            # Check at top level
            if key in self.config:
                return self.config[key]
        
        # Finally, return default
        return default
    
    def _convert_value(self, value: str) -> Any:
        """
        Convert string values to appropriate types.
        
        Args:
            value: String value to convert
            
        Returns:
            Converted value
        """
        # Handle boolean values
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        # Handle numeric values
        try:
            # Try as int
            return int(value)
        except ValueError:
            try:
                # Try as float
                return float(value)
            except ValueError:
                # Keep as string
                return value
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        return self.config

@lru_cache()
def get_config_provider() -> ConfigProvider:
    """
    Get a singleton instance of ConfigProvider.
    
    Returns:
        ConfigProvider instance
    """
    return ConfigProvider()
