# scripts/set_profile.py

"""
CLI para cambiar perfil de riesgo.

Uso:
    python scripts/set_profile.py conservative
    python scripts/set_profile.py balanced
    python scripts/set_profile.py aggressive
"""

import sys
from pathlib import Path

# Agregar root al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config.settings import set_risk_profile, print_config_summary, RISK_PROFILES


def main():
    if len(sys.argv) != 2:
        print("❌ Usage: python scripts/set_profile.py <profile_name>")
        print(f"   Available profiles: {list(RISK_PROFILES.keys())}")
        sys.exit(1)
    
    profile = sys.argv[1].lower()
    
    try:
        set_risk_profile(profile)
        print()
        print_config_summary()
    
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()