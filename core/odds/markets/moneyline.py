# core/odds/markets/moneyline.py

from typing import Dict, Any, Optional
from math import exp

# =========================
# Configuración
# =========================
MIN_EDGE = 0.03
MIN_CONFIDENCE = 0.55
LOGISTIC_K = 0.65  # sensibilidad MLB


# =========================
# Helpers
# =========================
def implied_prob(odds: float) -> float:
    if not odds or odds <= 1:
        return 0.0
    return 1.0 / odds


def edge(model_prob: float, odds: float) -> float:
    return model_prob - implied_prob(odds)


def win_probability(diff: float) -> float:
    """
    Convierte diferencia de carreras esperadas
    en probabilidad de victoria.
    """
    return 1.0 / (1.0 + exp(-LOGISTIC_K * diff))


# =========================
# Core Evaluator
# =========================
def evaluate_moneyline_market(
    analysis: Dict[str, Any]
) -> Optional[Dict[str, Any]]:

    if not analysis:
        return None

    conf = analysis.get("confidence", 0.0)
    if conf < MIN_CONFIDENCE:
        return None

    projections = analysis.get("projections", {})
    home_runs = projections.get("home_runs")
    away_runs = projections.get("away_runs")

    if home_runs is None or away_runs is None:
        return None

    market = analysis.get("market", {}).get("moneyline", {})
    odds_home = market.get("home")
    odds_away = market.get("away")

    if not odds_home and not odds_away:
        return None

    diff = home_runs - away_runs

    prob_home = win_probability(diff)
    prob_away = 1.0 - prob_home

    best_pick = None
    best_edge = 0.0

    if odds_home:
        e = edge(prob_home, odds_home)
        if e >= MIN_EDGE and e > best_edge:
            best_edge = e
            best_pick = {
                "market": "MONEYLINE",
                "side": "HOME",
                "odds": odds_home,
                "model_prob": round(prob_home, 3),
                "edge": round(e, 3),
                "confidence": round(conf, 3),
            }

    if odds_away:
        e = edge(prob_away, odds_away)
        if e >= MIN_EDGE and e > best_edge:
            best_edge = e
            best_pick = {
                "market": "MONEYLINE",
                "side": "AWAY",
                "odds": odds_away,
                "model_prob": round(prob_away, 3),
                "edge": round(e, 3),
                "confidence": round(conf, 3),
            }

    return best_pick
