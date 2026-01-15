import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from core.odds.markets.totals import evaluate_totals_market

analysis = {
    "proj_total": 6.9,
    "projection_confidence": 0.70,
    "market": {
        "total": {
            "line": 8.0,
            "odds_over": 1.85,
            "odds_under": 2.05
        }
    }
}

pick = evaluate_totals_market(analysis)
print(pick)


