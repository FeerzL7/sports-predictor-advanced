# core/backtesting/backtest_engine.py

"""
Motor de backtesting para validar modelo con datos históricos.

Simula apuestas y calcula métricas de performance.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from core.backtesting.historical_data import HistoricalGame, ResultMatcher
from core.storage.picks_db import PicksDatabase
from core.utils.logger import setup_logger

logger = setup_logger(__name__)


# =========================
# DATA CLASSES
# =========================

@dataclass
class BacktestResult:
    """Resultado de una apuesta en backtest."""
    
    game_id: int
    date: str
    market: str
    side: str
    team: Optional[str]
    line: Optional[float]
    
    # Pick info
    odds: float
    model_prob: float
    edge: float
    confidence: float
    stake_amount: float
    
    # Resultado
    result: str  # WIN, LOSS, PUSH
    profit: float
    roi: float
    
    # Metadata
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    total_runs: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BacktestSummary:
    """Resumen de performance de backtest."""
    
    # Básico
    total_picks: int
    total_stake: float
    
    # Resultados
    wins: int
    losses: int
    pushes: int
    
    # Performance
    total_profit: float
    roi: float
    win_rate: float
    
    # Por mercado
    moneyline_picks: int
    moneyline_profit: float
    total_picks_market: int
    total_profit_market: float
    
    # Risk
    max_drawdown: float
    sharpe_ratio: Optional[float]
    
    # Edge vs Reality
    avg_edge: float
    avg_actual_edge: float
    edge_realization: float  # Qué % del edge se materializó
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =========================
# BACKTEST ENGINE
# =========================

class BacktestEngine:
    """
    Motor de backtesting.
    
    Uso:
        engine = BacktestEngine(bankroll=10000)
        results = engine.run_backtest(games, picks_generator)
        summary = engine.get_summary()
    """
    
    def __init__(
        self,
        initial_bankroll: float = 10000.0,
        use_kelly: bool = True,
        track_in_db: bool = False,
        db_path: str = None
    ):
        """
        Args:
            initial_bankroll: Bankroll inicial
            use_kelly: Si usar stakes calculados o flat
            track_in_db: Si guardar en database
            db_path: Path a DB (opcional)
        """
        self.initial_bankroll = initial_bankroll
        self.current_bankroll = initial_bankroll
        self.use_kelly = use_kelly
        self.track_in_db = track_in_db
        
        self.results: List[BacktestResult] = []
        self.bankroll_history: List[Tuple[str, float]] = []
        
        if track_in_db:
            self.db = PicksDatabase(db_path) if db_path else PicksDatabase()
        else:
            self.db = None
        
        logger.info(
            f"BacktestEngine initialized: bankroll=${initial_bankroll:,.2f}, "
            f"kelly={use_kelly}, track_db={track_in_db}"
        )
    
    def simulate_bet(
        self,
        pick: Dict[str, Any],
        game: HistoricalGame
    ) -> BacktestResult:
        """
        Simula una apuesta y devuelve resultado.
        
        Args:
            pick: Dict con market, odds, stake, etc
            game: HistoricalGame con resultado real
        
        Returns:
            BacktestResult
        """
        
        # Determinar resultado
        result = ResultMatcher.match_pick(pick, game)
        
        # Calcular profit
        stake = pick.get("stake", 0)
        odds = pick.get("odds", 1.0)
        
        if result == "WIN":
            profit = stake * (odds - 1)
        elif result == "LOSS":
            profit = -stake
        else:  # PUSH
            profit = 0.0
        
        roi = (profit / stake) if stake > 0 else 0.0
        
        # Crear resultado
        backtest_result = BacktestResult(
            game_id=game.game_id,
            date=game.date,
            market=pick.get("market", "unknown"),
            side=pick.get("side", "unknown"),
            team=pick.get("team"),
            line=pick.get("line"),
            odds=odds,
            model_prob=pick.get("model_prob", 0),
            edge=pick.get("edge", 0),
            confidence=pick.get("confidence", 0),
            stake_amount=stake,
            result=result,
            profit=profit,
            roi=roi,
            home_team=game.home_team,
            away_team=game.away_team,
            home_score=game.home_score,
            away_score=game.away_score,
            total_runs=game.total_runs
        )
        
        # Actualizar bankroll
        self.current_bankroll += profit
        self.bankroll_history.append((game.date, self.current_bankroll))
        
        # Guardar en DB
        if self.track_in_db and self.db:
            self._save_to_db(pick, game, result, profit)
        
        return backtest_result
    
    def run_backtest(
        self,
        games: List[HistoricalGame],
        picks: List[Dict[str, Any]],
        match_by_game_id: bool = True
    ) -> List[BacktestResult]:
        """
        Ejecuta backtest completo.
        
        Args:
            games: Lista de juegos históricos
            picks: Lista de picks generados
            match_by_game_id: Si matchear por game_id o por equipos+fecha
        
        Returns:
            Lista de BacktestResult
        """
        
        logger.info(f"Running backtest: {len(picks)} picks, {len(games)} games")
        
        # Crear índice de juegos
        if match_by_game_id:
            games_index = {g.game_id: g for g in games}
        else:
            games_index = {
                f"{g.date}_{g.home_team}_{g.away_team}": g
                for g in games
            }
        
        matched = 0
        unmatched = 0
        
        for pick in picks:
            # Buscar juego correspondiente
            if match_by_game_id:
                game_id = pick.get("game_id") or pick.get("event_id")
                game = games_index.get(game_id)
            else:
                key = f"{pick.get('date')}_{pick.get('home_team')}_{pick.get('away_team')}"
                game = games_index.get(key)
            
            if not game:
                unmatched += 1
                logger.warning(
                    f"No game found for pick: {pick.get('market')} | "
                    f"{pick.get('team')} | {pick.get('date')}"
                )
                continue
            
            # Simular apuesta
            result = self.simulate_bet(pick, game)
            self.results.append(result)
            matched += 1
        
        logger.info(
            f"Backtest complete: {matched} matched, {unmatched} unmatched"
        )
        
        return self.results
    
    def get_summary(self) -> BacktestSummary:
        """Calcula resumen de performance."""
        
        if not self.results:
            logger.warning("No results to summarize")
            return self._empty_summary()
        
        total_picks = len(self.results)
        wins = sum(1 for r in self.results if r.result == "WIN")
        losses = sum(1 for r in self.results if r.result == "LOSS")
        pushes = sum(1 for r in self.results if r.result == "PUSH")
        
        total_stake = sum(r.stake_amount for r in self.results)
        total_profit = sum(r.profit for r in self.results)
        
        decided = wins + losses
        win_rate = (wins / decided) if decided > 0 else 0.0
        roi = (total_profit / total_stake) if total_stake > 0 else 0.0
        
        # Por mercado
        ml_results = [r for r in self.results if r.market == "moneyline"]
        total_results = [r for r in self.results if r.market in ["total", "totals"]]
        
        ml_profit = sum(r.profit for r in ml_results)
        total_profit_market = sum(r.profit for r in total_results)
        
        # Edge
        avg_edge = sum(r.edge for r in self.results) / total_picks
        actual_edge = roi  # ROI realizado
        edge_realization = (actual_edge / avg_edge) if avg_edge > 0 else 0.0
        
        # Drawdown
        max_dd = self._calculate_max_drawdown()
        
        # Sharpe (simplificado)
        sharpe = self._calculate_sharpe_ratio()
        
        return BacktestSummary(
            total_picks=total_picks,
            total_stake=total_stake,
            wins=wins,
            losses=losses,
            pushes=pushes,
            total_profit=total_profit,
            roi=roi,
            win_rate=win_rate,
            moneyline_picks=len(ml_results),
            moneyline_profit=ml_profit,
            total_picks_market=len(total_results),
            total_profit_market=total_profit_market,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            avg_edge=avg_edge,
            avg_actual_edge=actual_edge,
            edge_realization=edge_realization
        )
    
    def _calculate_max_drawdown(self) -> float:
        """Calcula drawdown máximo."""
        
        if not self.bankroll_history:
            return 0.0
        
        peak = self.initial_bankroll
        max_dd = 0.0
        
        for _, bankroll in self.bankroll_history:
            if bankroll > peak:
                peak = bankroll
            
            dd = (peak - bankroll) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def _calculate_sharpe_ratio(self) -> Optional[float]:
        """Calcula Sharpe ratio simplificado."""
        
        if len(self.results) < 2:
            return None
        
        returns = [r.roi for r in self.results]
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return None
        
        # Sharpe anualizado (asumiendo ~250 picks/año)
        sharpe = (avg_return / std_dev) * (250 ** 0.5)
        
        return sharpe
    
    def _empty_summary(self) -> BacktestSummary:
        """Resumen vacío."""
        return BacktestSummary(
            total_picks=0,
            total_stake=0.0,
            wins=0,
            losses=0,
            pushes=0,
            total_profit=0.0,
            roi=0.0,
            win_rate=0.0,
            moneyline_picks=0,
            moneyline_profit=0.0,
            total_picks_market=0,
            total_profit_market=0.0,
            max_drawdown=0.0,
            sharpe_ratio=None,
            avg_edge=0.0,
            avg_actual_edge=0.0,
            edge_realization=0.0
        )
    
    def _save_to_db(
        self,
        pick: Dict[str, Any],
        game: HistoricalGame,
        result: str,
        profit: float
    ):
        """Guarda pick y resultado en DB."""
        
        # Guardar evento
        self.db.save_event(
            event_id=str(game.game_id),
            sport="baseball",
            league="MLB",
            date=game.date,
            home_team=game.home_team,
            away_team=game.away_team,
            venue=game.venue
        )
        
        # Guardar pick con resultado
        pick_copy = pick.copy()
        pick_copy["event_id"] = str(game.game_id)
        pick_id = self.db.save_pick(pick_copy)
        
        # Actualizar resultado
        self.db.update_result(
            pick_id,
            result,
            actual_outcome=f"{game.home_score}-{game.away_score}",
            profit=profit
        )
    
    def print_summary(self):
        """Imprime resumen legible."""
        
        summary = self.get_summary()
        
        print("=" * 60)
        print("BACKTEST SUMMARY")
        print("=" * 60)
        print(f"Total Picks: {summary.total_picks}")
        print(f"Wins: {summary.wins}")
        print(f"Losses: {summary.losses}")
        print(f"Pushes: {summary.pushes}")
        print(f"Win Rate: {summary.win_rate*100:.1f}%")
        print()
        print(f"Total Stake: ${summary.total_stake:,.2f}")
        print(f"Total Profit: ${summary.total_profit:,.2f}")
        print(f"ROI: {summary.roi*100:.2f}%")
        print()
        print(f"Initial Bankroll: ${self.initial_bankroll:,.2f}")
        print(f"Final Bankroll: ${self.current_bankroll:,.2f}")
        print(f"Net Change: ${self.current_bankroll - self.initial_bankroll:,.2f}")
        print()
        print(f"Max Drawdown: {summary.max_drawdown*100:.1f}%")
        if summary.sharpe_ratio:
            print(f"Sharpe Ratio: {summary.sharpe_ratio:.2f}")
        print()
        print(f"Avg Model Edge: {summary.avg_edge*100:.2f}%")
        print(f"Realized Edge: {summary.avg_actual_edge*100:.2f}%")
        print(f"Edge Realization: {summary.edge_realization*100:.1f}%")
        print()
        print("BY MARKET:")
        print(f"  Moneyline: {summary.moneyline_picks} picks, ${summary.moneyline_profit:,.2f}")
        print(f"  Totals: {summary.total_picks_market} picks, ${summary.total_profit_market:,.2f}")
        print("=" * 60)