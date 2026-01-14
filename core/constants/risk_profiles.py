RISK_PROFILES = {
    "conservador": {
        "DELTA_EV_MIN": 3.0,
        "DELTA_PROB_MAX": 0.02,
        "STAKE_RL_MULT": 1.10,
        "PROB_MIN_TOP": 0.56
    },
    "balanceado": {
        "DELTA_EV_MIN": 2.0,
        "DELTA_PROB_MAX": 0.03,
        "STAKE_RL_MULT": 1.25,
        "PROB_MIN_TOP": 0.54
    },
    "agresivo": {
        "DELTA_EV_MIN": 1.2,
        "DELTA_PROB_MAX": 0.05,
        "STAKE_RL_MULT": 1.50,
        "PROB_MIN_TOP": 0.52
    }
}

ACTIVE_RISK_PROFILE = "none"
