import fastf1
import os
from google import genai
from google.genai import types

# Set up fastf1 cache
# We use an absolute path or a path relative to the workspace root
cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'f1_cache'))
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
fastf1.Cache.enable_cache(cache_dir)

def get_session_results(year: int, grand_prix: str, session_type: str = 'R') -> str:
    """Gets the results for a given year, Grand Prix name, and session type (e.g. 'R' for Race, 'Q' for Qualifying, 'FP1' for practice)."""
    try:
        session = fastf1.get_session(year, grand_prix, session_type)
        session.load(telemetry=False, weather=False)
        results = session.results[['Position', 'Abbreviation', 'TeamName', 'Time', 'Status']]
        return results.to_string()
    except Exception as e:
        return f"Error retrieving data: {e}"

def get_fastest_lap(year: int, grand_prix: str, session_type: str = 'R') -> str:
    """Gets the fastest lap of a given session (e.g. 'R' for Race, 'Q' for Qualifying). Useful for questions about fastest laps."""
    try:
        session = fastf1.get_session(year, grand_prix, session_type)
        session.load(telemetry=False, weather=False)
        fastest_lap = session.laps.pick_fastest()
        return f"Fastest lap was by {fastest_lap['Driver']} with a time of {fastest_lap['LapTime']}."
    except Exception as e:
        return f"Error retrieving data: {e}"

def ask_f1_agent(query: str) -> str:
    """Main function to ask the Gemini agent a question."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY environment variable is not set. Please add it to your .env file."
    
    client = genai.Client(api_key=api_key)
    
    # Define the tools for Gemini to use
    tools = [get_session_results, get_fastest_lap]
    
    try:
        chat = client.chats.create(
            model='gemini-2.5-flash',
            config=types.GenerateContentConfig(
                tools=tools,
                temperature=0.2,
                system_instruction="You are a helpful Formula 1 assistant. Use the provided tools to fetch F1 data when needed. Format your responses nicely for a web dashboard.",
            )
        )
        response = chat.send_message(query)
        return response.text
    except Exception as e:
        return f"Error communicating with AI: {e}"
