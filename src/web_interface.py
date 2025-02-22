from flask import Flask, render_template, request, jsonify
from bet_parser.parser import BetParser
import asyncio
from services.odds_service import OddsService
from datetime import datetime

app = Flask(__name__)
parser = BetParser()
odds_service = OddsService()

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
                # Track odds history (you'll need to store this in a database for production)
                game_id = game['id']
                current_time = datetime.now().isoformat()
                
                home_odds = []
                away_odds = []
                for book in game.get('bookmakers', []):
                    for market in book.get('markets', []):
                        if market['key'] == 'h2h':
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
                
                # Get longest odds for either team
                longest_home_odds = max(home_odds, key=lambda x: x['odds'])['odds'] if home_odds else 0
                longest_away_odds = max(away_odds, key=lambda x: x['odds'])['odds'] if away_odds else 0
                longest_odds = max(longest_home_odds, longest_away_odds)
                
                games.append({
                    "id": game_id,
                    "home_team": game['home_team'],
                    "away_team": game['away_team'],
                    "start_time": game['commence_time'],
                    "sport": game['sport_title'],
                    "longest_odds": longest_odds,  # Renamed from best_odds
                    "odds": {
                        "home": sorted(home_odds, key=lambda x: x['odds'], reverse=True)[:3],
                        "away": sorted(away_odds, key=lambda x: x['odds'], reverse=True)[:3]
                    }
                })
            
            # Sort games if requested
            sort_by = request.args.get('sort')
            if sort_by == 'time':
                games.sort(key=lambda x: x['start_time'])
            elif sort_by == 'odds':
                # Sort by the best available odds for either team
                games.sort(key=lambda x: x['longest_odds'], reverse=True)
            
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

def run_app():
    app.run(debug=True, port=5001)

if __name__ == '__main__':
    run_app() 