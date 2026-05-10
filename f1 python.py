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
YEAR         = 2025
SAMPLE_EVERY = 10
MAX_DRIVERS  = 20
CACHE_DIR    = ".fastf1_cache"
OUTPUT_FILE  = "races_all.json"
# ──────────────────────────────────────────────────────────────────────────────

TEAM_COLORS = {
    'Mercedes':         '#00D2BE',
    'Red Bull Racing':  '#3671C6',
    'Ferrari':          '#E8002D',
    'McLaren':          '#FF8000',
    'Aston Martin':     '#358C75',
    'Alpine':           '#FF87BC',
    'Williams':         '#64C4FF',
    'Racing Bulls':     '#6692FF',
    'Kick Sauber':      '#52E252',
    'Haas F1 Team':     '#B6BABD',
}


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]


def normalize_track(x_arr, y_arr, target_width=1200, target_height=700, padding=80):
    x_min, x_max = x_arr.min(), x_arr.max()
    y_min, y_max = y_arr.min(), y_arr.max()
    scale = min(
        (target_width  - 2 * padding) / (x_max - x_min),
        (target_height - 2 * padding) / (y_max - y_min)
    )
    x_norm = (x_arr - x_min) * scale + padding + (target_width  - 2*padding - (x_max - x_min)*scale) / 2
    y_norm = (y_arr - y_min) * scale + padding + (target_height - 2*padding - (y_max - y_min)*scale) / 2
    y_norm = target_height - y_norm
    return x_norm, y_norm, x_min, x_max, y_min, y_max, scale


def _race_key(race, session_type):
    """Unikalny klucz dla wyścigu+sesji, używany jako ID w JSON."""
    suffix = "Race" if session_type == 'R' else "Sprint"
    return f"{race['name'].replace(' ', '_')}_{suffix}"


def wczytaj_istniejacy_plik():
    """Wczytuje races_all.json jeśli już istnieje, zwraca słownik wyścigów."""
    if os.path.exists(OUTPUT_FILE):
        print(f"📂 Znaleziono istniejący plik '{OUTPUT_FILE}' — doczytam nowe wyścigi.")
        with open(OUTPUT_FILE, 'r') as f:
            data = json.load(f)
        return data.get("races", {})
    return {}


def zapisz_plik(races_dict):
    """Zapisuje wszystkie wyścigi do races_all.json."""
    output = {
        "year":  YEAR,
        "races": races_dict,
    }
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, separators=(',', ':'))
    size_mb = os.path.getsize(OUTPUT_FILE) / 1_000_000
    print(f"\n✅ Zapisano '{OUTPUT_FILE}' ({size_mb:.1f} MB) — {len(races_dict)} wyścig(ów) w pliku.")


def wybierz_wyscig(races_dict):
    """Wyświetla listę wyścigów z oznaczeniem już pobranych."""
    print("\n" + "="*62)
    print("  F1 2025 – Wybór wyścigu")
    print("="*62)
    for key, race in RACES.items():
        race_key    = _race_key(race, 'R')
        sprint_tag  = " [SPRINT]" if race["sprint"] else ""
        pobrano_tag = " ✓" if race_key in races_dict else ""
        print(f"  {key:>2}. {race['name']:<22} ({race['circuit']}){sprint_tag}{pobrano_tag}")
    print("="*62)
    print("  ✓ = już pobrane i zapisane w pliku")

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
    """Wybór sesji: wyścig główny lub sprint."""
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


