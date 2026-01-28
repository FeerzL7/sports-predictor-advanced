# config/settings.py

"""
Configuración centralizada del sistema.

Todas las constantes, thresholds, y parámetros en un solo lugar.
Soporta perfiles de riesgo y variables de entorno.
"""

import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Cargar .env
load_dotenv()


# =========================
# PATHS
# =========================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


# =========================
# API KEYS
# =========================

ODDS_API_KEY = os.getenv("ODDS_API_KEY")


# =========================
# GENERAL
# =========================

DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
SEASON = int(os.getenv("SEASON", "2025"))


# =========================
# BANKROLL
# =========================

DEFAULT_BANKROLL = float(os.getenv("BANKROLL", "10000.0"))


# =========================
# RISK PROFILES
# =========================

RISK_PROFILES = {
    "conservative": {
        "min_edge": 0.04,              # 4% mínimo
        "min_confidence": 0.65,        # 65% mínimo
        "kelly_fraction": 0.20,        # 20% de Kelly
        "max_stake_pct": 0.03,         # 3% máximo
        "max_picks_per_day": 3,
        "description": "Low risk, high confidence picks only"
    },
    "balanced": {
        "min_edge": 0.03,              # 3% mínimo
        "min_confidence": 0.60,        # 60% mínimo
        "kelly_fraction": 0.25,        # 25% de Kelly
        "max_stake_pct": 0.05,         # 5% máximo
        "max_picks_per_day": 5,
        "description": "Moderate risk, balanced approach"
    },
    "aggressive": {
        "min_edge": 0.02,              # 2% mínimo
        "min_confidence": 0.55,        # 55% mínimo
        "kelly_fraction": 0.33,        # 33% de Kelly
        "max_stake_pct": 0.05,         # 5% máximo (mismo cap por seguridad)
        "max_picks_per_day": 8,
        "description": "Higher risk, more picks"
    }
}

# Perfil activo (desde .env o default)
ACTIVE_RISK_PROFILE = os.getenv("RISK_PROFILE", "balanced")

# Validar perfil
if ACTIVE_RISK_PROFILE not in RISK_PROFILES:
    raise ValueError(
        f"Invalid RISK_PROFILE: {ACTIVE_RISK_PROFILE}. "
        f"Must be one of: {list(RISK_PROFILES.keys())}"
    )


# =========================
# PICK VALIDATION
# =========================

class PickValidationConfig:
    """Configuración de validación de picks."""
    
    profile = RISK_PROFILES[ACTIVE_RISK_PROFILE]
    
    # Thresholds desde perfil activo
    MIN_EDGE = profile["min_edge"]
    MIN_CONFIDENCE = profile["min_confidence"]
    MAX_STAKE_PCT = profile["max_stake_pct"]
    
    # Límites absolutos (no dependen de perfil)
    MIN_ODDS_DECIMAL = 1.01
    MAX_ODDS_DECIMAL = 50.0
    MAX_STAKE_AMOUNT = 500.0
    MIN_MODEL_PROB = 0.05
    MAX_MODEL_PROB = 0.95
    MAX_EDGE_WARNING = 0.25  # Edge > 25% es sospechoso
    
    # Confidence para edges altos
    MIN_CONFIDENCE_HIGH_EDGE = 0.60


# =========================
# PROJECTION VALIDATION
# =========================

class ProjectionValidationConfig:
    """Configuración de validación de proyecciones."""
    
    # MLB específico
    MIN_RUNS_PER_TEAM = 0.5
    MAX_RUNS_PER_TEAM = 15.0
    MIN_TOTAL_RUNS = 1.0
    MAX_TOTAL_RUNS = 25.0
    LEAGUE_AVG_RUNS = 4.6
    MAX_DEVIATION_FROM_AVG = 3.0


# =========================
# KELLY CRITERION
# =========================

class KellyConfig:
    """Configuración de Kelly Criterion."""
    
    profile = RISK_PROFILES[ACTIVE_RISK_PROFILE]
    
    KELLY_FRACTION = profile["kelly_fraction"]
    KELLY_CAP = profile["max_stake_pct"]
    
    # Ajustes por mercado (multiplicadores)
    MARKET_MULTIPLIERS = {
        "moneyline": 1.0,
        "total": 0.9,      # Más conservador en totals
        "spread": 0.85     # Aún más conservador en spreads
    }


# =========================
# MONTE CARLO
# =========================

class MonteCarloConfig:
    """Configuración de simulaciones Monte Carlo."""
    
    N_SIMULATIONS = int(os.getenv("MONTE_CARLO_SIMS", "10000"))
    
    # Innings split (starters vs bullpen)
    STARTER_INNINGS = 6
    BULLPEN_INNINGS = 3


# =========================
# LOGGING
# =========================

class LoggingConfig:
    """Configuración de logging."""
    
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_TO_FILE = True
    LOG_TO_CONSOLE = True
    COLORED_CONSOLE = True
    
    MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    BACKUP_COUNT = 5


# =========================
# DATABASE
# =========================

class DatabaseConfig:
    """Configuración de base de datos."""
    
    DB_PATH = str(DATA_DIR / "picks.db")
    BACKUP_DB_PATH = str(DATA_DIR / "picks_backup.db")
    
    # Auto-backup cada N picks
    AUTO_BACKUP_FREQUENCY = 100


