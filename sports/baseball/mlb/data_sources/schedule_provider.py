# sports/baseball/mlb/data_sources/schedule_provider.py

from typing import List, Dict, Any

from sports.baseball.mlb.data_sources.mlb_api_wrapper import mlb_api_get


def get_schedule_by_date(date: str, season: int = None) -> List[Dict[str, Any]]:
    """
    Obtiene el calendario MLB para una fecha específica.
    """
    
    if season is None:
        season = int(date[:4])  # Extraer de fecha
    
    try:
        resp = mlb_api_get(
            "schedule",
            {"date": date},
            season=season
        )

        games = resp.get("dates", [])
        if not games:
            return []

        return games[0].get("games", [])

    except Exception:
        return []