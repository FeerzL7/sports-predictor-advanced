from dotenv import load_dotenv
import os

load_dotenv()

ODDS_API_KEY = os.getenv("ODDS_API_KEY")

if not ODDS_API_KEY:
    raise RuntimeError("ODDS_API_KEY no encontrada en el entorno")
