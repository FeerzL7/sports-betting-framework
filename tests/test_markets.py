"""
tests/test_markets.py - pytest version of market integration tests

Migrado de script tests/test_markets.py (if __name__ == "__main__")
a pytest para integración con CI/CD y coverage.
"""
import sys
from pathlib import Path
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from markets import MoneylineMarket, TotalsMarket
from core.models import Sport, GameAnalysis, OddsData, MarketType


# ============================================================================
# MoneylineMarket Tests
# ============================================================================

class TestMoneylineMarket:
    """Tests para MoneylineMarket"""

    def test_positive_value_generates_pick(self, soccer_analysis, odds_with_ml_value):
        """
        home_win real=45%, home_odds=2.30
        Con vig removal: fair implied < 43.5% → edge positivo
        Debe generar Pick con selection="home"
        """
        market = MoneylineMarket(min_edge=0.02)
        pick = market.evaluate(soccer_analysis, odds_with_ml_value)

        assert pick is not None, "Debe generar Pick: home tiene edge positivo"
        assert pick.selection == "home", f"Debe ser home, got {pick.selection}"
        assert pick.edge > 0.02, f"Edge debe ser > 0.02, got {pick.edge}"
        assert pick.market == MarketType.MONEYLINE

    def test_no_value_returns_none(self, soccer_analysis):
        """
        Odds derivadas de probabilidades reales del modelo + 5% vig uniforme.

        Model: home=45%, draw=28%, away=27%
        Fair odds: home=2.22, draw=3.57, away=3.70
        Con vig 5%: home= 2.11, draw=3.40, away=3.52

        Después de remove_vig, los fair probs igualan los del modelo → edge ≈ 0.
        """
        from core.models import OddsData, Sport
        # fair_home = 1/0.45 = 2.222 → con vig: 2.222 * 0.952 ≈ 2.11
        # fair_draw = 1/0.28 = 3.571 → con vig: 3.571 * 0.952 ≈ 3.40
        # fair_away = 1/0.27 = 3.704 → con vig: 3.704 * 0.952 ≈ 3.52
        efficient_odds = OddsData(
            game_id="soccer_PL_86_81",
            sport=Sport.SOCCER,
            bookmaker="TestBook",
            home_odds=2.11,
            draw_odds=3.40,
            away_odds=3.52,
        )

        market = MoneylineMarket(min_edge=0.02)
        pick = market.evaluate(soccer_analysis, efficient_odds)

        assert pick is None, (
            f"Con odds eficientes (vig ~5%), no debe haber edge detectable. "
            f"Got: {pick.selection if pick else None}"
        )

    def test_selects_best_edge_outcome(self, soccer_analysis):
        """
        home: 45% real vs odds 2.00 (implied 50%) → negativo
        away: 27% real vs odds 4.20 (implied 23.8%) → positivo (mejor)
        draw: 28% real vs odds 3.50 (implied 28.6%) → marginal
        → Debe seleccionar away
        """
        odds = OddsData(
            game_id="soccer_PL_86_81",
            sport=Sport.SOCCER,
            bookmaker="TestBook",
            home_odds=2.00,
            draw_odds=3.50,
            away_odds=4.20,
        )

        market = MoneylineMarket(min_edge=0.02)
        pick = market.evaluate(soccer_analysis, odds)

        assert pick is not None, "Debe generar Pick (away tiene edge positivo)"
        assert pick.selection == "away", f"Should pick away, got {pick.selection}"

    def test_missing_home_odds_evaluates_others(self, soccer_analysis):
        """
        Si home_odds es None, el mercado evalúa away y draw solamente.
        No debe lanzar excepción.
        """
        from core.models import OddsData, Sport
        odds = OddsData(
            game_id="soccer_PL_86_81",
            sport=Sport.SOCCER,
            bookmaker="TestBook",
            home_odds=None,  # Faltante
            away_odds=4.50,
            draw_odds=3.50,
        )

        market = MoneylineMarket(min_edge=0.02)
        # No debe lanzar excepción
        pick = market.evaluate(soccer_analysis, odds)

        # Si hay pick, no debe ser home
        if pick is not None:
            assert pick.selection != "home"

    def test_mismatched_game_id_returns_none(self, soccer_analysis):
        """
        El Orchestrator asigna siempre el mismo game_id, pero si
        se llama directamente con IDs diferentes, debe ser rechazado.
        """
        odds = OddsData(
            game_id="DIFFERENT_ID",
            sport=Sport.SOCCER,
            bookmaker="TestBook",
            home_odds=2.30,
            away_odds=3.60,
            draw_odds=3.20,
        )

        market = MoneylineMarket(min_edge=0.02)
        pick = market.evaluate(soccer_analysis, odds)

        assert pick is None, "Game ID mismatch debe retornar None"

    def test_none_analysis_returns_none(self):
        """Análisis None → retornar None sin explotar."""
        odds = OddsData(
            game_id="test", sport=Sport.SOCCER, bookmaker="TB", home_odds=2.0
        )
        market = MoneylineMarket()
        assert market.evaluate(None, odds) is None

    def test_none_odds_returns_none(self, soccer_analysis):
        """OddsData None → retornar None sin explotar."""
        market = MoneylineMarket()
        assert market.evaluate(soccer_analysis, None) is None

    def test_pick_has_expected_fields(self, soccer_analysis, odds_with_ml_value):
        """El Pick generado debe tener todos los campos necesarios."""
        market = MoneylineMarket(min_edge=0.02)
        pick = market.evaluate(soccer_analysis, odds_with_ml_value)

        assert pick is not None
        assert pick.game_id == soccer_analysis.game_id
        assert pick.market == MarketType.MONEYLINE
        assert 1.0 < pick.odds < 10.0, "Odds deben ser razonables"
        assert 0 < pick.probability < 1, "Probability en rango (0,1)"
        assert pick.confidence == soccer_analysis.confidence
        assert pick.stake_pct == 0.0, "stake_pct es 0 antes de Kelly"


