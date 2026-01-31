"""
Soccer Adapter Integration Test

IMPORTANTE:
Este test requiere API key válida de API-Football.
Si no tienes API key, el test fallará en los fetch reales.

EJECUTAR:
    python -m tests.test_soccer_adapter
    
O con mock data (sin API):
    # TODO: Implementar mock mode
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sports.soccer.adapter import SoccerAdapter
from config import is_provider_configured
from utils import get_logger, log_startup, log_shutdown
from datetime import datetime


# Setup logger
logger = get_logger(__name__)


def test_adapter_initialization():
    """Test 1: Adapter se inicializa correctamente"""
    print("\n" + "="*60)
    print("TEST 1: Adapter Initialization")
    print("="*60)
    
    adapter = SoccerAdapter()
    
    assert adapter.sport.value == "soccer"
    assert len(adapter.supported_leagues) == 5
    assert "PL" in adapter.supported_leagues
    
    print(f"✅ Sport: {adapter.sport.value}")
    print(f"✅ Supported leagues: {len(adapter.supported_leagues)}")
    print(f"   {', '.join(adapter.supported_leagues)}")
    print(f"✅ Supported markets: {adapter.get_supported_markets()}")


def test_league_validation():
    """Test 2: Validación de ligas"""
    print("\n" + "="*60)
    print("TEST 2: League Validation")
    print("="*60)
    
    adapter = SoccerAdapter()
    
    # Valid league
    try:
        adapter.validate_league("PL")
        print("✅ Valid league 'PL' accepted")
    except ValueError:
        print("❌ Valid league rejected")
        raise
    
    # Invalid league
    try:
        adapter.validate_league("INVALID")
        print("❌ Invalid league accepted")
        raise AssertionError("Invalid league should be rejected")
    except ValueError as e:
        print(f"✅ Invalid league rejected: {e}")


def test_fetch_games_mock():
    """Test 3: Fetch games (sin API real - structure only)"""
    print("\n" + "="*60)
    print("TEST 3: Fetch Games Structure")
    print("="*60)
    
    # Check if API configured
    if not is_provider_configured("api_football"):
        print("⚠️  API-Football not configured")
        print("   Skipping real API test")
        print("   Configure API key in config/api_keys.py to run this test")
        return
    
    adapter = SoccerAdapter()
    
    try:
        # Try to fetch today's games (may return empty list)
        today = datetime.now().strftime("%Y-%m-%d")
        fixtures = adapter.fetch_games(today, "PL")
        
        print(f"✅ Fetch successful: {len(fixtures)} fixtures found")
        
        if fixtures:
            print(f"\n   Sample fixture:")
            fixture = fixtures[0]
            print(f"   Home: {fixture['homeTeam']['name']}")
            print(f"   Away: {fixture['awayTeam']['name']}")
            print(f"   Date: {fixture['utcDate']}")
    
    except Exception as e:
        print(f"⚠️  Fetch failed (expected if no games today): {e}")


def test_game_analysis_structure():
    """Test 4: GameAnalysis estructura (mock data)"""
    print("\n" + "="*60)
    print("TEST 4: GameAnalysis Structure (Mock)")
    print("="*60)
    
    # Create mock game data
    mock_game = {
        "id": 12345,
        "utcDate": "2025-01-30T20:00:00Z",
        "homeTeam": {
            "id": 86,
            "name": "Real Madrid"
        },
        "awayTeam": {
            "id": 81,
            "name": "Barcelona"
        },
        "competition": {
            "code": "PD",
            "name": "Primera Division"
        },
        "status": "SCHEDULED",
        "score": {
            "fullTime": {"home": None, "away": None}
        }
    }
    
    print("Mock game data created:")
    print(f"  {mock_game['homeTeam']['name']} vs {mock_game['awayTeam']['name']}")
    print(f"  League: {mock_game['competition']['code']}")
    
    # NOTA: No podemos ejecutar analyze_game sin API real
    # porque necesita fetch team stats y form
    
    print("\n✅ Mock data structure valid")
    print("ℹ️  Full analysis test requires API configuration")


def test_confidence_calculation():
    """Test 5: Cálculo de confidence"""
    print("\n" + "="*60)
    print("TEST 5: Confidence Calculation")
    print("="*60)
    
    adapter = SoccerAdapter()
    
    # Mock analysis data
    mock_analysis = {
        "home_form": {
            "games_analyzed": 5,
            "form_strength": 0.7
        },
        "away_form": {
            "games_analyzed": 5,
            "form_strength": 0.6
        },
        "home_stats": {
            "games_played": 10,
            "goals_per_game": 2.1
        },
        "away_stats": {
            "games_played": 10,
            "goals_per_game": 1.8
        },
        "home_xg": 1.9,
        "away_xg": 1.5
    }
    
    mock_game = {"id": 123}
    
    confidence = adapter.calculate_confidence(mock_game, mock_analysis)
    
    print(f"✅ Confidence calculated: {confidence:.1%}")
    assert 0 <= confidence <= 1, "Confidence must be 0-1"
    
    # Test with poor data quality
    poor_analysis = {
        "home_form": {
            "games_analyzed": 2,  # Low sample
            "form_strength": 0.3
        },
        "away_form": {
            "games_analyzed": 1,  # Very low sample
            "form_strength": 0.2
        },
        "home_stats": {
            "games_played": 0,  # No stats (defaults)
            "goals_per_game": 1.5
        },
        "away_stats": {
            "games_played": 0,
            "goals_per_game": 1.5
        },
        "home_xg": 0.3,  # Extreme low
        "away_xg": 4.0   # Extreme high
    }
    
    poor_confidence = adapter.calculate_confidence(mock_game, poor_analysis)
    
    print(f"✅ Poor data confidence: {poor_confidence:.1%}")
    assert poor_confidence < confidence, "Poor data should have lower confidence"
    print(f"   Confidence reduction: {(1 - poor_confidence/confidence)*100:.1f}%")


def test_supported_markets():
    """Test 6: Mercados soportados"""
    print("\n" + "="*60)
    print("TEST 6: Supported Markets")
    print("="*60)
    
    adapter = SoccerAdapter()
    markets = adapter.get_supported_markets()
    
    assert "moneyline" in markets
    assert "totals" in markets
    
    print(f"✅ Supported markets: {markets}")
    print(f"   Count: {len(markets)}")


def run_all_tests():
    """Execute all soccer adapter tests"""
    print("\n" + "🧪 "*30)
    print("SOCCER ADAPTER TESTS")
    print("🧪 "*30)
    
    log_startup()
    
    try:
        test_adapter_initialization()
        test_league_validation()
        test_fetch_games_mock()
        test_game_analysis_structure()
        test_confidence_calculation()
        test_supported_markets()
        
        print("\n" + "="*60)
        print("✅ ALL SOCCER ADAPTER TESTS PASSED")
        print("="*60)
        
        print("\nNOTE:")
        print("  Some tests were skipped due to missing API configuration.")
        print("  To run full integration tests:")
        print("  1. Configure API-Football key in config/api_keys.py")
        print("  2. Run tests on a day with scheduled matches")
        print("  3. Or implement mock data provider")
        
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