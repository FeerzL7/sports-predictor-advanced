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
MIN_BULLPEN_IP = 30.0       # IP mínimo del bullpen para confianza alta
RECENT_DAYS_BULLPEN = 7     # forma reciente del bullpen
LEAGUE_BULLPEN_ERA = 4.20   # bullpens típicamente tienen ERA ~0.1 menor que starters

# =========================
# DATA CLASS
# =========================
@dataclass
class BullpenMetrics:
    team_id: Optional[int]
    team: str
    season: int
    
    # Stats principales
    bullpen_era: float
    bullpen_whip: float
    bullpen_k9: float
    bullpen_bb9: Optional[float]
    
    # High leverage (innings 7-9)
    high_leverage_era: Optional[float]
    
    # Forma reciente
    recent_era_7d: Optional[float]
    recent_ip_7d: float
    
    # Volumen
    total_innings_pitched: float
    num_relievers: int
    
    # Ajustadas
    bullpen_era_adj: float
    
    # Confianza y flags
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
    """Ajuste Bayesiano empírico para ERA del bullpen."""
    if ip <= 0:
        return league_value
    return (value * ip + league_value * eb_ip) / (ip + eb_ip)


def _fetch_team_pitching_roster(team_id: int, season: int) -> List[Dict[str, Any]]:
    """
    Obtiene el roster de pitchers del equipo.
    Retorna lista de pitchers con sus stats básicas.
    """
    try:
        resp = statsapi_get(
            "team_roster",
            {
                "teamId": team_id,
                "season": season
            }
        )
        
        roster = resp.get("roster", [])
        pitchers = []
        
        for player in roster:
            position = player.get("position", {}).get("abbreviation", "")
            if position == "P":  # Solo pitchers
                pitchers.append({
                    "id": player.get("person", {}).get("id"),
                    "name": player.get("person", {}).get("fullName"),
                })
        
        return pitchers
    
    except Exception:
        return []


