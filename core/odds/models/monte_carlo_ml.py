# core/odds/models/monte_carlo_ml.py

import random
from typing import Dict, Any


def simulate_inning(run_mean: float) -> float:
    """
    Simula carreras en un inning usando Poisson aproximado.
    """
    runs = 0
    p = random.random()
    threshold = run_mean / 9  # distribución básica por inning

    if p < threshold:
        runs += 1
        if random.random() < 0.25:
            runs += 1
        if random.random() < 0.1:
            runs += 1

    return runs


def monte_carlo_moneyline(
    analysis: Dict[str, Any],
    simulations: int = 10000
) -> Dict[str, float]:
    """
    Simula partidos completos (1–9 innings) y devuelve
    probabilidad real de victoria.
    """

    proj = analysis.get("projections", {})
    if not proj:
        return {"home_win_prob": 0.5, "away_win_prob": 0.5}

    home_mean = proj.get("home_runs", 0)
    away_mean = proj.get("away_runs", 0)

    if home_mean == 0 or away_mean == 0:
        return {"home_win_prob": 0.5, "away_win_prob": 0.5}

    # ✨ NUEVO: Obtener bullpen_era REAL (con fallback a adjusted)
    pitching = analysis.get("analysis", {}).get("pitching", {})
    
    home_bullpen_data = pitching.get("home_bullpen", {})
    away_bullpen_data = pitching.get("away_bullpen", {})
    
    bullpen_home = (
        home_bullpen_data.get("bullpen_era_adj") or
        home_bullpen_data.get("bullpen_era") or
        4.20
    )
    
    bullpen_away = (
        away_bullpen_data.get("bullpen_era_adj") or
        away_bullpen_data.get("bullpen_era") or
        4.20
    )

    # Ajuste bullpen → menor ERA = menos carreras permitidas
    # Home offense se beneficia si bullpen rival (away) es malo
    bullpen_adj_home = max(0.8, min(1.2, bullpen_away / 4.20))
    bullpen_adj_away = max(0.8, min(1.2, bullpen_home / 4.20))

    home_wins = 0
    away_wins = 0

    for _ in range(simulations):
        home_runs = 0
        away_runs = 0

        # Innings 1–6 (abridores)
        for _ in range(6):
            home_runs += simulate_inning(home_mean)
            away_runs += simulate_inning(away_mean)

        # Innings 7–9 (bullpen) ✨ AHORA USA BULLPEN REAL
        for _ in range(3):
            home_runs += simulate_inning(home_mean * bullpen_adj_home)
            away_runs += simulate_inning(away_mean * bullpen_adj_away)

        if home_runs > away_runs:
            home_wins += 1
        elif away_runs > home_runs:
            away_wins += 1
        else:
            # extra innings → coin flip ponderado
            if random.random() < 0.5:
                home_wins += 1
            else:
                away_wins += 1

    total = home_wins + away_wins

    return {
        "home_win_prob": round(home_wins / total, 4),
        "away_win_prob": round(away_wins / total, 4),
        "mean_run_diff": round(home_mean - away_mean, 3),
        # ✨ DEBUG: Incluir bullpen usado
        "bullpen_era_home": round(bullpen_home, 2),
        "bullpen_era_away": round(bullpen_away, 2)
    }