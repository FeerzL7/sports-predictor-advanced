from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple
from sports.baseball.mlb.data_sources.schedule_provider import get_schedule_by_date
from sports.baseball.mlb.data_sources.pitching_provider import (
    lookup_player_id,
    get_pitch_hand,
    get_season_pitching_stats,
    get_game_logs
)
# =========================
# CONFIG (mueve a constants/config si quieres)
# =========================
from sports.baseball.mlb.constants.mlb_constants import (
    LEAGUE_ERA, LEAGUE_FIP, LEAGUE_K9, LEAGUE_BB9,
    EB_IP, MIN_IP_CONFIDENT, RECENT_DAYS, RECENT_STARTS, SEASON
)

# =========================
# DATA CLASSES
# =========================

@dataclass
class PitcherMetrics:
    player_id: Optional[int]
    name: str
    throws: str
    season: int

    # volumen
    gs: int
    ip: float

    # métricas principales
    era: float
    whip: float
    k9: float
    bb9: Optional[float]
    hr9: Optional[float]
    k_bb_pct: Optional[float]

    fip: Optional[float]
    xFIP: Optional[float]

    # ajustadas
    era_adj: float
    fip_adj: Optional[float]

    # forma reciente
    recent_era_30d: Optional[float]
    recent_ip_30d: float
    recent_k9_30d: Optional[float]

    last_n_starts_era: Optional[float]
    last_n_starts_ip: float

    # métricas de fatiga
    days_rest: Optional[int]
    fatigue_flag: bool

    # banderas
    flags: Dict[str, bool]
    missing_fields: List[str]

    # confianza global (0–1)
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

# =========================
# HELPERS
# =========================

def _safe_float(v, default=None):
    try:
        return float(v)
    except Exception:
        return default

def empirical_bayes_adjust(value: float, ip: float, league_value: float, eb_ip: float = EB_IP) -> float:
    return (value * ip + league_value * eb_ip) / (ip + eb_ip) if (ip is not None) else league_value

def probables_today(date: str) -> List[Dict[str, Any]]:
    return get_schedule_by_date(date)

def _get_player_id(name: str) -> Optional[int]:
    if not name or name.lower() in ("tbd", "probable", "desconocido", "unknown"):
        return None
    try:
        return lookup_player_id(name)
    except Exception:
        return None


def _get_throws(player_id: int) -> str:
    try:
        return get_pitch_hand(player_id)
    except Exception:
        return 'R'

def _season_stat(player_id: int, season: int) -> Dict[str, Any]:
    try:
        return get_season_pitching_stats(player_id, season)
    except Exception:
        return {}


def _game_logs(player_id: int, season: int) -> List[Dict[str, Any]]:
    try:
        return get_game_logs(player_id, season)
    except Exception:
        return []




