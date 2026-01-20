# sports/baseball/mlb/adapter.py

from core.interfaces.sport_adapter import SportAdapter

from sports.baseball.mlb.analysis.pitching import analizar_pitchers
from sports.baseball.mlb.analysis.offense import analizar_ofensiva
from sports.baseball.mlb.analysis.defense import analizar_defensiva
from sports.baseball.mlb.analysis.context import analizar_contexto
from sports.baseball.mlb.analysis.h2h import analizar_h2h
from sports.baseball.mlb.analysis.projections import proyectar_totales

from core.odds.markets.totals import evaluate_totals_market
from core.odds.providers.odds_api_provider import OddsAPIProvider


class MLBAdapter(SportAdapter):
    """
    Adapter MLB v2 – Fase 1
    - Orquesta análisis MLB
    - Inyecta odds vía provider externo (opcional)
    - Devuelve analysis normalizado
    - El core decide los picks
    """

    # =========================
    # Init
    # =========================
    def __init__(self, odds_api_key: str | None = None):
        self.odds_provider = (
            OddsAPIProvider(odds_api_key)
            if odds_api_key
            else None
        )

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
        """
        Obtiene eventos base del día (pitchers como punto de entrada).
        """
        events = analizar_pitchers(date)
        return events or []

    # =========================
    # Analysis Pipeline
    # =========================
    def analyze_event(self, event: dict) -> dict:
        """
        Ejecuta TODO el pipeline de análisis.
        NO genera picks.
        """

        partidos = [event]

        partidos = analizar_ofensiva(partidos)
        partidos = analizar_defensiva(partidos)
        partidos = analizar_contexto(partidos)
        partidos = analizar_h2h(partidos)
        partidos = proyectar_totales(partidos)

        p = partidos[0]

        # =========================
        # Odds (si provider activo)
        # =========================
        if self.odds_provider:
            market = self.odds_provider.get_totals_market(
                event_id=p.get("game_id") or p.get("id")
            )
            if isinstance(market, dict):
                p["market"] = market

        return self._normalize_analysis(p)

    # =========================
    # Picks
    # =========================
    def generate_picks(self, analysis: dict):
        """
        Consume analysis normalizado y devuelve picks.
        """
        if not isinstance(analysis, dict):
            return []

        market = analysis.get("market")
        if not isinstance(market, dict):
            return []

        picks = []

        total_pick = evaluate_totals_market(analysis)
        if total_pick:
            picks.append(total_pick)

        return picks

    # =========================
    # Normalization
    # =========================
    def _normalize_analysis(self, p: dict) -> dict:
        """
        Salida estándar, estable y agnóstica al core.
        NUNCA devuelve market = None.
        """

        market = p.get("market", {}) or {}

        # Fallback de totals si el provider no respondió
        if "total" not in market:
            market["total"] = {
                "line": p.get("total_line"),
                "odds_over": p.get("odds_over"),
                "odds_under": p.get("odds_under"),
            }

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

            "market": market,
            "confidence": round(p.get("projection_confidence", 0.5), 3),
            "flags": p.get("data_warnings", []),
        }
