"""
Markets Package - Market Evaluators

Cada mercado:
1. Compara probabilidades reales vs implícitas
2. Calcula edge normalizado
3. Devuelve Pick si edge >= threshold

NO ES RESPONSABLE DE:
- Calcular probabilidades (lo hace SportAdapter)
- Decidir stake (lo hace KellyCalculator)
- Gestión de riesgo (lo hace RiskManager)
"""

from markets.base import Market
from markets.moneyline import MoneylineMarket
from markets.totals import TotalsMarket

__all__ = [
    'Market',
    'MoneylineMarket',
    'TotalsMarket'
]