def _calc_recent_from_logs(logs: List[Dict[str, Any]], days: int, last_n_starts: int) -> Tuple[Dict[str, float], Dict[str, float]]:
    recent_cut = datetime.now() - timedelta(days=days)

    def _to_dt(g):
        try:
            return datetime.strptime(g.get('date', ''), '%Y-%m-%d')
        except Exception:
            return None

    def _extract_stat(g):
        st = g.get('stats', {})
        ip = _safe_float(st.get('inningsPitched', 0), 0.0)
        er = _safe_float(st.get('earnedRuns', 0), 0.0)
        so = _safe_float(st.get('strikeOuts', 0), None)
        bb = _safe_float(st.get('baseOnBalls', 0), None)
        hr = _safe_float(st.get('homeRuns', 0), None)
        gs = int(_safe_float(st.get('gamesStarted', 0), 0) or 0)
        return {
            'ip': ip,
            'er': er,
            'so': so,
            'bb': bb,
            'hr': hr,
            'gs': gs
        }

    logs_parsed = []
    for g in logs:
        dt = _to_dt(g)
        if not dt:
            continue
        logs_parsed.append((dt, _extract_stat(g)))
    logs_parsed.sort(key=lambda x: x[0], reverse=True)

    ip_days = er_days = so_days = bb_days = hr_days = 0.0
    for dt, st in logs_parsed:
        if dt >= recent_cut:
            ip_days += st['ip']
            er_days += st['er']
            so_days += st['so'] if st['so'] is not None else 0
            bb_days += st['bb'] if st['bb'] is not None else 0
            hr_days += st['hr'] if st['hr'] is not None else 0

    recent_days = {
        'ip': ip_days,
        'era': (er_days * 9 / ip_days) if ip_days > 0 else None,
        'k9': (so_days * 9 / ip_days) if ip_days > 0 and so_days is not None else None,
        'bb9': (bb_days * 9 / ip_days) if ip_days > 0 and bb_days is not None else None,
        'hr9': (hr_days * 9 / ip_days) if ip_days > 0 and hr_days is not None else None,
    }

    starts = [st for dt, st in logs_parsed if st['gs'] == 1][:last_n_starts]
    ip_n = er_n = so_n = bb_n = hr_n = 0.0
    for st in starts:
        ip_n += st['ip']
        er_n += st['er']
        so_n += st['so'] if st['so'] is not None else 0
        bb_n += st['bb'] if st['bb'] is not None else 0
        hr_n += st['hr'] if st['hr'] is not None else 0

    last_n = {
        'ip': ip_n,
        'era': (er_n * 9 / ip_n) if ip_n > 0 else None,
        'k9': (so_n * 9 / ip_n) if ip_n > 0 and so_n is not None else None,
        'bb9': (bb_n * 9 / ip_n) if ip_n > 0 and bb_n is not None else None,
        'hr9': (hr_n * 9 / ip_n) if ip_n > 0 and hr_n is not None else None,
    }

    return recent_days, last_n

def _calc_days_rest(logs: List[Dict[str, Any]]) -> Optional[int]:
    """Calcula los días de descanso desde la última apertura."""
    if not logs:
        return None
    logs_sorted = sorted(
        [g for g in logs if int(_safe_float(g.get('stats', {}).get('gamesStarted', 0), 0)) == 1],
        key=lambda g: g.get('date', ''), reverse=True
    )
    if not logs_sorted:
        return None
    last_game_date = datetime.strptime(logs_sorted[0]['date'], '%Y-%m-%d')
    return (datetime.now() - last_game_date).days

