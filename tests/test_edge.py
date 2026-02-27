"""
tests/test_edge.py - Unit tests for EdgeCalculator

Cubre:
- Vig removal (Pinnacle-style normalization)
- Edge calculation with and without vig
- EV calculation
- odds_to_probability conversion
- Edge comparison across markets
"""
import sys
from pathlib import Path
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.edge import EdgeCalculator
from core.models import MarketType


# ============================================================================
# Fixtures locales
# ============================================================================

@pytest.fixture
def calc():
    """EdgeCalculator con vig adjustment activado (default)."""
    return EdgeCalculator(vig_adjustment=True)


@pytest.fixture
def calc_no_vig():
    """EdgeCalculator sin vig adjustment (comportamiento legacy)."""
    return EdgeCalculator(vig_adjustment=False)


# ============================================================================
# Vig Removal Tests
# ============================================================================

class TestVigRemoval:
    """Prueba el método estático remove_vig()"""

    def test_two_way_market_removes_vig(self):
        """
        odds home=1.90, away=1.90
        overround = 1/1.90 + 1/1.90 = 1.0526
        fair probs: 50.0% each
        fair odds: 2.0 each
        """
        fair_odds = EdgeCalculator.remove_vig({
            "home": 1.90,
            "away": 1.90
        })

        assert abs(fair_odds["home"] - 2.0) < 0.01
        assert abs(fair_odds["away"] - 2.0) < 0.01

    def test_three_way_market_removes_vig(self):
        """
        Soccer 1X2 con overround típico de ~8%.
        Después del vig removal, las probs deben sumar exactamente 1.0.
        """
        raw_odds = {
            "home": 2.30,
            "draw": 3.20,
            "away": 3.60
        }
        fair_odds = EdgeCalculator.remove_vig(raw_odds)

        # Verificar que las probabilidades fair sumen 1.0
        fair_probs = {k: 1 / v for k, v in fair_odds.items()}
        prob_sum = sum(fair_probs.values())
        assert abs(prob_sum - 1.0) < 0.001, (
            f"Fair probs should sum to 1.0, got {prob_sum:.4f}"
        )

    def test_remove_vig_fair_odds_are_longer(self):
        """Las fair odds deben ser mayores o iguales a las originales."""
        raw_odds = {"home": 1.85, "away": 2.05}
        fair_odds = EdgeCalculator.remove_vig(raw_odds)

        # Con vig, fair odds > raw odds
        assert fair_odds["home"] >= raw_odds["home"]
        assert fair_odds["away"] >= raw_odds["away"]

    def test_empty_dict_returns_empty(self):
        """remove_vig no debe explotar con dict vacío."""
        result = EdgeCalculator.remove_vig({})
        assert result == {}

    def test_single_outcome_returns_fair_1_0(self):
        """Con un solo outcome, la prob fair es 1.0 → fair_odds = 1.0."""
        fair = EdgeCalculator.remove_vig({"outcome": 2.00})
        assert abs(fair["outcome"] - 1.0) < 0.001


# ============================================================================
# Edge Calculation Tests
# ============================================================================

class TestEdgeCalculation:
    """Prueba EdgeCalculator.calculate() con y sin vig removal."""

    def test_positive_edge_without_vig(self, calc_no_vig):
        """
        Sin vig removal (legacy):
        real_prob=0.55, odds=2.10 → implied=47.6%
        raw_edge = 55% - 47.6% = 7.4%
        normalized = 7.4% / 3% (MONEYLINE efficiency) = 2.47
        → clipped a 1.0
        """
        edge = calc_no_vig.calculate(0.55, 2.10, MarketType.MONEYLINE)
        assert edge > 0, "Edge debe ser positivo cuando real_prob > implied"

    def test_negative_edge_without_vig(self, calc_no_vig):
        """
        real_prob=0.30, odds=2.10 → implied=47.6%
        raw_edge = 30% - 47.6% = -17.6% → negativo
        """
        edge = calc_no_vig.calculate(0.30, 2.10, MarketType.MONEYLINE)
        assert edge < 0, "Edge debe ser negativo cuando real_prob < implied"

    def test_edge_with_vig_removal_is_more_accurate(self, calc):
        """
        Con vig removal, la fair_odds es mayor que raw → implied prob es menor
        → el edge calculado es más generoso (más preciso).

        home_odds=2.30 en mercado {home:2.30, away:3.60, draw:3.20}
        fair_home_odds > 2.30 → fair_implied_prob < 43.5%
        → edge(vig=True) > edge(vig=False) para mismo real_prob
        """
        all_odds = {"home": 2.30, "away": 3.60, "draw": 3.20}

        calc_novig = EdgeCalculator(vig_adjustment=False)

        edge_with_vig = calc.calculate(
            0.45, 2.30, MarketType.MONEYLINE, all_odds
        )
        edge_no_vig = calc_novig.calculate(
            0.45, 2.30, MarketType.MONEYLINE
        )

        assert edge_with_vig > edge_no_vig, (
            "Vig removal should increase edge (fair implied prob is lower)"
        )

    def test_edge_clipped_to_minus_one(self, calc):
        """Edge nunca debe ser menor que -1."""
        edge = calc.calculate(0.01, 1.01, MarketType.MONEYLINE)
        assert edge >= -1.0

    def test_edge_clipped_to_one(self, calc):
        """Edge nunca debe ser mayor que 1."""
        edge = calc.calculate(0.99, 100.0, MarketType.MONEYLINE)
        assert edge <= 1.0

    def test_near_zero_edge_for_fair_market(self, calc_no_vig):
        """
        real_prob = 1/odds (mercado eficiente perfecto).
        raw_edge ≈ 0 → normalized ≈ 0.
        """
        odds = 2.00
        real_prob = 1 / odds  # 50% exacto
        edge = calc_no_vig.calculate(real_prob, odds, MarketType.MONEYLINE)
        assert abs(edge) < 0.01, (
            f"Edge para mercado justo debe ser ~0, got {edge}"
        )


