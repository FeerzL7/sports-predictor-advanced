# core/validators/pick_validator.py

"""
Sistema de validación de picks antes de guardarlos en base de datos.

Validaciones:
- Edge mínimo
- Confidence mínimo
- Stake dentro de límites
- Odds realistas
- Datos completos
- No duplicados
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

from core.utils.logger import setup_logger
from config.settings import PickValidationConfig

logger = setup_logger(__name__)


# =========================
# VALIDATION RESULT
# =========================

class ValidationResult:
    """Resultado de validación."""
    
    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def add_error(self, message: str):
        """Agrega error (pick inválido)."""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Agrega warning (pick válido pero sospechoso)."""
        self.warnings.append(message)
    
    def add_info(self, message: str):
        """Agrega información."""
        self.info.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a dict."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info
        }
    
    def __bool__(self):
        """Permite usar como bool."""
        return self.is_valid
    
    def __str__(self):
        """String representation."""
        if self.is_valid:
            status = "✅ VALID"
        else:
            status = "❌ INVALID"
        
        parts = [status]
        
        if self.errors:
            parts.append(f"Errors: {len(self.errors)}")
        if self.warnings:
            parts.append(f"Warnings: {len(self.warnings)}")
        
        return " | ".join(parts)


# =========================
# VALIDATORS
# =========================

