from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

from sports.baseball.mlb.data_sources.statsapi_client import (
    statsapi_get,
    safe_int,
    safe_float
)

from sports.baseball.mlb.data_sources.team_stats_provider import get_team_id
from sports.baseball.mlb.data_sources.mlb_api_wrapper import mlb_api_get

# =========================
# CONFIG
# =========================
from sports.baseball.mlb.constants.mlb_constants import (
    SEASON,
    RECENT_GAMES,
    LEAGUE_FPCT,
    LEAGUE_ERRORS_PER_GAME,
    EB_GAMES,
    MIN_GAMES_CONFIDENT,
)

# =========================
# DATACLASS
# =========================
@dataclass
class TeamDefenseMetrics:
    team_id: Optional[int]
    team: str
    season: int
    games: int

    errors: int
    errors_per_game: float
    double_plays: int
    fpct: float

    recent_errors: Optional[int]
    recent_games_counted: int
    recent_errors_per_game: Optional[float]

    der: Optional[float]
    der_adj: Optional[float]
    fpct_adj: float
    errors_pg_adj: float

    flags: Dict[str, bool]
    missing_fields: List[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# =========================
# HELPERS
# =========================
def empirical_bayes_adjust(
    value: float,
    n: float,
    league_value: float,
    eb_n: float = EB_GAMES
) -> float:
    return (value * n + league_value * eb_n) / (n + eb_n)


def _fetch_fielding_team_stats(team_id: int, season: int = 2024) -> Dict[str, Any]:
    try:
        resp = mlb_api_get(
            "team_stats",
            {
                "teamId": team_id,
                "group": "fielding",
                "stats": "season"
            },
            season=season
        )
        return resp["stats"][0]["splits"][0]["stat"]
    except Exception:
        return {}


def _fetch_recent_fielding(
    team_id: int,
    season: int,
    limit_games: int
) -> List[Dict[str, Any]]:
    # NOTA: team_game_logs no existe en StatsAPI público
    # Dejamos vacío para evitar errores
    return []

def _calc_der_proxy(_: Dict[str, Any]) -> Optional[float]:
    return None

# =========================
# CORE
# =========================
def _build_team_defense(team: str, season: int = None) -> TeamDefenseMetrics:
    """Construye métricas defensivas."""
    
    if season is None:
        season = SEASON
    
    flags = {
        "no_recent": False,
        "low_sample": False,
        "no_der": True,
        "no_adv_metrics": True
    }
    missing = []

    team_id = get_team_id(team)

    if team_id is None:
        return TeamDefenseMetrics(
            team_id=None,
            team=team,
            season=season,
            games=0,
            errors=int(LEAGUE_ERRORS_PER_GAME * EB_GAMES),
            errors_per_game=LEAGUE_ERRORS_PER_GAME,
            double_plays=0,
            fpct=LEAGUE_FPCT,
            recent_errors=None,
            recent_games_counted=0,
            recent_errors_per_game=None,
            der=None,
            der_adj=None,
            fpct_adj=LEAGUE_FPCT,
            errors_pg_adj=LEAGUE_ERRORS_PER_GAME,
            flags={"no_team_id": True, **flags},
            missing_fields=["all"],
            confidence=0.5
        )

    st = _fetch_fielding_team_stats(team_id, season)
    if not st:
        missing.append("season_fielding")

    errors = safe_int(st.get("errors"), 0)
    dp = safe_int(st.get("doublePlays"), 0)
    fpct = safe_float(st.get("fieldingPercentage"), LEAGUE_FPCT)
    games = safe_int(st.get("games")) or safe_int(st.get("gamesPlayed"), 0)

    errors_pg = errors / games if games > 0 else LEAGUE_ERRORS_PER_GAME

    # Reciente (deshabilitado porque endpoint no existe)
    logs = _fetch_recent_fielding(team_id, season, RECENT_GAMES)
    if not logs:
        flags["no_recent"] = True

    recent_errors = 0
    recent_count = 0
    for g in logs:
        stg = g.get("stat", {})
        recent_errors += safe_int(stg.get("errors"), 0)
        recent_count += 1

    recent_e_pg = (
        recent_errors / recent_count if recent_count > 0 else None
    )

    der = _calc_der_proxy(st)
    if der is None:
        missing.append("der")

    fpct_adj = empirical_bayes_adjust(fpct, games, LEAGUE_FPCT)
    errors_pg_adj = empirical_bayes_adjust(
        errors_pg, games, LEAGUE_ERRORS_PER_GAME
    )

    confidence = 1.0
    if games < MIN_GAMES_CONFIDENT:
        flags["low_sample"] = True
        confidence *= 0.85
    if flags["no_recent"]:
        confidence *= 0.92
    if flags["no_der"]:
        confidence *= 0.97

    confidence = max(min(confidence, 1.0), 0.5)

    return TeamDefenseMetrics(
        team_id=team_id,
        team=team,
        season=season,
        games=games,
        errors=errors,
        errors_per_game=round(errors_pg, 3),
        double_plays=dp,
        fpct=round(fpct, 3),
        recent_errors=recent_errors if not flags["no_recent"] else None,
        recent_games_counted=recent_count,
        recent_errors_per_game=(
            round(recent_e_pg, 3) if recent_e_pg is not None else None
        ),
        der=der,
        der_adj=None,
        fpct_adj=round(fpct_adj, 3),
        errors_pg_adj=round(errors_pg_adj, 3),
        flags=flags,
        missing_fields=missing,
        confidence=round(confidence, 3)
    )

# =========================
# API PÚBLICA
# =========================
def analizar_defensiva(partidos: List[Dict[str, Any]], season: int = None) -> List[Dict[str, Any]]:
    """Analiza defensiva con season específico."""
    
    if season is None:
        from datetime import datetime
        season = datetime.now().year
    
    for p in partidos:
        home = p["home_team"]
        away = p["away_team"]

        home_def = _build_team_defense(home, season).to_dict()
        away_def = _build_team_defense(away, season).to_dict()

        warnings = []
        if home_def["flags"]["low_sample"]:
            warnings.append(f"LOW_SAMPLE_DEF_{home}")
        if away_def["flags"]["low_sample"]:
            warnings.append(f"LOW_SAMPLE_DEF_{away}")
        if home_def["flags"]["no_recent"] or away_def["flags"]["no_recent"]:
            warnings.append("NO_DEF_RECENT")

        p["home_defense"] = home_def
        p["away_defense"] = away_def
        p.setdefault("data_warnings", [])
        p["data_warnings"] += warnings

    return partidos