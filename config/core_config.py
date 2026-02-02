"""
Core Configuration - Sport-Agnostic Settings

SCOPE:
- Kelly Calculator parameters
- Risk Manager limits
- Edge thresholds
- Market efficiency baselines

USAGE:
    from config import DEFAULT_KELLY_CONFIG, DEFAULT_RISK_CONFIG

    kelly = KellyCalculator(
        fraction=DEFAULT_KELLY_CONFIG.fraction,
        max_stake_pct=DEFAULT_KELLY_CONFIG.max_stake_pct
    )
"""
from dataclasses import dataclass
from typing import Dict


@dataclass
class KellyConfig:
    """
    Kelly Criterion configuration

    CONSERVATIVE (recommended for most users):
        fraction=0.25, max_stake_pct=10.0

    MODERATE (experienced bettors):
        fraction=0.50, max_stake_pct=12.0

    AGGRESSIVE (large bankroll + high confidence):
        fraction=0.75, max_stake_pct=15.0
    """
    fraction: float = 0.25              # Quarter Kelly (conservative)
    max_stake_pct: float = 10.0         # Never bet more than 10% of bankroll
    min_edge: float = 0.02              # Minimum 2% edge to bet

    def validate(self) -> None:
        """Validate configuration"""
        assert 0.1 <= self.fraction <= 1.0, "Fraction must be 0.1-1.0"
        assert 1.0 <= self.max_stake_pct <= 100.0, "Max stake must be 1-100%"
        assert 0.0 < self.min_edge < 0.5, "Min edge must be 0-50%"


@dataclass
class RiskConfig:
    """
    Risk Management configuration

    CONSERVATIVE:
        max_total_exposure=15.0, max_picks_per_game=1

    MODERATE:
        max_total_exposure=20.0, max_picks_per_game=2

    AGGRESSIVE:
        max_total_exposure=30.0, max_picks_per_game=3
    """
    max_total_exposure: float = 20.0    # Max % of bankroll at risk simultaneously
    max_single_pick: float = 10.0       # Max % on single pick
    max_correlated_exposure: float = 15.0  # Max % on correlated picks
    max_picks_per_game: int = 2         # Max picks on same game
    max_picks_per_league: int = 10      # Max picks in same league/day

    def validate(self) -> None:
        """Validate configuration"""
        assert 5.0 <= self.max_total_exposure <= 50.0, "Total exposure 5-50%"
        assert self.max_single_pick <= self.max_total_exposure, "Single pick <= total"
        assert 1 <= self.max_picks_per_game <= 5, "Picks per game: 1-5"


@dataclass
class EdgeConfig:
    """
    Edge calculation configuration

    Market efficiency factors (lower = more efficient market)
    Based on empirical analysis of closing line value

    M3 FIX: Usa strings como keys en vez de MarketType enum.
    Esto elimina la dependencia config → core.models.
    EdgeCalculator (que ya importa MarketType) hace el mapping.
    """
    market_efficiency: Dict[str, float] = None
    vig_adjustment: bool = True  # Attempt to remove vig from implied probabilities

    def __post_init__(self):
        if self.market_efficiency is None:
            # Keys son strings, no MarketType enums
            # Valores son los mismos que antes (no cambia la lógica)
            self.market_efficiency = {
                "moneyline": 0.03,         # Very efficient
                "totals": 0.04,            # Moderately efficient
                "spread": 0.04,            # Similar to totals
                "btts": 0.05,              # Both Teams Score (less efficient)
                "props": 0.06              # Player props (least efficient, more value)
            }


# ============================================================
# DEFAULT CONFIGURATIONS
# ============================================================

# Conservative defaults (recommended for starting)
DEFAULT_KELLY_CONFIG = KellyConfig(
    fraction=0.25,
    max_stake_pct=10.0,
    min_edge=0.02
)

DEFAULT_RISK_CONFIG = RiskConfig(
    max_total_exposure=20.0,
    max_single_pick=10.0,
    max_correlated_exposure=15.0,
    max_picks_per_game=2,
    max_picks_per_league=10
)

DEFAULT_EDGE_CONFIG = EdgeConfig()


# ============================================================
# ALTERNATIVE PROFILES
# ============================================================

CONSERVATIVE_KELLY = KellyConfig(
    fraction=0.20,
    max_stake_pct=8.0,
    min_edge=0.03
)

AGGRESSIVE_KELLY = KellyConfig(
    fraction=0.50,
    max_stake_pct=15.0,
    min_edge=0.01
)

CONSERVATIVE_RISK = RiskConfig(
    max_total_exposure=15.0,
    max_single_pick=8.0,
    max_correlated_exposure=12.0,
    max_picks_per_game=1,
    max_picks_per_league=8
)

AGGRESSIVE_RISK = RiskConfig(
    max_total_exposure=30.0,
    max_single_pick=15.0,
    max_correlated_exposure=20.0,
    max_picks_per_game=3,
    max_picks_per_league=15
)


# ============================================================
# VALIDATION
# ============================================================

def validate_all_configs():
    """Validate all predefined configs (run in tests)"""
    DEFAULT_KELLY_CONFIG.validate()
    DEFAULT_RISK_CONFIG.validate()
    CONSERVATIVE_KELLY.validate()
    AGGRESSIVE_KELLY.validate()
    CONSERVATIVE_RISK.validate()
    AGGRESSIVE_RISK.validate()


if __name__ == "__main__":
    # Self-test
    validate_all_configs()
    print("✅ All core configs validated")