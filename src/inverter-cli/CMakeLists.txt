cmake_minimum_required(VERSION 3.10)
project(inverter_poller)

# Modern CMake style for compiler options
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2 -static")

# Automatically find source files
file(GLOB SOURCES *.cpp)

add_executable(inverter_poller ${SOURCES})

# Modern CMake for thread support
find_package(Threads REQUIRED)
target_link_libraries(inverter_poller PRIVATE Threads::Threads)

# Set output directory structure
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

# Optional: Add install rules for system-wide deployment
install(TARGETS inverter_poller
    RUNTIME DESTINATION bin
)
