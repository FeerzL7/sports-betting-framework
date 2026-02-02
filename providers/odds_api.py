"""
Odds API Provider - Production odds source

API: https://the-odds-api.com/
Docs: https://the-odds-api.com/lv4/supported-leagues/

RESPONSABILIDAD:
- Fetch odds desde The Odds API
- Normalizar a OddsData (formato universal)
- Seleccionar best available odds por outcome
- Manejar rate limits y errores

IMPORTANTE:
- La API retorna odds en formato decimal
- Múltiples bookmakers por juego → tomamos el máximo por outcome
- Team names pueden diferir vs API-Football → normalización es crítica

NO ES RESPONSABLE DE:
- Calcular edge (lo hace Market)
- Decidir qué juegos analizar (lo hace Orchestrator)
- Matching con games del adapter (lo hace Orchestrator)
"""
import requests
from typing import List, Optional, Dict
from datetime import datetime
from providers.base import OddsProviderBase
from core.models import OddsData, Sport
from config.api_keys import get_api_config
from utils import (
    get_logger,
    DataFetchError,
    RateLimitError,
    AuthenticationError,
    PerformanceLogger
)
import time

logger = get_logger(__name__)


# ============================================================
# LEAGUE MAPPING
# The Odds API usa sport keys y league slugs diferentes a API-Football.
# Este mapping conecta nuestros códigos internos con la API externa.
# ============================================================

SPORT_TO_ODDS_API = {
    Sport.SOCCER: "soccer",
    Sport.MLB: "baseball",
    Sport.NFL: "americanfootball",
    Sport.NBA: "basketball",
    Sport.TENNIS: "tennis"
}

# Liga → slug en The Odds API
# Agregar nuevas ligas aquí cuando las implementemos
LEAGUE_TO_ODDS_API = {
    # Soccer
    "PL": "soccer_england_premier_league",
    "PD": "soccer_spain_la_liga",
    "SA": "soccer_italy_serie_a",
    "BL1": "soccer_germany_bundesliga",
    "FL1": "soccer_france_ligue_1",
}

# Market keys que pedimos a la API
ODDS_API_MARKETS = ["h2h", "totals"]  # h2h = moneyline, totals = over/under


