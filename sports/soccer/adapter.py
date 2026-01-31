"""
Soccer Adapter - Implementación de SportAdapter para fútbol

RESPONSABILIDAD:
Orquestar el pipeline completo de análisis:
1. Fetch games desde API-Football
2. Fetch team stats y form
3. Calcular xG (Expected Goals)
4. Analizar form reciente
5. Convertir a probabilidades (Poisson)
6. Calcular confidence score
7. Devolver GameAnalysis (contrato universal)

ESTE ADAPTER NO SABE DE:
- Odds (lo maneja OddsProvider)
- Edge (lo maneja Market)
- Stake (lo maneja KellyCalculator)
- Risk (lo maneja RiskManager)
"""
from sports.base import SportAdapter
from core.models import Sport, GameAnalysis
from sports.soccer.api_client import APIFootballClient
from sports.soccer.analysis.xg_calculator import ExpectedGoalsCalculator
from sports.soccer.analysis.form_analyzer import FormAnalyzer
from core.probability import ProbabilityEngine
from config.soccer_config import SUPPORTED_SOCCER_LEAGUES, DEFAULT_SOCCER_CONFIG
from utils import (
    get_logger,
    LogContext,
    PerformanceLogger,
    DataFetchError,
    InsufficientDataError
)
from typing import Dict, List
from datetime import datetime


# Setup logger
logger = get_logger(__name__)


