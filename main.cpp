#include <SFML/Graphics.hpp>
#include <nlohmann/json.hpp>
#include <vector>
#include <string>
#include <iostream>
#include <fstream>
#include <cmath>
#include <algorithm>

using json = nlohmann::json;

/**
 * @brief Pojedynczy punkt na mapie toru wyścigowego.
 */
struct TrackPoint {
    float x;
    float y;
};

/**
 * @brief Dane telemetryczne pojedynczego bolidu w konkretnej klatce czasu.
 */
struct CarFrame {
    std::string driver;
    float x;
    float y;
    int speed;
    int gear;
    int position = 99;
    bool isOut = false;
};

/**
 * @brief Pojedyncza klatka czasu w wyścigu zawierająca stan wszytskich bolidów.
 */
struct RaceFrame {
    float time;
    int lap;
    int status;
    std::vector<CarFrame> cars;
};

/**
 * @brief Kompletne dane o całym wyścigu (tor, wszytskie klatki telemetrii).
 */
struct RaceData {
    std::string event;
    std::string circuit;
    std::string session;
    std::vector<TrackPoint> trackPoints;
    std::vector<RaceFrame> frames;
};

/**
 * @brief Klasa reprezentująca wizualną stronę bolidu F1 oraz jego stan w wyścigu.
 */
class F1Car {
    public:
    sf::CircleShape shape;
    std::string driverCode;
    sf::Text label;
    std::string abbr;
    std::vector<int> pitLaps;

    int position = 99;
    bool isOut = false;
    int outFromLap = 999;

    /**
     * @brief Tworzy nowy obiekt bolidu.
     * @param code Skrótowy kod kierowcy.
     * @param color Kolor kółka bolidu.
     * @param font Czcionka napisu nad bolidem.
     */
    F1Car(std::string code, sf::Color color, const sf::Font& font ):driverCode(code), label(font, code, 12) {
        shape.setRadius(8.f);
        shape.setFillColor(color);
        shape.setOrigin({8.f,8.f});
        label.setFillColor(sf::Color::White);
        label.setOutlineColor(sf::Color::Black);
        label.setOutlineThickness(1.f);
    }

    /**
     * @brief Aktualizuje położenie kropki bolidu i etykiety tekstowej.
     * @param x Współrzędna pozioma.
     * @param y Współrzędna pionowa.
     */
    void updatePosition(float x, float y) {
        shape.setPosition({x,y});
        label.setPosition({x + 10.f,y - 14.f});
    }

    /**
     * @brief Rysuje elementy bolidu w oknie aplikacji.
     * @param window Referencja do okna SFML, w którym wyświetlamy grafikę.
     */
    void draw(sf::RenderWindow& window) const{
        window.draw(shape);
        window.draw(label);
    }
};

/**
 * @brief Przetwarza dane wyścigu z formatu JSON na strukturę RaceData.
 * @param raceJson Obiekt JSON zawierający informacje o wyścigu, punkty toru i telemetrię.
 * @return Zwraca wypełnioną strukturę RaceData gotową do użycia w programie.
 */
RaceData parseRace(const json& raceJson) {
    RaceData rd;

    // Pobieranie podstawowych informacji o sesji
    rd.event = raceJson.value("event", "Unknown");
    rd.circuit = raceJson.value("circuit", "Unknown");
    rd.session = raceJson.value("session", "R");

    // Wczytywannie punktów toru (nitki wyścigowej)
    for (auto& pt: raceJson["track_points"]) {
        rd.trackPoints.push_back({pt["x"], pt["y"]});
    }

    // Wczytywanie klatek telemetrii (stan wyścigu w czasie)
    for (auto& f: raceJson["frames"]) {
        RaceFrame frame;
        frame.time = f["t"];
        frame.lap = f["lap"];
        frame.status = f.value("status", 1);

        // Wczytywanie danych o każdym bolidzie w danej klatce
        for (auto& c: f["cars"]) {
            CarFrame cf;
            cf.driver = c["drv"];
            cf.x = c["x"];
            cf.y = c["y"];
            cf.speed = c.value("speed", 0);
            cf.gear = c.value("gear", 0);
            cf.position = c.value("pos", 99);
            cf.isOut = c.value("out", false);
            frame.cars.push_back(cf);
        }
        rd.frames.push_back(frame);
    }
    return rd;
}

