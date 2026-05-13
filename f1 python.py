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
    21: {"name": "Sao Paulo GP",      "round": 21, "circuit": "São Paulo",   "sprint": True},
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

def convert_hex_to_rgb(hex_color: str) -> list[int]:
    """
    Konwertuje kolor zapisany w formacie szesnastkowym (HEX) na listę wartości RGB.
    :param hex_color: Ciąg znaków reprezentujący kolor.
    :return: Zwraca listę trzech liczb całkowitych [R, G, B] w zakresie 0-255.
    """
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]

def normalize_track_coordinates(x_coords, y_coords, window_width=1200, window_height=700, margin=80):
    """
    Przeskalowuje surowe współrzędne GPS bolidów na współrzędne ekranowe okna SFML.
    :param x_coords: Tablica numpy ze współrzędnymi X.
    :param y_coords: Tablica numpy ze współrzędnymi Y.
    :param window_width: Szerokość okna aplikacji.
    :param window_height: Wysokość okna aplikacji.
    :param margin: Margines od krawędzi okna w pikselach.
    :return: Zwraca krotkę (skalowane_x, skalowane_y, x_min, x_max, y_min, y_max, skala).
    """

    # Wyznaczenie ekstremów toru
    x_min, x_max = x_coords.min(), x_coords.max()
    y_min, y_max = y_coords.min(), y_coords.max()

    # Obliczenie skali
    scale = min(
        (window_width  - 2 * margin) / (x_max - x_min),
        (window_height - 2 * margin) / (y_max - y_min)
    )

    # Normalizacja współrzędnych i centrowanie toru w oknie
    x_scaled = (x_coords - x_min) * scale + margin + (window_width  - 2*margin - (x_max - x_min)*scale) / 2
    y_scaled = (y_coords - y_min) * scale + margin + (window_height - 2*margin - (y_max - y_min)*scale) / 2

    # Odwrócenie osi Y
    y_scaled = window_height - y_scaled

    return x_scaled, y_scaled, x_min, x_max, y_min, y_max, scale

def generate_race_session_key(race: dict, session_type: str) -> str:
    """
    Tworzy unikalny identyfikator sesji wyścigowej używany jako klucz w pliku JSON.
    :param race: Słownik z danymi wyścigu
    :param session_type: Kod sesji.
    :return: Zwraca string będący unikalnym identyfikatorem.
    """
    session_suffix = "Race" if session_type == 'R' else "Sprint"

    return f"{race['name'].replace(' ', '_')}_{session_suffix}"

def load_existing_race_data() -> dict:
    """
    Wczytuje dane z pliku wyjściowego JSON, jeśli ten istnieje.
    :return: Zwraca słownik zawierający dane wyścigów lub pusty słownik (jeśli plik nie istnieje).
    """
    if os.path.exists(OUTPUT_FILE):
        print(f"📂 Znaleziono istniejący plik '{OUTPUT_FILE}' — doczytam nowe wyścigi.")
        with open(OUTPUT_FILE, 'r') as f:
            data = json.load(f)
        return data.get("races", {})
    return {}

def save_race_data_to_file(races_dict: dict):
    """
    Zapisuje zbiorcze dane wszystkich wyscigow do pliku wyjsciowego JSON.
    :param races_dict: Słownik zawierajacy przetworzone dane wszystkich sesji.
    """
    output = {
        "year":  YEAR,
        "races": races_dict,
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, separators=(',', ':'))

    file_size_mb = os.path.getsize(OUTPUT_FILE) / 1_000_000

    print(f"\n✅ Zapisano '{OUTPUT_FILE}' ({file_size_mb:.1f} MB). Liczba wyścigów w bazie: {len(races_dict)}.")

def select_race(races_dict: dict):
    """
    Wyświetla listę wyścigów z oznaczeniem już pobranych.
    :param races_dict: Aktualny słownik z już przetworzonymi wyścigami.
    :return: Zwraca słownik z danymi wybranego wyścigu.
    """
    print("\n" + "="*62)
    print("  F1 2025 – Wybór wyścigu")
    print("="*62)

    for key, race in RACES.items():
        race_key    = generate_race_session_key(race, 'R')
        sprint_tag  = " [SPRINT]" if race["sprint"] else ""
        downloaded_tag = " ✓" if race_key in races_dict else ""
        print(f"  {key:>2}. {race['name']:<22} ({race['circuit']}){sprint_tag}{downloaded_tag}")
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


