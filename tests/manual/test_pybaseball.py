# tests/manual/test_pybaseball.py

"""
Test de integración de pybaseball.
"""

from core.backtesting.pybaseball_data import (
    get_team_batting_stats_pybaseball,
    get_team_pitching_stats_pybaseball,
    get_team_fielding_stats_pybaseball,
    get_team_recent_stats_pybaseball
)


def test_batting_stats():
    """Test batting stats."""
    
    print("=" * 60)
    print("TEST 1: Batting Stats (Yankees 2024)")
    print("=" * 60)
    
    stats = get_team_batting_stats_pybaseball("New York Yankees", 2024)
    
    print(f"Available: {stats.get('available')}")
    print(f"Games: {stats.get('gamesPlayed')}")
    print(f"Runs/Game: {stats.get('runsPerGame')}")
    print(f"OPS: {stats.get('ops')}")
    print(f"Source: {stats.get('source')}")
    print()


def test_pitching_stats():
    """Test pitching stats."""
    
    print("=" * 60)
    print("TEST 2: Pitching Stats (Dodgers 2024)")
    print("=" * 60)
    
    stats = get_team_pitching_stats_pybaseball("Los Angeles Dodgers", 2024)
    
    print(f"Available: {stats.get('available')}")
    print(f"ERA: {stats.get('era')}")
    print(f"IP: {stats.get('inningsPitched')}")
    print(f"K/9: {stats.get('strikeoutsPer9Inn')}")
    print(f"Source: {stats.get('source')}")
    print()


def test_fielding_stats():
    """Test fielding stats."""
    
    print("=" * 60)
    print("TEST 3: Fielding Stats (Red Sox 2024)")
    print("=" * 60)
    
    stats = get_team_fielding_stats_pybaseball("Boston Red Sox", 2024)
    
    print(f"Available: {stats.get('available')}")
    print(f"Games: {stats.get('games')}")
    print(f"Errors: {stats.get('errors')}")
    print(f"Fld%: {stats.get('fieldingPercentage')}")
    print(f"Source: {stats.get('source')}")
    print()


def test_recent_stats():
    """Test recent stats calculation."""
    
    print("=" * 60)
    print("TEST 4: Recent Stats (Braves, last 14 days before 2024-04-15)")
    print("=" * 60)
    
    stats = get_team_recent_stats_pybaseball(
        "Atlanta Braves",
        2024,
        "2024-04-15",
        window_days=14
    )
    
    print(f"Available: {stats.get('available')}")
    print(f"Games: {stats.get('games')}")
    print(f"Runs/Game: {stats.get('runsPerGame')}")
    print(f"Confidence: {stats.get('confidence')}")
    print(f"Source: {stats.get('source')}")
    print()


if __name__ == "__main__":
    test_batting_stats()
    test_pitching_stats()
    test_fielding_stats()
    test_recent_stats()
    
    print("=" * 60)
    print("✅ All pybaseball tests completed!")
    print("=" * 60)