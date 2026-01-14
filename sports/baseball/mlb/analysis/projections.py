from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, asdict

from sports.baseball.mlb.constants.mlb_constants import (
    LEAGUE_RPG, LEAGUE_ERA, LEAGUE_OPS, LEAGUE_WRC_PLUS,
    WEATHER_TEMP_NEUTRAL,  # disponible para futuros ajustes
)

# -------------------------
# Pesos / hiperparámetros
# -------------------------
ALPHA_PITCHER_SUPPRESSION = 1.00    # cuánto pesa el pitcher en reducir/aumentar carreras
BETA_DEFENSE = 0.25                 # qué tanto la defensa afecta la proyección
GAMMA_H2H = 0.05                    # tamaño máximo del micro-ajuste H2H (carreras)
WEIGHT_SPLIT = 0.60                 # peso del split vs mano sobre la métrica ofensiva base
WEIGHT_RECENT_30 = 0.20             # cuánto pesa el form 30 días en runs/OPS
MIN_RUNS = 0.1                      # límite mínimo de carreras proyectadas

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

    def to_dict(self):
        return asdict(self)

# -------------------------
# Helpers
# -------------------------

def _offense_base(off: Dict[str, Any]) -> float:
    """
    Base ofensiva: usamos runs_per_game_adj. Si no está, fallback a runs_per_game.
    """
    return float(off.get('runs_per_game_adj') or off.get('runsPerGame') or LEAGUE_RPG)

def _offense_split_factor(off: Dict[str, Any], pitcher_throws: str) -> float:
    """
    Factor por split vs mano. Si no hay splits, 1.0.
    Usamos OPS vs mano / OPS liga con un peso.
    """
    ops_vs = off.get('ops_vs_r') if pitcher_throws == 'R' else off.get('ops_vs_l')
    ops_adj = off.get('ops_adj') or off.get('ops') or LEAGUE_OPS

    if ops_vs is None or ops_adj is None or ops_adj <= 0:
        return 1.0

    # Forzar límites de seguridad
    ops_vs = max(0.3, min(ops_vs, 1.5))
    ops_adj = max(0.3, min(ops_adj, 1.5))

    split_idx = (ops_vs / LEAGUE_OPS)
    team_idx = (ops_adj / LEAGUE_OPS)
    combined = WEIGHT_SPLIT * split_idx + (1 - WEIGHT_SPLIT) * team_idx
    return max(combined, 0.5)

def _offense_recent_factor(off: Dict[str, Any]) -> float:
    """
    Factor por forma reciente (runs_last_30 u ops_last_30). Si no hay, 1.0.
    """
    runs30 = off.get('runs_last_30')
    if runs30 is None:
        return 1.0

    base_rpg = _offense_base(off)
    if base_rpg <= 0:
        return 1.0

    ratio = runs30 / max(base_rpg, 0.1)
    return max(0.5, 1 + WEIGHT_RECENT_30 * (ratio - 1))

def _pitcher_factor(pit: Dict[str, Any]) -> float:
    """
    Si proyectamos carreras CONTRA este pitcher:
    factor < 1 reduce carreras (pitcher bueno), >1 las aumenta (pitcher malo).
    """
    era_adj = pit.get('era_adj') or pit.get('ERA') or LEAGUE_ERA
    era_adj = max(0.5, min(float(era_adj), 10.0))  # límites seguros

    factor = (era_adj / LEAGUE_ERA) ** ALPHA_PITCHER_SUPPRESSION
    return max(0.5, min(1.8, factor))

def _defense_factor(defteam: Dict[str, Any]) -> float:
    """
    Penalización/bonificación por defensa.
    """
    errors_pg_adj = defteam.get('errors_pg_adj') or defteam.get('errors_per_game')
    if errors_pg_adj is None:
        return 1.0
    diff = (errors_pg_adj - 0.55)  # media estándar MLB ~0.55
    return max(0.7, min(1.3, 1.0 + BETA_DEFENSE * diff))

