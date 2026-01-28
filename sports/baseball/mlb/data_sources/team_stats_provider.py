# sports/baseball/mlb/data_sources/team_stats_provider.py

from typing import Dict, Any, Optional
from statsapi import lookup_team

from sports.baseball.mlb.data_sources.mlb_api_wrapper import mlb_api_get
from sports.baseball.mlb.data_sources.statsapi_client import safe_int, safe_float

# =========================
# TEAM ID
# =========================

def get_team_id(team_name: str) -> Optional[int]:
    """
    Devuelve team_id a partir del nombre del equipo.
    """
    if not team_name:
        return None

    try:
        res = lookup_team(team_name)
        if res:
            return res[0]["id"]
    except Exception:
        pass

    return None


# =========================
# SEASON OFFENSE STATS
# =========================

def get_team_season_stats(team_id: int, season: int = 2024) -> Dict[str, Any]:
    """
    Stats ofensivos de temporada (season).
    """
    try:
        resp = mlb_api_get(
            "team_stats",
            {
                "teamId": team_id,
                "stats": "season",
                "group": "hitting"
            },
            season=season
        )

        splits = resp.get("stats", [])
        if not splits:
            raise ValueError("No season stats")

        stat = splits[0]["splits"][0]["stat"]

        return {
            "available": True,
            "gamesPlayed": safe_int(stat.get("gamesPlayed")),
            "runsPerGame": safe_float(stat.get("runsPerGame")),
            "ops": safe_float(stat.get("ops")),
            "woba": safe_float(stat.get("woba")),
            "iso": safe_float(stat.get("iso")),
            "bbPercent": safe_float(stat.get("baseOnBalls")),
            "kPercent": safe_float(stat.get("strikeOuts")),
            "babip": safe_float(stat.get("babip")),
            "source": "statsapi"
        }

    except Exception:
        return {
            "available": False,
            "gamesPlayed": None,
            "runsPerGame": None,
            "ops": None,
            "woba": None,
            "iso": None,
            "bbPercent": None,
            "kPercent": None,
            "babip": None,
            "source": "missing"
        }


# =========================
# SPLITS VS HAND (R / L)
# =========================

def get_team_split_stats(team_id: int, hand: str, season: int = 2024) -> Dict[str, Any]:
    """
    Stats ofensivos vs pitchers derechos o zurdos.
    """
    split_key = "vsRhp" if hand.upper() == "R" else "vsLhp"

    try:
        resp = mlb_api_get(
            "team_stats",
            {
                "teamId": team_id,
                "stats": "season",
                "group": "hitting",
                "split": split_key
            },
            season=season
        )

        splits = resp.get("stats", [])
        if not splits:
            raise ValueError("No split stats")

        stat = splits[0]["splits"][0]["stat"]

        return {
            "available": True,
            "ops": safe_float(stat.get("ops")),
            "runsPerGame": safe_float(stat.get("runsPerGame")),
            "games": safe_int(stat.get("gamesPlayed")),
            "source": "statsapi"
        }

    except Exception:
        return {
            "available": False,
            "ops": None,
            "runsPerGame": None,
            "games": None,
            "source": "missing"
        }


# =========================
# RECENT FORM (LAST X GAMES)
# =========================

def get_team_last_x_games(team_id: int, window: int, season: int = 2024) -> Dict[str, Any]:
    """
    Forma reciente del equipo (last X games).
    """
    try:
        resp = mlb_api_get(
            "team_stats",
            {
                "teamId": team_id,
                "stats": f"last{window}Games",
                "group": "hitting"
            },
            season=season
        )

        splits = resp.get("stats", [])
        if not splits:
            raise ValueError("No recent stats")

        stat = splits[0]["splits"][0]["stat"]
        games = safe_int(stat.get("gamesPlayed"))

        confidence = 0.6
        if games is not None:
            if games < window * 0.6:
                confidence = 0.4
            elif games >= window:
                confidence = 0.7

        return {
            "available": True,
            "window": window,
            "runsPerGame": safe_float(stat.get("runsPerGame")),
            "ops": safe_float(stat.get("ops")),
            "games": games,
            "confidence": confidence,
            "source": "statsapi"
        }

    except Exception:
        return {
            "available": False,
            "window": window,
            "runsPerGame": None,
            "ops": None,
            "games": None,
            "confidence": 0.3,
            "source": "missing"
        }