/**
 * @brief Tworzy wektor obiektów bolidów na podstawie danych o kierowcach z pliku JSON.
 * @param driversJson Obiekt JSON zawierający kody kierowców, kolory zespołów i statystyki.
 * @param font Referencja do czcionki używanej do etykiet nad bolidami.
 * @return Zwraca listę gotowych do użycia obiektów bolidów.
 */
std::vector <F1Car> buildCars(const json& driversJson, const sf::Font& font) {
    std::vector <F1Car> cars;

    for (auto& [code, info]: driversJson.items()) {

        // Pobieranie koloru zespołu w formacie RGB
        auto rgb = info["color_rgb"];
        sf::Color color(rgb[0], rgb[1], rgb[2]);

        // Inicjalizacja nowego obiektu bolidu
        F1Car car(code, color, font);

        // Ustawienie skrótu i tekstu etykiety
        car.abbr = info.value("abbr", code);
        car.label.setString(car.abbr);

        // Pobieranie okrążeń, na kórych nastąpił pit-stop
        if (info.contains("pit_laps")) {
            for (auto& pl : info["pit_laps"])
                car.pitLaps.push_back(pl.get<int>());

                // Pobieranie informacji o wycofaniu się z wyścigu (DNF)
                car.outFromLap = info.value("out_from_lap", 999);
        }

        // Przeniesienie gotowego bolidu do listy
        cars.push_back(std::move(car));
    }
    return cars;
}

/**
 * @brief Buduje wizualną reprezentację toru jako wstęgę o określonej szerokości.
 * @param points Wektor punktów (X, Y) definiujących środek trasy.
 * @return Zwraca gotowy obiekt graficzny reprezentujący asfaltową nawierzchnię toru.
 */
sf::VertexArray buildTrack(const std::vector<TrackPoint>& points) {
    sf::VertexArray track(sf::PrimitiveType::TriangleStrip);
    float width = 8.f;

    for (size_t i = 0; i + 1 < points.size(); i++) {
        // Obliczanie wektora kierunku między obecnym a następnym punktem
        float dx = points[i+1].x - points[i].x;
        float dy = points[i+1].y - points[i].y;
        float length = std::sqrt(dx*dx + dy*dy);

        if (length == 0) continue;

        // Obliczanie wektora normalnego (prostopadłego) do kierunku jazdy.
        float nx = -dy / length * width * 0.5f;
        float ny =  dx / length * width * 0.5f;

        // Tworzenie dwóch wierzchołków dla każdego punktu (lewa i prawa krawędź toru)
        sf::Vertex leftEdge, rightEdge;
        leftEdge.position = {points[i].x + nx, points[i].y + ny};
        rightEdge.position = {points[i].x - nx, points[i].y - ny};
        leftEdge.color = sf::Color(90, 90, 90);
        rightEdge.color = sf::Color(90, 90, 90);

        track.append(leftEdge);
        track.append(rightEdge);
    }
    return track;
}

/**
 * @brief Interkatywny przycisk w menu wyboru wyścigu.
 */
struct MenuButton {
    sf::RectangleShape box;
    sf::Text text;
    std::string raceKey;

    /**
     * @brief Konstruktor przycisku inicjalizujący tekst i czcionkę.
     * @param font Referencja do czcionki używanej w menu.
     */
    MenuButton(const sf::Font& font) : text(font, "", 18) {}
};

/**
 * @brief Generuje listę przycisków menu na podstawie kluczy wyścigów.
 * @param keys Wektor stringów zawierający identyfikatory wyścigów.
 * @param font Referencja do czcionki używanej w przyciskach.
 * @return Zwraca wektor gotowych, sformatowanych przycisków.
 */
