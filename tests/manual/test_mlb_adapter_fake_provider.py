from sports.baseball.mlb.adapter import MLBAdapter
from core.odds.providers.fake_provider import FakeOddsProvider
from tests.fixtures.mlb_event_sample import SAMPLE_MLB_EVENT


def test_mlb_adapter_with_fake_provider():
    # =========================
    # Setup
    # =========================
    adapter = MLBAdapter()
    adapter.odds_provider = FakeOddsProvider()

    # =========================
    # Analysis
    # =========================
    analysis = adapter.analyze_event(SAMPLE_MLB_EVENT)

    print("\nANALYSIS OUTPUT:\n", analysis)

    # =========================
    # Picks
    # =========================
    picks = adapter.generate_picks(analysis)

    print("\nPICKS GENERATED:\n", picks)

    # =========================
    # Assertions mentales 😎
    # =========================
    assert isinstance(analysis, dict)
    assert "market" in analysis
    assert "total" in analysis["market"]
    assert isinstance(picks, list)


if __name__ == "__main__":
    test_mlb_adapter_with_fake_provider()
