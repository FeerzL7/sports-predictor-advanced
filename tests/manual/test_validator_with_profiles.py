# tests/manual/test_validator_with_profiles.py

from config.settings import set_risk_profile, PickValidationConfig
from core.validators.pick_validator import PickValidator


def test_profile_integration():
    """Verifica que el validador use la config correctamente."""
    
    pick = {
        "market": "moneyline",
        "side": "home",
        "team": "Yankees",
        "odds": 1.85,
        "model_prob": 0.562,
        "implied_prob": 0.541,
        "edge": 0.021,  # 2.1%
        "confidence": 0.58,
        "stake_pct": 0.0125,
        "stake": 125.00
    }
    
    print("=" * 60)
    print("TEST: Validator with Risk Profiles")
    print("=" * 60)
    
    # CONSERVATIVE (4% edge, 65% confidence)
    print("\n🎯 Profile: CONSERVATIVE")
    set_risk_profile("conservative")
    validator = PickValidator()
    result = validator.validate(pick)
    print(f"   Min Edge: {validator.min_edge*100:.1f}%")
    print(f"   Result: {'✅ VALID' if result.is_valid else '❌ INVALID'}")
    if result.errors:
        print(f"   Errors: {result.errors}")
    
    # BALANCED (3% edge, 60% confidence)
    print("\n🎯 Profile: BALANCED")
    set_risk_profile("balanced")
    validator = PickValidator()
    result = validator.validate(pick)
    print(f"   Min Edge: {validator.min_edge*100:.1f}%")
    print(f"   Result: {'✅ VALID' if result.is_valid else '❌ INVALID'}")
    if result.errors:
        print(f"   Errors: {result.errors}")
    
    # AGGRESSIVE (2% edge, 55% confidence)
    print("\n🎯 Profile: AGGRESSIVE")
    set_risk_profile("aggressive")
    validator = PickValidator()
    result = validator.validate(pick)
    print(f"   Min Edge: {validator.min_edge*100:.1f}%")
    print(f"   Result: {'✅ VALID' if result.is_valid else '❌ INVALID'}")
    if result.errors:
        print(f"   Errors: {result.errors}")
    
    print("\n" + "=" * 60)
    print("Expected:")
    print("  Conservative: ❌ (2.1% < 4% AND 58% < 65%)")
    print("  Balanced: ❌ (58% < 60%)")
    print("  Aggressive: ✅ (2.1% > 2% AND 58% > 55%)")
    print("=" * 60)


if __name__ == "__main__":
    test_profile_integration()