import pytest
from src.bet_parser.parser import BetParser
from src.models.bet import Bet

@pytest.mark.asyncio
async def test_game_winner_bet():
    parser = BetParser()
    bet = await parser.parse("Texans beat the bills")
    
    assert bet.bet_type == "game_winner"
    assert bet.team_away == "Texans"
    assert bet.team_home == "Bills"

@pytest.mark.asyncio
async def test_player_prop_bet():
    parser = BetParser()
    bet = await parser.parse("Josh allen over 200 passing yards")
    
    assert bet.bet_type == "player_prop"
    assert bet.player == "Josh Allen"
    assert bet.prop_type == "passing_yards"
    assert bet.prop_value == 200 