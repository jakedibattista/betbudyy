import asyncio
from src.services.odds_service import OddsService

async def test_odds():
    service = OddsService()
    try:
        # Test getting sports
        print("\nTesting get_sports()...")
        sports = await service.get_sports()
        print("NFL found:", any(s['key'] == 'americanfootball_nfl' for s in sports))
        
        # Test getting NFL odds
        print("\nTesting get_odds()...")
        odds = await service.get_odds()
        print(f"Number of NFL games found: {len(odds) if odds else 0}")
        
        # Test finding specific game
        print("\nTesting find_game_odds()...")
        game_odds = await service.find_game_odds("Chiefs", "Eagles")
        if game_odds and game_odds.get('available'):
            print(f"Found game odds:")
            print(f"Home team: {game_odds['home_team']}")
            print(f"Away team: {game_odds['away_team']}")
            print(f"Game date: {game_odds['game_date']}")
            print("\nOdds by bookmaker:")
            for book, odds in game_odds['odds'].items():
                print(f"{book}: Home {odds['home']} | Away {odds['away']}")
        else:
            print(f"Game odds not found: {game_odds}")
    
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_odds()) 