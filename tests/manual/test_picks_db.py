# tests/manual/test_picks_db.py

from core.storage.picks_db import PicksDatabase
from datetime import datetime


def test_save_event():
    """Test guardar evento."""
    db = PicksDatabase("data/test_picks.db")
    
    event_id = db.save_event(
        event_id="mlb_2026_001",
        sport="baseball",
        league="MLB",
        date="2026-04-15",
        home_team="Yankees",
        away_team="Red Sox",
        venue="Yankee Stadium"
    )
    
    print(f"✅ Event saved with ID: {event_id}")


def test_save_pick():
    """Test guardar pick."""
    db = PicksDatabase("data/test_picks.db")
    
    pick = {
        "event_id": "mlb_2026_001",
        "market": "moneyline",
        "side": "home",
        "team": "Yankees",
        "odds": 1.85,
        "odds_format": "decimal",
        "model_prob": 0.568,
        "implied_prob": 0.541,
        "edge": 0.050,
        "confidence": 0.634,
        "stake_pct": 0.0125,
        "stake": 125.00,
        "reason": "Monte Carlo ML with bullpen adjustment",
        "correlation_reason": "Neutral correlation"
    }
    
    pick_id = db.save_pick(pick)
    print(f"✅ Pick saved with ID: {pick_id}")
    
    return pick_id


def test_get_picks():
    """Test recuperar picks."""
    db = PicksDatabase("data/test_picks.db")
    
    # Pending
    pending = db.get_pending_picks()
    print(f"\n📊 Pending picks: {len(pending)}")
    
    if pending:
        print(f"   First: {pending[0]['market']} | {pending[0]['team']}")
    
    # Recent
    recent = db.get_recent_picks(limit=5)
    print(f"\n📊 Recent picks: {len(recent)}")
    
    for p in recent:
        print(f"   - {p['market']} | {p['team']} | Edge: {p['edge']*100:.1f}%")


def test_update_result():
    """Test actualizar resultado."""
    db = PicksDatabase("data/test_picks.db")
    
    # Obtener primer pick pendiente
    pending = db.get_pending_picks()
    
    if pending:
        pick = pending[0]
        pick_id = pick['id']
        stake = pick['stake_amount']
        odds = pick['odds']
        
        # Simular WIN
        profit = stake * (odds - 1)
        
        success = db.update_result(
            pick_id=pick_id,
            result="WIN",
            actual_outcome="5-3 Yankees",
            profit=profit
        )
        
        if success:
            print(f"\n✅ Pick {pick_id} updated: WIN | Profit: ${profit:.2f}")
            
            # Ver pick actualizado
            updated = db.get_pick(pick_id)
            print(f"   ROI: {updated['roi']*100:.1f}%")
    else:
        print("\n⚠️  No pending picks to update")


def test_performance_stats():
    """Test estadísticas de performance."""
    db = PicksDatabase("data/test_picks.db")
    
    stats = db.get_performance_stats()
    
    print("\n" + "=" * 60)
    print("PERFORMANCE STATS")
    print("=" * 60)
    print(f"Total Picks: {stats['total_picks']}")
    print(f"Wins: {stats['wins']}")
    print(f"Losses: {stats['losses']}")
    print(f"Pushes: {stats['pushes']}")
    print(f"Pending: {stats['pending']}")
    print(f"Win Rate: {stats['win_rate']*100:.1f}%")
    print(f"Total Stake: ${stats['total_stake']:.2f}")
    print(f"Total Profit: ${stats['total_profit']:.2f}")
    print(f"ROI: {stats['roi']*100:.1f}%")
    print(f"Avg Edge: {stats['avg_edge']*100:.1f}%")
    print(f"Avg Confidence: {stats['avg_confidence']*100:.1f}%")


def test_performance_by_market():
    """Test performance por mercado."""
    db = PicksDatabase("data/test_picks.db")
    
    by_market = db.get_performance_by_market()
    
    print("\n" + "=" * 60)
    print("PERFORMANCE BY MARKET")
    print("=" * 60)
    
    for market in by_market:
        print(f"\n{market['market'].upper()}:")
        print(f"  Picks: {market['total_picks']}")
        print(f"  Win Rate: {market['win_rate']*100:.1f}%")
        print(f"  ROI: {market['roi']*100:.1f}%")
        print(f"  Profit: ${market['total_profit']:.2f}")


if __name__ == "__main__":
    print("=" * 60)
    print("TEST 1: Save Event")
    print("=" * 60)
    test_save_event()
    
    print("\n" + "=" * 60)
    print("TEST 2: Save Pick")
    print("=" * 60)
    pick_id = test_save_pick()
    
    print("\n" + "=" * 60)
    print("TEST 3: Get Picks")
    print("=" * 60)
    test_get_picks()
    
    print("\n" + "=" * 60)
    print("TEST 4: Update Result")
    print("=" * 60)
    test_update_result()
    
    print("\n" + "=" * 60)
    print("TEST 5: Performance Stats")
    print("=" * 60)
    test_performance_stats()
    
    print("\n" + "=" * 60)
    print("TEST 6: Performance by Market")
    print("=" * 60)
    test_performance_by_market()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("Database file: data/test_picks.db")
    print("=" * 60)