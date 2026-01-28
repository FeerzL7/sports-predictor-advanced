# tests/manual/test_pick_validation.py

from core.validators.pick_validator import PickValidator, format_validation_report
from core.validators.projection_validator import ProjectionValidator


def test_valid_pick():
    """Test con pick válido."""
    
    validator = PickValidator()
    
    pick = {
        "market": "moneyline",
        "side": "home",
        "team": "Yankees",
        "odds": 1.85,
        "model_prob": 0.568,
        "implied_prob": 0.541,
        "edge": 0.050,
        "confidence": 0.634,
        "stake_pct": 0.0125,
        "stake": 125.00
    }
    
    result = validator.validate(pick)
    
    print("=" * 60)
    print("TEST 1: Valid Pick")
    print("=" * 60)
    print(format_validation_report(result))
    print()


def test_invalid_pick_low_edge():
    """Test con edge muy bajo."""
    
    validator = PickValidator()
    
    pick = {
        "market": "moneyline",
        "side": "home",
        "team": "Yankees",
        "odds": 1.85,
        "model_prob": 0.545,
        "implied_prob": 0.541,
        "edge": 0.004,  # Muy bajo
        "confidence": 0.634,
        "stake_pct": 0.0125,
        "stake": 125.00
    }
    
    result = validator.validate(pick)
    
    print("=" * 60)
    print("TEST 2: Invalid Pick (Low Edge)")
    print("=" * 60)
    print(format_validation_report(result))
    print()


def test_invalid_pick_high_stake():
    """Test con stake muy alto."""
    
    validator = PickValidator()
    
    pick = {
        "market": "moneyline",
        "side": "home",
        "team": "Yankees",
        "odds": 1.85,
        "model_prob": 0.568,
        "implied_prob": 0.541,
        "edge": 0.050,
        "confidence": 0.634,
        "stake_pct": 0.08,  # Excede cap de 5%
        "stake": 800.00
    }
    
    result = validator.validate(pick)
    
    print("=" * 60)
    print("TEST 3: Invalid Pick (Stake Too High)")
    print("=" * 60)
    print(format_validation_report(result))
    print()


def test_suspicious_pick():
    """Test con pick sospechoso pero técnicamente válido."""
    
    validator = PickValidator()
    
    pick = {
        "market": "moneyline",
        "side": "home",
        "team": "Yankees",
        "odds": 1.85,
        "model_prob": 0.70,  # Muy alto
        "implied_prob": 0.541,
        "edge": 0.30,  # Sospechosamente alto
        "confidence": 0.55,  # Bajo para este edge
        "stake_pct": 0.0125,
        "stake": 125.00
    }
    
    result = validator.validate(pick)
    
    print("=" * 60)
    print("TEST 4: Suspicious Pick (High Edge, Low Confidence)")
    print("=" * 60)
    print(format_validation_report(result))
    print()


def test_projection_validation():
    """Test validación de proyecciones."""
    
    validator = ProjectionValidator()
    
    # Válida
    print("=" * 60)
    print("TEST 5: Valid Projection")
    print("=" * 60)
    result = validator.validate_projection(4.5, 4.0, 0.70)
    print(f"Valid: {result['is_valid']}")
    print(f"Warnings: {result['warnings']}")
    print()
    
    # Inválida (muy baja)
    print("=" * 60)
    print("TEST 6: Invalid Projection (Too Low)")
    print("=" * 60)
    result = validator.validate_projection(0.2, 0.3, 0.70)
    print(f"Valid: {result['is_valid']}")
    print(f"Errors: {result['errors']}")
    print()
    
    # Sospechosa (muy alta)
    print("=" * 60)
    print("TEST 7: Suspicious Projection (Very High)")
    print("=" * 60)
    result = validator.validate_projection(12.0, 10.5, 0.70)
    print(f"Valid: {result['is_valid']}")
    print(f"Warnings: {result['warnings']}")
    print()


if __name__ == "__main__":
    test_valid_pick()
    test_invalid_pick_low_edge()
    test_invalid_pick_high_stake()
    test_suspicious_pick()
    test_projection_validation()
    
    print("=" * 60)
    print("✅ All validation tests completed!")
    print("=" * 60)