class PickValidator:
    """
    Validador de picks.
    
    Uso:
        validator = PickValidator()
        result = validator.validate(pick)
        
        if result.is_valid:
            db.save_pick(pick)
        else:
            logger.error(f"Invalid pick: {result.errors}")
    """
    
    def __init__(
        self,
        min_edge: float = None,
        min_confidence: float = None,
        max_stake_pct: float = None
    ):
        """
        Inicializa validador.
        
        Args:
            min_edge: Edge mínimo (default: usa config)
            min_confidence: Confidence mínimo (default: usa config)
            max_stake_pct: Stake máximo % (default: usa config)
        """
        # Usar config centralizada si no se proveen valores
        self.min_edge = min_edge if min_edge is not None else PickValidationConfig.MIN_EDGE
        self.min_confidence = min_confidence if min_confidence is not None else PickValidationConfig.MIN_CONFIDENCE
        self.max_stake_pct = max_stake_pct if max_stake_pct is not None else PickValidationConfig.MAX_STAKE_PCT
        
        # Límites absolutos (no dependen de perfil)
        self.max_edge_warning = PickValidationConfig.MAX_EDGE_WARNING
        self.min_confidence_high_edge = PickValidationConfig.MIN_CONFIDENCE_HIGH_EDGE
        self.min_stake_pct = 0.001  # 0.1% mínimo
        self.max_stake_amount = PickValidationConfig.MAX_STAKE_AMOUNT
        self.min_odds = PickValidationConfig.MIN_ODDS_DECIMAL
        self.max_odds = PickValidationConfig.MAX_ODDS_DECIMAL
        self.min_model_prob = PickValidationConfig.MIN_MODEL_PROB
        self.max_model_prob = PickValidationConfig.MAX_MODEL_PROB
        
        logger.info(
            f"PickValidator initialized: min_edge={self.min_edge*100:.1f}%, "
            f"min_confidence={self.min_confidence*100:.1f}%, "
            f"max_stake={self.max_stake_pct*100:.1f}%"
        )
    
    def validate(self, pick: Dict[str, Any]) -> ValidationResult:
        """
        Valida un pick completo.
        
        Args:
            pick: Dict con datos del pick
        
        Returns:
            ValidationResult con errores, warnings, info
        """
        
        result = ValidationResult()
        
        # Validaciones críticas (errores)
        self._validate_required_fields(pick, result)
        self._validate_edge(pick, result)
        self._validate_confidence(pick, result)
        self._validate_odds(pick, result)
        self._validate_probabilities(pick, result)
        self._validate_stake(pick, result)
        
        # Validaciones de calidad (warnings)
        self._check_data_quality(pick, result)
        self._check_edge_confidence_correlation(pick, result)
        
        # Log resultado
        if not result.is_valid:
            logger.warning(
                f"Pick validation FAILED: {pick.get('market')} | "
                f"{pick.get('team')} | Errors: {result.errors}"
            )
        elif result.warnings:
            logger.info(
                f"Pick validation OK (with warnings): {pick.get('market')} | "
                f"{pick.get('team')} | Warnings: {result.warnings}"
            )
        else:
            logger.debug(f"Pick validation OK: {pick.get('market')} | {pick.get('team')}")
        
        return result
    
    # =========================
    # VALIDACIONES CRÍTICAS
    # =========================
    
    def _validate_required_fields(self, pick: Dict, result: ValidationResult):
        """Valida campos requeridos."""
        
        required = [
            "market", "side", "odds", "model_prob", 
            "implied_prob", "edge", "confidence"
        ]
        
        missing = [field for field in required if pick.get(field) is None]
        
        if missing:
            result.add_error(f"Missing required fields: {missing}")
    
    def _validate_edge(self, pick: Dict, result: ValidationResult):
        """Valida edge."""
        
        edge = pick.get("edge")
        
        if edge is None:
            return  # Ya capturado en required_fields
        
        # Edge mínimo
        if edge < self.min_edge:
            result.add_error(
                f"Edge too low: {edge*100:.2f}% < {self.min_edge*100:.1f}%"
            )
        
        # Edge negativo
        if edge < 0:
            result.add_error(f"Negative edge: {edge*100:.2f}%")
        
        # Edge sospechosamente alto
        if edge > self.max_edge_warning:
            result.add_warning(
                f"Edge suspiciously high: {edge*100:.1f}% (check data quality)"
            )
    
    def _validate_confidence(self, pick: Dict, result: ValidationResult):
        """Valida confidence."""
        
        confidence = pick.get("confidence")
        edge = pick.get("edge", 0)
        
        if confidence is None:
            return
        
        # Confidence mínimo
        if confidence < self.min_confidence:
            result.add_error(
                f"Confidence too low: {confidence*100:.1f}% < {self.min_confidence*100:.1f}%"
            )
        
        # Confidence más alto para edges grandes
        if edge > 0.10 and confidence < self.min_confidence_high_edge:
            result.add_warning(
                f"High edge ({edge*100:.1f}%) requires higher confidence "
                f"(current: {confidence*100:.1f}%, required: {self.min_confidence_high_edge*100:.1f}%)"
            )
        
        # Confidence fuera de rango [0, 1]
        if not (0 <= confidence <= 1):
            result.add_error(f"Confidence out of range [0, 1]: {confidence}")
    
    def _validate_odds(self, pick: Dict, result: ValidationResult):
        """Valida odds."""
        
        odds = pick.get("odds")
        
        if odds is None:
            return
        
        # Odds demasiado bajos
        if odds < self.min_odds:
            result.add_error(f"Odds too low: {odds} < {self.min_odds}")
        
        # Odds demasiado altos
        if odds > self.max_odds:
            result.add_warning(f"Odds very high: {odds} (longshot)")
    
    def _validate_probabilities(self, pick: Dict, result: ValidationResult):
        """Valida probabilidades."""
        
        model_prob = pick.get("model_prob")
        implied_prob = pick.get("implied_prob")
        
        if model_prob is not None:
            # Rango válido
            if not (self.min_model_prob <= model_prob <= self.max_model_prob):
                result.add_error(
                    f"Model probability out of range [{self.min_model_prob}, {self.max_model_prob}]: {model_prob}"
                )
        
        if implied_prob is not None:
            # Rango válido
            if not (0 < implied_prob < 1):
                result.add_error(f"Implied probability out of range (0, 1): {implied_prob}")
        
        # Coherencia entre probabilidades y edge
        if model_prob is not None and implied_prob is not None:
            expected_edge = model_prob - implied_prob
            actual_edge = pick.get("edge", 0)
            
            # Permitir pequeña diferencia por redondeo
            if abs(expected_edge - actual_edge) > 0.01:
                result.add_warning(
                    f"Edge mismatch: calculated={expected_edge:.3f}, "
                    f"provided={actual_edge:.3f}"
                )
    
    def _validate_stake(self, pick: Dict, result: ValidationResult):
        """Valida stake."""
        
        stake_pct = pick.get("stake_pct")
        stake_amount = pick.get("stake")
        
        if stake_pct is not None:
            # Stake mínimo
            if stake_pct < self.min_stake_pct:
                result.add_warning(f"Stake very small: {stake_pct*100:.2f}%")
            
            # Stake máximo (Kelly cap)
            if stake_pct > self.max_stake_pct:
                result.add_error(
                    f"Stake exceeds cap: {stake_pct*100:.2f}% > {self.max_stake_pct*100:.1f}%"
                )
        
        if stake_amount is not None:
            # Stake negativo
            if stake_amount < 0:
                result.add_error(f"Negative stake: ${stake_amount}")
            
            # Stake máximo absoluto
            if stake_amount > self.max_stake_amount:
                result.add_warning(
                    f"Stake very high: ${stake_amount:.2f} > ${self.max_stake_amount}"
                )
    
    # =========================
    # VALIDACIONES DE CALIDAD
    # =========================
    
    def _check_data_quality(self, pick: Dict, result: ValidationResult):
        """Verifica calidad de datos del análisis."""
        
        # Revisar si hay flags de baja calidad en el reason
        reason = pick.get("reason", "")
        
        quality_flags = [
            "LOW_SAMPLE", "NO_H2H", "NO_RECENT", "TBD_pitcher",
            "NO_BULLPEN", "NO_SPLITS"
        ]
        
        found_flags = [flag for flag in quality_flags if flag in reason]
        
        if found_flags:
            result.add_info(f"Data quality flags: {found_flags}")
    
    def _check_edge_confidence_correlation(self, pick: Dict, result: ValidationResult):
        """Verifica coherencia entre edge y confidence."""
        
        edge = pick.get("edge", 0)
        confidence = pick.get("confidence", 0)
        
        # Edge alto debería tener confidence alto
        if edge > 0.08 and confidence < 0.65:
            result.add_warning(
                f"High edge ({edge*100:.1f}%) with low confidence ({confidence*100:.1f}%)"
            )
        
        # Confidence muy alto con edge bajo es sospechoso
        if confidence > 0.80 and edge < 0.03:
            result.add_warning(
                f"High confidence ({confidence*100:.1f}%) with low edge ({edge*100:.1f}%)"
            )


