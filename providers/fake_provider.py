"""
Fake Odds Provider - Deterministic test doubles

RESPONSABILIDAD:
Proveer odds hardcodeados para testing sin APIs.

DISEÑO:
- Cada scenario es reproducible (sin randomness)
- Cubre casos positivos, negativos y edge cases
- Formato idéntico a OddsAPIProvider (mismo contrato)

SCENARIOS DISPONIBLES:
- "value_exists":    Odds con edge positivo en home ML + over totals
- "no_value":        Odds muy ajustados (alta vig), sin valor en ningún outcome
- "partial_odds":    Faltan algunos campos (draw, under) → testa graceful handling
- "empty":           Sin datos de odds (simula API sin coverage)

USO:
    provider = FakeOddsProvider(scenario="value_exists")
    odds_list = provider.get_odds(Sport.SOCCER, "PL", "2025-01-30")
"""
from typing import List, Optional
from datetime import datetime
from providers.base import OddsProviderBase
from core.models import OddsData, Sport
from utils import get_logger

logger = get_logger(__name__)


# ============================================================================
# SCENARIOS
# Cada scenario es un Dict de fixtures con odds hardcodeados.
# Keys = game_id que debe coincidir con lo que produce el adapter.
# ============================================================================

SCENARIOS = {
    # ----------------------------------------------------------------
    # VALUE EXISTS
    # Home tiene edge positivo en ML (odds generosos)
    # Over tiene edge positivo en Totals (línea baja vs proyección alta)
    # ----------------------------------------------------------------
    "value_exists": {
        "soccer_PL_86_81": OddsData(
            game_id="soccer_PL_86_81",
            sport=Sport.SOCCER,
            bookmaker="FakeBook",
            # ML: home_odds=2.30 → implied 43.5%
            # Si modelo dice 45% → edge positivo
            home_odds=2.30,
            away_odds=3.60,
            draw_odds=3.20,
            # Totals: line=2.5, over=2.10 → implied 47.6%
            # Si modelo proyecta 2.8 goles → P(over) ~53% → edge positivo
            total_line=2.5,
            over_odds=2.10,
            under_odds=1.80,
            # Spread: no incluido en este scenario
            spread_line=None,
            spread_home_odds=None,
            spread_away_odds=None
        ),
        "soccer_PL_57_65": OddsData(
            game_id="soccer_PL_57_65",
            sport=Sport.SOCCER,
            bookmaker="FakeBook",
            home_odds=1.95,
            away_odds=3.80,
            draw_odds=3.40,
            total_line=2.5,
            over_odds=1.90,
            under_odds=1.95,
            spread_line=None,
            spread_home_odds=None,
            spread_away_odds=None
        )
    },

    # ----------------------------------------------------------------
    # NO VALUE
    # Todas las odds muy ajustadas (alta vigorish)
    # Ningún outcome tiene edge positivo
    # ----------------------------------------------------------------
    "no_value": {
        "soccer_PL_86_81": OddsData(
            game_id="soccer_PL_86_81",
            sport=Sport.SOCCER,
            bookmaker="FakeBook",
            # home_odds=1.70 → implied 58.8% (vs real ~45%) → negativo
            home_odds=1.70,
            away_odds=2.80,
            draw_odds=2.60,
            total_line=2.5,
            over_odds=1.75,   # implied 57.1% vs real ~53% → negativo
            under_odds=2.10,
            spread_line=None,
            spread_home_odds=None,
            spread_away_odds=None
        )
    },

    # ----------------------------------------------------------------
    # PARTIAL ODDS
    # Faltan draw_odds y under_odds → testa que los mercados
    # manejan None sin explotar
    # ----------------------------------------------------------------
    "partial_odds": {
        "soccer_PL_86_81": OddsData(
            game_id="soccer_PL_86_81",
            sport=Sport.SOCCER,
            bookmaker="FakeBook",
            home_odds=2.30,
            away_odds=3.60,
            draw_odds=None,       # Faltante
            total_line=2.5,
            over_odds=2.10,
            under_odds=None,      # Faltante
            spread_line=None,
            spread_home_odds=None,
            spread_away_odds=None
        )
    },

    # ----------------------------------------------------------------
    # EMPTY
    # Sin datos (simula liga sin coverage en la API de odds)
    # ----------------------------------------------------------------
    "empty": {}
}


class FakeOddsProvider(OddsProviderBase):
    """
    Provider de odds hardcodeados para testing.
    
    GARANTÍAS:
    - Determinista (mismo input → mismo output siempre)
    - Sin dependencias externas
    - Cubre happy path, edge cases y failures
    
    Args:
        scenario: Clave del scenario a usar (default "value_exists")
    
    Ejemplo:
        >>> provider = FakeOddsProvider(scenario="value_exists")
        >>> odds = provider.get_odds(Sport.SOCCER, "PL")
        >>> len(odds)
        2
    """
    
    provider_name = "FakeOddsProvider"
    
    def __init__(self, scenario: str = "value_exists"):
        if scenario not in SCENARIOS:
            raise ValueError(
                f"Scenario '{scenario}' no existe. "
                f"Disponibles: {list(SCENARIOS.keys())}"
            )
        
        self.scenario = scenario
        self._data = SCENARIOS[scenario]
        
        logger.info(
            f"FakeOddsProvider initialized",
            extra={"scenario": scenario, "fixtures": len(self._data)}
        )
    
    def get_odds(
        self,
        sport: Sport,
        league: str,
        date: Optional[str] = None
    ) -> List[OddsData]:
        """
        Retorna todos los odds del scenario activo.
        
        Ignora sport/league/date (test doubles son simples).
        En producción, OddsAPIProvider filtra por estos campos.
        """
        logger.debug(
            f"FakeOddsProvider.get_odds called",
            extra={
                "scenario": self.scenario,
                "sport": sport.value,
                "league": league
            }
        )
        
        return list(self._data.values())
    
    def get_game_odds(self, game_id: str) -> Optional[OddsData]:
        """Busca odds por game_id exacto."""
        result = self._data.get(game_id)
        
        if result is None:
            logger.debug(
                f"No odds found for game_id={game_id}",
                extra={"scenario": self.scenario}
            )
        
        return result