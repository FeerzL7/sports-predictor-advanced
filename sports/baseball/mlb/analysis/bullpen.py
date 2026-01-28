# sports/baseball/mlb/analysis/bullpen.py

"""
Análisis de bullpen (relevistas) para innings 7-9.

Estrategia dual:
1. Intenta analizar roster individual de relevistas
2. Fallback a stats agregadas del equipo si no hay roster disponible
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime

from sports.baseball.mlb.data_sources.mlb_api_wrapper import mlb_api_get
from sports.baseball.mlb.data_sources.statsapi_client import safe_float, safe_int
from sports.baseball.mlb.data_sources.team_stats_provider import get_team_id
from sports.baseball.mlb.constants.mlb_constants import (
    LEAGUE_BULLPEN_ERA,
    LEAGUE_K9,
    LEAGUE_BB9,
    MIN_BULLPEN_IP,
    EB_IP,
    RECENT_DAYS_BULLPEN
)

from core.utils.logger import setup_logger

logger = setup_logger(__name__)


# =========================
# DATA CLASS
# =========================

@dataclass
class BullpenMetrics:
    """Métricas del bullpen de un equipo."""
    
    team_id: Optional[int]
    team: str
    season: int
    
    # Métricas principales
    bullpen_era: float
    bullpen_era_adj: float
    bullpen_ip: float
    bullpen_k9: float
    bullpen_bb9: Optional[float]
    bullpen_whip: Optional[float]
    
    # High leverage (si disponible)
    high_leverage_era: Optional[float]
    high_leverage_ip: float
    
    # Forma reciente
    recent_era: Optional[float]
    recent_ip: float
    
    # Flags
    flags: Dict[str, bool]
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =========================
# HELPERS
# =========================

def empirical_bayes_adjust(value: float, ip: float, league_value: float, eb_ip: float = EB_IP) -> float:
    """Ajuste bayesiano empírico."""
    if ip is None or ip <= 0:
        return league_value
    return (value * ip + league_value * eb_ip) / (ip + eb_ip)


def _get_bullpen_stats_team_aggregate(team_id: int, season: int) -> Dict[str, Any]:
    """
    Obtiene stats del bullpen usando agregados del equipo.
    Fallback cuando no hay roster individual disponible.
    """
    
    try:
        resp = mlb_api_get(
            "team_stats",
            {
                "teamId": team_id,
                "group": "pitching",
                "stats": "season"
            },
            season=season
        )
        
        splits = resp.get("stats", [])
        if not splits or not splits[0].get("splits"):
            return {}
        
        stats = splits[0]["splits"][0]["stat"]
        
        # Estimar bullpen como ~40% de los innings del equipo
        total_ip = safe_float(stats.get("inningsPitched"), 0)
        bullpen_ip_est = total_ip * 0.40  # Aproximación
        
        era = safe_float(stats.get("era"), LEAGUE_BULLPEN_ERA)
        k9 = safe_float(stats.get("strikeoutsPer9Inn"), LEAGUE_K9)
        bb9 = safe_float(stats.get("walksPer9Inn"), LEAGUE_BB9)
        whip = safe_float(stats.get("whip"))
        
        return {
            "era": era,
            "ip": bullpen_ip_est,
            "k9": k9,
            "bb9": bb9,
            "whip": whip,
            "using_team_estimate": True
        }
    
    except Exception as e:
        logger.warning(f"Error getting team bullpen stats: {e}")
        return {}


def _get_bullpen_stats_high_leverage(team_id: int, season: int) -> Dict[str, Any]:
    """
    Intenta obtener stats de high leverage situations.
    """
    
    try:
        resp = mlb_api_get(
            "team_stats",
            {
                "teamId": team_id,
                "group": "pitching",
                "stats": "season",
                "sitCodes": "high_lvrg"  # High leverage
            },
            season=season
        )
        
        splits = resp.get("stats", [])
        if not splits or not splits[0].get("splits"):
            return {"available": False}
        
        stats = splits[0]["splits"][0]["stat"]
        
        return {
            "available": True,
            "era": safe_float(stats.get("era")),
            "ip": safe_float(stats.get("inningsPitched"), 0)
        }
    
    except Exception:
        return {"available": False}


def _get_bullpen_stats_recent(team_id: int, season: int, days: int = RECENT_DAYS_BULLPEN) -> Dict[str, Any]:
    """
    Stats recientes del bullpen (últimos N días).
    Usa last7Days o similar.
    """
    
    try:
        resp = mlb_api_get(
            "team_stats",
            {
                "teamId": team_id,
                "group": "pitching",
                "stats": "last7Days"  # StatsAPI tiene last7Days, last14Days, last30Days
            },
            season=season
        )
        
        splits = resp.get("stats", [])
        if not splits or not splits[0].get("splits"):
            return {"available": False}
        
        stats = splits[0]["splits"][0]["stat"]
        
        # Estimar bullpen como 40% del total reciente
        total_ip = safe_float(stats.get("inningsPitched"), 0)
        bullpen_ip_est = total_ip * 0.40
        
        return {
            "available": True,
            "era": safe_float(stats.get("era")),
            "ip": bullpen_ip_est
        }
    
    except Exception:
        return {"available": False}


# =========================
# CORE
# =========================

def _build_bullpen_metrics(team: str, season: int = None) -> BullpenMetrics:
    """
    Construye métricas de bullpen para un equipo.
    
    Estrategia:
    1. Intenta obtener stats agregadas del equipo
    2. Ajusta por empirical Bayes
    3. Busca high leverage situations
    4. Busca forma reciente
    """
    
    if season is None:
        season = datetime.now().year
    
    team_id = get_team_id(team)
    
    flags = {
        "using_team_estimate": False,
        "no_high_leverage": False,
        "no_recent": False,
        "low_sample": False
    }
    
    if team_id is None:
        logger.warning(f"No team_id found for {team}")
        return _default_bullpen_metrics(team, season, flags)
    
    # 1. Stats agregadas del equipo (fallback principal)
    team_stats = _get_bullpen_stats_team_aggregate(team_id, season)
    
    if not team_stats:
        logger.warning(f"No bullpen stats for {team}")
        return _default_bullpen_metrics(team, season, flags)
    
    era = team_stats.get("era", LEAGUE_BULLPEN_ERA)
    ip = team_stats.get("ip", 0)
    k9 = team_stats.get("k9", LEAGUE_K9)
    bb9 = team_stats.get("bb9")
    whip = team_stats.get("whip")
    flags["using_team_estimate"] = team_stats.get("using_team_estimate", False)
    
    # 2. High leverage situations
    hl_stats = _get_bullpen_stats_high_leverage(team_id, season)
    
    if hl_stats.get("available"):
        hl_era = hl_stats.get("era")
        hl_ip = hl_stats.get("ip", 0)
    else:
        hl_era = None
        hl_ip = 0
        flags["no_high_leverage"] = True
    
    # 3. Recent form
    recent_stats = _get_bullpen_stats_recent(team_id, season)
    
    if recent_stats.get("available"):
        recent_era = recent_stats.get("era")
        recent_ip = recent_stats.get("ip", 0)
    else:
        recent_era = None
        recent_ip = 0
        flags["no_recent"] = True
    
    # 4. Ajuste bayesiano
    era_adj = empirical_bayes_adjust(era, ip, LEAGUE_BULLPEN_ERA, EB_IP)
    
    # 5. Low sample flag
    if ip < MIN_BULLPEN_IP:
        flags["low_sample"] = True
    
    # 6. Confidence
    confidence = 1.0
    
    if flags["using_team_estimate"]:
        confidence *= 0.85  # Menos confianza en estimaciones
    
    if flags["low_sample"]:
        confidence *= 0.80
    
    if flags["no_high_leverage"]:
        confidence *= 0.95
    
    if flags["no_recent"]:
        confidence *= 0.92
    
    confidence = max(min(confidence, 1.0), 0.30)
    
    return BullpenMetrics(
        team_id=team_id,
        team=team,
        season=season,
        bullpen_era=round(era, 2),
        bullpen_era_adj=round(era_adj, 2),
        bullpen_ip=round(ip, 1),
        bullpen_k9=round(k9, 2),
        bullpen_bb9=round(bb9, 2) if bb9 else None,
        bullpen_whip=round(whip, 2) if whip else None,
        high_leverage_era=round(hl_era, 2) if hl_era else None,
        high_leverage_ip=round(hl_ip, 1),
        recent_era=round(recent_era, 2) if recent_era else None,
        recent_ip=round(recent_ip, 1),
        flags=flags,
        confidence=round(confidence, 3)
    )


def _default_bullpen_metrics(team: str, season: int, flags: Dict[str, bool]) -> BullpenMetrics:
    """Métricas por defecto cuando no hay datos."""
    
    flags["using_team_estimate"] = True
    
    return BullpenMetrics(
        team_id=None,
        team=team,
        season=season,
        bullpen_era=LEAGUE_BULLPEN_ERA,
        bullpen_era_adj=LEAGUE_BULLPEN_ERA,
        bullpen_ip=0.0,
        bullpen_k9=LEAGUE_K9,
        bullpen_bb9=LEAGUE_BB9,
        bullpen_whip=None,
        high_leverage_era=None,
        high_leverage_ip=0.0,
        recent_era=None,
        recent_ip=0.0,
        flags=flags,
        confidence=0.30
    )


# =========================
# API PÚBLICA
# =========================

def analizar_bullpens(partidos: List[Dict[str, Any]], season: int = None) -> List[Dict[str, Any]]:
    """
    Analiza bullpens de todos los equipos en los partidos.
    
    Args:
        partidos: Lista de partidos con home_team y away_team
        season: Año de la temporada (default: extraer de fecha o año actual)
    
    Returns:
        Partidos con home_bullpen y away_bullpen agregados
    """
    
    if season is None:
        # Intentar extraer de la fecha del primer partido
        if partidos and "date" in partidos[0]:
            season = int(partidos[0]["date"][:4])
        else:
            season = datetime.now().year
    
    for p in partidos:
        home = p["home_team"]
        away = p["away_team"]

        home_bp = _build_bullpen_metrics(home, season).to_dict()
        away_bp = _build_bullpen_metrics(away, season).to_dict()

        p["home_bullpen"] = home_bp
        p["away_bullpen"] = away_bp

        # Warnings
        if home_bp["flags"]["using_team_estimate"]:
            p.setdefault("data_warnings", []).append(f"BULLPEN_TEAM_ESTIMATE_{home}")
        if away_bp["flags"]["using_team_estimate"]:
            p.setdefault("data_warnings", []).append(f"BULLPEN_TEAM_ESTIMATE_{away}")

    return partidos