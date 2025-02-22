import aiohttp
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import os

class WeatherService:
    def __init__(self):
        self.base_url = "https://api.weather.gov"
        # NWS API requires a User-Agent header
        self.headers = {
            "User-Agent": "BetBuddy/1.0 (https://github.com/yourusername/betbuddy)",
            "Accept": "application/geo+json"
        }
    
    async def get_forecast(self, city: str, game_date: str) -> Optional[Dict[str, Any]]:
        """Get weather forecast for a location and specific date"""
        try:
            print(f"Getting stadium info for: {city}")  # Debug print
            stadium_info = self._get_stadium_info(city)
            if not stadium_info:
                print(f"No stadium found for {city}")
                return None
                
            coords, is_indoor, stadium_name = stadium_info
            print(f"Found stadium: {stadium_name} (Indoor: {is_indoor})")  # Debug print
            
            # Return controlled environment for indoor stadiums
            if is_indoor:
                return {
                    "temperature": 70,
                    "humidity": 50,
                    "wind_speed": 0,
                    "conditions": "Indoor Stadium",
                    "description": f"Climate controlled environment at {stadium_name}",
                    "forecast_time": game_date,
                    "is_indoor": True,
                    "stadium": stadium_name
                }
            
            # Get outdoor forecast
            async with aiohttp.ClientSession(headers=self.headers) as session:
                lat, lon = coords
                points_url = f"{self.base_url}/points/{lat},{lon}"
                async with session.get(points_url) as response:
                    points_data = await response.json()
                    forecast_url = points_data['properties']['forecast']
                    async with session.get(forecast_url) as response:
                        forecast = await response.json()
                        game_dt = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
                        
                        for period in forecast['properties']['periods']:
                            start_time = datetime.fromisoformat(period['startTime'])
                            end_time = datetime.fromisoformat(period['endTime'])
                            
                            if start_time <= game_dt <= end_time:
                                return {
                                    "temperature": period['temperature'],
                                    "humidity": period.get('relativeHumidity', {}).get('value', 0),
                                    "wind_speed": int(period['windSpeed'].split()[0]),
                                    "conditions": period['shortForecast'],
                                    "description": period['detailedForecast'],
                                    "forecast_time": period['startTime'],
                                    "is_indoor": False,
                                    "stadium": stadium_name
                                }
                        
                        return {
                            "temperature": forecast['properties']['periods'][0]['temperature'],
                            "humidity": forecast['properties']['periods'][0].get('relativeHumidity', {}).get('value', 0),
                            "wind_speed": int(forecast['properties']['periods'][0]['windSpeed'].split()[0]),
                            "conditions": forecast['properties']['periods'][0]['shortForecast'],
                            "description": forecast['properties']['periods'][0]['detailedForecast'],
                            "forecast_time": forecast['properties']['periods'][0]['startTime'],
                            "note": "Exact game time forecast not available yet",
                            "is_indoor": False,
                            "stadium": stadium_name
                        }
                    
        except Exception as e:
            print(f"Error getting weather forecast: {e}")
            return None
            
    def _get_stadium_info(self, city: str) -> Optional[Tuple[Tuple[float, float], bool, str]]:
        """Get stadium coordinates, indoor/outdoor status, and name"""
        # Format: (latitude, longitude), is_indoor, stadium_name
        stadiums = {
            # AFC East
            "bills": ((42.7738, -78.7870), False, "Highmark Stadium"),
            "dolphins": ((25.9580, -80.2389), False, "Hard Rock Stadium"),
            "patriots": ((42.0909, -71.2643), False, "Gillette Stadium"),
            "jets": ((40.8135, -74.0745), False, "MetLife Stadium"),
            
            # AFC North
            "ravens": ((39.2780, -76.6227), False, "M&T Bank Stadium"),
            "bengals": ((39.0955, -84.5161), False, "Paycor Stadium"),
            "browns": ((41.5061, -81.6995), False, "Cleveland Browns Stadium"),
            "steelers": ((40.4468, -80.0158), False, "Acrisure Stadium"),
            
            # AFC South
            "texans": ((29.6847, -95.4107), True, "NRG Stadium"),
            "colts": ((39.7601, -86.1639), True, "Lucas Oil Stadium"),
            "jaguars": ((30.3239, -81.6373), False, "TIAA Bank Field"),
            "titans": ((36.1665, -86.7713), False, "Nissan Stadium"),
            
            # AFC West
            "broncos": ((39.7439, -105.0201), False, "Empower Field at Mile High"),
            "chiefs": ((39.0489, -94.4839), False, "GEHA Field at Arrowhead Stadium"),
            "raiders": ((36.0909, -115.1833), True, "Allegiant Stadium"),
            "chargers": ((33.9534, -118.3387), True, "SoFi Stadium"),
            
            # NFC East
            "cowboys": ((32.7473, -97.0945), True, "AT&T Stadium"),
            "giants": ((40.8135, -74.0745), False, "MetLife Stadium"),
            "eagles": ((39.9013, -75.1674), False, "Lincoln Financial Field"),
            "commanders": ((38.9077, -76.8645), False, "FedExField"),
            
            # NFC North
            "bears": ((41.8623, -87.6167), False, "Soldier Field"),
            "lions": ((42.3400, -83.0456), True, "Ford Field"),
            "packers": ((44.5013, -88.0622), False, "Lambeau Field"),
            "vikings": ((44.9736, -93.2575), True, "U.S. Bank Stadium"),
            
            # NFC South
            "falcons": ((33.7555, -84.4011), True, "Mercedes-Benz Stadium"),
            "panthers": ((35.2258, -80.8528), False, "Bank of America Stadium"),
            "saints": ((29.9511, -90.0815), True, "Caesars Superdome"),
            "buccaneers": ((27.9759, -82.5033), False, "Raymond James Stadium"),
            
            # NFC West
            "cardinals": ((33.5276, -112.2626), True, "State Farm Stadium"),
            "rams": ((33.9534, -118.3387), True, "SoFi Stadium"),
            "49ers": ((37.4033, -121.9694), False, "Levi's Stadium"),
            "seahawks": ((47.5952, -122.3316), False, "Lumen Field"),
            
            # Common city names
            "arizona": ((33.5276, -112.2626), True, "State Farm Stadium"),
            "atlanta": ((33.7555, -84.4011), True, "Mercedes-Benz Stadium"),
            "baltimore": ((39.2780, -76.6227), False, "M&T Bank Stadium"),
            "buffalo": ((42.7738, -78.7870), False, "Highmark Stadium"),
            "carolina": ((35.2258, -80.8528), False, "Bank of America Stadium"),
            "chicago": ((41.8623, -87.6167), False, "Soldier Field"),
            "cincinnati": ((39.0955, -84.5161), False, "Paycor Stadium"),
            "cleveland": ((41.5061, -81.6995), False, "Cleveland Browns Stadium"),
            "dallas": ((32.7473, -97.0945), True, "AT&T Stadium"),
            "denver": ((39.7439, -105.0201), False, "Empower Field at Mile High"),
            "detroit": ((42.3400, -83.0456), True, "Ford Field"),
            "green bay": ((44.5013, -88.0622), False, "Lambeau Field"),
            "houston": ((29.6847, -95.4107), True, "NRG Stadium"),
            "indianapolis": ((39.7601, -86.1639), True, "Lucas Oil Stadium"),
            "jacksonville": ((30.3239, -81.6373), False, "TIAA Bank Field"),
            "kansas city": ((39.0489, -94.4839), False, "GEHA Field at Arrowhead Stadium"),
            "las vegas": ((36.0909, -115.1833), True, "Allegiant Stadium"),
            "los angeles": ((33.9534, -118.3387), True, "SoFi Stadium"),
            "miami": ((25.9580, -80.2389), False, "Hard Rock Stadium"),
            "minnesota": ((44.9736, -93.2575), True, "U.S. Bank Stadium"),
            "new england": ((42.0909, -71.2643), False, "Gillette Stadium"),
            "new orleans": ((29.9511, -90.0815), True, "Caesars Superdome"),
            "new york": ((40.8135, -74.0745), False, "MetLife Stadium"),
            "philadelphia": ((39.9013, -75.1674), False, "Lincoln Financial Field"),
            "pittsburgh": ((40.4468, -80.0158), False, "Acrisure Stadium"),
            "san francisco": ((37.4033, -121.9694), False, "Levi's Stadium"),
            "seattle": ((47.5952, -122.3316), False, "Lumen Field"),
            "tampa bay": ((27.9759, -82.5033), False, "Raymond James Stadium"),
            "tennessee": ((36.1665, -86.7713), False, "Nissan Stadium"),
            "washington": ((38.9077, -76.8645), False, "FedExField")
        }
        
        return stadiums.get(city.lower()) 