class OddsAPIProvider(OddsProviderBase):
    """
    Provider de odds usando The Odds API (producción).

    SELECCIÓN DE BEST ODDS:
    La API retorna múltiples bookmakers. Para cada outcome,
    tomamos la odds máxima disponible (mejor valor para el bettor).

    Ejemplo:
        DraftKings: home=2.10, away=1.85
        Bet365:     home=2.15, away=1.80
        → Usamos: home=2.15 (Bet365), away=1.85 (DraftKings)
    """

    provider_name = "OddsAPIProvider"

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: API key de The Odds API (usa config si no se provee)
        """
        api_config = get_api_config("odds_api")

        self.api_key = api_key or api_config["api_key"]
        self.base_url = api_config["base_url"]
        self.rate_limit = api_config.get("rate_limit", 20)

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 60.0 / self.rate_limit

        # Cache para evitar requests repetidos en el mismo run
        self._cache: Dict[str, List[OddsData]] = {}

        logger.info(
            "OddsAPIProvider initialized",
            extra={"base_url": self.base_url}
        )

    def get_odds(
        self,
        sport: Sport,
        league: str,
        date: Optional[str] = None
    ) -> List[OddsData]:
        """
        Fetch odds desde The Odds API.

        Args:
            sport: Sport enum
            league: Código interno ("PL", "PD", etc.)
            date: Filtro de fecha (The Odds API no soporta filtro directo,
                  así que filtramos después del fetch)

        Returns:
            Lista de OddsData normalizados con best odds por outcome
        """
        # Check cache
        cache_key = f"{sport.value}_{league}_{date}"
        if cache_key in self._cache:
            logger.debug(f"Cache hit: {cache_key}")
            return self._cache[cache_key]

        # Validate sport mapping
        odds_api_sport = SPORT_TO_ODDS_API.get(sport)
        if not odds_api_sport:
            logger.warning(f"Sport {sport.value} not mapped to Odds API")
            return []

        # Validate league mapping
        odds_api_league = LEAGUE_TO_ODDS_API.get(league)
        if not odds_api_league:
            logger.warning(f"League {league} not mapped to Odds API")
            return []

        perf = PerformanceLogger(logger, f"OddsAPI: {sport.value}/{league}")

        with perf.track():
            try:
                raw_data = self._make_request(odds_api_sport, odds_api_league)
                odds_list = self._normalize_response(raw_data, sport)

                # Cache el resultado
                self._cache[cache_key] = odds_list

                logger.info(
                    f"Fetched {len(odds_list)} games with odds",
                    extra={"sport": sport.value, "league": league}
                )

                return odds_list

            except Exception as e:
                logger.error(
                    f"Failed to fetch odds",
                    extra={"sport": sport.value, "league": league, "error": str(e)}
                )
                return []  # Retorna vacío, no explota el pipeline

    def get_game_odds(self, game_id: str) -> Optional[OddsData]:
        """
        Busca odds por game_id.

        NOTA: game_id en este provider es generado internamente
        (formato: "{sport}_{home_normalized}_{away_normalized}").
        El Orchestrator es responsable del matching.
        """
        # Buscar en todo el cache
        for cached_list in self._cache.values():
            for odds in cached_list:
                if odds.game_id == game_id:
                    return odds

        logger.debug(f"No cached odds for game_id={game_id}")
        return None

    # ================================================================
    # PRIVATE: API communication
    # ================================================================

    def _make_request(self, sport: str, league: str) -> List[Dict]:
        """
        Hace request a The Odds API con rate limiting.

        Args:
            sport: Sport key ("soccer", "baseball", etc.)
            league: League slug

        Returns:
            Lista de raw game dicts de la API

        Raises:
            DataFetchError: Si la API no responde
            AuthenticationError: Si API key inválida
            RateLimitError: Si se excede rate limit
        """
        # Rate limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.min_request_interval:
            wait = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: waiting {wait:.2f}s")
            time.sleep(wait)

        url = f"{self.base_url}/{sport}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "us,uk",
            "markets": ",".join(ODDS_API_MARKETS),
            "oddsFormat": "decimal"
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            self.last_request_time = time.time()

            if response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError(
                    "The Odds API: invalid key or insufficient permissions",
                    endpoint=url
                )

            if response.status_code == 429:
                raise RateLimitError(
                    "The Odds API: rate limit exceeded",
                    endpoint=url
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            raise DataFetchError(
                "The Odds API: request timeout",
                endpoint=url
            )
        except requests.exceptions.RequestException as e:
            if isinstance(e, (AuthenticationError, RateLimitError, DataFetchError)):
                raise
            raise DataFetchError(
                f"The Odds API: connection error - {e}",
                endpoint=url
            )

    # ================================================================
    # PRIVATE: Normalization
    # ================================================================

    def _normalize_response(
        self,
        raw_games: List[Dict],
        sport: Sport
    ) -> List[OddsData]:
        """
        Convierte response raw de The Odds API a List[OddsData].

        Para cada juego:
        1. Generar game_id normalizado
        2. Iterar bookmakers → seleccionar best odds por outcome
        3. Extraer línea de totals si disponible
        """
        result = []

        for game in raw_games:
            try:
                odds_data = self._normalize_single_game(game, sport)
                if odds_data:
                    result.append(odds_data)
            except Exception as e:
                logger.warning(
                    f"Failed to normalize game, skipping",
                    extra={"game_id": game.get("id"), "error": str(e)}
                )
                continue

        return result

    def _normalize_single_game(self, game: Dict, sport: Sport) -> Optional[OddsData]:
        """Normaliza un solo juego de la API response."""
        home_team = self._normalize_team_name(game.get("home_team", ""), sport)
        away_team = self._normalize_team_name(game.get("away_team", ""), sport)

        # game_id normalizado para matching con adapter
        game_id = f"{sport.value}_{home_team}_{away_team}"

        # Acumuladores para best odds
        best_home_odds = None
        best_away_odds = None
        best_draw_odds = None
        best_over_odds = None
        best_under_odds = None
        total_line = None
        best_bookmaker = "unknown"

        # Iterar bookmakers
        for bookmaker in game.get("bookmakers", []):
            bm_name = bookmaker.get("title", "unknown")

            for market in bookmaker.get("markets", []):
                market_key = market.get("key")

                if market_key == "h2h":
                    # Moneyline / 1X2
                    outcomes = {
                        o["name"].lower(): o["price"]
                        for o in market.get("outcomes", [])
                    }

                    # Home
                    home_price = outcomes.get(home_team) or outcomes.get(
                        game.get("home_team", "").lower()
                    )
                    if home_price and (best_home_odds is None or home_price > best_home_odds):
                        best_home_odds = home_price
                        best_bookmaker = bm_name

                    # Away
                    away_price = outcomes.get(away_team) or outcomes.get(
                        game.get("away_team", "").lower()
                    )
                    if away_price and (best_away_odds is None or away_price > best_away_odds):
                        best_away_odds = away_price

                    # Draw (solo soccer)
                    draw_price = outcomes.get("draw")
                    if draw_price and (best_draw_odds is None or draw_price > best_draw_odds):
                        best_draw_odds = draw_price

                elif market_key == "totals":
                    # Over/Under
                    for outcome in market.get("outcomes", []):
                        name = outcome.get("name", "").lower()
                        price = outcome.get("price")
                        point = outcome.get("point")

                        if name == "over" and price:
                            if best_over_odds is None or price > best_over_odds:
                                best_over_odds = price
                                total_line = point

                        elif name == "under" and price:
                            if best_under_odds is None or price > best_under_odds:
                                best_under_odds = price

        # Si no tenemos odds básicos, skip este juego
        if best_home_odds is None and best_away_odds is None:
            return None

        return OddsData(
            game_id=game_id,
            sport=sport,
            bookmaker=best_bookmaker,
            home_odds=best_home_odds,
            away_odds=best_away_odds,
            draw_odds=best_draw_odds,
            total_line=total_line,
            over_odds=best_over_odds,
            under_odds=best_under_odds,
            spread_line=None,
            spread_home_odds=None,
            spread_away_odds=None
        )

    def _normalize_team_name(self, name: str, sport: Sport) -> str:
        """
        Normaliza nombre de equipo para matching.

        The Odds API vs API-Football tienen nombres diferentes:
        - "Manchester United" vs "Manchester Utd"
        - "Real Madrid CF" vs "Real Madrid"

        Estrategia: lowercase + remover sufijos comunes.
        En futuro: fuzzy matching con difflib.
        """
        normalized = super()._normalize_team_name(name, sport)

        # Remover sufijos comunes
        suffixes = [" cf", " fc", " afc", " s.a.d.", " ltd"]
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()

        return normalized