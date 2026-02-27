"""
main.py - CLI Entry Point

RESPONSABILIDAD:
- Parsear argumentos de línea de comandos
- Instanciar dependencias (adapter, provider, markets)
- Ejecutar el Orchestrator
- Formatear y printear el output

DISEÑO:
- Este archivo es la ÚNICA dependencia de UI
- El Orchestrator no sabe que main.py existe
- Una futura web app puede importar Orchestrator directamente
- Output siempre es JSON-serializable

USO:
    # Con datos reales (requiere API keys configuradas):
    python main.py --sport soccer --league PL --date 2025-01-30

    # Con datos falsos (testing sin API):
    python main.py --sport soccer --league PL --provider fake

    # Con bankroll personalizado:
    python main.py --sport soccer --league PL --provider fake --bankroll 50000

    # Verbose (muestra logs detallados):
    python main.py --sport soccer --league PL --provider fake --verbose

ARGUMENTOS:
    --sport     Deporte (soccer | mlb | nfl | nba | tennis)
    --league    Liga ("PL", "PD", "SA", "BL1", "FL1")
    --date      Fecha YYYY-MM-DD (default: hoy)
    --provider  Fuente de odds: "fake" | "real" (default: fake)
    --scenario  Scenario del FakeProvider (default: value_exists)
    --bankroll  Bankroll total (default: 10000)
    --verbose   Mostrar logs DEBUG
    --json      Output solo JSON (sin logs, para integración)
"""
import argparse
import json
import sys
import logging
from datetime import datetime
from pathlib import Path

# Asegurar que el proyecto root está en el path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from engine.orchestrator import Orchestrator
from core.models import Sport
from markets import MoneylineMarket, TotalsMarket
from utils import get_logger, log_startup, log_shutdown

logger = get_logger(__name__)


# ============================================================================
# REGISTRY: Deportes y sus adapters
# Agregar un nuevo deporte = agregar una línea aquí.
# ============================================================================

def get_adapter(sport: str):
    """
    Factory: retorna el adapter correcto según el deporte.
    
    EXTENSIBILIDAD:
    Para agregar MLB:
        1. Crear sports/mlb/adapter.py con MLBAdapter
        2. Agregar "mlb": lambda: MLBAdapter() aquí
        3. Done. Nada más cambia.
    """
    adapters = {
        "soccer": lambda: _import_soccer_adapter(),
    }
    
    if sport not in adapters:
        print(f"❌ Sport '{sport}' not implemented yet.")
        print(f"   Available: {list(adapters.keys())}")
        sys.exit(1)
    
    return adapters[sport]()


def _import_soccer_adapter():
    """Import isolado para evitar errores si las dependencias no están."""
    from sports.soccer.adapter import SoccerAdapter
    return SoccerAdapter()


# ============================================================================
# REGISTRY: Markets disponibles
# ============================================================================

def get_markets(sport: str) -> list:
    """
    Retorna los markets apropiados según el deporte.
    
    En futuro: cada adapter puede declarar sus markets soportados
    y aquí validamos que el market es compatible.
    """
    # Universal: moneyline + totals
    markets = [
        MoneylineMarket(min_edge=0.02),
        TotalsMarket(min_edge=0.02)
    ]
    
    # En futuro:
    # if sport == "soccer":
    #     markets.append(BTTSMarket())
    # if sport == "nfl":
    #     markets.append(SpreadMarket())
    
    return markets


# ============================================================================
# PROVIDER FACTORY
# ============================================================================

def get_provider(provider_type: str, scenario: str = "value_exists"):
    """
    Factory: retorna el provider según el tipo.
    
    Args:
        provider_type: "fake" | "real"
        scenario: Solo para FakeProvider
    """
    if provider_type == "fake":
        from providers import FakeOddsProvider
        return FakeOddsProvider(scenario=scenario)
    
    elif provider_type == "real":
        from providers import OddsAPIProvider
        return OddsAPIProvider()
    
    else:
        print(f"❌ Provider '{provider_type}' unknown.")
        print(f"   Options: fake, real")
        sys.exit(1)


# ============================================================================
# CLI
# ============================================================================

