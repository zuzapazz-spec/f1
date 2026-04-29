#include <SFML/Graphics.hpp>
#include <curl/curl.h>
#include <nlohmann/json.hpp>
#include <vector>
#include <string>
#include <iostream>

using json = nlohmann::json;

class F1Car {
    public:
    sf::CircleShape shape;
    std::string driverCode;
    sf::Text label;

    F1Car(std::string code , sf::Color color, sf::Font& font ):driverCode(code), label(font, code, 14) {
        shape.setRadius(10.f);
        shape.setFillColor(color);
        shape.setOrigin({10.f,10.f});

        label.setFont(font);
        label.setString(code);
        label.setFillColor(sf::Color::White);
        label.setCharacterSize(14);

    }
    void updatePosition(float x, float y) {
        sf::Vector2f pos = {600.f + x, 350.f + y};
        shape.setPosition(pos);
        label.setPosition({pos.x + 12.f, pos.y - 12.f});
    }

    void draw(sf::RenderWindow& window) {
        window.draw(shape);
        window.draw(label);
    }
};

size_t WriteCallback(void* contents, size_t size , size_t nmemb, std::string* s) {
    s->append((char*)contents, size*nmemb);
    return size*nmemb;
}





int main () {
    sf::RenderWindow window(sf::VideoMode({1200,700}), "F1 Telemetry Visualizer");
    window.setFramerateLimit(60);

    sf::Font font;
    if (!font.openFromFile("/System/Library/Fonts/Supplemental/Arial.ttf")) {
        std::cerr<<"Font not found"<<std::endl;
    }
    std::vector<F1Car> activeCars;
    CURL *curl = curl_easy_init();
    if (curl ) {
        std::string readBuffer;
        curl_easy_setopt(curl, CURLOPT_URL, "https://ergast.com/api/f1/2024/drivers.json");
        curl_easy_setopt(curl, CURLOPT_USERAGENT,"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)");
        curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
        curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);

        std::cout <<"Pobieranie danych"<<std::endl;
        CURLcode res = curl_easy_perform(curl);
        if (res != CURLE_OK) {
            std::cerr << "Błąd CURL: " << curl_easy_strerror(res) << std::endl;
        } else if (readBuffer.empty()) {
            std::cerr << "Błąd: Odebrano pustą odpowiedź z serwera!" << std::endl;
        } else {
            try {
                auto j = json::parse(readBuffer);
                auto drivers = j["MRData"]["DriverTable"]["Drivers"];
                for (int i =0; i<std::min((int)drivers.size(), 10); i++) {
                    std::string code = drivers[i].value("code", "??");
                    activeCars.emplace_back(code, sf::Color::Red, font);
                    activeCars.back().updatePosition(i*70.f - 300.f, 0);
                }
                std::cout<<"załadowano"<< activeCars.size()<<"kierowcow"<<std::endl;
            } catch (json::parse_error& e) {
                std::cerr << "Błąd parsowania: " << e.what() << std::endl;
                std::cerr << "tresc:"<< readBuffer.substr(0, 100) << std::endl;
            }
        }
        curl_easy_cleanup(curl);
    }
    activeCars.emplace_back("TEST", sf::Color::Yellow, font);
    activeCars.back().updatePosition(0, 0);
    while (window.isOpen()) {
        while (const std::optional event = window.pollEvent()) {
            if (event->is<sf::Event::Closed>()) window.close();
        }
        window.clear(sf::Color(30, 30, 30 ));

        for (auto& car : activeCars) {
            car.draw(window);
        }
        window.display();
    }

    return 0;
}