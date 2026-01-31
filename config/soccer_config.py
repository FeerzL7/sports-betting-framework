"""
Soccer Configuration - Sport-Specific Settings

SCOPE:
- League definitions and parameters
- xG calculation weights
- Form analysis windows
- Home advantage factors
- Baseline goals per league

USAGE:
    from config import DEFAULT_SOCCER_CONFIG, SUPPORTED_SOCCER_LEAGUES
    
    xg_calc = ExpectedGoalsCalculator(
        baseline=DEFAULT_SOCCER_CONFIG.league_baselines["PL"]
    )
"""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class LeagueConfig:
    """Configuration for a specific soccer league"""
    name: str
    code: str               # API-Football code
    api_id: int            # API-Football ID
    baseline_goals: float  # Average goals per game
    home_advantage: float  # Home win rate multiplier
    country: str
    tier: int = 1          # 1=top tier, 2=second tier


@dataclass
class SoccerConfig:
    """
    Soccer-specific configuration
    
    CALIBRATED FROM:
    - Historical data (2020-2024)
    - Top 5 European leagues
    - Closing line analysis
    """
    
    # ========================================================================
    # LEAGUE BASELINES (goals per game, average)
    # ========================================================================
    league_baselines: Dict[str, float] = field(default_factory=lambda: {
        "PL": 2.72,   # Premier League (England)
        "PD": 2.64,   # La Liga (Spain)
        "SA": 2.88,   # Serie A (Italy)
        "BL1": 3.08,  # Bundesliga (Germany)
        "FL1": 2.58,  # Ligue 1 (France)
    })
    
    # ========================================================================
    # HOME ADVANTAGE (multiplier for xG)
    # ========================================================================
    home_advantage: float = 1.12  # Home teams score ~12% more
    
    # ========================================================================
    # XG CALCULATION WEIGHTS
    # ========================================================================
    # Used in advanced xG models (future)
    xg_weights: Dict[str, float] = field(default_factory=lambda: {
        "goals_per_game": 0.40,
        "shots_on_target": 0.25,
        "possession": 0.15,
        "corners": 0.10,
        "attacks": 0.10
    })
    
    # ========================================================================
    # FORM ANALYSIS
    # ========================================================================
    form_window: int = 5              # Last N games to analyze
    form_weights: list = field(       # Recency weights [most recent → oldest]
        default_factory=lambda: [1.5, 1.3, 1.1, 1.0, 0.9]
    )
    
    # ========================================================================
    # CONFIDENCE ADJUSTMENTS
    # ========================================================================
    min_games_for_confidence: int = 5  # Team needs 5+ games for full confidence
    confidence_penalty_per_missing_game: float = 0.10  # -10% per missing game
    
    # ========================================================================
    # POISSON PARAMETERS
    # ========================================================================
    max_score_simulation: int = 10    # Max goals to simulate in Poisson
    
    # ========================================================================
    # DATA QUALITY THRESHOLDS
    # ========================================================================
    min_stats_quality: float = 0.70   # Min confidence if stats incomplete


# ============================================================================
# SUPPORTED LEAGUES
# ============================================================================

SUPPORTED_SOCCER_LEAGUES = {
    "PL": LeagueConfig(
        name="Premier League",
        code="PL",
        api_id=2021,
        baseline_goals=2.72,
        home_advantage=1.12,
        country="England",
        tier=1
    ),
    "PD": LeagueConfig(
        name="La Liga",
        code="PD",
        api_id=2014,
        baseline_goals=2.64,
        home_advantage=1.10,
        country="Spain",
        tier=1
    ),
    "SA": LeagueConfig(
        name="Serie A",
        code="SA",
        api_id=2019,
        baseline_goals=2.88,
        home_advantage=1.14,
        country="Italy",
        tier=1
    ),
    "BL1": LeagueConfig(
        name="Bundesliga",
        code="BL1",
        api_id=2002,
        baseline_goals=3.08,
        home_advantage=1.15,
        country="Germany",
        tier=1
    ),
    "FL1": LeagueConfig(
        name="Ligue 1",
        code="FL1",
        api_id=2015,
        baseline_goals=2.58,
        home_advantage=1.11,
        country="France",
        tier=1
    )
}


# ============================================================================
# DEFAULT CONFIGURATION
# ============================================================================

DEFAULT_SOCCER_CONFIG = SoccerConfig()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_league_baseline(league_code: str) -> float:
    """
    Get baseline goals for a league
    
    Args:
        league_code: "PL", "PD", etc.
    
    Returns:
        Average goals per game
    
    Example:
        >>> get_league_baseline("PL")
        2.72
    """
    if league_code in SUPPORTED_SOCCER_LEAGUES:
        return SUPPORTED_SOCCER_LEAGUES[league_code].baseline_goals
    
    # Fallback to default if league unknown
    return DEFAULT_SOCCER_CONFIG.league_baselines.get(league_code, 2.7)


def get_home_advantage(league_code: str) -> float:
    """
    Get home advantage multiplier for a league
    
    Args:
        league_code: "PL", "PD", etc.
    
    Returns:
        Home advantage multiplier
    
    Example:
        >>> get_home_advantage("BL1")
        1.15
    """
    if league_code in SUPPORTED_SOCCER_LEAGUES:
        return SUPPORTED_SOCCER_LEAGUES[league_code].home_advantage
    
    return DEFAULT_SOCCER_CONFIG.home_advantage


def validate_league_code(league_code: str) -> bool:
    """Check if league is supported"""
    return league_code in SUPPORTED_SOCCER_LEAGUES


def get_all_league_codes() -> list:
    """Get list of all supported league codes"""
    return list(SUPPORTED_SOCCER_LEAGUES.keys())


# ============================================================================
# VALIDATION
# ============================================================================

def validate_soccer_config():
    """Validate soccer configuration"""
    config = DEFAULT_SOCCER_CONFIG
    
    # Validate weights sum to ~1.0
    xg_weights_sum = sum(config.xg_weights.values())
    assert 0.98 <= xg_weights_sum <= 1.02, f"xG weights must sum to 1.0, got {xg_weights_sum}"
    
    # Validate form weights
    assert len(config.form_weights) >= config.form_window, "Not enough form weights"
    
    # Validate leagues
    for code, league in SUPPORTED_SOCCER_LEAGUES.items():
        assert code == league.code, f"Code mismatch: {code} != {league.code}"
        assert 1.0 <= league.baseline_goals <= 5.0, f"Unrealistic baseline: {league.baseline_goals}"
        assert 1.0 <= league.home_advantage <= 1.3, f"Unrealistic home advantage: {league.home_advantage}"
    
    print("✅ Soccer config validated")


if __name__ == "__main__":
    # Self-test
    validate_soccer_config()
    
    # Print summary
    print(f"\nSupported Leagues: {len(SUPPORTED_SOCCER_LEAGUES)}")
    for code, league in SUPPORTED_SOCCER_LEAGUES.items():
        print(f"  {code}: {league.name} (baseline: {league.baseline_goals} goals)")