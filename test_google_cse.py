#!/usr/bin/env python3
"""Test script for Google CSE client."""
import os
import sys
import tomllib

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Load secrets.toml
secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
if os.path.exists(secrets_path):
    with open(secrets_path, "rb") as f:
        secrets = tomllib.load(f)
        # Set environment variables from secrets.toml
        if "GOOGLE_CSE_API_KEY" in secrets:
            os.environ["GOOGLE_CSE_API_KEY"] = secrets["GOOGLE_CSE_API_KEY"]
        if "GOOGLE_CSE_CX_WEATHER" in secrets:
            os.environ["GOOGLE_CSE_CX_WEATHER"] = secrets["GOOGLE_CSE_CX_WEATHER"]
        if "GOOGLE_CSE_CX_SAFETY" in secrets:
            os.environ["GOOGLE_CSE_CX_SAFETY"] = secrets["GOOGLE_CSE_CX_SAFETY"]

from tools.google_cse import GoogleCSE

def test_weather_search():
    """Test weather search functionality."""
    print("=== Google CSE Weather Search Test ===\n")
    
    try:
        # Initialize client
        cse = GoogleCSE()
        print("✓ Google CSE client initialized")
        print(f"  - API Key: {cse.api_key[:10]}...")
        print(f"  - Weather CX: {cse.cx_weather}")
        print()
        
        # Perform search
        query = "Tokyo March weather"
        print(f"Searching: '{query}'")
        results = cse.search_weather(query, num_results=3)
        
        print(f"\n✓ Found {len(results)} results\n")
        
        # Display results
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.title}")
            print(f"   URL: {result.url}")
            print(f"   Snippet: {result.snippet[:150]}...")
            print()
        
        if len(results) == 0:
            print("⚠️  No results found. Check:")
            print("   - API key is valid")
            print("   - PSE ID is correct")
            print("   - PSE is configured with correct sites")
            return False
        
        return True
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nPlease check your .streamlit/secrets.toml:")
        print("  - GOOGLE_CSE_API_KEY")
        print("  - GOOGLE_CSE_CX_WEATHER")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_weather_search()
    sys.exit(0 if success else 1)
