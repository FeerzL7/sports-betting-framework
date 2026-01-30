"""
Sport Adapter Base Contract

REGLA CRÍTICA: Todo deporte DEBE implementar esta interfaz.
Si no puede calcular algo → devuelve None o valores default seguros.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
from core.models import GameAnalysis, Sport


class SportAdapter(ABC):
    """
    Contrato universal para adapters de deportes
    
    RESPONSABILIDADES:
    1. Fetch games desde API específica del deporte
    2. Analizar cada juego (stats, proyecciones, contexto)
    3. Convertir a GameAnalysis (contrato universal)
    4. Calcular confidence score basado en calidad de datos
    
    NO ES RESPONSABLE DE:
    - Fetch de odds (lo hace OddsProvider)
    - Cálculo de edge (lo hace Market)
    - Stake sizing (lo hace KellyCalculator)
    - Gestión de riesgo (lo hace RiskManager)
    """
    
    sport: Sport
    supported_leagues: List[str]
    
    @abstractmethod
    def fetch_games(self, date: str, league: str) -> List[Dict]:
        """
        Obtiene partidos desde API específica del deporte
        
        Args:
            date: "YYYY-MM-DD"
            league: "LaLiga", "MLB", etc.
        
        Returns:
            Lista de raw game data (formato específico del deporte)
            Cada dict debe tener al menos: home_team, away_team, start_time
        
        Raises:
            ValueError: Si league no está en supported_leagues
            ConnectionError: Si API no responde
        """
        pass
    
    @abstractmethod
    def analyze_game(self, game_data: Dict) -> GameAnalysis:
        """
        Analiza un juego y produce GameAnalysis
        
        PIPELINE TÍPICO:
        1. Extraer teams/fecha del game_data
        2. Fetch stats de equipos (form, xG, ERA, etc.)
        3. Fetch contexto (injuries, weather, stadium)
        4. Calcular proyecciones (goals, runs, points)
        5. Convertir proyecciones → probabilidades
        6. Calcular confidence score
        7. Empaquetar en GameAnalysis
        
        Args:
            game_data: Dict con datos raw del juego
        
        Returns:
            GameAnalysis con contrato completo
        
        IMPORTANTE:
        - Si faltan datos críticos → confidence bajo (ej: 0.5)
        - Si NO se puede calcular algo → None en ese campo
        - NUNCA lanzar excepciones por datos faltantes
        """
        pass
    
    @abstractmethod
    def calculate_confidence(self, game_data: Dict, analysis_data: Dict) -> float:
        """
        Calcula confidence score (0-1) basado en calidad de datos
        
        Factores que REDUCEN confidence:
        - Sample size pequeño (ej: equipo con <10 juegos)
        - Datos faltantes (injuries sin info, stats incompletas)
        - Alta varianza en proyecciones
        - Contexto inusual (ej: juego en campo neutral)
        
        Args:
            game_data: Datos raw del juego
            analysis_data: Stats calculadas en analyze_game
        
        Returns:
            Float entre 0-1 (1 = máxima confianza)
        
        Ejemplo:
            confidence = 1.0
            if team_games < 10: confidence *= 0.7
            if missing_injury_data: confidence *= 0.85
            if high_variance: confidence *= 0.9
            return confidence
        """
        pass
    
    def get_supported_markets(self) -> List[str]:
        """
        Qué mercados tiene sentido para este deporte
        
        Default: moneyline + totals (universal)
        Soccer puede agregar: draw, btts
        NFL puede agregar: spread, player_props
        
        Override si necesitas customizar
        """
        return ["moneyline", "totals"]
    
    def validate_league(self, league: str) -> None:
        """Helper para validar league antes de fetch"""
        if league not in self.supported_leagues:
            raise ValueError(
                f"League '{league}' no soportada. "
                f"Opciones: {', '.join(self.supported_leagues)}"
            )