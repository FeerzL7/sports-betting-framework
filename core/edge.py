"""
Edge Calculator - Comparación probabilidad real vs implícita

RESPONSABILIDAD:
Calcular el "edge" (ventaja) que tenemos sobre el mercado.

FÓRMULA BASE:
edge_raw = probabilidad_real - probabilidad_implícita

NORMALIZACIÓN:
Ajustar por eficiencia del mercado (moneyline es más eficiente que props)

NO DEPENDE DE:
- Deporte específico
- Source de odds
- Stake sizing
"""
from typing import Dict, Optional
from core.models import MarketType


class EdgeCalculator:
    """
    Calculador de edge normalizado

    Edge > 0 → Hay valor (odds favorables)
    Edge < 0 → Sin valor (odds desfavorables)
    Edge ~ 0 → Mercado eficiente (sin edge claro)
    """

    # Eficiencia por tipo de mercado (basado en estudios empíricos)
    # Menor valor = mercado más eficiente = edge más raro
    # M3 FIX: Estos son los valores reales usados en cálculos.
    # EdgeConfig (config layer) define los mismos valores pero con string keys.
    MARKET_EFFICIENCY = {
        MarketType.MONEYLINE: 0.03,      # Muy eficiente (3% edge es excepcional)
        MarketType.TOTALS: 0.04,          # Moderadamente eficiente
        MarketType.SPREAD: 0.04,          # Similar a totals
        MarketType.BOTH_TEAMS_SCORE: 0.05,  # Menos eficiente
        MarketType.PLAYER_PROPS: 0.06    # Menos eficiente (más valor posible)
    }

    def __init__(self, vig_adjustment: bool = True):
        """
        Args:
            vig_adjustment: Si ajustar por vigorish implícito
        """
        self.vig_adjustment = vig_adjustment

    def calculate(
        self,
        real_probability: float,
        odds: float,
        market_type: MarketType
    ) -> float:
        """
        Calcula edge normalizado

        Args:
            real_probability: Nuestra probabilidad real (0-1)
            odds: Cuota decimal (ej: 2.10)
            market_type: Tipo de mercado (para normalización)

        Returns:
            Edge normalizado (-1 a 1, típicamente -0.2 a 0.2)
            - Positivo: hay valor
            - Negativo: odds sobrevaluados por el mercado

        Ejemplo:
            >>> calc = EdgeCalculator()
            >>> calc.calculate(
            ...     real_probability=0.55,
            ...     odds=2.10,  # Implica ~47.6% probabilidad
            ...     market_type=MarketType.MONEYLINE
            ... )
            0.0740  # Edge positivo del 7.4% (normalizado)
        """
        # 1. Convertir odds a probabilidad implícita
        implied_prob = self.odds_to_probability(odds)

        # 2. Edge raw
        raw_edge = real_probability - implied_prob

        # 3. Normalizar por eficiencia del mercado
        market_variance = self.MARKET_EFFICIENCY.get(market_type, 0.05)
        normalized_edge = raw_edge / market_variance

        # 4. Clip a rango razonable (-1, 1)
        normalized_edge = max(-1.0, min(1.0, normalized_edge))

        return round(normalized_edge, 4)

    def calculate_expected_value(
        self,
        real_probability: float,
        odds: float
    ) -> float:
        """
        Calcula Expected Value (EV) en porcentaje

        EV% = (probabilidad_real * cuota - 1) * 100

        Args:
            real_probability: Nuestra probabilidad (0-1)
            odds: Cuota decimal

        Returns:
            EV en porcentaje (ej: 5.2 = 5.2% de ganancia esperada)

        Ejemplo:
            >>> calc = EdgeCalculator()
            >>> calc.calculate_expected_value(0.55, 2.10)
            15.5  # 15.5% EV
        """
        ev = (real_probability * odds - 1) * 100
        return round(ev, 2)

    @staticmethod
    def odds_to_probability(odds: float, remove_vig: bool = False) -> float:
        """
        Convierte odds decimales a probabilidad implícita

        Args:
            odds: Cuota decimal (ej: 2.10)
            remove_vig: Si intentar remover vigorish

        Returns:
            Probabilidad implícita (0-1)

        Ejemplo:
            >>> EdgeCalculator.odds_to_probability(2.10)
            0.4762

            >>> EdgeCalculator.odds_to_probability(1.50)
            0.6667
        """
        if odds <= 1.0:
            raise ValueError(f"Odds inválidas: {odds}. Deben ser > 1.0")

        implied_prob = 1 / odds

        # TODO: Implementar remoción de vig en v2
        # Requiere conocer odds de todos los outcomes del mercado
        if remove_vig:
            pass  # Placeholder para futura implementación

        return round(implied_prob, 4)

    @staticmethod
    def probability_to_odds(probability: float, add_vig: float = 0.05) -> float:
        """
        Convierte probabilidad a odds (útil para testing)

        Args:
            probability: Probabilidad real (0-1)
            add_vig: Vigorish a agregar (bookmaker margin)

        Returns:
            Odds decimal

        Ejemplo:
            >>> EdgeCalculator.probability_to_odds(0.50, add_vig=0.05)
            1.90  # 50% real → 52.6% con vig → 1.90 odds
        """
        if not 0 < probability < 1:
            raise ValueError(f"Probabilidad debe estar entre 0 y 1: {probability}")

        # Ajustar probabilidad por vig
        adjusted_prob = probability * (1 + add_vig)
        adjusted_prob = min(adjusted_prob, 0.99)  # Cap al 99%

        odds = 1 / adjusted_prob
        return round(odds, 2)

    def kelly_fraction_from_edge(
        self,
        edge: float,
        odds: float,
        max_fraction: float = 0.25
    ) -> float:
        """
        Calcula fracción de Kelly directamente desde edge

        NOTA: Este es un helper. El cálculo oficial está en KellyCalculator.

        Args:
            edge: Edge calculado (probabilidad_real - implícita)
            odds: Cuota decimal
            max_fraction: Fracción máxima de Kelly (default 1/4 Kelly)

        Returns:
            Fracción de bankroll a apostar (0-1)

        Fórmula Kelly:
            f = (p * (b + 1) - 1) / b
            donde b = odds - 1
        """
        if edge <= 0:
            return 0.0

        b = odds - 1
        implied_prob = self.odds_to_probability(odds)
        real_prob = implied_prob + edge

        kelly = (real_prob * (b + 1) - 1) / b

        # Aplicar fracción conservadora
        kelly = max(0, kelly) * max_fraction

        return round(kelly, 4)

    def compare_markets(
        self,
        market_edges: Dict[str, float]
    ) -> Dict[str, Dict]:
        """
        Compara edge entre múltiples mercados

        Útil para decidir cuál mercado tiene mejor valor

        Args:
            market_edges: {"moneyline": 0.05, "totals": 0.08, "spread": 0.02}

        Returns:
            Dict ordenado con ranking y metadata

        Ejemplo:
            >>> calc = EdgeCalculator()
            >>> calc.compare_markets({
            ...     "moneyline": 0.05,
            ...     "totals": 0.08,
            ...     "spread": 0.02
            ... })
            {
                "totals": {"edge": 0.08, "rank": 1, "tier": "excellent"},
                "moneyline": {"edge": 0.05, "rank": 2, "tier": "good"},
                "spread": {"edge": 0.02, "rank": 3, "tier": "marginal"}
            }
        """
        # Ordenar por edge
        sorted_markets = sorted(
            market_edges.items(),
            key=lambda x: x[1],
            reverse=True
        )

        result = {}
        for rank, (market, edge) in enumerate(sorted_markets, 1):
            # Clasificar tier de edge
            if edge >= 0.10:
                tier = "excellent"
            elif edge >= 0.05:
                tier = "good"
            elif edge >= 0.02:
                tier = "marginal"
            else:
                tier = "no_value"

            result[market] = {
                "edge": edge,
                "rank": rank,
                "tier": tier
            }

        return result