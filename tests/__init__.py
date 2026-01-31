"""
Configuration Package

Centralizes all configuration for:
- Core modules (Kelly, Risk)
- Sport-specific settings (Soccer, MLB, etc.)
- API credentials

PHILOSOPHY:
- No hardcoded values in business logic
- Environment-specific configs (dev/prod)
- Type-safe with dataclasses
- Easy to test (inject fake configs)
"""

from config.core_config import (
    KellyConfig,
    RiskConfig,
    DEFAULT_KELLY_CONFIG,
    DEFAULT_RISK_CONFIG
)

from config.soccer_config import (
    SoccerConfig,
    SUPPORTED_SOCCER_LEAGUES,
    DEFAULT_SOCCER_CONFIG
)

# API keys imported separately (not in __all__ for security)
from config.api_keys import API_KEYS, validate_api_keys

__all__ = [
    # Core
    'KellyConfig',
    'RiskConfig',
    'DEFAULT_KELLY_CONFIG',
    'DEFAULT_RISK_CONFIG',
    
    # Soccer
    'SoccerConfig',
    'SUPPORTED_SOCCER_LEAGUES',
    'DEFAULT_SOCCER_CONFIG',
    
    # API Keys
    'API_KEYS',
    'validate_api_keys'
]