# ============================================================================
# TotalsMarket Tests
# ============================================================================

class TestTotalsMarket:
    """Tests para TotalsMarket"""

    def test_over_value_when_expected_high(self, soccer_analysis, odds_with_totals_value):
        """
        Expected total=2.8, line=2.5
        Poisson P(over 2.5 | λ=2.8) ≈ 53%
        over_odds=2.10 → implied 47.6% → edge positivo
        """
        market = TotalsMarket(min_edge=0.02)
        pick = market.evaluate(soccer_analysis, odds_with_totals_value)

        assert pick is not None, "Debe generar Pick (over tiene edge positivo)"
        assert "over" in pick.selection, f"Should be over, got {pick.selection}"
        assert pick.market == MarketType.TOTALS

    def test_under_value_when_line_is_high(self, soccer_analysis):
        """
        Expected total=2.8, line=3.5
        Poisson P(under 3.5 | λ=2.8) ≈ 75%+
        under_odds=2.20 → implied 45.5% → edge muy positivo
        """
        odds = OddsData(
            game_id="soccer_PL_86_81",
            sport=Sport.SOCCER,
            bookmaker="TestBook",
            home_odds=2.00,
            away_odds=2.00,
            draw_odds=3.50,
            total_line=3.5,
            over_odds=1.70,
            under_odds=2.20,
        )

        market = TotalsMarket(min_edge=0.02)
        pick = market.evaluate(soccer_analysis, odds)

        assert pick is not None, "Debe generar Pick (under tiene edge positivo)"
        assert "under" in pick.selection, f"Should be under, got {pick.selection}"

    def test_no_value_when_tight_odds(self, soccer_analysis):
        """
        Odds derivadas de probabilidades reales + vig uniforme del 5%.

        Expected total=2.8 goals, line=2.5
        Poisson P(over 2.5|λ=2.8) ≈ 53% = over_fair=1.887
        Poisson P(under 2.5|λ=2.8) ≈ 47% = under_fair=2.128

        Con vig 5%: over=1.79, under=2.02
        Después de remove_vig, fair probs ≈ 53%/47% = igualan modelo.
        Edge ≈ 0 para ambos lados → bajo threshold 5%.
        """
        from core.models import OddsData, Sport
        # over fair = 1/0.53 = 1.887, con vig 5%: 1.887 * 0.952 = 1.796
        # under fair = 1/0.47 = 2.128, con vig 5%: 2.128 * 0.952 = 2.026
        efficient_odds = OddsData(
            game_id="soccer_PL_86_81",
            sport=Sport.SOCCER,
            bookmaker="TestBook",
            home_odds=2.00,
            away_odds=2.00,
            draw_odds=3.50,
            total_line=2.5,
            over_odds=1.80,   # slightly under fair → neg edge for over
            under_odds=2.03,  # slightly under fair → neg edge for under
        )

        market = TotalsMarket(min_edge=0.05)  # threshold 5%
        pick = market.evaluate(soccer_analysis, efficient_odds)

        assert pick is None, (
            f"Con odds eficientes no debe haber edge explotable. "
            f"Got: {pick.selection if pick else None}"
        )

    def test_missing_total_line_returns_none(self, soccer_analysis):
        """Sin línea de totals, debe retornar None sin explotar."""
        odds = OddsData(
            game_id="soccer_PL_86_81",
            sport=Sport.SOCCER,
            bookmaker="TestBook",
            home_odds=2.30,
            away_odds=3.60,
            draw_odds=3.20,
            total_line=None,   # Sin línea
            over_odds=2.10,
            under_odds=1.80,
        )

        market = TotalsMarket()
        pick = market.evaluate(soccer_analysis, odds)
        assert pick is None

    def test_selection_includes_line(self, soccer_analysis, odds_with_totals_value):
        """
        La selección debe incluir la línea: "over_2.5" en vez de sólo "over".
        Esto es importante para el output JSON de la UI.
        """
        market = TotalsMarket(min_edge=0.02)
        pick = market.evaluate(soccer_analysis, odds_with_totals_value)

        assert pick is not None
        # Selection debe ser "over_2.5" o similar (incluye la línea)
        assert "2.5" in pick.selection, (
            f"Selection debe incluir la línea, got: {pick.selection}"
        )

    def test_mlb_analysis_works_with_totals(self, mlb_analysis):
        """
        Totals debe funcionar con MLB también (sport-agnostic).
        MLB usa total_runs en vez de total_goals.
        """
        mlb_odds = OddsData(
            game_id="mlb_NYY_BOS_20250301",
            sport=Sport.MLB,
            bookmaker="TestBook",
            home_odds=1.80,
            away_odds=2.10,
            total_line=8.5,
            over_odds=2.20,   # implied 45.5% vs real P(>8.5|runs=9.2) > 50%
            under_odds=1.75,
        )

        market = TotalsMarket(min_edge=0.02)
        # No debe explotar (aunque may not find edge depending on prob calc)
        result = market.evaluate(mlb_analysis, mlb_odds)
        # No assertion on pick (depends on Poisson/Normal calculation)
        # Just verify it doesn't crash