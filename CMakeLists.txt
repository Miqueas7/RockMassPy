cmake_minimum_required(VERSION 3.20)
project(rockmasspy
    VERSION 0.1.0
    DESCRIPTION "Rock mass classifications, Hoek-Brown strength and mining geomechanics"
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Núcleo header-only (interfaz)
add_library(rockmasspy_core INTERFACE)
target_include_directories(rockmasspy_core INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_compile_features(rockmasspy_core INTERFACE cxx_std_20)

# Bindings Python (nanobind vía scikit-build-core)
option(ROCKMASSPY_BUILD_PYTHON "Build Python bindings" ON)

if(ROCKMASSPY_BUILD_PYTHON)
    find_package(Python 3.10
        REQUIRED COMPONENTS Interpreter Development.Module
        OPTIONAL_COMPONENTS Development.SABIModule
    )

    execute_process(
        COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
        OUTPUT_STRIP_TRAILING_WHITESPACE
        OUTPUT_VARIABLE NB_DIR
        RESULT_VARIABLE NB_RESULT
    )

    if(NB_RESULT EQUAL 0 AND EXISTS "${NB_DIR}")
        list(APPEND CMAKE_PREFIX_PATH "${NB_DIR}")
        find_package(nanobind CONFIG REQUIRED)

        nanobind_add_module(_rockmasspy_core
            STABLE_ABI
            NB_STATIC
            bindings/bindings.cpp
        )
        target_link_libraries(_rockmasspy_core PRIVATE rockmasspy_core)

        install(TARGETS _rockmasspy_core
            LIBRARY DESTINATION rockmasspy
            RUNTIME DESTINATION rockmasspy
            ARCHIVE DESTINATION rockmasspy
        )

        # Stubs .pyi para editores y mypy; se generan al instalar (la ruta es relativa al prefijo del wheel).
        # python/rockmasspy/py.typed marca el paquete como tipado.
        nanobind_add_stub(_rockmasspy_core_stub
            MODULE _rockmasspy_core
            OUTPUT rockmasspy/_rockmasspy_core.pyi
            PYTHON_PATH rockmasspy
            INSTALL_TIME
        )
    else()
        message(FATAL_ERROR
            "nanobind not found, so the Python package would be incomplete.\n"
            "Install with: pip install nanobind"
        )
    endif()
endif()

# Pruebas C++ (Google Test)
option(ROCKMASSPY_BUILD_TESTS "Build C++ unit tests" OFF)

if(ROCKMASSPY_BUILD_TESTS)
    enable_testing()

    include(FetchContent)
    FetchContent_Declare(
        googletest
        URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
    )
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)

    # Cada tarea agrega aquí su archivo de pruebas
    add_executable(rockmasspy_tests
        tests/cpp/test_validation.cpp
        tests/cpp/test_rqd.cpp
        tests/cpp/test_rmr89.cpp
        tests/cpp/test_rmr76.cpp
        tests/cpp/test_rmr14.cpp
        tests/cpp/test_q_system.cpp
        tests/cpp/test_q_support.cpp
        tests/cpp/test_mathews.cpp
        tests/cpp/test_mrmr.cpp
        tests/cpp/test_gsi.cpp
        tests/cpp/test_correlations.cpp
        tests/cpp/test_hoek_brown.cpp
        tests/cpp/test_stereonet.cpp
    )
    target_link_libraries(rockmasspy_tests PRIVATE
        rockmasspy_core
        GTest::gtest_main
    )

    include(GoogleTest)
    gtest_discover_tests(rockmasspy_tests)
endif()
