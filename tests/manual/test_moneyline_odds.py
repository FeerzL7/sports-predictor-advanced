# tests/manual/test_moneyline_odds.py

from core.odds.markets.moneyline import evaluate_moneyline_market
from core.odds.models.monte_carlo_ml import monte_carlo_moneyline

# Test con odds DECIMALES (formato real de OddsAPI)
analysis_decimal = {
    "teams": {"home": "Yankees", "away": "Red Sox"},
    "market": {
        "moneyline": {
            "home": 1.85,  # Decimal
            "away": 2.05   # Decimal
        }
    },
    "projections": {
        "home_runs": 4.5,
        "away_runs": 4.0
    },
    "analysis": {
        "pitching": {
            "home": {},
            "away": {},
            "home_bullpen": {"bullpen_era_adj": 3.84},
            "away_bullpen": {"bullpen_era_adj": 3.65}
        }
    },
    "confidence": 0.70,
    "flags": []
}

# Test con odds AMERICANOS (formato de FakeProvider)
analysis_american = {
    "teams": {"home": "Yankees", "away": "Red Sox"},
    "market": {
        "moneyline": {
            "home": -140,  # Americano
            "away": +120   # Americano
        }
    },
    "projections": {
        "home_runs": 4.5,
        "away_runs": 4.0
    },
    "analysis": {
        "pitching": {
            "home": {},
            "away": {},
            "home_bullpen": {"bullpen_era_adj": 3.84},
            "away_bullpen": {"bullpen_era_adj": 3.65}
        }
    },
    "confidence": 0.70,
    "flags": []
}

print("=" * 60)
print("TEST 1: Odds DECIMALES (OddsAPI format)")
print("=" * 60)

# Debug Monte Carlo
mc_result_1 = monte_carlo_moneyline(analysis_decimal)
print(f"[DEBUG] Monte Carlo Result:")
print(f"  Home Win Prob: {mc_result_1['home_win_prob']}")
print(f"  Away Win Prob: {mc_result_1['away_win_prob']}")
print(f"  Bullpen ERA Home: {mc_result_1.get('bullpen_era_home', 'N/A')}")
print(f"  Bullpen ERA Away: {mc_result_1.get('bullpen_era_away', 'N/A')}")
print()

pick_decimal = evaluate_moneyline_market(analysis_decimal)
if pick_decimal:
    print(f"✅ PICK GENERATED:")
    print(f"  Team: {pick_decimal['team']}")
    print(f"  Odds: {pick_decimal['odds']} ({pick_decimal['odds_format']})")
    print(f"  Model Prob: {pick_decimal['model_prob']}")
    print(f"  Implied Prob: {pick_decimal['implied_prob']}")
    print(f"  Edge: {pick_decimal['edge']} ({pick_decimal['edge']*100:.1f}%)")
    print(f"  Confidence: {pick_decimal['confidence']}")
else:
    print("❌ No pick generated")

print("\n" + "=" * 60)
print("TEST 2: Odds AMERICANOS (FakeProvider format)")
print("=" * 60)

# Debug Monte Carlo
mc_result_2 = monte_carlo_moneyline(analysis_american)
print(f"[DEBUG] Monte Carlo Result:")
print(f"  Home Win Prob: {mc_result_2['home_win_prob']}")
print(f"  Away Win Prob: {mc_result_2['away_win_prob']}")
print(f"  Bullpen ERA Home: {mc_result_2.get('bullpen_era_home', 'N/A')}")
print(f"  Bullpen ERA Away: {mc_result_2.get('bullpen_era_away', 'N/A')}")
print()

# Debug odds conversion
from core.odds.utils.odds_converter import (
    normalize_odds_to_decimal,
    implied_probability_from_decimal
)

try:
    home_odds_decimal = normalize_odds_to_decimal(-140)
    away_odds_decimal = normalize_odds_to_decimal(+120)
    
    print(f"[DEBUG] Odds Conversion:")
    print(f"  Home: -140 → {home_odds_decimal:.3f}")
    print(f"  Away: +120 → {away_odds_decimal:.3f}")
    
    imp_home = implied_probability_from_decimal(home_odds_decimal)
    imp_away = implied_probability_from_decimal(away_odds_decimal)
    
    print(f"[DEBUG] Implied Probabilities:")
    print(f"  Home: {imp_home:.3f} ({imp_home*100:.1f}%)")
    print(f"  Away: {imp_away:.3f} ({imp_away*100:.1f}%)")
    
    print(f"[DEBUG] Edges:")
    print(f"  Home: {mc_result_2['home_win_prob']} - {imp_home:.3f} = {mc_result_2['home_win_prob'] - imp_home:.3f}")
    print(f"  Away: {mc_result_2['away_win_prob']} - {imp_away:.3f} = {mc_result_2['away_win_prob'] - imp_away:.3f}")
    
except Exception as e:
    print(f"[ERROR] Odds conversion failed: {e}")

print()

pick_american = evaluate_moneyline_market(analysis_american)
if pick_american:
    print(f"✅ PICK GENERATED:")
    print(f"  Team: {pick_american['team']}")
    print(f"  Odds: {pick_american['odds']} ({pick_american['odds_format']})")
    print(f"  Model Prob: {pick_american['model_prob']}")
    print(f"  Implied Prob: {pick_american['implied_prob']}")
    print(f"  Edge: {pick_american['edge']} ({pick_american['edge']*100:.1f}%)")
    print(f"  Confidence: {pick_american['confidence']}")
else:
    print("❌ No pick generated (likely edge < 4% threshold)")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Min Edge Threshold: 4.0%")
print(f"Both tests use same projections (Home: 4.5, Away: 4.0)")
print(f"TEST 1 has +EV because odds are worse (1.85 vs 1.71)")
print(f"TEST 2 might have -EV because odds are better (1.71 = stronger favorite)")