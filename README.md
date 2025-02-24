# BetBuddy - Sports Betting Analysis Tool

BetBuddy is a web application that provides real-time sports betting odds, weather data, injury reports, and AI-generated game previews for NBA, MLB, and NFL games.

## Features

- Real-time betting odds from multiple sportsbooks
- Best moneyline, spread, and over/under odds
- Weather data for outdoor stadiums
- Team injury reports
- AI-generated game previews
- Responsive web interface

## Prerequisites

- Python 3.8+
- API Keys:
  - OpenWeather API
  - Sportradar API
  - The Odds API
  - Google Gemini API

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/betbuddy.git
cd betbuddy
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API keys:

```
GEMINI_API_KEY=your_gemini_key
SPORTRADAR_API_KEY=your_sportradar_key
ODDS_API_KEY=your_odds_api_key
WEATHER_API_KEY=your_openweather_key
```

## Usage

1. Start the server:

```bash
python src/main.py
```

2. Open your browser and navigate to:

```
http://localhost:5001
```

## API Endpoints

- `/available_games` - Get current games with odds
- `/test_weather/<team>` - Test weather data for a team
- `/test_injuries/<team>` - Test injury reports for a team
- `/available_sports` - List supported sports

## Project Structure

```
betbuddy/
├── src/
│   ├── services/
│   │   ├── odds_service.py
│   │   ├── weather_service.py
│   │   ├── sportradar_service.py
│   │   └── preview_service.py
│   ├── templates/
│   │   └── index.html
│   ├── bet_parser/
│   │   └── parser.py
│   ├── models/
│   │   └── bet.py
│   └── main.py
├── tests/
│   └── test_bet_parser.py
├── requirements.txt
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The Odds API for betting odds
- OpenWeather API for weather data
- Sportradar API for sports data
- Google Gemini for AI-powered previews
