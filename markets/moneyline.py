"""
Moneyline Market Evaluator

Evalúa mercado de ganador directo:
- Soccer: Home / Draw / Away (1X2)
- MLB/NBA/NFL: Home / Away

RESPONSABILIDAD:
Comparar probabilidad real vs implícita y generar Pick si hay valor.
"""
from typing import Optional
from markets.base import Market
from core.models import MarketType, GameAnalysis, OddsData, Pick
from core.edge import EdgeCalculator
from utils import get_logger, LogContext

logger = get_logger(__name__)


class MoneylineMarket(Market):
    """
    Evaluador de mercado Moneyline (ganador directo)
    
    CASOS DE USO:
    - Soccer: 1X2 (Home/Draw/Away)
    - MLB: Home/Away
    - NBA: Home/Away
    - NFL: Home/Away
    """
    
    market_type = MarketType.MONEYLINE
    
    # Mapeo flexible: outcome canónico → claves aceptadas en analysis.probabilities
    # ProbabilityEngine.from_poisson produce "home_win"/"away_win"
    # Algunos adapters podrían usar "home"/"away"
    # El mercado acepta ambas sin que el core tenga que saber de qué deporte viene
    PROB_KEY_MAP = {
        "home": ["home", "home_win"],
        "away": ["away", "away_win"],
        "draw": ["draw"]
    }
    
    def __init__(self, min_edge: float = 0.02):
        """
        Args:
            min_edge: Edge mínimo para generar pick (default 2%)
        """
        self.min_edge = min_edge
        self.edge_calc = EdgeCalculator()
        
        logger.debug(
            f"MoneylineMarket initialized with min_edge={min_edge:.2%}"
        )
    
    def evaluate(self, analysis: GameAnalysis, odds: OddsData) -> Optional[Pick]:
        """
        Evalúa moneyline para detectar valor
        
        Args:
            analysis: GameAnalysis con probabilidades reales
            odds: OddsData con cuotas del mercado
        
        Returns:
            Pick con mejor edge si >= min_edge, None si no hay valor
        
        Proceso:
        1. Validar inputs
        2. Extraer probabilidades reales (analysis.probabilities)
        3. Extraer odds del mercado (odds.get_market_odds)
        4. Para cada outcome: calcular edge
        5. Retornar outcome con mayor edge si >= threshold
        """
        # Validate inputs
        if not self._validate_inputs(analysis, odds):
            return None
        
        with LogContext(
            logger,
            game_id=analysis.game_id,
            market="moneyline"
        ):
            logger.debug("Evaluating moneyline market")
            
            # Extract probabilities and odds
            real_probs = analysis.probabilities
            market_odds = odds.get_market_odds(MarketType.MONEYLINE)
            
            if not market_odds:
                logger.debug("No moneyline odds available")
                return None
            
            # Evaluate each outcome
            best_pick = None
            best_edge = self.min_edge
            
            for outcome in ["home", "away", "draw"]:
                # --- Flexible probability lookup ---
                # analysis.probabilities puede usar "home_win" o "home"
                # según qué adapter lo produjo. Nunca asumimos formato fijo.
                real_prob = None
                for prob_key in self.PROB_KEY_MAP[outcome]:
                    if prob_key in real_probs:
                        real_prob = real_probs[prob_key]
                        break
                
                if real_prob is None:
                    continue
                
                # --- Odds lookup (OddsData.get_market_odds ya normaliza a "home"/"away"/"draw") ---
                if outcome not in market_odds or market_odds[outcome] is None:
                    continue
                
                outcome_odds = market_odds[outcome]
                
                # Calculate edge
                edge = self.edge_calc.calculate(
                    real_prob,
                    outcome_odds,
                    self.market_type
                )
                
                # Calculate EV for logging
                ev = self.edge_calc.calculate_expected_value(
                    real_prob,
                    outcome_odds
                )
                
                logger.debug(
                    f"{outcome}: prob={real_prob:.2%}, odds={outcome_odds:.2f}, "
                    f"edge={edge:.4f}, EV={ev:.2f}%"
                )
                
                # Track best edge
                if edge > best_edge:
                    best_edge = edge
                    best_pick = Pick(
                        game_id=analysis.game_id,
                        market=self.market_type,
                        selection=outcome,
                        odds=outcome_odds,
                        probability=real_prob,
                        edge=edge,
                        confidence=analysis.confidence,
                        stake_pct=0.0  # Will be set by KellyCalculator
                    )
            
            # Log result
            if best_pick:
                logger.info(
                    f"✅ VALUE FOUND: {best_pick.selection} @ {best_pick.odds:.2f}",
                    extra={
                        "selection": best_pick.selection,
                        "odds": best_pick.odds,
                        "edge": best_pick.edge,
                        "probability": best_pick.probability,
                        "confidence": best_pick.confidence
                    }
                )
            else:
                logger.debug("No value found (all edges < threshold)")
            
            return best_pick
    
    def _validate_inputs(self, analysis: GameAnalysis, odds: OddsData) -> bool:
        """Validate moneyline-specific inputs"""
        if not super()._validate_inputs(analysis, odds):
            return False
        
        # Check that we have probabilities
        if not analysis.probabilities:
            logger.warning(
                "No probabilities in GameAnalysis",
                extra={"game_id": analysis.game_id}
            )
            return False
        
        # Check required outcomes (flexible key matching)
        # Acepta "home" O "home_win", "away" O "away_win"
        has_home = any(k in analysis.probabilities for k in self.PROB_KEY_MAP["home"])
        has_away = any(k in analysis.probabilities for k in self.PROB_KEY_MAP["away"])
        
        if not (has_home and has_away):
            logger.warning(
                "Missing required outcomes in probabilities",
                extra={
                    "game_id": analysis.game_id,
                    "available": list(analysis.probabilities.keys())
                }
            )
            return False
        
        return True