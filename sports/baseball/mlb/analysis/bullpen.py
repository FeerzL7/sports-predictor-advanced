# sports/baseball/mlb/analysis/bullpen.py

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from sports.baseball.mlb.data_sources.statsapi_client import (
    statsapi_get,
    safe_int,
    safe_float
)
from sports.baseball.mlb.data_sources.team_stats_provider import get_team_id
from sports.baseball.mlb.constants.mlb_constants import (
    LEAGUE_ERA,
    LEAGUE_K9,
    SEASON,
    EB_IP
)

# =========================
# CONFIG
# =========================
MIN_BULLPEN_IP = 30.0
RECENT_DAYS_BULLPEN = 7
LEAGUE_BULLPEN_ERA = 4.20

# =========================
# DATA CLASS
# =========================
@dataclass
class BullpenMetrics:
    team_id: Optional[int]
    team: str
    season: int
    
    bullpen_era: float
    bullpen_whip: float
    bullpen_k9: float
    bullpen_bb9: Optional[float]
    
    high_leverage_era: Optional[float]
    
    recent_era_7d: Optional[float]
    recent_ip_7d: float
    
    total_innings_pitched: float
    num_relievers: int
    
    bullpen_era_adj: float
    
    confidence: float
    flags: Dict[str, bool]
    missing_fields: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# =========================
# HELPERS
# =========================
def empirical_bayes_adjust(
    value: float,
    ip: float,
    league_value: float,
    eb_ip: float = EB_IP
) -> float:
    if ip <= 0:
        return league_value
    return (value * ip + league_value * eb_ip) / (ip + eb_ip)


def _get_available_season(team_id: int) -> int:
    """
    Determina qué temporada tiene datos disponibles.
    Intenta: año actual → año anterior → 2025
    """
    current_year = datetime.now().year
    
    for year in [current_year, current_year - 1, 2025]:
        try:
            # Test si hay datos de pitching para este año
            resp = statsapi_get(
                "team_stats",
                {
                    "teamId": team_id,
                    "stats": "season",
                    "group": "pitching",
                    "season": year
                }
            )
            
            if resp.get("stats"):
                print(f"[DEBUG] Usando temporada: {year}")
                return year
        
        except Exception:
            continue
    
    # Default a año actual si todo falla
    return current_year


def _fetch_team_pitching_stats_aggregated(
    team_id: int,
    season: int
) -> Dict[str, Any]:
    """
    MÉTODO ALTERNATIVO: En vez de buscar roster individual,
    obtiene stats AGREGADAS del bullpen del equipo directamente.
    
    Esto es más confiable en off-season.
    """
    try:
        # StatsAPI tiene stats de bullpen como split
        resp = statsapi_get(
            "team_stats",
            {
                "teamId": team_id,
                "stats": "season",
                "group": "pitching",
                "season": season
            }
        )
        
        stats = resp.get("stats", [])
        if not stats:
            return {}
        
        splits = stats[0].get("splits", [])
        if not splits:
            return {}
        
        # Stats del equipo completo (starters + relievers)
        team_stat = splits[0].get("stat", {})
        
        # Extraer métricas
        return {
            "era": safe_float(team_stat.get("era")),
            "whip": safe_float(team_stat.get("whip")),
            "k9": safe_float(team_stat.get("strikeoutsPer9Inn")),
            "bb9": safe_float(team_stat.get("walksPer9Inn")),
            "ip": safe_float(team_stat.get("inningsPitched")),
        }
    
    except Exception as e:
        print(f"[ERROR] _fetch_team_pitching_stats_aggregated: {e}")
        return {}


def _estimate_bullpen_from_team_stats(
    team_stats: Dict[str, Any]
) -> Dict[str, float]:
    """
    Estima stats de bullpen a partir de stats del equipo completo.
    
    Asumimos:
    - Bullpen lanza ~40% de los innings
    - Bullpen ERA típicamente ~5% mejor que team ERA
    """
    team_era = team_stats.get("era", LEAGUE_BULLPEN_ERA)
    team_whip = team_stats.get("whip", 1.30)
    team_k9 = team_stats.get("k9", LEAGUE_K9)
    team_bb9 = team_stats.get("bb9")
    team_ip = team_stats.get("ip", 0.0)
    
    # Estimación conservadora
    bullpen_era = team_era * 0.98  # Bullpens ligeramente mejor que team
    bullpen_ip = team_ip * 0.40     # ~40% de innings
    
    return {
        "era": round(bullpen_era, 2),
        "whip": round(team_whip, 3),
        "k9": round(team_k9, 2),
        "bb9": round(team_bb9, 2) if team_bb9 else None,
        "total_ip": round(bullpen_ip, 1)
    }


def _get_high_leverage_era(team_id: int, season: int) -> Optional[float]:
    """
    Intenta obtener ERA en situaciones de high leverage.
    """
    try:
        resp = statsapi_get(
            "team_stats",
            {
                "teamId": team_id,
                "stats": "season",
                "group": "pitching",
                "split": "highLeverage",
                "season": season
            }
        )
        
        stats = resp.get("stats", [])
        if not stats:
            return None
        
        splits = stats[0].get("splits", [])
        if not splits:
            return None
        
        stat = splits[0].get("stat", {})
        return safe_float(stat.get("era"))
    
    except Exception:
        return None


