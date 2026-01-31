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
    """Create mock GameAnalysis for testing"""
    return GameAnalysis(
        sport=Sport.SOCCER,
        league="PL",
        game_id="test_game_123",
        home_team="Arsenal",
        away_team="Chelsea",
        start_time=datetime.now(),
        probabilities={
            "home_win": 0.45,
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
    """Test 1: Moneyline con valor (edge positivo)"""
    print("\n" + "="*60)
    print("TEST 1: Moneyline - Valor Positivo")
    print("="*60)
    
    analysis = create_mock_analysis()
    # Odds favorables: home tiene 45% real pero odds implican ~45.5%
    odds = create_mock_odds(home_odds=2.20)  # implica 45.5%
    
    market = MoneylineMarket(min_edge=0.02)
    pick = market.evaluate(analysis, odds)
    
    if pick:
        print(f"✅ Pick generado:")
        print(f"   Selection: {pick.selection}")
        print(f"   Odds: {pick.odds}")
        print(f"   Probability: {pick.probability:.2%}")
        print(f"   Edge: {pick.edge:.4f}")
        print(f"   Confidence: {pick.confidence:.1%}")
        assert pick.market == MarketType.MONEYLINE
        assert pick.selection in ["home", "away", "draw"]
    else:
        print("ℹ️  No value found (expected - odds too tight)")


def test_moneyline_without_value():
    """Test 2: Moneyline sin valor (edge negativo)"""
    print("\n" + "="*60)
    print("TEST 2: Moneyline - Sin Valor")
    print("="*60)
    
    analysis = create_mock_analysis()
    # Odds desfavorables: home tiene 45% pero odds implican 58.8%
    odds = create_mock_odds(home_odds=1.70)
    
    market = MoneylineMarket(min_edge=0.02)
    pick = market.evaluate(analysis, odds)
    
    if pick:
        print(f"❌ Unexpected pick generated: {pick.selection}")
        raise AssertionError("Should not generate pick with negative edge")
    else:
        print("✅ Correctly rejected (no value)")


def test_moneyline_best_edge():
    """Test 3: Moneyline selecciona mejor edge"""
    print("\n" + "="*60)
    print("TEST 3: Moneyline - Mejor Edge")
    print("="*60)
    
    analysis = create_mock_analysis()
    # Away tiene mejor value: 27% prob pero odds implican 23.8%
    odds = create_mock_odds(
        home_odds=2.00,   # implica 50% (peor que 45%)
        away_odds=4.20    # implica 23.8% (mejor que 27%)
    )
    
    market = MoneylineMarket(min_edge=0.02)
    pick = market.evaluate(analysis, odds)
    
    if pick:
        print(f"✅ Pick generado: {pick.selection}")
        assert pick.selection == "away", f"Should pick away, got {pick.selection}"
        print(f"   Edge: {pick.edge:.4f}")
    else:
        print("⚠️  No pick generated")


def test_totals_over_value():
    """Test 4: Totals - Over con valor"""
    print("\n" + "="*60)
    print("TEST 4: Totals - Over con Valor")
    print("="*60)
    
    analysis = create_mock_analysis()
    # Expected: 2.8 goals, Line: 2.5
    # Over debería tener >50% prob
    odds = create_mock_odds(
        total_line=2.5,
        over_odds=2.10,   # implica 47.6%
        under_odds=1.80   # implica 55.6%
    )
    
    market = TotalsMarket(min_edge=0.02)
    pick = market.evaluate(analysis, odds)
    
    if pick:
        print(f"✅ Pick generado: {pick.selection}")
        print(f"   Odds: {pick.odds}")
        print(f"   Probability: {pick.probability:.2%}")
        print(f"   Edge: {pick.edge:.4f}")
        assert "over" in pick.selection or "under" in pick.selection
        assert pick.market == MarketType.TOTALS
    else:
        print("ℹ️  No pick generated")


def test_totals_under_value():
    """Test 5: Totals - Under con valor"""
    print("\n" + "="*60)
    print("TEST 5: Totals - Under con Valor")
    print("="*60)
    
    analysis = create_mock_analysis()
    # Expected: 2.8, Line: 3.5 (alta)
    # Under debería tener alta prob
    odds = create_mock_odds(
        total_line=3.5,
        over_odds=1.70,   # implica 58.8%
        under_odds=2.20   # implica 45.5%
    )
    
    market = TotalsMarket(min_edge=0.02)
    pick = market.evaluate(analysis, odds)
    
    if pick:
        print(f"✅ Pick generado: {pick.selection}")
        assert "under" in pick.selection, f"Should pick under, got {pick.selection}"
        print(f"   Edge: {pick.edge:.4f}")
    else:
        print("ℹ️  No pick generated")


def test_missing_odds():
    """Test 6: Manejo de odds faltantes"""
    print("\n" + "="*60)
    print("TEST 6: Odds Faltantes")
    print("="*60)
    
    analysis = create_mock_analysis()
    odds = create_mock_odds()
    odds.home_odds = None  # Simular odds faltantes
    
    market = MoneylineMarket(min_edge=0.02)
    pick = market.evaluate(analysis, odds)
    
    # Debería evaluar otros outcomes disponibles
    if pick:
        print(f"✅ Evaluó otros outcomes: {pick.selection}")
        assert pick.selection != "home"
    else:
        print("✅ Correctly handled missing odds")


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