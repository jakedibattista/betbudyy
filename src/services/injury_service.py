import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
from .injury_database import InjuryDatabase

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InjuryService:
    def __init__(self):
        self.db = InjuryDatabase()
        self._cache = {}
        self._cache_duration = timedelta(minutes=15)
        logger.info("InjuryService initialized")

    async def update_injuries(self):
        """Update injury database"""
        await self.db.update_injuries()
        
    async def get_injuries(self, team_name: str) -> list:
        """Get injuries with caching"""
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"Getting injuries for: {team_name}")
            
            cache_key = f"injuries_{team_name}_{datetime.now().strftime('%Y%m%d')}"
            
            # Check cache
            if cache_key in self._cache:
                cache_time, cache_data = self._cache[cache_key]
                if datetime.now() - cache_time < self._cache_duration:
                    return cache_data

            # Get from database
            injuries = await self.db.get_team_injuries(team_name)
            
            if not injuries:
                logger.warning(f"No injuries found for {team_name}")
                # Debug: Print the HTML structure
                logger.info("HTML structure:")
                logger.info(soup.prettify()[:1000])  # Print first 1000 chars
                injuries = [{"player": "No reported injuries"}]
            else:
                logger.info(f"Found {len(injuries)} injuries for {team_name}")
                for injury in injuries:
                    logger.info(f"- {injury['player']}: {injury['status']}")
            
            # Cache the result
            self._cache[cache_key] = (datetime.now(), injuries)
            return injuries
            
        except Exception as e:
            logger.error(f"Error getting injuries: {e}")
            return [{"player": "Error fetching injuries"}]

    def _determine_impact(self, status: str, player: str, injury_type: str) -> str:
        """Determine impact level of an injury"""
        # ... existing impact determination code ... 