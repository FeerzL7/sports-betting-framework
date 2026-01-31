"""
Soccer-specific configuration

API: https://www.football-data.org/
Registro gratis: 10 requests/minuto
"""

# API-Football credentials
API_FOOTBALL_KEY = "996765d03c9045888a4805af8693a9a6"  # Obtener de https://www.football-data.org/client/register
API_FOOTBALL_BASE_URL = "https://api.football-data.org/v4"

# Ligas soportadas (IDs de API-Football)
SUPPORTED_LEAGUES = {
    "PL": {
        "name": "Premier League",
        "id": 2021,
        "country": "England"
    },
    "PD": {
        "name": "LaLiga",
        "id": 2014,
        "country": "Spain"
    },
    "SA": {
        "name": "Serie A",
        "id": 2019,
        "country": "Italy"
    },
    "BL1": {
        "name": "Bundesliga",
        "id": 2002,
        "country": "Germany"
    },
    "FL1": {
        "name": "Ligue 1",
        "id": 2015,
        "country": "France"
    }
}

# Expected Goals: Pesos por estadística
# Basado en análisis empírico de correlación xG
XG_WEIGHTS = {
    "shots_on_target": 0.12,      # 12% conversión promedio
    "shots_total": 0.04,           # 4% conversión promedio
    "possession": 0.01,            # 1 gol por 100% posesión extra
    "corners": 0.03,               # 3% conversión de corners
    "attacks": 0.005               # 0.5% conversión de ataques
}

# Form analysis: ventana de juegos
FORM_WINDOW = 5  # Últimos 5 partidos

# xG baseline por liga (goles promedio por partido)
LEAGUE_BASELINE_GOALS = {
    "PL": 2.8,
    "PD": 2.6,
    "SA": 2.7,
    "BL1": 3.1,
    "FL1": 2.7
}

# Ajuste por localía
HOME_ADVANTAGE = 1.15  # Local tiene 15% más xG que visitante en campo neutral