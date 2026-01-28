# tests/manual/test_historical_data.py

from core.backtesting.historical_data import (
    HistoricalDataLoader,
    ResultMatcher,
    HistoricalGame
)


def test_load_single_date():
    """Test cargar juegos de una fecha."""
    
    loader = HistoricalDataLoader(delay_between_requests=0.2)
    
    # Fecha con juegos conocidos (Opening Day 2024)
    games = loader.load_single_date("2024-03-28")
    
    print("=" * 60)
    print("TEST 1: Load Single Date (2024-03-28)")
    print("=" * 60)
    print(f"Games loaded: {len(games)}")
    
    if games:
        game = games[0]
        print(f"\nSample game:")
        print(f"  {game.away_team} @ {game.home_team}")
        print(f"  Score: {game.away_score} - {game.home_score}")
        print(f"  Total: {game.total_runs}")
        print(f"  Winner: {game.winner}")
    
    print()


def test_load_date_range():
    """Test cargar rango de fechas."""
    
    loader = HistoricalDataLoader(delay_between_requests=0.2)
    
    # Primera semana de temporada 2024
    games = loader.load_date_range("2024-03-28", "2024-04-03")
    
    print("=" * 60)
    print("TEST 2: Load Date Range (Week 1, 2024)")
    print("=" * 60)
    print(f"Total games: {len(games)}")
    
    # Estadísticas
    if games:
        avg_total = sum(g.total_runs for g in games) / len(games)
        home_wins = sum(1 for g in games if g.winner == "home")
        away_wins = sum(1 for g in games if g.winner == "away")
        
        print(f"Average total runs: {avg_total:.2f}")
        print(f"Home wins: {home_wins} ({home_wins/len(games)*100:.1f}%)")
        print(f"Away wins: {away_wins} ({away_wins/len(games)*100:.1f}%)")
    
    print()


def test_result_matcher():
    """Test matcher de resultados."""
    
    # Juego simulado
    game = HistoricalGame(
        game_id=123,
        date="2024-04-01",
        home_team="Yankees",
        away_team="Red Sox",
        venue="Yankee Stadium",
        home_score=5,
        away_score=3,
        total_runs=8,
        game_status="Final",
        innings=9
    )
    
    print("=" * 60)
    print("TEST 3: Result Matcher")
    print("=" * 60)
    print(f"Game: {game.away_team} {game.away_score} @ {game.home_team} {game.home_score}")
    print(f"Total: {game.total_runs}")
    print()
    
    # Pick 1: Moneyline Home (Yankees)
    pick_ml_home = {
        "market": "moneyline",
        "side": "home",
        "team": "Yankees"
    }
    result = ResultMatcher.match_pick(pick_ml_home, game)
    print(f"Moneyline HOME: {result} (expected: WIN)")
    
    # Pick 2: Moneyline Away (Red Sox)
    pick_ml_away = {
        "market": "moneyline",
        "side": "away",
        "team": "Red Sox"
    }
    result = ResultMatcher.match_pick(pick_ml_away, game)
    print(f"Moneyline AWAY: {result} (expected: LOSS)")
    
    # Pick 3: Total OVER 7.5
    pick_over = {
        "market": "total",
        "side": "OVER",
        "line": 7.5
    }
    result = ResultMatcher.match_pick(pick_over, game)
    print(f"Total OVER 7.5: {result} (expected: WIN, total was 8)")
    
    # Pick 4: Total UNDER 8.5
    pick_under = {
        "market": "total",
        "side": "UNDER",
        "line": 8.5
    }
    result = ResultMatcher.match_pick(pick_under, game)
    print(f"Total UNDER 8.5: {result} (expected: WIN, total was 8)")
    
    # Pick 5: Total OVER 8.5
    pick_over_high = {
        "market": "total",
        "side": "OVER",
        "line": 8.5
    }
    result = ResultMatcher.match_pick(pick_over_high, game)
    print(f"Total OVER 8.5: {result} (expected: LOSS, total was 8)")
    
    print()


if __name__ == "__main__":
    test_load_single_date()
    test_load_date_range()
    test_result_matcher()
    
    print("=" * 60)
    print("✅ All historical data tests completed!")
    print("=" * 60)