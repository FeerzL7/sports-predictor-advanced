from abc import ABC, abstractmethod

class SportAdapter(ABC):

    @property
    @abstractmethod
    def sport(self) -> str:
        pass

    @property
    @abstractmethod
    def league(self) -> str:
        pass

    @abstractmethod
    def get_events(self, date: str):
        """
        Devuelve los eventos crudos del día (partidos, juegos, matches).
        """
        pass

    @abstractmethod
    def analyze_event(self, event):
        """
        Aplica el análisis propio del deporte.
        """
        pass

    @abstractmethod
    def generate_picks(self, analysis):
        """
        Genera picks normalizados para el core.
        """
        pass
