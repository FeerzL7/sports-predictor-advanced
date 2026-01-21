# core/odds/markets/moneyline.py

from typing import Dict, Any, Optional

from core.odds.models.monte_carlo_ml import monte_carlo_moneyline
from core.odds.models.ml_totals_correlation import (
    ml_totals_correlation_adjustment
)

# =========================
# Helpers
# =========================

def implied_probability_moneyline(odds: int) -> float:
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)


def normalize_edge(model_prob: float, implied_prob: float) -> float:
    """
    Edge normalizado:
    > positivo = valor real
    > comparable entre favoritos y underdogs
    """
    if implied_prob <= 0 or implied_prob >= 1:
        return 0.0
    return (model_prob - implied_prob) / implied_prob


def apply_low_sample_penalty(
    probability: float,
    flags: list,
    penalty_per_flag: float = 0.035,
    max_penalty: float = 0.12
) -> float:
    low_quality_flags = [
        f for f in flags
        if "LOW_SAMPLE" in f or "NO_H2H" in f or "NO_RECENT" in f
    ]

    penalty = min(len(low_quality_flags) * penalty_per_flag, max_penalty)
    adjusted = probability * (1 - penalty)

    return max(min(adjusted, 0.95), 0.05)


# =========================
# Main Evaluator
# =========================

def evaluate_moneyline_market(
    analysis: Dict[str, Any],
    min_edge: float = 0.04,
    min_confidence: float = 0.55
) -> Optional[Dict[str, Any]]:

    market = analysis.get("market", {}).get("moneyline")
    system_conf = analysis.get("confidence", 0)
    flags = analysis.get("flags", [])

    if not market or system_conf < min_confidence:
        return None

    # =========================
    # Monte Carlo ML (CORE)
    # =========================
    mc_result = monte_carlo_moneyline(analysis)

    prob_home = mc_result.get("home_win_prob")
    prob_away = mc_result.get("away_win_prob")

    if prob_home is None or prob_away is None:
        return None

    # =========================
    # Penalización por data pobre
    # =========================
    prob_home = apply_low_sample_penalty(prob_home, flags)
    prob_away = 1 - prob_home

    # =========================
    # Odds
    # =========================
    home_odds = market.get("home", {}).get("odds")
    away_odds = market.get("away", {}).get("odds")

    if home_odds is None or away_odds is None:
        return None

    imp_home = implied_probability_moneyline(home_odds)
    imp_away = implied_probability_moneyline(away_odds)

    edge_home = normalize_edge(prob_home, imp_home)
    edge_away = normalize_edge(prob_away, imp_away)

    best_pick = None
    best_edge = min_edge

    # =========================
    # Pick HOME
    # =========================
    if edge_home >= best_edge:
        best_edge = edge_home
        best_pick = {
            "market": "moneyline",
            "side": "home",
            "team": analysis["teams"]["home"],
            "odds": home_odds,
            "model_prob": round(prob_home, 3),
            "implied_prob": round(imp_home, 3),
            "edge": round(edge_home, 3),
            "confidence": round((system_conf + prob_home) / 2, 3),
            "reason": "Monte Carlo ML (starter + bullpen, 7–9 innings), adjusted for data quality"
        }

    # =========================
    # Pick AWAY
    # =========================
    if edge_away >= best_edge:
        best_pick = {
            "market": "moneyline",
            "side": "away",
            "team": analysis["teams"]["away"],
            "odds": away_odds,
            "model_prob": round(prob_away, 3),
            "implied_prob": round(imp_away, 3),
            "edge": round(edge_away, 3),
            "confidence": round((system_conf + prob_away) / 2, 3),
            "reason": "Monte Carlo ML (starter + bullpen, 7–9 innings), adjusted for data quality"
        }

    if not best_pick:
        return None

    # =========================
    # Correlación ML ↔ Totals
    # =========================
    corr = ml_totals_correlation_adjustment(best_pick, analysis)

    best_pick["edge"] = round(
        best_pick["edge"] * corr["edge_multiplier"], 3
    )

    best_pick["confidence"] = round(
        best_pick["confidence"] * corr["confidence_multiplier"], 3
    )

    best_pick["correlation_reason"] = corr["reason"]

    return best_pick
