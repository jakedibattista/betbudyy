import asyncio
from bet_parser.parser import BetParser
import os
from dotenv import load_dotenv
from services.sportradar_service import SportradarService
from web_interface import run_app

def main():
    # Load environment variables
    load_dotenv()
    
    # Verify required environment variables
    required_vars = [
        "GEMINI_API_KEY",
        "ODDS_API_KEY",
        "SPORTRADAR_API_KEY",
        "WEATHER_API_KEY"
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"{var} not found in environment variables")
        print(f"Loaded {var}: {os.getenv(var)[:10]}...")
    
    # Run the Flask app
    run_app()

if __name__ == "__main__":
    main()

async def main():
    # Test Sportradar API first
    sportradar = SportradarService()
    hierarchy = await sportradar.get_league_hierarchy()
    if hierarchy:
        print("Sportradar API is working")
        if hierarchy.get("conferences"):
            print(f"First conference: {hierarchy['conferences'][0]['name']}")
    else:
        print("Could not access Sportradar API")
        return  # Exit if we can't access the API

    # Continue with the rest of the program
    parser = BetParser()
    
    print("\nWelcome to BetBuddy! Type 'quit' to exit")
    print("Example bets:")
    print("- Team vs team: 'chiefs beat eagles'")
    print("- Player props: 'mahomes over 300 passing yards'")
    
    while True:
        try:
            # Get raw input
            raw_input = input("\nEnter bet: ")
            if raw_input.lower() in ['quit', 'exit', 'q']:
                break
            
            # Clean the input
            text = raw_input.lower().strip()
            if "enter bet" in text:
                text = text.split("enter bet")[-1].strip(': ')
            
            print(f"Processing bet: {text}")
            
            # Parse bet
            bet = await parser.parse(text)
            print(f"\n=== Analysis for bet: {text} ===")
            
            # Display basic info
            print(f"Bet type: {bet.bet_type}")
            if bet.bet_type == "game_winner":
                print(f"Teams: {bet.team_away} @ {bet.team_home}")
                print(f"Game date: {bet.game_date}")
                
                # Display odds if available
                if bet.odds:
                    print("\nBetting odds:")
                    for book, odds in bet.odds.items():
                        print(f"{book.title()}: {bet.team_home} {odds['home']} | {bet.team_away} {odds['away']}")
                
                # Display team stats if available
                if bet.analysis and bet.analysis.get("team_stats"):
                    stats = bet.analysis["team_stats"]
                    print("\nTEAM COMPARISON:")
                    
                    for matchup in stats["key_matchups"]:
                        print(f"\n{matchup['category']} Stats:")
                        for stat in matchup["stats"]:
                            print(f"{stat['name']}:")
                            print(f"  {bet.team_home}: {stat[bet.team_home]}")
                            print(f"  {bet.team_away}: {stat[bet.team_away]}")
                
                # Display weather if available
                if bet.weather:
                    print("\nVenue & Weather:")
                    print(f"Stadium: {bet.weather['stadium']}")
                    if bet.weather.get('is_indoor'):
                        print("Indoor stadium - Climate controlled environment")
                    else:
                        print(f"Forecast for: {bet.weather['forecast_time']}")
                        print(f"Temperature: {bet.weather['temperature']}°F")
                        print(f"Conditions: {bet.weather['description']}")
                        print(f"Wind: {bet.weather['wind_speed']} mph")
                        print(f"Humidity: {bet.weather['humidity']}%")
            
        except Exception as e:
            print(f"Error processing bet: {str(e)}") 