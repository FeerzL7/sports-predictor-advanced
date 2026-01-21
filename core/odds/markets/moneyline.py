# core/odds/markets/moneyline.py

import math
from typing import Dict, Any, Optional


# =========================
# Helpers
# =========================

def implied_probability_moneyline(odds: int) -> float:
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)


def logistic_probability(run_diff: float, scale: float = 1.6) -> float:
    return 1 / (1 + math.exp(-run_diff / scale))


def normalize_edge(model_prob: float, implied_prob: float) -> float:
    """
    Edge normalizado:
    > positivo = valor real
    > comparable entre favoritos y dogs
    """
    if implied_prob <= 0 or implied_prob >= 1:
        return 0.0
    return (model_prob - implied_prob) / implied_prob


def apply_home_field_adjustment(
    run_diff: float,
    is_home: bool,
    adjustment: float = 0.18
) -> float:
    if not is_home:
        return run_diff
    return run_diff + adjustment


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


def bullpen_run_adjustment(
    bullpen_home: float,
    bullpen_away: float,
    weight: float = 0.35,
    cap: float = 0.25
) -> float:
    if bullpen_home is None or bullpen_away is None:
        return 0.0

    diff = bullpen_away - bullpen_home
    adj = diff * weight

    return max(min(adj, cap), -cap)


# =========================
# Main Evaluator
# =========================

def evaluate_moneyline_market(
    analysis: Dict[str, Any],
    min_edge: float = 0.04,
    min_confidence: float = 0.55
) -> Optional[Dict[str, Any]]:

    market = analysis.get("market", {}).get("moneyline")
    projections = analysis.get("projections")
    system_conf = analysis.get("confidence", 0)
    flags = analysis.get("flags", [])

    if not market or not projections or system_conf < min_confidence:
        return None

    home_runs = projections.get("home_runs")
    away_runs = projections.get("away_runs")

    if home_runs is None or away_runs is None:
        return None

    # =========================
    # Base run diff
    # =========================
    run_diff = home_runs - away_runs

    # =========================
    # Localía real
    # =========================
    context_home = (
        analysis.get("analysis", {})
        .get("context", {})
        .get("home", {})
    )

    is_home = bool(context_home)
    run_diff = apply_home_field_adjustment(run_diff, is_home)

    # =========================
    # Bullpen adjustment
    # =========================
    pitching = analysis.get("analysis", {}).get("pitching", {})
    bullpen_home = pitching.get("home", {}).get("bullpen_era")
    bullpen_away = pitching.get("away", {}).get("bullpen_era")

    run_diff += bullpen_run_adjustment(bullpen_home, bullpen_away)

    # =========================
    # Modelo base (logístico)
    # =========================
    prob_home = logistic_probability(run_diff)
    prob_away = 1 - prob_home

    # =========================
    # Penalización data pobre (una vez)
    # =========================
    prob_home = apply_low_sample_penalty(prob_home, flags)
    prob_away = 1 - prob_home

    # =========================
    # Implícitas
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
            "reason": "Normalized edge after home field, bullpen and data quality adjustments"
        }

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
            "reason": "Normalized edge after bullpen and data quality adjustments"
        }

    return best_pick
