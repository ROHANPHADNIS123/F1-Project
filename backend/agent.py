import fastf1
import os
import datetime
import re
import pandas as pd
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend
import matplotlib.pyplot as plt
from fastf1 import plotting

# Set up fastf1 cache
cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'f1_cache'))
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
fastf1.Cache.enable_cache(cache_dir)

def get_session_results(year: int, grand_prix: str, session_type: str = 'R') -> str:
    """Gets the results for a given year, Grand Prix name, and session type (e.g. 'R' for Race, 'Q' for Qualifying, 'FP1' for practice)."""
    try:
        session = fastf1.get_session(year, grand_prix, session_type)
        session.load(telemetry=False, weather=False)
        results = session.results[['Position', 'FullName', 'Abbreviation', 'TeamName', 'Time', 'Status']]
        return results.to_string()
    except Exception as e:
        return f"Error retrieving data: {e}"

def get_fastest_lap(year: int, grand_prix: str, session_type: str = 'R') -> str:
    """Gets the fastest lap of a given session (e.g. 'R' for Race, 'Q' for Qualifying). Useful for questions about fastest laps."""
    try:
        session = fastf1.get_session(year, grand_prix, session_type)
        session.load(telemetry=False, weather=False)
        fastest_lap = session.laps.pick_fastest()
        
        # Look up full name from session.results if available
        driver_abbrev = fastest_lap['Driver']
        driver_row = session.results[session.results['Abbreviation'] == driver_abbrev]
        if not driver_row.empty:
            driver_name = driver_row.iloc[0]['FullName']
        else:
            driver_name = driver_abbrev
            
        return f"Fastest lap was by {driver_name} with a time of {fastest_lap['LapTime']}."
    except Exception as e:
        return f"Error retrieving data: {e}"

def get_race_schedule(year: int) -> str:
    """Gets the race calendar/schedule for a given year. 
    This includes round number, country, location, event name, and date.
    Use this to look up which Grand Prix corresponds to a given date or round,
    or to see the list of races for a year.
    """
    try:
        schedule = fastf1.get_event_schedule(year)
        cols = ['RoundNumber', 'EventName', 'Country', 'Location', 'EventDate']
        df = schedule[cols]
        return df.to_string(index=False)
    except Exception as e:
        return f"Error retrieving schedule: {e}"

def extract_year(query: str) -> int:
    match = re.search(r'\b(19\d\d|20\d\d)\b', query)
    if match:
        return int(match.group(1))
    return datetime.date.today().year

def find_most_recent_grand_prix(year: int) -> str:
    try:
        schedule = fastf1.get_event_schedule(year)
        today = datetime.date.today()
        past_events = schedule[(schedule['RoundNumber'] > 0) & (pd.to_datetime(schedule['EventDate']).dt.date <= today)]
        if not past_events.empty:
            latest_event = past_events.sort_values(by='EventDate', ascending=False).iloc[0]
            return latest_event['EventName']
    except Exception:
        pass
    return None

def find_grand_prix(query: str, year: int) -> str:
    try:
        schedule = fastf1.get_event_schedule(year)
        stop_words = {'grand', 'prix', 'gp', 'testing', 'pre-season', 'season', 'the', 'race', 'in', 'on', 'at'}
        query_words = [w.strip("?,.!:;").lower() for w in query.split()]
        
        for _, row in schedule.iterrows():
            event_name = str(row['EventName']).lower()
            location = str(row['Location']).lower()
            country = str(row['Country']).lower()
            
            if location in query_words or country in query_words:
                return str(row['EventName'])
                
            event_words = [w for w in event_name.split() if w not in stop_words]
            for ew in event_words:
                if ew in query_words:
                    return str(row['EventName'])
    except Exception:
        pass
    return None

