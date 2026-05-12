cmake_minimum_required(VERSION 3.20)
project(f1)

set(CMAKE_CXX_STANDARD 17)

find_package(nlohmann_json REQUIRED)

find_package(SFML 3 REQUIRED COMPONENTS Graphics Window System)

add_executable(f1 main.cpp)

target_link_libraries(f1 PRIVATE
        nlohmann_json::nlohmann_json
        SFML::Graphics
        SFML::Window
        SFML::System
)
add_custom_command(TARGET f1 POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
        ${CMAKE_SOURCE_DIR}/races_all.json
        $<TARGET_FILE_DIR:f1>/races_all.json
)
configure_file(${CMAKE_SOURCE_DIR}/logo.png ${CMAKE_BINARY_DIR}/logo.png COPYONLY)