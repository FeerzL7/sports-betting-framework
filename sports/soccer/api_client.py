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
from utils import get_logger, DataFetchError, RateLimitError, AuthenticationError, PerformanceLogger

# Setup logger for this module
logger = get_logger(__name__)


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
        
        logger.info(
            "API-Football client initialized",
            extra={
                "base_url": self.base_url,
                "rate_limit": f"{self.rate_limit} req/min"
            }
        )
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Hace request a la API con rate limiting
        
        Args:
            endpoint: "/competitions/PD/matches"
            params: Query parameters
        
        Returns:
            JSON response
        
        Raises:
            DataFetchError: Si API no responde
            AuthenticationError: Si API key inválida
            RateLimitError: Si rate limit excedido
        """
        # Rate limiting: esperar si es necesario
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
        
        url = f"{self.base_url}{endpoint}"
        
        # Track performance
        perf = PerformanceLogger(logger, f"API Request: {endpoint}")
        
        with perf.track():
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                self.last_request_time = time.time()
                
                if response.status_code == 403:
                    logger.error("API authentication failed", extra={"endpoint": endpoint})
                    raise AuthenticationError(
                        "API key inválida o sin permisos",
                        endpoint=endpoint
                    )
                
                if response.status_code == 429:
                    logger.warning("API rate limit exceeded", extra={"endpoint": endpoint})
                    raise RateLimitError(
                        "Rate limit excedido",
                        endpoint=endpoint,
                        retry_after="60s"
                    )
                
                response.raise_for_status()
                
                logger.debug(
                    "API request successful",
                    extra={
                        "endpoint": endpoint,
                        "status": response.status_code
                    }
                )
                
                return response.json()
            
            except requests.exceptions.Timeout:
                logger.error("API request timeout", extra={"endpoint": endpoint})
                raise DataFetchError(
                    f"API timeout for {endpoint}",
                    endpoint=endpoint,
                    timeout="10s"
                )
            
            except requests.exceptions.RequestException as e:
                logger.error(
                    "API request failed",
                    extra={
                        "endpoint": endpoint,
                        "error": str(e)
                    }
                )
                raise DataFetchError(
                    f"Error al conectar con API-Football: {e}",
                    endpoint=endpoint
                )
    
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
        """
        if league_code not in SUPPORTED_SOCCER_LEAGUES:
            logger.error(
                "Unsupported league",
                extra={"league_code": league_code}
            )
            raise ValueError(f"Liga '{league_code}' no soportada")
        
        # Construir filtro de fecha
        if date is None:
            date_from = datetime.now().strftime("%Y-%m-%d")
            date_to = date_from
        else:
            date_from = date
            date_to = date
        
        logger.info(
            "Fetching fixtures",
            extra={
                "league": league_code,
                "date": date_from
            }
        )
        
        endpoint = f"/competitions/{league_code}/matches"
        params = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "status": "SCHEDULED"
        }
        
        data = self._make_request(endpoint, params)
        fixtures = data.get("matches", [])
        
        logger.info(
            f"Found {len(fixtures)} fixtures",
            extra={
                "league": league_code,
                "count": len(fixtures)
            }
        )
        
        return fixtures
    
    def get_team_stats(self, team_id: int, league_code: str) -> Dict:
        """Obtiene estadísticas de un equipo en la temporada"""
        logger.debug(
            "Fetching team stats",
            extra={"team_id": team_id, "league": league_code}
        )
        
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
                logger.warning(
                    "No matches found for team",
                    extra={"team_id": team_id}
                )
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
            
            stats = {
                "goals_per_game": round(total_goals_for / games_count, 2),
                "goals_against_per_game": round(total_goals_against / games_count, 2),
                "games_played": games_count,
                "total_goals": total_goals_for,
                "total_conceded": total_goals_against
            }
            
            logger.debug(
                "Team stats calculated",
                extra={
                    "team_id": team_id,
                    "games": games_count,
                    "goals_per_game": stats["goals_per_game"]
                }
            )
            
            return stats
        
        except Exception as e:
            logger.warning(
                "Failed to fetch team stats, using defaults",
                extra={
                    "team_id": team_id,
                    "error": str(e)
                }
            )
            return self._get_default_team_stats()
    
    def get_head_to_head(self, team1_id: int, team2_id: int, limit: int = 5) -> List[Dict]:
        """Obtiene historial entre dos equipos"""
        logger.debug(
            "Fetching H2H",
            extra={
                "team1": team1_id,
                "team2": team2_id,
                "limit": limit
            }
        )
        
        endpoint = f"/teams/{team1_id}/matches"
        params = {
            "season": datetime.now().year,
            "status": "FINISHED",
            "limit": 50
        }
        
        try:
            data = self._make_request(endpoint, params)
            all_matches = data.get("matches", [])
            
            # Filtrar solo partidos contra team2
            h2h_matches = [
                m for m in all_matches
                if m["homeTeam"]["id"] == team2_id or m["awayTeam"]["id"] == team2_id
            ]
            
            result = h2h_matches[:limit]
            
            logger.debug(
                f"Found {len(result)} H2H matches",
                extra={"count": len(result)}
            )
            
            return result
        
        except Exception as e:
            logger.warning(
                "Failed to fetch H2H",
                extra={
                    "team1": team1_id,
                    "team2": team2_id,
                    "error": str(e)
                }
            )
            return []
    
    def get_team_form(self, team_id: int, games: int = 5) -> List[Dict]:
        """Obtiene últimos N partidos de un equipo"""
        logger.debug(
            "Fetching team form",
            extra={"team_id": team_id, "games": games}
        )
        
        endpoint = f"/teams/{team_id}/matches"
        params = {
            "season": datetime.now().year,
            "status": "FINISHED",
            "limit": games
        }
        
        try:
            data = self._make_request(endpoint, params)
            matches = data.get("matches", [])
            
            logger.debug(
                f"Retrieved {len(matches)} form matches",
                extra={"team_id": team_id}
            )
            
            return matches
        except Exception as e:
            logger.warning(
                "Failed to fetch team form",
                extra={
                    "team_id": team_id,
                    "error": str(e)
                }
            )
            return []
    
    @staticmethod
    def _get_default_team_stats() -> Dict:
        """Stats por default si API falla"""
        logger.debug("Using default team stats")
        return {
            "goals_per_game": 1.5,
            "goals_against_per_game": 1.5,
            "games_played": 0,
            "total_goals": 0,
            "total_conceded": 0
        }
    
    def normalize_team_name(self, api_name: str) -> str:
        """Normaliza nombres de equipos"""
        suffixes = [" CF", " FC", " AFC", " United", " City"]
        normalized = api_name
        
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        
        logger.debug(
            f"Normalized team name: '{api_name}' → '{normalized}'"
        )
        
        return normalized.strip()