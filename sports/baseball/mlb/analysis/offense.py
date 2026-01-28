# sports/baseball/mlb/analysis/offense.py
# (Solo mostrar cambios necesarios)

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime

from sports.baseball.mlb.data_sources.team_stats_provider import (
    get_team_id,
    get_team_season_stats,
    get_team_split_stats,
    get_team_last_x_games
)

from sports.baseball.mlb.data_sources.statsapi_client import safe_float

from sports.baseball.mlb.constants.mlb_constants import (
    POST_ALL_STAR_MODE,
    POST_ALL_STAR_SETTINGS
)

# =========================
# CONFIG
# =========================
SEASON = datetime.now().year

LEAGUE_RPG = 4.60
LEAGUE_OPS = 0.715
LEAGUE_WRC_PLUS = 100.0

EB_GAMES = 162
MIN_GAMES_CONFIDENT = 40

# =========================
# DATA CLASS
# =========================
@dataclass
class TeamOffenseMetrics:
    team_id: Optional[int]
    team: str
    season: int
    games: int

    runs_per_game: float
    ops: float
    wrc_plus: float
    woba: Optional[float]
    iso: Optional[float]
    bb_pct: Optional[float]
    k_pct: Optional[float]
    babip: Optional[float]

    ops_vs_r: Optional[float]
    ops_vs_l: Optional[float]
    wrc_plus_vs_r: Optional[float]
    wrc_plus_vs_l: Optional[float]

    runs_last_14: Optional[float]
    runs_last_30: Optional[float]
    ops_last_14: Optional[float]
    ops_last_30: Optional[float]

    runs_per_game_adj: float
    ops_adj: float
    wrc_plus_adj: float

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
    return (value * n + league_value * eb_n) / (n + eb_n) if n else league_value