def _context_adjustments(ctx: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    Devuelve (park_factor, climate_runs_adj, b2b_penalty)
    """
    pf = float(ctx.get('park_factor', 1.0))
    clima_adj = float(ctx.get('impacto_clima_carreras', 0.0))
    b2b_pen = float(ctx.get('penalizaciones_carreras', 0.0))
    return pf, clima_adj, b2b_pen

def _h2h_adjust(h2h: Dict[str, Any], for_home: bool) -> float:
    """
    Ajuste H2H (margen en carreras).
    """
    if not h2h or h2h.get('confidence', 0) <= 0:
        return 0.0
    wr = h2h.get('winrate_weighted', 0.5)
    conf = h2h.get('confidence', 0.3)
    adj = (wr - 0.5) * GAMMA_H2H * conf
    return adj if for_home else -adj

def _combine_confidences(off=None, pit=None, defense=None, context=None, h2h=None) -> float:
    """
    Combina confidencias con pesos relativos.
    """
    vals = []
    if off: vals.append(off * 0.4)
    if pit: vals.append(pit * 0.4)
    if defense: vals.append(defense * 0.1)
    if context: vals.append(context * 0.05)
    if h2h: vals.append(h2h * 0.05)
    return max(0.1, min(1.0, sum(vals))) if vals else 0.5

# -------------------------
# Core
# -------------------------

def proyectar_equipo(
    offense: Dict[str, Any],
    pitcher_rival: Dict[str, Any],
    defense_rival: Dict[str, Any],
    context_team: Dict[str, Any],
    is_home: bool,
    h2h: Dict[str, Any],
    pitcher_rival_throws: str
) -> ProjectionBreakdown:
    base_rpg = _offense_base(offense)
    of_split = _offense_split_factor(offense, pitcher_rival_throws)
    of_recent = _offense_recent_factor(offense)
    pit_fac = _pitcher_factor(pitcher_rival)
    def_fac = _defense_factor(defense_rival)
    pf, climate_runs, b2b_pen = _context_adjustments(context_team)
    h2h_adj = _h2h_adjust(h2h, for_home=is_home)

    mu = base_rpg
    mu *= of_split
    mu *= of_recent
    mu *= pit_fac
    mu *= def_fac
    mu *= pf
    mu += climate_runs
    mu -= b2b_pen
    mu += h2h_adj
    mu = max(mu, MIN_RUNS)

    conf = _combine_confidences(
        offense.get('confidence'),
        pitcher_rival.get('confidence'),
        defense_rival.get('confidence'),
        context_team.get('confidence'),
        h2h.get('confidence', 0.35) if h2h else None
    )

    return ProjectionBreakdown(
        base_rpg=round(base_rpg, 3),
        offense_split_factor=round(of_split, 3),
        offense_recent_factor=round(of_recent, 3),
        pitcher_factor=round(pit_fac, 3),
        defense_factor=round(def_fac, 3),
        park_factor=round(pf, 3),
        climate_runs_adj=round(climate_runs, 3),
        b2b_penalty=round(b2b_pen, 3),
        h2h_adj=round(h2h_adj, 3),
        final_mu=round(mu, 3),
        confidence=round(conf, 3)
    )

def proyectar_totales(partidos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for p in partidos:
        home_off = p['home_offense']
        away_off = p['away_offense']
        home_def = p.get('home_defense', {})
        away_def = p.get('away_defense', {})
        home_pit = p['home_stats']
        away_pit = p['away_stats']
        home_ctx = p.get('home_context', {})
        away_ctx = p.get('away_context', {})
        h2h = p.get('h2h', {})

        away_pitcher_throws = away_pit.get('throws', 'R')
        home_pitcher_throws = home_pit.get('throws', 'R')

        home_break = proyectar_equipo(
            offense=home_off,
            pitcher_rival=away_pit,
            defense_rival=away_def,
            context_team=home_ctx,
            is_home=True,
            h2h=h2h,
            pitcher_rival_throws=away_pitcher_throws
        )

        away_break = proyectar_equipo(
            offense=away_off,
            pitcher_rival=home_pit,
            defense_rival=home_def,
            context_team=away_ctx,
            is_home=False,
            h2h=h2h,
            pitcher_rival_throws=home_pitcher_throws
        )

        p['proj_home'] = home_break.final_mu
        p['proj_away'] = away_break.final_mu
        p['proj_total'] = round(home_break.final_mu + away_break.final_mu, 3)

        p['projection_home_breakdown'] = home_break.to_dict()
        p['projection_away_breakdown'] = away_break.to_dict()

        p['projection_confidence'] = round((home_break.confidence + away_break.confidence) / 2, 3)

    return partidos
