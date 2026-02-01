"""
Markets Integration Test

EJECUTAR:
    python -m tests.test_markets
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from markets import MoneylineMarket, TotalsMarket
from core.models import Sport, GameAnalysis, OddsData, MarketType
from datetime import datetime
from utils import get_logger, log_startup, log_shutdown

logger = get_logger(__name__)


def create_mock_analysis() -> GameAnalysis:
    """Create mock GameAnalysis for testing
    
    Simula output real de ProbabilityEngine.from_poisson()
    que usa claves "home_win" / "away_win" (no "home"/"away")
    """
    return GameAnalysis(
        sport=Sport.SOCCER,
        league="PL",
        game_id="test_game_123",
        home_team="Arsenal",
        away_team="Chelsea",
        start_time=datetime.now(),
        probabilities={
            "home_win": 0.45,   # Formato real de from_poisson
            "draw": 0.28,
            "away_win": 0.27
        },
        projections={
            "total_goals": 2.8,
            "home_goals": 1.6,
            "away_goals": 1.2
        },
        confidence=0.85,
        model_version="test_v1.0"
    )


def create_mock_odds(
    home_odds: float = 2.20,
    draw_odds: float = 3.50,
    away_odds: float = 3.60,
    total_line: float = 2.5,
    over_odds: float = 1.90,
    under_odds: float = 1.95
) -> OddsData:
    """Create mock OddsData for testing"""
    return OddsData(
        game_id="test_game_123",
        sport=Sport.SOCCER,
        bookmaker="TestBook",
        home_odds=home_odds,
        draw_odds=draw_odds,
        away_odds=away_odds,
        total_line=total_line,
        over_odds=over_odds,
        under_odds=under_odds
    )


def test_moneyline_with_value():
    """Test 1: Moneyline con valor (edge positivo)
    
    SCENARIO:
        home_win real = 45%
        home_odds = 2.30 → implied = 43.48%
        raw_edge = 0.45 - 0.4348 = +0.0152
        normalized = 0.0152 / 0.03 (MONEYLINE efficiency) = 0.507
        → Edge claramente positivo, debe generar Pick
    """
    print("\n" + "="*60)
    print("TEST 1: Moneyline - Valor Positivo")
    print("="*60)
    
    analysis = create_mock_analysis()
    # home_odds=2.30 → implied 43.5% vs real 45% → edge positivo
    odds = create_mock_odds(home_odds=2.30)
    
    market = MoneylineMarket(min_edge=0.02)
    pick = market.evaluate(analysis, odds)
    
    assert pick is not None, (
        "Debe generar Pick: home tiene 45% real vs 43.5% implícita (edge positivo)"
    )
    assert pick.selection == "home", f"Debe ser home, got {pick.selection}"
    assert pick.edge > 0.02, f"Edge debe ser > 0.02, got {pick.edge}"
    assert pick.market == MarketType.MONEYLINE
    
    print(f"✅ Pick generado:")
    print(f"   Selection: {pick.selection}")
    print(f"   Odds: {pick.odds}")
    print(f"   Probability: {pick.probability:.2%}")
    print(f"   Edge: {pick.edge:.4f}")
    print(f"   Confidence: {pick.confidence:.1%}")


def test_moneyline_without_value():
    """Test 2: Moneyline sin valor (edge negativo)
    
    SCENARIO:
        home_win real = 45%
        home_odds = 1.70 → implied = 58.8%
        raw_edge = 0.45 - 0.588 = -0.138 (muy negativo)
        → No debe generar Pick en ningún outcome
    """
    print("\n" + "="*60)
    print("TEST 2: Moneyline - Sin Valor")
    print("="*60)
    
    analysis = create_mock_analysis()
    # Todas las odds muy ajustadas (alta vigorish), sin valor en ningún outcome
    odds = create_mock_odds(
        home_odds=1.70,   # implied 58.8% vs real 45% → negativo
        draw_odds=2.80,   # implied 35.7% vs real 28% → negativo
        away_odds=2.90    # implied 34.5% vs real 27% → negativo
    )
    
    market = MoneylineMarket(min_edge=0.02)
    pick = market.evaluate(analysis, odds)
    
    assert pick is None, f"No debe generar pick con edge negativo, got {pick.selection}"
    print("✅ Correctly rejected (no value)")


def test_moneyline_best_edge():
    """Test 3: Moneyline selecciona mejor edge entre outcomes
    
    SCENARIO:
        home: 45% real vs odds 2.00 (implied 50%) → edge negativo
        away: 27% real vs odds 4.20 (implied 23.8%) → edge positivo (mejor)
        draw: 28% real vs odds 3.50 (implied 28.6%) → edge negativo
        → Debe seleccionar away (único con edge positivo)
    """
    print("\n" + "="*60)
    print("TEST 3: Moneyline - Mejor Edge")
    print("="*60)
    
    analysis = create_mock_analysis()
    odds = create_mock_odds(
        home_odds=2.00,   # implied 50% vs real 45% → negativo
        draw_odds=3.50,   # implied 28.6% vs real 28% → negativo
        away_odds=4.20    # implied 23.8% vs real 27% → positivo ✓
    )
    
    market = MoneylineMarket(min_edge=0.02)
    pick = market.evaluate(analysis, odds)
    
    assert pick is not None, "Debe generar Pick (away tiene edge positivo)"
    assert pick.selection == "away", f"Should pick away, got {pick.selection}"
    print(f"✅ Pick generado: {pick.selection}")
    print(f"   Edge: {pick.edge:.4f}")


def test_totals_over_value():
    """Test 4: Totals - Over con valor
    
    SCENARIO:
        Expected total = 2.8 goals
        Line = 2.5 → Poisson P(>2.5) ≈ 53%
        over_odds = 2.10 → implied 47.6%
        → Over tiene edge positivo
    """
    print("\n" + "="*60)
    print("TEST 4: Totals - Over con Valor")
    print("="*60)
    
    analysis = create_mock_analysis()
    odds = create_mock_odds(
        total_line=2.5,
        over_odds=2.10,   # implied 47.6% vs real ~53% → positivo
        under_odds=1.80   # implied 55.6% vs real ~47% → negativo
    )
    
    market = TotalsMarket(min_edge=0.02)
    pick = market.evaluate(analysis, odds)
    
    assert pick is not None, "Debe generar Pick (over tiene edge positivo)"
    assert "over" in pick.selection, f"Should pick over, got {pick.selection}"
    assert pick.market == MarketType.TOTALS
    
    print(f"✅ Pick generado: {pick.selection}")
    print(f"   Odds: {pick.odds}")
    print(f"   Probability: {pick.probability:.2%}")
    print(f"   Edge: {pick.edge:.4f}")


def test_totals_under_value():
    """Test 5: Totals - Under con valor
    
    SCENARIO:
        Expected total = 2.8 goals
        Line = 3.5 → Poisson P(≤3.5) ≈ 80%+ → under muy probable
        under_odds = 2.20 → implied 45.5% vs real ~80%
        → Under tiene edge muy positivo
    """
    print("\n" + "="*60)
    print("TEST 5: Totals - Under con Valor")
    print("="*60)
    
    analysis = create_mock_analysis()
    odds = create_mock_odds(
        total_line=3.5,
        over_odds=1.70,   # implied 58.8% vs real ~20% → negativo
        under_odds=2.20   # implied 45.5% vs real ~80% → muy positivo
    )
    
    market = TotalsMarket(min_edge=0.02)
    pick = market.evaluate(analysis, odds)
    
    assert pick is not None, "Debe generar Pick (under tiene edge positivo)"
    assert "under" in pick.selection, f"Should pick under, got {pick.selection}"
    print(f"✅ Pick generado: {pick.selection}")
    print(f"   Edge: {pick.edge:.4f}")


def test_missing_odds():
    """Test 6: Manejo de odds faltantes
    
    Si home_odds es None, el mercado debe evaluar los otros outcomes
    sin explotar. Si ningún otro tiene valor → None es correcto.
    """
    print("\n" + "="*60)
    print("TEST 6: Odds Faltantes")
    print("="*60)
    
    analysis = create_mock_analysis()
    odds = create_mock_odds()
    odds.home_odds = None  # Simular odds faltantes
    
    market = MoneylineMarket(min_edge=0.02)
    pick = market.evaluate(analysis, odds)
    
    # Con odds por default (draw=3.50, away=3.60), ningún outcome tiene edge positivo
    # Lo importante es que no crash y que si hay pick, no sea "home"
    if pick:
        print(f"✅ Evaluó otros outcomes: {pick.selection}")
        assert pick.selection != "home"
    else:
        print("✅ Correctly handled missing odds (no value en otros outcomes)")


def test_validation():
    """Test 7: Validación de inputs"""
    print("\n" + "="*60)
    print("TEST 7: Validación de Inputs")
    print("="*60)
    
    analysis = create_mock_analysis()
    odds = create_mock_odds()
    
    # Test 1: Game ID mismatch
    odds.game_id = "different_id"
    market = MoneylineMarket()
    pick = market.evaluate(analysis, odds)
    
    assert pick is None, "Should reject mismatched game IDs"
    print("✅ Game ID mismatch rejected")
    
    # Test 2: None inputs
    pick = market.evaluate(None, odds)
    assert pick is None
    print("✅ None analysis rejected")
    
    pick = market.evaluate(analysis, None)
    assert pick is None
    print("✅ None odds rejected")


def run_all_tests():
    """Execute all markets tests"""
    print("\n" + "🧪 "*30)
    print("MARKETS TESTS")
    print("🧪 "*30)
    
    log_startup()
    
    try:
        test_moneyline_with_value()
        test_moneyline_without_value()
        test_moneyline_best_edge()
        test_totals_over_value()
        test_totals_under_value()
        test_missing_odds()
        test_validation()
        
        print("\n" + "="*60)
        print("✅ ALL MARKETS TESTS PASSED")
        print("="*60)
        
        print("\nSUMMARY:")
        print("  ✅ Moneyline evaluation working")
        print("  ✅ Totals evaluation working")
        print("  ✅ Edge calculation accurate")
        print("  ✅ Best edge selection correct")
        print("  ✅ Validation working")
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ TESTS FAILED: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        log_shutdown()


if __name__ == "__main__":
    run_all_tests()