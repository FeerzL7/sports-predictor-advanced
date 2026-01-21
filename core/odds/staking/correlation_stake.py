# core/odds/staking/correlation_stake.py

from typing import Dict


def correlation_stake_multiplier(
    ml_pick: Dict,
    totals_pick: Dict | None
) -> Dict[str, float]:
    """
    Devuelve multiplicadores de stake según correlación ML ↔ Totals
    """

    if not ml_pick or not totals_pick:
        return {
            "multiplier": 1.0,
            "reason": "No correlated market"
        }

    ml_side = ml_pick["side"]
    total_side = totals_pick["side"]

    # Correlaciones típicas
    positive_corr = (
        (ml_side == "home" and total_side == "over") or
        (ml_side == "away" and total_side == "over")
    )

    negative_corr = (
        (ml_side == "home" and total_side == "under") or
        (ml_side == "away" and total_side == "under")
    )

    if positive_corr:
        return {
            "multiplier": 0.75,
            "reason": "Positive ML ↔ Totals correlation (shared scoring dominance)"
        }

    if negative_corr:
        return {
            "multiplier": 0.70,
            "reason": "Negative ML ↔ Totals correlation (pace suppression)"
        }

    return {
        "multiplier": 1.0,
        "reason": "No meaningful correlation detected"
    }
