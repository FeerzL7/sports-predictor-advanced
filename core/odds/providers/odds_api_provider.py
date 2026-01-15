# core/odds/providers/odds_api_provider.py
import requests
from typing import Dict, Any, Optional

from sports.baseball.mlb.constants.mlb_constants import SPORT, REGION

class OddsAPIProvider:
    BASE_URL = "https://api.the-odds-api.com/v4/sports"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_totals_market(
        self,
        event_id: str,
        bookmaker: str = "draftkings"
    ) -> Optional[Dict[str, Any]]:
        """
        Devuelve mercado de totales normalizado o None
        """

        try:
            resp = requests.get(
                f"{self.BASE_URL}/{SPORT}/odds",
                params={
                    "apiKey": self.api_key,
                    "regions": REGION,
                    "markets": "totals",
                    "bookmakers": bookmaker,
                },
                timeout=10
            )
            resp.raise_for_status()
            events = resp.json()

            for e in events:
                if e.get("id") != event_id:
                    continue

                for bm in e.get("bookmakers", []):
                    for m in bm.get("markets", []):
                        if m.get("key") != "totals":
                            continue

                        outcomes = m.get("outcomes", [])
                        over = next(o for o in outcomes if o["name"] == "Over")
                        under = next(o for o in outcomes if o["name"] == "Under")

                        return {
                            "total": {
                                "line": over.get("point"),
                                "odds_over": over.get("price"),
                                "odds_under": under.get("price"),
                                "bookmaker": bm.get("key"),
                            }
                        }

        except Exception:
            return None

        return None