std::vector<MenuButton> buildMenuButtons(const std::vector<std::string>& keys, const sf::Font& font) {
    std::vector<MenuButton> buttons;

    // Ustawienia układu menu
    const float startY = 120.f;
    const float buttonWidth = 700.f;
    const float buttonHeight = 42.f;
    const float gap = 10.f;
    const float startX = (1200.f - buttonWidth) / 2.f;

    for (size_t i = 0; i < keys.size(); i++) {
        MenuButton btn(font);
        btn.raceKey = keys[i];

        // Konfiguracja tła przycisku
        btn.box.setSize({buttonWidth, buttonHeight});
        btn.box.setPosition({startX,startY + i * (buttonHeight + gap)});
        btn.box.setFillColor(sf::Color(40, 40, 40));
        btn.box.setOutlineColor(sf::Color(180, 0, 0));
        btn.box.setOutlineThickness(1.f);

        // Formatowanie tekstu
        std::string label = keys[i];
        for (char& c : label) if (c=='-') c = ' ';

        btn.text.setString(label);
        btn.text.setCharacterSize(18);
        btn.text.setFillColor(sf::Color::White);

        // Centrowanie napisu
        auto textBounds = btn.text.getLocalBounds();
        btn.text.setPosition({
            startX + (buttonWidth - textBounds.size.x)/2.f,
            startY + i * (buttonHeight + gap) + (buttonHeight - textBounds.size.y) / 2.f - 4.f
        });

        buttons.push_back(btn);
    }
    return buttons;
}

/**
 * @brief Pobiera informacje o flagach i statusie tou na podstawie kodu statusu.
 * @param status Kod statusu otrzymany z telemetrii.
 * @return Zwraca parę zawierającą kolor flagi oraz jej nazwę do wyświetlenia.
 */
std::pair<sf::Color, std::string> getFlagInfo(int status) {
    switch (status) {
        case 2:  return {sf::Color(255, 255, 0), "YELLOW FLAG"};
        case 4:  return {sf::Color(255, 165, 0), "SAFETY CAR"};
        case 5:  return {sf::Color(255, 0, 0), "RED FLAG"};
        case 6:  return {sf::Color(255, 165, 0), "VIRTUAL SC"};
        default: return {sf::Color(0, 255, 0), ""};
    }
}

