# core/odds/providers/fake_provider.py

from typing import Dict, Any
from core.odds.providers.base import OddsProvider


class FakeOddsProvider(OddsProvider):
    """
    Proveedor falso de odds.
    Se usa para tests y desarrollo local sin depender de APIs.
    """

    def __init__(
        self,
        total_line: float = 8.5,
        odds_over: float = 1.95,
        odds_under: float = 1.95
    ):
        self.total_line = total_line
        self.odds_over = odds_over
        self.odds_under = odds_under

    def get_markets(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Devuelve mercados fake pero con estructura real.
        """

        # Si no hay proyección, no inventamos
        projections = analysis.get("projections") if analysis else None
        if not projections or projections.get("total_runs") is None:
            return {}

        return {
            "total": {
                "line": self.total_line,
                "odds_over": self.odds_over,
                "odds_under": self.odds_under,
            }
        }
