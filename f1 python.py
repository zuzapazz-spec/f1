"""
F1 Race Replay - Data Fetcher
Fetches car position telemetry from a 2025 F1 race using FastF1
and exports it as a JSON file for the C++ visualizer.

Usage:
    pip install fastf1
    python fetch_f1_data.py

Output:
    race_data_<NazwaWyscigu>.json  - position frames + track layout
"""

import fastf1
import json
import numpy as np
import os

# ── Kalendarz wyścigów 2025 ────────────────────────────────────────────────────
RACES = {
    1:  {"name": "Australian GP",     "round": 1,  "circuit": "Melbourne",   "sprint": False},
    2:  {"name": "Chinese GP",        "round": 2,  "circuit": "Shanghai",    "sprint": True},
    3:  {"name": "Japanese GP",       "round": 3,  "circuit": "Suzuka",      "sprint": False},
    4:  {"name": "Bahrain GP",        "round": 4,  "circuit": "Sakhir",      "sprint": False},
    5:  {"name": "Saudi Arabian GP",  "round": 5,  "circuit": "Jeddah",      "sprint": False},
    6:  {"name": "Miami GP",          "round": 6,  "circuit": "Miami",       "sprint": True},
    7:  {"name": "Emilia Romagna GP", "round": 7,  "circuit": "Imola",       "sprint": False},
    8:  {"name": "Monaco GP",         "round": 8,  "circuit": "Monaco",      "sprint": False},
    9:  {"name": "Spanish GP",        "round": 9,  "circuit": "Barcelona",   "sprint": False},
    10: {"name": "Canadian GP",       "round": 10, "circuit": "Montreal",    "sprint": False},
    11: {"name": "Austrian GP",       "round": 11, "circuit": "Spielberg",   "sprint": False},
    12: {"name": "British GP",        "round": 12, "circuit": "Silverstone", "sprint": False},
    13: {"name": "Belgian GP",        "round": 13, "circuit": "Spa",         "sprint": True},
    14: {"name": "Hungarian GP",      "round": 14, "circuit": "Budapest",    "sprint": False},
    15: {"name": "Dutch GP",          "round": 15, "circuit": "Zandvoort",   "sprint": False},
    16: {"name": "Italian GP",        "round": 16, "circuit": "Monza",       "sprint": False},
    17: {"name": "Azerbaijan GP",     "round": 17, "circuit": "Baku",        "sprint": False},
    18: {"name": "Singapore GP",      "round": 18, "circuit": "Singapore",   "sprint": False},
    19: {"name": "United States GP",  "round": 19, "circuit": "Austin",      "sprint": True},
    20: {"name": "Mexico City GP",    "round": 20, "circuit": "Mexico City", "sprint": False},
    21: {"name": "São Paulo GP",      "round": 21, "circuit": "São Paulo",   "sprint": True},
    22: {"name": "Las Vegas GP",      "round": 22, "circuit": "Las Vegas",   "sprint": False},
    23: {"name": "Qatar GP",          "round": 23, "circuit": "Lusail",      "sprint": True},
    24: {"name": "Abu Dhabi GP",      "round": 24, "circuit": "Yas Marina",  "sprint": False},
}

# ── Stała konfiguracja ─────────────────────────────────────────────────────────
YEAR        = 2025
SAMPLE_EVERY = 10   # Co który sample telemetrii zachować (wyżej = mniejszy plik)
MAX_DRIVERS  = 20   # Maksymalna liczba kierowców
CACHE_DIR    = ".fastf1_cache"
# ──────────────────────────────────────────────────────────────────────────────

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
    """Skaluje współrzędne toru do rozmiaru canvasu."""
    x_min, x_max = x_arr.min(), x_arr.max()
    y_min, y_max = y_arr.min(), y_arr.max()
    scale = min(
        (target_width  - 2 * padding) / (x_max - x_min),
        (target_height - 2 * padding) / (y_max - y_min)
    )
    x_norm = (x_arr - x_min) * scale + padding + (target_width  - 2*padding - (x_max - x_min)*scale) / 2
    y_norm = (y_arr - y_min) * scale + padding + (target_height - 2*padding - (y_max - y_min)*scale) / 2
    y_norm = target_height - y_norm  # Odwróć oś Y (współrzędne ekranowe)
    return x_norm, y_norm, x_min, x_max, y_min, y_max, scale


def wybierz_wyscig():
    """Interaktywny wybór wyścigu z listy."""
    print("\n" + "="*55)
    print("  F1 2025 – Wybór wyścigu")
    print("="*55)
    for key, race in RACES.items():
        sprint_tag = " [SPRINT]" if race["sprint"] else ""
        print(f"  {key:>2}. {race['name']:<22} ({race['circuit']}){sprint_tag}")
    print("="*55)

    while True:
        try:
            choice = int(input("\nWybierz numer wyścigu (1-24): "))
            if choice in RACES:
                return RACES[choice]
            else:
                print("  ❌ Podaj liczbę od 1 do 24.")
        except ValueError:
            print("  ❌ Nieprawidłowy wybór, spróbuj ponownie.")


def wybierz_sesje(race):
    """Wybór sesji: wyścig główny lub sprint (jeśli dostępny)."""
    print(f"\nDostępne sesje dla {race['name']}:")
    print("  1. Wyścig (Race)")
    if race["sprint"]:
        print("  2. Sprint")

    while True:
        try:
            choice = int(input("Wybierz sesję: "))
            if choice == 1:
                return 'R'
            elif choice == 2 and race["sprint"]:
                return 'S'
            else:
                print("  ❌ Nieprawidłowy wybór.")
        except ValueError:
            print("  ❌ Nieprawidłowy wybór.")


