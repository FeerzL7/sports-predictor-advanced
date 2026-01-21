# core/odds/providers/fake_provider.py

from typing import Dict, Any
from core.odds.providers.base import OddsProviderBase


class FakeOddsProvider(OddsProviderBase):
    """
    Proveedor falso de odds.
    Devuelve mercados consistentes para tests:
    - Totales
    - Moneyline
    """

    def __init__(
        self,
        total_line: float = 8.5,
        odds_over: float = 1.95,
        odds_under: float = 1.95,
        ml_home: float = 2.20,
        ml_away: float = 1.65,
    ):
        self.total_line = total_line
        self.odds_over = odds_over
        self.odds_under = odds_under
        self.ml_home = ml_home
        self.ml_away = ml_away

    def get_markets(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Devuelve mercados fake con estructura REAL.
        """

        if not isinstance(analysis, dict):
            return {}

        projections = analysis.get("projections")
        if not projections:
            return {}

        total_runs = projections.get("total_runs")
        home_runs = projections.get("home_runs")
        away_runs = projections.get("away_runs")

        markets: Dict[str, Any] = {}

        # =========================
        # Totals
        # =========================
        if total_runs is not None:
            markets["total"] = {
                "line": self.total_line,
                "odds_over": self.odds_over,
                "odds_under": self.odds_under,
            }

        # =========================
        # Moneyline
        # =========================
        if home_runs is not None and away_runs is not None:
            markets["moneyline"] = {
                "home": self.ml_home,
                "away": self.ml_away,
            }

        return markets
