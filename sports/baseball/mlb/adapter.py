from core.interfaces.sport_adapter import SportAdapter

from sports.baseball.mlb.analysis.pitching import analizar_pitchers
from sports.baseball.mlb.analysis.offense import analizar_ofensiva
from sports.baseball.mlb.analysis.defense import analizar_defensiva
from sports.baseball.mlb.analysis.context import analizar_contexto
from sports.baseball.mlb.analysis.h2h import analizar_h2h
from sports.baseball.mlb.analysis.projections import proyectar_totales

class MLBAdapter(SportAdapter):

    @property
    def sport(self):
        return "baseball"

    @property
    def league(self):
        return "MLB"

    def get_events(self, date: str):
        return analizar_pitchers(date)

    def analyze_event(self, event):
        partidos = [event]

        partidos = analizar_ofensiva(partidos)
        partidos = analizar_defensiva(partidos)
        partidos = analizar_contexto(partidos)
        partidos = analizar_h2h(partidos)
        partidos = proyectar_totales(partidos)

        return partidos[0]

    def generate_picks(self, analysis):
        # Por ahora solo regresamos el análisis crudo
        return analysis
