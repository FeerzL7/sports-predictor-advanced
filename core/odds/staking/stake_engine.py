# core/odds/staking/stake_engine.py

from core.odds.staking.kelly import fractional_kelly
from core.odds.staking.correlation_stake import correlation_stake_multiplier


def calculate_stake(
    pick: dict,
    bankroll: float,
    totals_pick: dict | None = None
) -> dict:
    
    # ✨ NUEVO: odds ya vienen en decimal desde evaluate_moneyline_market
    odds_decimal = pick.get("odds")
    
    # Validar que sean decimales válidos
    if odds_decimal is None or odds_decimal <= 1.0:
        pick["stake_pct"] = 0.0
        pick["stake"] = 0.0
        pick["stake_reason"] = "Invalid odds"
        return pick
    
    model_prob = pick["model_prob"]

    base_stake_pct = fractional_kelly(
        odds=odds_decimal,  # ✨ Ya es decimal
        model_prob=model_prob,
        fraction=0.25
    )

    corr = correlation_stake_multiplier(pick, totals_pick)

    final_stake_pct = base_stake_pct * corr["multiplier"]
    final_stake = bankroll * final_stake_pct

    pick["stake_pct"] = round(final_stake_pct, 4)
    pick["stake"] = round(final_stake, 2)
    pick["stake_reason"] = corr["reason"]

    return pick