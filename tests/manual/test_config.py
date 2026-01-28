# tests/manual/test_config.py

from config.settings import (
    get_active_profile,
    set_risk_profile,
    get_config_summary,
    print_config_summary,
    RISK_PROFILES,
    PickValidationConfig,
    KellyConfig
)


def test_print_config():
    """Test imprimir configuración actual."""
    print("=" * 60)
    print("TEST 1: Current Configuration")
    print("=" * 60)
    print_config_summary()
    print()


def test_risk_profiles():
    """Test cambiar entre perfiles de riesgo."""
    
    print("=" * 60)
    print("TEST 2: Risk Profiles")
    print("=" * 60)
    
    for profile_name in ["conservative", "balanced", "aggressive"]:
        print(f"\n🎯 Switching to: {profile_name.upper()}")
        set_risk_profile(profile_name)
        
        print(f"   Min Edge: {PickValidationConfig.MIN_EDGE*100:.1f}%")
        print(f"   Min Confidence: {PickValidationConfig.MIN_CONFIDENCE*100:.1f}%")
        print(f"   Kelly Fraction: {KellyConfig.KELLY_FRACTION*100:.1f}%")
        print(f"   Max Stake: {KellyConfig.KELLY_CAP*100:.1f}%")
    
    # Volver a balanced
    print("\n🔄 Resetting to: BALANCED")
    set_risk_profile("balanced")
    print()


def test_get_summary():
    """Test obtener resumen como dict."""
    
    print("=" * 60)
    print("TEST 3: Config Summary (Dict)")
    print("=" * 60)
    
    summary = get_config_summary()
    
    import json
    print(json.dumps(summary, indent=2))
    print()


def test_profile_comparison():
    """Test comparar todos los perfiles."""
    
    print("=" * 60)
    print("TEST 4: Profile Comparison")
    print("=" * 60)
    
    print(f"{'Metric':<20} {'Conservative':<15} {'Balanced':<15} {'Aggressive':<15}")
    print("-" * 65)
    
    metrics = ["min_edge", "min_confidence", "kelly_fraction", "max_stake_pct", "max_picks_per_day"]
    
    for metric in metrics:
        values = [
            f"{RISK_PROFILES[p][metric]*100:.1f}%" if "pct" in metric or metric in ["min_edge", "min_confidence", "kelly_fraction"] else str(RISK_PROFILES[p][metric])
            for p in ["conservative", "balanced", "aggressive"]
        ]
        
        print(f"{metric:<20} {values[0]:<15} {values[1]:<15} {values[2]:<15}")
    
    print()


if __name__ == "__main__":
    test_print_config()
    test_risk_profiles()
    test_get_summary()
    test_profile_comparison()
    
    print("=" * 60)
    print("✅ All config tests completed!")
    print("=" * 60)