# =========================
# CORE
# =========================
def _build_offense_metrics(team: str, season: int = None) -> TeamOffenseMetrics:
    """Construye métricas ofensivas."""
    
    if season is None:
        season = SEASON
    
    team_id = get_team_id(team)

    flags = {
        "no_team_id": False,
        "no_splits": False,
        "no_recent": False,
        "low_sample": False,
        "wrc_proxy": True
    }

    missing = []

    if team_id is None:
        flags["no_team_id"] = True
        return TeamOffenseMetrics(
            team_id=None,
            team=team,
            season=season,
            games=0,
            runs_per_game=LEAGUE_RPG,
            ops=LEAGUE_OPS,
            wrc_plus=LEAGUE_WRC_PLUS,
            woba=None,
            iso=None,
            bb_pct=None,
            k_pct=None,
            babip=None,
            ops_vs_r=None,
            ops_vs_l=None,
            wrc_plus_vs_r=None,
            wrc_plus_vs_l=None,
            runs_last_14=None,
            runs_last_30=None,
            ops_last_14=None,
            ops_last_30=None,
            runs_per_game_adj=LEAGUE_RPG,
            ops_adj=LEAGUE_OPS,
            wrc_plus_adj=LEAGUE_WRC_PLUS,
            flags=flags,
            missing_fields=["all"],
            confidence=0.4
        )

    # -------------------------
    # Season (con season param)
    # -------------------------
    st = get_team_season_stats(team_id, season)

    games = int(safe_float(st.get("gamesPlayed"), 0))
    rpg = safe_float(st.get("runsPerGame"), LEAGUE_RPG)
    ops = safe_float(st.get("ops"), LEAGUE_OPS)

    wrc_plus = (ops / LEAGUE_OPS) * 100 if ops else LEAGUE_WRC_PLUS
    missing.append("wrc_plus_proxy")

    woba = safe_float(st.get("woba"))
    iso = safe_float(st.get("iso"))
    bb_pct = safe_float(st.get("bbPercent"))
    k_pct = safe_float(st.get("kPercent"))
    babip = safe_float(st.get("babip"))

    for k, v in [("woba", woba), ("iso", iso), ("babip", babip)]:
        if v is None:
            missing.append(k)

    # -------------------------
    # Splits (con season param)
    # -------------------------
    split_r = get_team_split_stats(team_id, "R", season)
    split_l = get_team_split_stats(team_id, "L", season)

    if not split_r["available"] and not split_l["available"]:
        flags["no_splits"] = True

    ops_vs_r = split_r["ops"] if split_r["available"] else None
    ops_vs_l = split_l["ops"] if split_l["available"] else None

    wrc_plus_vs_r = (ops_vs_r / LEAGUE_OPS * 100) if ops_vs_r else None
    wrc_plus_vs_l = (ops_vs_l / LEAGUE_OPS * 100) if ops_vs_l else None

    # -------------------------
    # Recent (con season param)
    # -------------------------
    r14 = get_team_last_x_games(team_id, 14, season)
    r30 = get_team_last_x_games(team_id, 30, season)

    if not r14["available"] and not r30["available"]:
        flags["no_recent"] = True

    runs_last_14 = r14["runsPerGame"] if r14["available"] else None
    ops_last_14 = r14["ops"] if r14["available"] else None

    runs_last_30 = r30["runsPerGame"] if r30["available"] else None
    ops_last_30 = r30["ops"] if r30["available"] else None

    # -------------------------
    # Adjusted
    # -------------------------
    rpg_adj = empirical_bayes_adjust(rpg, games, LEAGUE_RPG)
    ops_adj = empirical_bayes_adjust(ops, games, LEAGUE_OPS)
    wrc_adj = empirical_bayes_adjust(wrc_plus, games, LEAGUE_WRC_PLUS)

    if POST_ALL_STAR_MODE:
        factor = 1 - POST_ALL_STAR_SETTINGS.get("motivation_penalty", 0.0)
        rpg_adj *= factor
        ops_adj *= factor
        wrc_adj *= factor

    if games < MIN_GAMES_CONFIDENT:
        flags["low_sample"] = True

    # -------------------------
    # Confidence
    # -------------------------
    confidence = 1.0
    if flags["low_sample"]:
        confidence *= 0.8
    if flags["no_recent"]:
        confidence *= 0.9
    if flags["no_splits"]:
        confidence *= 0.92
    if flags["wrc_proxy"]:
        confidence *= 0.9

    confidence = max(min(confidence, 1.0), 0.4)

    return TeamOffenseMetrics(
        team_id=team_id,
        team=team,
        season=season,
        games=games,
        runs_per_game=rpg,
        ops=ops,
        wrc_plus=wrc_plus,
        woba=woba,
        iso=iso,
        bb_pct=bb_pct,
        k_pct=k_pct,
        babip=babip,
        ops_vs_r=ops_vs_r,
        ops_vs_l=ops_vs_l,
        wrc_plus_vs_r=wrc_plus_vs_r,
        wrc_plus_vs_l=wrc_plus_vs_l,
        runs_last_14=runs_last_14,
        runs_last_30=runs_last_30,
        ops_last_14=ops_last_14,
        ops_last_30=ops_last_30,
        runs_per_game_adj=rpg_adj,
        ops_adj=ops_adj,
        wrc_plus_adj=wrc_adj,
        flags=flags,
        missing_fields=missing,
        confidence=round(confidence, 3)
    )

# =========================
# API
# =========================
def analizar_ofensiva(partidos: List[Dict[str, Any]], season: int = None) -> List[Dict[str, Any]]:
    """Analiza ofensiva con season específico."""
    
    if season is None:
        from datetime import datetime
        season = datetime.now().year
    
    for p in partidos:
        home = p["home_team"]
        away = p["away_team"]

        home_off = _build_offense_metrics(home, season).to_dict()
        away_off = _build_offense_metrics(away, season).to_dict()

        warnings = []
        if home_off["flags"]["low_sample"]:
            warnings.append(f"LOW_SAMPLE_OFF_{home}")
        if away_off["flags"]["low_sample"]:
            warnings.append(f"LOW_SAMPLE_OFF_{away}")
        if home_off["flags"]["no_recent"] or away_off["flags"]["no_recent"]:
            warnings.append("NO_RECENT_OFFENSE")
        if home_off["flags"]["no_splits"] or away_off["flags"]["no_splits"]:
            warnings.append("NO_SPLITS_OFFENSE")

        p["home_offense"] = home_off
        p["away_offense"] = away_off
        p.setdefault("data_warnings", [])
        p["data_warnings"].extend(warnings)

    return partidos