def pobierz_dane(race, session_type, races_dict):
    """Pobiera dane wyścigu i dodaje do słownika races_dict."""

    race_key = _race_key(race, session_type)

    if race_key in races_dict:
        ans = input(f"\n⚠️  '{race_key}' już istnieje w pliku. Nadpisać? (t/n): ")
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
    tel     = fastest.get_telemetry()
    raw_x   = tel['X'].values.astype(float)
    raw_y   = tel['Y'].values.astype(float)

    step  = max(1, len(raw_x) // 500)
    raw_x = raw_x[::step]
    raw_y = raw_y[::step]

    norm_x, norm_y, x_min, x_max, y_min, y_max, scale = normalize_track(raw_x, raw_y)

    track_points = [{"x": round(float(nx), 2), "y": round(float(ny), 2)}
                    for nx, ny in zip(norm_x, norm_y)]

    # ── Lista kierowców ──────────────────────────────────────────────────────
    drivers     = list(session.drivers)[:MAX_DRIVERS]
    driver_info = {}
    for drv in drivers:
        try:
            info  = session.get_driver(drv)
            team  = info.get('TeamName', 'Unknown')
            color = TEAM_COLORS.get(team, '#FFFFFF')
            abbr  = info.get('Abbreviation', drv)

            # Pit stopy
            try:
                drv_laps = session.laps[session.laps['Driver'] == abbr]
                pit_laps = drv_laps[drv_laps['PitInTime'].notna()]['LapNumber'].tolist()
                pit_laps = [int(x) for x in pit_laps]
            except Exception:
                pit_laps = []

            driver_info[drv] = {
                "abbr":      abbr,
                "full_name": f"{info.get('FirstName','')} {info.get('LastName','')}".strip(),
                "team":      team,
                "color_hex": color,
                "color_rgb": hex_to_rgb(color),
                "pit_laps":  pit_laps,  # ← nowe
            }
        except Exception:
            driver_info[drv] = {
                "abbr":      drv,
                "full_name": drv,
                "team":      "Unknown",
                "color_hex": "#FFFFFF",
                "color_rgb": [255, 255, 255],
                "pit_laps":  [],
            }
    print(f"Kierowcy: {list(driver_info.keys())}")

    # ── Klatki pozycji ───────────────────────────────────────────────────────────
    print("Buduję klatki pozycji (to może chwilę potrwać)...")
    frames = []

    try:
        pos = session.pos_data
    except Exception as e:
        print(f"Brak danych pozycyjnych: {e}")
        pos = {}

    print(f"Liczba kierowców w pos_data: {len(pos)}")

    if pos is None or len(pos) == 0:
        print("⚠️  Brak danych pozycyjnych dla tej sesji.")
    else:
# Znajdź kierowcę który ma najwięcej okrążeń w laps
        ref_drv = drivers[0]
        if ref_drv not in pos:
            ref_drv = next(iter(pos))

# Użyj skrótu do liczenia okrążeń
        best_drv = ref_drv
        best_count = 0
        for d in drivers:
            if d not in pos:
                continue
            abbr = driver_info.get(d, {}).get('abbr', d)
            count = len(session.laps[session.laps['Driver'] == abbr])
            if count > best_count:
                best_count = count
                best_drv = d
        ref_drv = best_drv

        ref_df = pos[ref_drv].copy()
        ref_df = ref_df.iloc[::SAMPLE_EVERY].copy().reset_index(drop=True)
        print(f"Ref driver: {ref_drv}, klatek: {len(ref_df)}")


        pos_times = {}
        for drv in drivers:
            if drv in pos:
                pos_times[drv] = pos[drv]['SessionTime'].dt.total_seconds().values
        try:
            track_status_data = session.track_status
            ts_times = track_status_data['Time'].dt.total_seconds().values
            ts_status = track_status_data['Status'].values
        except Exception:
            track_status_data = None
            ts_times = None
            ts_status = None

        for i, (_, ref_row) in enumerate(ref_df.iterrows()):
            t = float(ref_row['SessionTime'].total_seconds())
            lap_num = 0
            try:
                ref_abbr = driver_info[ref_drv]['abbr']  # np. '81' → 'BEA'
                drv_laps = session.laps[session.laps['Driver'] == ref_abbr].sort_values('LapStartTime')
                for _, lap_row in drv_laps.iterrows():
                    lst = lap_row['LapStartTime']
                    if hasattr(lst, 'total_seconds'):
                        lst_sec = lst.total_seconds()
                    else:
                        lst_sec = float(lst) / 1e9
                    if lst_sec <= t:
                        lap_num = int(lap_row['LapNumber'])
                    else:
                        break
            except Exception as e:
                print(f"Błąd lap_num: {e}")

            status = 1
            try:
                if ts_times is not None:
                    idx_s = int(np.argmin(np.abs(ts_times - t)))
                    status = int(ts_status[idx_s])
            except Exception:
                pass

            frame = {"t": round(t, 2), "lap": lap_num, "status": status, "cars": []}

            for drv in drivers:
                if drv not in pos or drv not in pos_times:
                    continue
                times_arr = pos_times[drv]
                idx = int(np.argmin(np.abs(times_arr - t)))
                row = pos[drv].iloc[idx]

                raw_x = float(row['X'])
                raw_y = float(row['Y'])

                if np.isnan(raw_x) or np.isnan(raw_y) or (raw_x == 0.0 and raw_y == 0.0):
                    continue

                car_x = (raw_x - x_min) * scale + 80 + (1200 - 160 - (x_max - x_min)*scale) / 2
                car_y = 700 - ((raw_y - y_min) * scale + 80 + (700 - 160 - (y_max - y_min)*scale) / 2)
                pos_num = 99
                try:
                    drv_abbr = driver_info[drv]['abbr']
                    drv_laps_pos = session.laps[session.laps['Driver'] == drv_abbr]
                    on_lap = drv_laps_pos[drv_laps_pos['LapStartTime'].dt.total_seconds() <= t]
                    if not on_lap.empty:
                        pos_val = on_lap.iloc[-1]['Position']
                        if not np.isnan(pos_val):
                            pos_num = int(pos_val)
                except Exception:
                    pass

                out = False
                try:
                    drv_abbr = driver_info[drv]['abbr']
                    if hasattr(session, 'results') and session.results is not None:
                        res = session.results[session.results['Abbreviation'] == drv_abbr]
                        if not res.empty:
                            finish_status = str(res.iloc[0].get('Status', ''))
                            if finish_status not in ['Finished', '+1 Lap', '+2 Laps',
                                                     '+3 Laps', '+4 Laps', '+5 Laps']:
                                out = True
                except Exception:
                    pass
                frame["cars"].append({
                    "drv":   drv,
                    "x":     round(car_x, 1),
                    "y":     round(car_y, 1),
                    "speed": 0,
                    "gear":  0,
                    "pos": pos_num,
                    "out": out,
                })

            if i < 3:
                print(f"Klatka {i}: t={t:.1f}s, samochodów={len(frame['cars'])}")

            if frame["cars"]:
                frames.append(frame)

        print(f"\nLiczba wyeksportowanych klatek: {len(frames)}")
    # ── Dodaj do słownika ────────────────────────────────────────────────────
    races_dict[race_key] = {
        "event":         event_name,
        "round":         race["round"],
        "circuit":       race["circuit"],
        "session":       session_type,
        "canvas_width":  1200,
        "canvas_height": 700,
        "track_points":  track_points,
        "drivers":       driver_info,
        "frames":        frames,
    }

    print(f"  Dodano '{race_key}' do pliku.")


def main():
    print("\n🏎  F1 Race Replay – Data Fetcher")

    races_dict = wczytaj_istniejacy_plik()

    while True:
        race         = wybierz_wyscig(races_dict)
        session_type = wybierz_sesje(race)
        pobierz_dane(race, session_type, races_dict)

        # Zapisz po każdym wyścigu — żeby nie stracić danych przy przerwaniu
        zapisz_plik(races_dict)

        again = input("\nPobrać kolejny wyścig? (t/n): ")
        if again.lower() != 't':
            print("\nGotowe. Do zobaczenia na torze! 🏁\n")
            break


if __name__ == "__main__":
    main()
 