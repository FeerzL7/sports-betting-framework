"""
Tests manuales para core modules

EJECUTAR DESDE RAÍZ:
    python -m tests.test_core

O agregar raíz al PYTHONPATH:
    set PYTHONPATH=%cd%  (Windows CMD)
    $env:PYTHONPATH = $pwd  (PowerShell)
    export PYTHONPATH=$(pwd)  (Linux/Mac)
    
    python tests/test_core.py
"""
import sys
from pathlib import Path

# Agregar directorio raíz al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Ahora sí podemos importar
from core import ProbabilityEngine, EdgeCalculator, KellyCalculator, RiskManager
from core.models import MarketType, Pick, Sport
from datetime import datetime


def test_probability_engine():
    """Test conversión de proyecciones a probabilidades"""
    print("\n" + "="*60)
    print("TEST 1: Probability Engine")
    print("="*60)
    
    # Soccer: Poisson con empates
    print("\n📊 Soccer - Poisson (home=1.6, away=1.2):")
    probs_soccer = ProbabilityEngine.from_poisson(1.6, 1.2, include_draw=True)
    for outcome, prob in probs_soccer.items():
        print(f"  {outcome}: {prob:.2%}")
    
    # Validar que sumen 1.0
    assert ProbabilityEngine.validate_probabilities(probs_soccer), "Probabilities no suman 1.0"
    print("  ✅ Validación: Probabilidades suman 1.0")
    
    # Baseball: Poisson sin empates
    print("\n⚾ Baseball - Poisson (home=4.5, away=4.2):")
    probs_mlb = ProbabilityEngine.from_poisson(4.5, 4.2, include_draw=False)
    for outcome, prob in probs_mlb.items():
        print(f"  {outcome}: {prob:.2%}")
    
    # Over/Under
    print("\n📈 Over/Under - Soccer (total=2.8, line=2.5):")
    over_prob, under_prob = ProbabilityEngine.calculate_over_under_probability(
        total_expected=2.8,
        line=2.5,
        distribution="poisson"
    )
    print(f"  Over: {over_prob:.2%}")
    print(f"  Under: {under_prob:.2%}")


def test_edge_calculator():
    """Test cálculo de edge"""
    print("\n" + "="*60)
    print("TEST 2: Edge Calculator")
    print("="*60)
    
    calc = EdgeCalculator()
    
    # Scenario 1: Edge positivo (valor)
    print("\n💰 Scenario 1: Edge POSITIVO (hay valor)")
    real_prob = 0.55
    odds = 2.10  # Implica ~47.6%
    edge = calc.calculate(real_prob, odds, MarketType.MONEYLINE)
    ev = calc.calculate_expected_value(real_prob, odds)
    
    print(f"  Probabilidad real: {real_prob:.2%}")
    print(f"  Odds: {odds} (implica {calc.odds_to_probability(odds):.2%})")
    print(f"  Edge normalizado: {edge:.4f}")
    print(f"  Expected Value: {ev:.2f}%")
    
    if edge > 0:
        print("  ✅ HAY VALOR - Apostar")
    else:
        print("  ❌ SIN VALOR - No apostar")
    
    # Scenario 2: Edge negativo (sin valor)
    print("\n🚫 Scenario 2: Edge NEGATIVO (sin valor)")
    real_prob = 0.45
    odds = 1.85  # Implica ~54%
    edge = calc.calculate(real_prob, odds, MarketType.MONEYLINE)
    ev = calc.calculate_expected_value(real_prob, odds)
    
    print(f"  Probabilidad real: {real_prob:.2%}")
    print(f"  Odds: {odds} (implica {calc.odds_to_probability(odds):.2%})")
    print(f"  Edge normalizado: {edge:.4f}")
    print(f"  Expected Value: {ev:.2f}%")
    
    if edge > 0:
        print("  ✅ HAY VALOR - Apostar")
    else:
        print("  ❌ SIN VALOR - No apostar")