# =========================
# MARKETS
# =========================

class MarketsConfig:
    """Configuración de mercados."""
    
    # Mercados activos
    ENABLED_MARKETS = os.getenv("ENABLED_MARKETS", "moneyline,total").split(",")
    
    # Configuración por mercado
    MONEYLINE = {
        "enabled": "moneyline" in ENABLED_MARKETS,
        "min_edge": PickValidationConfig.MIN_EDGE,
        "min_confidence": PickValidationConfig.MIN_CONFIDENCE
    }
    
    TOTAL = {
        "enabled": "total" in ENABLED_MARKETS,
        "min_edge": PickValidationConfig.MIN_EDGE,
        "min_confidence": PickValidationConfig.MIN_CONFIDENCE
    }
    
    SPREAD = {
        "enabled": "spread" in ENABLED_MARKETS,
        "min_edge": PickValidationConfig.MIN_EDGE + 0.01,  # Más exigente
        "min_confidence": PickValidationConfig.MIN_CONFIDENCE + 0.05
    }


# =========================
# MLB SPECIFIC
# =========================

class MLBConfig:
    """Configuración específica de MLB."""
    
    # League averages
    LEAGUE_ERA = 4.30
    LEAGUE_FIP = 4.20
    LEAGUE_K9 = 8.60
    LEAGUE_BB9 = 3.30
    LEAGUE_RPG = 4.60
    LEAGUE_OPS = 0.715
    LEAGUE_WRC_PLUS = 100.0
    LEAGUE_BULLPEN_ERA = 4.20
    
    # Empirical Bayes
    EB_IP = 20.0
    EB_GAMES = 162
    
    # Minimum samples
    MIN_IP_CONFIDENT = 25.0
    MIN_GAMES_CONFIDENT = 40
    MIN_BULLPEN_IP = 30.0
    
    # Recent form windows
    RECENT_DAYS = 15
    RECENT_STARTS = 3
    RECENT_GAMES = 15
    RECENT_DAYS_BULLPEN = 7


# =========================
# HELPER FUNCTIONS
# =========================

def get_active_profile() -> Dict[str, Any]:
    """Obtiene el perfil de riesgo activo."""
    return RISK_PROFILES[ACTIVE_RISK_PROFILE].copy()


def set_risk_profile(profile_name: str):
    """
    Cambia el perfil de riesgo activo.
    
    Args:
        profile_name: 'conservative', 'balanced', o 'aggressive'
    
    Raises:
        ValueError: Si el perfil no existe
    """
    global ACTIVE_RISK_PROFILE
    
    if profile_name not in RISK_PROFILES:
        raise ValueError(
            f"Invalid profile: {profile_name}. "
            f"Must be one of: {list(RISK_PROFILES.keys())}"
        )
    
    ACTIVE_RISK_PROFILE = profile_name
    
    # Actualizar configs que dependen del perfil
    profile = RISK_PROFILES[profile_name]
    
    PickValidationConfig.MIN_EDGE = profile["min_edge"]
    PickValidationConfig.MIN_CONFIDENCE = profile["min_confidence"]
    PickValidationConfig.MAX_STAKE_PCT = profile["max_stake_pct"]
    
    KellyConfig.KELLY_FRACTION = profile["kelly_fraction"]
    KellyConfig.KELLY_CAP = profile["max_stake_pct"]
    
    print(f"✅ Risk profile changed to: {profile_name}")
    print(f"   Min Edge: {profile['min_edge']*100:.1f}%")
    print(f"   Min Confidence: {profile['min_confidence']*100:.1f}%")
    print(f"   Kelly Fraction: {profile['kelly_fraction']*100:.1f}%")


def get_config_summary() -> Dict[str, Any]:
    """Obtiene resumen de configuración actual."""
    
    profile = get_active_profile()
    
    return {
        "risk_profile": ACTIVE_RISK_PROFILE,
        "profile_settings": profile,
        "bankroll": DEFAULT_BANKROLL,
        "monte_carlo_sims": MonteCarloConfig.N_SIMULATIONS,
        "enabled_markets": MarketsConfig.ENABLED_MARKETS,
        "database_path": DatabaseConfig.DB_PATH,
        "debug_mode": DEBUG_MODE
    }


def print_config_summary():
    """Imprime resumen de configuración."""
    
    summary = get_config_summary()
    
    print("=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    print(f"Risk Profile: {summary['risk_profile'].upper()}")
    print(f"  Description: {summary['profile_settings']['description']}")
    print(f"  Min Edge: {summary['profile_settings']['min_edge']*100:.1f}%")
    print(f"  Min Confidence: {summary['profile_settings']['min_confidence']*100:.1f}%")
    print(f"  Max Stake: {summary['profile_settings']['max_stake_pct']*100:.1f}%")
    print(f"  Kelly Fraction: {summary['profile_settings']['kelly_fraction']*100:.1f}%")
    print(f"\nBankroll: ${summary['bankroll']:,.2f}")
    print(f"Monte Carlo Simulations: {summary['monte_carlo_sims']:,}")
    print(f"Enabled Markets: {', '.join(summary['enabled_markets'])}")
    print(f"Database: {summary['database_path']}")
    print(f"Debug Mode: {summary['debug_mode']}")
    print("=" * 60)