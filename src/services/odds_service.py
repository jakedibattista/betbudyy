import aiohttp
import os
from typing import Dict, Any, Optional

class OddsService:
    def __init__(self):
        self.api_key = os.getenv("ODDS_API_KEY")
        if not self.api_key:
            print("WARNING: ODDS_API_KEY not found in environment variables")
        self.base_url = "https://api.the-odds-api.com/v4/sports"
    
    async def get_sports(self) -> Dict[str, Any]:
        """Get all available sports"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/sports"
            params = {"apiKey": self.api_key}
            
            async with session.get(url, params=params) as response:
                return await response.json()
    
    SUPPORTED_SPORTS = {
        'NBA': 'basketball_nba',
        'NHL': 'icehockey_nhl',
        'MLB': 'baseball_mlb'
    }
    
    async def get_odds(self, sport_key: str = None) -> Optional[Dict[str, Any]]:
        """Get odds for a specific sport"""
        try:
            if sport_key and sport_key not in self.SUPPORTED_SPORTS.values():
                print(f"Unsupported sport: {sport_key}")
                return None
                
            sport = sport_key or self.SUPPORTED_SPORTS['NBA']  # Default to NBA
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
                params = {
                    "apiKey": self.api_key,
                    "regions": "us",
                    "markets": "h2h,spreads,totals",
                    "dateFormat": "iso",
                    "oddsFormat": "american"
                }
                
                print(f"Fetching odds for {sport}...")
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        print(f"Error: {await response.text()}")
                        return None
                    
                    data = await response.json()
                    print(f"Found {len(data)} games for {sport}")
                    return data
                    
        except Exception as e:
            print(f"Error in get_odds: {str(e)}")
            return None
    
    async def find_game_odds(self, team1: str, team2: str) -> Optional[Dict[str, Any]]:
        """Find odds for a specific game"""
        odds_data = await self.get_odds()
        print(f"Looking for game: {team1} vs {team2}")  # Debug print
        
        if not odds_data:
            print("No odds data received")  # Debug print
            return None
            
        # Normalize team names for comparison
        team1 = team1.lower()
        team2 = team2.lower()
        
        for game in odds_data:
            home_team = game.get('home_team', '').lower()
            away_team = game.get('away_team', '').lower()
            print(f"Checking game: {away_team} @ {home_team}")  # Debug print
            
            # Check both combinations since we don't know which team is home/away
            if ((team1 in home_team or team1 in away_team) and 
                (team2 in home_team or team2 in away_team)):
                return {
                    "available": True,
                    "odds": self._format_odds(game),
                    "game_date": game.get('commence_time'),
                    "home_team": game['home_team'],
                    "away_team": game['away_team']
                }
        
        return {
            "available": False,
            "reason": f"No upcoming games found matching {team1} vs {team2}"
        }
    
    def _format_odds(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format odds data into our standard structure"""
        formatted_odds = {}
        
        for bookmaker in game_data.get('bookmakers', []):
            book_name = bookmaker['key']
            markets = {m['key']: m for m in bookmaker.get('markets', [])}
            
            # Get moneyline (h2h) odds
            if 'h2h' in markets:
                h2h_market = markets['h2h']
                home_odds = next((o['price'] for o in h2h_market['outcomes'] 
                                if o['name'] == game_data['home_team']), None)
                away_odds = next((o['price'] for o in h2h_market['outcomes']
                                if o['name'] == game_data['away_team']), None)
                
                formatted_odds[book_name] = {
                    "home": f"{home_odds:+d}" if home_odds else "N/A",
                    "away": f"{away_odds:+d}" if away_odds else "N/A"
                }
        
        return formatted_odds 