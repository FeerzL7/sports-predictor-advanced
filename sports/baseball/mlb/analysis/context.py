from datetime import datetime, timedelta
from typing import Dict, Any, List, Set
import pytz
import requests

from sports.baseball.mlb.data_sources.schedule_provider import get_schedule_by_date
from sports.baseball.mlb.constants.mlb_constants import (
    PARK_FACTORS,
    DEFAULT_PARK_FACTOR,
    STADIUM_COORDS,
    DEFAULT_STADIUM_COORD,
    WEATHER_CODES,
    WEATHER_TEMP_NEUTRAL,
    WEATHER_TEMP_PER_RUN,
    WEATHER_WIND_PER_RUN,
    B2B_PENALTY_RUNS,
    CONTEXT_BASE_CONFIDENCE,
    CONTEXT_CONF_PENALTIES,
)

# =========================
# WEATHER
# =========================
_SESSION = requests.Session()

def obtener_clima(lat: float, lon: float) -> Dict[str, Any]:
    try:
        resp = _SESSION.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true"
            },
            timeout=6
        )
        clima = resp.json().get("current_weather", {})
        return {
            "temperatura": clima.get("temperature", WEATHER_TEMP_NEUTRAL),
            "viento_kph": clima.get("windspeed", 10.0),
            "condiciones": WEATHER_CODES.get(
                clima.get("weathercode"),
                "desconocido"
            )
        }
    except Exception:
        return {
            "temperatura": WEATHER_TEMP_NEUTRAL,
            "viento_kph": 10.0,
            "condiciones": "desconocido"
        }

# =========================
# B2B
# =========================
def _teams_that_played(games: List[Dict[str, Any]]) -> Set[str]:
    teams = set()
    for g in games:
        if g.get("home_name"):
            teams.add(g["home_name"])
        if g.get("away_name"):
            teams.add(g["away_name"])
    return teams

# =========================
# HELPERS
# =========================
def estimar_impacto_clima(clima: Dict[str, Any]) -> float:
    temp = clima.get("temperatura", WEATHER_TEMP_NEUTRAL)
    wind = clima.get("viento_kph", 10.0)

    return round(
        (temp - WEATHER_TEMP_NEUTRAL) * WEATHER_TEMP_PER_RUN +
        (wind - 10.0) * WEATHER_WIND_PER_RUN,
        3
    )

def calcular_confidence(has_weather: bool, has_park: bool) -> float:
    conf = CONTEXT_BASE_CONFIDENCE

    if not has_weather:
        conf *= CONTEXT_CONF_PENALTIES["no_weather"]
    if not has_park:
        conf *= CONTEXT_CONF_PENALTIES["no_park"]

    return round(max(min(conf, 1.0), 0.4), 3)

def _tz_hour(start_time_iso: str, tz: str = "US/Eastern") -> int:
    try:
        dt = datetime.fromisoformat(start_time_iso.replace("Z", ""))
        return (
            dt.replace(tzinfo=pytz.utc)
              .astimezone(pytz.timezone(tz))
              .hour
        )
    except Exception:
        return 19

# =========================
# CORE
# =========================
def _build_team_context(
    team: str,
    estadio: str,
    start_time_iso: str,
    teams_b2b: Set[str],
    clima: Dict[str, Any]
) -> Dict[str, Any]:

    park_factor = PARK_FACTORS.get(estadio, DEFAULT_PARK_FACTOR)
    pf_ok = estadio in PARK_FACTORS

    b2b = team in teams_b2b
    penalties = B2B_PENALTY_RUNS if b2b else 0.0

    confidence = calcular_confidence(
        has_weather=clima["condiciones"] != "desconocido",
        has_park=pf_ok
    )

    return {
        "team": team,
        "estadio": estadio,
        "hora_local": _tz_hour(start_time_iso),
        "park_factor": park_factor,
        "b2b": b2b,
        "clima": clima,
        "impacto_clima_carreras": estimar_impacto_clima(clima),
        "penalizaciones_carreras": round(penalties, 3),
        "confidence": confidence,
        "flags": {
            "no_weather": clima["condiciones"] == "desconocido",
            "no_park_factor": not pf_ok
        }
    }

# =========================
# PUBLIC API
# =========================
def analizar_contexto(partidos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not partidos:
        return partidos

    date = partidos[0].get(
        "date",
        datetime.now().strftime("%Y-%m-%d")
    )

    yesterday = (
        datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)
    ).strftime("%Y-%m-%d")

    teams_b2b = _teams_that_played(
        get_schedule_by_date(yesterday)
    )

    for p in partidos:
        estadio = p.get("venue", "default")
        start_time = p.get("start_time", f"{date}T19:00:00")

        lat, lon = STADIUM_COORDS.get(estadio, DEFAULT_STADIUM_COORD)
        clima = obtener_clima(lat, lon)

        p["home_context"] = _build_team_context(
            p["home_team"], estadio, start_time, teams_b2b, clima
        )
        p["away_context"] = _build_team_context(
            p["away_team"], estadio, start_time, teams_b2b, clima
        )

    return partidos
