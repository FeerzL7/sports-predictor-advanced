from datetime import datetime
from datetime import datetime

SEASON = datetime.now().year

# ==========================
# Odds API (MLB specific)
# ==========================
SPORT = "baseball_mlb"
REGION = "us"

TODAY = datetime.now().strftime("%Y-%m-%d")

# ==========================
# Seasonal Modes (MLB)
# ==========================
def es_post_all_star() -> bool:
    year = datetime.now().year
    fecha_all_star = datetime(year, 7, 13)
    fin_periodo = datetime(year, 7, 15)
    hoy = datetime.now()
    return fecha_all_star <= hoy <= fin_periodo

def es_final_temporada() -> bool:
    return datetime.now().month >= 9

POST_ALL_STAR_MODE = es_post_all_star()
END_SEASON_MODE = es_final_temporada()

POST_ALL_STAR_SETTINGS = {
    "recent_games_weight": 0.40,
    "pitcher_last_start_required": True,
    "stake_multiplier": 0.75,
    "motivation_penalty": 0.05,
    "offense_volatility_factor": 1.05,
}

END_SEASON_SETTINGS = {
    "motivation_factor": 0.15,
    "variance_boost": 0.10,
    "stake_multiplier": 0.60,
}

VOLATILITY_POST_ASG_FACTOR = 1.15

# ==========================
# Park Factors (MLB)
# ==========================
PARK_FACTORS = {
    "Coors Field": 1.34,
    "Fenway Park": 1.12,
    "Globe Life Field": 1.10,
    "Oakland Coliseum": 0.94,
    "Dodger Stadium": 1.01,
    "Petco Park": 0.92,
    "Yankee Stadium": 1.08,
}

DEFAULT_PARK_FACTOR = 1.00

# ==========================
# Stadium Coordinates (Context)
# ==========================
STADIUM_COORDS = {
    "Coors Field": (39.7559, -104.9942),
    "Fenway Park": (42.3467, -71.0972),
    "Dodger Stadium": (34.0739, -118.2390),
    "Petco Park": (32.7076, -117.1570),
    "Yankee Stadium": (40.8296, -73.9262),
    "Globe Life Field": (32.7473, -97.0847),
    "Oakland Coliseum": (37.7516, -122.2005),
}

DEFAULT_STADIUM_COORD = (40.0, -100.0)

# ==========================
# Weather Impact (Baseball)
# ==========================
WEATHER_CODES = {
    0: "Despejado",
    1: "Principalmente despejado",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Niebla",
    51: "Llovizna ligera",
    61: "Lluvia moderada",
    71: "Nieve ligera",
    95: "Tormenta",
}

WEATHER_TEMP_NEUTRAL = 22.0
WEATHER_TEMP_PER_RUN = 0.005
WEATHER_WIND_PER_RUN = 0.002

# Confidence mínima aceptable cuando hay datos incompletos
WEATHER_MIN_SAMPLE_CONF = 0.70

# ==========================
# Context Penalties / Confidence
# ==========================
B2B_PENALTY_RUNS = 0.05
CONTEXT_BASE_CONFIDENCE = 0.70

CONTEXT_CONF_PENALTIES = {
    "no_weather": 0.90,
    "no_park": 0.95,
    # bullpen queda documentado, pero no activo en el modelo actual
}

# ==========================
# League Averages (MLB)
# ==========================
LEAGUE_ERA = 4.30
LEAGUE_FIP = 4.20
LEAGUE_K9 = 8.60
LEAGUE_BB9 = 3.30

LEAGUE_RPG = 4.60
LEAGUE_OPS = 0.715
LEAGUE_WRC_PLUS = 100.0
LEAGUE_DER = 0.685

LEAGUE_FPCT = 0.985
LEAGUE_ERRORS_PER_GAME = 0.55

EB_IP = 20.0
MIN_IP_CONFIDENT = 25.0

EB_GAMES = 162
MIN_GAMES_CONFIDENT = 40

# ==========================
# Pitcher / Recent Form
# ==========================
RECENT_DAYS = 15
RECENT_STARTS = 3
RECENT_GAMES = RECENT_DAYS
