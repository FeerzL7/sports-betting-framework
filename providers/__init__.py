"""
Providers Package - Odds Sources

Implementaciones de OddsProviderBase:
- FakeOddsProvider: Datos hardcodeados para testing (sin API)
- OddsAPIProvider:  The Odds API (producción)

El Orchestrator recibe un provider por inyección de dependencia.
Nunca hardcodea qué provider usar → intercambiable sin cambiar lógica.

USO:
    from providers import FakeOddsProvider, OddsAPIProvider
    
    # Testing
    provider = FakeOddsProvider(scenario="value_exists")
    
    # Producción
    provider = OddsAPIProvider()
"""

from providers.base import OddsProviderBase
from providers.fake_provider import FakeOddsProvider
from providers.odds_api import OddsAPIProvider

__all__ = [
    'OddsProviderBase',
    'FakeOddsProvider',
    'OddsAPIProvider'
]