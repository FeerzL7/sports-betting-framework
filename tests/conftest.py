"""
conftest.py - Shared pytest fixtures for all tests

Fixtures disponibles:
    soccer_analysis: GameAnalysis válido para soccer con probabilidades con valor
    balanced_analysis: GameAnalysis donde ningún mercado tiene valor
    odds_with_ml_value: OddsData donde home ML tiene edge positivo
    odds_with_totals_value: OddsData donde over tiene edge positivo
    odds_no_value: OddsData con odds tan ajustadas que no hay edge en ningún outcome
    odds_partial: OddsData con draw=None y under=None
"""
import sys
from pathlib import Path
from datetime import datetime
import pytest

# Asegurar que el proyecto root esté en el path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.models import Sport, GameAnalysis, OddsData, MarketType


# ============================================================================
# GameAnalysis Fixtures
# ============================================================================

@pytest.fixture
def soccer_analysis() -> GameAnalysis:
    """
    Soccer game con ventaja para home en moneyline y over en totals.

    Probabilities: home_win=0.45, draw=0.28, away_win=0.27
    Projections: total_goals=2.8 (lo suficiente para over 2.5)
    """
    return GameAnalysis(
        sport=Sport.SOCCER,
        league="PL",
        game_id="soccer_PL_86_81",
        home_team="Arsenal",
        away_team="Chelsea",
        start_time=datetime(2025, 3, 1, 15, 0, 0),
        probabilities={
            "home_win": 0.45,
            "draw": 0.28,
            "away_win": 0.27,
        },
        projections={
            "total_goals": 2.8,
            "home_goals": 1.6,
            "away_goals": 1.2,
        },
        confidence=0.85,
        model_version="soccer_xg_test_v1.0"
    )


@pytest.fixture
def balanced_analysis() -> GameAnalysis:
    """50/50 match donde ningún mercado debería tener edge con odds normales."""
    return GameAnalysis(
        sport=Sport.SOCCER,
        league="PL",
        game_id="soccer_PL_balanced",
        home_team="Liverpool",
        away_team="Man City",
        start_time=datetime(2025, 3, 2, 17, 30, 0),
        probabilities={
            "home_win": 0.40,
            "draw": 0.28,
            "away_win": 0.32,
        },
        projections={
            "total_goals": 2.5,
            "home_goals": 1.3,
            "away_goals": 1.2,
        },
        confidence=0.70,
        model_version="soccer_xg_test_v1.0"
    )


@pytest.fixture
def mlb_analysis() -> GameAnalysis:
    """MLB game para verificar que el core maneja sport=MLB correctamente."""
    return GameAnalysis(
        sport=Sport.MLB,
        league="MLB",
        game_id="mlb_NYY_BOS_20250301",
        home_team="New York Yankees",
        away_team="Boston Red Sox",
        start_time=datetime(2025, 3, 1, 19, 5, 0),
        probabilities={
            "home_win": 0.55,
            "away_win": 0.45,
        },
        projections={
            "total_runs": 9.2,
            "home_runs": 4.8,
            "away_runs": 4.4,
        },
        confidence=0.78,
        model_version="mlb_monte_carlo_v1.0"
    )


# ============================================================================
# OddsData Fixtures
# ============================================================================

@pytest.fixture
def odds_with_ml_value() -> OddsData:
    """
    Odds donde home ML tiene edge positivo.

    home real=45%, home_odds=2.30 → implied raw=43.5%
    Con vig removal de mercado (2.30/3.60/3.20):
        overround ≈ 1.087
        fair home prob ≈ 40.0% (después de remove_vig)
    Edge real = 45% - 40% = +5% (positivo)
    """
    return OddsData(
        game_id="soccer_PL_86_81",
        sport=Sport.SOCCER,
        bookmaker="TestBook",
        home_odds=2.30,
        away_odds=3.60,
        draw_odds=3.20,
        total_line=2.5,
        over_odds=1.90,
        under_odds=1.95,
    )


@pytest.fixture
def odds_with_totals_value() -> OddsData:
    """
    Odds donde over 2.5 tiene edge positivo.

    Expected total=2.8, line=2.5
    over_odds=2.10 → implied=47.6% mientras Poisson P(>2.5|λ=2.8) ≈ 53%
    """
    return OddsData(
        game_id="soccer_PL_86_81",
        sport=Sport.SOCCER,
        bookmaker="TestBook",
        home_odds=2.00,
        away_odds=2.00,
        draw_odds=3.50,
        total_line=2.5,
        over_odds=2.10,
        under_odds=1.80,
    )


@pytest.fixture
def odds_no_value() -> OddsData:
    """
    Odds muy ajustadas (alta vigorish). Ningún outcome tiene edge real.

    home_odds=1.70 → implied 58.8% vs real 45% → negativo
    """
    return OddsData(
        game_id="soccer_PL_86_81",
        sport=Sport.SOCCER,
        bookmaker="TestBook",
        home_odds=1.70,
        away_odds=2.80,
        draw_odds=2.60,
        total_line=2.5,
        over_odds=1.75,
        under_odds=2.10,
    )


@pytest.fixture
def odds_partial() -> OddsData:
    """OddsData con draw=None y under=None (datos parciales)."""
    return OddsData(
        game_id="soccer_PL_86_81",
        sport=Sport.SOCCER,
        bookmaker="TestBook",
        home_odds=2.30,
        away_odds=3.60,
        draw_odds=None,      # Faltante
        total_line=2.5,
        over_odds=2.10,
        under_odds=None,     # Faltante
    )
