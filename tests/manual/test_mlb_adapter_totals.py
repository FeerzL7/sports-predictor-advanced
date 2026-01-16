# tests/manual/test_mlb_adapter_totals.py

from sports.baseball.mlb.adapter import MLBAdapter

# =========================
# CONFIG
# =========================
DATE = "2024-07-15"  # usa una fecha con juegos reales
ODDS_API_KEY = None  # pon tu key real o deja None para testear sin odds

# =========================
# TEST
# =========================
def main():
    adapter = MLBAdapter(odds_api_key=ODDS_API_KEY)

    print("\n[TEST] Cargando eventos...")
    events = adapter.get_events(DATE)

    if not events:
        print("❌ No se cargaron eventos")
        return

    print(f"✔ Eventos cargados: {len(events)}")

    # Tomamos solo el primer juego
    event = events[0]

    print("\n[TEST] Analizando evento...")
    analysis = adapter.analyze_event(event)

    print("\n=== ANALYSIS ===")
    print("Teams:", analysis["teams"])
    print("Projections:", analysis["projections"])
    print("Confidence:", analysis["confidence"])
    print("Flags:", analysis["flags"])
    print("Market:", analysis.get("market"))

    print("\n[TEST] Generando picks...")
    picks = adapter.generate_picks(analysis)

    print("\n=== PICKS ===")
    if not picks:
        print("⚠️ No se generó pick (puede ser normal)")
    else:
        for p in picks:
            print(p)


if __name__ == "__main__":
    main()