def extract_drivers(text: str, session) -> list:
    try:
        available_drivers = session.results[['Abbreviation', 'FirstName', 'LastName', 'FullName']]
    except Exception:
        return []
        
    matched_drivers = []
    text_lower = text.lower()
    text_words = [w.strip("?,.!:;()").lower() for w in text.split()]
    
    for _, row in available_drivers.iterrows():
        abbrev = str(row['Abbreviation']).lower()
        firstname = str(row['FirstName']).lower()
        lastname = str(row['LastName']).lower()
        fullname = str(row['FullName']).lower()
        
        if (abbrev in text_words or 
            firstname in text_words or 
            lastname in text_lower or 
            fullname in text_lower):
            matched_drivers.append(str(row['Abbreviation']))
            
    return matched_drivers

def generate_telemetry_plot(year: int, grand_prix: str, session_type: str, drivers: list) -> str:
    """Generates speed telemetry plot comparison and saves it to the frontend folder."""
    try:
        session = fastf1.get_session(year, grand_prix, session_type)
        session.load(telemetry=True, weather=False)
        
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor('#0f1115')
        ax.set_facecolor('#15181f')
        ax.spines['bottom'].set_color('#a0aab2')
        ax.spines['top'].set_color('#a0aab2')
        ax.spines['left'].set_color('#a0aab2')
        ax.spines['right'].set_color('#a0aab2')
        ax.tick_params(colors='#a0aab2', which='both')
        ax.yaxis.label.set_color('#a0aab2')
        ax.xaxis.label.set_color('#a0aab2')
        ax.title.set_color('#ffffff')
        
        fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1')
        
        plotted_count = 0
        for driver in drivers:
            try:
                laps = session.laps.pick_drivers(driver)
                if laps.empty:
                    continue
                fastest = laps.pick_fastest()
                telemetry = fastest.get_telemetry().add_distance()
                
                try:
                    style = plotting.get_driver_style(identifier=driver, style=['color'], session=session)
                    color = style['color']
                except Exception:
                    color = None
                
                driver_row = session.results[session.results['Abbreviation'] == driver]
                driver_name = driver_row.iloc[0]['FullName'] if not driver_row.empty else driver
                
                ax.plot(telemetry['Distance'], telemetry['Speed'], label=driver_name, color=color)
                plotted_count += 1
            except Exception:
                pass
                
        if plotted_count == 0:
            plt.close(fig)
            return "Error: Could not plot telemetry for any of the specified drivers."
            
        ax.set_xlabel('Distance in m')
        ax.set_ylabel('Speed in km/h')
        ax.set_title(f'Speed Telemetry Comparison - {year} {grand_prix}')
        ax.legend(facecolor='#15181f', edgecolor='#a0aab2', labelcolor='#ffffff')
        plt.tight_layout()
        
        frontend_graphs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'graphs'))
        if not os.path.exists(frontend_graphs_dir):
            os.makedirs(frontend_graphs_dir)
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"telemetry_{year}_{grand_prix.replace(' ', '_')}_{timestamp}.png"
        filepath = os.path.join(frontend_graphs_dir, filename)
        
        fig.savefig(filepath, facecolor=fig.get_facecolor(), edgecolor='none', dpi=150)
        plt.close(fig)
        
        return f'<div class="graph-container"><img src="/static/graphs/{filename}" alt="Telemetry Plot" /></div>'
    except Exception as e:
        return f"Error generating telemetry plot: {e}"

