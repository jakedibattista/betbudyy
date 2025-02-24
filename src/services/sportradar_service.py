import aiohttp
from typing import Dict, Any, Optional
import os
from datetime import datetime, timedelta

class SportradarService:
    def __init__(self):
        try:
            self.api_key = os.getenv("SPORTRADAR_API_KEY")
            if not self.api_key:
                print("WARNING: SPORTRADAR_API_KEY not found in environment variables")
            else:
                print(f"Loaded API key: {self.api_key[:5]}...")
            
            # Update base URL to use NBA trial API
            self.base_url = "https://api.sportradar.us"
            # Cache for injury data
            self._injury_cache = {}
            self._cache_duration = timedelta(minutes=15)  # Cache for 15 minutes
        except Exception as e:
            print(f"Error initializing SportradarService: {e}")
        
    async def get_team_comparison(self, home_team: str = None, away_team: str = None) -> Optional[Dict[str, Any]]:
        """Get and compare seasonal statistics for both teams"""
        try:
            params = {"api_key": self.api_key}
            
            async with aiohttp.ClientSession() as session:
                # First get the schedule to find team IDs
                schedule_url = f"{self.base_url}/nfl/trial/v7/en/games/2024/PST/schedule.json"
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
                    home_url = f"{self.base_url}/nfl/trial/v7/en/teams/{home_id}/profile.json"
                    away_url = f"{self.base_url}/nfl/trial/v7/en/teams/{away_id}/profile.json"
                    
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
                url = f"{self.base_url}/nfl/trial/v7/en/league/hierarchy.json"
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

    def _normalize_team_name(self, team_name: str) -> str:
        """Normalize team name to match Sportradar format"""
        # Common variations to standardize
        replacements = {
            "76ers": "Philadelphia 76ers",
            "Sixers": "Philadelphia 76ers",
            "Blazers": "Portland Trail Blazers",
            "Wolves": "Minnesota Timberwolves",
            "Cavs": "Cleveland Cavaliers",
            "Mavs": "Dallas Mavericks"
        }

        # First check direct replacements
        for key, value in replacements.items():
            if key in team_name:
                return value

        # Handle special cases
        if "Portland" in team_name:
            return "Portland Trail Blazers"
        if "Golden State" in team_name:
            return "Golden State Warriors"
        if "LA " in team_name or "Los Angeles" in team_name:
            if "Clippers" in team_name:
                return "Los Angeles Clippers"
            if "Lakers" in team_name:
                return "Los Angeles Lakers"

        # Add city if missing
        team_cities = {
            "Jazz": "Utah Jazz",
            "Heat": "Miami Heat",
            "Hornets": "Charlotte Hornets",
            "Rockets": "Houston Rockets",
            "Warriors": "Golden State Warriors",
            "Nets": "Brooklyn Nets",
            "Knicks": "New York Knicks",
            "Celtics": "Boston Celtics",
            "Bulls": "Chicago Bulls",
            "Suns": "Phoenix Suns"
        }
        
        for key, value in team_cities.items():
            if key in team_name:
                return value

        return team_name

    def _get_team_id(self, team_name: str) -> Optional[str]:
        """Convert team name to Sportradar ID"""
        # First normalize the team name
        normalized_name = self._normalize_team_name(team_name)
        print(f"Normalized team name: {team_name} -> {normalized_name}")
        
        # NBA team IDs from Sportradar documentation
        team_ids = {
            # Eastern Conference
            "Boston Celtics": "583eccfa-fb46-11e1-82cb-f4ce4684ea4c",
            "Brooklyn Nets": "583ec9d6-fb46-11e1-82cb-f4ce4684ea4c",
            "New York Knicks": "583ec70e-fb46-11e1-82cb-f4ce4684ea4c",
            "Philadelphia 76ers": "583ec87d-fb46-11e1-82cb-f4ce4684ea4c",
            "Toronto Raptors": "583ecda6-fb46-11e1-82cb-f4ce4684ea4c",
            "Chicago Bulls": "583ec5fd-fb46-11e1-82cb-f4ce4684ea4c",
            "Cleveland Cavaliers": "583ec773-fb46-11e1-82cb-f4ce4684ea4c",
            "Detroit Pistons": "583ec928-fb46-11e1-82cb-f4ce4684ea4c",
            "Indiana Pacers": "583ec7cd-fb46-11e1-82cb-f4ce4684ea4c",
            "Milwaukee Bucks": "583ecefd-fb46-11e1-82cb-f4ce4684ea4c",
            "Atlanta Hawks": "583ecb3a-fb46-11e1-82cb-f4ce4684ea4c",
            "Charlotte Hornets": "583ec97e-fb46-11e1-82cb-f4ce4684ea4c",
            "Miami Heat": "583ecea6-fb46-11e1-82cb-f4ce4684ea4c",
            "Orlando Magic": "583ed157-fb46-11e1-82cb-f4ce4684ea4c",
            "Washington Wizards": "583ec8d4-fb46-11e1-82cb-f4ce4684ea4c",
            
            # Western Conference
            "Denver Nuggets": "583ed102-fb46-11e1-82cb-f4ce4684ea4c",
            "Minnesota Timberwolves": "583eca2f-fb46-11e1-82cb-f4ce4684ea4c",
            "Oklahoma City Thunder": "583ecfff-fb46-11e1-82cb-f4ce4684ea4c",
            "Portland Trail Blazers": "583ed056-fb46-11e1-82cb-f4ce4684ea4c",
            "Utah Jazz": "583ece50-fb46-11e1-82cb-f4ce4684ea4c",
            "Golden State Warriors": "583ec825-fb46-11e1-82cb-f4ce4684ea4c",
            "Los Angeles Clippers": "583ecdfb-fb46-11e1-82cb-f4ce4684ea4c",
            "Los Angeles Lakers": "583ecae2-fb46-11e1-82cb-f4ce4684ea4c",
            "Phoenix Suns": "583ecfa8-fb46-11e1-82cb-f4ce4684ea4c",
            "Sacramento Kings": "583ed0ac-fb46-11e1-82cb-f4ce4684ea4c",
            "Dallas Mavericks": "583ecf50-fb46-11e1-82cb-f4ce4684ea4c",
            "Houston Rockets": "583ecb8f-fb46-11e1-82cb-f4ce4684ea4c",
            "Memphis Grizzlies": "583eca88-fb46-11e1-82cb-f4ce4684ea4c",
            "New Orleans Pelicans": "583ecc9a-fb46-11e1-82cb-f4ce4684ea4c",
            "San Antonio Spurs": "583ecd4f-fb46-11e1-82cb-f4ce4684ea4c"
        }
        
        team_id = team_ids.get(normalized_name)
        if not team_id:
            print(f"No team ID found for: {normalized_name}")
            # Try to find a partial match
            for known_name, known_id in team_ids.items():
                if normalized_name.lower() in known_name.lower():
                    print(f"Found partial match: {known_name}")
                    return known_id
        return team_id

    async def get_injuries(self, team: str) -> Optional[Dict[str, Any]]:
        """Get team injury report with caching"""
        try:
            # Check cache first
            if team in self._injury_cache:
                cache_time, cache_data = self._injury_cache[team]
                if datetime.now() - cache_time < self._cache_duration:
                    print(f"Using cached injury data for {team}")
                    return cache_data

            print(f"\nFetching injuries for: {team}")
            team_id = self._get_team_id(team)
            if not team_id:
                print(f"Could not find team ID for: {team}")
                return None
                
            url = f"{self.base_url}/nba/trial/v8/en/teams/{team_id}/injuries.json"
            params = {"api_key": self.api_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 429:  # Rate limit
                        print("Rate limit hit, using cached data if available")
                        return self._injury_cache.get(team, (None, None))[1]
                        
                    if response.status != 200:
                        return None
                        
                    data = await response.json()
                    injuries = self._format_injuries(data)
                    
                    # Cache the result
                    self._injury_cache[team] = (datetime.now(), injuries)
                    return injuries
                    
        except Exception as e:
            print(f"Error getting injuries: {str(e)}")
            return None
            
    def _format_injuries(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format injury data into standardized structure"""
        injuries = []
        for player in data.get('players', []):
            if player.get('injuries'):
                injuries.append({
                    "name": player.get('name'),
                    "position": player.get('position'),
                    "status": player.get('injuries')[0].get('status'),
                    "description": player.get('injuries')[0].get('desc'),
                    "practice_status": player.get('injuries')[0].get('practice_status')
                })
        return injuries 