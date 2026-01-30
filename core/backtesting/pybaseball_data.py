# core/backtesting/pybaseball_data.py

"""
Cargador de datos históricos usando pybaseball.

Alternativa a MLB StatsAPI para backtesting, ya que
pybaseball tiene acceso completo a datos históricos.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

from core.utils.logger import setup_logger

logger = setup_logger(__name__)

# Lazy imports (pybaseball tarda en importar)
_pybaseball_imported = False
_schedule_and_record = None
_team_batting = None
_team_pitching = None
_team_fielding = None


def _ensure_pybaseball():
    """Import pybaseball solo cuando se necesite."""
    global _pybaseball_imported, _schedule_and_record, _team_batting, _team_pitching, _team_fielding
    
    if not _pybaseball_imported:
        try:
            from pybaseball import schedule_and_record, team_batting, team_pitching, team_fielding
            _schedule_and_record = schedule_and_record
            _team_batting = team_batting
            _team_pitching = team_pitching
            _team_fielding = team_fielding
            _pybaseball_imported = True
            logger.info("pybaseball loaded successfully")
        except ImportError:
            logger.error("pybaseball not installed. Install with: pip install pybaseball")
            raise


# =========================
# TEAM NAME MAPPING
# =========================

MLB_TEAM_ABBR = {
    "Arizona Diamondbacks": "ARI",
    "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS",
    "Chicago Cubs": "CHC",
    "Chicago White Sox": "CHW",
    "Cincinnati Reds": "CIN",
    "Cleveland Guardians": "CLE",
    "Cleveland Indians": "CLE",  # Alias para datos pre-2022
    "Colorado Rockies": "COL",
    "Detroit Tigers": "DET",
    "Houston Astros": "HOU",
    "Kansas City Royals": "KCR",
    "Los Angeles Angels": "LAA",
    "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN",
    "New York Mets": "NYM",
    "New York Yankees": "NYY",
    "Oakland Athletics": "OAK",
    "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT",
    "San Diego Padres": "SDP",
    "San Francisco Giants": "SFG",
    "Seattle Mariners": "SEA",
    "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TBR",
    "Texas Rangers": "TEX",
    "Toronto Blue Jays": "TOR",
    "Washington Nationals": "WSN",
}


def get_team_abbr(team_name: str) -> Optional[str]:
    """Convierte nombre completo a abreviatura."""
    return MLB_TEAM_ABBR.get(team_name)


# =========================
# BATTING STATS
# =========================

def get_team_batting_stats_pybaseball(
    team_name: str,
    season: int
) -> Dict[str, Any]:
    """
    Obtiene stats ofensivas de temporada completa.
    
    Returns:
        Dict con formato compatible con StatsAPI
    """
    
    _ensure_pybaseball()
    
    abbr = get_team_abbr(team_name)
    if not abbr:
        logger.warning(f"Team abbreviation not found: {team_name}")
        return {"available": False}
    
    try:
        logger.debug(f"Fetching batting stats for {abbr} ({season})")
        df = _team_batting(season)
        
        # Filtrar por equipo
        team_data = df[df['Team'] == abbr]
        
        if team_data.empty:
            logger.warning(f"No batting data for {abbr} in {season}")
            return {"available": False}
        
        row = team_data.iloc[0]
        
        # Mapear a formato StatsAPI
        games = int(row.get('G', 0))
        runs = int(row.get('R', 0))
        
        return {
            "available": True,
            "gamesPlayed": games,
            "runsPerGame": runs / games if games > 0 else 4.6,
            "ops": float(row.get('OPS', 0.715)),
            "woba": float(row.get('wOBA', None)) if pd.notna(row.get('wOBA')) else None,
            "iso": float(row.get('ISO', None)) if pd.notna(row.get('ISO')) else None,
            "bbPercent": None,  # pybaseball no tiene BB%
            "kPercent": None,   # pybaseball no tiene K%
            "babip": float(row.get('BABIP', None)) if pd.notna(row.get('BABIP')) else None,
            "source": "pybaseball"
        }
    
    except Exception as e:
        logger.error(f"Error getting batting stats for {team_name}: {e}", exc_info=True)
        return {"available": False}


# =========================
# PITCHING STATS
# =========================

def get_team_pitching_stats_pybaseball(
    team_name: str,
    season: int
) -> Dict[str, Any]:
    """
    Obtiene stats de pitching de temporada.
    
    Returns:
        Dict con ERA, IP, etc.
    """
    
    _ensure_pybaseball()
    
    abbr = get_team_abbr(team_name)
    if not abbr:
        return {"available": False}
    
    try:
        logger.debug(f"Fetching pitching stats for {abbr} ({season})")
        df = _team_pitching(season)
        
        team_data = df[df['Team'] == abbr]
        
        if team_data.empty:
            logger.warning(f"No pitching data for {abbr} in {season}")
            return {"available": False}
        
        row = team_data.iloc[0]
        
        return {
            "available": True,
            "era": float(row.get('ERA', 4.30)),
            "inningsPitched": float(row.get('IP', 0)),
            "strikeoutsPer9Inn": float(row.get('SO9', 8.6)) if pd.notna(row.get('SO9')) else None,
            "walksPer9Inn": float(row.get('BB9', 3.3)) if pd.notna(row.get('BB9')) else None,
            "whip": float(row.get('WHIP', 1.30)),
            "source": "pybaseball"
        }
    
    except Exception as e:
        logger.error(f"Error getting pitching stats: {e}", exc_info=True)
        return {"available": False}


# =========================
# FIELDING STATS
# =========================

def get_team_fielding_stats_pybaseball(
    team_name: str,
    season: int
) -> Dict[str, Any]:
    """Obtiene stats defensivas."""
    
    _ensure_pybaseball()
    
    abbr = get_team_abbr(team_name)
    if not abbr:
        return {"available": False}
    
    try:
        logger.debug(f"Fetching fielding stats for {abbr} ({season})")
        df = _team_fielding(season)
        
        team_data = df[df['Team'] == abbr]
        
        if team_data.empty:
            return {"available": False}
        
        row = team_data.iloc[0]
        games = int(row.get('G', 0))
        errors = int(row.get('E', 0))
        
        return {
            "available": True,
            "games": games,
            "errors": errors,
            "fieldingPercentage": float(row.get('Fld%', 0.985)),
            "doublePlays": int(row.get('DP', 0)),
            "source": "pybaseball"
        }
    
    except Exception as e:
        logger.error(f"Error getting fielding stats: {e}", exc_info=True)
        return {"available": False}


# =========================
# RECENT STATS (CALCULADOS)
# =========================

def get_team_recent_stats_pybaseball(
    team_name: str,
    season: int,
    end_date: str,
    window_days: int = 14
) -> Dict[str, Any]:
    """
    Calcula stats recientes desde schedule.
    
    Args:
        team_name: Nombre completo del equipo
        season: Año
        end_date: Fecha final YYYY-MM-DD
        window_days: Ventana de días
    
    Returns:
        Dict con stats recientes
    """
    
    _ensure_pybaseball()
    
    abbr = get_team_abbr(team_name)
    if not abbr:
        return {"available": False}
    
    try:
        logger.debug(f"Fetching recent stats for {abbr} ({end_date}, {window_days}d)")
        
        # Obtener schedule
        schedule = _schedule_and_record(season, abbr)
        
        # Convertir fechas
        schedule['Date'] = pd.to_datetime(schedule['Date'])
        end = pd.to_datetime(end_date)
        start = end - timedelta(days=window_days)
        
        # Filtrar ventana
        recent = schedule[
            (schedule['Date'] >= start) & 
            (schedule['Date'] <= end)
        ]
        
        if recent.empty:
            return {"available": False}
        
        games = len(recent)
        runs = recent['R'].sum()
        
        # OPS aproximado (no disponible en schedule)
        # Usamos runs como proxy
        
        return {
            "available": True,
            "window": window_days,
            "games": games,
            "runsPerGame": float(runs / games) if games > 0 else None,
            "ops": None,  # No disponible en schedule
            "confidence": 0.7 if games >= window_days * 0.6 else 0.4,
            "source": "pybaseball_schedule"
        }
    
    except Exception as e:
        logger.error(f"Error calculating recent stats: {e}", exc_info=True)
        return {"available": False}


# =========================
# SCHEDULE
# =========================

def get_schedule_pybaseball(
    team_name: str,
    season: int
) -> List[Dict[str, Any]]:
    """Obtiene schedule completo con resultados."""
    
    _ensure_pybaseball()
    
    abbr = get_team_abbr(team_name)
    if not abbr:
        return []
    
    try:
        df = _schedule_and_record(season, abbr)
        
        games = []
        for _, row in df.iterrows():
            games.append({
                "date": row['Date'].strftime('%Y-%m-%d') if pd.notna(row['Date']) else None,
                "opponent": row['Opp'],
                "home_away": "home" if row.get('Home_Away') == 'Home' else "away",
                "result": row.get('W/L'),
                "runs": int(row.get('R', 0)),
                "runs_allowed": int(row.get('RA', 0)),
            })
        
        return games
    
    except Exception as e:
        logger.error(f"Error getting schedule: {e}", exc_info=True)
        return []