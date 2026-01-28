# tests/manual/test_backtest_real.py

"""
Backtest REAL usando el modelo completo de MLB.
"""

from datetime import datetime

from core.backtesting.historical_data import HistoricalDataLoader
from core.backtesting.backtest_engine import BacktestEngine
from sports.baseball.mlb.adapter import MLBAdapter
from core.odds.providers.fake_provider import FakeOddsProvider

from config.settings import set_risk_profile


def test_real_backtest():
    """
    Backtest con modelo real.
    
    Proceso:
    1. Cargar juegos históricos
    2. Para cada juego, ejecutar análisis completo
    3. Generar picks con validación
    4. Simular apuestas
    5. Calcular performance
    """
    
    print("=" * 60)
    print("REAL MODEL BACKTEST")
    print("=" * 60)
    
    # Configuración
    BACKTEST_START = "2024-04-01"
    BACKTEST_END = "2024-04-07"  # Primera semana completa (7 días)
    RISK_PROFILE = "balanced"
    INITIAL_BANKROLL = 10000.0
    
    print(f"\nConfiguration:")
    print(f"  Period: {BACKTEST_START} to {BACKTEST_END}")
    print(f"  Risk Profile: {RISK_PROFILE}")
    print(f"  Bankroll: ${INITIAL_BANKROLL:,.2f}")
    
    # Establecer perfil
    set_risk_profile(RISK_PROFILE)
    
    # 1. Cargar datos históricos
    print(f"\n📊 Loading historical data...")
    loader = HistoricalDataLoader(delay_between_requests=0.3)
    games = loader.load_date_range(BACKTEST_START, BACKTEST_END)
    
    print(f"   Loaded: {len(games)} games")
    
    if not games:
        print("❌ No games found for this period")
        return
    
    # 2. Inicializar adapter con fake provider
    print(f"\n🔧 Initializing MLB adapter...")
    
    # Usamos FakeProvider porque no tenemos odds reales históricos
    # En producción real, necesitarías historical odds data
    adapter = MLBAdapter(
        odds_provider=FakeOddsProvider(
            total_line=8.5,  # Line promedio MLB
            odds_over=1.91,  # -110
            odds_under=1.91,
            ml_home=1.85,    # Promedio
            ml_away=2.10
        ),
        validate_picks=True  # Validación activada
    )
    
    # 3. Generar picks para cada juego
    print(f"\n⚙️  Generating picks...")
    
    all_picks = []
    picks_by_date = {}
    
    for game in games:
        # Convertir HistoricalGame a formato event
        event = {
            "game_id": game.game_id,
            "date": game.date,
            "home_team": game.home_team,
            "away_team": game.away_team,
            "venue": game.venue,
            "start_time": f"{game.date}T19:00:00"
        }
        
        try:
            # Análisis completo
            analysis = adapter.analyze_event(event)
            
            # Generar picks (con validación)
            picks = adapter.generate_picks(analysis)
            
            # Agregar metadata del juego
            for pick in picks:
                pick["game_id"] = game.game_id
                pick["date"] = game.date
                pick["home_team"] = game.home_team
                pick["away_team"] = game.away_team
                
                # Calcular stake (Kelly)
                from core.odds.staking.stake_engine import calculate_stake
                pick_with_stake = calculate_stake(
                    pick,
                    bankroll=INITIAL_BANKROLL
                )
                all_picks.append(pick_with_stake)
            
            # Agrupar por fecha
            if game.date not in picks_by_date:
                picks_by_date[game.date] = []
            picks_by_date[game.date].extend(picks)
        
        except Exception as e:
            print(f"   ⚠️  Error analyzing {game.home_team} vs {game.away_team}: {e}")
            continue
    
    print(f"   Generated: {len(all_picks)} picks")
    print(f"\n   Picks by date:")
    for date, picks in sorted(picks_by_date.items()):
        print(f"      {date}: {len(picks)} picks")
    
    if not all_picks:
        print("❌ No valid picks generated")
        return
    
    # 4. Ejecutar backtest
    print(f"\n🎲 Running backtest simulation...")
    
    engine = BacktestEngine(
        initial_bankroll=INITIAL_BANKROLL,
        use_kelly=True,
        track_in_db=False
    )
    
    results = engine.run_backtest(games, all_picks)
    
    # 5. Mostrar resultados
    print(f"\n" + "=" * 60)
    engine.print_summary()
    
    # 6. Breakdown por mercado
    summary = engine.get_summary()
    
    print("\nDETAILED BREAKDOWN:")
    print("-" * 60)
    
    ml_results = [r for r in results if r.market == "moneyline"]
    total_results = [r for r in results if r.market in ["total", "TOTAL"]]
    
    if ml_results:
        ml_wins = sum(1 for r in ml_results if r.result == "WIN")
        ml_losses = sum(1 for r in ml_results if r.result == "LOSS")
        ml_wr = (ml_wins / (ml_wins + ml_losses)) if (ml_wins + ml_losses) > 0 else 0
        ml_profit = sum(r.profit for r in ml_results)
        ml_stake = sum(r.stake_amount for r in ml_results)
        ml_roi = (ml_profit / ml_stake) if ml_stake > 0 else 0
        
        print(f"MONEYLINE:")
        print(f"  Record: {ml_wins}-{ml_losses} ({ml_wr*100:.1f}%)")
        print(f"  Profit: ${ml_profit:.2f}")
        print(f"  ROI: {ml_roi*100:.1f}%")
    
    if total_results:
        tot_wins = sum(1 for r in total_results if r.result == "WIN")
        tot_losses = sum(1 for r in total_results if r.result == "LOSS")
        tot_wr = (tot_wins / (tot_wins + tot_losses)) if (tot_wins + tot_losses) > 0 else 0
        tot_profit = sum(r.profit for r in total_results)
        tot_stake = sum(r.stake_amount for r in total_results)
        tot_roi = (tot_profit / tot_stake) if tot_stake > 0 else 0
        
        print(f"\nTOTALS:")
        print(f"  Record: {tot_wins}-{tot_losses} ({tot_wr*100:.1f}%)")
        print(f"  Profit: ${tot_profit:.2f}")
        print(f"  ROI: {tot_roi*100:.1f}%")
    
    # 7. Sample de picks
    print(f"\nSAMPLE PICKS (first 5):")
    print("-" * 60)
    for r in results[:5]:
        symbol = "✅" if r.result == "WIN" else "❌" if r.result == "LOSS" else "➖"
        print(
            f"{symbol} {r.market.upper()} {r.side} | "
            f"{r.away_team} @ {r.home_team} | "
            f"Edge: {r.edge*100:.1f}% | Conf: {r.confidence*100:.1f}% | "
            f"Stake: ${r.stake_amount:.2f} | P/L: ${r.profit:.2f}"
        )
    
    print("\n" + "=" * 60)
    print("✅ Backtest completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_real_backtest()