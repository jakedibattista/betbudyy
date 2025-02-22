import aiohttp
from typing import Dict, Any, Optional
import os
from datetime import datetime

class SportradarService:
    def __init__(self):
        try:
            self.api_key = os.getenv("SPORTRADAR_API_KEY")
            if not self.api_key:
                print("WARNING: SPORTRADAR_API_KEY not found in environment variables")
            else:
                print(f"Loaded API key: {self.api_key[:5]}...")
            
            # Use trial API endpoint
            self.base_url = "https://api.sportradar.us/nfl/trial/v7/en"
        except Exception as e:
            print(f"Error initializing SportradarService: {e}")
        
    async def get_team_comparison(self, home_team: str = None, away_team: str = None) -> Optional[Dict[str, Any]]:
        """Get and compare seasonal statistics for both teams"""
        try:
            params = {"api_key": self.api_key}
            
            async with aiohttp.ClientSession() as session:
                # First get the schedule to find team IDs
                schedule_url = f"{self.base_url}/games/2024/PST/schedule.json"
                print(f"Getting schedule to find team IDs...")
                
                async with session.get(schedule_url, params=params) as schedule_response:
                    if schedule_response.status != 200:
                        print(f"Error getting schedule: {await schedule_response.text()}")
                        return None
                        
                    schedule_data = await schedule_response.json()
                    
                    # Find team IDs from schedule
                    home_id = None
                    away_id = None
                    
                    for week in schedule_data.get("weeks", []):
                        for game in week.get("games", []):
                            if game.get("home", {}).get("name") == home_team:
                                home_id = game["home"]["id"]
                            if game.get("away", {}).get("name") == away_team:
                                away_id = game["away"]["id"]
                    
                    if not (home_id and away_id):
                        print(f"Could not find team IDs in schedule")
                        return None
                    
                    print(f"Found team IDs - Home: {home_id}, Away: {away_id}")
                    
                    # Now get team profiles using IDs
                    home_url = f"{self.base_url}/teams/{home_id}/profile.json"
                    away_url = f"{self.base_url}/teams/{away_id}/profile.json"
                    
                    print(f"Getting team profiles...")
                    
                    async with session.get(home_url, params=params) as home_response:
                        if home_response.status != 200:
                            print(f"Error getting {home_team} profile: {await home_response.text()}")
                            return None
                        home_stats = await home_response.json()
                        print(f"Got {home_team} profile")
                    
                    async with session.get(away_url, params=params) as away_response:
                        if away_response.status != 200:
                            print(f"Error getting {away_team} profile: {await away_response.text()}")
                            return None
                        away_stats = await away_response.json()
                        print(f"Got {away_team} profile")
                    
                    return self._format_team_comparison(home_stats, away_stats, home_team, away_team)
                
        except Exception as e:
            print(f"Error getting team stats: {str(e)}")
            print(f"Full error: {repr(e)}")  # More detailed error info
            return None

    def _format_team_comparison(self, home_stats: Dict, away_stats: Dict, home_team: str, away_team: str) -> Dict[str, Any]:
        """Format key statistics comparison between teams"""
        
        def get_team_stats(stats: Dict) -> Dict:
            record = stats.get("record", {})
            return {
                "offense": {
                    "points_per_game": record.get("points", 0) / max(record.get("games_played", 1), 1),
                    "total_yards": record.get("offense", {}).get("total_yards", 0),
                    "passing_yards": record.get("passing", {}).get("yards", 0),
                    "rushing_yards": record.get("rushing", {}).get("yards", 0),
                    "third_down_pct": record.get("efficiency", {}).get("thirddown", {}).get("pct", 0),
                    "redzone_pct": record.get("efficiency", {}).get("redzone", {}).get("pct", 0),
                    "turnovers": (
                        record.get("passing", {}).get("interceptions", 0) + 
                        record.get("fumbles", {}).get("lost_fumbles", 0)
                    )
                },
                "defense": {
                    "points_allowed_per_game": record.get("points_against", 0) / max(record.get("games_played", 1), 1),
                    "sacks": record.get("defense", {}).get("sacks", 0),
                    "interceptions": record.get("defense", {}).get("interceptions", 0),
                    "forced_fumbles": record.get("defense", {}).get("forced_fumbles", 0),
                    "third_down_stops_pct": 100 - record.get("efficiency", {}).get("thirddown", {}).get("pct", 0),
                    "redzone_stops_pct": 100 - record.get("efficiency", {}).get("redzone", {}).get("pct", 0)
                }
            }

        home_team_stats = get_team_stats(home_stats)
        away_team_stats = get_team_stats(away_stats)

        return {
            "teams": {
                home_team: home_team_stats,
                away_team: away_team_stats
            },
            "key_matchups": [
                {
                    "category": "Offense",
                    "stats": [
                        {
                            "name": "Points Per Game",
                            home_team: round(home_team_stats["offense"]["points_per_game"], 1),
                            away_team: round(away_team_stats["offense"]["points_per_game"], 1)
                        },
                        {
                            "name": "Total Yards",
                            home_team: home_team_stats["offense"]["total_yards"],
                            away_team: away_team_stats["offense"]["total_yards"]
                        },
                        {
                            "name": "3rd Down %",
                            home_team: f"{home_team_stats['offense']['third_down_pct']}%",
                            away_team: f"{away_team_stats['offense']['third_down_pct']}%"
                        }
                    ]
                },
                {
                    "category": "Defense",
                    "stats": [
                        {
                            "name": "Points Allowed/Game",
                            home_team: round(home_team_stats["defense"]["points_allowed_per_game"], 1),
                            away_team: round(away_team_stats["defense"]["points_allowed_per_game"], 1)
                        },
                        {
                            "name": "Sacks",
                            home_team: home_team_stats["defense"]["sacks"],
                            away_team: away_team_stats["defense"]["sacks"]
                        },
                        {
                            "name": "Takeaways",
                            home_team: home_team_stats["defense"]["interceptions"] + home_team_stats["defense"]["forced_fumbles"],
                            away_team: away_team_stats["defense"]["interceptions"] + away_team_stats["defense"]["forced_fumbles"]
                        }
                    ]
                }
            ]
        } 

    async def get_league_hierarchy(self) -> Optional[Dict[str, Any]]:
        """Get basic NFL league structure - most basic endpoint to test API"""
        try:
            params = {"api_key": self.api_key}
            
            async with aiohttp.ClientSession() as session:
                # Use the league hierarchy endpoint - most basic endpoint
                url = f"{self.base_url}/league/hierarchy.json"
                print(f"Testing API with league hierarchy endpoint...")
                print(f"URL: {url}")
                print(f"API Key: {self.api_key[:10]}...")  # Show first 10 chars to verify key
                
                async with session.get(url, params=params) as response:
                    print(f"Response status: {response.status}")
                    if response.status != 200:
                        print(f"Error: {await response.text()}")
                        return None
                        
                    data = await response.json()
                    print("Successfully got league data")
                    return data
                    
        except Exception as e:
            print(f"Error accessing Sportradar API: {str(e)}")
            print(f"Full error: {repr(e)}")
            return None 