def pobierz_dane(race, session_type):
    """Główna logika pobierania i eksportu danych telemetrycznych."""

    safe_name = race["name"].replace(" ", "_").replace("/", "-")
    session_suffix = "Race" if session_type == 'R' else "Sprint"
    output_file = f"race_data_{safe_name}_{session_suffix}.json"

    # Sprawdź czy plik już istnieje
    if os.path.exists(output_file):
        ans = input(f"\n⚠️  Plik '{output_file}' już istnieje. Nadpisać? (t/n): ")
        if ans.lower() != 't':
            print("Pominięto.")
            return

    os.makedirs(CACHE_DIR, exist_ok=True)
    fastf1.Cache.enable_cache(CACHE_DIR)

    print(f"\nŁadowanie: {YEAR} {race['name']} – sesja '{session_type}'...")
    session = fastf1.get_session(YEAR, race["round"], session_type)
    session.load(telemetry=True, laps=True, weather=False, messages=False)

    event_name = session.event['EventName']
    print(f"Załadowano: {event_name}")

    # ── Layout toru ──────────────────────────────────────────────────────────
    print("Wyodrębniam layout toru...")
    fastest = session.laps.pick_fastest()
    tel = fastest.get_telemetry()
    raw_x = tel['X'].values.astype(float)
    raw_y = tel['Y'].values.astype(float)

    step = max(1, len(raw_x) // 500)
    raw_x = raw_x[::step]
    raw_y = raw_y[::step]

    norm_x, norm_y, x_min, x_max, y_min, y_max, scale = normalize_track(raw_x, raw_y)

    track_points = [{"x": round(float(nx), 2), "y": round(float(ny), 2)}
                    for nx, ny in zip(norm_x, norm_y)]

    # ── Lista kierowców ──────────────────────────────────────────────────────
    drivers = list(session.drivers)[:MAX_DRIVERS]
    driver_info = {}
    for drv in drivers:
        try:
            info  = session.get_driver(drv)
            team  = info.get('TeamName', 'Unknown')
            color = TEAM_COLORS.get(team, '#FFFFFF')
            driver_info[drv] = {
                "abbr":      drv,
                "full_name": f"{info.get('FirstName','')} {info.get('LastName','')}".strip(),
                "team":      team,
                "color_hex": color,
                "color_rgb": hex_to_rgb(color),
            }
        except Exception:
            driver_info[drv] = {
                "abbr": drv, "full_name": drv, "team": "Unknown",
                "color_hex": "#FFFFFF", "color_rgb": [255, 255, 255]
            }

    print(f"Kierowcy: {list(driver_info.keys())}")

    # ── Klatki pozycji ───────────────────────────────────────────────────────
    print("Buduję klatki pozycji (to może chwilę potrwać)...")
    frames = []
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
                "t":    round(frame_time, 2),
                "lap":  int(lap['LapNumber']) if not np.isnan(lap['LapNumber']) else 0,
                "cars": []
            }

            for drv in drivers:
                try:
                    drv_laps = all_laps[all_laps['Driver'] == drv]
                    on_lap   = drv_laps[drv_laps['LapStartTime'].dt.total_seconds() <= frame_time]
                    if on_lap.empty:
                        continue
                    cur_lap  = on_lap.iloc[-1]
                    drv_tel  = cur_lap.get_telemetry()

                    elapsed    = frame_time - float(cur_lap['LapStartTime'].total_seconds())
                    elapsed_td = (drv_tel['Time'].dt.total_seconds()
                                  if hasattr(drv_tel['Time'], 'dt')
                                  else drv_tel['Time'].apply(lambda t: t.total_seconds()))
                    closest  = (elapsed_td - elapsed).abs().idxmin()
                    drv_row  = drv_tel.loc[closest]

                    raw_car_x = float(drv_row['X'])
                    raw_car_y = float(drv_row['Y'])

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

        if sampled >= 3000:
            print(f"  Osiągnięto limit 3000 klatek po okrążeniu {i+1}")
            break

        print(f"  Okrążenie {i+1}/{len(ref_laps)}: {sampled} klatek")

    print(f"\nLiczba wyeksportowanych klatek: {len(frames)}")

    # ── Zapis JSON ───────────────────────────────────────────────────────────
    output = {
        "event":         event_name,
        "year":          YEAR,
        "round":         race["round"],
        "session":       session_type,
        "canvas_width":  1200,
        "canvas_height": 700,
        "track_points":  track_points,
        "drivers":       driver_info,
        "frames":        frames,
    }

    with open(output_file, 'w') as f:
        json.dump(output, f, separators=(',', ':'))

    size_mb = os.path.getsize(output_file) / 1_000_000
    print(f"\n✅ Zapisano do {output_file} ({size_mb:.1f} MB)")
    print(f"   {len(track_points)} punktów toru | {len(frames)} klatek | {len(driver_info)} kierowców")


def main():
    print("\n🏎  F1 Race Replay – Data Fetcher")

    while True:
        race         = wybierz_wyscig()
        session_type = wybierz_sesje(race)
        pobierz_dane(race, session_type)

        again = input("\nPobrać kolejny wyścig? (t/n): ")
        if again.lower() != 't':
            print("\nGotowe. Do zobaczenia na torze! 🏁\n")
            break


if __name__ == "__main__":
    main()
