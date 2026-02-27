"""
Totals Market Evaluator (Over/Under)

Evalúa mercado de totales:
- Soccer: Over/Under 2.5 goals
- NBA: Over/Under 220.5 points
- MLB: Over/Under 8.5 runs

RESPONSABILIDAD:
Comparar probabilidad calculada vs odds y generar Pick si hay valor.
"""
from typing import Optional
from markets.base import Market
from core.models import MarketType, GameAnalysis, OddsData, Pick, Sport
from core.edge import EdgeCalculator
from core.probability import ProbabilityEngine
from utils import get_logger, LogContext

logger = get_logger(__name__)


class TotalsMarket(Market):
    """
    Evaluador de mercado Totals (Over/Under)

    CASOS DE USO:
    - Soccer: Over/Under 2.5 goals
    - NBA: Over/Under 220.5 points
    - MLB: Over/Under 8.5 runs
    """

    market_type = MarketType.TOTALS

    def __init__(self, min_edge: float = 0.02):
        """
        Args:
            min_edge: Edge mínimo para generar pick (default 2%)
        """
        self.min_edge = min_edge
        self.edge_calc = EdgeCalculator()

        logger.debug(
            f"TotalsMarket initialized with min_edge={min_edge:.2%}"
        )

    def evaluate(self, analysis: GameAnalysis, odds: OddsData) -> Optional[Pick]:
        """
        Evalúa totals para detectar valor

        Args:
            analysis: GameAnalysis con proyecciones de totales
            odds: OddsData con línea y cuotas

        Returns:
            Pick (over o under) con mejor edge si >= min_edge, None si no

        Proceso:
        1. Validar inputs
        2. Extraer total esperado (analysis.projections)
        3. Extraer línea y odds del mercado
        4. Calcular prob(over) y prob(under) usando ProbabilityEngine
        5. Calcular edge para ambos lados
        6. Retornar lado con mayor edge si >= threshold
        """
        # Validate inputs
        if not self._validate_inputs(analysis, odds):
            return None

        with LogContext(
            logger,
            game_id=analysis.game_id,
            market="totals"
        ):
            logger.debug("Evaluating totals market")

            # Extract total expected
            total_expected = self._extract_total_expected(analysis)
            if total_expected is None:
                logger.warning("No total projection available")
                return None

            # Extract market odds
            market_odds = odds.get_market_odds(MarketType.TOTALS)

            if not market_odds or market_odds.get("line") is None:
                logger.debug("No totals line available")
                return None

            line = market_odds["line"]
            over_odds = market_odds.get("over")
            under_odds = market_odds.get("under")

            if over_odds is None or under_odds is None:
                logger.debug("Missing over/under odds")
                return None

            logger.debug(
                f"Line: {line}, Expected: {total_expected:.2f}"
            )

            # Calculate probabilities using ProbabilityEngine
            distribution = self._get_distribution_type(analysis.sport)

            # H3 FIX: Extraer std de projections o usar default
            std = self._get_std(analysis, distribution)

            try:
                over_prob, under_prob = ProbabilityEngine.calculate_over_under_probability(
                    total_expected=total_expected,
                    line=line,
                    distribution=distribution,
                    std=std
                )
            except Exception as e:
                logger.error(
                    f"Failed to calculate probabilities: {e}",
                    extra={"error": str(e)}
                )
                return None

            logger.debug(
                f"Probabilities: Over={over_prob:.2%}, Under={under_prob:.2%}"
            )

            # Vig removal: pasar todas las odds del mercado a EdgeCalculator
            all_totals_odds = odds.get_all_totals_odds()

            # Evaluate both sides
            picks = []

            # Over
            over_edge = self.edge_calc.calculate(
                over_prob,
                over_odds,
                self.market_type,
                all_market_odds=all_totals_odds if all_totals_odds else None
            )
            over_ev = self.edge_calc.calculate_expected_value(over_prob, over_odds)

            logger.debug(
                f"Over: prob={over_prob:.2%}, odds={over_odds:.2f}, "
                f"edge={over_edge:.4f}, EV={over_ev:.2f}%"
            )

            if over_edge > self.min_edge:
                picks.append(("over", over_odds, over_prob, over_edge))

            # Under
            under_edge = self.edge_calc.calculate(
                under_prob,
                under_odds,
                self.market_type,
                all_market_odds=all_totals_odds if all_totals_odds else None
            )
            under_ev = self.edge_calc.calculate_expected_value(under_prob, under_odds)

            logger.debug(
                f"Under: prob={under_prob:.2%}, odds={under_odds:.2f}, "
                f"edge={under_edge:.4f}, EV={under_ev:.2f}%"
            )

            if under_edge > self.min_edge:
                picks.append(("under", under_odds, under_prob, under_edge))

            # Return best pick
            if not picks:
                logger.debug("No value found (all edges < threshold)")
                return None

            # Get pick with highest edge
            best = max(picks, key=lambda x: x[3])
            selection, outcome_odds, prob, edge = best

            pick = Pick(
                game_id=analysis.game_id,
                market=self.market_type,
                selection=f"{selection}_{line}",  # e.g., "over_2.5" or "under_2.5"
                odds=outcome_odds,
                probability=prob,
                edge=edge,
                confidence=analysis.confidence,
                stake_pct=0.0  # Will be set by KellyCalculator
            )

            logger.info(
                f"✅ VALUE FOUND: {selection.upper()} {line} @ {outcome_odds:.2f}",
                extra={
                    "selection": selection,
                    "line": line,
                    "odds": outcome_odds,
                    "edge": edge,
                    "probability": prob,
                    "confidence": analysis.confidence
                }
            )

            return pick

    def _extract_total_expected(self, analysis: GameAnalysis) -> Optional[float]:
        """
        Extract total expected from projections

        Looks for:
        - "total_goals" (soccer)
        - "total_runs" (MLB)
        - "total_points" (NBA/NFL)
        """
        projections = analysis.projections

        # Try common keys
        for key in ["total_goals", "total_runs", "total_points"]:
            if key in projections and projections[key] is not None:
                return projections[key]

        # Fallback: sum home + away if available
        home_key = None
        away_key = None

        for key in projections:
            if "home" in key.lower():
                home_key = key
            elif "away" in key.lower():
                away_key = key

        if home_key and away_key:
            total = projections[home_key] + projections[away_key]
            logger.debug(
                f"Calculated total from components: {total:.2f}",
                extra={
                    "home": projections[home_key],
                    "away": projections[away_key]
                }
            )
            return total

        return None

    def _get_distribution_type(self, sport: Sport) -> str:
        """
        Determine which probability distribution to use

        Low-scoring sports (soccer, hockey, baseball) → Poisson
        High-scoring sports (NBA, NFL) → Normal
        """
        low_scoring = [Sport.SOCCER]  # Add Sport.MLB, Sport.NHL when implemented

        if sport in low_scoring:
            return "poisson"
        else:
            return "normal"

    def _get_std(self, analysis: GameAnalysis, distribution: str) -> Optional[float]:
        """
        Extrae standard deviation de projections, o retorna default razonable.

        Args:
            analysis: GameAnalysis con projections
            distribution: "poisson" o "normal"

        Returns:
            - None si distribution == "poisson" (no se usa)
            - float con std si distribution == "normal"

        H3 FIX:
        Si distribution == "normal" y projections no tiene "total_std",
        usamos defaults empíricos por deporte:
        - Basketball (NBA): 12.0 puntos de desviación estándar
        - Football (NFL): 14.0 puntos de desviación estándar

        Estos valores están basados en análisis histórico de varianza
        en totales. Los adapters de NBA/NFL deberán calcular std real
        cuando sea posible, pero estos defaults previenen crashes.
        """
        if distribution == "poisson":
            # Poisson no usa std
            return None

        # distribution == "normal"
        projections = analysis.projections

        # 1. Intentar leer de projections (lo correcto)
        if "total_std" in projections:
            std = projections["total_std"]
            logger.debug(
                f"Using std from projections: {std:.2f}",
                extra={"std": std}
            )
            return std

        # 2. Fallback: defaults por deporte
        defaults = {
            Sport.NBA: 12.0,    # Basketball: ~12 puntos de desviación
            Sport.NFL: 14.0,    # Football: ~14 puntos de desviación
            Sport.MLB: 2.5      # Baseball: ~2.5 runs (si se implementa con normal)
        }

        std = defaults.get(analysis.sport)

        if std is not None:
            logger.warning(
                f"total_std not in projections, using default for {analysis.sport.value}: {std:.2f}",
                extra={"sport": analysis.sport.value, "default_std": std}
            )
            return std

        # 3. Si el deporte no está en defaults y requiere normal → error
        logger.error(
            f"Distribution is 'normal' but no std available for sport {analysis.sport.value}",
            extra={"sport": analysis.sport.value}
        )
        raise ValueError(
            f"Cannot use normal distribution for {analysis.sport.value} "
            f"without total_std in projections or default mapping"
        )

    def _validate_inputs(self, analysis: GameAnalysis, odds: OddsData) -> bool:
        """Validate totals-specific inputs"""
        if not super()._validate_inputs(analysis, odds):
            return False

        # Check that we have projections
        if not analysis.projections:
            logger.warning(
                "No projections in GameAnalysis",
                extra={"game_id": analysis.game_id}
            )
            return False

        return True