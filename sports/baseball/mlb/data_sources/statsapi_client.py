from typing import Dict, Any, Optional
import time

from statsapi import get


# =========================
# SAFE CASTS (ÚNICA FUENTE)
# =========================

def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


# =========================
# CORE CLIENT
# =========================

def statsapi_get(
    endpoint: str,
    params: Dict[str, Any],
    retries: int = 2,
    sleep: float = 0.25
) -> Dict[str, Any]:
    """
    Wrapper robusto alrededor de statsapi.get

    - Retries automáticos
    - Respuesta SIEMPRE dict o excepción clara
    - No imprime, no loggea, no decide
    """

    last_error: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            resp = get(endpoint, params)

            if isinstance(resp, dict):
                return resp

            raise ValueError(f"Invalid response type: {type(resp)}")

        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(sleep)

    raise RuntimeError(
        f"StatsAPI failed after {retries + 1} attempts: {last_error}"
    )
