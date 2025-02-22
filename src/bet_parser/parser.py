from typing import Dict, Any
from models.bet import Bet
from services.odds_service import OddsService
from services.weather_service import WeatherService
from services.sportradar_service import SportradarService

class BetParser:
    def __init__(self):
        self.odds_service = OddsService()
        self.weather_service = WeatherService()
        self.sportradar_service = SportradarService()
        
    async def parse(self, text: str) -> Bet:
        """Parse bet and get odds + weather"""
        # Create basic bet object
        bet = Bet(raw_text=text)
        
        # Get teams from text
        teams = self._extract_teams_from_text(text)
        print(f"Extracted teams: {teams}")
        
        if len(teams) >= 2:
            odds_info = await self.odds_service.find_game_odds(teams[0], teams[1])
            if odds_info and odds_info.get("available"):
                bet.bet_type = "game_winner"
                bet.odds = odds_info.get("odds", {})
                bet.game_date = odds_info.get("game_date")
                bet.team_home = odds_info.get("home_team")
                bet.team_away = odds_info.get("away_team")
                
                # Get weather for home team's city
                if bet.team_home:
                    city = bet.team_home.split()[-1]
                    weather = await self.weather_service.get_forecast(city, bet.game_date)
                    if weather:
                        bet.weather = weather
                
                # Get team comparison stats
                print("Fetching team statistics...")
                stats = await self.sportradar_service.get_team_comparison(
                    home_team=bet.team_home,
                    away_team=bet.team_away
                )
                if stats:
                    bet.analysis = {"team_stats": stats}
                else:
                    print("No team statistics available")
                
        return bet

    def _extract_teams_from_text(self, text: str) -> list:
        """Extract team names from bet text"""
        text = text.lower().strip()
        teams = []
        
        # Handle 'X beat Y' format
        if ' beat ' in text:
            parts = text.split(' beat ')
            if len(parts) == 2:
                teams = [parts[0].strip(), parts[1].strip()]
        
        # Handle 'X vs Y' format    
        elif ' vs ' in text:
            parts = text.split(' vs ')
            if len(parts) == 2:
                teams = [parts[0].strip(), parts[1].strip()]
        
        # Normalize team names
        return [self._normalize_team_name(team) for team in teams]

    def _normalize_team_name(self, team_name: str) -> str:
        """Normalize team name to standard format"""
        if not team_name:
            return ""
        
        # Remove common prefixes/suffixes and clean
        name = team_name.lower().strip()
        name = name.replace("the ", "").replace(" team", "")
        
        # Handle common variations and typos
        team_mappings = {
            "kc": "kansas city chiefs",
            "chiefs": "kansas city chiefs",
            "cheifs": "kansas city chiefs",  # Common typo
            "kansas": "kansas city chiefs",
            "kansas city": "kansas city chiefs",
            "philly": "philadelphia eagles",
            "eagles": "philadelphia eagles",
            "philadelphia": "philadelphia eagles",
        }
        
        # Try to find a mapping
        for key, value in team_mappings.items():
            if key in name:
                return value
            
        return name 