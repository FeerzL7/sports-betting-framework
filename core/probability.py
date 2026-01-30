"""
Probability Engine - Conversión de proyecciones a probabilidades

RESPONSABILIDAD:
Convertir proyecciones numéricas (ej: "2.5 goles esperados") 
en probabilidades de outcomes (ej: "45% home win, 28% draw, 27% away win")

MÉTODOS:
- from_poisson: Deportes low-scoring (soccer, hockey, baseball)
- from_normal: Deportes high-scoring (basketball, football)
- from_logistic: Modelos ML custom

NO DEPENDE DE:
- Ningún deporte específico
- Ningún mercado específico
- APIs externas
"""
from typing import Dict, Tuple, Optional
from scipy.stats import poisson, norm
import numpy as np


class ProbabilityEngine:
    """
    Motor de conversión proyecciones → probabilidades
    
    Todos los métodos son estáticos (no necesita instancia).
    Puro cálculo matemático, sin estado.
    """
    
    @staticmethod
    def from_poisson(
        home_expected: float,
        away_expected: float,
        max_score: int = 10,
        include_draw: bool = True
    ) -> Dict[str, float]:
        """
        Simulación Poisson para deportes low-scoring
        
        CASOS DE USO:
        - Soccer: from_poisson(1.6, 1.2, include_draw=True)
        - Hockey: from_poisson(3.2, 2.8, include_draw=False)  # Overtime
        - Baseball: from_poisson(4.5, 4.2, include_draw=False)  # No ties
        
        Args:
            home_expected: Goles/runs esperados del local
            away_expected: Goles/runs esperados del visitante
            max_score: Score máximo a simular (performance)
            include_draw: Si incluir empate en resultados
        
        Returns:
            Dict con probabilidades:
            - include_draw=True: {"home_win", "draw", "away_win"}
            - include_draw=False: {"home_win", "away_win"}
        
        Ejemplo:
            >>> ProbabilityEngine.from_poisson(1.6, 1.2, include_draw=True)
            {"home_win": 0.452, "draw": 0.276, "away_win": 0.272}
        """
        prob_home = 0.0
        prob_draw = 0.0
        prob_away = 0.0
        
        # Simulación exhaustiva de todos los scores posibles
        for home_goals in range(max_score + 1):
            for away_goals in range(max_score + 1):
                # Probabilidad de este score exacto
                prob = (
                    poisson.pmf(home_goals, home_expected) *
                    poisson.pmf(away_goals, away_expected)
                )
                
                if home_goals > away_goals:
                    prob_home += prob
                elif home_goals == away_goals:
                    prob_draw += prob
                else:
                    prob_away += prob
        
        # Normalizar (por si max_score truncó probabilidad)
        total = prob_home + prob_draw + prob_away
        prob_home /= total
        prob_draw /= total
        prob_away /= total
        
        if include_draw:
            return {
                "home_win": round(prob_home, 4),
                "draw": round(prob_draw, 4),
                "away_win": round(prob_away, 4)
            }
        else:
            # Redistribuir probabilidad de empate
            # En baseball/hockey, empates se resuelven (extra innings/OT)
            # Asumimos 50/50 split del draw
            total_decisive = prob_home + prob_away
            return {
                "home_win": round(
                    (prob_home + prob_draw * 0.5) / (total_decisive + prob_draw), 
                    4
                ),
                "away_win": round(
                    (prob_away + prob_draw * 0.5) / (total_decisive + prob_draw), 
                    4
                )
            }
    
    @staticmethod
    def from_normal(
        home_mean: float,
        away_mean: float,
        home_std: float,
        away_std: float,
        simulations: int = 10000
    ) -> Dict[str, float]:
        """
        Simulación Monte Carlo con distribución normal
        
        CASOS DE USO:
        - NBA: from_normal(112.5, 108.3, std_home=8.5, std_away=7.8)
        - NFL: from_normal(24.2, 21.5, std_home=6.2, std_away=5.9)
        
        Args:
            home_mean: Puntos esperados del local
            away_mean: Puntos esperados del visitante
            home_std: Desviación estándar del local
            away_std: Desviación estándar del visitante
            simulations: Número de simulaciones Monte Carlo
        
        Returns:
            {"home_win": float, "away_win": float}
            
        Ejemplo:
            >>> ProbabilityEngine.from_normal(112.5, 108.3, 8.5, 7.8)
            {"home_win": 0.6823, "away_win": 0.3177}
        """
        # Generar simulaciones
        home_scores = np.random.normal(home_mean, home_std, simulations)
        away_scores = np.random.normal(away_mean, away_std, simulations)
        
        # Contar victorias
        home_wins = np.sum(home_scores > away_scores)
        
        prob_home = home_wins / simulations
        prob_away = 1 - prob_home
        
        return {
            "home_win": round(prob_home, 4),
            "away_win": round(prob_away, 4)
        }
    
    @staticmethod
    def from_score_differential(
        expected_diff: float,
        diff_std: float = 10.0
    ) -> Dict[str, float]:
        """
        Método alternativo: calcular probabilidad desde diferencia esperada
        
        CASOS DE USO:
        - Spread betting (NFL, NBA)
        - Cuando solo tienes proyección de diferencia, no scores absolutos
        
        Args:
            expected_diff: Diferencia esperada (positivo = local favorito)
            diff_std: Desviación estándar de la diferencia
        
        Returns:
            {"home_win": float, "away_win": float}
        
        Ejemplo:
            >>> # Local favorito por 5.5 puntos
            >>> ProbabilityEngine.from_score_differential(5.5, diff_std=10.0)
            {"home_win": 0.7088, "away_win": 0.2912}
        """
        # Probabilidad de que diff > 0 (local gana)
        prob_home = norm.cdf(expected_diff, loc=0, scale=diff_std)
        
        return {
            "home_win": round(prob_home, 4),
            "away_win": round(1 - prob_home, 4)
        }
    
    @staticmethod
    def calculate_over_under_probability(
        total_expected: float,
        line: float,
        distribution: str = "poisson",
        std: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Calcula probabilidad de Over/Under para totales
        
        Args:
            total_expected: Total proyectado (ej: 2.8 goles, 220.5 puntos)
            line: Línea del mercado (ej: 2.5, 225.0)
            distribution: "poisson" o "normal"
            std: Desviación estándar (solo para normal)
        
        Returns:
            (prob_over, prob_under)
        
        Ejemplo Soccer:
            >>> ProbabilityEngine.calculate_over_under_probability(
            ...     total_expected=2.8,
            ...     line=2.5,
            ...     distribution="poisson"
            ... )
            (0.5438, 0.4562)
        
        Ejemplo NBA:
            >>> ProbabilityEngine.calculate_over_under_probability(
            ...     total_expected=220.5,
            ...     line=225.0,
            ...     distribution="normal",
            ...     std=12.0
            ... )
            (0.3538, 0.6462)
        """
        if distribution == "poisson":
            # P(X > line) = 1 - P(X <= line)
            # En Poisson, sumamos PMF hasta floor(line)
            prob_under = poisson.cdf(int(line), total_expected)
            prob_over = 1 - prob_under
            
        elif distribution == "normal":
            if std is None:
                raise ValueError("std es requerido para distribución normal")
            
            # P(X > line) usando CDF normal
            prob_over = 1 - norm.cdf(line, loc=total_expected, scale=std)
            prob_under = 1 - prob_over
        
        else:
            raise ValueError(f"Distribución '{distribution}' no soportada")
        
        return (round(prob_over, 4), round(prob_under, 4))
    
    @staticmethod
    def validate_probabilities(probs: Dict[str, float], tolerance: float = 0.02) -> bool:
        """
        Valida que probabilidades sumen ~1.0
        
        Args:
            probs: Dict con probabilidades
            tolerance: Tolerancia para redondeo (default 2%)
        
        Returns:
            True si válido, False si no
        
        IMPORTANTE: Siempre validar antes de usar probabilidades en cálculos
        """
        total = sum(probs.values())
        return (1.0 - tolerance) <= total <= (1.0 + tolerance)