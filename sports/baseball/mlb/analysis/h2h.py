# sports/baseball/mlb/analysis/h2h.py

"""
Análisis head-to-head (H2H) entre equipos.

NOTA IMPORTANTE:
El endpoint 'team_game_logs' NO existe en la API pública de MLB StatsAPI.
Esta implementación devuelve valores por defecto hasta que se integre
una fuente alternativa de datos H2H (ej: web scraping, API pagada, etc).
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime

from sports.baseball.mlb.data_sources.statsapi_client import safe_int
from statsapi import lookup_team

from core.utils.logger import setup_logger

logger = setup_logger(__name__)


# =========================
# CONFIG
# =========================
CURRENT_SEASON = datetime.now().year
SEASONS_BACK = 3          # actual + 2 anteriores
LIMIT_GAMES = 20
BASE_CONFIDENCE = 0.35

SEASON_DECAY = [1.0, 0.6, 0.4]

# =========================
# DATA CLASS
# =========================
@dataclass
class H2HMetrics:
    seasons_covered: List[int]
    total_games: int

    runs_for_pg: float
    runs_against_pg: float
    winrate: float
    margin_pg: float

    winrate_weighted: float
    margin_pg_weighted: float

    flags: Dict[str, bool]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# =========================
# HELPERS
# =========================
def _get_team_id(name: str) -> Optional[int]:
    try:
        res = lookup_team(name)
        if res:
            return res[0]["id"]
    except Exception:
        pass
    return None


def _fetch_team_logs_vs(
    team_id: int,
    opp_id: int,
    season: int,
    limit: int
) -> List[Dict[str, Any]]:
    """
    Game logs del equipo (team_id) vs rival (opp_id).
    
    NOTA CRÍTICA:
    Este endpoint NO existe en MLB StatsAPI público.
    
    Alternativas para producción:
    1. Web scraping de Baseball Reference
    2. API pagada (Sportradar, etc)
    3. Base de datos propia con histórico
    4. Endpoint diferente de StatsAPI (si existe)
    
    Por ahora devolvemos lista vacía.
    """
    
    logger.debug(
        f"H2H data not available via public API: "
        f"team={team_id} vs opp={opp_id}, season={season}"
    )
    
    return []


# =========================
# CORE
# =========================
def _build_h2h(home: str, away: str, season: int = CURRENT_SEASON) -> H2HMetrics:
    """
    Construye métricas H2H.
    
    IMPORTANTE: Dado que team_game_logs no existe en API pública,
    esta función SIEMPRE devolverá valores por defecto.
    """
    
    flags = {
        "no_data": False,
        "very_low_sample": False
    }

    home_id = _get_team_id(home)
    away_id = _get_team_id(away)

    seasons = [season - i for i in range(SEASONS_BACK)]

    if home_id is None or away_id is None:
        flags["no_data"] = True
        return _default_h2h(seasons, flags, BASE_CONFIDENCE * 0.5)

    # Intentar obtener datos H2H (siempre fallará con API pública)
    runs_for_sum = 0
    runs_against_sum = 0
    wins = 0
    games_ct = 0

    weighted_wins = 0.0
    weighted_games = 0.0
    weighted_margin_sum = 0.0

    for idx, s in enumerate(seasons):
        logs = _fetch_team_logs_vs(home_id, away_id, s, LIMIT_GAMES)
        
        # logs estará vacío siempre con API pública
        for g in logs:
            st = g.get("stat", {})
            rf = safe_int(st.get("runs"), 0)
            ra = safe_int(st.get("opponentRuns"), 0)

            runs_for_sum += rf
            runs_against_sum += ra
            margin = rf - ra

            games_ct += 1

            if rf > ra:
                wins += 1

            weight = SEASON_DECAY[idx] if idx < len(SEASON_DECAY) else SEASON_DECAY[-1]
            weighted_games += weight
            weighted_wins += (1 if rf > ra else 0) * weight
            weighted_margin_sum += margin * weight

    # Si no hay datos (siempre será el caso)
    if games_ct == 0:
        flags["no_data"] = True
        logger.info(f"No H2H data available for {home} vs {away}")
        return _default_h2h(seasons, flags, BASE_CONFIDENCE * 0.5)

    # Este código nunca se ejecutará con API pública
    if games_ct < 5:
        flags["very_low_sample"] = True

    runs_for_pg = runs_for_sum / games_ct
    runs_against_pg = runs_against_sum / games_ct
    winrate = wins / games_ct
    margin_pg = (runs_for_sum - runs_against_sum) / games_ct

    winrate_weighted = (
        weighted_wins / weighted_games if weighted_games > 0 else 0.5
    )
    margin_pg_weighted = (
        weighted_margin_sum / weighted_games if weighted_games > 0 else 0.0
    )

    confidence = BASE_CONFIDENCE
    if flags["very_low_sample"]:
        confidence *= 0.65

    return H2HMetrics(
        seasons_covered=seasons,
        total_games=games_ct,
        runs_for_pg=round(runs_for_pg, 3),
        runs_against_pg=round(runs_against_pg, 3),
        winrate=round(winrate, 3),
        margin_pg=round(margin_pg, 3),
        winrate_weighted=round(winrate_weighted, 3),
        margin_pg_weighted=round(margin_pg_weighted, 3),
        flags=flags,
        confidence=round(confidence, 3)
    )


def _default_h2h(
    seasons: List[int],
    flags: Dict[str, bool],
    confidence: float
) -> H2HMetrics:
    """
    Valores por defecto cuando no hay datos H2H.
    
    Usa promedios neutrales (50/50, 4.5 runs por lado).
    """
    return H2HMetrics(
        seasons_covered=seasons,
        total_games=0,
        runs_for_pg=4.5,
        runs_against_pg=4.5,
        winrate=0.5,
        margin_pg=0.0,
        winrate_weighted=0.5,
        margin_pg_weighted=0.0,
        flags=flags,
        confidence=round(confidence, 3)
    )

# =========================
# API PÚBLICA
# =========================
def analizar_h2h(partidos: List[Dict[str, Any]], season: int = None) -> List[Dict[str, Any]]:
    """
    Analiza head-to-head entre equipos.
    
    Args:
        partidos: Lista de partidos con home_team y away_team
        season: Año base de la temporada (default: año actual)
    
    Returns:
        Partidos con campo 'h2h' agregado
    
    NOTA: Con API pública, siempre devolverá valores por defecto
    debido a que el endpoint de game logs vs equipo específico no existe.
    """
    
    if season is None:
        # Intentar extraer de fecha del primer partido
        if partidos and "date" in partidos[0]:
            season = int(partidos[0]["date"][:4])
        else:
            season = CURRENT_SEASON
    
    for p in partidos:
        home = p["home_team"]
        away = p["away_team"]

        h2h = _build_h2h(home, away, season).to_dict()
        p["h2h"] = h2h

        p.setdefault("data_warnings", [])
        if h2h["flags"]["no_data"]:
            p["data_warnings"].append("NO_H2H_DATA")
        if h2h["flags"]["very_low_sample"]:
            p["data_warnings"].append("H2H_VERY_LOW_SAMPLE")

    return partidos