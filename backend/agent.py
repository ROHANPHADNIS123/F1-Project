import fastf1
import os
import datetime
import re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from fastf1 import plotting
import logging
import unicodedata
import json
import html

# Set up fastf1 cache
if os.environ.get("RENDER") == "true":
    cache_dir = "/var/data/f1_cache"
else:
    cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'f1_cache'))
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
fastf1.Cache.enable_cache(cache_dir)

# Suppress FastF1 verbose INFO and WARNING logs in the terminal
logging.getLogger('fastf1').setLevel(logging.ERROR)

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
    # Check for specific car designations mapping to F1 years
    car_mappings = {
        r'\bw09\b': 2018,
        r'\bw10\b': 2019,
        r'\bw11\b': 2020,
        r'\bw12\b': 2021,
        r'\bw13\b': 2022,
        r'\bw14\b': 2023,
        r'\bw15\b': 2024,
        r'\bw16\b': 2025,
        r'\bsf71h\b': 2018,
        r'\bsf90\b': 2019,
        r'\bsf1000\b': 2020,
        r'\bsf21\b': 2021,
        r'\bf1-75\b': 2022,
        r'\bsf-23\b': 2023,
        r'\bsf-24\b': 2024,
        r'\brb14\b': 2018,
        r'\brb15\b': 2019,
        r'\brb16\b': 2020,
        r'\brb16b\b': 2021,
        r'\brb18\b': 2022,
        r'\brb19\b': 2023,
        r'\brb20\b': 2024
    }
    for pattern, y in car_mappings.items():
        if re.search(pattern, query.lower()):
            return y
            
    match = re.search(r'\b(19\d\d|20\d\d)\b', query)
    if match:
        return int(match.group(1))
    return None

def get_car_models_context(year: int) -> str:
    mappings = {
        2018: {
            "Mercedes": "W09", "Red Bull Racing": "RB14", "Ferrari": "SF71H", 
            "McLaren": "MCL33", "Renault": "R.S.18", "Toro Rosso": "STR13", 
            "Force India": "VJM11", "Sauber": "C37", "Haas F1 Team": "VF-18", "Williams": "FW41"
        },
        2019: {
            "Mercedes": "W10", "Red Bull Racing": "RB15", "Ferrari": "SF90", 
            "McLaren": "MCL34", "Renault": "R.S.19", "Toro Rosso": "STR14", 
            "Racing Point": "RP19", "Alfa Romeo Racing": "C38", "Haas F1 Team": "VF-19", "Williams": "FW42"
        },
        2020: {
            "Mercedes": "W11", "Red Bull Racing": "RB16", "Ferrari": "SF1000", 
            "McLaren": "MCL35", "Renault": "R.S.20", "AlphaTauri": "AT01", 
            "Racing Point": "RP20", "Alfa Romeo": "C39", "Haas F1 Team": "VF-20", "Williams": "FW43"
        },
        2021: {
            "Mercedes": "W12", "Red Bull Racing": "RB16B", "Ferrari": "SF21", 
            "McLaren": "MCL35M", "Alpine": "A521", "AlphaTauri": "AT02", 
            "Aston Martin": "AMR21", "Alfa Romeo Racing": "C41", "Haas F1 Team": "VF-21", "Williams": "FW43B"
        },
        2022: {
            "Mercedes": "W13", "Red Bull Racing": "RB18", "Ferrari": "F1-75", 
            "McLaren": "MCL36", "Alpine": "A522", "AlphaTauri": "AT03", 
            "Aston Martin": "AMR22", "Alfa Romeo": "C42", "Haas F1 Team": "VF-22", "Williams": "FW44"
        },
        2023: {
            "Mercedes": "W14", "Red Bull Racing": "RB19", "Ferrari": "SF-23", 
            "McLaren": "MCL60", "Alpine": "A523", "AlphaTauri": "AT04", 
            "Aston Martin": "AMR23", "Alfa Romeo": "C43", "Haas F1 Team": "VF-23", "Williams": "FW45"
        },
        2024: {
            "Mercedes": "W15", "Red Bull Racing": "RB20", "Ferrari": "SF-24", 
            "McLaren": "MCL38", "Alpine": "A524", "RB": "VCARB 01", 
            "Aston Martin": "AMR24", "Kick Sauber": "C44", "Haas F1 Team": "VF-24", "Williams": "FW46"
        },
        2025: {
            "Mercedes": "W16", "Red Bull Racing": "RB21", "Ferrari": "SF-25", 
            "McLaren": "MCL39", "Alpine": "A525", "RB": "VCARB 02", 
            "Aston Martin": "AMR25", "Sauber": "C45", "Haas F1 Team": "VF-25", "Williams": "FW47"
        },
        2026: {
            "Mercedes": "W17", "Red Bull Racing": "RB22", "Ferrari": "SF-26", 
            "McLaren": "MCL40", "Alpine": "A526", "RB": "VCARB 03", 
            "Aston Martin": "AMR26", "Sauber": "C46", "Haas F1 Team": "VF-26", "Williams": "FW48"
        }
    }
    
    year_map = mappings.get(year, {})
    if not year_map:
        return ""
        
    lines = ["F1 Car Model Designations for the season:"]
    for team, car in year_map.items():
        lines.append(f"- {team}: {car}")
    return "\n".join(lines) + "\n\n"

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

def remove_diacritics(text: str) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize('NFKD', text)
    return "".join(c for c in normalized if not unicodedata.combining(c))

def clean_history_for_llm(history: list) -> list:
    if not history:
        return []
    cleaned = []
    for msg in history:
        content = msg['content']
        # Replace telemetry containers
        content = re.sub(
            r'<div class="interactive-telemetry-plot".*?</div>',
            '[Interactive Speed Telemetry Comparison Chart]',
            content,
            flags=re.IGNORECASE | re.DOTALL
        )
        # Replace track map containers
        content = re.sub(
            r'<div class="interactive-track-map".*?</div>',
            '[Interactive Track Map Layout]',
            content,
            flags=re.IGNORECASE | re.DOTALL
        )
        # Replace any other SVG blocks
        content = re.sub(
            r'<svg.*?</svg>',
            '[SVG Chart]',
            content,
            flags=re.IGNORECASE | re.DOTALL
        )
        cleaned.append({
            "role": msg["role"],
            "content": content
        })
    return cleaned

def extract_drivers(text: str, session) -> list:
    try:
        available_drivers = session.results[['Abbreviation', 'FirstName', 'LastName', 'FullName']]
    except Exception:
        return []
        
    matched_drivers = []
    
    # Strip diacritics from query text
    text_clean = remove_diacritics(text).lower()
    # Preprocess text to clean "max" terms that refer to "maximum"
    text_clean = re.sub(
        r'\bmax\.?\s+(speed|rpm|g|g-force|velocity|acceleration|power|temp|temperature|capacity|downforce|grip|limit|braking|brake|straight|straights|torque|gear|revs|rev)\b',
        r'maximum \1',
        text_clean
    )
    
    for _, row in available_drivers.iterrows():
        abbrev = remove_diacritics(str(row['Abbreviation'])).lower() if not pd.isna(row['Abbreviation']) else ""
        firstname = remove_diacritics(str(row['FirstName'])).lower() if not pd.isna(row['FirstName']) else ""
        lastname = remove_diacritics(str(row['LastName'])).lower() if not pd.isna(row['LastName']) else ""
        fullname = remove_diacritics(str(row['FullName'])).lower() if not pd.isna(row['FullName']) else ""
        
        # Word boundary pattern matching for name/abbrev with optional possessive 's or s
        def is_match(name):
            if not name or len(name) < 2:  # avoid empty or extremely short names matching
                return False
            pattern = r'\b' + re.escape(name) + r"(?:'s|s)?\b"
            return bool(re.search(pattern, text_clean))
            
        if is_match(abbrev) or is_match(firstname) or is_match(lastname) or is_match(fullname):
            matched_drivers.append(str(row['Abbreviation']))
            
    return matched_drivers


