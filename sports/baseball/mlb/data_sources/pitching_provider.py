from typing import List, Dict, Any, Optional

from sports.baseball.mlb.data_sources.statsapi_client import (
    statsapi_get,
    safe_int,
    safe_float
)

from statsapi import lookup_player, player_stat_data


# =========================
# PLAYERS
# =========================

def lookup_player_id(name: str) -> Optional[int]:
    """
    Devuelve player_id a partir del nombre.
    Maneja TBD / unknown / errores silenciosamente.
    """
    if not name or name.lower() in ("tbd", "probable", "desconocido", "unknown"):
        return None

    try:
        res = lookup_player(name)
        if res:
            return safe_int(res[0].get("id"))
    except Exception:
        pass

    return None


def get_pitch_hand(player_id: int) -> Optional[str]:
    """
    Devuelve 'R' o 'L'. None si no disponible.
    """
    if not player_id:
        return None

    try:
        resp = statsapi_get("people", {"personIds": player_id})
        people = resp.get("people", [])

        if not people:
            return None

        return people[0].get("pitchHand", {}).get("code")

    except Exception:
        return None


# =========================
# STATS
# =========================

def get_season_pitching_stats(player_id: int, season: int) -> Dict[str, Any]:
    """
    Stats de temporada para un pitcher.
    Devuelve dict vacío si no hay data.
    """
    if not player_id or not season:
        return {}

    try:
        data = player_stat_data(
            player_id,
            group="pitching",
            type="season",
            season=season
        )

        stats = data.get("stats", [])
        if not stats:
            return {}

        return stats[0].get("stats", {}) or {}

    except Exception:
        return {}


def get_game_logs(player_id: int, season: int) -> List[Dict[str, Any]]:
    """
    Game logs de temporada.
    Devuelve lista vacía si falla.
    """
    if not player_id or not season:
        return []

    try:
        data = player_stat_data(
            player_id,
            group="pitching",
            type="gameLog",
            season=season
        )

        return data.get("stats", []) or []

    except Exception:
        return []
