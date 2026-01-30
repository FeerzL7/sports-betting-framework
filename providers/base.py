"""
Odds Provider Base Contract

REGLA: El adapter NUNCA llama directamente a una API de odds.
Siempre usa OddsProviderBase.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from core.models import OddsData, Sport


class OddsProviderBase(ABC):
    """
    Interface para providers de cuotas
    
    IMPLEMENTACIONES:
    - OddsAPIProvider: The Odds API (producción)
    - FakeOddsProvider: Datos hardcodeados (testing)
    
    RESPONSABILIDADES:
    1. Fetch cuotas desde fuente externa
    2. Normalizar a OddsData (formato universal)
    3. Manejar errores de API (rate limits, timeouts)
    
    NO ES RESPONSABLE DE:
    - Decidir qué juegos analizar (lo hace Orchestrator)
    - Calcular edge (lo hace Market)
    """
    
    provider_name: str
    
    @abstractmethod
    def get_odds(
        self,
        sport: Sport,
        league: str,
        date: Optional[str] = None
    ) -> List[OddsData]:
        """
        Obtiene cuotas para juegos de una liga
        
        Args:
            sport: Sport enum
            league: "LaLiga", "MLB", etc.
            date: "YYYY-MM-DD" (None = hoy)
        
        Returns:
            Lista de OddsData normalizados
        
        IMPORTANTE:
        - Siempre devolver lista (vacía si no hay datos)
        - NUNCA lanzar excepción por datos faltantes
        - Loggear warnings si API falla
        - Usar best available odds (max odds por outcome)
        """
        pass
    
    @abstractmethod
    def get_game_odds(self, game_id: str) -> Optional[OddsData]:
        """
        Obtiene cuotas para un juego específico
        
        Args:
            game_id: ID único del juego
        
        Returns:
            OddsData o None si no encontrado
        """
        pass
    
    def _normalize_team_name(self, api_name: str, sport: Sport) -> str:
        """
        Normaliza nombres de equipos entre APIs
        
        Problema común:
        - Stats API: "Real Madrid"
        - Odds API: "Real Madrid CF"
        
        Solución: fuzzy matching + mappings hardcodeados
        
        Override en subclases para sport-specific logic
        """
        return api_name.strip().lower()