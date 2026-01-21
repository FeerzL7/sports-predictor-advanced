import random
import numpy as np


def monte_carlo_ml(
    home_runs: float,
    away_runs: float,
    bullpen_home_era: float,
    bullpen_away_era: float,
    simulations: int = 5000,
    league_era: float = 4.20
) -> float:
    home_wins = 0

    for _ in range(simulations):
        # 1–6 innings
        h_1_6 = np.random.poisson(home_runs * 0.65)
        a_1_6 = np.random.poisson(away_runs * 0.65)

        # 7–9 innings (bullpen)
        h_7_9 = np.random.poisson((bullpen_away_era / league_era) * 3)
        a_7_9 = np.random.poisson((bullpen_home_era / league_era) * 3)

        total_home = h_1_6 + h_7_9
        total_away = a_1_6 + a_7_9

        if total_home > total_away:
            home_wins += 1

    return home_wins / simulations
