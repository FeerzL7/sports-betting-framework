"""
Form Analyzer - Análisis de racha reciente

MÉTRICAS:
- Win rate últimos N juegos
- Goals scored/conceded trend
- Home/Away form
- Clean sheets rate
"""
from typing import Dict, List
from config.soccer_config import DEFAULT_SOCCER_CONFIG
from utils import get_logger

# Setup logger
logger = get_logger(__name__)


class FormAnalyzer:
    """
    Analiza la racha reciente de un equipo
    
    OUTPUT: Metrics que ajustan confidence del modelo
    """
    
    @staticmethod
    def analyze_team_form(matches: List[Dict], team_id: int) -> Dict:
        """
        Analiza form de un equipo
        
        Args:
            matches: Últimos N partidos del equipo (ya filtrados)
            team_id: ID del equipo
        
        Returns:
            {
                "win_rate": 0.6,
                "goals_per_game": 1.8,
                "conceded_per_game": 1.2,
                "clean_sheets_pct": 0.4,
                "form_strength": 0.75  # 0-1 (qué tan buena es la racha)
            }
        """
        if not matches:
            logger.warning(
                "No matches provided for form analysis",
                extra={"team_id": team_id}
            )
            return FormAnalyzer._get_default_form()
        
        logger.debug(
            f"Analyzing form for team {team_id}",
            extra={"team_id": team_id, "matches_count": len(matches)}
        )
        
        wins = 0
        draws = 0
        goals_scored = 0
        goals_conceded = 0
        clean_sheets = 0
        
        for match in matches:
            is_home = match["homeTeam"]["id"] == team_id
            
            if is_home:
                team_goals = match["score"]["fullTime"]["home"]
                opp_goals = match["score"]["fullTime"]["away"]
            else:
                team_goals = match["score"]["fullTime"]["away"]
                opp_goals = match["score"]["fullTime"]["home"]
            
            goals_scored += team_goals
            goals_conceded += opp_goals
            
            if opp_goals == 0:
                clean_sheets += 1
            
            if team_goals > opp_goals:
                wins += 1
            elif team_goals == opp_goals:
                draws += 1
        
        games = len(matches)
        
        form_result = {
            "games_analyzed": games,
            "win_rate": round(wins / games, 3),
            "draw_rate": round(draws / games, 3),
            "goals_per_game": round(goals_scored / games, 2),
            "conceded_per_game": round(goals_conceded / games, 2),
            "clean_sheets_pct": round(clean_sheets / games, 3),
            "form_strength": FormAnalyzer._calculate_form_strength(
                wins, draws, games
            )
        }
        
        logger.info(
            f"Form analysis complete",
            extra={
                "team_id": team_id,
                "games": games,
                "win_rate": form_result["win_rate"],
                "form_strength": form_result["form_strength"]
            }
        )
        
        return form_result
    
    @staticmethod
    def _calculate_form_strength(wins: int, draws: int, games: int) -> float:
        """
        Calcula "fuerza" de la racha (0-1)
        
        3 puntos por victoria, 1 por empate
        Normalizado a 0-1
        """
        points = (wins * 3) + (draws * 1)
        max_points = games * 3
        
        strength = round(points / max_points, 3) if max_points > 0 else 0.5
        
        logger.debug(
            f"Form strength calculated: {strength:.3f}",
            extra={
                "wins": wins,
                "draws": draws,
                "games": games,
                "points": points
            }
        )
        
        return strength
    
    @staticmethod
    def _get_default_form() -> Dict:
        """Form por default si no hay datos"""
        logger.debug("Using default form values")
        return {
            "games_analyzed": 0,
            "win_rate": 0.33,  # Asumimos 33% (promedio liga)
            "draw_rate": 0.27,
            "goals_per_game": 1.5,
            "conceded_per_game": 1.5,
            "clean_sheets_pct": 0.30,
            "form_strength": 0.50
        }
    
    @staticmethod
    def compare_forms(home_form: Dict, away_form: Dict) -> Dict:
        """
        Compara forms de dos equipos
        
        Returns:
            {
                "home_advantage_form": 0.2,  # Home tiene 20% mejor form
                "total_expected_goals": 2.8,
                "high_scoring_likely": False
            }
        """
        home_strength = home_form["form_strength"]
        away_strength = away_form["form_strength"]
        
        form_diff = home_strength - away_strength
        
        total_goals = (
            home_form["goals_per_game"] +
            away_form["goals_per_game"]
        ) / 2
        
        comparison = {
            "home_advantage_form": round(form_diff, 3),
            "total_expected_goals": round(total_goals, 2),
            "high_scoring_likely": total_goals > 3.0,
            "defensive_battle": (
                home_form["clean_sheets_pct"] > 0.4 and
                away_form["clean_sheets_pct"] > 0.4
            )
        }
        
        logger.info(
            "Form comparison complete",
            extra={
                "home_strength": home_strength,
                "away_strength": away_strength,
                "form_diff": form_diff,
                "high_scoring": comparison["high_scoring_likely"]
            }
        )
        
        return comparison