import requests
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, List, Set

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
def obtener_clima(lat: float, lon: float) -> Dict[str, Any]:
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true"
            },
            timeout=8
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
# B2B HELPERS
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
# CONTEXT HELPERS
# =========================
def estimar_impacto_clima(clima: Dict[str, Any]) -> float:
    temp = clima.get("temperatura", WEATHER_TEMP_NEUTRAL)
    viento = clima.get("viento_kph", 10.0)

    impact_temp = (temp - WEATHER_TEMP_NEUTRAL) * WEATHER_TEMP_PER_RUN
    impact_wind = (viento - 10.0) * WEATHER_WIND_PER_RUN

    return round(impact_temp + impact_wind, 3)

def calcular_confidence(
    has_weather: bool,
    has_park: bool,
    has_bullpen: bool
) -> float:
    conf = CONTEXT_BASE_CONFIDENCE

    if not has_weather:
        conf *= CONTEXT_CONF_PENALTIES["no_weather"]
    if not has_park:
        conf *= CONTEXT_CONF_PENALTIES["no_park"]
    if not has_bullpen:
        conf *= CONTEXT_CONF_PENALTIES["no_bullpen"]

    return round(max(min(conf, 1.0), 0.4), 3)

def _tz_hour(start_time_iso: str, tz: str = "US/Eastern") -> int:
    try:
        dt = datetime.strptime(start_time_iso, "%Y-%m-%dT%H:%M:%S")
        return (
            dt.replace(tzinfo=pytz.utc)
              .astimezone(pytz.timezone(tz))
              .hour
        )
    except Exception:
        return 19

# =========================
# CORE BUILDER
# =========================
def _build_team_context(
    team: str,
    estadio: str,
    start_time_iso: str,
    teams_b2b: Set[str]
) -> Dict[str, Any]:

    lat, lon = STADIUM_COORDS.get(estadio, DEFAULT_STADIUM_COORD)
    clima = obtener_clima(lat, lon)
    hora_local = _tz_hour(start_time_iso)

    park_factor = PARK_FACTORS.get(estadio, DEFAULT_PARK_FACTOR)
    pf_ok = estadio in PARK_FACTORS

    b2b = team in teams_b2b
    penalties = B2B_PENALTY_RUNS if b2b else 0.0

    clima_impact = estimar_impacto_clima(clima)

    confidence = calcular_confidence(
        has_weather=clima["condiciones"] != "desconocido",
        has_park=pf_ok,
        has_bullpen=False
    )

    return {
        "team": team,
        "estadio": estadio,
        "hora_local": hora_local,
        "park_factor": park_factor,
        "b2b": b2b,
        "clima": clima,
        "impacto_clima_carreras": clima_impact,
        "penalizaciones_carreras": round(penalties, 3),
        "confidence": confidence,
        "flags": {
            "no_bullpen_model": True,
            "no_weather_dir": True,
            "no_park_factor": not pf_ok
        }
    }

# =========================
# PUBLIC API
# =========================
def analizar_contexto(partidos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    print("[INFO] Analizando contexto (clima, park factor, B2B)...")

    if not partidos:
        return partidos

    date = partidos[0].get(
        "date",
        datetime.now().strftime("%Y-%m-%d")
    )

    yesterday = (
        datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)
    ).strftime("%Y-%m-%d")

    games_ayer = get_schedule_by_date(yesterday)
    teams_b2b = _teams_that_played(games_ayer)

    for p in partidos:
        estadio = p.get("venue", "default")
        start_time = p.get("start_time", f"{date}T19:00:00")

        home = p["home_team"]
        away = p["away_team"]

        p["home_context"] = _build_team_context(
            home, estadio, start_time, teams_b2b
        )
        p["away_context"] = _build_team_context(
            away, estadio, start_time, teams_b2b
        )

        p.setdefault("data_warnings", [])

        for side, ctx in (
            ("HOME", p["home_context"]),
            ("AWAY", p["away_context"])
        ):
            if ctx["flags"]["no_bullpen_model"]:
                p["data_warnings"].append(f"{side}_NO_BULLPEN_MODEL")
            if ctx["flags"]["no_park_factor"]:
                p["data_warnings"].append(f"{side}_NO_PARK_FACTOR")
            if ctx["clima"]["condiciones"] == "desconocido":
                p["data_warnings"].append(f"{side}_NO_WEATHER")

    return partidos
