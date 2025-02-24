from google import genai
import os
from dotenv import load_dotenv

def test_gemini():
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        print(f"Using API key: {api_key[:10]}...")
        
        client = genai.Client(api_key=api_key)
        
        # Test generation
        print("\nTesting Gemini API...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-001",  # Updated model name
            contents="Explain how AI works in one sentence"
        )
        
        print("\nResponse from Gemini:")
        print(response.text)
        
        return True
        
    except Exception as e:
        print(f"\nError testing Gemini: {str(e)}")
        return False

if __name__ == "__main__":
    test_gemini() 