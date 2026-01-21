# core/odds/models/ml_totals_correlation.py

from typing import Dict, Any


def ml_totals_correlation_adjustment(
    ml_pick: Dict[str, Any],
    analysis: Dict[str, Any],
    max_boost: float = 0.07,
    max_penalty: float = -0.07
) -> Dict[str, Any]:
    """
    Ajusta confianza y edge del Moneyline según correlación con Totals.
    NO modifica probabilidad base.
    """

    projections = analysis.get("projections", {})
    market_total = analysis.get("market", {}).get("total", {})

    proj_total = projections.get("total_runs")
    total_line = market_total.get("line")

    if proj_total is None or total_line is None:
        return {
            "confidence_multiplier": 1.0,
            "edge_multiplier": 1.0,
            "reason": "No totals data available"
        }

    side = ml_pick.get("side")          # home / away
    edge = ml_pick.get("edge", 0)

    delta_total = proj_total - total_line

    # =========================
    # Favorito / Underdog
    # =========================
    is_favorite = edge > 0 and ml_pick.get("odds", 0) < 0
    is_underdog = ml_pick.get("odds", 0) > 0

    boost = 0.0
    reason = "Neutral ML ↔ Totals correlation"

    # =========================
    # Reglas de correlación
    # =========================

    # Favorito + total alto
    if is_favorite and delta_total > 0.6:
        boost = min(max_boost, 0.04 + delta_total * 0.02)
        reason = "Favorite aligned with high-scoring projection"

    # Favorito + total bajo
    elif is_favorite and delta_total < -0.6:
        boost = max(max_penalty, -0.04 + delta_total * 0.02)
        reason = "Favorite in projected low-scoring game (higher variance)"

    # Underdog + total bajo
    elif is_underdog and delta_total < -0.6:
        boost = min(max_boost, 0.035 + abs(delta_total) * 0.02)
        reason = "Underdog aligned with low-scoring projection"

    # Underdog + total alto
    elif is_underdog and delta_total > 0.6:
        boost = max(max_penalty, -0.04 - delta_total * 0.02)
        reason = "Underdog in projected high-scoring game"

    # Clamp final
    boost = max(min(boost, max_boost), max_penalty)

    return {
        "confidence_multiplier": round(1 + boost, 3),
        "edge_multiplier": round(1 + boost, 3),
        "reason": reason
    }
