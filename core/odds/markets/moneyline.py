# core/odds/markets/moneyline.py

import math
from typing import Dict, Any, Optional


def implied_probability(odds: float) -> float:
    """
    Convierte momio decimal a probabilidad implícita.
    """
    if odds <= 1:
        return 0.0
    return 1 / odds


def logistic_probability(run_diff: float, scale: float = 1.6) -> float:
    """
    Convierte diferencia de carreras proyectadas
    en probabilidad de victoria usando logística.
    """
    return 1 / (1 + math.exp(-run_diff / scale))


def evaluate_moneyline_market(
    analysis: Dict[str, Any],
    min_edge: float = 0.03
) -> Optional[Dict[str, Any]]:
    """
    Evalúa mercado Moneyline y devuelve pick si hay valor.
    """

    market = analysis.get("market", {}).get("moneyline")
    projections = analysis.get("projections")

    if not market or not projections:
        return None

    home_runs = projections.get("home_runs")
    away_runs = projections.get("away_runs")

    if home_runs is None or away_runs is None:
        return None

    # =========================
    # Probabilidad proyectada
    # =========================
    run_diff = home_runs - away_runs
    prob_home = logistic_probability(run_diff)
    prob_away = 1 - prob_home

    # =========================
    # Probabilidad implícita
    # =========================
    home_odds = market.get("home", {}).get("odds")
    away_odds = market.get("away", {}).get("odds")

    if not home_odds or not away_odds:
        return None

    imp_home = implied_probability(home_odds)
    imp_away = implied_probability(away_odds)

    # =========================
    # Edge
    # =========================
    edge_home = prob_home - imp_home
    edge_away = prob_away - imp_away

    # =========================
    # Decisión
    # =========================
    if edge_home >= min_edge:
        return {
            "market": "moneyline",
            "side": "home",
            "team": analysis["teams"]["home"],
            "odds": home_odds,
            "probability": round(prob_home, 3),
            "edge": round(edge_home, 3),
            "confidence": round(
                (analysis.get("confidence", 0.5) + prob_home) / 2, 3
            ),
            "reason": "Projected win probability exceeds implied odds"
        }

    if edge_away >= min_edge:
        return {
            "market": "moneyline",
            "side": "away",
            "team": analysis["teams"]["away"],
            "odds": away_odds,
            "probability": round(prob_away, 3),
            "edge": round(edge_away, 3),
            "confidence": round(
                (analysis.get("confidence", 0.5) + prob_away) / 2, 3
            ),
            "reason": "Projected win probability exceeds implied odds"
        }

    return None
