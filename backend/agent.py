import fastf1
import os
import datetime
import re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from fastf1 import plotting
import logging
import unicodedata
import json
import html

# Set up fastf1 cache
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
                    t_val = f"{time_sub[i].total_seconds():.3f}s"
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
            f'</g>'
            f'</svg>'
            f'{legend_gradient}'
            f'<div class="track-tooltip" style="display: none; position: absolute; background: rgba(15, 17, 21, 0.95); border: 1px solid rgba(255,255,255,0.15); color: white; padding: 10px 14px; border-radius: 8px; pointer-events: none; font-family: sans-serif; font-size: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.6); z-index: 1000; backdrop-filter: blur(4px); transition: opacity 0.15s ease;"></div>'
            f'</div>'
        )
        return container_html.replace('\n', ' ')
    except Exception as e:
        return f"Error generating track map plot: {e}"

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
    
    is_graph_request = has_lap_and_driver or any(k in query.lower() for k in ["plot", "telemetry", "graph", "chart", "show speed", "map", "diagram", "layout"])
    
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
            
        if any(k in query.lower() for k in ["map", "diagram", "layout"]):
            track_maps = []
            for d in drivers:
                driver_row = session.results[session.results['Abbreviation'] == d]
                driver_name = driver_row.iloc[0]['FullName'] if not driver_row.empty else d
                
                graph_html = generate_track_map_plot(year, grand_prix, session_type, d)
                track_maps.append(f"#### {driver_name}\n{graph_html}")
            return f"Here is the circuit diagram for **{', '.join(drivers)}** in the **{year} {grand_prix}**:\n\n" + "\n\n".join(track_maps)
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
