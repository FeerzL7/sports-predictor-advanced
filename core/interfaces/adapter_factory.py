from sports.baseball.mlb.adapter import MLBAdapter

class AdapterFactory:

    @staticmethod
    def load(sport: str, league: str):
        if sport == "baseball" and league == "MLB":
            return MLBAdapter()

        raise ValueError(f"No existe adapter para {sport} - {league}")
