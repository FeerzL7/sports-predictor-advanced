from core.interfaces.sport_adapter import SportAdapter

from sports.baseball.mlb.analysis.pitching import analizar_pitchers
from sports.baseball.mlb.analysis.offense import analizar_ofensiva
from sports.baseball.mlb.analysis.defense import analizar_defensiva
from sports.baseball.mlb.analysis.context import analizar_contexto
from sports.baseball.mlb.analysis.h2h import analizar_h2h
from sports.baseball.mlb.analysis.projections import proyectar_totales

from core.odds.markets.totals import evaluate_totals_market

class MLBAdapter(SportAdapter):

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
        Obtiene eventos base del día.
        Por ahora reutiliza analizar_pitchers como loader principal.
        """
        return analizar_pitchers(date)

    # =========================
    # Core Analysis
    # =========================
    def analyze_event(self, event: dict) -> dict:
        """
        Ejecuta el pipeline completo de análisis y devuelve
        un objeto normalizado listo para core / picks.
        """
        partidos = [event]

        partidos = analizar_ofensiva(partidos)
        partidos = analizar_defensiva(partidos)
        partidos = analizar_contexto(partidos)
        partidos = analizar_h2h(partidos)
        partidos = proyectar_totales(partidos)

        p = partidos[0]

        return self._normalize_analysis(p)

    # =========================
    # Picks (placeholder)
    # =========================
    def generate_picks(self, analysis):
        pick = evaluate_totals_market(analysis)
        return pick

    # =========================
    # Normalization
    # =========================
    def _normalize_analysis(self, p: dict) -> dict:
        """
        Convierte el análisis crudo en una salida estándar.
        """

        flags = p.get("data_warnings", [])

        projection_conf = p.get("projection_confidence", 0.5)

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

            "confidence": round(projection_conf, 3),
            "flags": flags,
        }
