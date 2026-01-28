# sports/baseball/mlb/data_sources/statsapi_client.py

from typing import Dict, Any, Optional
import time

from statsapi import get
from core.utils.logger import setup_logger, log_api_call, log_error_with_context

# ✨ NUEVO: Setup logger
logger = setup_logger(__name__)


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
    - Logging completo
    """

    # ✨ NUEVO: Log API call
    log_api_call(endpoint, params, logger)

    last_error: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            logger.debug(f"StatsAPI request (attempt {attempt + 1}/{retries + 1}): {endpoint}")
            
            resp = get(endpoint, params)

            if isinstance(resp, dict):
                logger.debug(f"StatsAPI success: {endpoint}")
                return resp

            raise ValueError(f"Invalid response type: {type(resp)}")

        except Exception as e:
            last_error = e
            
            # ✨ NUEVO: Log error
            logger.warning(
                f"StatsAPI attempt {attempt + 1} failed: {endpoint} - {e}"
            )
            
            if attempt < retries:
                time.sleep(sleep)

    # ✨ NUEVO: Log critical failure
    log_error_with_context(
        last_error,
        {"endpoint": endpoint, "params": params, "retries": retries},
        logger
    )

    raise RuntimeError(
        f"StatsAPI failed after {retries + 1} attempts: {last_error}"
    )