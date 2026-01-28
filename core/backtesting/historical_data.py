# core/backtesting/historical_data.py

"""
Carga y procesa datos históricos de MLB para backtesting.

Fuente: MLB StatsAPI (gratis, sin límites)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import time

from sports.baseball.mlb.data_sources.statsapi_client import statsapi_get
from core.utils.logger import setup_logger

logger = setup_logger(__name__)


# =========================
# DATA CLASSES
# =========================

@dataclass
class HistoricalGame:
    """Juego histórico con resultado real."""
    
    game_id: int
    date: str
    home_team: str
    away_team: str
    venue: str
    
    # Resultados reales
    home_score: int
    away_score: int
    total_runs: int
    
    # Metadata
    game_status: str  # Final, Postponed, etc
    innings: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @property
    def winner(self) -> str:
        """Ganador del juego."""
        if self.home_score > self.away_score:
            return "home"
        elif self.away_score > self.home_score:
            return "away"
        return "push"


# =========================
# HISTORICAL DATA LOADER
# =========================

class HistoricalDataLoader:
    """
    Carga datos históricos de MLB desde StatsAPI.
    
    Uso:
        loader = HistoricalDataLoader()
        games = loader.load_date_range("2024-04-01", "2024-04-07")
    """
    
    def __init__(self, delay_between_requests: float = 0.5):
        """
        Args:
            delay_between_requests: Segundos entre requests (rate limiting)
        """
        self.delay = delay_between_requests
    
    def load_single_date(self, date: str) -> List[HistoricalGame]:
        """
        Carga juegos de una fecha específica.
        
        Args:
            date: Fecha en formato YYYY-MM-DD
        
        Returns:
            Lista de HistoricalGame
        """
        
        logger.info(f"Loading games for {date}")
        
        try:
            resp = statsapi_get("schedule", {"date": date, "sportId": 1})
            
            dates = resp.get("dates", [])
            if not dates:
                logger.warning(f"No games found for {date}")
                return []
            
            games_raw = dates[0].get("games", [])
            games = []
            
            for g in games_raw:
                # Solo juegos finalizados
                status = g.get("status", {}).get("abstractGameState", "")
                if status != "Final":
                    logger.debug(f"Skipping game {g.get('gamePk')} (status: {status})")
                    continue
                
                teams = g.get("teams", {})
                home = teams.get("home", {})
                away = teams.get("away", {})
                
                game = HistoricalGame(
                    game_id=g.get("gamePk"),
                    date=date,
                    home_team=home.get("team", {}).get("name", "Unknown"),
                    away_team=away.get("team", {}).get("name", "Unknown"),
                    venue=g.get("venue", {}).get("name", "Unknown"),
                    home_score=home.get("score", 0),
                    away_score=away.get("score", 0),
                    total_runs=home.get("score", 0) + away.get("score", 0),
                    game_status=status,
                    innings=g.get("scheduledInnings", 9)
                )
                
                games.append(game)
            
            logger.info(f"Loaded {len(games)} completed games for {date}")
            return games
        
        except Exception as e:
            logger.error(f"Error loading games for {date}: {e}", exc_info=True)
            return []
    
    def load_date_range(
        self,
        start_date: str,
        end_date: str,
        max_days: int = 180
    ) -> List[HistoricalGame]:
        """
        Carga juegos en un rango de fechas.
        
        Args:
            start_date: Fecha inicial (YYYY-MM-DD)
            end_date: Fecha final (YYYY-MM-DD)
            max_days: Máximo de días a cargar (protección)
        
        Returns:
            Lista de HistoricalGame
        """
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        if (end - start).days > max_days:
            raise ValueError(f"Date range too large: max {max_days} days")
        
        all_games = []
        current = start
        
        logger.info(f"Loading historical data: {start_date} to {end_date}")
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            games = self.load_single_date(date_str)
            all_games.extend(games)
            
            current += timedelta(days=1)
            time.sleep(self.delay)  # Rate limiting
        
        logger.info(f"Total games loaded: {len(all_games)}")
        
        return all_games
    
    def load_season_sample(
        self,
        season: int,
        sample_size: int = 50
    ) -> List[HistoricalGame]:
        """
        Carga muestra aleatoria de una temporada.
        
        Args:
            season: Año de la temporada (ej: 2024)
            sample_size: Número de días a samplear
        
        Returns:
            Lista de HistoricalGame
        """
        
        # Temporada MLB típica: Abril 1 - Septiembre 30
        start_date = f"{season}-04-01"
        end_date = f"{season}-09-30"
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        total_days = (end - start).days
        
        if sample_size > total_days:
            sample_size = total_days
        
        # Samplear días uniformemente
        import random
        random.seed(42)  # Reproducible
        
        sample_days = sorted(random.sample(range(total_days), sample_size))
        
        all_games = []
        
        logger.info(f"Sampling {sample_size} days from {season} season")
        
        for day_offset in sample_days:
            date = start + timedelta(days=day_offset)
            date_str = date.strftime("%Y-%m-%d")
            
            games = self.load_single_date(date_str)
            all_games.extend(games)
            
            time.sleep(self.delay)
        
        logger.info(f"Sample loaded: {len(all_games)} games")
        
        return all_games


# =========================
# RESULT MATCHER
# =========================

class ResultMatcher:
    """
    Relaciona picks con resultados reales.
    """
    
    @staticmethod
    def match_moneyline(
        pick: Dict[str, Any],
        game: HistoricalGame
    ) -> str:
        """
        Evalúa resultado de pick moneyline.
        
        Returns:
            "WIN", "LOSS", o "PUSH"
        """
        
        side = pick.get("side")
        
        if side == "home":
            if game.home_score > game.away_score:
                return "WIN"
            elif game.away_score > game.home_score:
                return "LOSS"
            return "PUSH"
        
        elif side == "away":
            if game.away_score > game.home_score:
                return "WIN"
            elif game.home_score > game.away_score:
                return "LOSS"
            return "PUSH"
        
        return "UNKNOWN"
    
    @staticmethod
    def match_total(
        pick: Dict[str, Any],
        game: HistoricalGame
    ) -> str:
        """
        Evalúa resultado de pick total.
        
        Returns:
            "WIN", "LOSS", o "PUSH"
        """
        
        side = pick.get("side", "").upper()
        line = pick.get("line")
        
        if line is None:
            return "UNKNOWN"
        
        total = game.total_runs
        
        if side == "OVER":
            if total > line:
                return "WIN"
            elif total < line:
                return "LOSS"
            return "PUSH"
        
        elif side == "UNDER":
            if total < line:
                return "WIN"
            elif total > line:
                return "LOSS"
            return "PUSH"
        
        return "UNKNOWN"
    
    @classmethod
    def match_pick(
        cls,
        pick: Dict[str, Any],
        game: HistoricalGame
    ) -> str:
        """
        Evalúa resultado de cualquier pick.
        
        Args:
            pick: Dict con market, side, line, etc
            game: HistoricalGame con resultados reales
        
        Returns:
            "WIN", "LOSS", "PUSH", o "UNKNOWN"
        """
        
        market = pick.get("market", "").lower()
        
        if market == "moneyline":
            return cls.match_moneyline(pick, game)
        
        elif market in ["total", "totals"]:
            return cls.match_total(pick, game)
        
        else:
            logger.warning(f"Unknown market: {market}")
            return "UNKNOWN"


# =========================
# HELPERS
# =========================

def filter_games_by_teams(
    games: List[HistoricalGame],
    teams: List[str]
) -> List[HistoricalGame]:
    """Filtra juegos que incluyan equipos específicos."""
    
    teams_lower = [t.lower() for t in teams]
    
    return [
        g for g in games
        if g.home_team.lower() in teams_lower or g.away_team.lower() in teams_lower
    ]


def games_to_dict_list(games: List[HistoricalGame]) -> List[Dict[str, Any]]:
    """Convierte lista de games a lista de dicts."""
    return [g.to_dict() for g in games]