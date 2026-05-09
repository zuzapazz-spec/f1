#include <SFML/Graphics.hpp>
#include <nlohmann/json.hpp>
#include <vector>
#include <string>
#include <iostream>
#include <fstream>

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
        cars.emplace_back(code, color, font);
    }
    return cars;
}

sf::VertexArray buildTrack(const std::vector<TrackPoint>& points) {
    sf::VertexArray track(sf::PrimitiveType::LineStrip);
    for (auto& pt: points) {
        sf::Vertex v;
        v.position = {pt.x, pt.y };
        v.color = sf::Color(90, 90, 90);
        track.append(v);
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

    sf::Text controlsText(font, "SPACJA:pauza    <-/->:przewijanie    ESC:menu", 13);
    controlsText.setFillColor(sf::Color(120, 120, 120));
    controlsText.setPosition({10.f, 678.f});

    sf::RectangleShape progressBg({1200.f, 6.f});
    progressBg.setPosition({0.f, 694.f});
    progressBg.setFillColor(sf::Color(50, 50, 50));

    sf::RectangleShape progressFill({0.f, 6.f});
    progressFill.setPosition({0.f, 694.f});
    progressFill.setFillColor(sf::Color(220, 0, 0));

    while (window.isOpen()) {

        while (const std::optional event = window.pollEvent()) {
            if (event->is<sf::Event::Closed>())
                window.close();
        }

        if (frameIndex < frames.size()) {
            for (auto& carData: frames[frameIndex]["cars"]) {
                string drv = carData["drv"];
                float x = carData["x"];
                float y = carData["y"];
                for (auto& car : activeCars) {
                    if (car.driverCode == drv) {
                        car.updatePosition(x, y);
                    }
                }
                if (clock.getElapsedTime().asMilliseconds() > 100) {
                    frameIndex++;
                    clock.restart();
                }
            }
            window.clear(sf::Color(20,20,20));
            for (auto& car: activeCars) {
                car.draw(window);

            }
            window.display();
        }
    }
    return 0;
}