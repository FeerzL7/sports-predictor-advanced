# tests/manual/test_backtest_simple.py

"""
Test simple de backtest con picks simulados.
"""

from core.backtesting.historical_data import HistoricalDataLoader, HistoricalGame
from core.backtesting.backtest_engine import BacktestEngine


def test_simple_backtest():
    """Test con picks simulados sobre juegos reales."""
    
    print("=" * 60)
    print("SIMPLE BACKTEST TEST")
    print("=" * 60)
    
    # 1. Cargar juegos reales (Opening Day 2024)
    loader = HistoricalDataLoader(delay_between_requests=0.2)
    games = loader.load_single_date("2024-03-28")
    
    print(f"\nLoaded {len(games)} games from 2024-03-28")
    
    # 2. Crear picks simulados (favoreciendo totals OVER)
    picks = []
    
    for game in games[:5]:  # Solo primeros 5 para test rápido
        # Pick: Total OVER (line conservadora)
        pick = {
            "game_id": game.game_id,
            "date": game.date,
            "market": "total",
            "side": "OVER",
            "line": 7.5,  # Line conservadora
            "odds": 1.91,  # -110 en americano
            "model_prob": 0.55,
            "implied_prob": 0.524,
            "edge": 0.026,
            "confidence": 0.62,
            "stake": 100.0,
            "home_team": game.home_team,
            "away_team": game.away_team
        }
        picks.append(pick)
    
    print(f"Generated {len(picks)} simulated picks (all OVER 7.5)")
    
    # 3. Ejecutar backtest
    engine = BacktestEngine(initial_bankroll=10000, use_kelly=False)
    results = engine.run_backtest(games, picks)
    
    print(f"\nBacktest completed: {len(results)} bets simulated")
    
    # 4. Mostrar resumen
    print()
    engine.print_summary()
    
    # 5. Mostrar picks individuales
    print("\nINDIVIDUAL RESULTS:")
    print("-" * 60)
    for r in results:
        symbol = "✅" if r.result == "WIN" else "❌" if r.result == "LOSS" else "➖"
        print(
            f"{symbol} {r.away_team} @ {r.home_team} | "
            f"Total: {r.total_runs} | Line: {r.line} | "
            f"Result: {r.result} | Profit: ${r.profit:.2f}"
        )


if __name__ == "__main__":
    test_simple_backtest()