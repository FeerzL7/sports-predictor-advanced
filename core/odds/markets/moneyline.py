# core/odds/markets/moneyline.py

import math
from typing import Dict, Any, Optional


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
    Convierte diferencia de carreras proyectadas
    en probabilidad de victoria usando función logística.
    """
    return 1 / (1 + math.exp(-run_diff / scale))


def evaluate_moneyline_market(
    analysis: Dict[str, Any],
    min_edge: float = 0.03,
    min_confidence: float = 0.55
) -> Optional[Dict[str, Any]]:
    """
    Evalúa mercado Moneyline y devuelve pick si hay valor real.
    Edge = Prob_modelo - Prob_implícita
    """

    market = analysis.get("market", {}).get("moneyline")
    projections = analysis.get("projections")
    system_conf = analysis.get("confidence", 0)

    if not market or not projections or system_conf < min_confidence:
        return None

    home_runs = projections.get("home_runs")
    away_runs = projections.get("away_runs")

    if home_runs is None or away_runs is None:
        return None

    # =========================
    # Probabilidad del modelo
    # =========================
    run_diff = home_runs - away_runs
    prob_home = logistic_probability(run_diff)
    prob_away = 1 - prob_home

    # =========================
    # Probabilidad implícita
    # =========================
    home_data = market.get("home")
    away_data = market.get("away")

    if not home_data or not away_data:
        return None

    home_odds = home_data.get("odds")
    away_odds = away_data.get("odds")

    if home_odds is None or away_odds is None:
        return None

    imp_home = implied_probability_moneyline(home_odds)
    imp_away = implied_probability_moneyline(away_odds)

    # =========================
    # Edge real
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
            "reason": "Model probability exceeds implied odds"
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
            "reason": "Model probability exceeds implied odds"
        }

    return best_pick
