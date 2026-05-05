"""
F1 Race Replay - Data Fetcher
Fetches car position telemetry from a 2025 F1 race using FastF1
and exports it as a JSON file for the C++ visualizer.

Usage:
    pip install fastf1
    python fetch_f1_data.py

Output:
    race_data.json  - position frames + track layout
"""

import fastf1
import json
import numpy as np
import os

RACES={
    1:{"name":"Australian Gp", "round": 1},
    2:{"name": "Chinese GP", "round": 2},
    3:{"name": "Japanese GP", "round": 3},
    4:  {"name": "Bahrain GP", "round": 4},
    5:  {"name": "Saudi Arabian GP","round": 5},
    6:  {"name": "Miami GP", "round": 6},
    7:  {"name": "Emilia Romagna GP", "round": 7},
    8:  {"name": "Monaco GP", "round": 8},
    9:  {"name": "Spanish GP", "round": 9},
    10: {"name": "Canadian GP", "round": 10},
}


TEAM_COLORS = {
    'Mercedes':         '#00D2BE',
    'Red Bull Racing':  '#3671C6',
    'Ferrari':          '#E8002D',
    'McLaren':          '#FF8000',
    'Aston Martin':     '#358C75',
    'Alpine':           '#FF87BC',
    'Williams':         '#64C4FF',
    'RB':               '#6692FF',
    'Kick Sauber':      '#52E252',
    'Haas F1 Team':     '#B6BABD',
}

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]

def normalize_track(x_arr, y_arr, target_width=1200, target_height=700, padding=80):
    """Scale track coordinates to fit within target canvas dimensions."""
    x_min, x_max = x_arr.min(), x_arr.max()
    y_min, y_max = y_arr.min(), y_arr.max()
    scale = min(
        (target_width  - 2 * padding) / (x_max - x_min),
        (target_height - 2 * padding) / (y_max - y_min)
    )
    x_norm = (x_arr - x_min) * scale + padding + (target_width  - 2*padding - (x_max - x_min)*scale) / 2
    y_norm = (y_arr - y_min) * scale + padding + (target_height - 2*padding - (y_max - y_min)*scale) / 2
    # Flip Y axis (screen coords)
    y_norm = target_height - y_norm
    return x_norm, y_norm, x_min, x_max, y_min, y_max, scale

