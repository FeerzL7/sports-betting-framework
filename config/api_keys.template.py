"""
API Keys Configuration Template

Copy this file to api_keys.py and fill in your keys:
    cp config/api_keys.template.py config/api_keys.py

Then edit api_keys.py with your actual API keys.
"""

import os

API_KEYS = {
    "api_football": {
        "api_key": os.getenv("FOOTBALL_API_KEY", "YOUR_KEY_HERE"),
        "base_url": "https://api.football-data.org/v4",
        "rate_limit": 10,
        "description": "Football-data.org - Soccer fixtures and team stats"
    },
    
    "odds_api": {
        "api_key": os.getenv("ODDS_API_KEY", "YOUR_KEY_HERE"),
        "base_url": "https://api.the-odds-api.com/v4/sports",
        "rate_limit": 20,
        "monthly_limit": 500,
        "description": "The Odds API - Live betting odds"
    }
}

def get_api_config(provider: str):
    """Get API configuration"""
    if provider not in API_KEYS:
        raise ValueError(f"Provider '{provider}' not configured")
    
    config = API_KEYS[provider].copy()
    
    if config["api_key"] == "YOUR_KEY_HERE":
        raise ValueError(
            f"API key for '{provider}' not set. "
            f"Edit config/api_keys.py or set environment variable."
        )
    
    return config

def validate_api_keys():
    """Validate API keys are configured"""
    validation = {}
    for provider, config in API_KEYS.items():
        key = config.get("api_key", "")
        validation[provider] = {
            "configured": key != "YOUR_KEY_HERE" and len(key) > 0,
            "status": "valid" if (key != "YOUR_KEY_HERE" and len(key) > 0) else "placeholder"
        }
    return validation

def is_provider_configured(provider: str):
    """Check if provider is ready"""
    val = validate_api_keys()
    return val.get(provider, {}).get("configured", False)