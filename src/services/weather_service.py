import aiohttp
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import os

class WeatherService:
    def __init__(self):
        self.api_key = os.getenv("WEATHER_API_KEY")
        if not self.api_key:
            print("WARNING: WEATHER_API_KEY not found in environment variables")
        else:
            print(f"Weather API Key loaded: {self.api_key[:10]}...")  # Debug print
        self.base_url = "https://api.openweathermap.org/data/2.5"

    async def _get_forecast(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Get current weather for coordinates"""
        try:
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "imperial"  # Use Fahrenheit
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/weather"
                print(f"Making weather request to: {url}")
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        print(f"Weather API error: {await response.text()}")
                        return None
                        
                    data = await response.json()
                    return {
                        "temperature": round(data['main']['temp']),
                        "description": data['weather'][0]['description'],
                        "humidity": data['main']['humidity'],
                        "wind_speed": round(data['wind']['speed'])
                    }
                    
        except Exception as e:
            print(f"Error getting forecast: {e}")
            return None

    def _get_stadium_info(self, city: str) -> Optional[Tuple[Tuple[float, float], bool, str]]:
        """Get stadium coordinates and indoor/outdoor status"""
        stadiums = {
            # MLB Stadiums
            "boston": ((42.3467, -71.0972), False, "Fenway Park"),
            "new york yankees": ((40.8296, -73.9262), False, "Yankee Stadium"),
            "tampa bay": ((27.7682, -82.6534), True, "Tropicana Field"),
            "baltimore": ((39.2838, -76.6215), False, "Oriole Park at Camden Yards"),
            "toronto": ((43.6416, -79.3891), True, "Rogers Centre"),
            "chicago cubs": ((41.9484, -87.6553), False, "Wrigley Field"),
            "chicago white sox": ((41.8299, -87.6338), False, "Guaranteed Rate Field"),
            "houston": ((29.7573, -95.3555), True, "Minute Maid Park"),
            "la angels": ((33.8003, -117.8827), False, "Angel Stadium"),
            "la dodgers": ((34.0739, -118.2400), False, "Dodger Stadium"),
            "san francisco": ((37.7786, -122.3893), False, "Oracle Park"),
            "oakland": ((37.7516, -122.2005), False, "Oakland Coliseum"),
            "seattle": ((47.5915, -122.3317), True, "T-Mobile Park"),
            "texas": ((32.7512, -97.0832), True, "Globe Life Field"),
            "arizona": ((33.4453, -112.0667), True, "Chase Field"),
            
            # NFL Stadiums (Outdoor)
            "green bay": ((44.5013, -88.0622), False, "Lambeau Field"),
            "buffalo": ((42.7738, -78.7870), False, "Highmark Stadium"),
            "miami": ((25.9580, -80.2389), False, "Hard Rock Stadium"),
            "kansas city": ((39.0489, -94.4839), False, "Arrowhead Stadium"),
            "chicago": ((41.8623, -87.6167), False, "Soldier Field"),
            
            # NFL Stadiums (Indoor)
            "dallas": ((32.7473, -97.0945), True, "AT&T Stadium"),
            "detroit": ((42.3400, -83.0456), True, "Ford Field"),
            "minnesota": ((44.9736, -93.2575), True, "U.S. Bank Stadium"),
            
            # NBA Stadiums (All Indoor)
            "phoenix": ((33.4457, -112.0712), True, "Footprint Center"),
            "brooklyn": ((40.6828, -73.9758), True, "Barclays Center"),
            "philadelphia": ((39.9012, -75.1720), True, "Wells Fargo Center"),
            "denver": ((39.7487, -105.0077), True, "Ball Arena"),
            "chicago": ((41.8807, -87.6742), True, "United Center"),
            
            # MLB Stadiums (All Outdoor except noted)
            "boston": ((42.3467, -71.0972), False, "Fenway Park"),
            "new york": ((40.8296, -73.9262), False, "Yankee Stadium"),
            "san francisco": ((37.7786, -122.3893), False, "Oracle Park"),
            "chicago cubs": ((41.9484, -87.6553), False, "Wrigley Field"),
            "chicago sox": ((41.8299, -87.6338), False, "Guaranteed Rate Field"),
            "los angeles": ((34.0739, -118.2400), False, "Dodger Stadium"),
            "st louis": ((38.6226, -90.1928), False, "Busch Stadium"),
            "houston": ((29.7573, -95.3555), True, "Minute Maid Park"),  # Retractable roof
            "arizona": ((33.4453, -112.0667), True, "Chase Field"),  # Retractable roof
            "toronto": ((43.6416, -79.3891), True, "Rogers Centre"),  # Retractable roof
            "seattle": ((47.5915, -122.3317), True, "T-Mobile Park"),  # Retractable roof
            "atlanta": ((33.8907, -84.4677), False, "Truist Park"),
            "cincinnati": ((39.0979, -84.5088), False, "Great American Ball Park"),
            "cleveland": ((41.4962, -81.6852), False, "Progressive Field"),
            "colorado": ((39.7559, -104.9942), False, "Coors Field")
        }
        
        stadium = stadiums.get(city.lower())
        if not stadium:
            print(f"Stadium not found for city: {city}")
            print(f"Available cities: {', '.join(stadiums.keys())}")
        return stadium

    def _get_team_city(self, team_name: str) -> Optional[str]:
        """Convert team name to city"""
        team_cities = {
            # MLB Teams
            "Boston Red Sox": "boston",
            "New York Yankees": "new york yankees",
            "Tampa Bay Rays": "tampa bay",
            "Baltimore Orioles": "baltimore",
            "Toronto Blue Jays": "toronto",
            "Chicago Cubs": "chicago cubs",
            "Chicago White Sox": "chicago white sox",
            "Houston Astros": "houston",
            "Los Angeles Angels": "la angels",
            "Los Angeles Dodgers": "la dodgers",
            "San Francisco Giants": "san francisco",
            "Oakland Athletics": "oakland",
            "Seattle Mariners": "seattle",
            "Texas Rangers": "texas",
            "Arizona Diamondbacks": "arizona",
            
            # NBA Teams
            "Phoenix Suns": "phoenix",
            "Brooklyn Nets": "brooklyn",
            "Philadelphia 76ers": "philadelphia",
            "Los Angeles Lakers": "los angeles",
            "Denver Nuggets": "denver",
            "Chicago Bulls": "chicago",
            
            # NFL Teams
            "Green Bay Packers": "green bay",
            "Buffalo Bills": "buffalo",
            "Miami Dolphins": "miami",
            "Kansas City Chiefs": "kansas city",
            "Chicago Bears": "chicago",
            "Dallas Cowboys": "dallas",
        }
        
        return team_cities.get(team_name)

    async def get_stadium_weather(self, team_name: str, game_date: str) -> Optional[Dict[str, Any]]:
        """Get weather for stadium location"""
        try:
            print(f"\n=== Weather Request Debug ===")
            print(f"Team name: {team_name}")
            print(f"API Key: {self.api_key[:10]}...")
            
            city = self._get_team_city(team_name)
            print(f"Mapped city: {city}")
            
            if not city:
                print(f"❌ Could not determine city for team: {team_name}")
                return None
                
            print(f"Looking up stadium for city: {city}")
            stadium_info = self._get_stadium_info(city)
            if not stadium_info:
                print(f"❌ No stadium found for city: {city}")
                return None
                
            coords, is_indoor, stadium_name = stadium_info
            print(f"✓ Found stadium: {stadium_name}")
            print(f"✓ Coordinates: {coords}")
            print(f"✓ Indoor: {is_indoor}")
            
            # Return controlled environment for indoor stadiums
            if is_indoor:
                print("Indoor stadium - returning controlled environment")
                return {
                    "stadium": stadium_name,
                    "is_indoor": True,
                    "description": "Climate controlled indoor stadium",
                    "temperature": 72,  # Standard indoor temp
                    "humidity": 45,     # Standard indoor humidity
                    "wind_speed": 0
                }
            
            # Get outdoor weather forecast
            lat, lon = coords
            print(f"Getting forecast for coordinates: {lat}, {lon}")
            forecast = await self._get_forecast(lat, lon)
            if forecast:
                print(f"Got forecast: {forecast}")
                return {
                    "stadium": stadium_name,
                    "is_indoor": False,
                    **forecast
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting stadium weather: {e}")
            print(f"Full error: {repr(e)}")
            return None 