# =========================
# BATCH VALIDATION
# =========================

def validate_picks_batch(
    picks: List[Dict[str, Any]],
    validator: PickValidator = None
) -> Tuple[List[Dict], List[Tuple[Dict, ValidationResult]]]:
    """
    Valida múltiples picks.
    
    Args:
        picks: Lista de picks
        validator: Validador custom (opcional)
    
    Returns:
        (valid_picks, invalid_picks_with_reasons)
    """
    
    if validator is None:
        validator = PickValidator()
    
    valid = []
    invalid = []
    
    for pick in picks:
        result = validator.validate(pick)
        
        if result.is_valid:
            valid.append(pick)
        else:
            invalid.append((pick, result))
    
    logger.info(
        f"Batch validation: {len(valid)} valid, {len(invalid)} invalid "
        f"(total: {len(picks)})"
    )
    
    return valid, invalid


# =========================
# HELPERS
# =========================

def format_validation_report(result: ValidationResult) -> str:
    """Formatea resultado de validación como string legible."""
    
    lines = []
    
    if result.is_valid:
        lines.append("✅ PICK VALID")
    else:
        lines.append("❌ PICK INVALID")
    
    if result.errors:
        lines.append("\nERRORS:")
        for error in result.errors:
            lines.append(f"  ❌ {error}")
    
    if result.warnings:
        lines.append("\nWARNINGS:")
        for warning in result.warnings:
            lines.append(f"  ⚠️  {warning}")
    
    if result.info:
        lines.append("\nINFO:")
        for info in result.info:
            lines.append(f"  ℹ️  {info}")
    
    return "\n".join(lines)