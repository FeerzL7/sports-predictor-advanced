# tests/manual/test_bullpen_analysis.py

from sports.baseball.mlb.analysis.bullpen import build_bullpen_metrics

# Test con equipo real
bullpen = build_bullpen_metrics("Yankees")

print("=" * 60)
print(f"BULLPEN: {bullpen.team}")
print("=" * 60)
print(f"ERA: {bullpen.bullpen_era} (adj: {bullpen.bullpen_era_adj})")
print(f"WHIP: {bullpen.bullpen_whip}")
print(f"K/9: {bullpen.bullpen_k9}")
print(f"Total IP: {bullpen.total_innings_pitched}")
print(f"Num Relievers: {bullpen.num_relievers}")
print(f"Recent ERA (7d): {bullpen.recent_era_7d}")
print(f"High Leverage ERA: {bullpen.high_leverage_era}")
print(f"Confidence: {bullpen.confidence}")
print(f"Flags: {bullpen.flags}")
print(f"Missing: {bullpen.missing_fields}")