cmake_minimum_required(VERSION 3.20)
project(f1)

set(CMAKE_CXX_STANDARD 17)

# Ścieżka dla Homebrew na Macach M1/M2/M3
list(APPEND CMAKE_PREFIX_PATH "/opt/homebrew")

# Szukanie pakietów
find_package(CURL REQUIRED)
find_package(nlohmann_json REQUIRED)

# Zmiana na wielkie litery w COMPONENTS - to kluczowe dla SFML 3
find_package(SFML 3 REQUIRED COMPONENTS Graphics Window System)

add_executable(f1 main.cpp)

# Łączenie bibliotek - używamy nazw z przestrzenią nazw SFML::
target_link_libraries(f1 PRIVATE
        CURL::libcurl
        nlohmann_json::nlohmann_json
        SFML::Graphics
        SFML::Window
        SFML::System
)