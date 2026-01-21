# core/odds/markets/moneyline.py

import math
from typing import Dict, Any, Optional


# =========================
# Helpers
# =========================

def implied_probability_moneyline(odds: int) -> float:
    """
    Convierte momio americano a probabilidad implícita.
    """
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    else:
        return 100 / (odds + 100)


def logistic_probability(run_diff: float, scale: float = 1.6) -> float:
    """
    Convierte diferencia de carreras en probabilidad de victoria.
    """
    return 1 / (1 + math.exp(-run_diff / scale))


def apply_home_field_adjustment(
    run_diff: float,
    is_home: bool,
    adjustment: float = 0.18
) -> float:
    """
    Ajuste conservador de localía en términos de carreras.
    """
    if is_home:
        return run_diff + adjustment
    return run_diff


def apply_low_sample_penalty(
    probability: float,
    flags: list,
    penalty_per_flag: float = 0.035,
    max_penalty: float = 0.12
) -> float:
    """
    Penaliza probabilidad por flags de baja confiabilidad.
    """
    low_quality_flags = [
        f for f in flags
        if "LOW_SAMPLE" in f
        or "NO_H2H" in f
        or "NO_RECENT" in f
    ]

    penalty = min(len(low_quality_flags) * penalty_per_flag, max_penalty)
    adjusted = probability * (1 - penalty)

    return max(min(adjusted, 0.95), 0.05)


# =========================
# Main Evaluator
# =========================

def evaluate_moneyline_market(
    analysis: Dict[str, Any],
    min_edge: float = 0.03,
    min_confidence: float = 0.55
) -> Optional[Dict[str, Any]]:
    """
    Evalúa Moneyline con:
    - Ajuste real de localía
    - Penalización por baja muestra
    """

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
    # Probabilidad base modelo
    # =========================
    base_run_diff = home_runs - away_runs

    # Ajuste localía
    run_diff_home = apply_home_field_adjustment(
        base_run_diff,
        is_home=True
    )

    prob_home = logistic_probability(run_diff_home)
    prob_away = 1 - prob_home

    # Penalización por baja calidad de datos
    prob_home = apply_low_sample_penalty(prob_home, flags)
    prob_away = apply_low_sample_penalty(prob_away, flags)

    # =========================
    # Probabilidad implícita
    # =========================
    home_odds = market.get("home", {}).get("odds")
    away_odds = market.get("away", {}).get("odds")

    if home_odds is None or away_odds is None:
        return None

    imp_home = implied_probability_moneyline(home_odds)
    imp_away = implied_probability_moneyline(away_odds)

    # =========================
    # Edge
    # =========================
    edge_home = prob_home - imp_home
    edge_away = prob_away - imp_away

    best_pick = None
    best_edge = min_edge

    # =========================
    # HOME
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
            "reason": "Home edge after venue and data-quality adjustment"
        }

    # =========================
    # AWAY
    # =========================
    if edge_away >= best_edge:
        best_edge = edge_away
        best_pick = {
            "market": "moneyline",
            "side": "away",
            "team": analysis["teams"]["away"],
            "odds": away_odds,
            "model_prob": round(prob_away, 3),
            "implied_prob": round(imp_away, 3),
            "edge": round(edge_away, 3),
            "confidence": round((system_conf + prob_away) / 2, 3),
            "reason": "Away edge after venue and data-quality adjustment"
        }

    return best_pick
