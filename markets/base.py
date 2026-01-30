"""
Market Base Contract

REGLA: Un mercado NUNCA decide stake.
Su ÚNICA responsabilidad es detectar edge.
"""
from abc import ABC, abstractmethod
from typing import Optional
from core.models import GameAnalysis, OddsData, Pick, MarketType


class Market(ABC):
    """
    Evaluador de mercado agnóstico al deporte
    
    RESPONSABILIDADES:
    1. Recibir GameAnalysis (probabilidades reales)
    2. Recibir OddsData (probabilidades implícitas)
    3. Calcular edge
    4. Devolver Pick si edge >= umbral, None si no
    
    NO ES RESPONSABLE DE:
    - Calcular probabilidades (lo hace SportAdapter)
    - Decidir stake (lo hace KellyCalculator)
    - Gestión de riesgo (lo hace RiskManager)
    """
    
    market_type: MarketType
    min_edge: float  # Umbral mínimo para generar pick
    
    @abstractmethod
    def evaluate(self, analysis: GameAnalysis, odds: OddsData) -> Optional[Pick]:
        """
        Evalúa si hay edge en este mercado
        
        PIPELINE:
        1. Extraer probabilidades reales de analysis
        2. Extraer odds de OddsData
        3. Calcular edge normalizado (usando EdgeCalculator)
        4. Si edge >= min_edge → crear Pick
        5. Caso contrario → return None
        
        Args:
            analysis: Probabilidades reales + proyecciones
            odds: Cuotas del mercado
        
        Returns:
            Pick si hay valor, None si no
        
        IMPORTANTE:
        - Pick NO tiene stake aquí (stake_pct = 0.0)
        - Edge normalizado considera market efficiency
        - Si odds faltantes → return None (sin error)
        """
        pass
    
    def _validate_inputs(self, analysis: GameAnalysis, odds: OddsData) -> bool:
        """
        Helper para validar que inputs tengan datos necesarios
        
        Override en subclases para validaciones específicas
        """
        return (
            analysis is not None and
            odds is not None and
            analysis.game_id == odds.game_id
        )