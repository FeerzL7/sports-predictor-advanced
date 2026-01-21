from typing import Dict, Any
from core.odds.providers.base import OddsProviderBase


class FakeOddsProvider(OddsProviderBase):
    """
    Proveedor fake de odds.
    Usado para tests manuales y desarrollo sin APIs externas.
    Soporta Totals y Moneyline.
    """

    def __init__(
        self,
        total_line: float = 8.5,
        odds_over: float = 1.95,
        odds_under: float = 1.95,
        ml_home: float = -135,
        ml_away: float = +120,
    ):
        self.total_line = total_line
        self.odds_over = odds_over
        self.odds_under = odds_under
        self.ml_home = ml_home
        self.ml_away = ml_away

    def get_markets(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Devuelve mercados fake pero con estructura REAL.
        """

        if not analysis:
            return {}

        projections = analysis.get("projections", {})
        teams = analysis.get("teams", {})

        # Si no hay proyección, no inventamos
        if projections.get("total_runs") is None:
            return {}

        return {
            "total": {
                "line": self.total_line,
                "odds_over": self.odds_over,
                "odds_under": self.odds_under,
            },
            "moneyline": {
                "home": {
                    "team": teams.get("home"),
                    "odds": self.ml_home,
                },
                "away": {
                    "team": teams.get("away"),
                    "odds": self.ml_away,
                },
            },
        }
