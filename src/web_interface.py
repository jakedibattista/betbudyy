from flask import Flask, render_template, request, jsonify
from bet_parser.parser import BetParser
import asyncio
from services.odds_service import OddsService
from datetime import datetime, timedelta
from services.weather_service import WeatherService
from services.sportradar_service import SportradarService
from time import sleep
from services.preview_service import PreviewService
from services.gemini_analysis_service import GeminiAnalysisService
from services.injury_service import InjuryService
import json
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

app = Flask(__name__, 
    template_folder='../templates'  # If templates are in project root
)
app.config['DEBUG'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
parser = BetParser()

# Initialize services
load_dotenv()
odds_service = OddsService()
injury_service = InjuryService()
gemini_service = GeminiAnalysisService()
scheduler = BackgroundScheduler()

def init_services():
    """Initialize all services"""
    global odds_service, injury_service, gemini_service
    
    print("\n=== Initializing Services ===")
    try:
        odds_service = OddsService()
        print("✓ Odds service initialized")
        
        injury_service = InjuryService()
        
        # Do initial injury database update
        asyncio.run(injury_service.update_injuries())
        print("✓ Injury database updated")
        print("✓ Injury service initialized")
        
        # Schedule future updates
        scheduler.add_job(
            func=lambda: asyncio.run(injury_service.update_injuries()),
            trigger='interval',
            hours=6,
            next_run_time=datetime.now() + timedelta(hours=6)
        )
        scheduler.start()
        print("✓ Injury update scheduler started")
            
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        raise

def run_app():
    """Run the Flask application"""
    try:
        # Initialize services before running the app
        init_services()
        
        # Try ports 5500-5510 instead
        for port in range(5500, 5511):
            try:
                print(f"\nAttempting to start server on port {port}...")
                app.run(debug=True, port=port, host='0.0.0.0')
                break
            except OSError:
                print(f"Port {port} is in use, trying next port...")
                continue
                
    except Exception as e:
        print(f"❌ Fatal error starting server: {e}")
        scheduler.shutdown()
        raise

# Shutdown scheduler when app exits
import atexit
atexit.register(lambda: scheduler.shutdown())

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
        odds = await odds_service.get_odds('basketball_nba')
        
        if not odds:
            return jsonify({"status": "error", "message": "No games found"})

        games = []
        for game in odds:
            home_team = game['home_team']
            away_team = game['away_team']
            
            # Get injuries
            home_injuries = await injury_service.get_injuries(home_team)
            away_injuries = await injury_service.get_injuries(away_team)

            # Get AI Preview
            preview = await gemini_service.analyze_game({
                'home_team': home_team,
                'away_team': away_team,
                'home_injuries': home_injuries,
                'away_injuries': away_injuries,
                'odds': {
                    'home': game.get('bookmakers', [{}])[0].get('markets', [{}])[0].get('outcomes', [{}])[0].get('price'),
                    'away': game.get('bookmakers', [{}])[0].get('markets', [{}])[0].get('outcomes', [{}])[1].get('price')
                }
            })

            game_data = {
                'home_team': home_team,
                'away_team': away_team,
                'start_time': game['commence_time'],
                'injuries': {
                    'home_team': home_injuries,
                    'away_team': away_injuries
                },
                'odds': {
                    'moneyline': {'home': [], 'away': []}
                },
                'preview': preview
            }

            # Add moneyline odds
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home_team:
                                game_data['odds']['moneyline']['home'].append({
                                    'book': bookmaker['key'],
                                    'odds': outcome['price']
                                })
                            else:
                                game_data['odds']['moneyline']['away'].append({
                                    'book': bookmaker['key'],
                                    'odds': outcome['price']
                                })

            games.append(game_data)

        return jsonify({
            "status": "success",
            "game_count": len(games),
            "games": games
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)})

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

if __name__ == '__main__':
    run_app() 