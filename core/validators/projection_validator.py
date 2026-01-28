# core/validators/projection_validator.py

"""
Validador de proyecciones de runs/totals.

Verifica que las proyecciones sean realistas antes de usarlas.
"""

from typing import Dict, Any, Optional

from core.utils.logger import setup_logger

logger = setup_logger(__name__)


# =========================
# CONFIGURACIÓN
# =========================

# Límites para MLB
MIN_RUNS_PER_TEAM = 0.5         # Mínimo realista
MAX_RUNS_PER_TEAM = 15.0        # Máximo realista
MIN_TOTAL_RUNS = 1.0            # Total mínimo
MAX_TOTAL_RUNS = 25.0           # Total máximo
LEAGUE_AVG_RUNS = 4.6           # Promedio MLB

# Desviaciones sospechosas
MAX_DEVIATION_FROM_AVG = 3.0    # ±3 runs del promedio


# =========================
# VALIDATOR
# =========================

class ProjectionValidator:
    """
    Valida proyecciones de runs.
    
    Uso:
        validator = ProjectionValidator()
        is_valid = validator.validate_projection(proj_home, proj_away)
    """
    
    def __init__(
        self,
        min_runs: float = MIN_RUNS_PER_TEAM,
        max_runs: float = MAX_RUNS_PER_TEAM,
        league_avg: float = LEAGUE_AVG_RUNS
    ):
        self.min_runs = min_runs
        self.max_runs = max_runs
        self.league_avg = league_avg
    
    def validate_projection(
        self,
        home_runs: float,
        away_runs: float,
        confidence: float = None
    ) -> Dict[str, Any]:
        """
        Valida proyección de runs.
        
        Returns:
            Dict con: is_valid, errors, warnings
        """
        
        errors = []
        warnings = []
        
        # Validar home
        if home_runs < self.min_runs:
            errors.append(f"Home runs too low: {home_runs} < {self.min_runs}")
        
        if home_runs > self.max_runs:
            warnings.append(f"Home runs very high: {home_runs} > {self.max_runs}")
        
        # Validar away
        if away_runs < self.min_runs:
            errors.append(f"Away runs too low: {away_runs} < {self.min_runs}")
        
        if away_runs > self.max_runs:
            warnings.append(f"Away runs very high: {away_runs} > {self.max_runs}")
        
        # Validar total
        total = home_runs + away_runs
        
        if total < MIN_TOTAL_RUNS:
            errors.append(f"Total runs too low: {total} < {MIN_TOTAL_RUNS}")
        
        if total > MAX_TOTAL_RUNS:
            warnings.append(f"Total runs very high: {total} > {MAX_TOTAL_RUNS}")
        
        # Desviación del promedio
        home_deviation = abs(home_runs - self.league_avg)
        away_deviation = abs(away_runs - self.league_avg)
        
        if home_deviation > MAX_DEVIATION_FROM_AVG:
            warnings.append(
                f"Home projection far from average: {home_runs:.1f} "
                f"(avg: {self.league_avg})"
            )
        
        if away_deviation > MAX_DEVIATION_FROM_AVG:
            warnings.append(
                f"Away projection far from average: {away_runs:.1f} "
                f"(avg: {self.league_avg})"
            )
        
        # Validar confidence
        if confidence is not None and confidence < 0.50:
            warnings.append(f"Low projection confidence: {confidence*100:.1f}%")
        
        is_valid = len(errors) == 0
        
        result = {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "home_runs": home_runs,
            "away_runs": away_runs,
            "total_runs": total
        }
        
        if not is_valid:
            logger.warning(f"Invalid projection: {errors}")
        elif warnings:
            logger.info(f"Projection warnings: {warnings}")
        
        return result
    
    def validate_analysis(self, analysis: Dict[str, Any]) -> bool:
        """
        Valida proyecciones en un analysis dict completo.
        
        Returns:
            True si es válido
        """
        
        proj = analysis.get("projections", {})
        
        home_runs = proj.get("home_runs")
        away_runs = proj.get("away_runs")
        confidence = analysis.get("confidence")
        
        if home_runs is None or away_runs is None:
            logger.error("Missing projections in analysis")
            return False
        
        result = self.validate_projection(home_runs, away_runs, confidence)
        
        return result["is_valid"]