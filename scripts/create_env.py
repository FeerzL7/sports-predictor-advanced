# scripts/create_env.py

"""
Script para crear archivo .env inicial desde .env.example
"""

from pathlib import Path
import shutil

ROOT = Path(__file__).parent.parent
ENV_EXAMPLE = ROOT / ".env.example"
ENV_FILE = ROOT / ".env"


def main():
    if ENV_FILE.exists():
        print("⚠️  .env file already exists!")
        response = input("   Overwrite? (y/N): ")
        
        if response.lower() != 'y':
            print("❌ Cancelled")
            return
    
    if not ENV_EXAMPLE.exists():
        print("❌ .env.example not found!")
        return
    
    shutil.copy(ENV_EXAMPLE, ENV_FILE)
    
    print("✅ .env file created!")
    print(f"   Location: {ENV_FILE}")
    print()
    print("📝 Next steps:")
    print("   1. Edit .env and add your ODDS_API_KEY")
    print("   2. Adjust other settings as needed")
    print("   3. Run: python -m tests.manual.test_config")


if __name__ == "__main__":
    main()