def select_session(race: dict) -> str:
    """
    Pozwala użytkownikowi wybrać typ sesji: Wyścig (Race) lub Sprint.
    :param race: Słownik z danymi wybranego wyścigu z kalendarza RACES.
    :return: Zwraca kod sesji ('R' dla Race, 'S' dla Sprint).
    """
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


def fetch_session_data(race, session_type, races_dict):
    """
    Pobiera dane sesji z FastF1, przetwarza telemetrię i zapisuje do słownika.
    :param race: Słownik z kalendarza RACES zawierający dane o rundzie.
    :param session_type: Typ sesji
    :param races_dict: Główny słownik z danymi, do którego dopisujemy wyniki.
    """
    # Generowanie unikalnego klucza
    race_key = generate_race_session_key(race, session_type)

    if race_key in races_dict:
        ans = input(f"\n⚠️  '{race_key}' już istnieje w pliku. Nadpisać? (t/n): ")
        if ans.lower() != 't':
            print("Pominięto.")
            return

    # Przygotowanie folder na dane (Cache)
    os.makedirs(CACHE_DIR, exist_ok=True)
    fastf1.Cache.enable_cache(CACHE_DIR)

    print(f"\nŁadowanie: {YEAR} {race['name']} – sesja '{session_type}'...")

    # Pobieranie sesji z serwerow FastF1
    session = fastf1.get_session(YEAR, race["round"], session_type)
    session.load(telemetry=True, laps=True, weather=False, messages=False)

    event_name = session.event['EventName']
    print(f"Załadowano dane dla: {event_name}")

    # 1. LAYOUT TORU

    print("Wyodrębniam layout toru...")

    fastest = session.laps.pick_fastest()
    tel     = fastest.get_telemetry()
    raw_x   = tel['X'].values.astype(float)
    raw_y   = tel['Y'].values.astype(float)

    step  = max(1, len(raw_x) // 500)
    raw_x = raw_x[::step]
    raw_y = raw_y[::step]

    # Sklalowanie współrzędnych GPS na piksele
    x_scaled, y_scaled, x_min, x_max, y_min, y_max, scale = normalize_track_coordinates(raw_x, raw_y)

    # Lista punktów toru w dormacie gotowym dla SFML
    track_points = [{"x": round(float(nx), 2), "y": round(float(ny), 2)}
                    for nx, ny in zip(x_scaled,y_scaled)]

    # 2. LISTA KIEROWCÓW

    drivers     = list(session.drivers)[:MAX_DRIVERS]
    driver_info = {}

    for d in drivers:
        try:
            info  = session.get_driver(d)
            team  = info.get('TeamName', 'Unknown')
            color = TEAM_COLORS.get(team, '#FFFFFF')
            abbr  = info.get('Abbreviation', d)

            # Pobieranie okrążeń, na których wystąpiły zjazdy do boksów
            try:
                driver_laps = session.laps[session.laps['Driver'] == abbr]
                pit_laps = driver_laps[driver_laps['PitInTime'].notna()]['LapNumber'].tolist()
                pit_laps = [int(x) for x in pit_laps]
            except Exception:
                pit_laps = []

            # Określanie czy i kiedy kierowca odpadł z wyścigu (DNF)
            out_from_lap = 999
            try:
                if hasattr(session, 'results') and session.results is not None:
                    res = session.results[session.results['Abbreviation'] == abbr]
                    if not res.empty:
                        finish_status = str(res.iloc[0].get('Status', ''))
                        if finish_status not in ['Finished', '+1 Lap', '+2 Laps',
                                                 '+3 Laps', '+4 Laps', '+5 Laps']:
                            driver_laps_out = session.laps[session.laps['Driver'] == abbr]
                            if not driver_laps_out.empty:
                                out_from_lap = int(driver_laps_out.iloc[-1]['LapNumber'])
            except Exception:
                pass

            driver_info[abbr] = {
                "abbr":      abbr,
                "full_name": f"{info.get('FirstName','')} {info.get('LastName','')}".strip(),
                "team":      team,
                "color_hex": color,
                "color_rgb": convert_hex_to_rgb(color),
                "pit_laps":  pit_laps,
                "out_from_lap": out_from_lap,
            }
        except Exception:
            driver_info[d] = {
                "abbr":      d,
                "full_name": d,
                "team":      "Unknown",
                "color_hex": "#FFFFFF",
                "color_rgb": [255, 255, 255],
                "pit_laps":  [],
                "out_from_lap": 999,
            }

    # 3. KLATKI POZYCJI

    print("Buduję klatki pozycji (to może chwilę potrwać)...")
    frames = []

    try:
        pos = session.pos_data
    except Exception as e:
        print(f"Brak danych pozycyjnych: {e}")
        pos = {}

    print(f"Liczba kierowców: {len(pos)}")

    if pos is None or len(pos) == 0:
        print("⚠️  Brak danych pozycyjnych dla tej sesji.")
    else:
        # Znajdź kierowcę, który ma najwięcej okrążeń w laps
        best_driver = drivers[0]
        best_count = 0

        for d in drivers:
            if d in pos:
                abbr = driver_info.get(d, {}).get('abbr', d)
                count = len(session.laps[session.laps['Driver'] == abbr])
                if count > best_count:
                    best_count = count
                    best_driver = d

        ref_driver = best_driver

        ref_df = pos[ref_driver].copy()
        ref_df = ref_df.iloc[::SAMPLE_EVERY].copy().reset_index(drop=True)
        print(f"Kierowca referencyjny: {ref_driver}, klatek: {len(ref_df)}")

        pos_times = {}
        for d in drivers:
            if d in pos:
                pos_times[d] = pos[d]['SessionTime'].dt.total_seconds().values

        try:
            track_status_data = session.track_status
            ts_times = track_status_data['Time'].dt.total_seconds().values
            ts_status = track_status_data['Status'].values
        except Exception:
            ts_times, ts_status = None, None

        # Główna pętla budująca klatki czasu
        for i, (_, ref_row) in enumerate(ref_df.iterrows()):
            t = float(ref_row['SessionTime'].total_seconds())

            lap_num = 0
            try:
                #ref_abbr = driver_info[ref_driver]['abbr']
                #driver_laps = session.laps[session.laps['Driver'] == ref_abbr].sort_values('LapStartTime')
                ref_abbr = session.get_driver(ref_driver)['Abbreviation']
                driver_laps = session.laps[session.laps['Driver'] == ref_abbr].sort_values('LapStartTime')
                for _, lap_row in driver_laps.iterrows():
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

            for d in drivers:
                if d not in pos or d not in pos_times:
                    continue

                try:
                    driver_abbr = session.get_driver(d)['Abbreviation']
                except:
                    driver_abbr = str(d)

                times_arr = pos_times[d]
                idx = int(np.argmin(np.abs(times_arr - t)))
                row = pos[d].iloc[idx]

                raw_x = float(row['X'])
                raw_y = float(row['Y'])

                if np.isnan(raw_x) or np.isnan(raw_y) or (raw_x == 0.0 and raw_y == 0.0):
                    continue

                car_x = (raw_x - x_min) * scale + 80 + (1200 - 160 - (x_max - x_min)*scale) / 2
                car_y = 700 - ((raw_y - y_min) * scale + 80 + (700 - 160 - (y_max - y_min)*scale) / 2)
                pos_num = 99
                try:
                    driver_abbr = driver_info[d]['abbr']
                    driver_laps_pos = session.laps[session.laps['Driver'] == driver_abbr]
                    on_lap = driver_laps_pos[driver_laps_pos['LapStartTime'].dt.total_seconds() <= t]
                    if not on_lap.empty:
                        pos_val = on_lap.iloc[-1]['Position']
                        if not np.isnan(pos_val):
                            pos_num = int(pos_val)
                except Exception:
                    pass
                frame["cars"].append({
                    "driver":   driver_abbr,
                    "x":     round(car_x, 1),
                    "y":     round(car_y, 1),
                    "speed": 0,
                    "gear":  0,
                    "pos": pos_num,

                })

            if i < 3:
                print(f"Klatka {i}: t={t:.1f}s, samochodów={len(frame['cars'])}")

            if frame["cars"]:
                frames.append(frame)

        print(f"\nLiczba wyeksportowanych klatek: {len(frames)}")

    # 4. DODANIE DO SŁOWNIKA

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

    print(f" Dodano '{race_key}' do pliku.")

def main():
    print("\n🏎  F1 Race Replay – Data Fetcher")

    races_dict = load_existing_race_data()

    while True:
        race         = select_race(races_dict)
        session_type = select_session(race)
        fetch_session_data(race, session_type, races_dict)

        # Zapisz po każdym wyścigu — żeby nie stracić danych przy przerwaniu
        save_race_data_to_file(races_dict)

        again = input("\nPobrać kolejny wyścig? (t/n): ")
        if again.lower() != 't':
            print("\nGotowe. Do zobaczenia na torze! 🏁\n")
            break


if __name__ == "__main__":
    main()
 