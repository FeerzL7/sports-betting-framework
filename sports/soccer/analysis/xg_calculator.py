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
from typing import List,Dict
from sports.soccer.config import (
    XG_WEIGHTS,
    LEAGUE_BASELINE_GOALS,
    HOME_ADVANTAGE
)


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
        self.baseline = LEAGUE_BASELINE_GOALS.get(league_code, 2.7)
    
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
        
        # 3. Ajuste por calidad defensiva del oponente
        opp_conceded_avg = opponent_stats.get("goals_against_per_game", self.baseline)
        defensive_weakness = opp_conceded_avg / self.baseline
        xg *= defensive_weakness
        
        # 4. Ajuste por localía
        if is_home:
            xg *= HOME_ADVANTAGE
        else:
            xg /= HOME_ADVANTAGE
        
        # 5. Clipping: xG debe estar en rango realista
        xg = max(0.3, min(xg, 4.0))
        
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
            # Fallback a método simple
            return self.calculate(
                {"goals_per_game": self.baseline},
                {"goals_against_per_game": self.baseline},
                is_home
            )
        
        # Calcular goles promedio ponderados por recencia
        team_goals = []
        weights = [1.5, 1.3, 1.1, 1.0, 0.9]  # Más reciente = más peso
        
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
        
        # Combinar con baseline
        xg = (weighted_avg + opp_weighted_avg) / 2
        
        # Ajuste por localía
        if is_home:
            xg *= HOME_ADVANTAGE
        else:
            xg /= HOME_ADVANTAGE
        
        return round(xg, 2)