"""
Configuration CMake pour compiler le module C++
"""

cmake_minimum_required(VERSION 3.14)
project(strategy_metrics_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Optimisations
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -DNDEBUG -ffast-math")

# Trouver pybind11
find_package(pybind11 REQUIRED)

# Créer le module Python
pybind11_add_module(strategy_metrics_cpp 
    strategy_metrics.cpp
    bindings.cpp
)

# Headers
target_include_directories(strategy_metrics_cpp PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# Installation dans le répertoire courant
install(TARGETS strategy_metrics_cpp LIBRARY DESTINATION ${CMAKE_CURRENT_SOURCE_DIR}/..)
