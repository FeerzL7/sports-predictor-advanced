# core/odds/staking/kelly.py

def fractional_kelly(
    odds: float,
    model_prob: float,
    fraction: float = 0.25,
    cap: float = 0.05
) -> float:
    """
    Kelly fraccional con cap de riesgo.
    Devuelve % del bankroll.
    """

    b = odds - 1
    q = 1 - model_prob

    kelly = (b * model_prob - q) / b

    if kelly <= 0:
        return 0.0

    stake = kelly * fraction
    return min(stake, cap)
