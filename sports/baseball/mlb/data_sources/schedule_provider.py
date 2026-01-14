from typing import List, Dict, Any

from sports.baseball.mlb.data_sources.statsapi_client import statsapi_get


def get_schedule_by_date(date: str) -> List[Dict[str, Any]]:
    """
    Obtiene el calendario MLB para una fecha específica.
    Devuelve la lista cruda de juegos de StatsAPI.
    """
    try:
        resp = statsapi_get(
            "schedule",
            {"date": date}
        )

        games = resp.get("dates", [])
        if not games:
            return []

        # StatsAPI devuelve fechas → juegos
        return games[0].get("games", [])

    except Exception:
        return []
