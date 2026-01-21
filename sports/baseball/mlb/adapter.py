# sports/baseball/mlb/adapter.py

from core.interfaces.sport_adapter import SportAdapter
from core.odds.providers.base import OddsProviderBase
from core.odds.providers.odds_api_provider import OddsAPIProvider

from core.odds.markets.totals import evaluate_totals_market
from core.odds.markets.moneyline import evaluate_moneyline_market

from sports.baseball.mlb.analysis.pitching import analizar_pitchers
from sports.baseball.mlb.analysis.offense import analizar_ofensiva
from sports.baseball.mlb.analysis.defense import analizar_defensiva
from sports.baseball.mlb.analysis.context import analizar_contexto
from sports.baseball.mlb.analysis.h2h import analizar_h2h
from sports.baseball.mlb.analysis.projections import proyectar_totales


class MLBAdapter(SportAdapter):
    """
    Adapter MLB
    - Orquesta análisis MLB
    - Inyecta odds vía OddsProvider (real o fake)
    - Devuelve analysis normalizado
    - El core decide los picks (Totals / Moneyline)
    """

    # =========================
    # Init
    # =========================
    def __init__(
        self,
        odds_provider: OddsProviderBase | None = None,
        odds_api_key: str | None = None
    ):
        if odds_provider:
            self.odds_provider = odds_provider
        elif odds_api_key:
            self.odds_provider = OddsAPIProvider(odds_api_key)
        else:
            self.odds_provider = None

    # =========================
    # Metadata
    # =========================
    @property
    def sport(self) -> str:
        return "baseball"

    @property
    def league(self) -> str:
        return "MLB"

    # =========================
    # Events
    # =========================
    def get_events(self, date: str):
        return analizar_pitchers(date) or []

    # =========================
    # Analysis Pipeline
    # =========================
    def analyze_event(self, event: dict) -> dict:
        partidos = [event]

        partidos = analizar_ofensiva(partidos)
        partidos = analizar_defensiva(partidos)
        partidos = analizar_contexto(partidos)
        partidos = analizar_h2h(partidos)
        partidos = proyectar_totales(partidos)

        analysis = self._normalize_analysis(partidos[0])

        # =========================
        # Odds (provider)
        # =========================
        if self.odds_provider:
            markets = self.odds_provider.get_markets(analysis)
            if isinstance(markets, dict) and markets:
                # merge seguro
                analysis["market"].update(markets)

        return analysis

    # =========================
    # Picks
    # =========================
    def generate_picks(self, analysis: dict):
        if not isinstance(analysis, dict):
            return []

        picks = []

        # Totals
        total_pick = evaluate_totals_market(analysis)
        if total_pick:
            picks.append(total_pick)

        # Moneyline
        ml_pick = evaluate_moneyline_market(analysis)
        if ml_pick:
            picks.append(ml_pick)

        return picks

    # =========================
    # Normalization
    # =========================
    def _normalize_analysis(self, p: dict) -> dict:
        """
        Salida estándar.
        market SIEMPRE existe, aunque esté incompleto.
        """

        return {
            "sport": self.sport,
            "league": self.league,

            "event_id": p.get("game_id") or p.get("id"),
            "date": p.get("date"),
            "start_time": p.get("start_time"),
            "venue": p.get("venue"),

            "teams": {
                "home": p.get("home_team"),
                "away": p.get("away_team"),
            },

            "analysis": {
                "pitching": {
                    "home": p.get("home_stats"),
                    "away": p.get("away_stats"),
                },
                "offense": {
                    "home": p.get("home_offense"),
                    "away": p.get("away_offense"),
                },
                "defense": {
                    "home": p.get("home_defense"),
                    "away": p.get("away_defense"),
                },
                "context": {
                    "home": p.get("home_context"),
                    "away": p.get("away_context"),
                },
                "h2h": p.get("h2h"),
            },

            "projections": {
                "home_runs": p.get("proj_home"),
                "away_runs": p.get("proj_away"),
                "total_runs": p.get("proj_total"),
            },

            # Market base (se completa vía provider)
            "market": {
                "total": {
                    "line": p.get("total_line"),
                    "odds_over": p.get("odds_over"),
                    "odds_under": p.get("odds_under"),
                }
                # moneyline se inyecta por provider
            },

            "confidence": round(p.get("projection_confidence", 0.5), 3),
            "flags": p.get("data_warnings", []),
        }
