from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class SocialBuzz:
    source: str
    role: str
    content: str
    sentiment: str

@dataclass
class HistoricalGame:
    date: str
    winner: str
    score: str
    key_notes: str

@dataclass
class HistoricalRecord:
    team1_wins: int
    team2_wins: int
    ties: int
    trends: List[str]

@dataclass
class Bet:
    raw_text: str
    bet_type: str = "unknown"
    team_home: str = None
    team_away: str = None
    game_date: str = None
    odds: Dict[str, Any] = None
    weather: Dict[str, Any] = None
    analysis: Dict[str, Any] = None
    is_rivalry: bool = False
    influencer_opinions: List[str] = None
    
    # Player prop specific fields
    player: str = ""
    prop_type: str = ""
    prop_value: float = 0.0
    over_under: str = ""
    
    def __post_init__(self):
        if self.odds is None:
            self.odds = {}
        if self.weather is None:
            self.weather = {}
        if self.analysis is None:
            self.analysis = {}
        if self.influencer_opinions is None:
            self.influencer_opinions = [] 