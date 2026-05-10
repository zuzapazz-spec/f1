#include <SFML/Graphics.hpp>
#include <nlohmann/json.hpp>
#include <vector>
#include <string>
#include <iostream>
#include <fstream>
#include <cmath>
#include <algorithm>

using json = nlohmann::json;

struct TrackPoint {
    float x, y;
};

struct CarFrame {
    std::string driver;
    float x, y;
    int speed;
    int gear;
};

struct Frame {
    float time;
    int lap;
    int status;
    std::vector<CarFrame> cars;
};

struct RaceData {
    std::string event;
    std::string circuit;
    std::string session;
    std::vector<TrackPoint> trackPoints;
    std::vector<Frame> frames;

};

class F1Car {
    public:
    sf::CircleShape shape;
    std::string driverCode;
    sf::Text label;
    std::string abbr;
    std::vector<int> pitLaps;


    F1Car(std::string code, sf::Color color, const sf::Font& font ):driverCode(code), label(font, code, 12) {
        shape.setRadius(8.f);
        shape.setFillColor(color);
        shape.setOrigin({8.f,8.f});
        label.setFillColor(sf::Color::White);
        label.setOutlineColor(sf::Color::Black);
        label.setOutlineThickness(1.f);
    }

    void updatePosition(float x, float y) {
        shape.setPosition({x,y});
        label.setPosition({x + 10.f,y - 14.f});
    }

    void draw(sf::RenderWindow& window) const{
        window.draw(shape);
        window.draw(label);
    }
};

RaceData parseRace(const json& raceJson) {
    RaceData rd;
    rd.event = raceJson.value("event", "Unknown");
    rd.circuit = raceJson.value("circuit", "Unknown");
    rd.session = raceJson.value("session", "R");

    for (auto& pt: raceJson["track_points"]) {
        rd.trackPoints.push_back({pt["x"], pt["y"]});
    }

    for (auto& f: raceJson["frames"]) {
        Frame frame;
        frame.time = f["t"];
        frame.lap = f["lap"];
        frame.status = f.value("status", 1);
        for (auto& c: f["cars"]) {
            CarFrame cf;
            cf.driver = c["drv"];
            cf.x = c["x"];
            cf.y = c["y"];
            cf.speed = c.value("speed", 0);
            cf.gear = c.value("gear", 0);
            frame.cars.push_back(cf);
        }
        rd.frames.push_back(frame);
    }
    return rd;
}

std::vector <F1Car> buildCars(const json& driversJson, const sf::Font& font) {
    std::vector <F1Car> cars;
    for (auto& [code, info]: driversJson.items()) {
        auto rgb = info["color_rgb"];
        sf::Color color(rgb[0], rgb[1], rgb[2]);
        F1Car car(code, color, font);
        car.abbr = info.value("abbr", code);
        car.label.setString(car.abbr);
        if (info.contains("pit_laps")) {
            for (auto& pl : info["pit_laps"])
                car.pitLaps.push_back(pl.get<int>());
        }
        cars.push_back(std::move(car));

    }

    return cars;
}

sf::VertexArray buildTrack(const std::vector<TrackPoint>& points) {
    sf::VertexArray track(sf::PrimitiveType::TriangleStrip);
    float width = 8.f;

    for (size_t i = 0; i + 1 < points.size(); i++) {
        float dx = points[i+1].x - points[i].x;
        float dy = points[i+1].y - points[i].y;
        float len = std::sqrt(dx*dx + dy*dy);
        if (len == 0) continue;

        float nx = -dy / len * width * 0.5f;
        float ny =  dx / len * width * 0.5f;

        sf::Vertex v1, v2;
        v1.position = {points[i].x + nx, points[i].y + ny};
        v2.position = {points[i].x - nx, points[i].y - ny};
        v1.color = sf::Color(90, 90, 90);
        v2.color = sf::Color(90, 90, 90);

        track.append(v1);
        track.append(v2);
    }
    return track;
}

struct MenuButton {
    sf::RectangleShape box;
    sf::Text text;
    std::string raceKey;

    MenuButton(const sf::Font& font) : text(font, "", 18) {}
};