def test_kelly_calculator():
    """Test stake sizing con Kelly"""
    print("\n" + "="*60)
    print("TEST 3: Kelly Calculator")
    print("="*60)
    
    kelly_calc = KellyCalculator(
        fraction=0.25,      # Quarter Kelly (conservador)
        max_stake_pct=10.0,
        bankroll=10000
    )
    
    # Scenario 1: Edge alto, alta confianza
    print("\n🎯 Scenario 1: Edge ALTO + Alta confianza")
    result = kelly_calc.calculate(
        probability=0.60,  # 60% real
        odds=2.00,         # Implica 50%
        confidence=0.90,   # Alta confianza
        correlation=0.0    # Sin correlación
    )
    
    print(f"  Probabilidad: {0.60:.2%}")
    print(f"  Odds: 2.00")
    print(f"  Confidence: {0.90:.2%}")
    print(f"  Kelly completo: {result.kelly_full:.2%}")
    print(f"  Kelly ajustado (1/4): {result.kelly_full * 0.25:.2%}")
    print(f"  Stake final: {result.stake_pct:.2f}%")
    print(f"  Stake amount: ${result.stake_amount:.2f}")
    
    # Scenario 2: Edge moderado, baja confianza
    print("\n⚠️  Scenario 2: Edge MODERADO + Baja confianza")
    result = kelly_calc.calculate(
        probability=0.52,
        odds=2.05,
        confidence=0.60,  # Baja confianza → reduce stake
        correlation=0.0
    )
    
    print(f"  Probabilidad: {0.52:.2%}")
    print(f"  Odds: 2.05")
    print(f"  Confidence: {0.60:.2%}")
    print(f"  Stake final: {result.stake_pct:.2f}%")
    print(f"  Stake amount: ${result.stake_amount:.2f}")
    
    # Scenario 3: Edge con correlación alta
    print("\n🔗 Scenario 3: Edge ALTO + Alta correlación")
    result = kelly_calc.calculate(
        probability=0.58,
        odds=2.10,
        confidence=0.85,
        correlation=0.70  # Alta correlación → reduce stake
    )
    
    print(f"  Probabilidad: {0.58:.2%}")
    print(f"  Odds: 2.10")
    print(f"  Confidence: {0.85:.2%}")
    print(f"  Correlación: {0.70:.2%}")
    print(f"  Stake SIN correlación: {result.kelly_full * 0.25 * 0.85 * 100:.2f}%")
    print(f"  Stake CON correlación: {result.stake_pct:.2f}%")
    print(f"  Reducción por correlación: {(1 - result.correlation_adjustment) * 100:.1f}%")


def test_risk_manager():
    """Test gestión de riesgo"""
    print("\n" + "="*60)
    print("TEST 4: Risk Manager")
    print("="*60)
    
    from core.risk import RiskLimits
    
    manager = RiskManager(
        limits=RiskLimits(
            max_total_exposure=20.0,
            max_single_pick=10.0,
            max_picks_per_game=2
        ),
        bankroll=10000
    )
    
    # Crear picks de ejemplo
    pick1 = Pick(
        game_id="game1",
        market=MarketType.MONEYLINE,
        selection="home",
        odds=2.10,
        probability=0.55,
        edge=0.08,
        confidence=0.85,
        stake_pct=3.5
    )
    
    pick2 = Pick(
        game_id="game1",
        market=MarketType.TOTALS,
        selection="over",
        odds=1.95,
        probability=0.58,
        edge=0.06,
        confidence=0.80,
        stake_pct=2.8
    )
    
    pick3 = Pick(
        game_id="game1",
        market=MarketType.SPREAD,
        selection="home",
        odds=1.90,
        probability=0.60,
        edge=0.10,
        confidence=0.90,
        stake_pct=4.2
    )
    
    # Test 1: Agregar primer pick
    print("\n➕ Agregar Pick 1 (game1 ML):")
    can_add, reason = manager.can_add_pick(pick1)
    print(f"  ¿Puede agregar? {can_add}")
    if can_add:
        manager.add_pick(pick1)
        print(f"  ✅ Agregado - Exposure total: {manager.get_total_exposure():.1f}%")
    
    # Test 2: Agregar segundo pick (mismo juego, diferente mercado)
    print("\n➕ Agregar Pick 2 (game1 TOTALS):")
    can_add, reason = manager.can_add_pick(pick2)
    print(f"  ¿Puede agregar? {can_add}")
    if can_add:
        manager.add_pick(pick2)
        corr = manager.calculate_correlation(pick1, pick2)
        print(f"  ✅ Agregado - Correlación con Pick 1: {corr:.2f}")
        print(f"  Exposure total: {manager.get_total_exposure():.1f}%")
    
    # Test 3: Intentar agregar tercer pick (excede límite por juego)
    print("\n➕ Agregar Pick 3 (game1 SPREAD - debería RECHAZAR):")
    can_add, reason = manager.can_add_pick(pick3)
    print(f"  ¿Puede agregar? {can_add}")
    if not can_add:
        print(f"  ❌ RECHAZADO: {reason}")
    
    # Test 4: Status de riesgo
    print("\n📊 Risk Status:")
    status = manager.get_risk_status()
    print(f"  Total exposure: {status.total_exposure:.1f}%")
    print(f"  Picks activos: {status.active_picks}")
    print(f"  Dentro de límites: {status.within_limits}")
    if status.warnings:
        print(f"  ⚠️  Warnings:")
        for warning in status.warnings:
            print(f"    - {warning}")


def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n" + "🧪 "*30)
    print("CORE MODULES - TESTS MANUALES")
    print("🧪 "*30)
    
    try:
        test_probability_engine()
        test_edge_calculator()
        test_kelly_calculator()
        test_risk_manager()
        
        print("\n" + "="*60)
        print("✅ TODOS LOS TESTS PASARON")
        print("="*60 + "\n")
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ ERROR EN TESTS: {e}")
        print("="*60 + "\n")
        raise


if __name__ == "__main__":
    run_all_tests()