def build_pitcher_metrics(name: str) -> PitcherMetrics:
    pid = _get_player_id(name)
    tbd = pid is None

    missing = []
    flags = {
        'tbd': tbd,
        'low_sample': False,
        'no_fip': False,
        'no_bb9': False,
        'no_hr9': False,
        'no_recent_data': False
    }

    if tbd:
        return PitcherMetrics(
            player_id=None,
            name=name or "TBD",
            throws='R',
            season=SEASON,
            gs=0,
            ip=0.0,
            era=LEAGUE_ERA,
            whip=1.30,
            k9=LEAGUE_K9,
            bb9=LEAGUE_BB9,
            hr9=None,
            k_bb_pct=None,
            fip=None,
            xFIP=None,
            era_adj=LEAGUE_ERA,
            fip_adj=None,
            recent_era_30d=None,
            recent_ip_30d=0.0,
            recent_k9_30d=None,
            last_n_starts_era=None,
            last_n_starts_ip=0.0,
            days_rest=None,
            fatigue_flag=False,
            flags=flags,
            missing_fields=['all'],
            confidence=0.10
        )

    stat = _season_stat(pid, SEASON)
    throws = _get_throws(pid)

    era = _safe_float(stat.get('era'), LEAGUE_ERA)
    whip = _safe_float(stat.get('whip'), 1.30)
    k9   = _safe_float(stat.get('strikeOutsPer9Inn'), LEAGUE_K9)
    bb9  = _safe_float(stat.get('walksPer9Inn'), None)
    hr9  = _safe_float(stat.get('homeRunsPer9'), None)
    ip   = _safe_float(stat.get('inningsPitched'), 0.0)
    gs   = int(_safe_float(stat.get('gamesStarted'), 0) or 0)

    fip  = _safe_float(stat.get('fip'), None)
    xFIP = _safe_float(stat.get('xfip'), None)

    if fip is None:
        flags['no_fip'] = True
    if bb9 is None:
        flags['no_bb9'] = True
    if hr9 is None:
        flags['no_hr9'] = True

    logs = _game_logs(pid, SEASON)
    if not logs:
        flags['no_recent_data'] = True

    recent_days, last_n = _calc_recent_from_logs(logs, RECENT_DAYS, RECENT_STARTS)
    days_rest = _calc_days_rest(logs)
    fatigue_flag = days_rest is not None and days_rest < 4  # menos de 4 días = posible fatiga

    era_adj = empirical_bayes_adjust(era, ip, LEAGUE_ERA, EB_IP)
    fip_adj = empirical_bayes_adjust(fip, ip, LEAGUE_FIP, EB_IP) if fip is not None else None

    k_bb_pct = None
    try:
        so = _safe_float(stat.get('strikeOuts'), None)
        bb = _safe_float(stat.get('baseOnBalls'), None)
        bf = _safe_float(stat.get('battersFaced'), None)
        if all(v is not None and v > 0 for v in [so, bb, bf]):
            k_bb_pct = ((so - bb) / bf) * 100.0
    except Exception:
        pass

    flags['low_sample'] = ip < MIN_IP_CONFIDENT

    for key, v in [('bb9', bb9), ('hr9', hr9), ('fip', fip)]:
        if v is None:
            missing.append(key)

    confidence = 1.0
    if flags['tbd']:
        confidence *= 0.1
    if flags['low_sample']:
        confidence *= 0.6
    if flags['no_recent_data']:
        confidence *= 0.85
    if flags['no_fip']:
        confidence *= 0.9
    if fatigue_flag:
        confidence *= 0.8

    confidence = max(min(confidence, 1.0), 0.05)

    return PitcherMetrics(
        player_id=pid,
        name=name,
        throws=throws,
        season=SEASON,
        gs=gs,
        ip=ip,
        era=era,
        whip=whip,
        k9=k9,
        bb9=bb9,
        hr9=hr9,
        k_bb_pct=k_bb_pct,
        fip=fip,
        xFIP=xFIP,
        era_adj=era_adj,
        fip_adj=fip_adj,
        recent_era_30d=recent_days['era'],
        recent_ip_30d=recent_days['ip'],
        recent_k9_30d=recent_days['k9'],
        last_n_starts_era=last_n['era'],
        last_n_starts_ip=last_n['ip'],
        days_rest=days_rest,
        fatigue_flag=fatigue_flag,
        flags=flags,
        missing_fields=missing,
        confidence=round(confidence, 3)
    )

# =========================
# API PÚBLICA DEL MÓDULO
# =========================

def analizar_pitchers(date: Optional[str] = None) -> List[Dict[str, Any]]:
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    sched = probables_today(date)
    partidos = []

    for juego in sched:
        home = juego['home_name']
        away = juego['away_name']
        home_p = juego.get('home_probable_pitcher', 'TBD')
        away_p = juego.get('away_probable_pitcher', 'TBD')

        home_stats = build_pitcher_metrics(home_p).to_dict()
        away_stats = build_pitcher_metrics(away_p).to_dict()

        warnings = []
        if home_stats['flags']['tbd'] or away_stats['flags']['tbd']:
            warnings.append('TBD_pitcher')
        if home_stats['flags']['low_sample']:
            warnings.append(f'LOW_SAMPLE_{home_p}')
        if away_stats['flags']['low_sample']:
            warnings.append(f'LOW_SAMPLE_{away_p}')
        if home_stats['fatigue_flag']:
            warnings.append(f'FATIGUE_{home_p}')
        if away_stats['fatigue_flag']:
            warnings.append(f'FATIGUE_{away_p}')

        partidos.append({
            'date': date,
            'home_team': home,
            'away_team': away,
            'home_pitcher': home_p,
            'home_stats': home_stats,
            'away_pitcher': away_p,
            'away_stats': away_stats,
            'start_time': juego.get('game_datetime', '')[:19],
            'data_warnings': warnings
        })

    return partidos
