import requests
from datetime import datetime, timedelta
import pytz
from sports.baseball.mlb.data_sources.schedule_provider import get_schedule_by_date

from typing import Dict, Any, List, Optional

from sports.baseball.mlb.constants.mlb_constants import (
    PARK_FACTORS,
    DEFAULT_PARK_FACTOR,
    WEATHER_TEMP_NEUTRAL,
    WEATHER_TEMP_PER_RUN,
    WEATHER_WIND_PER_RUN,
    WEATHER_MIN_SAMPLE_CONF,
    B2B_PENALTY_RUNS,
    CONTEXT_BASE_CONFIDENCE,
)

# Coordenadas geográficas de estadios conocidos (puedes moverlo a constants.py si quieres)
COORDENADAS_ESTADIOS = {
    'Coors Field': (39.7559, -104.9942),
    'Fenway Park': (42.3467, -71.0972),
    'Dodger Stadium': (34.0739, -118.2390),
    'Petco Park': (32.7076, -117.1570),
    'Yankee Stadium': (40.8296, -73.9262),
    'Globe Life Field': (32.7473, -97.0847),
    'Oakland Coliseum': (37.7516, -122.2005),
    'default': (40.0, -100.0)
}

CLIMA_CODES = {
    0: 'Despejado', 1: 'Principalmente despejado', 2: 'Parcialmente nublado',
    3: 'Nublado', 45: 'Niebla', 51: 'Llovizna ligera', 61: 'Lluvia moderada',
    71: 'Nieve ligera', 95: 'Tormenta',
}

def obtener_clima(lat: float, lon: float) -> Dict[str, Any]:
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "current_weather": "true"}
        response = requests.get(url, params=params, timeout=10)
        clima = response.json().get('current_weather', {})
        return {
            'temperatura': clima.get('temperature', WEATHER_TEMP_NEUTRAL),
            'viento_kph': clima.get('windspeed', 10),
            'condiciones': CLIMA_CODES.get(clima.get('weathercode'), 'desconocido')
        }
    except Exception as e:
        print(f"[ERROR] Al obtener clima: {e}")
        return {'temperatura': WEATHER_TEMP_NEUTRAL, 'viento_kph': 10, 'condiciones': 'desconocido'}

def jugo_ayer(equipo: str, date_str: str) -> bool:
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        yesterday = (date - timedelta(days=1)).strftime('%Y-%m-%d')
        games = get_schedule_by_date(yesterday)
        return any(g['home_name'] == equipo or g['away_name'] == equipo for g in games)
    except:
        return False

def estimar_impacto_clima(clima: Dict[str, Any]) -> float:
    """
    Estima impacto en carreras por temperatura y viento.
    Muy simplificado. Ajusta los pesos en constants.py
    """
    temp = clima.get('temperatura', WEATHER_TEMP_NEUTRAL)
    viento = clima.get('viento_kph', 10)

    delta_temp = temp - WEATHER_TEMP_NEUTRAL
    impact_temp = delta_temp * WEATHER_TEMP_PER_RUN

    # Nota: sin dirección del viento, esto es un proxy muy burdo
    impact_wind = (viento - 10) * WEATHER_WIND_PER_RUN

    return round(impact_temp + impact_wind, 3)

def calcular_confidence(has_weather: bool, has_park: bool, has_bullpen: bool = False) -> float:
    conf = CONTEXT_BASE_CONFIDENCE
    if not has_weather:
        conf *= 0.9
    if not has_park:
        conf *= 0.95
    if not has_bullpen:
        conf *= 0.85
    return round(max(min(conf, 1.0), 0.4), 3)

def _tz_hour(start_time_iso: str, tz: str = 'US/Eastern') -> int:
    try:
        start_time = datetime.strptime(start_time_iso, "%Y-%m-%dT%H:%M:%S")
        return start_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(tz)).hour
    except Exception as e:
        print(f"[ERROR] Al convertir hora del partido: {e}")
        return 19

def _build_team_context(team: str, estadio: str, date: str, start_time_iso: str, is_home: bool) -> Dict[str, Any]:
    lat, lon = COORDENADAS_ESTADIOS.get(estadio, COORDENADAS_ESTADIOS['default'])
    clima = obtener_clima(lat, lon)
    hora_local = _tz_hour(start_time_iso)

    park_factor = PARK_FACTORS.get(estadio, DEFAULT_PARK_FACTOR)
    pf_ok = estadio in PARK_FACTORS

    # B2B
    b2b = jugo_ayer(team, date)
    penalties = B2B_PENALTY_RUNS if b2b else 0.0

    # Impacto clima
    clima_impact = estimar_impacto_clima(clima)

    confidence = calcular_confidence(
        has_weather=clima.get('condiciones') != 'desconocido',
        has_park=pf_ok,
        has_bullpen=False # hook pendiente
    )

    return {
        'team': team,
        'estadio': estadio,
        'hora_local': hora_local,
        'park_factor': park_factor,
        'b2b': b2b,
        'clima': clima,
        'impacto_clima_carreras': clima_impact,
        'penalizaciones_carreras': round(penalties, 3),
        'confidence': confidence,
        'flags': {
            'no_bullpen_model': True,
            'no_weather_dir': True,   # no dirección del viento
            'no_park_factor': not pf_ok
        }
    }

def analizar_contexto(partidos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    print("[INFO] Analizando contexto (clima, PF, b2b)...")
    for p in partidos:
        date = p.get('date', datetime.now().strftime('%Y-%m-%d'))
        estadio = p.get('venue', 'default')
        start_time_iso = p.get('start_time', f"{date}T19:00:00")  # fallback

        home = p['home_team']
        away = p['away_team']

        p['home_context'] = _build_team_context(home, estadio, date, start_time_iso, is_home=True)
        p['away_context'] = _build_team_context(away, estadio, date, start_time_iso, is_home=False)

        # warnings
        p.setdefault('data_warnings', [])
        for key, ctx in [('HOME', p['home_context']), ('AWAY', p['away_context'])]:
            if ctx['flags']['no_bullpen_model']:
                p['data_warnings'].append(f'{key}_NO_BULLPEN_MODEL')
            if ctx['flags']['no_park_factor']:
                p['data_warnings'].append(f'{key}_NO_PARK_FACTOR')
            if ctx['clima']['condiciones'] == 'desconocido':
                p['data_warnings'].append(f'{key}_NO_WEATHER')

    return partidos

def pretty_print_context(partidos: List[Dict[str, Any]]) -> None:
    """
    Muestra una tablita simple en consola para inspección rápida.
    """
    headers = (
        "Equipo", "Estadio", "PF", "B2B", "Temp", "Viento(kph)", "ImpactoWx",
        "Penal B2B", "HoraLocal", "Conf"
    )
    line = "-" * 112
    print(line)
    print("{:<18} {:<20} {:>4} {:>4} {:>5} {:>11} {:>10} {:>10} {:>9} {:>6}".format(*headers))
    print(line)
    for p in partidos:
        for side in ['home_context', 'away_context']:
            c = p[side]
            print("{:<18} {:<20} {:>4.2f} {:>4} {:>5.1f} {:>11.1f} {:>10.2f} {:>10.2f} {:>9} {:>6.2f}".format(
                c['team'][:18],
                c['estadio'][:20],
                c['park_factor'],
                "Y" if c['b2b'] else "N",
                c['clima'].get('temperatura', 0.0),
                c['clima'].get('viento_kph', 0.0),
                c['impacto_clima_carreras'],
                c['penalizaciones_carreras'],
                c['hora_local'],
                c['confidence'],
            ))
    print(line)
