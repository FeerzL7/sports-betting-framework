"""
Expected Goals (xG) Calculator

RESPONSABILIDAD:
Calcular goles esperados basado en stats ofensivas/defensivas.

MÉTODO:
xG = f(shots_on_target, shots_total, possession, corners, attacks)

Pesos calibrados desde análisis histórico de ligas top 5.

IMPORTANTE:
- xG es una PROYECCIÓN, no una predicción exacta
- Ajustar por opponent quality
- Incluir home advantage
"""
from typing import List, Dict
from config.soccer_config import (
    get_league_baseline,
    get_home_advantage,
    DEFAULT_SOCCER_CONFIG
)
from utils import get_logger

# Setup logger
logger = get_logger(__name__)


class ExpectedGoalsCalculator:
    """
    Calculador de xG (Expected Goals)
    
    ENTRADA: Stats ofensivas del equipo
    SALIDA: Goles esperados (float)
    """
    
    def __init__(self, league_code: str = "PL"):
        """
        Args:
            league_code: "PL", "PD", "SA", etc.
        """
        self.league_code = league_code
        self.baseline = get_league_baseline(league_code)
        self.home_advantage = get_home_advantage(league_code)
        
        logger.debug(
            f"xG Calculator initialized for {league_code}",
            extra={
                "league": league_code,
                "baseline": self.baseline,
                "home_advantage": self.home_advantage
            }
        )
    
    def calculate(
        self,
        team_stats: Dict,
        opponent_stats: Dict,
        is_home: bool = True
    ) -> float:
        """
        Calcula xG para un equipo en un partido
        
        Args:
            team_stats: Stats ofensivas del equipo
                       {"goals_per_game", "shots_on_target_avg", ...}
            
            opponent_stats: Stats defensivas del oponente
                           {"goals_against_per_game", ...}
            
            is_home: Si el equipo juega de local
        
        Returns:
            Expected goals (ej: 1.8)
        
        FÓRMULA:
        xG = baseline_liga * (ataque_team / ataque_promedio) * (defensa_opp / defensa_promedio)
        """
        # 1. Base: goles promedio de la liga
        xg = self.baseline
        
        # 2. Ajuste por calidad ofensiva del equipo
        team_goals_avg = team_stats.get("goals_per_game", self.baseline)
        offensive_strength = team_goals_avg / self.baseline
        xg *= offensive_strength
        
        logger.debug(
            f"Offensive adjustment: {offensive_strength:.3f}x",
            extra={"team_goals_avg": team_goals_avg}
        )
        
        # 3. Ajuste por calidad defensiva del oponente
        opp_conceded_avg = opponent_stats.get("goals_against_per_game", self.baseline)
        defensive_weakness = opp_conceded_avg / self.baseline
        xg *= defensive_weakness
        
        logger.debug(
            f"Defensive adjustment: {defensive_weakness:.3f}x",
            extra={"opp_conceded_avg": opp_conceded_avg}
        )
        
        # 4. Ajuste por localía
        if is_home:
            xg *= self.home_advantage
            logger.debug(f"Home advantage applied: {self.home_advantage}x")
        else:
            xg /= self.home_advantage
            logger.debug(f"Away disadvantage applied: {1/self.home_advantage:.3f}x")
        
        # 5. Clipping: xG debe estar en rango realista
        xg_raw = xg
        xg = max(0.3, min(xg, 4.0))
        
        if xg != xg_raw:
            logger.debug(
                f"xG clipped from {xg_raw:.2f} to {xg:.2f}",
                extra={"xg_raw": xg_raw, "xg_clipped": xg}
            )
        
        logger.info(
            f"xG calculated: {xg:.2f}",
            extra={
                "xg": xg,
                "is_home": is_home,
                "offensive_strength": offensive_strength,
                "defensive_weakness": defensive_weakness
            }
        )
        
        return round(xg, 2)
    
    def calculate_advanced(
        self,
        team_form: List[Dict],
        opponent_form: List[Dict],
        is_home: bool = True
    ) -> float:
        """
        Cálculo avanzado con form reciente
        
        Args:
            team_form: Últimos N partidos del equipo
            opponent_form: Últimos N partidos del oponente
            is_home: Localía
        
        Returns:
            xG ajustado por form
        
        MEJORA: Pesa más los partidos recientes
        """
        if not team_form or not opponent_form:
            logger.warning(
                "Insufficient form data, using simple calculation",
                extra={
                    "team_form_games": len(team_form) if team_form else 0,
                    "opp_form_games": len(opponent_form) if opponent_form else 0
                }
            )
            # Fallback a método simple
            return self.calculate(
                {"goals_per_game": self.baseline},
                {"goals_against_per_game": self.baseline},
                is_home
            )
        
        logger.debug(
            "Calculating advanced xG with form data",
            extra={
                "team_form_games": len(team_form),
                "opp_form_games": len(opponent_form)
            }
        )
        
        # Calcular goles promedio ponderados por recencia
        team_goals = []
        weights = DEFAULT_SOCCER_CONFIG.form_weights
        
        for i, match in enumerate(team_form[:5]):
            weight = weights[i] if i < len(weights) else 0.8
            
            # Determinar goles del equipo
            team_id = match.get("homeTeam", {}).get("id")
            is_home_match = team_id == match["homeTeam"]["id"]
            
            if is_home_match:
                goals = match["score"]["fullTime"]["home"]
            else:
                goals = match["score"]["fullTime"]["away"]
            
            team_goals.append(goals * weight)
        
        weighted_avg = sum(team_goals) / sum(weights[:len(team_goals)])
        
        logger.debug(
            f"Team weighted average: {weighted_avg:.2f} goals/game",
            extra={"weighted_avg": weighted_avg}
        )
        
        # Similar para oponente (goles concedidos)
        opp_conceded = []
        for i, match in enumerate(opponent_form[:5]):
            weight = weights[i] if i < len(weights) else 0.8
            
            is_home_match = match["homeTeam"]["id"] == match.get("homeTeam", {}).get("id")
            
            if is_home_match:
                conceded = match["score"]["fullTime"]["away"]
            else:
                conceded = match["score"]["fullTime"]["home"]
            
            opp_conceded.append(conceded * weight)
        
        opp_weighted_avg = sum(opp_conceded) / sum(weights[:len(opp_conceded)])
        
        logger.debug(
            f"Opponent weighted conceded: {opp_weighted_avg:.2f} goals/game",
            extra={"opp_weighted_avg": opp_weighted_avg}
        )
        
        # Combinar con baseline
        xg = (weighted_avg + opp_weighted_avg) / 2
        
        # Ajuste por localía
        if is_home:
            xg *= self.home_advantage
        else:
            xg /= self.home_advantage
        
        xg_final = round(xg, 2)
        
        logger.info(
            f"Advanced xG calculated: {xg_final:.2f}",
            extra={
                "xg": xg_final,
                "method": "form_weighted",
                "is_home": is_home
            }
        )
        
        return xg_final