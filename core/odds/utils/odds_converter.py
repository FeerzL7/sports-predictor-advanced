# core/odds/utils/odds_converter.py

"""
Utilidades para conversión y cálculo de odds.
Soporta formatos: Decimal, Americano, Fraccionario, Implied Probability
"""

from typing import Union


# =========================
# CONVERSIONES
# =========================

def american_to_decimal(american_odds: int) -> float:
    """
    Convierte odds americanos a decimales.
    
    Ejemplos:
        -150 → 1.67
        +200 → 3.00
    """
    if american_odds == 0:
        raise ValueError("American odds cannot be 0")
    
    if american_odds < 0:
        return (100 / abs(american_odds)) + 1
    else:
        return (american_odds / 100) + 1


def decimal_to_american(decimal_odds: float) -> int:
    """
    Convierte odds decimales a americanos.
    
    Ejemplos:
        1.67 → -150
        3.00 → +200
    """
    if decimal_odds <= 1.0:
        raise ValueError("Decimal odds must be > 1.0")
    
    if decimal_odds >= 2.0:
        # Underdog
        return int((decimal_odds - 1) * 100)
    else:
        # Favorite
        return int(-100 / (decimal_odds - 1))


def implied_probability_from_decimal(decimal_odds: float) -> float:
    """
    Calcula probabilidad implícita desde odds decimales.
    
    Ejemplo:
        2.00 → 0.50 (50%)
        1.85 → 0.541 (54.1%)
    """
    if decimal_odds <= 1.0:
        return 0.0
    
    return 1.0 / decimal_odds


def implied_probability_from_american(american_odds: int) -> float:
    """
    Calcula probabilidad implícita desde odds americanos.
    
    Ejemplo:
        -150 → 0.60 (60%)
        +200 → 0.333 (33.3%)
    """
    if american_odds == 0:
        return 0.0
    
    if american_odds < 0:
        return abs(american_odds) / (abs(american_odds) + 100)
    else:
        return 100 / (american_odds + 100)


def normalize_odds_to_decimal(odds: Union[int, float]) -> float:
    """
    Normaliza cualquier formato de odds a decimal.
    
    Detecta automáticamente:
    - Si es int → Americano
    - Si es float entre 1.0 y 100.0 → Decimal
    
    Ejemplos:
        -150 → 1.67
        -140 → 1.71
        +200 → 3.00
        +120 → 2.20
        1.85 → 1.85
        2.50 → 2.50
    """
    if isinstance(odds, int):
        # Odds americanos (siempre int)
        # ✨ FIX: Remover validación de >= 100
        if odds == 0:
            raise ValueError("American odds cannot be 0")
        return american_to_decimal(odds)
    
    elif isinstance(odds, float):
        # Odds decimales (float entre 1.0 y ~50.0)
        if 1.0 < odds < 100.0:
            return odds
        else:
            raise ValueError(f"Invalid decimal odds: {odds}")
    
    else:
        raise TypeError(f"Odds must be int or float, got {type(odds)}")


# =========================
# HELPERS
# =========================

def calculate_vig(odds1: float, odds2: float) -> float:
    """
    Calcula el vigorish (overround) de un mercado.
    
    Ejemplo:
        odds1=1.95, odds2=1.95
        → implied probs: 51.3% + 51.3% = 102.6%
        → vig = 2.6%
    """
    prob1 = implied_probability_from_decimal(odds1)
    prob2 = implied_probability_from_decimal(odds2)
    
    return (prob1 + prob2) - 1.0


def remove_vig_equal_margin(odds1: float, odds2: float) -> tuple[float, float]:
    """
    Remueve el vig asumiendo margen igual en ambos lados.
    
    Retorna: (true_prob1, true_prob2)
    """
    prob1 = implied_probability_from_decimal(odds1)
    prob2 = implied_probability_from_decimal(odds2)
    
    total = prob1 + prob2
    
    return (prob1 / total, prob2 / total)


def is_positive_ev(
    model_prob: float,
    odds: float,
    min_edge: float = 0.0
) -> bool:
    """
    Determina si una apuesta tiene valor positivo.
    
    Args:
        model_prob: Probabilidad estimada por el modelo (0-1)
        odds: Odds decimales
        min_edge: Edge mínimo requerido (default 0%)
    
    Returns:
        True si model_prob > implied_prob + min_edge
    """
    implied_prob = implied_probability_from_decimal(odds)
    edge = model_prob - implied_prob
    
    return edge >= min_edge


def expected_value(
    model_prob: float,
    odds: float,
    stake: float = 1.0
) -> float:
    """
    Calcula el Expected Value (EV) de una apuesta.
    
    EV = (prob_win * profit) - (prob_loss * stake)
    
    Ejemplo:
        model_prob=0.55, odds=2.0, stake=100
        → EV = (0.55 * 100) - (0.45 * 100) = +10
    """
    profit = stake * (odds - 1)
    loss = stake
    
    return (model_prob * profit) - ((1 - model_prob) * loss)


# =========================
# VALIDACIONES
# =========================

def validate_probability(prob: float) -> bool:
    """Valida que una probabilidad esté en rango [0, 1]."""
    return 0.0 <= prob <= 1.0


def validate_decimal_odds(odds: float) -> bool:
    """Valida que odds decimales sean > 1.0."""
    return odds > 1.0