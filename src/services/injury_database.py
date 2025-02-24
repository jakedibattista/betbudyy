from datetime import datetime, timedelta
import sqlite3
import aiohttp
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class InjuryDatabase:
    def __init__(self, db_path="injuries.db"):
        self.db_path = db_path
        self.init_db()
        
    def init_db(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            # Create teams table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    city TEXT,
                    abbreviation TEXT
                )
            """)
            
            # Create players table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER,
                    name TEXT NOT NULL,
                    position TEXT,
                    number TEXT,
                    FOREIGN KEY(team_id) REFERENCES teams(id),
                    UNIQUE(team_id, name)
                )
            """)

            # Create injuries table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS injuries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    status TEXT,
                    last_updated TIMESTAMP,
                    source TEXT,
                    FOREIGN KEY(player_id) REFERENCES players(id)
                )
            """)

            # Insert some initial team data
            teams = [
                ("Boston Celtics", "Boston", "BOS"),
                ("New York Knicks", "New York", "NYK"),
                ("Brooklyn Nets", "Brooklyn", "BKN"),
                ("Philadelphia 76ers", "Philadelphia", "PHI"),
                ("Toronto Raptors", "Toronto", "TOR"),
                # Add all NBA teams...
            ]
            
            conn.executemany("""
                INSERT OR IGNORE INTO teams (name, city, abbreviation)
                VALUES (?, ?, ?)
            """, teams)
            
            conn.commit()

    def clean_player_name(self, name):
        """Clean player name to avoid duplicates"""
        try:
            # Extract any suffixes first
            suffixes = []
            base_name = name
            
            # Check for and remove suffixes, keeping track of them
            if " Jr." in name:
                suffixes.append("Jr.")
                base_name = base_name.replace(" Jr.", "")
            if " III" in name:
                suffixes.append("III")
                base_name = base_name.replace(" III", "")
            elif " II" in name:  # Use elif to avoid matching II in III
                suffixes.append("II")
                base_name = base_name.replace(" II", "")
            
            # Now handle the base name
            if any(c.isupper() for c in base_name[1:]):
                # Split on capital letters
                parts = []
                current = base_name[0]
                
                for c in base_name[1:]:
                    if c.isupper() and len(current) > 1:
                        parts.append(current)
                        current = c
                    else:
                        current += c
                parts.append(current)
                
                # Get the full name part (usually the second occurrence)
                if len(parts) >= 2:
                    # Find where the full name starts
                    for i, part in enumerate(parts):
                        if any(part in p for p in parts[i+1:]):
                            full_name = " ".join(parts[i+1:])
                            # Add back any suffixes
                            if suffixes:
                                full_name = f"{full_name} {' '.join(suffixes)}"
                            return full_name.strip()
                
                # If we didn't find a repeat, just use the last two parts
                full_name = " ".join(parts[-2:])
                if suffixes:
                    full_name = f"{full_name} {' '.join(suffixes)}"
                return full_name.strip()
            
            # If no capital letters found, just return the original name
            if suffixes:
                base_name = f"{base_name} {' '.join(suffixes)}"
            return base_name.strip()
        
        except Exception as e:
            logger.error(f"Error cleaning player name '{name}': {e}")
            return name.strip()

    async def update_injuries(self):
        """Daily update from CBS Sports"""
        try:
            logger.info("Starting injury database update...")
            async with aiohttp.ClientSession() as session:
                url = "https://www.cbssports.com/nba/injuries/"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
                }
                
                logger.info(f"Fetching injuries from {url}")
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        with sqlite3.connect(self.db_path) as conn:
                            cur = conn.cursor()
                            current_team_id = None  # Initialize here
                            
                            # First, make sure we have all NBA teams
                            teams = [
                                ("Boston Celtics", "Boston", "BOS"),
                                ("New York Knicks", "New York", "NYK"), 
                                ("Brooklyn Nets", "Brooklyn", "BKN"),
                                ("Philadelphia 76ers", "Philadelphia", "PHI"),
                                ("Toronto Raptors", "Toronto", "TOR"),
                                ("Milwaukee Bucks", "Milwaukee", "MIL"),
                                ("Cleveland Cavaliers", "Cleveland", "CLE"),
                                ("Chicago Bulls", "Chicago", "CHI"),
                                ("Atlanta Hawks", "Atlanta", "ATL"),
                                ("Miami Heat", "Miami", "MIA"),
                                ("Charlotte Hornets", "Charlotte", "CHA"),
                                ("Washington Wizards", "Washington", "WAS"),
                                ("Detroit Pistons", "Detroit", "DET"),
                                ("Indiana Pacers", "Indiana", "IND"),
                                ("Orlando Magic", "Orlando", "ORL"),
                                ("Denver Nuggets", "Denver", "DEN"),
                                ("Minnesota Timberwolves", "Minnesota", "MIN"),
                                ("Oklahoma City Thunder", "Oklahoma City", "OKC"),
                                ("Utah Jazz", "Utah", "UTA"),
                                ("Portland Trail Blazers", "Portland", "POR"),
                                ("Los Angeles Lakers", "Los Angeles", "LAL"),
                                ("Los Angeles Clippers", "Los Angeles", "LAC"),
                                ("Phoenix Suns", "Phoenix", "PHX"),
                                ("Sacramento Kings", "Sacramento", "SAC"),
                                ("Golden State Warriors", "Golden State", "GSW"),
                                ("Dallas Mavericks", "Dallas", "DAL"),
                                ("Houston Rockets", "Houston", "HOU"),
                                ("Memphis Grizzlies", "Memphis", "MEM"),
                                ("San Antonio Spurs", "San Antonio", "SAS"),
                                ("New Orleans Pelicans", "New Orleans", "NOP"),
                            ]
                            
                            # Insert teams
                            cur.executemany("""
                                INSERT OR IGNORE INTO teams (name, city, abbreviation)
                                VALUES (?, ?, ?)
                            """, teams)
                            conn.commit()
                            
                            # Process injuries
                            for team_section in soup.find_all(['h4', 'tr']):
                                if team_section.name == 'h4':
                                    team_name = team_section.text.strip()
                                    logger.info(f"\nProcessing team: {team_name}")
                                    
                                    # Get team ID
                                    cur.execute("SELECT id FROM teams WHERE name LIKE ?", (f"%{team_name}%",))
                                    team_result = cur.fetchone()
                                    current_team_id = team_result[0] if team_result else None
                                    continue
                                
                                if current_team_id and team_section.name == 'tr':
                                    cols = team_section.find_all('td')
                                    if len(cols) >= 5:
                                        raw_name = cols[0].text.strip()
                                        player_name = self.clean_player_name(raw_name)  # Clean the name
                                        position = cols[1].text.strip()
                                        status = cols[4].text.strip()
                                        
                                        if player_name and not player_name.startswith("Player"):
                                            logger.info(f"Found injury: {player_name} ({position}) - {status}")
                                            
                                            # Delete any existing injuries for this player
                                            cur.execute("""
                                                DELETE FROM injuries 
                                                WHERE player_id IN (
                                                    SELECT id FROM players 
                                                    WHERE team_id = ? AND name LIKE ?
                                                )
                                            """, (current_team_id, f"%{player_name}%"))
                                            
                                            # Add or update player
                                            cur.execute("""
                                                INSERT OR REPLACE INTO players (team_id, name, position)
                                                VALUES (?, ?, ?)
                                            """, (current_team_id, player_name, position))
                                            
                                            # Get player ID
                                            cur.execute("SELECT id FROM players WHERE team_id = ? AND name = ?",
                                                      (current_team_id, player_name))
                                            player_result = cur.fetchone()
                                            if player_result:
                                                player_id = player_result[0]
                                                
                                                # Update injury status
                                                cur.execute("""
                                                    INSERT INTO injuries 
                                                    (player_id, status, last_updated, source)
                                                    VALUES (?, ?, ?, ?)
                                                """, (player_id, status, datetime.now(), 'CBS Sports'))
                            
                            conn.commit()
                            
        except Exception as e:
            logger.error(f"Error updating injury database: {e}")
            raise

    async def get_team_injuries(self, team_name: str) -> list:
        """Get current injuries for a team"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT p.name, p.position, i.status
                    FROM injuries i
                    JOIN players p ON i.player_id = p.id
                    JOIN teams t ON p.team_id = t.id
                    WHERE t.name LIKE ?
                    AND i.last_updated > ?
                    ORDER BY 
                        CASE 
                            WHEN lower(i.status) LIKE '%out%' THEN 1
                            WHEN lower(i.status) LIKE '%doubt%' THEN 2
                            WHEN lower(i.status) LIKE '%quest%' THEN 3
                            ELSE 4
                        END,
                        p.name
                """, (f"%{team_name}%", datetime.now() - timedelta(days=2)))
                
                injuries = cur.fetchall()
                
                if not injuries:
                    # Check if team exists but has no injuries
                    cur.execute("SELECT id FROM teams WHERE name LIKE ?", (f"%{team_name}%",))
                    team_exists = cur.fetchone()
                    
                    if team_exists:
                        return [{"player": "No injuries", "position": "-", "status": "-"}]
                    else:
                        logger.info(f"Team not found: {team_name}")
                        return [{"player": "Team not found", "position": "-", "status": "-"}]
                    
                return [{
                    "player": row[0],
                    "position": row[1],
                    "status": row[2]
                } for row in injuries]
                
        except Exception as e:
            logger.error(f"Error getting team injuries: {e}")
            return [{"player": "No injuries", "position": "-", "status": "-"}] 