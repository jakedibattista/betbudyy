from flask import Flask, render_template, request, jsonify
from bet_parser.parser import BetParser
import asyncio
from services.odds_service import OddsService
from datetime import datetime
from services.weather_service import WeatherService
from services.sportradar_service import SportradarService
from time import sleep
from services.preview_service import PreviewService

app = Flask(__name__)
parser = BetParser()
odds_service = OddsService()
weather_service = WeatherService()
sportradar_service = SportradarService()
preview_service = PreviewService()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
async def analyze_bet():
    bet_text = request.json.get('bet')
    if not bet_text:
        return jsonify({'error': 'No bet text provided'}), 400
    
    try:
        bet = await parser.parse(bet_text)
        
        result = {
            'bet_type': bet.bet_type,
            'analysis': {
                'team_home': bet.team_home,
                'team_away': bet.team_away,
                'game_date': bet.game_date,
                'odds': bet.odds,
                'weather': bet.weather
            }
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test_odds')
async def test_odds():
    try:
        print("Testing odds API...")
        odds = await odds_service.get_odds()
        if odds and len(odds) > 0:
            sample_game = odds[0]
            return jsonify({
                "status": "success",
                "games": len(odds),
                "sample_game": {
                    "home_team": sample_game['home_team'],
                    "away_team": sample_game['away_team'],
                    "commence_time": sample_game['commence_time'],
                    "bookmakers": [b['key'] for b in sample_game.get('bookmakers', [])]
                }
            })
        return jsonify({
            "status": "error",
            "message": "No games found",
            "details": "Try a different sport or check back later"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "details": repr(e)
        })

@app.route('/available_sports')
def available_sports():
    return jsonify(list(OddsService.SUPPORTED_SPORTS.items()))

@app.route('/available_games')
async def available_games():
    try:
        sport = request.args.get('sport')
        odds = await odds_service.get_odds(sport)
        if odds and len(odds) > 0:
            games = []
            for game in odds:
                game_id = game['id']
                current_time = datetime.now().isoformat()
                
                # Process moneyline odds
                home_odds = []
                away_odds = []
                # Process spread odds
                spreads = []
                # Process totals
                totals = []
                
                for book in game.get('bookmakers', []):
                    for market in book.get('markets', []):
                        if market['key'] == 'h2h':
                            # Process moneyline odds as before
                            for outcome in market['outcomes']:
                                if outcome['name'] == game['home_team']:
                                    home_odds.append({
                                        'book': book['key'],
                                        'odds': outcome['price'],
                                        'timestamp': current_time
                                    })
                                else:
                                    away_odds.append({
                                        'book': book['key'],
                                        'odds': outcome['price'],
                                        'timestamp': current_time
                                    })
                        elif market['key'] == 'spreads':
                            # Process point spreads
                            spreads.append({
                                'book': book['key'],
                                'home': next((o for o in market['outcomes'] 
                                            if o['name'] == game['home_team']), None),
                                'away': next((o for o in market['outcomes'] 
                                            if o['name'] == game['away_team']), None),
                                'timestamp': current_time
                            })
                        elif market['key'] == 'totals':
                            # Process over/under totals
                            totals.append({
                                'book': book['key'],
                                'total': market['outcomes'][0]['point'],
                                'over_odds': next((o['price'] for o in market['outcomes'] 
                                                 if o['name'] == 'Over'), None),
                                'under_odds': next((o['price'] for o in market['outcomes'] 
                                                  if o['name'] == 'Under'), None),
                                'timestamp': current_time
                            })
                
                # Get best spread for each team (lowest spread with best odds)
                best_spreads = {
                    'home': None,
                    'away': None
                }
                for spread in spreads:
                    if spread['home'] and spread['away']:
                        if (not best_spreads['home'] or 
                            (spread['home']['point'] > best_spreads['home']['point'] or 
                             (spread['home']['point'] == best_spreads['home']['point'] and 
                              spread['home']['price'] > best_spreads['home']['price']))):
                            best_spreads['home'] = {
                                'point': spread['home']['point'],
                                'price': spread['home']['price'],
                                'book': spread['book']
                            }
                        if (not best_spreads['away'] or 
                            (spread['away']['point'] > best_spreads['away']['point'] or 
                             (spread['away']['point'] == best_spreads['away']['point'] and 
                              spread['away']['price'] > best_spreads['away']['price']))):
                            best_spreads['away'] = {
                                'point': spread['away']['point'],
                                'price': spread['away']['price'],
                                'book': spread['book']
                            }

                # Get best total (highest over odds and lowest under odds)
                best_total = {
                    'over': None,
                    'under': None
                }
                for total in totals:
                    if (not best_total['over'] or total['over_odds'] > best_total['over']['odds']):
                        best_total['over'] = {
                            'total': total['total'],
                            'odds': total['over_odds'],
                            'book': total['book']
                        }
                    if (not best_total['under'] or total['under_odds'] > best_total['under']['odds']):
                        best_total['under'] = {
                            'total': total['total'],
                            'odds': total['under_odds'],
                            'book': total['book']
                        }

                # Get weather for outdoor sports
                weather = None
                if sport in ['americanfootball_nfl', 'baseball_mlb']:
                    weather = await weather_service.get_stadium_weather(
                        game['home_team'], 
                        game['commence_time']
                    )
                
                # Get injury reports with delay between requests
                try:
                    home_injuries = await sportradar_service.get_injuries(game['home_team'])
                    await asyncio.sleep(1)  # Wait 1 second between requests
                    away_injuries = await sportradar_service.get_injuries(game['away_team'])
                    await asyncio.sleep(1)  # Wait 1 second between requests
                except Exception as e:
                    print(f"Error fetching injuries: {e}")
                    home_injuries = None
                    away_injuries = None
                
                # Get game preview
                preview = await preview_service.get_game_preview({
                    "home_team": game['home_team'],
                    "away_team": game['away_team'],
                    "injuries": {
                        "home": home_injuries,
                        "away": away_injuries
                    }
                })
                
                games.append({
                    "id": game_id,
                    "home_team": game['home_team'],
                    "away_team": game['away_team'],
                    "start_time": game['commence_time'],
                    "sport": game['sport_title'],
                    "weather": weather,
                    "injuries": {
                        "home": home_injuries,
                        "away": away_injuries
                    },
                    "preview": preview,
                    "odds": {
                        "moneyline": {
                            "home": sorted(home_odds, key=lambda x: x['odds'], reverse=True)[:3],
                            "away": sorted(away_odds, key=lambda x: x['odds'], reverse=True)[:3]
                        },
                        "spreads": best_spreads,
                        "totals": best_total
                    }
                })
            
            # Sort games if requested
            sort_by = request.args.get('sort')
            if sort_by == 'time':
                games.sort(key=lambda x: x['start_time'])
            elif sort_by == 'odds':
                # Sort by the best available odds for either team
                games.sort(key=lambda x: x['odds'], reverse=True)
            
            # Filter by team if requested
            team_filter = request.args.get('team', '').lower()
            if team_filter:
                games = [g for g in games if team_filter in g['home_team'].lower() or 
                        team_filter in g['away_team'].lower()]
            
            return jsonify({
                "status": "success",
                "sport": game['sport_title'],
                "game_count": len(games),
                "games": games
            })
            
        return jsonify({
            "status": "error",
            "message": "No games found"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route('/test_injuries/<team>')
async def test_injuries(team):
    try:
        print(f"Testing injury report for: {team}")
        injuries = await sportradar_service.get_injuries(team)
        return jsonify({
            "status": "success" if injuries else "error",
            "team": team,
            "injuries": injuries or [],
            "injury_count": len(injuries) if injuries else 0
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "details": repr(e)
        })

@app.route('/test_weather/<team>')
async def test_weather(team):
    try:
        print(f"Testing weather for: {team}")
        # Use current time for testing
        current_time = datetime.now().isoformat()
        weather = await weather_service.get_stadium_weather(team, current_time)
        
        return jsonify({
            "status": "success" if weather else "error",
            "team": team,
            "weather": weather,
            "details": {
                "stadium": weather.get("stadium") if weather else None,
                "is_indoor": weather.get("is_indoor") if weather else None,
                "raw_response": weather
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "details": repr(e)
        })

def run_app():
    # Try ports 5001-5010 until we find an open one
    for port in range(5001, 5011):
        try:
            print(f"Attempting to start server on port {port}...")
            app.run(debug=True, port=port)
            break
        except OSError as e:
            print(f"Port {port} is in use, trying next port...")
            continue

if __name__ == '__main__':
    run_app() 