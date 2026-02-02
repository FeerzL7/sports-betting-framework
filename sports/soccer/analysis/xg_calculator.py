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
        Calcula xG para un equipo en un partido (método simple, stats-based)

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
        team_id: int,
        opponent_id: int,
        is_home: bool = True
    ) -> float:
        """
        Cálculo avanzado con form reciente (ponderado por recencia)

        Args:
            team_form: Últimos N partidos del equipo objetivo
            opponent_form: Últimos N partidos del oponente
            team_id: ID del equipo objetivo (necesario para leer el score correcto)
            opponent_id: ID del oponente (necesario para leer sus goles concedidos)
            is_home: Si el equipo objetivo juega de local en el partido a analizar

        Returns:
            xG ajustado por form

        POR QUÉ team_id es obligatorio:
        Cada match dict tiene {"homeTeam": {"id": X}, "awayTeam": {"id": Y}}.
        Sin saber cuál es "nuestro" equipo, no podemos determinar si jugó
        home o away en cada partido histórico, y por tanto no sabemos de
        qué campo del score leer los goles.
        """
        if not team_form or not opponent_form:
            logger.warning(
                "Insufficient form data, using simple calculation",
                extra={
                    "team_form_games": len(team_form) if team_form else 0,
                    "opp_form_games": len(opponent_form) if opponent_form else 0
                }
            )
            # Fallback a método simple con baseline
            return self.calculate(
                {"goals_per_game": self.baseline},
                {"goals_against_per_game": self.baseline},
                is_home
            )

        logger.debug(
            "Calculating advanced xG with form data",
            extra={
                "team_id": team_id,
                "opponent_id": opponent_id,
                "team_form_games": len(team_form),
                "opp_form_games": len(opponent_form)
            }
        )

        weights = DEFAULT_SOCCER_CONFIG.form_weights

        # --- Goles ANOTADOS por el equipo objetivo ---
        team_goals_weighted = []
        for i, match in enumerate(team_form[:len(weights)]):
            weight = weights[i]

            # Determinar si el equipo objetivo jugó de local en ESTE partido
            played_home = match["homeTeam"]["id"] == team_id

            if played_home:
                goals = match["score"]["fullTime"]["home"]
            else:
                goals = match["score"]["fullTime"]["away"]

            team_goals_weighted.append(goals * weight)

            logger.debug(
                f"  Team match {i}: goals={goals}, home={played_home}, weight={weight}",
                extra={"match_home_id": match["homeTeam"]["id"], "team_id": team_id}
            )

        active_weights_team = weights[:len(team_goals_weighted)]
        team_weighted_avg = sum(team_goals_weighted) / sum(active_weights_team)

        logger.debug(
            f"Team weighted average: {team_weighted_avg:.2f} goals/game",
            extra={"weighted_avg": team_weighted_avg}
        )

        # --- Goles CONCEDIDOS por el oponente ---
        opp_conceded_weighted = []
        for i, match in enumerate(opponent_form[:len(weights)]):
            weight = weights[i]

            # Determinar si el oponente jugó de local en ESTE partido
            opp_played_home = match["homeTeam"]["id"] == opponent_id

            # Los goles concedidos por el oponente son los que metió el OTRO equipo
            if opp_played_home:
                conceded = match["score"]["fullTime"]["away"]
            else:
                conceded = match["score"]["fullTime"]["home"]

            opp_conceded_weighted.append(conceded * weight)

            logger.debug(
                f"  Opp match {i}: conceded={conceded}, home={opp_played_home}, weight={weight}",
                extra={"match_home_id": match["homeTeam"]["id"], "opponent_id": opponent_id}
            )

        active_weights_opp = weights[:len(opp_conceded_weighted)]
        opp_weighted_avg = sum(opp_conceded_weighted) / sum(active_weights_opp)

        logger.debug(
            f"Opponent weighted conceded: {opp_weighted_avg:.2f} goals/game",
            extra={"opp_weighted_avg": opp_weighted_avg}
        )

        # --- Combinar: promedio de ofensiva propia + defensiva rival ---
        xg = (team_weighted_avg + opp_weighted_avg) / 2

        # Ajuste por localía del partido A ANALIZAR (no de los históricos)
        if is_home:
            xg *= self.home_advantage
        else:
            xg /= self.home_advantage

        # Clipping
        xg = max(0.3, min(xg, 4.0))
        xg_final = round(xg, 2)

        logger.info(
            f"Advanced xG calculated: {xg_final:.2f}",
            extra={
                "xg": xg_final,
                "method": "form_weighted",
                "is_home": is_home,
                "team_id": team_id,
                "opponent_id": opponent_id
            }
        )

        return xg_final