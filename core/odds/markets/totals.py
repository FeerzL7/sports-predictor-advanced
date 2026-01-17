# core/odds/markets/totals.py

from typing import Dict, Any, Optional
from math import log

# -------------------------
# Configuración base
# -------------------------
MIN_EDGE = 0.02          # edge mínimo para considerar apuesta
MIN_CONFIDENCE = 0.55    # confianza mínima del modelo

# -------------------------
# Helpers
# -------------------------
def implied_prob(odds: float) -> float:
    """Probabilidad implícita desde momio decimal"""
    if odds <= 1:
        return 0.0
    return 1.0 / odds

def edge(model_prob: float, odds: float) -> float:
    """Edge = ventaja vs casa"""
    return model_prob - implied_prob(odds)

# -------------------------
# Core logic
# -------------------------
def evaluate_totals_market(analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Evalúa mercado de Totales (Over / Under).
    Devuelve pick o None.
    """

    proj_total = analysis.get("proj_total")
    conf = analysis.get("projection_confidence", 0)

    market_root = analysis.get("market") or {}
    market = market_root.get("total", {})

    line = market.get("line")
    odds_over = market.get("odds_over")
    odds_under = market.get("odds_under")

    if proj_total is None or line is None:
        return None

    if conf < MIN_CONFIDENCE:
        return None

    # Probabilidad modelo (logística simple)
    diff = proj_total - line
    model_prob_over = 1 / (1 + pow(2.71828, -diff))
    model_prob_under = 1 - model_prob_over

    best_pick = None
    best_edge = 0.0

    if odds_over:
        e = edge(model_prob_over, odds_over)
        if e > best_edge and e >= MIN_EDGE:
            best_edge = e
            best_pick = {
                "market": "TOTAL",
                "side": "OVER",
                "line": line,
                "odds": odds_over,
                "model_prob": round(model_prob_over, 3),
                "edge": round(e, 3),
                "confidence": round(conf, 3),
            }

    if odds_under:
        e = edge(model_prob_under, odds_under)
        if e > best_edge and e >= MIN_EDGE:
            best_edge = e
            best_pick = {
                "market": "TOTAL",
                "side": "UNDER",
                "line": line,
                "odds": odds_under,
                "model_prob": round(model_prob_under, 3),
                "edge": round(e, 3),
                "confidence": round(conf, 3),
            }

    return best_pick
