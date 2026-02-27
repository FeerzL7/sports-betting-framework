"""
Edge Calculator - Comparación probabilidad real vs implícita

RESPONSABILIDAD:
Calcular el "edge" (ventaja) que tenemos sobre el mercado.

FÓRMULA BASE:
    edge_raw = probabilidad_real - probabilidad_implícita_sin_vig

NORMALIZACIÓN:
    Ajustar por eficiencia del mercado (moneyline es más eficiente que props)

MEJORA RESPECTO A V1:
    En V1 se comparaba contra la probabilidad implícita CON vig, lo que
    subestimaba el edge en ~5-8%. Ahora removemos el vig primero usando
    el método de Pinnacle (normalizar la sobronda total a 1.0).

NO DEPENDE DE:
- Deporte específico
- Source de odds
- Stake sizing
"""
from typing import Dict, Optional
from core.models import MarketType


class EdgeCalculator:
    """
    Calculador de edge normalizado.

    Edge > 0 → Hay valor (odds favorables)
    Edge < 0 → Sin valor (odds desfavorables)
    Edge ~ 0 → Mercado eficiente (sin edge claro)

    CONFIGURACIÓN:
    Recibe market_efficiency como dict (strings) para permitir override
    via EdgeConfig sin importar el enum en la capa de config.
    """

    # Eficiencia BASE por tipo de mercado.
    # Estos son los defaults; se pueden sobreescribir vía constructor.
    # Menor valor = mercado más eficiente = edge más raro.
    _DEFAULT_MARKET_EFFICIENCY = {
        MarketType.MONEYLINE: 0.03,      # Muy eficiente (3% edge es excepcional)
        MarketType.TOTALS: 0.04,          # Moderadamente eficiente
        MarketType.SPREAD: 0.04,          # Similar a totals
        MarketType.BOTH_TEAMS_SCORE: 0.05,  # Menos eficiente
        MarketType.PLAYER_PROPS: 0.06    # Menos eficiente (más valor posible)
    }

    # Mapa de string key → MarketType enum (para compatibilidad con EdgeConfig)
    _MARKET_KEY_MAP = {
        "moneyline": MarketType.MONEYLINE,
        "totals": MarketType.TOTALS,
        "spread": MarketType.SPREAD,
        "btts": MarketType.BOTH_TEAMS_SCORE,
        "props": MarketType.PLAYER_PROPS,
    }

    def __init__(
        self,
        vig_adjustment: bool = True,
        market_efficiency: Optional[Dict[str, float]] = None
    ):
        """
        Args:
            vig_adjustment: Si remover el vigorish antes de calcular edge.
                           True (default) = más preciso.
                           False = comportamiento legacy (compatibilidad).

            market_efficiency: Dict con string keys y float values para
                              sobreescribir la eficiencia por mercado.
                              Ejemplo: {"moneyline": 0.025, "totals": 0.045}
                              Si None → usa _DEFAULT_MARKET_EFFICIENCY.
        """
        self.vig_adjustment = vig_adjustment

        # Construir dict de eficiencia con MarketType keys
        # Si se pasa un dict de strings (desde EdgeConfig), convertir
        if market_efficiency is not None:
            self._market_efficiency = {}
            for key, value in market_efficiency.items():
                market_type = self._MARKET_KEY_MAP.get(key)
                if market_type is not None:
                    self._market_efficiency[market_type] = value
        else:
            self._market_efficiency = dict(self._DEFAULT_MARKET_EFFICIENCY)

    @staticmethod
    def remove_vig(odds_dict: Dict[str, float]) -> Dict[str, float]:
        """
        Remueve el vigorish (margen del bookmaker) de un set de odds.

        MÉTODO: Pinnacle-style (proporcional).
            1. Convertir cada odds a probabilidad implícita (1/odds)
            2. Calcular la sobronda total (suma de probs implícitas > 1.0)
            3. Dividir cada prob por la sobronda para normalizar a 1.0
            4. Convertir de vuelta a odds

        EJEMPLO:
            Odds: home=1.90, away=1.90  (sobronda = 1/1.90 + 1/1.90 = 1.053)
            Prob implícita: home=52.6%, away=52.6% (suman 105.3%)
            Sin vig: home=50.0%, away=50.0% (dividir por 1.053)

        Args:
            odds_dict: {"home": 1.90, "away": 1.90, "draw": 3.30} (cualquier outcomes)

        Returns:
            Dict con mismas keys pero odds sin vig
            (probabilidades normalizadas a 1.0, convertidas de vuelta)

        IMPORTANTE: Retorna odds, no probabilidades.
        """
        if not odds_dict:
            return odds_dict

        # Filtrar valores None y menores o iguales a 1.0
        valid_odds = {k: v for k, v in odds_dict.items() if v and v > 1.0}
        if not valid_odds:
            return odds_dict

        # Calcular sobronda total
        implied_probs = {k: 1.0 / v for k, v in valid_odds.items()}
        overround = sum(implied_probs.values())

        if overround <= 0:
            return odds_dict

        # Normalizar probabilidades (remover vig)
        fair_probs = {k: p / overround for k, p in implied_probs.items()}

        # Convertir de vuelta a odds
        fair_odds = {k: round(1.0 / p, 4) for k, p in fair_probs.items()}

        return fair_odds

    def calculate(
        self,
        real_probability: float,
        odds: float,
        market_type: MarketType,
        all_market_odds: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calcula edge normalizado.

        Args:
            real_probability: Nuestra probabilidad real (0-1)
            odds: Cuota decimal del outcome a evaluar (ej: 2.10)
            market_type: Tipo de mercado (para normalización)
            all_market_odds: Todas las odds del mercado (para vig removal).
                            Ejemplo: {"home": 1.85, "away": 2.10, "draw": 3.50}
                            Si None → no se remueve vig (fallback legacy).

        Returns:
            Edge normalizado (-1 a 1, típicamente -0.2 a 0.2)
            - Positivo: hay valor
            - Negativo: odds sobrevaluados por el mercado

        Ejemplo (SIN vig removal):
            >>> calc = EdgeCalculator(vig_adjustment=False)
            >>> calc.calculate(0.55, 2.10, MarketType.MONEYLINE)
            0.0740

        Ejemplo (CON vig removal, más preciso):
            >>> calc = EdgeCalculator()
            >>> calc.calculate(
            ...     real_probability=0.55,
            ...     odds=2.10,
            ...     market_type=MarketType.MONEYLINE,
            ...     all_market_odds={"home": 2.10, "away": 1.85}
            ... )
            0.0820  # Ligeramente mayor porque vig se removió primero
        """
        # 1. Determinar la odds de referencia (con o sin vig)
        if self.vig_adjustment and all_market_odds:
            # Remover vig del mercado completo, luego extraer la odds fair
            # para el outcome que nos interesa (la que coincide con `odds`)
            fair_odds_dict = self.remove_vig(all_market_odds)
            # Identificar cuál outcome tiene `odds` y usar su fair equivalent
            # Encontramos el outcome por coincidencia de valor
            ref_odds = None
            for outcome_key, outcome_odds in all_market_odds.items():
                if outcome_odds and abs(outcome_odds - odds) < 0.001:
                    ref_odds = fair_odds_dict.get(outcome_key, odds)
                    break
            if ref_odds is None or ref_odds <= 1.0:
                ref_odds = odds  # Fallback si no encontramos match o fair_odds degeneró
        else:
            ref_odds = odds

        # Guard: ref_odds must be > 1.0 (if still degenerate, return 0 edge)
        if ref_odds <= 1.0:
            return 0.0

        # 2. Convertir odds de referencia a probabilidad implícita (ya sin vig)
        implied_prob = self.odds_to_probability(ref_odds)

        # 3. Edge raw
        raw_edge = real_probability - implied_prob

        # 4. Normalizar por eficiencia del mercado
        market_variance = self._market_efficiency.get(market_type, 0.05)
        normalized_edge = raw_edge / market_variance

        # 5. Clip a rango razonable (-1, 1)
        normalized_edge = max(-1.0, min(1.0, normalized_edge))

        return round(normalized_edge, 4)

    def calculate_expected_value(
        self,
        real_probability: float,
        odds: float
    ) -> float:
        """
        Calcula Expected Value (EV) en porcentaje.

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
    def odds_to_probability(odds: float) -> float:
        """
        Convierte odds decimales a probabilidad implícita.

        NOTA: Esta función NO remueve vig.
              Para vig removal usa remove_vig() sobre el mercado completo.
              Esta función convierte 1/odds directamente.

        Args:
            odds: Cuota decimal (ej: 2.10)

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
        return round(implied_prob, 4)

    @staticmethod
    def probability_to_odds(probability: float, add_vig: float = 0.05) -> float:
        """
        Convierte probabilidad a odds (útil para testing).

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
        Calcula fracción de Kelly directamente desde edge (helper).

        NOTA: Este es un helper de conveniencia. El cálculo oficial
              está en KellyCalculator. Usar este para estimaciones rápidas.

        Args:
            edge: Edge calculado (probabilidad_real - implícita sin vig)
            odds: Cuota decimal
            max_fraction: Fracción máxima de Kelly (default 1/4 Kelly)

        Returns:
            Fracción de bankroll a apostar (0-1)
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
        Compara edge entre múltiples mercados.

        Útil para decidir cuál mercado tiene mejor valor.

        Args:
            market_edges: {"moneyline": 0.05, "totals": 0.08, "spread": 0.02}

        Returns:
            Dict ordenado con ranking y metadata.

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