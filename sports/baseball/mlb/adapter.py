from core.interfaces.sport_adapter import SportAdapter

class MLBAdapter(SportAdapter):

    @property
    def sport(self):
        return "baseball"

    @property
    def league(self):
        return "MLB"

    def get_events(self, date: str):
        print(f"[MLB] get_events {date}")
        return []

    def analyze_event(self, event):
        return {}

    def generate_picks(self, analysis):
        return []