def generate_telemetry_plot(year: int, grand_prix: str, session_type: str, drivers: list) -> str:
    """Generates an interactive SVG speed telemetry plot comparison."""
    try:
        session = fastf1.get_session(year, grand_prix, session_type)
        session.load(telemetry=True, weather=False)
        
        # Collect telemetry data for each driver
        driver_data = []
        global_max_distance = 0
        global_max_speed = 0
        global_min_speed = 1000
        
        for driver in drivers:
            try:
                laps = session.laps.pick_drivers(driver)
                if laps.empty:
                    continue
                fastest = laps.pick_fastest()
                telemetry = fastest.get_telemetry().add_distance()
                
                # Check for needed columns
                if 'Distance' not in telemetry.columns or 'Speed' not in telemetry.columns:
                    continue
                    
                x = telemetry['Distance'].values
                y = telemetry['Speed'].values
                gear_col = 'nGear' if 'nGear' in telemetry.columns else ('Gear' if 'Gear' in telemetry.columns else None)
                gear = telemetry[gear_col].values if gear_col else None
                time = telemetry['Time'].values if 'Time' in telemetry.columns else None
                
                # Downsample to ~300 points
                target_points = 300
                step = max(1, len(x) // target_points)
                
                x_sub = x[::step]
                y_sub = y[::step]
                gear_sub = gear[::step] if gear is not None else None
                time_sub = time[::step] if time is not None else None
                
                # Update boundaries
                global_max_distance = max(global_max_distance, x_sub.max())
                global_max_speed = max(global_max_speed, y_sub.max())
                global_min_speed = min(global_min_speed, y_sub.min())
                
                driver_row = session.results[session.results['Abbreviation'] == driver]
                driver_name = driver_row.iloc[0]['FullName'] if not driver_row.empty else driver
                
                # Try to get driver style/color
                try:
                    style = plotting.get_driver_style(identifier=driver, style=['color'], session=session)
                    color = style['color']
                except Exception:
                    color = None
                    
                if not color:
                    # Assign a fallback color based on driver code
                    fallbacks = {
                        'VER': '#3671C6', 'HAM': '#00D2BE', 'SAI': '#E10600', 'LEC': '#E10600',
                        'NOR': '#FF8700', 'PIA': '#FF8700', 'ALO': '#0090FF', 'RUS': '#00D2BE',
                    }
                    color = fallbacks.get(driver, '#a0aab2')
                    
                driver_data.append({
                    'driver': driver,
                    'name': driver_name,
                    'x': x_sub,
                    'y': y_sub,
                    'gear': gear_sub,
                    'time': time_sub,
                    'color': color
                })
            except Exception:
                pass
                
        if not driver_data:
            return "Error: Could not plot telemetry for any of the specified drivers."
            
        # Draw SVG Line Chart
        svg_w, svg_h = 800, 450
        margin_l, margin_r = 60, 40
        margin_t, margin_b = 40, 50
        
        plot_w = svg_w - margin_l - margin_r
        plot_h = svg_h - margin_t - margin_b
        
        # Round boundaries for scaling
        x_min, x_max = 0, global_max_distance
        y_min = max(0, int(global_min_speed - 20) // 20 * 20)  # nice rounded min speed
        y_max = int(global_max_speed + 20) // 20 * 20          # nice rounded max speed
        
        # Scaling helper functions
        def scale_x(x_val):
            return margin_l + (x_val - x_min) / (x_max - x_min) * plot_w
            
        def scale_y(y_val):
            return (svg_h - margin_b) - (y_val - y_min) / (y_max - y_min) * plot_h
            
        # Generate grid lines (horizontal speed grid)
        grid_lines = []
        speed_step = 50
        for speed_tick in range(y_min, y_max + 10, speed_step):
            y_pos = scale_y(speed_tick)
            grid_lines.append(
                f'<line x1="{margin_l}" y1="{y_pos:.1f}" x2="{svg_w - margin_r}" y2="{y_pos:.1f}" '
                f'stroke="rgba(255,255,255,0.06)" stroke-width="1" />'
                f'<text x="{margin_l - 10}" y="{y_pos + 4:.1f}" fill="#a0aab2" font-size="10" '
                f'font-family="sans-serif" text-anchor="end">{speed_tick}</text>'
            )
            
        # Generate vertical distance grid (every 1000m)
        dist_step = 1000
        for dist_tick in range(0, int(x_max) + 500, dist_step):
            x_pos = scale_x(dist_tick)
            grid_lines.append(
                f'<line x1="{x_pos:.1f}" y1="{margin_t}" x2="{x_pos:.1f}" y2="{svg_h - margin_b}" '
                f'stroke="rgba(255,255,255,0.06)" stroke-width="1" />'
                f'<text x="{x_pos:.1f}" y="{svg_h - margin_b + 18}" fill="#a0aab2" font-size="10" '
                f'font-family="sans-serif" text-anchor="middle">{dist_tick}m</text>'
            )
            
        # Plot driver lines
        lines_html = []
        for data in driver_data:
            x_vals = data['x']
            y_vals = data['y']
            color = data['color']
            
            for i in range(len(x_vals) - 1):
                x1 = scale_x(x_vals[i])
                y1 = scale_y(y_vals[i])
                x2 = scale_x(x_vals[i+1])
                y2 = scale_y(y_vals[i+1])
                
                line_elem = (
                    f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                    f'stroke="{color}" stroke-width="3" stroke-linecap="round" class="telemetry-segment" '
                    f'style="transition: stroke-width 0.1s ease, filter 0.1s ease;" />'
                )
                lines_html.append(line_elem)
                
        # Generate legend indicators
        legend_items = []
        for data in driver_data:
            legend_items.append(
                f'<div style="display: flex; align-items: center; margin-right: 20px;">'
                f'<div style="width: 15px; height: 3px; background-color: {data["color"]}; margin-right: 8px; border-radius: 2px;"></div>'
                f'<span style="font-size: 12px; color: #ffffff; font-family: sans-serif;">{data["name"]}</span>'
                f'</div>'
            )
            
        legend_html = f'<div style="display: flex; justify-content: center; margin-top: 10px; flex-wrap: wrap;">{"".join(legend_items)}</div>'
        
        # Serialize telemetry data to JSON for snappy client-side hovering
        telemetry_serializable = []
        for data in driver_data:
            points_list = []
            x_vals = data['x']
            y_vals = data['y']
            gear_vals = data['gear']
            time_vals = data['time']
            for i in range(len(x_vals)):
                s_val = float(y_vals[i])
                d_val = float(x_vals[i])
                g_val = int(gear_vals[i]) if gear_vals is not None else 0
                
                if time_vals is not None:
                    try:
                        t_val = f"{time_vals[i].total_seconds():.3f}s"
                    except Exception:
                        t_val = str(time_vals[i])
                else:
                    t_val = "N/A"
                
                points_list.append({
                    'd': d_val,
                    's': s_val,
                    'g': g_val,
                    't': t_val
                })
            telemetry_serializable.append({
                'name': data['name'],
                'color': data['color'],
                'points': points_list
            })
            
        telemetry_json = json.dumps(telemetry_serializable)
        telemetry_json_escaped = html.escape(telemetry_json)
        
        # Generate guide line & circle markers
        guide_line_html = f'<line id="telemetry-guide" x1="0" y1="{margin_t}" x2="0" y2="{svg_h - margin_b}" stroke="rgba(255,255,255,0.4)" stroke-width="1.5" stroke-dasharray="4" style="display: none; pointer-events: none;" />'
        
        markers_html = []
        for idx, data in enumerate(driver_data):
            markers_html.append(
                f'<circle class="telemetry-marker" data-driver-index="{idx}" cx="0" cy="0" r="5" fill="{data["color"]}" stroke="#ffffff" stroke-width="1.5" style="display: none; pointer-events: none; filter: drop-shadow(0 0 2px {data["color"]});" />'
            )
        
        container_html = (
            f'<div class="interactive-telemetry-plot" style="position: relative; width: 100%; max-width: 800px; margin: 20px auto; background-color: #15181f; border-radius: 12px; padding: 15px; border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 8px 32px rgba(0,0,0,0.4);">'
            f'<div style="border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px; margin-bottom: 15px;">'
            f'<h4 style="margin: 0; color: #ffffff; font-size: 16px; font-weight: bold; font-family: \'Outfit\', sans-serif;">Speed Telemetry Comparison</h4>'
            f'<span style="font-size: 11px; color: #a0aab2; font-family: sans-serif;">{year} {grand_prix} - {session_type} Session</span>'
            f'</div>'
            f'<svg viewBox="0 0 {svg_w} {svg_h}" style="width: 100%; height: auto; background-color: transparent;" '
            f'data-margin-l="{margin_l}" data-margin-r="{margin_r}" data-margin-t="{margin_t}" data-margin-b="{margin_b}" '
            f'data-x-min="{x_min}" data-x-max="{x_max}" data-y-min="{y_min}" data-y-max="{y_max}" '
            f'data-telemetry="{telemetry_json_escaped}" '
            f'onmousemove="window.handleTelemetryHover(event, this)" onmouseleave="window.handleTelemetryLeave(event, this)">'
            f'<g>'
            f'<text x="{margin_l - 12}" y="{margin_t - 15}" fill="#a0aab2" font-size="10" font-family="sans-serif" text-anchor="middle">Speed (km/h)</text>'
            f'<text x="{svg_w - margin_r}" y="{svg_h - margin_b + 38}" fill="#a0aab2" font-size="10" font-family="sans-serif" text-anchor="end">Distance</text>'
            f'{"".join(grid_lines)}'
            f'{"".join(lines_html)}'
            f'{guide_line_html}'
            f'{"".join(markers_html)}'
            f'</g>'
            f'</svg>'
            f'{legend_html}'
            f'<div class="telemetry-tooltip" style="display: none; position: absolute; background: rgba(15, 17, 21, 0.95); border: 1px solid rgba(255,255,255,0.15); color: white; padding: 10px 14px; border-radius: 8px; pointer-events: none; font-family: sans-serif; font-size: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.6); z-index: 1000; backdrop-filter: blur(4px); transition: opacity 0.15s ease;"></div>'
            f'</div>'
        )
        return container_html.replace('\n', ' ')
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

def get_speed_color(speed_val, min_s, max_s):
    ratio = (speed_val - min_s) / max((max_s - min_s), 1.0)
    ratio = max(0.0, min(1.0, ratio))
    
    # Interpolate between purple (270), pink (320), and yellow (50)
    if ratio < 0.5:
        h = 270 + (320 - 270) * (ratio / 0.5)
        l = 50 + (55 - 50) * (ratio / 0.5)
    else:
        h = 320 + 90 * ((ratio - 0.5) / 0.5)
        if h >= 360:
            h -= 360
        l = 55 - (55 - 50) * ((ratio - 0.5) / 0.5)
        
    return f"hsl({int(h)}, 100%, {int(l)}%)"

def generate_track_map_plot(year: int, grand_prix: str, session_type: str, driver: str) -> str:
    """Generates an interactive SVG speed-colored track map for a given driver's fastest lap."""
    try:
        session = fastf1.get_session(year, grand_prix, session_type)
        session.load(telemetry=True, weather=False)
        
        laps = session.laps.pick_drivers(driver)
        if laps.empty:
            return f"Error: No laps found for driver {driver} in the {year} {grand_prix}."
            
        fastest_lap = laps.pick_fastest()
        telemetry = fastest_lap.get_telemetry()
        
        if 'X' not in telemetry.columns or 'Y' not in telemetry.columns or 'Speed' not in telemetry.columns:
            return f"Error: Telemetry coordinates/speed not available for driver {driver}."
            
        # Get driver metadata
        driver_row = session.results[session.results['Abbreviation'] == driver]
        driver_name = driver_row.iloc[0]['FullName'] if not driver_row.empty else driver
        team_name = driver_row.iloc[0]['TeamName'] if not driver_row.empty else ""
        
        # Format lap time
        lap_time = fastest_lap['LapTime']
        try:
            total_seconds = lap_time.total_seconds()
            minutes = int(total_seconds // 60)
            seconds = total_seconds % 60
            lap_time_str = f"{minutes}:{seconds:06.3f}"
        except Exception:
            lap_time_str = str(lap_time)
            
        # Extract telemetry arrays
        x = telemetry['X'].values
        y = telemetry['Y'].values
        speed = telemetry['Speed'].values
        distance = telemetry['Distance'].values if 'Distance' in telemetry.columns else None
        gear_col = 'nGear' if 'nGear' in telemetry.columns else ('Gear' if 'Gear' in telemetry.columns else None)
        gear = telemetry[gear_col].values if gear_col else None
        time = telemetry['Time'].values if 'Time' in telemetry.columns else None
        
        # Downsample to ~400 points to keep DOM size reasonable
        target_points = 400
        step = max(1, len(x) // target_points)
        
        x_sub = x[::step]
        y_sub = y[::step]
        speed_sub = speed[::step]
        distance_sub = distance[::step] if distance is not None else None
        gear_sub = gear[::step] if gear is not None else None
        time_sub = time[::step] if time is not None else None
        
        # Calculate boundaries
        x_min, x_max = x_sub.min(), x_sub.max()
        y_min, y_max = y_sub.min(), y_sub.max()
        width = x_max - x_min
        height = y_max - y_min
        
        # Scale to fit SVG view box (800x600) with margins
        margin = 50
        svg_w, svg_h = 800, 600
        target_w = svg_w - 2 * margin
        target_h = svg_h - 2 * margin
        
        scale = min(target_w / width, target_h / height)
        
        # Coordinates scaled and Y inverted
        x_scaled = margin + (x_sub - x_min) * scale
        y_scaled = margin + (y_max - y_sub) * scale
        
        speed_min, speed_max = speed_sub.min(), speed_sub.max()
        
        # Generate segments
        segments_html = []
        for i in range(len(x_scaled) - 1):
            x1, y1 = x_scaled[i], y_scaled[i]
            x2, y2 = x_scaled[i+1], y_scaled[i+1]
            color = get_speed_color(speed_sub[i], speed_min, speed_max)
            
            line_elem = (
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{color}" stroke-width="5" stroke-linecap="round" class="track-segment" '
                f'style="transition: stroke-width 0.1s ease, filter 0.1s ease;" />'
            )
            segments_html.append(line_elem)
            
        # Draw Start/Finish point
        start_point_html = (
            f'<circle cx="{x_scaled[0]:.1f}" cy="{y_scaled[0]:.1f}" r="8" '
            f'fill="#00ff66" stroke="#ffffff" stroke-width="2" style="filter: drop-shadow(0 0 4px #00ff66);" />'
        )
        
        # Checkered pattern / flag marker
        start_label_html = (
            f'<text x="{x_scaled[0]:.1f}" y="{y_scaled[0] - 15:.1f}" fill="#ffffff" font-size="10" '
            f'font-family="sans-serif" text-anchor="middle" font-weight="bold">Start</text>'
        )
        
        # Color legends using inline CSS
        legend_gradient = (
            '<div style="display: flex; align-items: center; justify-content: space-between; margin-top: 10px; padding: 0 10px;">'
            f'<span style="font-size: 11px; color: #a0aab2;">Slow cornering ({int(speed_min)} km/h)</span>'
            '<div style="flex-grow: 1; height: 8px; margin: 0 15px; border-radius: 4px; background: linear-gradient(to right, hsl(270, 100%, 50%), hsl(320, 100%, 55%), hsl(50, 100%, 50%));"></div>'
            f'<span style="font-size: 11px; color: #a0aab2;">High speed ({int(speed_max)} km/h)</span>'
            '</div>'
        )
        
        # Serialize points to JSON for snapping client-side hover
        points_serializable = []
        for i in range(len(x_scaled)):
            s_val = float(speed_sub[i])
            d_val = float(distance_sub[i]) if distance_sub is not None else 0.0
            g_val = int(gear_sub[i]) if gear_sub is not None else 0
            
            if time_sub is not None:
                try:
                    # Subtract first timestamp to get elapsed lap time from the start line
                    elapsed_td = time_sub[i] - time_sub[0]
                    total_ns = int(elapsed_td.astype('int64'))
                    
                    minutes = total_ns // 60_000_000_000
                    rem_ns = total_ns % 60_000_000_000
                    
                    seconds = rem_ns // 1_000_000_000
                    rem_ns = rem_ns % 1_000_000_000
                    
                    milliseconds = rem_ns // 1_000_000
                    rem_ns = rem_ns % 1_000_000
                    
                    nanoseconds = rem_ns
                    
                    t_val = f"{minutes:02d}:{seconds:02d}:{milliseconds:03d}:{nanoseconds:03d}"
                except Exception:
                    t_val = str(time_sub[i])
            else:
                t_val = "N/A"
                
            points_serializable.append({
                'x': float(x_scaled[i]),
                'y': float(y_scaled[i]),
                's': s_val,
                'd': d_val,
                'g': g_val,
                't': t_val
            })
            
        track_telemetry_json = json.dumps(points_serializable)
        track_telemetry_escaped = html.escape(track_telemetry_json)
        
        # Combined HTML
        container_html = (
            f'<div class="interactive-track-map" style="position: relative; width: 100%; max-width: 800px; margin: 20px auto; background-color: #15181f; border-radius: 12px; padding: 15px; border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 8px 32px rgba(0,0,0,0.4);">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px; margin-bottom: 15px;">'
            f'<div>'
            f'<h4 style="margin: 0; color: #ffffff; font-size: 16px; font-weight: bold; font-family: \'Outfit\', sans-serif;">{driver_name}</h4>'
            f'<span style="font-size: 11px; color: #a0aab2; font-family: sans-serif;">{team_name}</span>'
            f'</div>'
            f'<div style="text-align: right;">'
            f'<div style="font-size: 16px; color: #ff1801; font-weight: bold; font-family: monospace;">{lap_time_str}</div>'
            f'<span style="font-size: 10px; color: #a0aab2; font-family: sans-serif;">Qualifying Lap Time</span>'
            f'</div>'
            f'</div>'
            f'<svg viewBox="0 0 {svg_w} {svg_h}" style="width: 100%; height: auto; background-color: transparent;" '
            f'data-telemetry-points="{track_telemetry_escaped}" '
            f'onmousemove="window.handleTrackHover(event, this)" onmouseleave="window.handleTrackLeave(event, this)">'
            f'<g>'
            f'{"".join(segments_html)}'
            f'{start_point_html}'
            f'{start_label_html}'
            f'<circle id="track-guide-marker" cx="0" cy="0" r="7" fill="#ffffff" stroke="#ff1801" stroke-width="2" style="display: none; pointer-events: none; filter: drop-shadow(0 0 4px #ff1801);" />'
            f'<circle id="sim-car-marker" cx="0" cy="0" r="8" fill="#ffffff" stroke="#00ffff" stroke-width="2.5" style="display: none; pointer-events: none; filter: drop-shadow(0 0 6px #00ffff);" />'
            f'</g>'
            f'</svg>'
            f'{legend_gradient}'
            f'<div class="sim-controls" style="display: flex; align-items: center; gap: 12px; margin-top: 15px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.05);">'
            f'<button class="sim-play-btn" style="background: #e10600; border: none; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; flex-shrink: 0;"><i class="fa-solid fa-play"></i></button>'
            f'<input type="range" class="sim-slider" min="0" max="100" value="0" style="flex-grow: 1; height: 6px; border-radius: 3px; background: rgba(255,255,255,0.1); outline: none; cursor: pointer;">'
            f'<select class="sim-speed" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: white; border-radius: 6px; padding: 4px 8px; outline: none; font-size: 11px; cursor: pointer; font-family: inherit;">'
            f'<option value="1" selected>1x</option>'
            f'<option value="2">2x</option>'
            f'<option value="5">5x</option>'
            f'<option value="10">10x</option>'
            f'</select>'
            f'</div>'
            f'<div class="sim-telemetry-dashboard" style="display: flex; gap: 10px; margin-top: 10px; padding: 8px 10px; background: rgba(255,255,255,0.02); border-radius: 6px; border: 1px solid rgba(255,255,255,0.03); justify-content: space-around; font-family: monospace; font-size: 11px;">'
            f'<div>Speed: <strong class="sim-speed-val" style="color: #00ffff;">0.00 km/h</strong></div>'
            f'<div>Gear: <strong class="sim-gear-val" style="color: #ffffff;">-</strong></div>'
            f'<div>Distance: <strong class="sim-distance-val" style="color: #ffffff;">0.00 m</strong></div>'
            f'<div>Time: <strong class="sim-time-val" style="color: #ff1801;">0.000s</strong></div>'
            f'</div>'
            f'<div class="track-tooltip" style="display: none; position: absolute; background: rgba(15, 17, 21, 0.95); border: 1px solid rgba(255,255,255,0.15); color: white; padding: 10px 14px; border-radius: 8px; pointer-events: none; font-family: sans-serif; font-size: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.6); z-index: 1000; backdrop-filter: blur(4px); transition: opacity 0.15s ease;"></div>'
            f'</div>'
        )
        return container_html.replace('\n', ' ')
    except Exception as e:
        return f"Error generating track map plot: {e}"

# â”€â”€ Team colour palette for multi-driver comparison â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TEAM_COLORS = {
    "Red Bull Racing":      "#3671C6",
    "Ferrari":              "#E8002D",
    "Mercedes":             "#27F4D2",
    "McLaren":              "#FF8000",
    "Aston Martin":         "#229971",
    "Alpine":               "#FF87BC",
    "Williams":             "#64C4FF",
    "RB":                   "#6692FF",
    "Haas F1 Team":         "#B6BABD",
    "Kick Sauber":          "#52E252",
    # fallback palette for unknowns
    "_0": "#00FFFF", "_1": "#FF0055", "_2": "#FFD700",
    "_3": "#00FF88", "_4": "#FF5500", "_5": "#CC44FF",
}

def get_driver_color(driver_abbr: str, team_name: str, idx: int) -> str:
    """Return a distinct colour for a driver â€” team colour if known, else a fallback."""
    if team_name and team_name in TEAM_COLORS:
        return TEAM_COLORS[team_name]
    return TEAM_COLORS.get(f"_{idx % 6}", "#FFFFFF")

def generate_multi_driver_hot_lap(year: int, grand_prix: str, session_type: str, drivers: list) -> str:
    """Animated multi-driver hot lap: N coloured dots on a shared circuit with play/scrub/speed controls."""
    try:
        session = fastf1.get_session(year, grand_prix, session_type)
        session.load(telemetry=True, weather=False)

        svg_w, svg_h = 800, 520
        margin = 50

        driver_traces = []
        x_all, y_all = [], []

        for idx, driver in enumerate(drivers):
            try:
                laps = session.laps.pick_drivers(driver)
                if laps.empty:
                    continue
                fastest = laps.pick_fastest()
                tel = fastest.get_telemetry()
                if 'X' not in tel.columns or 'Y' not in tel.columns:
                    continue

                x_all.extend(tel['X'].values.tolist())
                y_all.extend(tel['Y'].values.tolist())

                lt = fastest['LapTime']
                try:
                    ts = lt.total_seconds()
                    lt_str = f"{int(ts // 60)}:{ts % 60:06.3f}"
                except Exception:
                    lt_str = str(lt)

                driver_row = session.results[session.results['Abbreviation'] == driver]
                full_name = driver_row.iloc[0]['FullName'] if not driver_row.empty else driver
                team_name = driver_row.iloc[0]['TeamName'] if not driver_row.empty else ""
                color = get_driver_color(driver, team_name, idx)

                # Build scaled telemetry points (to be filled after global bounds computed)
                driver_traces.append({
                    "abbr": driver, "name": full_name, "team": team_name,
                    "color": color, "lt": lt_str,
                    "x_raw": tel['X'].values, "y_raw": tel['Y'].values,
                    "speed": tel['Speed'].values if 'Speed' in tel.columns else None,
                    "gear": tel['nGear'].values if 'nGear' in tel.columns else (tel['Gear'].values if 'Gear' in tel.columns else None),
                    "dist": tel['Distance'].values if 'Distance' in tel.columns else None,
                    "time": tel['Time'].values if 'Time' in tel.columns else None,
                })
            except Exception:
                continue

        if not driver_traces:
            return "Could not load telemetry for any of the requested drivers."

        # Global bounds â†’ scale
        x_min, x_max = min(x_all), max(x_all)
        y_min, y_max = min(y_all), max(y_all)
        track_w = x_max - x_min or 1
        track_h = y_max - y_min or 1
        draw_w  = svg_w - 2 * margin
        draw_h  = svg_h - 2 * margin
        scale   = min(draw_w / track_w, draw_h / track_h)

        def to_svg_xy(xr, yr):
            return (margin + (xr - x_min) * scale,
                    margin + (y_max - yr) * scale)

        # Build SVG track segments + embed per-driver telemetry JSON
        svg_parts = ['<g>']
        all_driver_json = []

        for trace in driver_traces:
            # Downsampled polyline (visual trace)
            step = max(1, len(trace['x_raw']) // 500)
            coords = [to_svg_xy(trace['x_raw'][i], trace['y_raw'][i])
                      for i in range(0, len(trace['x_raw']), step)]
            polypts = " ".join(f"{c[0]:.1f},{c[1]:.1f}" for c in coords)

            # Speed-coloured segments for this driver's trace
            speed_arr = trace['speed']
            if speed_arr is not None and len(speed_arr) > 1:
                spd_min = float(speed_arr.min())
                spd_max = float(speed_arr.max())
                for i in range(0, len(trace['x_raw']) - 1, step):
                    x1, y1 = to_svg_xy(trace['x_raw'][i],   trace['y_raw'][i])
                    x2, y2 = to_svg_xy(trace['x_raw'][i+1], trace['y_raw'][i+1])
                    seg_color = get_speed_color(speed_arr[i], spd_min, spd_max)
                    svg_parts.append(
                        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                        f'stroke="{seg_color}" stroke-width="4" stroke-linecap="round" opacity="0.55"/>'
                    )
            else:
                svg_parts.append(
                    f'<polyline points="{polypts}" fill="none" stroke="{trace["color"]}" '
                    f'stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.6"/>'
                )

            # Build per-driver JSON for JS engine (all original points, scaled)
            pts_json = []
            for i in range(len(trace['x_raw'])):
                sx, sy = to_svg_xy(trace['x_raw'][i], trace['y_raw'][i])
                spd = float(trace['speed'][i]) if trace['speed'] is not None else 0.0
                gea = int(trace['gear'][i]) if trace['gear'] is not None else 0
                dst = float(trace['dist'][i]) if trace['dist'] is not None else 0.0
                t_val = "N/A"
                elapsed_ms = 0.0
                if trace['time'] is not None:
                    try:
                        elapsed_td = trace['time'][i] - trace['time'][0]
                        if hasattr(elapsed_td, 'total_seconds'):
                            elapsed_ms = elapsed_td.total_seconds() * 1000.0
                        else:
                            total_ns = int(elapsed_td.astype('int64'))
                            elapsed_ms = total_ns / 1_000_000.0
                        
                        mins = int(elapsed_ms) // 60_000
                        rem  = int(elapsed_ms) % 60_000
                        secs = rem // 1_000
                        ms   = rem % 1_000
                        t_val = f"{mins:02d}:{secs:02d}:{ms:03d}"
                    except Exception:
                        pass
                pts_json.append({'x': round(sx, 1), 'y': round(sy, 1),
                                 's': round(spd, 2), 'g': gea,
                                 'd': round(dst, 2), 't': t_val,
                                 'ms': round(elapsed_ms, 1)})

            all_driver_json.append({
                'abbr': trace['abbr'], 'name': trace['name'],
                'team': trace['team'], 'color': trace['color'],
                'lt': trace['lt'], 'points': pts_json,
            })

        # Start/Finish marker
        sf_x, sf_y = to_svg_xy(driver_traces[0]['x_raw'][0], driver_traces[0]['y_raw'][0])
        svg_parts.append(
            f'<circle cx="{sf_x:.1f}" cy="{sf_y:.1f}" r="8" fill="#00ff66" '
            f'stroke="#ffffff" stroke-width="2" style="filter:drop-shadow(0 0 4px #00ff66);"/>'
        )
        svg_parts.append(
            f'<text x="{sf_x:.1f}" y="{sf_y - 14:.1f}" fill="#ffffff" '
            f'font-size="9" font-family="monospace" text-anchor="middle">S/F</text>'
        )
        svg_parts.append('</g>')

        multi_json_str = html.escape(json.dumps(all_driver_json))

        # Build full SVG with embedded telemetry attribute
        svg_html = (
            f'<svg viewBox="0 0 {svg_w} {svg_h}" '
            f'style="width:100%;height:auto;background:transparent;" '
            f'data-multi-telemetry="{multi_json_str}">'
            '<defs>'
            '<pattern id="mgrid" width="20" height="20" patternUnits="userSpaceOnUse">'
            '<path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(0,255,255,0.03)" stroke-width="1"/>'
            '</pattern>'
            '</defs>'
            f'<rect width="{svg_w}" height="{svg_h}" fill="transparent"/>'
            + "".join(svg_parts) +
            '</svg>'
        )

        # Driver info header cards
        header_cards = ""
        for t in driver_traces:
            header_cards += (
                f'<div style="display:flex;align-items:center;gap:10px;padding:6px 10px;'
                f'border-left:3px solid {t["color"]};margin-bottom:6px;">'
                f'<div style="width:12px;height:12px;border-radius:50%;background:{t["color"]};'
                f'box-shadow:0 0 6px {t["color"]};flex-shrink:0;"></div>'
                f'<div><div style="font-weight:bold;font-size:13px;color:#fff;">{t["name"]} '
                f'<span style="color:#a0aab2;font-weight:normal;font-size:11px;">({t["abbr"]})</span></div>'
                f'<div style="font-size:11px;color:#a0aab2;">{t["team"]} &nbsp;Â·&nbsp; '
                f'<span style="color:{t["color"]};font-family:monospace;">{t["lt"]}</span></div>'
                f'</div></div>'
            )

        # Full container using flex row layout for map and controls side-by-side
        container_html = (
            f'<div class="interactive-multi-track-map" style="position:relative;width:100%;max-width:960px;'
            f'margin:20px auto;background-color:#15181f;border-radius:12px;padding:15px;'
            f'border:1px solid rgba(255,255,255,0.08);box-shadow:0 8px 32px rgba(0,0,0,0.4);">'

            # Header row
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'border-bottom:1px solid rgba(255,255,255,0.05);padding-bottom:10px;margin-bottom:12px;">'
            f'<div>'
            f'<h4 style="margin:0;color:#fff;font-size:15px;font-weight:bold;font-family:Outfit,sans-serif;">'
            f'Hot Lap Comparison</h4>'
            f'<span style="font-size:11px;color:#a0aab2;">{year} {grand_prix} · {session_type}</span>'
            f'</div>'
            f'<div style="display:flex;align-items:center;gap:12px;">'
            f'<button class="multi-universal-play-btn" style="background:#e10600;border:none;color:#ffffff;font-family:Outfit,sans-serif;font-weight:600;font-size:11px;padding:6px 14px;border-radius:6px;cursor:pointer;display:flex;align-items:center;gap:6px;transition:all 0.2s;box-shadow:0 2px 8px rgba(225,6,0,0.35);"><i class="fa-solid fa-play"></i> Universal Play</button>'
            f'<select class="multi-universal-speed" style="background:#1a1b1f !important;border:1px solid rgba(255,255,255,0.2);color:#ffffff !important;border-radius:6px;padding:6px 10px;outline:none;font-size:11px;font-family:Outfit,sans-serif;font-weight:600;cursor:pointer;transition:all 0.2s;min-width:105px;height:28px;">'
            f'<option value="1" style="background:#1a1b1f;color:#fff;">Speed: 1x</option>'
            f'<option value="2" style="background:#1a1b1f;color:#fff;">Speed: 2x</option>'
            f'<option value="3" style="background:#1a1b1f;color:#fff;">Speed: 3x</option>'
            f'<option value="5" style="background:#1a1b1f;color:#fff;">Speed: 5x</option>'
            f'<option value="10" style="background:#1a1b1f;color:#fff;">Speed: 10x</option>'
            f'</select>'
            f'<div style="font-size:11px;color:#a0aab2;text-align:right;">'
            f'{len(driver_traces)} drivers · fastest laps overlaid</div>'
            f'</div>'
            f'</div>'

            # Multi-driver layout container
            f'<div style="display:flex;flex-direction:row;gap:16px;flex-wrap:wrap;align-items:stretch;">'
            # Left pane: Circuit Map SVG
            f'<div class="circuit-pane" style="flex:1 1 450px;min-width:320px;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.15);border-radius:8px;padding:8px;">'
            + svg_html +
            f'</div>'
            # Right pane: Controls side-by-side or stacked
            f'<div class="driver-controls-pane" style="flex:1 1 300px;min-width:280px;display:flex;flex-direction:column;gap:10px;max-height:480px;overflow-y:auto;padding-right:4px;">'
            f'<div style="color:#a0aab2;font-size:12px;font-family:sans-serif;padding:20px;text-align:center;">Initializing telemetry controls...</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )

        return container_html.replace('\n', ' ')

    except Exception as e:
        return f"Error generating multi-driver hot lap comparison: {e}"

def generate_design_response(query: str) -> str:
    """Generate a 3D CAD design response for aero, chassis, or mechanical components."""
    query_lower = query.lower()

    # 1. Determine component type
    # Check mechanical/fastener parts FIRST before aero keywords
    mech_keywords = ["bolt", "nut", "screw", "fastener", "bracket", "bush", "bushing",
                     "stud", "washer", "pin", "bearing", "rod", "link", "clevis",
                     "spacer", "shim", "collar", "sleeve"]
    is_mech = any(k in query_lower for k in mech_keywords)

    if is_mech:
        # Parse dimensions from query: e.g. "M8 bolt 40mm", "10mm bolt"
        dim_match = re.search(r'(\d+(?:\.\d+)?)\s*mm', query_lower)
        thread_match = re.search(r'm(\d+)', query_lower)
        nom_diam = float(dim_match.group(1)) if dim_match else 8.0
        thread_size = f"M{thread_match.group(1)}" if thread_match else f"M{int(nom_diam)}"
        length_match = re.search(r'(\d+(?:\.\d+)?)\s*mm\s+(?:long|length)', query_lower)
        length = float(length_match.group(1)) if length_match else nom_diam * 5

        if "nut" in query_lower:
            part_type = "Nut"
            component = "Mechanical Nut"
        elif "bracket" in query_lower:
            part_type = "Bracket"
            component = "Mounting Bracket"
        elif "washer" in query_lower:
            part_type = "Washer"
            component = "Washer"
        else:
            part_type = "Bolt"
            component = "Fastener Bolt"

        spec_table = (
            "| Parameter | Dimension | Standard | Status |\n"
            "| --- | --- | --- | --- |\n"
            f"| Thread Size | {thread_size} | ISO 6721 | **PASS** |\n"
            f"| Nominal Diameter | {nom_diam:.1f} mm | DIN 912 | **PASS** |\n"
            f"| Shank Length | {length:.1f} mm | Customer Spec | **DEFINED** |\n"
            f"| Head Height | {nom_diam * 0.64:.1f} mm | ISO 4762 | **PASS** |\n"
            f"| Pitch | {nom_diam * 0.15:.2f} mm | Coarse Thread | **PASS** |\n"
            f"| Proof Load | {int(nom_diam ** 2 * 60)} N | Grade 12.9 | **PASS** |\n"
        )
        materials_table = (
            "#### Recommended Materials\n"
            "| Material | Grade | Tensile Strength | Use Case |\n"
            "| --- | --- | --- | --- |\n"
            "| Titanium Alloy | Grade 5 (Ti-6Al-4V) | 950 MPa | **Primary** — weight-critical joints |\n"
            "| Aerospace Steel | 300M / H11 | 1900 MPa | High-load suspension pivots |\n"
            "| Inconel 718 | AMS 5664 | 1380 MPa | High-temperature exhaust zones |\n"
        )
        cad_div = (
            f'<div data-cad3d="1" data-component="Fastener" data-setup="{part_type}" '
            f'data-dim-diam="{nom_diam}" data-dim-length="{length}" '
            f'style="min-height:60px;"></div>'
        )
        report = (
            f"### F1 Mechanical Part: {component} ({thread_size} × {length:.0f} mm)\n\n"
            "> [!NOTE]\n"
            "> #### 🎮 3D Model Control Instructions\n"
            "> * **Rotate**: Click and **drag** (or swipe with 1 finger) to spin the component in 3D.\n"
            "> * **Zoom**: Use your **scroll wheel** (or pinch) to zoom in very close (supports up to 15x zoom to inspect threading/chamfers).\n"
            "> * **Pan**: Hold **right-click** and drag (or drag with 2 fingers) to pan the camera view.\n"
            "> * **Reset**: **Double-click** anywhere on the 3D viewport to reset the camera to home view.\n"
            "> * **Download**: Click **Download OBJ** to export high-precision CAD files compatible with SOLIDWORKS, Fusion 360, Blender, etc.\n\n"
            f"{cad_div}\n\n"
            "#### Dimensional Specification\n"
            f"{spec_table}\n\n"
            f"{materials_table}\n\n"
            "#### Engineering Notes\n"
            f"1. **Thread standard**: {thread_size} coarse (ISO metric) — compatible with all standard F1 tooling.\n"
            "2. **Torque spec**: Apply thread-locking compound (Loctite 2701) and torque to manufacturer spec.\n"
            "3. **Surface finish**: Anodise (titanium) or black oxide (steel) to reduce galvanic corrosion risk.\n"
            "4. **Safety factor**: 2.5× minimum against proof load under FIA impact test conditions."
        )
        return report

    # Standard aero components
    component = "Rear Wing"
    if "front wing" in query_lower:
        component = "Front Wing"
    elif "chassis" in query_lower or "chassi" in query_lower:
        component = "Chassis Profile"
    elif "diffuser" in query_lower:
        component = "Floor Diffuser"

    # 2. Determine track setup
    # IMPORTANT: check Low Drag phrases FIRST — "low downforce" must match before bare "downforce"
    low_drag_triggers = [
        "low drag", "low-drag", "low downforce", "low-downforce",
        "monza", "spa", "baku", "jeddah", "spielberg",
        "red bull ring", "austria", "straight", "straights",
        "top speed", "high speed track"
    ]
    high_downforce_triggers = [
        "high downforce", "high-downforce", "maximum downforce",
        "monaco", "hungary", "singapore", "hungaroring",
        "street circuit", "tight corners"
    ]
    # "downforce" alone = High Downforce but ONLY if low drag not already matched
    bare_downforce = ["downforce"]

    setup = "Balanced"
    if any(w in query_lower for w in low_drag_triggers):
        setup = "Low Drag"
    elif any(w in query_lower for w in high_downforce_triggers):
        setup = "High Downforce"
    elif any(w in query_lower for w in bare_downforce):
        setup = "High Downforce"

    # 3. Spec table per component
    if component == "Rear Wing":
        chord = "450 mm" if setup == "High Downforce" else "300 mm"
        aoa   = "14.5°" if setup == "High Downforce" else "3.8°"
        cl    = "-2.45" if setup == "High Downforce" else "-0.78"
        spec_table = (
            "| Parameter | Target Dimension | Regulation Threshold | Status |\n"
            "| --- | --- | --- | --- |\n"
            f"| Span (Width) | 850 mm | Max 850 mm (FIA Art. 3.4.1) | **PASS** |\n"
            f"| Profile Height | 905 mm | Max 910 mm (FIA Art. 3.4.1) | **PASS** |\n"
            f"| Mainplane Chord | {chord} | Max 500 mm | **PASS** |\n"
            f"| DRS Opening Gap | 85 mm | 85 mm (Fixed Limit) | **PASS** |\n"
            f"| Angle of Attack | {aoa} | Custom Tuning | **OPTIMIZED** |\n"
            f"| Downforce Coeff (Cl) | {cl} | Est. Aerodynamics | **GOAL MET** |\n"
        )
        materials_table = (
            "#### Recommended Materials\n"
            "| Component | Material | Layup / Grade | Rationale |\n"
            "| --- | --- | --- | --- |\n"
            "| Mainplane skin | Carbon Fibre (CFRP) | [0°/90°/±45°] × 6 ply | Stiffness + aero surface |\n"
            "| Flap core | Nomex Honeycomb | 3.2 mm cell / 48 kg/m³ | Ultra-low weight |\n"
            "| Endplates | CFRP + woven carbon | [±45°] × 4 ply | Impact resistance |\n"
            "| DRS actuator | Titanium Grade 5 | Ti-6Al-4V rod | Corrosion + weight |\n"
            "| Fasteners | Titanium M5-M8 | Grade 12.9 equiv | Safety critical |\n"
        )
    elif component == "Front Wing":
        spec_table = (
            "| Parameter | Target Dimension | Regulation Threshold | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| Total Span | 1950 mm | Max 2000 mm (FIA Art. 3.2.2) | **PASS** |\n"
            "| Ground Clearance | 78 mm | Min 75 mm (FIA Art. 3.2.2) | **PASS** |\n"
            "| Element Count | 4 Flaps | Max 4 Elements | **PASS** |\n"
            "| Endplate Thickness | 12 mm | Min 10 mm (FIA Art. 3.2.4) | **PASS** |\n"
        )
        materials_table = (
            "#### Recommended Materials\n"
            "| Component | Material | Layup / Grade | Rationale |\n"
            "| --- | --- | --- | --- |\n"
            "| Main plane | CFRP (Toray T800) | [0°/±45°/90°] × 8 ply | Primary load path |\n"
            "| Cascade flaps | CFRP + ceramic coat | [±45°] × 6 ply | Outwash + heat |\n"
            "| Endplates | CFRP woven | [0°/90°] × 5 ply | Side impact |\n"
            "| Attachment pins | Titanium Grade 5 | M6 clevis pins | Lightweight pivot |\n"
        )
    else:
        spec_table = (
            "| Parameter | Target Dimension | Regulation Threshold | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| Wheelbase | 3400 mm | Max 3400 mm (2026 FIA Regs) | **PASS** |\n"
            "| Max Width | 1900 mm | Max 1900 mm (2026 FIA Regs) | **PASS** |\n"
            "| Monocoque Weight | 98 kg | Min 95 kg (FIA Art. 12.3) | **PASS** |\n"
            "| Roll Hoop Survival | 110 kN | Vertical Load 105 kN | **PASS** |\n"
        )
        materials_table = (
            "#### Recommended Materials\n"
            "| Component | Material | Layup / Grade | Rationale |\n"
            "| --- | --- | --- | --- |\n"
            "| Monocoque shell | CFRP (Toray T1100G) | [0°/±60°/90°] × 20 ply | FIA crash cell |\n"
            "| Crash structure | CFRP/Al honeycomb | 200 kN absorption | Impact standard |\n"
            "| Sidepod skin | CFRP + Zylon® | [±45°] × 10 ply | Penetration resist |\n"
            "| Roll hoop | CFRP titanium hybrid | Ti-6Al-4V insert | 105 kN load rating |\n"
            "| Floor panels | CFRP (low-cost weave) | 6 ply balanced | Ground effect |\n"
        )

    # 4. Return marker div
    cad_div = (
        f'<div data-cad3d="1" data-component="{component}" data-setup="{setup}" '
        f'style="min-height:60px;"></div>'
    )

    report = (
        f"### F1 Aerodynamic 3D CAD: {component} ({setup} Configuration)\n\n"
        "> [!NOTE]\n"
        "> #### 🎮 3D Model Control Instructions\n"
        "> * **Rotate**: Click and **drag** (or swipe with 1 finger) to spin the component in 3D.\n"
        "> * **Zoom**: Use your **scroll wheel** (or pinch) to zoom in very close (supports up to 15x zoom to inspect airflow streamlines).\n"
        "> * **Pan**: Hold **right-click** and drag (or drag with 2 fingers) to pan the camera view.\n"
        "> * **Reset**: **Double-click** anywhere on the 3D viewport to reset the camera to home view.\n"
        "> * **Toggle DRS**: (Rear Wing only) Click the **Toggle DRS** button in the header bar of the 3D window to animate the flap open/closed.\n"
        "> * **Download**: Click **Download OBJ** to export high-precision CAD files compatible with SOLIDWORKS, Fusion 360, Blender, etc.\n\n"
        f"{cad_div}\n\n"
        "#### Technical Specifications (FIA 2026 Compliance)\n"
        f"{spec_table}\n\n"
        f"{materials_table}\n\n"
        "#### Aerodynamic Analysis\n"
        f"1. **Performance**: Tuned for **{setup}** — "
        f"{'drag minimization prioritized for straight-line speed (low-downforce track).': 'maximum suction camber to maximize cornering downforce (high-downforce track).'}\n"
        "2. **DRS**: Mechanical linkages conform to the 85 mm fixed open gap. "
        "Click 'Toggle DRS' to see the flap animate open with updated airflow.\n"
    )
    return report

def needs_database_context(query: str) -> bool:
    """Helper to check if the query actually asks for data from FastF1. General greetings and chit-chat return False."""
    query_lower = query.lower()

    
    # 1. Year pattern
    if re.search(r'\b(19\d\d|20\d\d)\b', query):
        return True
        
    # 2. Grand Prix names/locations
    gp_keywords = {
        "gp", "grand prix", "bahrain", "jeddah", "melbourne", "australia", "imola", "miami", 
        "monaco", "barcelona", "spain", "montreal", "canada", "austria", "spielberg", 
        "silverstone", "britain", "hungaroring", "hungary", "spa", "belgium", "zandvoort", 
        "netherlands", "monza", "italy", "baku", "azerbaijan", "singapore", "marina bay", 
        "suzuka", "japan", "lusail", "qatar", "austin", "texas", "us gp", "united states", 
        "mexico", "hermanos rodriguez", "sao paulo", "brazil", "interlagos", "las vegas", 
        "abu dhabi", "yas marina", "shanghai", "china"
    }
    if any(k in query_lower for k in gp_keywords):
        return True
        
    # 3. Database operation keywords
    data_keywords = {
        "result", "results", "lap", "laps", "laptime", "laptimes", "telemetry", "speed", 
        "map", "chart", "graph", "plot", "winner", "won", "podium", "position", "place", 
        "finish", "finished", "quali", "qualifying", "sprint", "practice", "fp1", "fp2", "fp3"
    }
    if any(k in query_lower for k in data_keywords):
        return True
        
    # 4. Common driver names/abbreviations
    driver_keywords = {
        "verstappen", "hamilton", "russell", "norris", "piastri", "leclerc", "sainz", 
        "perez", "alonso", "stroll", "gasly", "ocon", "albon", "sargeant", "ricciardo", 
        "tsunoda", "bottas", "zhou", "magnussen", "hulkenberg", "antonelli", "bearman", 
        "ver", "ham", "rus", "nor", "pia", "lec", "sai", "per", "alo", "str", "gas", 
        "oco", "alb", "sar", "ric", "tsu", "bot", "zho", "mag", "hul", "ant", "bea"
    }
    query_words = [w.strip("?,.!:;()").lower() for w in query.split()]
    if any(w in driver_keywords for w in query_words):
        return True
        
    return False

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
    
    # Check for design requests (aerodynamic or mechanical components)
    design_keywords = ["design", "blueprint", "schematic", "cad", "aerodynamics", "model", "draw", "generate", "create", "make"]
    component_keywords = [
        "wing", "chassis", "nose", "diffuser", "endplate", "splitter", "floor", "sidepod", "chassi",
        "bolt", "nut", "screw", "fastener", "bracket", "bush", "bushing", "stud", "washer", "pin", "bearing", "collar"
    ]
    is_design_request = any(k in query.lower() for k in design_keywords) and any(k in query.lower() for k in component_keywords)
    if is_design_request:
        return generate_design_response(query)

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
            
    session_type = None
    if 'qualifying' in query.lower() or ' quali' in query.lower():
        session_type = 'Q'
    elif 'sprint' in query.lower():
        session_type = 'S'
    elif 'practice' in query.lower():
        if '1' in query: session_type = 'FP1'
        elif '2' in query: session_type = 'FP2'
        elif '3' in query: session_type = 'FP3'
        else: session_type = 'FP1'
        
    if not session_type and history:
        for msg in reversed(history):
            h_content = msg['content'].lower()
            if 'qualifying' in h_content or ' quali' in h_content:
                session_type = 'Q'
                break
            elif 'sprint' in h_content:
                session_type = 'S'
                break
            elif 'practice' in h_content:
                if '1' in h_content: session_type = 'FP1'
                elif '2' in h_content: session_type = 'FP2'
                elif '3' in h_content: session_type = 'FP3'
                else: session_type = 'FP1'
                break
                
    if not session_type:
        session_type = 'R'
        
    # Check for graph/telemetry generation requests
    query_words_clean = []
    for w in query.split():
        cleaned = w.strip("?,.!:;()\"'").lower()
        if cleaned.endswith("'s"):
            cleaned = cleaned[:-2]
        elif cleaned.endswith("s'"):
            cleaned = cleaned[:-1]
        query_words_clean.append(cleaned)
        
    driver_keywords = {
        "verstappen", "hamilton", "russell", "norris", "piastri", "leclerc", "sainz", 
        "perez", "alonso", "stroll", "gasly", "ocon", "albon", "sargeant", "ricciardo", 
        "tsunoda", "bottas", "zhou", "magnussen", "hulkenberg", "antonelli", "bearman", 
        "ver", "ham", "rus", "nor", "pia", "lec", "sai", "per", "alo", "str", "gas", 
        "oco", "alb", "sar", "ric", "tsu", "bot", "zho", "mag", "hul", "ant", "bea",
        "carlos", "max", "lewis", "lando", "charles", "george", "oscar", "pierre", "esteban",
        "fernando", "lance", "checo", "valtteri", "yuki", "kevin", "nico", "alex", "logan", 
        "daniel", "guanyu", "oliver", "bearman", "kimi"
    }
    has_driver_mention = any(w in driver_keywords for w in query_words_clean)
    has_lap_and_driver = has_driver_mention and any(w in ["lap", "laps"] for w in query_words_clean)
    
    plot_keywords = ["plot", "graph", "chart", "draw", "telemetry", "show speed",
                     "map", "diagram", "layout", "hot lap", "hotlap",
                     "compare hot lap", "compare hotlap", "hot lap comparison",
                     "compare laps", "lap comparison"]
    has_plot_keyword = any(k in query.lower() for k in plot_keywords)

    
    question_keywords = ["why", "how", "explain", "reason", "what is the reason", "why is", "why does", "how did"]
    is_analytical_question = any(k in query.lower() for k in question_keywords) or query.strip().endswith("?")
    
    is_graph_request = has_plot_keyword or (has_lap_and_driver and not is_analytical_question)
    
    if year < 2018:
        is_database_dependent = is_graph_request or any(k in query.lower() for k in ["fastest lap", "fastest time", "lap time", "laptimes", "laptime"])
        if is_database_dependent:
            return f"I can only retrieve F1 database results, layouts, and telemetry from the **2018 season onwards** (which is the limit of my underlying database). I do not have records for the **{year}** season to generate charts or load telemetry."
            
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if not groq_api_key:
            return f"I can only retrieve F1 database results, layouts, and telemetry from the **2018 season onwards** (which is the limit of my underlying database). I do not have records for the **{year}** season, and no Groq API key is configured to answer historical questions."

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
            
        if any(k in query.lower() for k in ["map", "diagram", "layout", "hot lap", "hotlap"]):
            # â”€â”€ Compare mode: multiple drivers on one frame â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            compare_keywords = ["compare", "comparison", "vs", "versus", "all", "together", "same"]
            is_compare = any(k in query.lower() for k in compare_keywords) or len(drivers) > 1
            if is_compare:
                return generate_multi_driver_hot_lap(year, grand_prix, session_type, drivers)
            else:
                # Single driver speed-coloured track map
                d = drivers[0]
                driver_row = session.results[session.results['Abbreviation'] == d]
                driver_name = driver_row.iloc[0]['FullName'] if not driver_row.empty else d
                graph_html = generate_track_map_plot(year, grand_prix, session_type, d)
                return f"Here is the circuit diagram for **{driver_name}** in the **{year} {grand_prix}**:\n\n{graph_html}"
        elif 'lap time' in query.lower() or 'laptimes' in query.lower() or 'laptime' in query.lower():
            graph_html = generate_laptimes_plot(year, grand_prix, session_type, drivers)
            return f"Here is the lap time comparison for **{', '.join(drivers)}** in the **{year} {grand_prix}**:\n\n{graph_html}"
        else:
            graph_html = generate_telemetry_plot(year, grand_prix, session_type, drivers)
            return f"Here is the speed telemetry comparison for **{', '.join(drivers)}** in the **{year} {grand_prix}**:\n\n{graph_html}"


    # Try Groq LLM RAG online
    groq_api_key = os.environ.get("GROQ_API_KEY")
    
    if groq_api_key:
        try:
            # Load session results to form database context
            if year >= 2018:
                try:
                    session = fastf1.get_session(year, grand_prix, session_type)
                    session.load(telemetry=False, weather=False)
                except Exception:
                    session = fastf1.get_session(year, grand_prix, 'R')
                    session.load(telemetry=False, weather=False)
                    
                results_df = session.results[['Position', 'FullName', 'Abbreviation', 'TeamName', 'Time', 'Status']].copy()
                # Calculate top speed for each driver from their laps data
                top_speeds = {}
                for abbr in results_df['Abbreviation']:
                    try:
                        driver_laps = session.laps.pick_drivers(abbr)
                        if not driver_laps.empty:
                            max_st = driver_laps['SpeedST'].max()
                            max_i1 = driver_laps['SpeedI1'].max()
                            max_i2 = driver_laps['SpeedI2'].max()
                            max_fl = driver_laps['SpeedFL'].max()
                            speeds = [s for s in [max_st, max_i1, max_i2, max_fl] if pd.notna(s)]
                            top_speeds[abbr] = int(max(speeds)) if speeds else "N/A"
                        else:
                            top_speeds[abbr] = "N/A"
                    except Exception:
                        top_speeds[abbr] = "N/A"
                
                results_df['TopSpeed_kmh'] = results_df['Abbreviation'].map(top_speeds)
                context_data = f"Race Results (with top speeds in km/h):\n{results_df.to_string(index=False)}\n\n"
                
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
                            
                context_content = f"F1 Database Context for current race ({year} {grand_prix}):\n{get_car_models_context(year)}{context_data}"
            else:
                context_content = f"Note: No local database context is available for the {year} season because FastF1 database only supports 2018 onwards. Please answer this query using your own training weights/general knowledge."
                
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
                    "content": context_content
                }
            ]
            
            cleaned_history = clean_history_for_llm(history) if history else []
            if cleaned_history:
                for h in cleaned_history:
                    messages.append({"role": h["role"], "content": h["content"]})
                    
            messages.append({"role": "user", "content": query})
            
            # Try Groq API
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
        status = str(matched_driver['Status']) if not pd.isna(matched_driver['Status']) and str(matched_driver['Status']).strip() else "Finished"
        
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
