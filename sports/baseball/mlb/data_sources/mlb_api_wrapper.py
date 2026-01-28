# sports/baseball/mlb/data_sources/mlb_api_wrapper.py

"""
Wrapper para StatsAPI que agrega parámetros requeridos automáticamente.
"""

from typing import Dict, Any
from sports.baseball.mlb.data_sources.statsapi_client import statsapi_get


def mlb_api_get(
    endpoint: str,
    params: Dict[str, Any],
    season: int = 2024,
    **kwargs
) -> Dict[str, Any]:
    """
    Wrapper que agrega season automáticamente si falta.
    
    Args:
        endpoint: Endpoint de StatsAPI
        params: Parámetros del request
        season: Año de la temporada (default 2024 para backtest)
        **kwargs: Otros argumentos (retries, sleep, etc)
    
    Returns:
        Response de StatsAPI
    """
    
    # Copiar params para no mutar original
    params = params.copy()
    
    # Endpoints que requieren season
    season_required = [
        "team_stats",
        "team_game_logs",
        "player_stats"
    ]
    
    # Agregar season si no está y es requerido
    if endpoint in season_required and "season" not in params:
        params["season"] = season
    
    # Agregar sportId si es schedule y no está
    if endpoint == "schedule" and "sportId" not in params:
        params["sportId"] = 1  # MLB
    
    return statsapi_get(endpoint, params, **kwargs)