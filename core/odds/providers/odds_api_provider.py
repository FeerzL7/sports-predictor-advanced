import requests
from typing import Dict, Any

from core.odds.providers.base import OddsProviderBase
from sports.baseball.mlb.constants.mlb_constants import SPORT, REGION


class OddsAPIProvider(OddsProviderBase):
    BASE_URL = "https://api.the-odds-api.com/v4/sports"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_markets(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Devuelve mercados normalizados (totals, moneyline)
        """

        event_id = analysis.get("event_id")
        teams = analysis.get("teams", {})
        home = teams.get("home")
        away = teams.get("away")

        if not event_id or not home or not away:
            return {}

        try:
            resp = requests.get(
                f"{self.BASE_URL}/{SPORT}/odds",
                params={
                    "apiKey": self.api_key,
                    "regions": REGION,
                    "markets": "totals,h2h",
                    "oddsFormat": "decimal",
                },
                timeout=10
            )
            resp.raise_for_status()
            events = resp.json()

        except Exception:
            return {}

        for e in events:
            if e.get("id") != event_id:
                continue

            markets: Dict[str, Any] = {}

            for bm in e.get("bookmakers", []):
                for m in bm.get("markets", []):

                    # ======================
                    # TOTALS
                    # ======================
                    if m.get("key") == "totals":
                        outcomes = m.get("outcomes", [])
                        over = next((o for o in outcomes if o["name"] == "Over"), None)
                        under = next((o for o in outcomes if o["name"] == "Under"), None)

                        if over and under:
                            markets["total"] = {
                                "line": over.get("point"),
                                "odds_over": over.get("price"),
                                "odds_under": under.get("price"),
                                "bookmaker": bm.get("key"),
                            }

                    # ======================
                    # MONEYLINE
                    # ======================
                    if m.get("key") == "h2h":
                        odds = {}
                        for o in m.get("outcomes", []):
                            if o["name"] == home:
                                odds["home"] = o.get("price")
                            elif o["name"] == away:
                                odds["away"] = o.get("price")

                        if len(odds) == 2:
                            markets["moneyline"] = odds

            return markets

        return {}
