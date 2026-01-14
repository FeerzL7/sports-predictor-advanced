# --------------------------
# Odds / Betting
# --------------------------
MARKETS_DEFAULT = "h2h,totals,spreads"

UMBRAL_VALOR_ML = 5
UMBRAL_VALOR_RL = 7
UMBRAL_VALOR_TOTAL = 4

UMBRAL_MOSTRAR_STAKE_ML = 5
UMBRAL_MOSTRAR_STAKE_RL = 6
UMBRAL_MOSTRAR_STAKE_TOTAL = 4

KELLY_FRACTION_GLOBAL = 0.5
KELLY_CAP = 0.05

# --------------------------
# Simulations
# --------------------------
N_SIM = 100_000
USE_MONTE_CARLO = True
USE_NEGBIN_TOTALS = True
K_NEGBIN = 15.0
MAX_RUNS_SUM = 20
