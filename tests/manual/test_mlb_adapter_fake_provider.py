from sports.baseball.mlb.adapter import MLBAdapter
from core.odds.providers.fake_provider import FakeOddsProvider
from tests.fixtures.mlb_event_sample import SAMPLE_MLB_EVENT

adapter = MLBAdapter(
    odds_provider=FakeOddsProvider(
        total_line=8.5,
        ml_home=-140,
        ml_away=+125
    )
)

analysis = adapter.analyze_event(SAMPLE_MLB_EVENT)
picks = adapter.generate_picks(analysis)

print("\nANALYSIS:")
print(analysis)

print("\nPICKS:")
print(picks)
