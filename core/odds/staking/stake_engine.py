# core/odds/staking/stake_engine.py

from core.odds.staking.kelly import fractional_kelly
from core.odds.staking.correlation_stake import correlation_stake_multiplier


def calculate_stake(
    pick: dict,
    bankroll: float,
    totals_pick: dict | None = None
) -> dict:

    odds = abs(pick["odds"]) / 100 + 1 if pick["odds"] < 0 else pick["odds"] / 100 + 1
    model_prob = pick["model_prob"]

    base_stake_pct = fractional_kelly(
        odds=odds,
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