def generate_laptimes_plot(year: int, grand_prix: str, session_type: str, drivers: list) -> str:
    """Generates lap time plot comparison and saves it to the frontend folder."""
    try:
        session = fastf1.get_session(year, grand_prix, session_type)
        session.load(telemetry=False, weather=False)
        
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor('#0f1115')
        ax.set_facecolor('#15181f')
        ax.spines['bottom'].set_color('#a0aab2')
        ax.spines['top'].set_color('#a0aab2')
        ax.spines['left'].set_color('#a0aab2')
        ax.spines['right'].set_color('#a0aab2')
        ax.tick_params(colors='#a0aab2', which='both')
        ax.yaxis.label.set_color('#a0aab2')
        ax.xaxis.label.set_color('#a0aab2')
        ax.title.set_color('#ffffff')
        
        fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1')
        
        plotted_count = 0
        for driver in drivers:
            try:
                laps = session.laps.pick_drivers(driver).pick_quicklaps().reset_index()
                if laps.empty:
                    continue
                    
                try:
                    style = plotting.get_driver_style(identifier=driver, style=['color', 'linestyle'], session=session)
                except Exception:
                    style = {'color': None}
                    
                driver_row = session.results[session.results['Abbreviation'] == driver]
                driver_name = driver_row.iloc[0]['FullName'] if not driver_row.empty else driver
                
                ax.plot(laps['LapNumber'], laps['LapTime'], **style, label=driver_name)
                plotted_count += 1
            except Exception:
                pass
                
        if plotted_count == 0:
            plt.close(fig)
            return "Error: Could not plot lap times for any of the specified drivers."
            
        ax.set_xlabel('Lap Number')
        ax.set_ylabel('Lap Time')
        ax.set_title(f'Lap Time Comparison - {year} {grand_prix}')
        ax.legend(facecolor='#15181f', edgecolor='#a0aab2', labelcolor='#ffffff')
        plt.tight_layout()
        
        frontend_graphs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'graphs'))
        if not os.path.exists(frontend_graphs_dir):
            os.makedirs(frontend_graphs_dir)
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"laptimes_{year}_{grand_prix.replace(' ', '_')}_{timestamp}.png"
        filepath = os.path.join(frontend_graphs_dir, filename)
        
        fig.savefig(filepath, facecolor=fig.get_facecolor(), edgecolor='none', dpi=150)
        plt.close(fig)
        
        return f'<div class="graph-container"><img src="/static/graphs/{filename}" alt="Lap Time Plot" /></div>'
    except Exception as e:
        return f"Error generating lap times plot: {e}"

def extract_position(query: str) -> int:
    match_ord = re.search(r'\b(\d+)(st|nd|rd|th)\b', query.lower())
    if match_ord:
        return int(match_ord.group(1))
        
    word_to_num = {
        'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
        'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10,
        'eleventh': 11, 'twelfth': 12, 'thirteenth': 13, 'fourteenth': 14, 'fifteenth': 15,
        'sixteenth': 16, 'seventeenth': 17, 'eighteenth': 18, 'nineteenth': 19, 'twentieth': 20
    }
    for word, num in word_to_num.items():
        if word in query.lower().split():
            return num
            
    match_num = re.search(r'\b(?:position|place|came|finished|p)\s*#?(\d+)\b', query.lower())
    if match_num:
        return int(match_num.group(1))
        
    return None

