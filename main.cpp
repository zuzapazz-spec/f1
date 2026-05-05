#include <SFML/Graphics.hpp>
#include <nlohmann/json.hpp>
#include <vector>
#include <string>
#include <iostream>
#include <fstream>
using namespace std;
using json = nlohmann::json;
struct TrackPoint {
    float x, y;
};

struct CarFrame {
    string driver;
    float x, y;
    int speed;
    int gear;
};
struct Frame {
    float time;
    int lap;
    vector<CarFrame> cars;
};
class F1Car {
    public:
    sf::CircleShape shape;
    std::string driverCode;
    sf::Text label;

    F1Car(std::string code , sf::Color color, sf::Font& font ):driverCode(code), label(font, code, 14) {
        shape.setRadius(10.f);
        shape.setFillColor(color);
        shape.setOrigin({10.f,10.f});
        label.setFillColor(sf::Color::White);


    }
    void updatePosition(float x, float y) {
        shape.setPosition({x,y});
        label.setPosition({x + 12.f,y - 12.f});
    }

    void draw(sf::RenderWindow& window) {
        window.draw(shape);
        window.draw(label);
    }
};

int main () {
    sf::RenderWindow window(sf::VideoMode({1200,700}), "F1 Telemetry Visualizer");
    window.setFramerateLimit(60);

    sf::Font font;
    if (!font.openFromFile("/System/Library/Fonts/Supplemental/Arial.ttf")) {
        std::cerr<<"Font not found"<<std::endl;
        return -1;
    }
    std::ifstream file("race_data_British_GP_Race.json");
    auto j = json::parse(file);


    std::vector<F1Car> activeCars;
    for (auto& [code, info]: j["drivers"].items()) {
        auto rgb = info["color_rgb"];
        sf::Color color(rgb[0], rgb[1], rgb[2]);
        activeCars.emplace_back(code, color, font);
    }
    auto frames = j["frames"];
    size_t frameIndex = 0;
    sf::Clock clock;

    while (window.isOpen()) {
        while (const std::optional event = window.pollEvent()) {
            if (event->is<sf::Event::Closed>()) window.close();
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