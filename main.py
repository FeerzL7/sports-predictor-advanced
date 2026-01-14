from core.interfaces.adapter_factory import AdapterFactory

def main():
    sport = "baseball"
    league = "MLB"
    date = "2026-01-14"

    adapter = AdapterFactory.load(sport, league)
    events = adapter.get_events(date)

    for event in events:
        analysis = adapter.analyze_event(event)
        picks = adapter.generate_picks(analysis)
        print(picks)

if __name__ == "__main__":
    main()
