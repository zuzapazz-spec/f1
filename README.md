# 🏎️ Wizualizator Wyścigów F1

Aplikacja w C++ z interfejsem graficznym (SFML) oraz skryptem w Pythonie, służąca do pobierania, analizowania i wizualizacji danych z wyścigów Formuły 1.


## 🚀 Kluczowe funkcjonalności
* **Moduł pobierania danych (Python):** Skrypt automatycznie łączy się z API biblioteki `FastF1`, skąd wyciąga szczegółowe czasy okrążeń, statystyki kierowców oraz pełne wyniki z sesji wyścigowych.


* **Warstwa przechowywania (JSON):** Wszystkie pobrane informacje są porządkowane i zapisywane w pliku `races_all.json`. Dzięki temu aplikacja zapamiętuje wyścigi i przy kolejnym uruchomieniu ładuje je błyskawicznie – nawet bez dostępu do internetu.


* **Silnik renderowania grafiki (C++ / SFML):** Projekt posiada dedykowane okno graficzne zbudowane w C++. Odpowiada ono za płynne renderowanie interfejsu, obsługę menu oraz wizualizację przebiegu sesji wyścigowych Formuły 1.


## 🛠️ Jak uruchomić projekt lokalnie

### 1. Wymagania wstępne
Do uruchomienia projektu potrzebujesz:
* Kompilatora **C++** obsługującego standard C++17 lub nowszy.
* Zainstalowanego środowiska **Python** (wersja 3.8 lub nowsza).
* Menedżera pakietów **vcpkg** (zintegrowanego z Twoim IDE, np. CLion) w celu automatycznego pobrania bibliotek `SFML` oraz `nlohmann-json`.

### 2. Konfiguracja środowiska Python
Projekt nie zawiera gotowego środowiska wirtualnego ze względu na optymalizację wielkości repozytorium. Należy je stworzyć lokalnie:
```bash
# Tworzenie wirtualnego środowiska
python -m venv f1env

# Aktywacja środowiska (Windows)
f1env\Scripts\activate

# Aktywacja środowiska (macOS / Linux)
source f1env/bin/activate

# Instalacja wymaganych bibliotek
pip install fastf1 requests
```

### 3. Kompilacja C++ i zarządzanie pakietami
Projekt wykorzystuje menedżera pakietów **vcpkg** do automatycznego zarządzania zewnętrznymi bibliotekami (takimi jak `SFML` oraz `nlohmann-json`).

Aby uruchomić projekt w środowisku CLion:
1. Upewnij się, że masz włączone wsparcie dla `vcpkg` w ustawieniach IDE.
2. Otwórz główny folder projektu – CLion automatycznie wykryje plik `CMakeLists.txt` oraz zintegrowany manifest vcpkg, po czym pobierze i skonfiguruje wymagane biblioteki.
3. Po zakończeniu indeksowania projektu kliknij ikonę **Build**, a następnie **Run**.


## 💡 Co jeśli brakuje pliku `races_all.json`?
Jeśli plik z danymi wyścigowymi nie pobrał się automatycznie lub chcesz zaktualizować bazę danych o nowe wyścigi, musisz uruchomić skrypt Python, który pobierze świeże dane z API i sam wygeneruje ten plik.

Aby to zrobić, po aktywacji środowiska wirtualnego uruchom w terminalu komendę:
```bash
python "f1 python.py"
```
Skrypt połączy się z API `FastF1` i pobierze wybrane statystyki.

Następnie wpisz w terminalu komendę:
```bash
python "f1 python.py" --save races_all.json
```
Wówczas plik `races_all.json` zostaje automatycznie zaktualizowany i gotowy do użycia.


## 📂 Struktura plików
```text
.
├── CMakeLists.txt      # Konfiguracja budowania projektu C++ (CMake)
├── main.cpp            # Główny kod źródłowy aplikacji i pętla graficzna SFML
├── f1 python.py        # Skrypt Python do pobierania telemetrii z API FastF1
├── races_all.json      # Lokalna baza danych w formacie JSON z wynikami wyścigów
└── logo.png            # Logotyp F1 wykorzystywany w interfejsie graficznym
```