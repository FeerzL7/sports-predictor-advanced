from sports.baseball.mlb.adapter import MLBAdapter
from tests.fixtures.mlb_event_sample import SAMPLE_MLB_EVENT

adapter = MLBAdapter()

analysis = adapter.analyze_event(SAMPLE_MLB_EVENT)
picks = adapter.generate_picks(analysis)

print("ANALYSIS MARKET:", analysis.get("market"))
print("PICKS:", picks)