def parse_args() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="🎯 Multi-Sport Betting Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXEMPLOS:
  python main.py --sport soccer --league PL --provider fake
  python main.py --sport soccer --league PD --provider fake --scenario no_value
  python main.py --sport soccer --league PL --provider real --bankroll 50000
  python main.py --sport soccer --league PL --provider fake --json
        """
    )
    
    parser.add_argument(
        "--sport",
        required=True,
        choices=["soccer", "mlb", "nfl", "nba", "tennis"],
        help="Deporte a analizar"
    )
    
    parser.add_argument(
        "--league",
        required=True,
        help="Liga (ej: PL, PD, SA, BL1, FL1)"
    )
    
    parser.add_argument(
        "--date",
        default=None,
        help="Fecha YYYY-MM-DD (default: hoy)"
    )
    
    parser.add_argument(
        "--provider",
        default="fake",
        choices=["fake", "real"],
        help="Fuente de odds (default: fake)"
    )
    
    parser.add_argument(
        "--scenario",
        default="value_exists",
        choices=["value_exists", "no_value", "partial_odds", "empty"],
        help="Scenario del FakeProvider (default: value_exists)"
    )
    
    parser.add_argument(
        "--bankroll",
        type=float,
        default=10000.0,
        help="Bankroll total (default: 10000)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar logs DEBUG"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output solo JSON (sin logs)"
    )
    
    return parser.parse_args()


def configure_logging(verbose: bool, json_mode: bool):
    """Configura niveles de logging según flags."""
    if json_mode:
        # En modo JSON, silenciar todo excepto CRITICAL
        logging.getLogger().setLevel(logging.CRITICAL)
    elif verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)


def main():
    """Entry point principal."""
    args = parse_args()
    
    # Configurar logging
    configure_logging(args.verbose, args.json)
    
    if not args.json:
        log_startup()
        print("\n🎯 Multi-Sport Betting Framework")
        print(f"   Sport: {args.sport}")
        print(f"   League: {args.league}")
        print(f"   Date: {args.date or 'today'}")
        print(f"   Provider: {args.provider}")
        print(f"   Bankroll: ${args.bankroll:,.2f}")
        print()
    
    try:
        # --- Wire dependencies ---
        adapter = get_adapter(args.sport)
        provider = get_provider(args.provider, args.scenario)
        markets = get_markets(args.sport)
        
        # --- Create orchestrator ---
        orchestrator = Orchestrator(
            adapter=adapter,
            odds_provider=provider,
            markets=markets,
            bankroll=args.bankroll
        )
        
        # --- Run pipeline ---
        result = orchestrator.run(
            league=args.league,
            date=args.date
        )
        
        # --- Output ---
        if args.json:
            # Modo JSON: output puro, parseable
            print(json.dumps(result.to_dict(), indent=2, default=str))
        else:
            # Modo human-readable
            _print_result(result)
    
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        if args.json:
            # En modo JSON, retornar error como JSON
            error_output = {
                "error": True,
                "message": str(e),
                "type": type(e).__name__
            }
            print(json.dumps(error_output, indent=2))
        else:
            print(f"\n❌ Pipeline failed: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
        sys.exit(1)
    
    finally:
        if not args.json:
            log_shutdown()


def _print_result(result):
    """Formatea y printea el resultado de forma legible."""
    print("\n" + "=" * 70)
    print("📊 PIPELINE RESULTS")
    print("=" * 70)
    
    # --- Stats ---
    stats = result.pipeline_stats
    print(f"\n📈 Pipeline Stats:")
    print(f"   Games fetched:    {stats.get('games_fetched', 0)}")
    print(f"   Odds fetched:     {stats.get('odds_fetched', 0)}")
    print(f"   Games matched:    {stats.get('games_matched', 0)}")
    print(f"   Games analyzed:   {stats.get('games_analyzed', 0)}")
    print(f"   Picks found:      {stats.get('picks_found', 0)}")
    print(f"   Picks approved:   {stats.get('picks_approved', 0)}")
    print(f"   Picks rejected:   {stats.get('picks_rejected', 0)}")
    
    if stats.get("errors"):
        print(f"\n⚠️  Errors ({len(stats['errors'])}):")
        for err in stats["errors"]:
            print(f"   - {err}")
    
    # --- Approved Picks ---
    if result.approved_picks:
        print(f"\n✅ APPROVED PICKS ({len(result.approved_picks)}):")
        print("-" * 70)
        print(f"{'Game':<30} {'Market':<12} {'Selection':<14} {'Odds':>6} {'Edge':>8} {'Stake':>10}")
        print("-" * 70)
        
        for pick in result.approved_picks:
            game = pick.get("game_id", "?")[:28]
            market = pick.get("market", "?")
            selection = pick.get("selection", "?")
            odds = pick.get("odds", 0)
            edge = pick.get("edge", 0)
            stake = pick.get("stake_pct", 0)
            amount = pick.get("stake_amount")
            
            stake_str = f"{stake:.2f}%"
            if amount:
                stake_str += f" (${amount:.2f})"
            
            print(f"{game:<30} {market:<12} {selection:<14} {odds:>6.2f} {edge:>8.4f} {stake_str:>10}")
        
        print("-" * 70)
    else:
        print("\n📭 No picks approved (no value found or all rejected by risk)")
    
    # --- Rejected Picks ---
    if result.rejected_picks:
        print(f"\n❌ REJECTED PICKS ({len(result.rejected_picks)}):")
        for pick in result.rejected_picks:
            print(f"   {pick.get('market')} {pick.get('selection')} — "
                  f"{pick.get('rejection_reason', 'unknown')}")
    
    # --- Risk Status ---
    risk = result.risk_status
    print(f"\n🛡️  Risk Status:")
    print(f"   Total exposure:   {risk.get('total_exposure_pct', 0):.1f}% "
          f"(${risk.get('total_exposure_amount', 0):.2f})")
    print(f"   Active picks:     {risk.get('active_picks', 0)}")
    print(f"   Within limits:    {'✅' if risk.get('within_limits', False) else '❌'}")
    
    if risk.get("warnings"):
        print(f"   ⚠️  Warnings:")
        for w in risk["warnings"]:
            print(f"      - {w}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()