def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    fastf1.Cache.enable_cache(CACHE_DIR)

    print(f"Loading {YEAR} Round {ROUND_NUMBER} ({SESSION_TYPE})...")
    session = fastf1.get_session(YEAR, ROUND_NUMBER, SESSION_TYPE)
    session.load(telemetry=True, laps=True, weather=False, messages=False)

    event_name = session.event['EventName']
    print(f"Loaded: {event_name}")

    # ── Track layout from fastest lap ────────────────────────────────────────
    print("Extracting track layout...")
    fastest = session.laps.pick_fastest()
    tel = fastest.get_telemetry()
    raw_x = tel['X'].values.astype(float)
    raw_y = tel['Y'].values.astype(float)

    # Downsample track points
    step = max(1, len(raw_x) // 500)
    raw_x = raw_x[::step]
    raw_y = raw_y[::step]

    norm_x, norm_y, x_min, x_max, y_min, y_max, scale = normalize_track(raw_x, raw_y)

    track_points = [{"x": round(float(nx), 2), "y": round(float(ny), 2)}
                    for nx, ny in zip(norm_x, norm_y)]

    # ── Driver list ──────────────────────────────────────────────────────────
    drivers = list(session.drivers)[:MAX_DRIVERS]
    driver_info = {}
    for drv in drivers:
        try:
            info = session.get_driver(drv)
            team  = info.get('TeamName', 'Unknown')
            color = TEAM_COLORS.get(team, '#FFFFFF')
            driver_info[drv] = {
                "abbr":       drv,
                "full_name":  f"{info.get('FirstName','')} {info.get('LastName','')}".strip(),
                "team":       team,
                "color_hex":  color,
                "color_rgb":  hex_to_rgb(color),
            }
        except Exception:
            driver_info[drv] = {
                "abbr": drv, "full_name": drv, "team": "Unknown",
                "color_hex": "#FFFFFF", "color_rgb": [255,255,255]
            }

    print(f"Drivers: {list(driver_info.keys())}")

    # ── Position frames ──────────────────────────────────────────────────────
    print("Building position frames (this may take a minute)...")
    frames = []

    # Get all laps, pick one for time reference
    all_laps = session.laps
    ref_laps = all_laps[all_laps['Driver'] == drivers[0]].sort_values('LapStartTime')

    sampled = 0
    total_frames_raw = 0

    for i, (_, lap) in enumerate(ref_laps.iterrows()):
        try:
            lap_tel = lap.get_telemetry()
        except Exception:
            continue

        for idx, row in lap_tel.iterrows():
            total_frames_raw += 1
            if total_frames_raw % SAMPLE_EVERY != 0:
                continue

            frame_time = float(lap['LapStartTime'].total_seconds()) + float(row['Time'].total_seconds())
            frame = {
                "t":      round(frame_time, 2),
                "lap":    int(lap['LapNumber']) if not np.isnan(lap['LapNumber']) else 0,
                "cars":   []
            }

            for drv in drivers:
                try:
                    drv_laps = all_laps[all_laps['Driver'] == drv]
                    # Find which lap this driver is on at this time
                    on_lap = drv_laps[drv_laps['LapStartTime'].dt.total_seconds() <= frame_time]
                    if on_lap.empty:
                        continue
                    cur_lap = on_lap.iloc[-1]
                    drv_tel = cur_lap.get_telemetry()

                    elapsed = frame_time - float(cur_lap['LapStartTime'].total_seconds())
                    elapsed_td = drv_tel['Time'].dt.total_seconds() if hasattr(drv_tel['Time'], 'dt') else drv_tel['Time'].apply(lambda t: t.total_seconds())
                    closest = (elapsed_td - elapsed).abs().idxmin()
                    drv_row = drv_tel.loc[closest]

                    raw_car_x = float(drv_row['X'])
                    raw_car_y = float(drv_row['Y'])

                    # Apply same normalization
                    car_x = (raw_car_x - x_min) * scale + 80 + (1200 - 160 - (x_max - x_min)*scale) / 2
                    car_y = 700 - ((raw_car_y - y_min) * scale + 80 + (700 - 160 - (y_max - y_min)*scale) / 2)

                    frame["cars"].append({
                        "drv":   drv,
                        "x":     round(car_x, 1),
                        "y":     round(car_y, 1),
                        "speed": int(drv_row.get('Speed', 0)) if 'Speed' in drv_row else 0,
                        "gear":  int(drv_row.get('nGear', 0)) if 'nGear' in drv_row else 0,
                    })
                except Exception:
                    pass

            if frame["cars"]:
                frames.append(frame)
                sampled += 1

        if sampled >= 3000:  # Cap at 3000 frames for file size
            print(f"  Capped at {sampled} frames after lap {i+1}")
            break

        print(f"  Lap {i+1}/{len(ref_laps)}: {sampled} frames so far")

    print(f"\nTotal frames exported: {len(frames)}")

    # ── Write JSON ───────────────────────────────────────────────────────────
    output = {
        "event":        event_name,
        "year":         YEAR,
        "round":        ROUND_NUMBER,
        "session":      SESSION_TYPE,
        "canvas_width":  1200,
        "canvas_height": 700,
        "track_points": track_points,
        "drivers":      driver_info,
        "frames":       frames,
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, separators=(',', ':'))

    size_mb = os.path.getsize(OUTPUT_FILE) / 1_000_000
    print(f"\n✅ Saved to {OUTPUT_FILE} ({size_mb:.1f} MB)")
    print(f"   {len(track_points)} track points, {len(frames)} frames, {len(driver_info)} drivers")

if __name__ == "__main__":
    main()