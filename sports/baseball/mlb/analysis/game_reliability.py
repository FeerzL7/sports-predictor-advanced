from typing import Dict, Any, List


# =========================
# CONFIGURACIÓN BASE (MLB)
# =========================

DEFAULT_MODULE_WEIGHTS = {
    "pitching": 0.35,
    "offense": 0.30,
    "context": 0.20,
    "market": 0.15
}

RELIABILITY_THRESHOLDS = {
    "DISCARD": 0.55,     # no se apuesta
    "LOW": 0.65,         # stake mínimo
    "GOOD": 0.75         # modelo completo
}


# =========================
# CORE ENGINE
# =========================

def compute_game_reliability(
    modules: Dict[str, Dict[str, Any]],
    custom_weights: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Calcula score global de confiabilidad del partido.

    modules = {
        "pitching": {"confidence": 0.78, "flags": {...}},
        "offense": {"confidence": 0.82, "flags": {...}},
        "context": {"confidence": 0.70, "flags": {...}},
        "market": {"confidence": 0.90, "flags": {...}},
    }
    """

    weights = custom_weights or DEFAULT_MODULE_WEIGHTS

    total_weight = 0.0
    weighted_score = 0.0
    warnings: List[str] = []

    for module_name, data in modules.items():
        confidence = data.get("confidence", None)
        flags = data.get("flags", {})

        if confidence is None:
            warnings.append(f"{module_name.upper()}_NO_CONFIDENCE")
            continue

        weight = weights.get(module_name, 0.0)

        weighted_score += confidence * weight
        total_weight += weight

        # Flags relevantes → warnings
        for flag, active in flags.items():
            if active:
                warnings.append(f"{module_name.upper()}_{flag.upper()}")

    reliability = weighted_score / total_weight if total_weight > 0 else 0.0
    reliability = round(reliability, 3)

    tier = _reliability_tier(reliability)

    return {
        "reliability": reliability,
        "tier": tier,
        "usable": tier != "DISCARD",
        "warnings": sorted(set(warnings))
    }


# =========================
# HELPERS
# =========================

def _reliability_tier(score: float) -> str:
    if score < RELIABILITY_THRESHOLDS["DISCARD"]:
        return "DISCARD"
    if score < RELIABILITY_THRESHOLDS["LOW"]:
        return "LOW"
    if score < RELIABILITY_THRESHOLDS["GOOD"]:
        return "MEDIUM"
    return "HIGH"


# =========================
# MLB ADAPTER
# =========================

def build_mlb_reliability_input(partido: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Traduce el output MLB a formato estándar para el motor.
    """

    modules = {}

    # Pitching
    home_p = partido.get("home_stats", {})
    away_p = partido.get("away_stats", {})

    pitching_conf = min(
        home_p.get("confidence", 0.0),
        away_p.get("confidence", 0.0)
    )

    modules["pitching"] = {
        "confidence": pitching_conf,
        "flags": {
            "tbd": home_p.get("flags", {}).get("tbd") or away_p.get("flags", {}).get("tbd"),
            "low_sample": home_p.get("flags", {}).get("low_sample") or away_p.get("flags", {}).get("low_sample"),
            "fatigue": home_p.get("fatigue_flag") or away_p.get("fatigue_flag")
        }
    }

    # Offense
    home_o = partido.get("home_offense", {})
    away_o = partido.get("away_offense", {})

    offense_conf = min(
        home_o.get("confidence", 0.0),
        away_o.get("confidence", 0.0)
    )

    modules["offense"] = {
        "confidence": offense_conf,
        "flags": {
            "no_recent": home_o.get("flags", {}).get("no_recent") or away_o.get("flags", {}).get("no_recent"),
            "no_splits": home_o.get("flags", {}).get("no_splits") or away_o.get("flags", {}).get("no_splits"),
            "low_sample": home_o.get("flags", {}).get("low_sample") or away_o.get("flags", {}).get("low_sample")
        }
    }

    # Context
    home_c = partido.get("home_context", {})
    away_c = partido.get("away_context", {})

    context_conf = min(
        home_c.get("confidence", 0.0),
        away_c.get("confidence", 0.0)
    )

    modules["context"] = {
        "confidence": context_conf,
        "flags": {
            "no_weather": home_c.get("clima", {}).get("condiciones") == "desconocido"
                          or away_c.get("clima", {}).get("condiciones") == "desconocido",
            "no_park_factor": home_c.get("flags", {}).get("no_park_factor")
                              or away_c.get("flags", {}).get("no_park_factor")
        }
    }

    # Market (placeholder por ahora)
    modules["market"] = {
        "confidence": partido.get("market_confidence", 0.75),
        "flags": {}
    }

    return modules