def ask_f1_agent(query: str, history: list = None) -> str:
    """Main function to ask the F1 agent a question. This local implementation uses rule-based parsing and regex to parse queries for free and with zero external rate limits."""
    # 1. Resolve Year
    year = extract_year(query)
    if not year and history:
        for msg in reversed(history):
            h_year = extract_year(msg['content'])
            if h_year:
                year = h_year
                break
    if not year:
        year = datetime.date.today().year

    query_words = [w.strip("?,.!:;").lower() for w in query.split()]
    
    # Check for reasoning/strategy query
    reasoning_keywords = {"should", "why", "explain", "how to", "strategy", "chances", "opinion", "what if", "would"}
    is_reasoning_query = any(k in query_words for k in reasoning_keywords) or "what should" in query.lower()
    
    reasoning_note = ""
    if is_reasoning_query:
        reasoning_note = "*Note: Because I am running on a local query parser (to save API quota), I can only retrieve structured F1 data and cannot perform complex strategy, opinion, or qualitative analysis. Here is the relevant data for your query:*\n\n"

    relative_keywords = {"last", "recent", "latest", "ago", "yesterday", "days"}
    is_relative = any(k in query_words for k in relative_keywords)
    
    # 2. Resolve Grand Prix
    grand_prix = find_grand_prix(query, year)
    if not grand_prix and history:
        for msg in reversed(history):
            h_gp = find_grand_prix(msg['content'], year)
            if h_gp:
                grand_prix = h_gp
                break
                
    if not grand_prix and is_relative:
        grand_prix = find_most_recent_grand_prix(year)
        
    if not grand_prix:
        grand_prix = find_most_recent_grand_prix(year)
        if not grand_prix:
            return "I couldn't identify the Grand Prix you are asking about. Please specify a location (e.g. 'Barcelona' or 'Monaco')."
            
    session_type = 'R'
    if 'qualifying' in query.lower() or ' quali' in query.lower():
        session_type = 'Q'
    elif 'sprint' in query.lower():
        session_type = 'S'
    elif 'practice' in query.lower():
        if '1' in query: session_type = 'FP1'
        elif '2' in query: session_type = 'FP2'
        elif '3' in query: session_type = 'FP3'
        else: session_type = 'FP1'
        
    # Check for graph/telemetry generation requests
    is_graph_request = any(k in query.lower() for k in ["plot", "telemetry", "graph", "chart", "show speed"])
    if is_graph_request:
        try:
            try:
                session = fastf1.get_session(year, grand_prix, session_type)
                session.load(telemetry=False, weather=False)
            except Exception:
                session = fastf1.get_session(year, grand_prix, 'R')
                session.load(telemetry=False, weather=False)
                
            drivers = extract_drivers(query, session)
            if not drivers and history:
                for msg in reversed(history):
                    h_drivers = extract_drivers(msg['content'], session)
                    if h_drivers:
                        drivers = h_drivers
                        break
                        
            # Default to top 2 if still empty
            if not drivers:
                try:
                    top_drivers = session.results.sort_values(by='Position').head(2)
                    drivers = top_drivers['Abbreviation'].tolist()
                except Exception:
                    drivers = ['HAM', 'VER']
        except Exception as e:
            return f"Error loading results for graphing: {e}"
            
        if 'lap time' in query.lower() or 'laptimes' in query.lower() or 'laptime' in query.lower():
            graph_html = generate_laptimes_plot(year, grand_prix, session_type, drivers)
            return f"Here is the lap time comparison for **{', '.join(drivers)}** in the **{year} {grand_prix}**:\n\n{graph_html}"
        else:
            graph_html = generate_telemetry_plot(year, grand_prix, session_type, drivers)
            return f"Here is the speed telemetry comparison for **{', '.join(drivers)}** in the **{year} {grand_prix}**:\n\n{graph_html}"

    # Try local Ollama or Groq LLM RAG first if available
    ollama_url = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    
    ollama_available = False
    try:
        import requests
        check_resp = requests.get(f"{ollama_url}/api/tags", timeout=1)
        if check_resp.status_code == 200:
            ollama_available = True
    except Exception:
        pass

    groq_api_key = os.environ.get("GROQ_API_KEY")
    
    if ollama_available or groq_api_key:
        try:
            # Load session results to form database context
            try:
                session = fastf1.get_session(year, grand_prix, session_type)
                session.load(telemetry=False, weather=False)
            except Exception:
                session = fastf1.get_session(year, grand_prix, 'R')
                session.load(telemetry=False, weather=False)
                
            context_data = f"Race Results:\n{session.results[['Position', 'FullName', 'Abbreviation', 'TeamName', 'Time', 'Status']].to_string(index=False)}\n\n"
            
            # Extract drivers to include lap times context if relevant
            drivers = extract_drivers(query, session)
            if not drivers and history:
                for msg in reversed(history):
                    h_drivers = extract_drivers(msg['content'], session)
                    if h_drivers:
                        drivers = h_drivers
                        break
            if drivers:
                for d in drivers:
                    try:
                        df_laps = session.laps.pick_drivers(d).dropna(subset=['LapTime'])
                        laps_str = df_laps[['LapNumber', 'LapTime', 'Compound', 'TyreLife']].tail(15).to_string(index=False)
                        context_data += f"Last 15 laps for {d}:\n{laps_str}\n\n"
                    except Exception:
                        pass
                        
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are a helpful Formula 1 assistant. Today's date is {datetime.date.today().strftime('%B %d, %Y')}. "
                        "You are running in a RAG system and have access to the F1 database context below. "
                        "Use this data to answer strategic, qualitative, or analytical F1 questions (like why a driver placed where they did, strategy options, or comparisons). "
                        "Format your responses nicely in markdown for a web dashboard. When referring to drivers, always use their full name."
                    )
                },
                {
                    "role": "system",
                    "content": f"F1 Database Context for current race ({year} {grand_prix}):\n{context_data}"
                }
            ]
            
            if history:
                for h in history:
                    messages.append({"role": h["role"], "content": h["content"]})
                    
            messages.append({"role": "user", "content": query})
            
            # 1. Try local Ollama first
            if ollama_available:
                try:
                    payload = {
                        "model": ollama_model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.2
                        }
                    }
                    ollama_resp = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=60)
                    if ollama_resp.status_code == 200:
                        return ollama_resp.json()["message"]["content"]
                except Exception as e:
                    print(f"Ollama generation failed: {e}. Trying Groq if available.")
            
            # 2. Try Groq API second
            if groq_api_key:
                try:
                    from groq import Groq
                    client = Groq(api_key=groq_api_key)
                    completion = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=messages,
                        temperature=0.2,
                    )
                    return completion.choices[0].message.content
                except Exception as e:
                    print(f"Groq API error: {e}. Falling back to local parser.")
        except Exception as e:
            print(f"RAG reasoning query failed: {e}. Falling back to local parser.")

    if 'fastest lap' in query.lower() or 'fastest time' in query.lower():
        return get_fastest_lap(year, grand_prix, session_type)
        
    is_laptimes_request = any(k in query.lower() for k in ["lap time", "laptimes", "laptime", "laps"])
    if is_laptimes_request:
        try:
            session = fastf1.get_session(year, grand_prix, session_type)
            session.load(telemetry=False, weather=False)
            
            drivers = extract_drivers(query, session)
            if not drivers and history:
                for msg in reversed(history):
                    h_drivers = extract_drivers(msg['content'], session)
                    if h_drivers:
                        drivers = h_drivers
                        break
                        
            if not drivers:
                return "Please specify a driver (name or abbreviation) to show lap times for."
                
            driver = drivers[0]
            driver_laps = session.laps.pick_drivers(driver).dropna(subset=['LapTime'])
            if driver_laps.empty:
                return f"No lap data found for driver {driver} in the {year} {grand_prix}."
                
            count = 10  # Default to 10
            match_count = re.search(r'\b(\d+)\s+laps?\b', query.lower())
            if match_count:
                count = int(match_count.group(1))
                
            is_first = 'first' in query.lower()
            if is_first:
                selected_laps = driver_laps.head(count)
                title_prefix = f"First {count}"
            else:
                selected_laps = driver_laps.tail(count)
                title_prefix = f"Last {count}"
                
            driver_row = session.results[session.results['Abbreviation'] == driver]
            driver_name = driver_row.iloc[0]['FullName'] if not driver_row.empty else driver
            
            response = f"### {driver_name} - {title_prefix} Laps ({year} {grand_prix})\n\n"
            response += "| Lap Number | Lap Time | Compound | Tyre Life |\n"
            response += "| --- | --- | --- | --- |\n"
            
            for _, row in selected_laps.iterrows():
                lap_num = int(row['LapNumber'])
                lap_time_td = row['LapTime']
                
                try:
                    total_seconds = lap_time_td.total_seconds()
                    minutes = int(total_seconds // 60)
                    seconds = total_seconds % 60
                    lap_time_str = f"{minutes}:{seconds:06.3f}"
                except Exception:
                    lap_time_str = str(lap_time_td)
                    
                compound = row['Compound']
                tyre_life = int(row['TyreLife']) if not pd.isna(row['TyreLife']) else "N/A"
                response += f"| {lap_num} | {lap_time_str} | {compound} | {tyre_life} |\n"
                
            return response
        except Exception as e:
            return f"Error retrieving lap times: {e}"
        
    try:
        session = fastf1.get_session(year, grand_prix, session_type)
        session.load(telemetry=False, weather=False)
        df = session.results
    except Exception as e:
        return f"Error retrieving F1 data: {e}"
        
    # Check if a specific driver was mentioned or fallback to history context
    matched_driver = None
    drivers = extract_drivers(query, session)
    if not drivers and history:
        for msg in reversed(history):
            h_drivers = extract_drivers(msg['content'], session)
            if h_drivers:
                drivers = h_drivers
                break
                
    if drivers:
        driver_code = drivers[0]
        df_driver = df[df['Abbreviation'] == driver_code]
        if not df_driver.empty:
            matched_driver = df_driver.iloc[0]
            
    if matched_driver is not None:
        pos = int(matched_driver['Position']) if not pd.isna(matched_driver['Position']) else "N/A"
        team = matched_driver['TeamName']
        status = matched_driver['Status']
        
        suffix = "th"
        if isinstance(pos, int):
            if pos == 1: suffix = "st"
            elif pos == 2: suffix = "nd"
            elif pos == 3: suffix = "rd"
            pos_str = f"{pos}{suffix}"
        else:
            pos_str = pos
            
        return reasoning_note + f"In the {year} {grand_prix} Race, **{matched_driver['FullName']}** ({matched_driver['Abbreviation']}) driving for **{team}** finished in **{pos_str}** place with status: *{status}*."

    # Check for specific position request
    requested_pos = extract_position(query)
    if requested_pos is not None:
        df_sorted = df[df['Position'] == float(requested_pos)]
        if not df_sorted.empty:
            driver_row = df_sorted.iloc[0]
            team = driver_row['TeamName']
            status = driver_row['Status']
            suffix = "th"
            if requested_pos == 1: suffix = "st"
            elif requested_pos == 2: suffix = "nd"
            elif requested_pos == 3: suffix = "rd"
            return reasoning_note + f"In the {year} {grand_prix} Race, **{driver_row['FullName']}** ({driver_row['Abbreviation']}) finished in **{requested_pos}{suffix}** place driving for **{team}** with status: *{status}*."
        else:
            return f"No driver was found in position {requested_pos} for the {year} {grand_prix} Race."

    # Check for last place
    if 'last' in query_words:
        df_sorted = df.dropna(subset=['Position']).sort_values(by='Position')
        if not df_sorted.empty:
            last_driver = df_sorted.iloc[-1]
            pos = int(last_driver['Position'])
            return reasoning_note + f"The last driver in the {year} {grand_prix} Race was **{last_driver['FullName']}** from **{last_driver['TeamName']}**, who finished in **{pos}** position."
            
    # Check for winner
    if 'winner' in query_words or 'won' in query_words or 'first' in query_words or '1st' in query_words:
        df_sorted = df[df['Position'] == 1.0]
        if not df_sorted.empty:
            winner = df_sorted.iloc[0]
            return reasoning_note + f"The winner of the {year} {grand_prix} Race was **{winner['FullName']}** driving for **{winner['TeamName']}**."
            
    # Check for podium
    if 'podium' in query_words or 'top 3' in query_words or 'top three' in query:
        df_sorted = df[df['Position'].isin([1.0, 2.0, 3.0])].sort_values(by='Position')
        if not df_sorted.empty:
            podium_list = []
            for _, row in df_sorted.iterrows():
                podium_list.append(f"{int(row['Position'])}. **{row['FullName']}** ({row['TeamName']})")
            return reasoning_note + f"The podium finishers for the {year} {grand_prix} Race were:\n" + "\n".join(podium_list)

    # General fallback: return table of top 10
    df_top_10 = df[['Position', 'FullName', 'TeamName', 'Status']].head(10)
    markdown_results = f"### {year} {grand_prix} Results (Top 10)\n\n"
    markdown_results += "| Position | Driver | Team | Status |\n"
    markdown_results += "| --- | --- | --- | --- |\n"
    for _, row in df_top_10.iterrows():
        pos = int(row['Position']) if not pd.isna(row['Position']) else "N/A"
        markdown_results += f"| {pos} | {row['FullName']} | {row['TeamName']} | {row['Status']} |\n"
    return reasoning_note + markdown_results
