from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, asdict

from sports.baseball.mlb.constants.mlb_constants import (
    LEAGUE_RPG,
    LEAGUE_ERA,
    LEAGUE_OPS,
)

# =========================
# Hyperparameters
# =========================
ALPHA_PITCHER_SUPPRESSION = 1.00
BETA_DEFENSE = 0.25
GAMMA_H2H = 0.05
WEIGHT_SPLIT = 0.60
WEIGHT_RECENT_30 = 0.20
MIN_RUNS = 0.1

# =========================
# Data Class
# =========================
@dataclass
class ProjectionBreakdown:
    base_rpg: float
    offense_split_factor: float
    offense_recent_factor: float
    pitcher_factor: float
    defense_factor: float
    park_factor: float
    climate_runs_adj: float
    b2b_penalty: float
    h2h_adj: float
    final_mu: float
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# =========================
# Helpers
# =========================
def _safe_float(val, default=0.0) -> float:
    try:
        return float(val)
    except Exception:
        return float(default)

def _offense_base(off: Dict[str, Any]) -> float:
    return _safe_float(
        off.get("runs_per_game_adj")
        or off.get("runs_per_game")
        or LEAGUE_RPG,
        LEAGUE_RPG
    )

def _offense_split_factor(off: Dict[str, Any], pitcher_throws: str) -> float:
    ops_vs = off.get("ops_vs_r") if pitcher_throws == "R" else off.get("ops_vs_l")
    ops_team = off.get("ops_adj") or off.get("ops") or LEAGUE_OPS

    if ops_vs is None:
        return 1.0

    ops_vs = max(0.3, min(_safe_float(ops_vs), 1.5))
    ops_team = max(0.3, min(_safe_float(ops_team), 1.5))

    split_idx = ops_vs / LEAGUE_OPS
    team_idx = ops_team / LEAGUE_OPS

    combined = WEIGHT_SPLIT * split_idx + (1 - WEIGHT_SPLIT) * team_idx
    return max(0.6, min(1.4, combined))

def _offense_recent_factor(off: Dict[str, Any]) -> float:
    runs30 = off.get("runs_last_30")
    if runs30 is None:
        return 1.0

    base = _offense_base(off)
    ratio = _safe_float(runs30) / max(base, 0.1)

    return max(0.7, min(1.3, 1 + WEIGHT_RECENT_30 * (ratio - 1)))

def _pitcher_factor(pit: Dict[str, Any]) -> float:
    era = pit.get("era_adj") or pit.get("ERA") or LEAGUE_ERA
    era = max(0.5, min(_safe_float(era), 10.0))

    factor = (era / LEAGUE_ERA) ** ALPHA_PITCHER_SUPPRESSION
    return max(0.6, min(1.7, factor))

def _defense_factor(defteam: Dict[str, Any]) -> float:
    errors_pg = defteam.get("errors_pg_adj") or defteam.get("errors_per_game")
    if errors_pg is None:
        return 1.0

    diff = _safe_float(errors_pg) - 0.55
    return max(0.8, min(1.2, 1 + BETA_DEFENSE * diff))

def _context_adjustments(ctx: Dict[str, Any]) -> Tuple[float, float, float]:
    return (
        _safe_float(ctx.get("park_factor", 1.0), 1.0),
        _safe_float(ctx.get("impacto_clima_carreras", 0.0)),
        _safe_float(ctx.get("penalizaciones_carreras", 0.0)),
    )

def _h2h_adjust(h2h: Dict[str, Any], for_home: bool) -> float:
    if not h2h or h2h.get("confidence", 0) <= 0:
        return 0.0

    wr = _safe_float(h2h.get("winrate_weighted", 0.5), 0.5)
    conf = _safe_float(h2h.get("confidence", 0.3), 0.3)

    adj = (wr - 0.5) * GAMMA_H2H * conf
    return adj if for_home else -adj

def _combine_confidences(off=None, pit=None, defense=None, context=None, h2h=None) -> float:
    weighted = []

    for val, w in [
        (off, 0.4),
        (pit, 0.4),
        (defense, 0.1),
        (context, 0.05),
        (h2h, 0.05),
    ]:
        if isinstance(val, (int, float)):
            weighted.append(val * w)

    return max(0.2, min(1.0, sum(weighted))) if weighted else 0.5

# =========================
# Core Projection
# =========================
def proyectar_equipo(
    offense: Dict[str, Any],
    pitcher_rival: Dict[str, Any],
    defense_rival: Dict[str, Any],
    context_team: Dict[str, Any],
    is_home: bool,
    h2h: Dict[str, Any],
    pitcher_rival_throws: str,
) -> ProjectionBreakdown:

    base = _offense_base(offense)
    mu = base

    mu *= _offense_split_factor(offense, pitcher_rival_throws)
    mu *= _offense_recent_factor(offense)
    mu *= _pitcher_factor(pitcher_rival)
    mu *= _defense_factor(defense_rival)

    pf, clima, b2b = _context_adjustments(context_team)
    mu *= pf
    mu += clima
    mu -= b2b
    mu += _h2h_adjust(h2h, is_home)

    mu = max(mu, MIN_RUNS)

    conf = _combine_confidences(
        offense.get("confidence"),
        pitcher_rival.get("confidence"),
        defense_rival.get("confidence"),
        context_team.get("confidence"),
        h2h.get("confidence") if h2h else None,
    )

    return ProjectionBreakdown(
        base_rpg=round(base, 3),
        offense_split_factor=round(_offense_split_factor(offense, pitcher_rival_throws), 3),
        offense_recent_factor=round(_offense_recent_factor(offense), 3),
        pitcher_factor=round(_pitcher_factor(pitcher_rival), 3),
        defense_factor=round(_defense_factor(defense_rival), 3),
        park_factor=round(pf, 3),
        climate_runs_adj=round(clima, 3),
        b2b_penalty=round(b2b, 3),
        h2h_adj=round(_h2h_adjust(h2h, is_home), 3),
        final_mu=round(mu, 3),
        confidence=round(conf, 3),
    )

def proyectar_totales(partidos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for p in partidos:
        home = proyectar_equipo(
            p["home_offense"],
            p["away_stats"],
            p.get("away_defense", {}),
            p.get("home_context", {}),
            True,
            p.get("h2h", {}),
            p["away_stats"].get("throws", "R"),
        )

        away = proyectar_equipo(
            p["away_offense"],
            p["home_stats"],
            p.get("home_defense", {}),
            p.get("away_context", {}),
            False,
            p.get("h2h", {}),
            p["home_stats"].get("throws", "R"),
        )

        p["proj_home"] = home.final_mu
        p["proj_away"] = away.final_mu
        p["proj_total"] = round(home.final_mu + away.final_mu, 3)

        p["projection_home_breakdown"] = home.to_dict()
        p["projection_away_breakdown"] = away.to_dict()
        p["projection_confidence"] = round((home.confidence + away.confidence) / 2, 3)

    return partidos