def _get_pitcher_season_stats(player_id: int, season: int) -> Dict[str, Any]:
    """
    Stats de temporada de un pitcher individual.
    Retorna dict con stats o vacío si falla.
    """
    try:
        resp = statsapi_get(
            "people_stats",
            {
                "personId": player_id,
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
        
        return splits[0].get("stat", {})
    
    except Exception:
        return {}


def _is_reliever(pitcher_stats: Dict[str, Any]) -> bool:
    """
    Determina si un pitcher es reliever.
    Criterio: GS = 0 o ratio GS/G < 0.3
    """
    gs = safe_int(pitcher_stats.get("gamesStarted"), 0)
    g = safe_int(pitcher_stats.get("gamesPlayed"), 0)
    
    if g == 0:
        return False
    
    # Es reliever si nunca abrió o abre <30% del tiempo
    return gs == 0 or (gs / g) < 0.3


def _calc_weighted_bullpen_era(relievers_stats: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calcula ERA ponderado del bullpen por innings pitched.
    Retorna dict con ERA, WHIP, K/9, BB/9, total IP.
    """
    total_ip = 0.0
    total_er = 0.0
    total_hits = 0.0
    total_bb = 0.0
    total_so = 0.0
    
    for stat in relievers_stats:
        ip = safe_float(stat.get("inningsPitched"), 0.0)
        er = safe_float(stat.get("earnedRuns"), 0.0)
        hits = safe_float(stat.get("hits"), 0.0)
        bb = safe_float(stat.get("baseOnBalls"), 0.0)
        so = safe_float(stat.get("strikeOuts"), 0.0)
        
        total_ip += ip
        total_er += er
        total_hits += hits
        total_bb += bb
        total_so += so
    
    if total_ip == 0:
        return {
            "era": LEAGUE_BULLPEN_ERA,
            "whip": 1.30,
            "k9": LEAGUE_K9,
            "bb9": None,
            "total_ip": 0.0
        }
    
    era = (total_er * 9) / total_ip
    whip = (total_hits + total_bb) / total_ip
    k9 = (total_so * 9) / total_ip
    bb9 = (total_bb * 9) / total_ip if total_bb > 0 else None
    
    return {
        "era": round(era, 2),
        "whip": round(whip, 3),
        "k9": round(k9, 2),
        "bb9": round(bb9, 2) if bb9 else None,
        "total_ip": round(total_ip, 1)
    }


def _get_high_leverage_era(team_id: int, season: int) -> Optional[float]:
    """
    Intenta obtener ERA en situaciones de high leverage.
    Esto es más difícil de conseguir de StatsAPI, así que puede retornar None.
    """
    try:
        # StatsAPI tiene splits por "highLeverage" pero no siempre disponible
        resp = statsapi_get(
            "team_stats",
            {
                "teamId": team_id,
                "stats": "season",
                "group": "pitching",
                "split": "highLeverage"
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


def _get_recent_bullpen_era(
    relievers: List[Dict[str, Any]],
    season: int,
    days: int
) -> Dict[str, float]:
    """
    Calcula ERA del bullpen en los últimos N días.
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    
    total_ip = 0.0
    total_er = 0.0
    
    for reliever in relievers:
        player_id = reliever.get("id")
        if not player_id:
            continue
        
        try:
            # Game logs del pitcher
            resp = statsapi_get(
                "people_stats",
                {
                    "personId": player_id,
                    "stats": "gameLog",
                    "group": "pitching",
                    "season": season
                }
            )
            
            stats = resp.get("stats", [])
            if not stats:
                continue
            
            splits = stats[0].get("splits", [])
            
            for game in splits:
                game_date_str = game.get("date", "")
                try:
                    game_date = datetime.strptime(game_date_str, "%Y-%m-%d")
                except Exception:
                    continue
                
                if game_date < cutoff_date:
                    continue
                
                stat = game.get("stat", {})
                ip = safe_float(stat.get("inningsPitched"), 0.0)
                er = safe_float(stat.get("earnedRuns"), 0.0)
                
                total_ip += ip
                total_er += er
        
        except Exception:
            continue
    
    if total_ip == 0:
        return {"era": None, "ip": 0.0}
    
    era = (total_er * 9) / total_ip
    return {"era": round(era, 2), "ip": round(total_ip, 1)}


# =========================
# CORE
# =========================
def build_bullpen_metrics(team: str) -> BullpenMetrics:
    """
    Construye métricas completas del bullpen de un equipo.
    """
    team_id = get_team_id(team)
    
    flags = {
        "no_team_id": False,
        "no_bullpen_data": False,
        "low_sample": False,
        "no_high_leverage": True,
        "no_recent": False
    }
    
    missing = []
    
    # Si no hay team_id, retornar defaults
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
    
    # 1. Obtener roster de pitchers
    pitchers = _fetch_team_pitching_roster(team_id, SEASON)
    
    if not pitchers:
        flags["no_bullpen_data"] = True
        missing.append("roster")
    
    # 2. Filtrar relievers y obtener sus stats
    relievers = []
    relievers_stats = []
    
    for pitcher in pitchers:
        pitcher_id = pitcher.get("id")
        if not pitcher_id:
            continue
        
        stats = _get_pitcher_season_stats(pitcher_id, SEASON)
        
        if not stats:
            continue
        
        if _is_reliever(stats):
            relievers.append(pitcher)
            relievers_stats.append(stats)
    
    # 3. Calcular stats agregados del bullpen
    bullpen_agg = _calc_weighted_bullpen_era(relievers_stats)
    
    bullpen_era = bullpen_agg["era"]
    bullpen_whip = bullpen_agg["whip"]
    bullpen_k9 = bullpen_agg["k9"]
    bullpen_bb9 = bullpen_agg["bb9"]
    total_ip = bullpen_agg["total_ip"]
    
    # 4. High leverage ERA (opcional)
    high_leverage_era = _get_high_leverage_era(team_id, SEASON)
    
    if high_leverage_era is None:
        missing.append("high_leverage_era")
    else:
        flags["no_high_leverage"] = False
    
    # 5. Forma reciente (últimos 7 días)
    recent = _get_recent_bullpen_era(relievers, SEASON, RECENT_DAYS_BULLPEN)
    recent_era_7d = recent["era"]
    recent_ip_7d = recent["ip"]
    
    if recent_era_7d is None:
        flags["no_recent"] = True
        missing.append("recent_era")
    
    # 6. Ajuste Empirical Bayes
    bullpen_era_adj = empirical_bayes_adjust(
        bullpen_era,
        total_ip,
        LEAGUE_BULLPEN_ERA,
        EB_IP
    )
    
    # 7. Flags de calidad
    if total_ip < MIN_BULLPEN_IP:
        flags["low_sample"] = True
    
    # 8. Confidence
    confidence = 1.0
    
    if flags["no_bullpen_data"]:
        confidence *= 0.5
    if flags["low_sample"]:
        confidence *= 0.75
    if flags["no_recent"]:
        confidence *= 0.90
    if flags["no_high_leverage"]:
        confidence *= 0.95
    
    confidence = max(min(confidence, 1.0), 0.50)
    
    return BullpenMetrics(
        team_id=team_id,
        team=team,
        season=SEASON,
        bullpen_era=bullpen_era,
        bullpen_whip=bullpen_whip,
        bullpen_k9=bullpen_k9,
        bullpen_bb9=bullpen_bb9,
        high_leverage_era=high_leverage_era,
        recent_era_7d=recent_era_7d,
        recent_ip_7d=recent_ip_7d,
        total_innings_pitched=total_ip,
        num_relievers=len(relievers),
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
        
        # Warnings
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