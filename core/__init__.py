"""
Core modules - Sport-agnostic betting logic

NUNCA importar nada de sports/ aquí.
Si lo necesitas, la arquitectura está mal.
"""
from core.models import (
    Sport,
    MarketType,
    GameAnalysis,
    Pick,
    OddsData
)
from core.probability import ProbabilityEngine
from core.edge import EdgeCalculator
from core.kelly import KellyCalculator
from core.risk import RiskManager

__all__ = [
    # Models
    'Sport',
    'MarketType',
    'GameAnalysis',
    'Pick',
    'OddsData',
    
    # Engines
    'ProbabilityEngine',
    'EdgeCalculator',
    'KellyCalculator',
    'RiskManager'
]