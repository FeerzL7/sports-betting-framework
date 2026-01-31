"""
API-Football Client

RESPONSABILIDADES:
- Fetch fixtures (partidos)
- Fetch team stats
- Fetch head-to-head
- Manejar rate limiting
- Normalizar respuestas

NO ES RESPONSABLE DE:
- Calcular xG (lo hace xg_calculator.py)
- Analizar form (lo hace form_analyzer.py)
- Generar probabilidades (lo hace adapter.py)
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime
import time
from config.soccer_config import SUPPORTED_SOCCER_LEAGUES
from config.api_keys import get_api_config


class APIFootballClient:
    """
    Client para API-Football (football-data.org)
    
    Rate limit: 10 requests/minuto (plan gratuito)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: API key (usa config si no se provee)
        """
        # Get config from centralized location
        api_config = get_api_config("api_football")
        
        self.api_key = api_key or api_config["api_key"]
        self.base_url = api_config["base_url"]
        self.rate_limit = api_config["rate_limit"]
        
        self.headers = {
            "X-Auth-Token": self.api_key
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 60.0 / self.rate_limit  # seconds per request
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Hace request a la API con rate limiting
        
        Args:
            endpoint: "/competitions/PD/matches"
            params: Query parameters
        
        Returns:
            JSON response
        
        Raises:
            ConnectionError: Si API no responde
            ValueError: Si API key inválida
        """
        # Rate limiting: esperar si es necesario
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            self.last_request_time = time.time()
            
            if response.status_code == 403:
                raise ValueError("API key inválida o sin permisos")
            
            if response.status_code == 429:
                raise ConnectionError("Rate limit excedido. Espera 1 minuto.")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error al conectar con API-Football: {e}")
    
    def get_fixtures(
        self,
        league_code: str,
        date: Optional[str] = None
    ) -> List[Dict]:
        """
        Obtiene partidos de una liga
        
        Args:
            league_code: "PL", "PD", "SA", etc.
            date: "YYYY-MM-DD" (None = hoy)
        
        Returns:
            Lista de fixtures
        
        Ejemplo response:
            [
                {
                    "id": 327185,
                    "utcDate": "2025-01-30T20:00:00Z",
                    "homeTeam": {"id": 86, "name": "Real Madrid"},
                    "awayTeam": {"id": 81, "name": "Barcelona"},
                    "status": "SCHEDULED"
                },
                ...
            ]
        """
        if league_code not in SUPPORTED_SOCCER_LEAGUES:
            raise ValueError(f"Liga '{league_code}' no soportada")
        
        # Construir filtro de fecha
        if date is None:
            date_from = datetime.now().strftime("%Y-%m-%d")
            date_to = date_from
        else:
            date_from = date
            date_to = date
        
        endpoint = f"/competitions/{league_code}/matches"
        params = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "status": "SCHEDULED"  # Solo partidos por jugarse
        }
        
        data = self._make_request(endpoint, params)
        return data.get("matches", [])
    
    def get_team_stats(self, team_id: int, league_code: str) -> Dict:
        """
        Obtiene estadísticas de un equipo en la temporada
        
        Args:
            team_id: ID del equipo
            league_code: "PL", "PD", etc.
        
        Returns:
            Dict con stats agregadas
        
        NOTA: API-Football no provee stats agregadas directamente.
              Calculamos desde últimos partidos.
        """
        # Obtener últimos partidos del equipo
        endpoint = f"/teams/{team_id}/matches"
        params = {
            "season": datetime.now().year,
            "limit": 10,
            "status": "FINISHED"
        }
        
        try:
            data = self._make_request(endpoint, params)
            matches = data.get("matches", [])
            
            if not matches:
                return self._get_default_team_stats()
            
            # Agregar stats desde partidos
            total_goals_for = 0
            total_goals_against = 0
            games_count = len(matches)
            
            for match in matches:
                is_home = match["homeTeam"]["id"] == team_id
                
                if is_home:
                    total_goals_for += match["score"]["fullTime"]["home"]
                    total_goals_against += match["score"]["fullTime"]["away"]
                else:
                    total_goals_for += match["score"]["fullTime"]["away"]
                    total_goals_against += match["score"]["fullTime"]["home"]
            
            return {
                "goals_per_game": round(total_goals_for / games_count, 2),
                "goals_against_per_game": round(total_goals_against / games_count, 2),
                "games_played": games_count,
                "total_goals": total_goals_for,
                "total_conceded": total_goals_against
            }
        
        except Exception as e:
            print(f"[WARNING] Error fetching team stats: {e}")
            return self._get_default_team_stats()
    
    def get_head_to_head(self, team1_id: int, team2_id: int, limit: int = 5) -> List[Dict]:
        """
        Obtiene historial entre dos equipos
        
        Args:
            team1_id, team2_id: IDs de equipos
            limit: Número de partidos a obtener
        
        Returns:
            Lista de partidos históricos
        """
        endpoint = f"/teams/{team1_id}/matches"
        params = {
            "season": datetime.now().year,
            "status": "FINISHED",
            "limit": 50  # Fetch más para filtrar después
        }
        
        try:
            data = self._make_request(endpoint, params)
            all_matches = data.get("matches", [])
            
            # Filtrar solo partidos contra team2
            h2h_matches = [
                m for m in all_matches
                if m["homeTeam"]["id"] == team2_id or m["awayTeam"]["id"] == team2_id
            ]
            
            return h2h_matches[:limit]
        
        except Exception as e:
            print(f"[WARNING] Error fetching H2H: {e}")
            return []
    
    def get_team_form(self, team_id: int, games: int = 5) -> List[Dict]:
        """
        Obtiene últimos N partidos de un equipo
        
        Args:
            team_id: ID del equipo
            games: Número de partidos
        
        Returns:
            Lista de últimos partidos con resultados
        """
        endpoint = f"/teams/{team_id}/matches"
        params = {
            "season": datetime.now().year,
            "status": "FINISHED",
            "limit": games
        }
        
        try:
            data = self._make_request(endpoint, params)
            return data.get("matches", [])
        except Exception as e:
            print(f"[WARNING] Error fetching team form: {e}")
            return []
    
    @staticmethod
    def _get_default_team_stats() -> Dict:
        """Stats por default si API falla"""
        return {
            "goals_per_game": 1.5,
            "goals_against_per_game": 1.5,
            "games_played": 0,
            "total_goals": 0,
            "total_conceded": 0
        }
    
    def normalize_team_name(self, api_name: str) -> str:
        """
        Normaliza nombres de equipos
        
        Problema: API-Football dice "Real Madrid CF"
                 Odds API dice "Real Madrid"
        
        Solución: Remover sufijos comunes
        """
        suffixes = [" CF", " FC", " AFC", " United", " City"]
        normalized = api_name
        
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        
        return normalized.strip()