# ============================================================================
# EV Calculation Tests
# ============================================================================

class TestEVCalculation:
    """Prueba calculate_expected_value()"""

    def test_positive_ev(self, calc):
        """
        real_prob=0.55, odds=2.10
        EV = (0.55 * 2.10 - 1) * 100 = 15.5%
        """
        ev = calc.calculate_expected_value(0.55, 2.10)
        assert abs(ev - 15.5) < 0.1

    def test_negative_ev(self, calc):
        """
        real_prob=0.40, odds=2.10
        EV = (0.40 * 2.10 - 1) * 100 = -16%
        """
        ev = calc.calculate_expected_value(0.40, 2.10)
        assert ev < 0

    def test_break_even_ev(self, calc):
        """
        real_prob = 1/odds → EV = 0
        """
        odds = 2.00
        ev = calc.calculate_expected_value(0.50, odds)
        assert abs(ev) < 0.1


# ============================================================================
# Odds Conversion Tests
# ============================================================================

class TestOddsConversion:
    """Prueba odds_to_probability() y probability_to_odds()"""

    def test_odds_to_probability_basic(self):
        """1/2.00 = 0.5"""
        prob = EdgeCalculator.odds_to_probability(2.00)
        assert abs(prob - 0.5) < 0.001

    def test_odds_to_probability_favourite(self):
        """1/1.50 = 0.6667"""
        prob = EdgeCalculator.odds_to_probability(1.50)
        assert abs(prob - 0.6667) < 0.001

    def test_odds_to_probability_invalid(self):
        """Odds <= 1.0 deben levantar ValueError."""
        with pytest.raises(ValueError):
            EdgeCalculator.odds_to_probability(1.0)

        with pytest.raises(ValueError):
            EdgeCalculator.odds_to_probability(0.5)

    def test_probability_to_odds_roundtrip(self):
        """
        Convertir prob → odds → prob (sin vig) debe dar valor similar.
        """
        original_prob = 0.55
        odds = EdgeCalculator.probability_to_odds(original_prob, add_vig=0.0)
        recovered_prob = EdgeCalculator.odds_to_probability(odds)
        assert abs(recovered_prob - original_prob) < 0.01


# ============================================================================
# Market Efficiency Config Tests
# ============================================================================

class TestMarketEfficiencyConfig:
    """Prueba que la eficiencia de mercado sea injectable."""

    def test_custom_efficiency_affects_normalization(self):
        """
        Un mercado con menor eficiencia normaliza el mismo edge bruto
        a un valor mayor (más fácil de superar el threshold).
        """
        default_calc = EdgeCalculator()  # moneyline efficiency = 0.03
        strict_calc = EdgeCalculator(
            market_efficiency={"moneyline": 0.01}  # más estricto
        )

        raw_prob = 0.45
        odds = 2.30  # implied ~43.5%

        edge_default = default_calc.calculate(raw_prob, odds, MarketType.MONEYLINE)
        edge_strict = strict_calc.calculate(raw_prob, odds, MarketType.MONEYLINE)

        # Con eficiencia más baja (0.01 vs 0.03), el mismo edge bruto
        # produce un edge normalizado MAYOR (dividido por número menor)
        assert edge_strict > edge_default, (
            "Lower market efficiency → higher normalized edge for same raw edge"
        )

    def test_default_efficiency_applied_when_not_provided(self):
        """Sin config, debe usar los defaults internos."""
        calc = EdgeCalculator()
        # Verificar que existe eficiencia para todos los MarketTypes
        for market_type in MarketType:
            # Debe calcular sin error
            edge = calc.calculate(0.30, 2.00, market_type)
            assert -1.0 <= edge <= 1.0
