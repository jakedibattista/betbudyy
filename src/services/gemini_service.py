import google.generativeai as genai
from typing import Dict, Any, Optional
import os
import json
from ..config.settings import Settings
from ..services.odds_service import OddsService
from ..services.sportradar_service import SportradarService

class GeminiService:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-pro')
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40
        }
    
    async def analyze_bet_type(self, bet_text: str) -> Dict[str, Any]:
        """
        Step 0: Identify the type of bet and basic information
        """
        prompt = f"""
        Analyze this sports bet and return a JSON object.
        Bet: "{bet_text}"

        Return ONLY a JSON object like this:
        For game winners:
        {{
            "bet_type": "game_winner",
            "teams": ["Chiefs", "Eagles"],
            "sport": "NFL"
        }}

        For player props:
        {{
            "bet_type": "player_prop",
            "player": "Patrick Mahomes",
            "team": "Chiefs",
            "prop_type": "passing_yards",
            "prop_value": 300,
            "sport": "NFL"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            print(f"Raw response: {response.text}")  # Debug print
            cleaned_text = response.text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            print(f"Cleaned text: {cleaned_text}")  # Debug print
            return json.loads(cleaned_text)
        except Exception as e:
            print(f"Error in analyze_bet_type: {str(e)}")
            return {
                "bet_type": "game_winner",
                "teams": bet_text.lower().replace(" beat ", " ").split(),
                "sport": "NFL"
            }

    async def get_betting_odds(self, bet_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Step 1: Look up available betting odds
        """
        if bet_info.get("bet_type") == "game_winner":
            # Clean and standardize team names
            team1 = bet_info.get('teams', ['Unknown'])[0].strip().title()
            team2 = bet_info.get('teams', ['', 'Unknown'])[1].strip().title()
            
            # Use OddsService to get real odds
            odds_service = OddsService()
            return await odds_service.find_game_odds(team1, team2)
        
        return {
            "available": False,
            "reason": "Not a game winner bet"
        }

    async def get_event_location(self, bet_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Step 2: Get event location details
        """
        if bet_info.get("bet_type") == "game_winner":
            prompt = f"""
            You are a sports venue analyst. Find the game location:
            Sport: {bet_info.get('sport')}
            Teams: {bet_info['teams'][0]} vs {bet_info['teams'][1]}
            
            Return a JSON object with:
            {{
                "venue": {{
                    "name": "Stadium Name",
                    "city": "City",
                    "state": "State",
                    "indoor": true/false
                }},
                "home_team": "team name"
            }}
            """
            return await self._get_json_response(prompt)
        return None

    async def get_weather_forecast(self, location_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Step 2b: Get weather forecast if game is outdoors
        """
        if not location_info.get("venue", {}).get("indoor", True):
            prompt = f"""
            You are a weather analyst. Get the forecast for:
            Location: {location_info['venue']['city']}, {location_info['venue']['state']}
            Venue: {location_info['venue']['name']}
            
            Return a JSON object with:
            {{
                "forecast": {{
                    "condition": "clear/rainy/snowy/etc",
                    "temperature": "XX°F",
                    "wind_speed": "XX mph",
                    "precipitation_chance": XX,
                    "humidity": XX
                }},
                "impact_level": "none/low/medium/high",
                "notes": "Any specific weather-related concerns"
            }}
            """
            return await self._get_json_response(prompt)
        return None

    async def _get_json_response(self, prompt: str) -> Dict[str, Any]:
        """
        Helper method to get and parse JSON responses from Gemini
        """
        try:
            response = self.model.generate_content(prompt)
            cleaned_text = response.text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            return json.loads(cleaned_text)
        except Exception as e:
            print(f"Error getting response: {e}")
            return {}

    async def analyze_player_prop(self, text: str) -> Dict[str, Any]:
        """Parse player prop bet"""
        prompt = f"""
        Analyze this player prop bet and return a JSON object:
        Bet: "{text}"
        
        Return this exact structure:
        {{
            "player": "Full Player Name",
            "team": "Team Name",
            "prop_type": "rushing_yards/passing_yards/etc",
            "prop_value": number,
            "over_under": "over/under"
        }}
        
        Example: "mahomes over 300 passing yards" should return:
        {{
            "player": "Patrick Mahomes",
            "team": "Kansas City Chiefs",
            "prop_type": "passing_yards",
            "prop_value": 300,
            "over_under": "over"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            result = response.text.strip()
            if result.startswith('```'):
                result = result.split('```')[1]
                if result.startswith('json'):
                    result = result[4:]
            result = result.strip()
            return json.loads(result)
        except Exception as e:
            print(f"Error analyzing player prop: {e}")
            return {
                "error": str(e)
            }

    async def analyze_player_prop_factors(self, player: str, prop_type: str, target: float) -> Optional[Dict[str, Any]]:
        """Analyze factors for a player prop bet"""
        try:
            # Get real injury data
            sportradar = SportradarService()
            injuries = await sportradar.get_injuries()
            
            prompt = f"""
            Analyze {player}'s {prop_type} prop bet for {target} yards.
            Consider these current injuries: {injuries}
            
            Return a JSON object with:
            {{
                "injuries": [
                    {{
                        "player": "Player Name",
                        "position": "Position",
                        "injury": "Type",
                        "status": "Out/Questionable/Probable",
                        "impact": "High/Medium/Low",
                        "details": "Impact description"
                    }}
                ],
                "key_factors": [
                    {{
                        "factor": "Factor description",
                        "impact": "How it affects the prop"
                    }}
                ],
                "prediction": {{
                    "call": "over/under",
                    "confidence": "High/Medium/Low",
                    "reasoning": "Explanation"
                }}
            }}
            """
            
            response = self.model.generate_content(prompt)
            result = response.text.strip()
            if result.startswith('```'):
                result = result.split('```')[1]
                if result.startswith('json'):
                    result = result[4:]
            result = result.strip()
            return json.loads(result)
        except Exception as e:
            print(f"Error analyzing player prop factors: {e}")
            return None

    async def get_game_location(self, home_team: str, away_team: str, game_date: str) -> Optional[Dict[str, Any]]:
        """Get the actual game location, accounting for neutral sites like Super Bowl"""
        prompt = f"""
        For the NFL game between {away_team} @ {home_team} on {game_date}, return ONLY a JSON object with the game location:
        {{
            "stadium": "Caesars Superdome",
            "city": "New Orleans",
            "state": "Louisiana",
            "is_neutral_site": true,
            "reason": "Super Bowl LVIII"
        }}
        Note: This is Super Bowl LVIII being played in New Orleans.
        """
        
        try:
            response = self.model.generate_content(prompt)
            result = response.text.strip()
            if result.startswith('```'):
                result = result.split('```')[1]
                if result.startswith('json'):
                    result = result[4:]
            return json.loads(result.strip())
        except Exception as e:
            print(f"Error getting game location: {e}")
            return {
                "stadium": "Caesars Superdome",
                "city": "new orleans",
                "state": "Louisiana",
                "is_neutral_site": True,
                "reason": "Super Bowl LVIII"
            }

    async def analyze_matchup(self, home_team: str, away_team: str, game_date: str) -> Optional[Dict[str, Any]]:
        """Analyze factors that could impact the game"""
        try:
            # Get real injury data from Sportradar
            sportradar = SportradarService()
            injuries = await sportradar.get_injuries()
            
            prompt = f"""
            Analyze this NFL matchup using the following injury data:
            {injuries}
            
            Game: {away_team} @ {home_team} on {game_date}
            
            Return a JSON object analyzing:
            1. How these injuries impact each team
            2. Key matchups considering injuries
            3. Betting factors to consider
            """
            
            response = self.model.generate_content(prompt)
            result = response.text.strip()
            if result.startswith('```'):
                result = result.split('```')[1]
                if result.startswith('json'):
                    result = result[4:]
            
            analysis = json.loads(result.strip())
            
            return {
                "injuries": injuries,
                "key_matchups": analysis.get("key_matchups", []),
                "betting_factors": analysis.get("betting_factors", [])
            }
            
        except Exception as e:
            print(f"Error in matchup analysis: {e}")
            return None 