class SoccerAdapter(SportAdapter):
    """
    Adapter para análisis de partidos de fútbol
    
    Pipeline:
    API → Stats → xG → Form → Probabilities → GameAnalysis
    """
    
    sport = Sport.SOCCER
    supported_leagues = list(SUPPORTED_SOCCER_LEAGUES.keys())
    
    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: API key para API-Football (opcional, usa config por default)
        """
        self.api_client = APIFootballClient(api_key)
        
        # Calculators se crean por juego (cada liga puede tener baseline diferente)
        self.xg_calculator = None
        self.form_analyzer = FormAnalyzer()
        
        logger.info(
            "SoccerAdapter initialized",
            extra={
                "supported_leagues": len(self.supported_leagues),
                "leagues": ", ".join(self.supported_leagues)
            }
        )
    
    def fetch_games(self, date: str, league: str) -> List[Dict]:
        """
        Obtiene partidos desde API-Football
        
        Args:
            date: "YYYY-MM-DD"
            league: "PL", "PD", "SA", etc.
        
        Returns:
            Lista de raw game data
        
        Raises:
            ValueError: Si league no soportada
            DataFetchError: Si API falla
        """
        self.validate_league(league)
        
        logger.info(
            f"Fetching games for {league}",
            extra={"league": league, "date": date}
        )
        
        perf = PerformanceLogger(logger, f"Fetch games: {league}")
        
        with perf.track():
            try:
                fixtures = self.api_client.get_fixtures(league, date)
                
                logger.info(
                    f"Found {len(fixtures)} fixtures",
                    extra={
                        "league": league,
                        "count": len(fixtures),
                        "date": date
                    }
                )
                
                return fixtures
            
            except Exception as e:
                logger.error(
                    f"Failed to fetch games for {league}",
                    extra={"league": league, "error": str(e)}
                )
                raise DataFetchError(
                    f"Failed to fetch games for {league}",
                    league=league,
                    date=date,
                    error=str(e)
                )
    
    def analyze_game(self, game_data: Dict) -> GameAnalysis:
        """
        Pipeline completo de análisis para un partido
        
        Args:
            game_data: Dict con datos raw del API
        
        Returns:
            GameAnalysis con todas las proyecciones y probabilidades
        
        Pipeline:
        1. Extraer info básica (teams, fecha, league)
        2. Fetch stats de equipos
        3. Fetch recent form
        4. Calcular xG (simple o advanced según data disponible)
        5. Analizar form
        6. Calcular probabilidades (Poisson)
        7. Calcular confidence
        8. Empaquetar GameAnalysis
        """
        # Extraer información básica
        game_id = str(game_data["id"])
        home_team = game_data["homeTeam"]["name"]
        away_team = game_data["awayTeam"]["name"]
        home_id = game_data["homeTeam"]["id"]
        away_id = game_data["awayTeam"]["id"]
        league_code = game_data.get("competition", {}).get("code", "PL")
        start_time = datetime.fromisoformat(
            game_data["utcDate"].replace("Z", "+00:00")
        )
        
        logger.info("="*60)
        logger.info(f"Analyzing: {home_team} vs {away_team}")
        logger.info("="*60)
        
        with LogContext(
            logger,
            game_id=game_id,
            league=league_code,
            matchup=f"{home_team} vs {away_team}"
        ):
            # Initialize xG calculator for this league
            self.xg_calculator = ExpectedGoalsCalculator(league_code)
            
            perf = PerformanceLogger(logger, "Full Game Analysis")
            
            with perf.track():
                # 1. Fetch team stats
                logger.info("Step 1: Fetching team stats")
                home_stats = self.api_client.get_team_stats(home_id, league_code)
                away_stats = self.api_client.get_team_stats(away_id, league_code)
                
                # 2. Fetch recent form
                logger.info("Step 2: Fetching recent form")
                home_form_matches = self.api_client.get_team_form(
                    home_id,
                    games=DEFAULT_SOCCER_CONFIG.form_window
                )
                away_form_matches = self.api_client.get_team_form(
                    away_id,
                    games=DEFAULT_SOCCER_CONFIG.form_window
                )
                
                # 3. Calculate xG
                logger.info("Step 3: Calculating xG")
                
                # Try advanced calculation first (with form data)
                if home_form_matches and away_form_matches:
                    logger.debug("Using advanced xG calculation (form-weighted)")
                    home_xg = self.xg_calculator.calculate_advanced(
                        home_form_matches,
                        away_form_matches,
                        is_home=True
                    )
                    away_xg = self.xg_calculator.calculate_advanced(
                        away_form_matches,
                        home_form_matches,
                        is_home=False
                    )
                else:
                    logger.debug("Using simple xG calculation (stats-based)")
                    home_xg = self.xg_calculator.calculate(
                        home_stats,
                        away_stats,
                        is_home=True
                    )
                    away_xg = self.xg_calculator.calculate(
                        away_stats,
                        home_stats,
                        is_home=False
                    )
                
                logger.info(
                    f"xG: {home_team} {home_xg:.2f} - {away_xg:.2f} {away_team}"
                )
                
                # 4. Analyze form
                logger.info("Step 4: Analyzing team form")
                home_form = self.form_analyzer.analyze_team_form(
                    home_form_matches,
                    home_id
                )
                away_form = self.form_analyzer.analyze_team_form(
                    away_form_matches,
                    away_id
                )
                
                form_comparison = self.form_analyzer.compare_forms(
                    home_form,
                    away_form
                )
                
                # 5. Calculate probabilities (Poisson distribution)
                logger.info("Step 5: Calculating match probabilities")
                probabilities = ProbabilityEngine.from_poisson(
                    home_expected=home_xg,
                    away_expected=away_xg,
                    max_score=DEFAULT_SOCCER_CONFIG.max_score_simulation,
                    include_draw=True
                )
                
                logger.info(
                    f"Probabilities: Home {probabilities['home_win']:.1%} | "
                    f"Draw {probabilities['draw']:.1%} | "
                    f"Away {probabilities['away_win']:.1%}"
                )
                
                # Validate probabilities sum to ~1.0
                if not ProbabilityEngine.validate_probabilities(probabilities):
                    logger.error(
                        "Probabilities don't sum to 1.0",
                        extra={"probabilities": probabilities}
                    )
                
                # 6. Calculate confidence
                logger.info("Step 6: Calculating confidence score")
                confidence = self.calculate_confidence(
                    game_data,
                    {
                        "home_form": home_form,
                        "away_form": away_form,
                        "home_stats": home_stats,
                        "away_stats": away_stats,
                        "home_xg": home_xg,
                        "away_xg": away_xg
                    }
                )
                
                logger.info(f"Confidence: {confidence:.1%}")
                
                # 7. Build GameAnalysis
                logger.info("Step 7: Building GameAnalysis")
                
                analysis = GameAnalysis(
                    sport=Sport.SOCCER,
                    league=league_code,
                    game_id=game_id,
                    home_team=home_team,
                    away_team=away_team,
                    start_time=start_time,
                    probabilities=probabilities,
                    projections={
                        "total_goals": round(home_xg + away_xg, 2),
                        "home_goals": home_xg,
                        "away_goals": away_xg
                    },
                    confidence=confidence,
                    model_version="soccer_poisson_xg_v1.0",
                    context={
                        "home_form": home_form,
                        "away_form": away_form,
                        "form_comparison": form_comparison,
                        "home_stats": home_stats,
                        "away_stats": away_stats
                    }
                )
                
                logger.info("="*60)
                logger.info("Analysis complete")
                logger.info("="*60)
                
                return analysis
    
    def calculate_confidence(
        self,
        game_data: Dict,
        analysis_data: Dict
    ) -> float:
        """
        Calcula confidence score basado en calidad de datos
        
        Factores que REDUCEN confidence:
        - Sample size pequeño (< 5 juegos de form)
        - Stats incompletas (games_played = 0)
        - xG extremos (muy altos o muy bajos)
        - Form muy inconsistente
        
        Args:
            game_data: Datos raw del juego
            analysis_data: Stats calculadas
        
        Returns:
            Float entre 0-1 (1 = máxima confianza)
        """
        logger.debug("Calculating confidence score")
        
        confidence = 1.0
        
        # Factor 1: Sample size de form
        home_form_games = analysis_data["home_form"]["games_analyzed"]
        away_form_games = analysis_data["away_form"]["games_analyzed"]
        
        min_form_games = DEFAULT_SOCCER_CONFIG.min_games_for_confidence
        
        if home_form_games < min_form_games:
            reduction = (min_form_games - home_form_games) * \
                       DEFAULT_SOCCER_CONFIG.confidence_penalty_per_missing_game
            confidence *= (1 - reduction)
            logger.debug(
                f"Home form penalty: {reduction:.2%}",
                extra={"home_form_games": home_form_games}
            )
        
        if away_form_games < min_form_games:
            reduction = (min_form_games - away_form_games) * \
                       DEFAULT_SOCCER_CONFIG.confidence_penalty_per_missing_game
            confidence *= (1 - reduction)
            logger.debug(
                f"Away form penalty: {reduction:.2%}",
                extra={"away_form_games": away_form_games}
            )
        
        # Factor 2: Stats quality (si games_played = 0, son defaults)
        if analysis_data["home_stats"]["games_played"] == 0:
            confidence *= 0.70
            logger.debug("Home stats penalty: 30% (using defaults)")
        
        if analysis_data["away_stats"]["games_played"] == 0:
            confidence *= 0.70
            logger.debug("Away stats penalty: 30% (using defaults)")
        
        # Factor 3: xG extremos (fuera de rango típico)
        home_xg = analysis_data["home_xg"]
        away_xg = analysis_data["away_xg"]
        
        if home_xg > 3.5 or home_xg < 0.5:
            confidence *= 0.90
            logger.debug(
                f"Extreme home xG penalty: 10%",
                extra={"home_xg": home_xg}
            )
        
        if away_xg > 3.5 or away_xg < 0.5:
            confidence *= 0.90
            logger.debug(
                f"Extreme away xG penalty: 10%",
                extra={"away_xg": away_xg}
            )
        
        # Factor 4: Form strength muy baja (ambos equipos inconsistentes)
        home_strength = analysis_data["home_form"]["form_strength"]
        away_strength = analysis_data["away_form"]["form_strength"]
        
        if home_strength < 0.3 and away_strength < 0.3:
            confidence *= 0.85
            logger.debug("Both teams poor form penalty: 15%")
        
        # Clip final
        confidence = max(0.1, min(confidence, 1.0))
        
        logger.info(
            f"Final confidence: {confidence:.2%}",
            extra={
                "confidence": confidence,
                "home_form_games": home_form_games,
                "away_form_games": away_form_games
            }
        )
        
        return round(confidence, 2)
    
    def get_supported_markets(self) -> List[str]:
        """Mercados soportados para soccer"""
        return [
            "moneyline",     # 1X2 (Home/Draw/Away)
            "totals",        # Over/Under goals
            "btts"           # Both Teams To Score (futuro)
        ]