"""
Core data models - Sport-agnostic contracts
Todos los adapters DEBEN producir estos tipos.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List, Any
from enum import Enum


class Sport(Enum):
    """Deportes soportados"""
    SOCCER = "soccer"
    MLB = "mlb"
    NFL = "nfl"
    NBA = "nba"
    TENNIS = "tennis"


class MarketType(Enum):
    """Tipos de mercado universales"""
    MONEYLINE = "moneyline"          # Ganador directo
    TOTALS = "totals"                # Over/Under
    SPREAD = "spread"                # Handicap/Runline
    BOTH_TEAMS_SCORE = "btts"        # Soccer-specific (futuro)
    PLAYER_PROPS = "props"           # Futuro


@dataclass
class GameAnalysis:
    """
    Contrato universal - Output de cualquier SportAdapter
    
    REGLA: Si un adapter no puede calcular algo, usa None.
           El core/markets manejan valores faltantes.
    """
    # Identificación
    sport: Sport
    league: str                       # "LaLiga", "MLB", "Premier League"
    game_id: str                      # Único por juego
    home_team: str
    away_team: str
    start_time: datetime
    
    # Probabilidades reales (0-1)
    # Soccer: {"home_win": 0.45, "draw": 0.28, "away_win": 0.27}
    # MLB: {"home_win": 0.55, "away_win": 0.45}
    probabilities: Dict[str, float]
    
    # Proyecciones cuantitativas
    # Soccer: {"total_goals": 2.7, "home_goals": 1.5, "away_goals": 1.2}
    # MLB: {"total_runs": 9.2, "home_runs": 4.8, "away_runs": 4.4}
    projections: Dict[str, float]
    
    # Metadata del modelo
    confidence: float                 # 0-1 (calidad de datos disponibles)
    model_version: str                # "soccer_xg_v1.0", "mlb_monte_carlo_v2.1"
    
    # Context adicional (opcional, para debugging/logging)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validación básica"""
        assert 0 <= self.confidence <= 1, "Confidence debe estar entre 0 y 1"
        
        # Validar que probabilities sumen ~1.0 (tolerancia para redondeo)
        prob_sum = sum(self.probabilities.values())
        assert 0.98 <= prob_sum <= 1.02, f"Probabilities deben sumar 1.0, suma actual: {prob_sum}"


@dataclass
class Pick:
    """
    Representación de una apuesta con valor
    
    GENERADO POR: Markets (moneyline.py, totals.py)
    CONSUMIDO POR: Risk Manager, Kelly Calculator
    """
    # Identificación
    game_id: str                      # Referencia a GameAnalysis
    market: MarketType
    selection: str                    # "home", "away", "draw", "over", "under"
    
    # Métricas
    odds: float                       # Decimal odds (ej: 2.10)
    probability: float                # Probabilidad real (0-1)
    edge: float                       # Edge normalizado (-1 a 1)
    confidence: float                 # Del GameAnalysis (0-1)
    
    # Stake (calculado por Kelly Calculator)
    stake_pct: float = 0.0            # % del bankroll (0-10%)
    stake_amount: Optional[float] = None  # Cantidad absoluta (calculado después)
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Para serialización JSON"""
        return {
            "game_id": self.game_id,
            "market": self.market.value,
            "selection": self.selection,
            "odds": round(self.odds, 2),
            "probability": round(self.probability, 4),
            "edge": round(self.edge, 4),
            "confidence": round(self.confidence, 2),
            "stake_pct": round(self.stake_pct, 2),
            "expected_value": round((self.probability * self.odds - 1) * 100, 2),
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class OddsData:
    """
    Cuotas normalizadas desde cualquier provider
    
    GENERADO POR: OddsProvider (odds_api.py, fake_provider.py)
    CONSUMIDO POR: Markets
    """
    game_id: str
    sport: Sport
    bookmaker: str                    # "DraftKings", "Bet365", etc.
    
    # Moneyline
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None
    draw_odds: Optional[float] = None  # Solo para soccer
    
    # Totals
    total_line: Optional[float] = None
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None
    
    # Spread/Handicap
    spread_line: Optional[float] = None
    spread_home_odds: Optional[float] = None
    spread_away_odds: Optional[float] = None
    
    last_update: datetime = field(default_factory=datetime.now)
    
    def get_market_odds(self, market: MarketType) -> Dict[str, float]:
        """Helper para extraer odds de un mercado específico"""
        if market == MarketType.MONEYLINE:
            result = {}
            if self.home_odds: result["home"] = self.home_odds
            if self.away_odds: result["away"] = self.away_odds
            if self.draw_odds: result["draw"] = self.draw_odds
            return result
        
        elif market == MarketType.TOTALS:
            return {
                "line": self.total_line,
                "over": self.over_odds,
                "under": self.under_odds
            }
        
        elif market == MarketType.SPREAD:
            return {
                "line": self.spread_line,
                "home": self.spread_home_odds,
                "away": self.spread_away_odds
            }
        
        return {}