import google.generativeai as genai
import os
from typing import Optional, Dict, Any

class PreviewService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("WARNING: GEMINI_API_KEY not found in environment variables")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    async def get_game_preview(self, game: Dict[str, Any]) -> Optional[str]:
        """Generate a 2-4 sentence preview for a game"""
        try:
            prompt = f"""
            Generate a concise 2-4 sentence preview for this game:
            {game['away_team']} @ {game['home_team']}
            
            Include:
            - Key matchup or storyline
            - Any notable injuries if available
            - Current form/trends if relevant
            
            Keep it factual and analytical, avoid speculation.
            """

            response = await self.model.generate_content_async(prompt)
            return response.text

        except Exception as e:
            print(f"Error generating preview: {e}")
            return None 