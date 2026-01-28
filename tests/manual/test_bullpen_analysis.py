# tests/manual/test_bullpen_analysis.py

from sports.baseball.mlb.analysis.bullpen import build_bullpen_metrics

# Test con varios equipos
teams = ["Yankees", "Red Sox", "Dodgers"]

for team_name in teams:
    bullpen = build_bullpen_metrics(team_name)
    
    print("=" * 60)
    print(f"BULLPEN: {bullpen.team} (Season {bullpen.season})")
    print("=" * 60)
    print(f"ERA: {bullpen.bullpen_era} (adj: {bullpen.bullpen_era_adj})")
    print(f"WHIP: {bullpen.bullpen_whip}")
    print(f"K/9: {bullpen.bullpen_k9}")
    print(f"BB/9: {bullpen.bullpen_bb9}")
    print(f"Total IP: {bullpen.total_innings_pitched}")
    print(f"High Leverage ERA: {bullpen.high_leverage_era}")
    print(f"Confidence: {bullpen.confidence}")
    print(f"Flags: {bullpen.flags}")
    print(f"Missing: {bullpen.missing_fields}")
    print()