# =========================
# CORE
# =========================
def build_bullpen_metrics(team: str) -> BullpenMetrics:
    """
    Construye métricas del bullpen.
    ESTRATEGIA DUAL:
    1. Intenta roster individual (ideal)
    2. Fallback a stats agregadas del equipo (off-season)
    """
    team_id = get_team_id(team)
    
    flags = {
        "no_team_id": False,
        "no_bullpen_data": False,
        "low_sample": False,
        "no_high_leverage": True,
        "no_recent": True,
        "using_team_estimate": False
    }
    
    missing = []
    
    if team_id is None:
        flags["no_team_id"] = True
        return BullpenMetrics(
            team_id=None,
            team=team,
            season=SEASON,
            bullpen_era=LEAGUE_BULLPEN_ERA,
            bullpen_whip=1.30,
            bullpen_k9=LEAGUE_K9,
            bullpen_bb9=None,
            high_leverage_era=None,
            recent_era_7d=None,
            recent_ip_7d=0.0,
            total_innings_pitched=0.0,
            num_relievers=0,
            bullpen_era_adj=LEAGUE_BULLPEN_ERA,
            confidence=0.50,
            flags=flags,
            missing_fields=["all"]
        )
    
    # Determinar temporada con datos disponibles
    working_season = _get_available_season(team_id)
    
    print(f"[DEBUG] Analizando bullpen de {team} (season {working_season})")
    
    # MÉTODO 1: Stats agregadas del equipo (más confiable en off-season)
    team_stats = _fetch_team_pitching_stats_aggregated(team_id, working_season)
    
    if not team_stats:
        flags["no_bullpen_data"] = True
        missing.append("team_stats")
        
        return BullpenMetrics(
            team_id=team_id,
            team=team,
            season=working_season,
            bullpen_era=LEAGUE_BULLPEN_ERA,
            bullpen_whip=1.30,
            bullpen_k9=LEAGUE_K9,
            bullpen_bb9=None,
            high_leverage_era=None,
            recent_era_7d=None,
            recent_ip_7d=0.0,
            total_innings_pitched=0.0,
            num_relievers=0,
            bullpen_era_adj=LEAGUE_BULLPEN_ERA,
            confidence=0.50,
            flags=flags,
            missing_fields=missing
        )
    
    # Estimar bullpen a partir de team stats
    bullpen_est = _estimate_bullpen_from_team_stats(team_stats)
    flags["using_team_estimate"] = True
    
    bullpen_era = bullpen_est["era"]
    bullpen_whip = bullpen_est["whip"]
    bullpen_k9 = bullpen_est["k9"]
    bullpen_bb9 = bullpen_est["bb9"]
    total_ip = bullpen_est["total_ip"]
    
    print(f"[DEBUG] Bullpen estimado - ERA: {bullpen_era}, IP: {total_ip}")
    
    # High leverage ERA
    high_leverage_era = _get_high_leverage_era(team_id, working_season)
    
    if high_leverage_era is None:
        missing.append("high_leverage_era")
    else:
        flags["no_high_leverage"] = False
    
    # Forma reciente (skip en off-season)
    recent_era_7d = None
    recent_ip_7d = 0.0
    
    # Empirical Bayes
    bullpen_era_adj = empirical_bayes_adjust(
        bullpen_era,
        total_ip,
        LEAGUE_BULLPEN_ERA,
        EB_IP
    )
    
    # Flags
    if total_ip < MIN_BULLPEN_IP:
        flags["low_sample"] = True
    
    # Confidence
    confidence = 1.0
    
    if flags["no_bullpen_data"]:
        confidence *= 0.5
    if flags["using_team_estimate"]:
        confidence *= 0.85  # Penalización por usar estimación
    if flags["low_sample"]:
        confidence *= 0.80
    if flags["no_high_leverage"]:
        confidence *= 0.95
    
    confidence = max(min(confidence, 1.0), 0.50)
    
    return BullpenMetrics(
        team_id=team_id,
        team=team,
        season=working_season,
        bullpen_era=bullpen_era,
        bullpen_whip=bullpen_whip,
        bullpen_k9=bullpen_k9,
        bullpen_bb9=bullpen_bb9,
        high_leverage_era=high_leverage_era,
        recent_era_7d=recent_era_7d,
        recent_ip_7d=recent_ip_7d,
        total_innings_pitched=total_ip,
        num_relievers=0,  # No podemos contar relievers individuales con este método
        bullpen_era_adj=round(bullpen_era_adj, 2),
        confidence=round(confidence, 3),
        flags=flags,
        missing_fields=missing
    )


# =========================
# API PÚBLICA
# =========================
def analizar_bullpens(partidos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Inyecta análisis de bullpen en cada partido.
    """
    for p in partidos:
        home_team = p.get("home_team")
        away_team = p.get("away_team")
        
        home_bullpen = build_bullpen_metrics(home_team).to_dict()
        away_bullpen = build_bullpen_metrics(away_team).to_dict()
        
        p["home_bullpen"] = home_bullpen
        p["away_bullpen"] = away_bullpen
        
        warnings = p.get("data_warnings", [])
        
        if home_bullpen["flags"]["no_bullpen_data"]:
            warnings.append(f"NO_BULLPEN_DATA_{home_team}")
        if away_bullpen["flags"]["no_bullpen_data"]:
            warnings.append(f"NO_BULLPEN_DATA_{away_team}")
        
        if home_bullpen["flags"]["low_sample"]:
            warnings.append(f"LOW_BULLPEN_SAMPLE_{home_team}")
        if away_bullpen["flags"]["low_sample"]:
            warnings.append(f"LOW_BULLPEN_SAMPLE_{away_team}")
        
        p["data_warnings"] = warnings
    
    return partidos