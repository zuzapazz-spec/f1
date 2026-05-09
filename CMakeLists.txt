cmake_minimum_required(VERSION 3.20)
project(f1)

set(CMAKE_CXX_STANDARD 17)

find_package(nlohmann_json REQUIRED)

find_package(SFML 3 REQUIRED COMPONENTS Graphics Window System)

add_executable(f1 main.cpp)

target_link_libraries(f1 PRIVATE
        CURL::libcurl
        nlohmann_json::nlohmann_json
        SFML::Graphics
        SFML::Window
        SFML::System
)