int main () {

    // KONFIGURACJA OKNA I ZASOBÓW

    sf::RenderWindow window(sf::VideoMode({1200,700}), "F1 Telemetry Visualizer");
    window.setFramerateLimit(60);

    sf::Font font;
    std::string fontPath;

#ifdef _WIN32
    fontPath="C:/Windows/Fonts/arial.ttf";
#else
    fontPath="/System/Library/Fonts/Supplemental/Arial.ttf";
#endif

    if (!font.openFromFile(fontPath)) {
        std::cerr<<"Font not found at:"<<fontPath<<std::endl;
        return -1;
    }

    // ŁADOWANIE DANYCH JSON

    std::ifstream file("races_all.json");
    if (!file.is_open()) {
        std::cerr<<"File not found"<<std::endl;
        return -1;
    }
    json j = json::parse(file);

    std::vector<std::string> raceKeys;
    for (auto& [key,value] : j["races"].items()) {
        raceKeys.push_back(key);
    }

    if (raceKeys.empty()) {
        std::cerr<<"Race Keys not found"<<std::endl;
        return -1;
    }

    // STAN APLIKACJI I ZMIENNE SYMULACJ

    enum class AppState {MENU, RACE};
    AppState state = AppState::MENU;

    RaceData currentRace;
    std::vector<F1Car> activeCars;
    sf::VertexArray trackline;
    size_t frameIndex = 0;
    bool isPaused = false;
    sf::Clock clock;

    auto menuButtons = buildMenuButtons(raceKeys, font);

    // ELEMENTY INTERFEJSU

    sf::Text titleText(font, "F1 2025 - Wybierz wyscig", 32);
    titleText.setFillColor(sf::Color(220, 0, 0));
    {
        auto b= titleText.getLocalBounds();
        titleText.setPosition({(1200.f - b.size.x)/ 2.f, 40.f});
    }

    sf::Text subtitleText(font, "Kliknij, aby odtworzyc replay", 16);
    subtitleText.setFillColor(sf::Color(150, 150, 150));
    {
        auto b= subtitleText.getLocalBounds();
        subtitleText.setPosition({(1200.f - b.size.x)/ 2.f, 85.f});
    }

    sf::Text hudText(font, "", 18);
    hudText.setFillColor(sf::Color::White);
    hudText.setPosition({10.f, 10.f});

    sf::Text controlsText(font, "SPACJA:pauza    A/D:przewijanie    F:fast forward    ESC:menu"  , 13);
    controlsText.setFillColor(sf::Color(120, 120, 120));
    controlsText.setPosition({10.f, 678.f});

    sf::RectangleShape progressBg({1200.f, 6.f});
    progressBg.setPosition({0.f, 694.f});
    progressBg.setFillColor(sf::Color(50, 50, 50));

    sf::RectangleShape progressFill({0.f, 6.f});
    progressFill.setPosition({0.f, 694.f});
    progressFill.setFillColor(sf::Color(220, 0, 0));

    // GŁÓWNA PĘTLA PROGRAMU

    while (window.isOpen()) {

        // 1. OBSŁUGA ZDARZEŃ
        while (const std::optional event = window.pollEvent()) {
            if (event->is<sf::Event::Closed>()) {
                window.close();
            }

            // Obsługa myszki (wybór wyścigu w menu)

            if (const auto* mouse = event->getIf<sf::Event::MouseButtonPressed>()) {
                if (mouse->button == sf::Mouse::Button::Left) {
                    sf::Vector2f mousePos = window.mapPixelToCoords({mouse->position.x, mouse->position.y});

                    if (state == AppState::MENU) {
                        for (auto& button : menuButtons) {
                            if (button.box.getGlobalBounds().contains(mousePos)) {
                                auto& raceJson = j["races"][button.raceKey];
                                currentRace = parseRace(raceJson);
                                activeCars = buildCars(raceJson["drivers"], font);
                                trackline = buildTrack(currentRace.trackPoints);

                                frameIndex = 0;
                                isPaused = false;
                                clock.restart();
                                state = AppState::RACE;
                            }
                        }
                    }
                }
            }

            // Obsługa klawiatury (sterowanie symulacją)

            if (const auto* key = event->getIf<sf::Event::KeyPressed>()) {
                if (state == AppState::RACE) {
                    // Zatrzymanie
                    if (key->code == sf::Keyboard::Key::Space) isPaused = !isPaused;

                    // Przewijanie do tyłu
                    if (key->code == sf::Keyboard::Key::A) {
                        std::cout << "LEFT" << std::endl;
                        if (frameIndex > 100)
                            frameIndex -= 100;
                        else
                            frameIndex = 0;
                        clock.restart();
                    }

                    // Przewijanie do przodu
                    if (key->code == sf::Keyboard::Key::D) {
                        std::cout << "RIGHT" << std::endl;
                        if (frameIndex + 100 < currentRace.frames.size())
                            frameIndex += 100;
                        else
                            frameIndex = currentRace.frames.size() - 1;
                        clock.restart();
                    }

                    // Reset
                    if (key->code == sf::Keyboard::Key::R) {
                        frameIndex = 0;
                        clock.restart();
                    }

                    // Powrót do menu
                    if (key->code == sf::Keyboard::Key::Escape) state = AppState::MENU;

                    // Szybkie przewijanie
                    if (key->code == sf::Keyboard::Key::F) {
                        if (frameIndex + 500 < currentRace.frames.size())
                            frameIndex += 500;
                        clock.restart();
                    }
                }
            }
        }

        // 2. AKTUALIZACJA LOGIKI

        window.clear(sf::Color(20,20,20));

        if (state == AppState::MENU) {
            sf::Vector2i pixelPos = sf::Mouse::getPosition(window);
            sf::Vector2f mousePos = window.mapPixelToCoords(pixelPos);

            for (auto& button : menuButtons) {
                if (button.box.getGlobalBounds().contains(mousePos)) {
                    button.box.setFillColor(sf::Color(80,20,20));
                }
                else {
                    button.box.setFillColor(sf::Color(40,40,40));
                }
            }
        }
        else if (state == AppState::RACE) {
            if (!currentRace.frames.empty() && frameIndex < currentRace.frames.size()) {
                const RaceFrame& frame = currentRace.frames[frameIndex];

                // Aktualizacja pozycji każdego bolidu
                for (const auto& carData : frame.cars) {
                    for (auto& car : activeCars) {
                        if (car.driverCode == carData.driver) {
                            car.updatePosition(carData.x, carData.y);
                            car.position = carData.position;
                            car.isOut = carData.isOut;
                        }
                    }
                }

                // Postęp klatek czasu
                if (!isPaused && clock.getElapsedTime().asMilliseconds() > 200) {
                    frameIndex++;
                    clock.restart();
                }

                // Aktualizacja napisów HUD
                std::string pauseLabel = isPaused ? " [PAUZA]" : "";
                hudText.setString(currentRace.event + " | Lap: " + std::to_string(frame.lap) + " | Time: " + std::to_string((int)frame.time) + "s" + pauseLabel);

                // Aktualizacja paska postępu na dole ekranu
                float progress = (float)frameIndex / (float)currentRace.frames.size();
                progressFill.setSize({1200.f * progress, 6.f});
            }
        }

        // 3. RYSOWANIE

        if (state == AppState::MENU) {
            window.draw(titleText);
            window.draw(subtitleText);

            for (auto& button : menuButtons) {
                window.draw(button.box);
                window.draw(button.text);
            }
        }

        // Rysowanie toru
        else if (state == AppState::RACE) {
            window.draw(trackline);

            // Rysowanie bolidów
            for (auto& car : activeCars) {
                car.draw(window);
            }

            // Legenda i tabela wyników po prawej stronie
            float legendY = 40.f;
            float legendX = 1080.f;
            int curLap = (frameIndex < currentRace.frames.size()) ? currentRace.frames[frameIndex].lap : currentRace.frames.back().lap;

            // // Sortowanie kierowców według pozycji w wyścigu
            std::vector<F1Car*> sorted;
            for (auto& car : activeCars)
                sorted.push_back(&car);
            std::sort(sorted.begin(), sorted.end(), [](F1Car* a, F1Car* b) {
                return a->position < b->position;
            });

            for (auto* car : sorted) {
                bool inPit = std::find(car->pitLaps.begin(), car->pitLaps.end(), curLap) != car->pitLaps.end();
                bool isOut = curLap >= car->outFromLap;

                // Kwadracik z kolorem zespołu
                sf::RectangleShape dot({10.f, 10.f});
                dot.setFillColor(car->shape.getFillColor());
                dot.setPosition({legendX, legendY + 4.f});
                window.draw(dot);

                // Tekst w legendzie
                std::string posStr = (car->position < 99) ? std::to_string(car->position) + " " : "";
                std::string label = posStr + car->abbr + (inPit ? " PIT" : "") + (isOut? " OUT" : "");

                sf::Color textColor = sf::Color::White;
                if (isOut)  textColor = sf::Color::Red;
                else if (inPit) textColor = sf::Color::Yellow;
                sf::Text drvLabel(font, label, 11);
                drvLabel.setFillColor(textColor);

                drvLabel.setPosition({legendX + 15.f, legendY});
                window.draw(drvLabel);
                legendY += 16.f;
            }

            // Wyświetlanie flag
            if (frameIndex < currentRace.frames.size()) {
                int currentStatus = currentRace.frames[frameIndex].status;
                auto [flagColor, flagName] = getFlagInfo(currentStatus);

                if (!flagName.empty()) {
                    sf::RectangleShape flagBg({200.f, 30.f});
                    flagBg.setFillColor(flagColor);
                    flagBg.setPosition({490.f, 10.f});
                    window.draw(flagBg);

                    sf::Text flagText(font, flagName, 16);
                    flagText.setFillColor(sf::Color::Black);
                    flagText.setPosition({500.f, 14.f});
                    window.draw(flagText);
                }
            }

            window.draw(hudText);
            window.draw(controlsText);
            window.draw(progressBg);
            window.draw(progressFill);
        }

        window.display();
    }

    return 0;
}
