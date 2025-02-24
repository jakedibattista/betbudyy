from google import generativeai as genai
from google.genai import types
from typing import Optional, Dict, Any
import os
import json
from datetime import datetime, timedelta
import aiohttp
from bs4 import BeautifulSoup
from google.generativeai import GenerativeModel
import asyncio
import logging

logger = logging.getLogger(__name__)

class GeminiAnalysisService:
    def __init__(self):
        """Initialize Gemini service with API key from environment"""
        try:
            api_key = os.getenv("GOOGLE_API_KEY")  # Changed from GEMINI_API_KEY to match docs
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment variables")
            
            genai.configure(api_key=api_key)
            # Using the recommended model from docs
            self.model = genai.GenerativeModel('gemini-pro')
            
            # Test the model with a simple prompt
            response = self.model.generate_content("Test connection")
            if response and hasattr(response, 'text'):
                print(f"✓ Gemini service initialized with API key: {api_key[:5]}...")
            else:
                raise Exception("Failed to generate test content")
                
        except Exception as e:
            print(f"❌ Error initializing Gemini service: {e}")
            raise

    async def analyze_game(self, game_data):
        """Analyze a game using Gemini AI"""
        try:
            # Format injuries for better prompt readability
            home_injuries = [f"{i['player']} ({i['status']})" for i in game_data['home_injuries'] 
                           if i['player'] not in ['No injuries', 'Team not found']]
            away_injuries = [f"{i['player']} ({i['status']})" for i in game_data['away_injuries']
                           if i['player'] not in ['No injuries', 'Team not found']]

            # Structure the prompt using Content and Part objects as recommended
            contents = [
                {
                    "role": "user",
                    "parts": [{
                        "text": f"""
                        As an NBA analyst, analyze this matchup:
                        {game_data['away_team']} at {game_data['home_team']}

                        Key Information:
                        - Home Team: {game_data['home_team']}
                          Injuries: {', '.join(home_injuries) if home_injuries else 'None reported'}
                          Odds: {game_data['odds']['home']}

                        - Away Team: {game_data['away_team']}
                          Injuries: {', '.join(away_injuries) if away_injuries else 'None reported'}
                          Odds: {game_data['odds']['away']}

                        Provide a concise analysis focusing on:
                        1. Impact of key injuries
                        2. Home court advantage
                        3. Betting value
                        4. Quick prediction
                        
                        Keep response to 2-3 sentences maximum.
                        """
                    }]
                }
            ]

            logger.info(f"Analyzing game: {game_data['away_team']} @ {game_data['home_team']}")
            
            # Make synchronous call in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    contents,
                    generation_config={
                        'temperature': 0.7,
                        'top_p': 0.8,
                        'top_k': 40,
                        'max_output_tokens': 200,
                    },
                    safety_settings=[
                        {
                            "category": "HARM_CATEGORY_HARASSMENT",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                        },
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                        }
                    ]
                )
            )

            logger.info(f"Generated analysis for {game_data['away_team']} @ {game_data['home_team']}")
            return response.text

        except Exception as e:
            logger.error(f"Error analyzing game: {e}")
            logger.debug(f"Game data: {game_data}")
            return "AI Preview temporarily unavailable"

    async def _fetch_espn_injuries(self, team_name: str) -> list:
        """Scrape CBS Sports for current NBA injuries"""
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://www.cbssports.com/nba/injuries/"
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        injuries = []
                        
                        # Find the team section
                        for section in soup.find_all('table'):
                            team_header = section.find_previous('h4')
                            if team_header and team_name.lower() in team_header.text.strip().lower():
                                # Process each injury row
                                for row in section.find_all('tr'):
                                    cols = row.find_all('td')
                                    if len(cols) >= 4:  # CBS has 4 columns: Player, Position, Updated, Injury Status
                                        player = cols[0].text.strip()
                                        injury = cols[2].text.strip()
                                        status = cols[3].text.strip()
                                        
                                        if player and status:
                                            injuries.append({
                                                "player": player,
                                                "injury_type": injury,
                                                "status": status,
                                                "impact": self._determine_impact(status, player, injury)
                                            })
                                break  # Found our team, stop looking
                                
                        if not injuries:
                            return [{"player": "No reported injuries"}]
                            
                        return sorted(injuries, key=lambda x: (
                            0 if "out" in x['status'].lower() else 
                            1 if "doubtful" in x['status'].lower() else
                            2 if "questionable" in x['status'].lower() else 3,
                            x['player']
                        ))
            return []
        except Exception as e:
            print(f"Error scraping CBS Sports injuries: {e}")
            return []

    async def get_injuries(self, team_name: str) -> list:
        """Get injuries with caching"""
        try:
            cache_key = f"injuries_{team_name}_{datetime.now().strftime('%Y%m%d')}"
            
            # Check cache
            if cache_key in self._injury_cache:
                cache_time, cache_data = self._injury_cache[cache_key]
                if datetime.now() - cache_time < self._injury_cache_duration:
                    return cache_data

            # Get fresh data from CBS Sports
            async with aiohttp.ClientSession() as session:
                url = "https://www.cbssports.com/nba/injuries/"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                print(f"Fetching injuries for {team_name} from CBS Sports...")
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'lxml')  # Use lxml parser for better performance
                        injuries = []
                        
                        # Find all team sections
                        team_sections = soup.find_all('div', class_='TeamLogoNameLockup')
                        for section in team_sections:
                            team_name_element = section.find('span', class_='TeamName')
                            if team_name_element and team_name.lower() in team_name_element.text.strip().lower():
                                # Found our team, get the associated table
                                injury_table = section.find_next('table', class_='TableBase')
                                if injury_table:
                                    # Process each injury row
                                    for row in injury_table.find_all('tr')[1:]:  # Skip header row
                                        cols = row.find_all('td')
                                        if len(cols) >= 4:
                                            player = cols[0].text.strip()
                                            injury = cols[2].text.strip()
                                            status = cols[3].text.strip()
                                            
                                            if player and status:
                                                injuries.append({
                                                    "player": player,
                                                    "injury_type": injury,
                                                    "status": status,
                                                    "impact": self._determine_impact(status, player, injury)
                                                })
                                    break  # Found our team, stop looking
                        
                        if not injuries:
                            print(f"No injuries found for {team_name}")
                            injuries = [{"player": "No reported injuries"}]
                        else:
                            print(f"Found {len(injuries)} injuries for {team_name}")
                        
                        # Sort injuries by severity
                        injuries = sorted(injuries, key=lambda x: (
                            0 if "out" in x.get('status', '').lower() else 
                            1 if "doubtful" in x.get('status', '').lower() else
                            2 if "questionable" in x.get('status', '').lower() else 3,
                            x.get('player', '')
                        ))
                        
                        # Cache the result
                        self._injury_cache[cache_key] = (datetime.now(), injuries)
                        return injuries
                    else:
                        print(f"Error: Got status code {response.status} from CBS Sports")
                        
            return [{"player": "No reported injuries"}]
            
        except Exception as e:
            print(f"Error getting injuries from CBS Sports: {e}")
            print(f"Full error: {repr(e)}")
            return [{"player": "Error fetching injuries"}]

    def _determine_impact(self, status: str, player: str, injury_type: str) -> str:
        """
        Determine impact level based on:
        1. Status (Out/Doubtful/Questionable/Probable)
        2. Injury type and severity
        3. Player importance
        """
        # Categorize injuries by severity
        severe_injuries = [
            "ACL", "MCL", "Achilles", "Fracture", "Surgery",
            "Concussion", "Torn", "Rupture"
        ]
        
        moderate_injuries = [
            "Knee", "Back", "Ankle", "Hamstring", "Groin",
            "Shoulder", "Hip", "Foot", "Wrist"
        ]
        
        minor_injuries = [
            "Illness", "Rest", "Personal", "Conditioning",
            "Soreness", "Contusion", "Sprain"
        ]

        # Key players to consider
        star_players = [
            "Jayson Tatum", "Jaylen Brown", "Jrue Holiday",  # Celtics
            "Julius Randle", "Jalen Brunson", "RJ Barrett",  # Knicks
            "Joel Embiid", "Tyrese Maxey", "Tobias Harris",  # 76ers
            "Donovan Mitchell", "Darius Garland",            # Cavs
            "Jimmy Butler", "Bam Adebayo", "Tyler Herro"     # Heat
        ]

        status = status.lower()
        injury_type = injury_type.lower()
        impact = "Low"

        # Check injury severity first
        if any(injury.lower() in injury_type for injury in severe_injuries):
            impact = "High"
        elif any(injury.lower() in injury_type for injury in moderate_injuries):
            impact = "Medium"
        elif any(injury.lower() in injury_type for injury in minor_injuries):
            impact = "Low"

        # Adjust based on status
        if "out" in status:
            impact = "High"
        elif "doubtful" in status and impact != "High":
            impact = "Medium"
        
        # Increase impact for star players
        if any(star in player for star in star_players) and impact != "High":
            impact = "High" if impact == "Medium" else "Medium"

        return impact

    def _normalize_team_name(self, team_name: str) -> str:
        """Normalize team name to match ESPN format"""
        replacements = {
            "76ers": "Philadelphia 76ers",
            "Blazers": "Portland Trail Blazers",
            "Cavs": "Cleveland Cavaliers",
            "Mavs": "Dallas Mavericks",
            "Sixers": "Philadelphia 76ers"
        }
        
        for key, value in replacements.items():
            if key in team_name:
                return value
                
        return team_name