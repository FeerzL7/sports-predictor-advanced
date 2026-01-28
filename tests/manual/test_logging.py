# tests/manual/test_logging.py

from core.utils.logger import (
    setup_logger,
    get_api_logger,
    get_model_logger,
    get_picks_logger,
    get_error_logger,
    LogContext,
    log_pick,
    log_api_call,
    log_error_with_context
)


def test_basic_logging():
    """Test básico de niveles de logging."""
    logger = setup_logger("test_basic")
    
    logger.debug("Mensaje DEBUG - solo en archivo")
    logger.info("Mensaje INFO - aparece en consola")
    logger.warning("Mensaje WARNING - advertencia")
    logger.error("Mensaje ERROR - error recuperable")
    logger.critical("Mensaje CRITICAL - error grave")


def test_specialized_loggers():
    """Test de loggers especializados."""
    
    api_logger = get_api_logger("statsapi")
    api_logger.info("Consultando StatsAPI...")
    
    model_logger = get_model_logger("monte_carlo")
    model_logger.info("Ejecutando simulación Monte Carlo")
    
    picks_logger = get_picks_logger()
    picks_logger.info("Generando picks del día")
    
    error_logger = get_error_logger()
    error_logger.error("Error crítico en producción")


def test_context_manager():
    """Test de LogContext."""
    logger = setup_logger("test_context")
    
    with LogContext("Procesando partido Yankees vs Red Sox", logger):
        logger.info("Analizando pitching...")
        logger.info("Analizando offense...")
        logger.info("Calculando proyecciones...")


def test_pick_logging():
    """Test de logging de picks."""
    
    pick = {
        "market": "moneyline",
        "team": "Yankees",
        "side": "home",
        "odds": 1.85,
        "edge": 0.056,
        "confidence": 0.635
    }
    
    log_pick(pick)


def test_api_logging():
    """Test de logging de API calls."""
    
    log_api_call(
        "schedule",
        {"date": "2026-04-15"},
        get_api_logger()
    )


def test_error_logging():
    """Test de logging de errores con contexto."""
    
    try:
        # Simular un error
        result = 10 / 0
    except Exception as e:
        log_error_with_context(
            e,
            {
                "operation": "division",
                "numerator": 10,
                "denominator": 0
            },
            get_error_logger()
        )


if __name__ == "__main__":
    print("=" * 60)
    print("TEST 1: Logging Básico")
    print("=" * 60)
    test_basic_logging()
    
    print("\n" + "=" * 60)
    print("TEST 2: Loggers Especializados")
    print("=" * 60)
    test_specialized_loggers()
    
    print("\n" + "=" * 60)
    print("TEST 3: Context Manager")
    print("=" * 60)
    test_context_manager()
    
    print("\n" + "=" * 60)
    print("TEST 4: Pick Logging")
    print("=" * 60)
    test_pick_logging()
    
    print("\n" + "=" * 60)
    print("TEST 5: API Logging")
    print("=" * 60)
    test_api_logging()
    
    print("\n" + "=" * 60)
    print("TEST 6: Error Logging")
    print("=" * 60)
    test_error_logging()
    
    print("\n" + "=" * 60)
    print("✅ Tests completados. Revisa logs/ para ver archivos generados")
    print("=" * 60)
    