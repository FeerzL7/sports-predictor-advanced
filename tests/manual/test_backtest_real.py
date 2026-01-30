# tests/manual/test_backtest_real.py

from datetime import datetime

from core.backtesting.historical_data import HistoricalDataLoader
from core.backtesting.backtest_engine import BacktestEngine
from sports.baseball.mlb.adapter import MLBAdapter
from core.odds.providers.fake_provider import FakeOddsProvider

from config.settings import set_risk_profile

from sports.baseball.mlb.data_sources.team_stats_provider import set_backtest_mode

def test_real_backtest():
    """Backtest con modelo real usando pybaseball."""
    
    print("=" * 60)
    print("REAL MODEL BACKTEST (with pybaseball)")
    print("=" * 60)
    
    # Configuración
    BACKTEST_START = "2024-04-01"
    BACKTEST_END = "2024-04-07"
    RISK_PROFILE = "balanced"
    INITIAL_BANKROLL = 10000.0
    
    
    
    print(f"\nConfiguration:")
    print(f"  Period: {BACKTEST_START} to {BACKTEST_END}")
    print(f"  Risk Profile: {RISK_PROFILE}")
    print(f"  Bankroll: ${INITIAL_BANKROLL:,.2f}")
    
    # ✨ CRÍTICO: Activar backtest mode
    set_backtest_mode(True)
    print(f"  Backtest Mode: ENABLED (recent stats disabled)")
    
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
    
    adapter = MLBAdapter(
        odds_provider=FakeOddsProvider(
            total_line=8.5,
            odds_over=1.91,
            odds_under=1.91,
            ml_home=1.85,
            ml_away=2.10
        ),
        validate_picks=True
    )
    
    # 3. Generar picks para cada juego
    print(f"\n⚙️  Generating picks...")
    
    all_picks = []
    picks_by_date = {}
    errors_count = 0
    
    for game in games:
        game_season = int(game.date[:4])
        
        # Crear evento MÍNIMO (sin pitchers)
        # El modelo usará defaults cuando no haya pitchers
        event = {
            "game_id": game.game_id,
            "date": game.date,
            "home_team": game.home_team,
            "away_team": game.away_team,
            "venue": game.venue,
            "start_time": f"{game.date}T19:00:00",
            "season": game_season,
            
            # ✨ CRÍTICO: Agregar datos mínimos de pitchers
            # Como no tenemos probable pitchers en datos históricos,
            # usamos "TBD" y el modelo aplicará defaults
            "home_pitcher": "TBD",
            "away_pitcher": "TBD",
            
            # Stats vacíos (se llenarán en análisis)
            "home_stats": {},
            "away_stats": {},
        }
        
        try:
            # Análisis completo (SKIP pitching analysis para backtest)
            from sports.baseball.mlb.analysis.offense import analizar_ofensiva
            from sports.baseball.mlb.analysis.defense import analizar_defensiva
            from sports.baseball.mlb.analysis.context import analizar_contexto
            from sports.baseball.mlb.analysis.h2h import analizar_h2h
            from sports.baseball.mlb.analysis.bullpen import analizar_bullpens
            from sports.baseball.mlb.analysis.projections import proyectar_totales
            
            # Pipeline SIMPLIFICADO (sin pitchers individuales)
            partidos = [event]
            
            # Usar defaults para pitchers (TBD)
            from sports.baseball.mlb.analysis.pitching import build_pitcher_metrics
            partidos[0]["home_stats"] = build_pitcher_metrics("TBD", game_season).to_dict()
            partidos[0]["away_stats"] = build_pitcher_metrics("TBD", game_season).to_dict()
            
            # Resto del pipeline
            partidos = analizar_ofensiva(partidos, game_season)
            partidos = analizar_defensiva(partidos, game_season)
            partidos = analizar_contexto(partidos)
            partidos = analizar_h2h(partidos, game_season)
            partidos = analizar_bullpens(partidos, game_season)
            partidos = proyectar_totales(partidos)
            
            # Normalizar análisis
            analysis = adapter._normalize_analysis(partidos[0])
            
            # Agregar odds (fake provider)
            if adapter.odds_provider:
                markets = adapter.odds_provider.get_markets(analysis)
                if isinstance(markets, dict) and markets:
                    analysis["market"].update(markets)
            
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
            errors_count += 1
            if errors_count <= 5:  # Solo mostrar primeros 5 errores
                print(f"   ⚠️  Error analyzing {game.home_team} vs {game.away_team}: {e}")
            continue
    
    if errors_count > 5:
        print(f"   ⚠️  ... and {errors_count - 5} more errors (suppressed)")
    
    print(f"   Generated: {len(all_picks)} picks")
    print(f"\n   Picks by date:")
    for date, picks in sorted(picks_by_date.items()):
        print(f"      {date}: {len(picks)} picks")
    
    if not all_picks:
        print("\n⚠️  No valid picks generated")
        print("\nPossible reasons:")
        print("  1. No pitchers available in historical data (using TBD defaults)")
        print("  2. Model confidence too low with missing pitcher data")
        print("  3. Edge threshold (3%) too high for games with incomplete data")
        print("\nSuggestion: Lower thresholds or use aggressive profile")
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