std::vector<MenuButton> buildMenuButtons(const std::vector<std::string>& keys, const sf::Font& font) {
    std::vector<MenuButton> buttons;
    float startY = 120.f;
    float btnW = 700.f;
    float btnH = 42.f;
    float gap = 10.f;
    float startX = (1200.f - btnW) / 2.f;

    for (size_t i = 0; i < keys.size(); i++) {
        MenuButton btn(font);
        btn.raceKey = keys[i];

        btn.box.setSize({btnW, btnH});
        btn.box.setPosition({startX,startY + i * (btnH + gap)});
        btn.box.setFillColor(sf::Color(40, 40, 40));
        btn.box.setOutlineColor(sf::Color(180, 0, 0));
        btn.box.setOutlineThickness(1.f);

        std::string label = keys[i];
        for (char& c : label) if (c=='-') c = ' ';

        btn.text.setString(label);
        btn.text.setCharacterSize(18);
        btn.text.setFillColor(sf::Color::White);

        auto bounds = btn.text.getLocalBounds();
        btn.text.setPosition({
            startX + (btnW - bounds.size.x)/2.f,
            startY + i * (btnH + gap) + (btnH - bounds.size.y) / 2.f - 4.f
        });

        buttons.push_back(btn);
    }
    return buttons;

}
std::pair<sf::Color, std::string> getFlagInfo(int status) {
    switch (status) {
        case 2:  return {sf::Color(255, 255,   0), "YELLOW FLAG"};
        case 4:  return {sf::Color(255, 165,   0), "SAFETY CAR"};
        case 5:  return {sf::Color(255,   0,   0), "RED FLAG"};
        case 6:  return {sf::Color(255, 165,   0), "VIRTUAL SC"};
        default: return {sf::Color(  0, 255,   0), ""};
    }
}
int main () {
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

    enum class AppState {MENU, RACE};
    AppState state = AppState::MENU;

    RaceData currentRace;
    std::vector<F1Car> activeCars;
    sf::VertexArray trackline;
    size_t frameIndex = 0;
    bool paused = false;
    sf::Clock clock;

    auto menuButtons = buildMenuButtons(raceKeys, font);

    sf::Text titleText(font, "F1 2025 - Wybierz wyscig", 32);
    titleText.setFillColor(sf::Color(220, 0, 0));
    {
        auto b= titleText.getLocalBounds();
        titleText.setPosition({(1200.f - b.size.x)/ 2.f, 40.f});
    }

    sf::Text subtitleText(font, "Kliknij aby odtworzyc replay", 16);
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

    while (window.isOpen()) {

        // 1. OBSŁUGA ZDARZEŃ
        while (const std::optional event = window.pollEvent()) {
            if (event->is<sf::Event::Closed>()) {
                window.close();
            }

            // Obsługa myszki

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
                                paused = false;
                                clock.restart();
                                state = AppState::RACE;
                            }
                        }
                    }
                }
            }

            // Obsługa klawiatury

            if (const auto* key = event->getIf<sf::Event::KeyPressed>()) {
                if (state == AppState::RACE) {
                    if (key->code == sf::Keyboard::Key::Space) {
                        paused = !paused;
                    }
                    if (key->code == sf::Keyboard::Key::A) {
                        std::cout << "LEFT" << std::endl;
                        if (frameIndex > 100)
                            frameIndex -= 100;
                        else
                            frameIndex = 0;
                        clock.restart();
                    }
                    if (key->code == sf::Keyboard::Key::D) {
                        std::cout << "RIGHT" << std::endl;
                        if (frameIndex + 100 < currentRace.frames.size())
                            frameIndex += 100;
                        else
                            frameIndex = currentRace.frames.size() - 1;
                        clock.restart();
                    }
                    if (key->code == sf::Keyboard::Key::R) {
                        frameIndex = 0;
                        clock.restart();
                    }
                    if (key->code == sf::Keyboard::Key::Escape) {
                        state = AppState::MENU;
                    }
                    if (key->code == sf::Keyboard::Key::F) {
                        if (frameIndex + 500 < currentRace.frames.size())
                            frameIndex += 500;
                        clock.restart();
                    }
                }
            }
        }

        // 2. AKTUALIZACJE

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
                const Frame& frame = currentRace.frames[frameIndex];

                // Aktualizacja pozycji bolidów

                for (const auto& carData : frame.cars) {
                    for (auto& car : activeCars) {
                        if (car.driverCode == carData.driver) {
                            car.updatePosition(carData.x, carData.y);
                        }
                    }
                }

                // Mierzenie czasu klatek

                if (!paused && clock.getElapsedTime().asMilliseconds() > 200) {
                    frameIndex++;
                    clock.restart();
                }

                // Aktualizacja HUD

                std::string pauseLabel = paused ? " [PAUZA]" : "";
                hudText.setString(currentRace.event + " | Lap: " + std::to_string(frame.lap) + " | Time: " + std::to_string((int)frame.time) + "s" + pauseLabel);

                // Aktualizacja paska postępu

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

            // Wyświetlanie legendy kierowców

            float legendY = 40.f;
            float legendX = 1080.f;

            int curLap = (frameIndex < currentRace.frames.size()) ? currentRace.frames[frameIndex].lap : currentRace.frames.back().lap;
            //std::cout << "curLap=" << curLap << std::endl;
            for (auto& car : activeCars) {
                if (car.abbr == "NOR") {  // sprawdź tylko NOR
                    std::cout << "NOR pitLaps: ";
                    for (auto& pl : car.pitLaps)
                        std::cout << pl << " ";
                    std::cout << std::endl;
                }
                bool inPit = std::find(car.pitLaps.begin(), car.pitLaps.end(), curLap) != car.pitLaps.end();

                sf::RectangleShape dot({10.f, 10.f});
                dot.setFillColor(car.shape.getFillColor());
                dot.setPosition({legendX, legendY + 4.f});
                window.draw(dot);

                std::string label = car.abbr + (inPit ? " PIT" : "");
                sf::Text drvLabel(font, label, 11);
                drvLabel.setFillColor(inPit ? sf::Color::Yellow : sf::Color::White);
                drvLabel.setPosition({legendX + 15.f, legendY});
                window.draw(drvLabel);
                legendY += 16.f;
            }
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
