cmake_minimum_required(VERSION 3.16)

project(market_strategies LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(BUILD_ALGOS "Build original C++ algorithm programs" ON)
option(BUILD_STRATEGY_FRAMEWORK "Build simple strategy runner scaffold" ON)
option(BUILD_TESTING "Enable CTest smoke tests" ON)
option(BUILD_TOOLS "Build helper tools (data converters)" ON)

if(BUILD_ALGOS)
  # Build one executable per subdirectory that contains .CPP files.
  file(GLOB children RELATIVE ${CMAKE_SOURCE_DIR} "*")
  foreach(child IN LISTS children)
    if(IS_DIRECTORY "${CMAKE_SOURCE_DIR}/${child}")
      file(GLOB alg_sources RELATIVE ${CMAKE_SOURCE_DIR} "${child}/*.[cC][pP][pP]")
      if(alg_sources)
        # Target name = directory name (assumed valid identifier)
        set(tgt ${child})
        add_executable(${tgt})
        target_sources(${tgt} PRIVATE ${alg_sources})
        target_include_directories(${tgt} PRIVATE
          ${CMAKE_SOURCE_DIR}/compat
          ${CMAKE_SOURCE_DIR}/${child}
        )
        if(NOT MSVC)
          # Force-include portability shims (pass as separate args)
          target_compile_options(${tgt} PRIVATE -include ${CMAKE_SOURCE_DIR}/compat/platform_compat.h)
          if(UNIX AND NOT APPLE)
            target_link_libraries(${tgt} PRIVATE m)
          endif()
        endif()
      endif()
    endif()
  endforeach()
endif()

if(BUILD_STRATEGY_FRAMEWORK)
  add_executable(strategy_runner
    framework/runner.cpp
  )
  target_include_directories(strategy_runner PRIVATE ${CMAKE_SOURCE_DIR}/framework)
  if(NOT MSVC)
    target_compile_options(strategy_runner PRIVATE -include ${CMAKE_SOURCE_DIR}/compat/platform_compat.h)
    if(UNIX AND NOT APPLE)
      target_link_libraries(strategy_runner PRIVATE m)
    endif()
  endif()

  # Framework library (without main function)
  add_library(strategy_framework STATIC
    framework/sma_strategy.cpp
    framework/strategy_factory.cpp
    framework/rsi_strategy.cpp
    framework/macd_strategy.cpp
  )
  target_include_directories(strategy_framework PRIVATE ${CMAKE_SOURCE_DIR}/framework)
  target_link_libraries(strategy_framework sqlite3)
  if(NOT MSVC)
    target_compile_options(strategy_framework PRIVATE -include ${CMAKE_SOURCE_DIR}/compat/platform_compat.h)
    if(UNIX AND NOT APPLE)
      target_link_libraries(strategy_framework PRIVATE m)
    endif()
  endif()

  target_link_libraries(strategy_runner strategy_framework sqlite3)

  # Strategy testing framework
  add_executable(strategy_batch_tester
    framework/strategy_batch_tester.cpp
    framework/strategy_tester.cpp
    framework/strategy_factory.cpp
    framework/strategy_registry.cpp
  )
  target_include_directories(strategy_batch_tester PRIVATE ${CMAKE_SOURCE_DIR}/framework)
  target_link_libraries(strategy_batch_tester strategy_framework sqlite3)
  if(NOT MSVC)
    target_compile_options(strategy_batch_tester PRIVATE -include ${CMAKE_SOURCE_DIR}/compat/platform_compat.h)
    if(UNIX AND NOT APPLE)
      target_link_libraries(strategy_batch_tester PRIVATE m)
    endif()
  endif()

  # Framework executable (for testing framework components)
  add_executable(framework
    framework/runner.cpp
  )
  target_include_directories(framework PRIVATE ${CMAKE_SOURCE_DIR}/framework)
  target_link_libraries(framework strategy_framework sqlite3)
  if(NOT MSVC)
    target_compile_options(framework PRIVATE -include ${CMAKE_SOURCE_DIR}/compat/platform_compat.h)
    if(UNIX AND NOT APPLE)
      target_link_libraries(framework PRIVATE m)
    endif()
  endif()
endif()

if(BUILD_TOOLS)
  add_executable(binance_to_txt tools/binance_to_txt.cpp)
  target_include_directories(binance_to_txt PRIVATE ${CMAKE_SOURCE_DIR}/compat)
  if(NOT MSVC)
    target_compile_options(binance_to_txt PRIVATE -include ${CMAKE_SOURCE_DIR}/compat/platform_compat.h)
    if(UNIX AND NOT APPLE)
      target_link_libraries(binance_to_txt PRIVATE m)
    endif()
  endif()
endif()

if(BUILD_TESTING)
  include(CTest)
  if(BUILD_ALGOS)
    # Smoke tests with tiny inputs/iterations to validate executables run
    if(TARGET DRAWDOWN)
      add_test(NAME drawdown_smoke
        COMMAND DRAWDOWN 100 50 0.5 0.9 50 50 1)
    endif()
    if(TARGET MCPT_BARS)
      add_test(NAME mcpt_bars_smoke
        COMMAND MCPT_BARS 10 2 ${CMAKE_SOURCE_DIR}/data/sample_ohlc.txt)
    endif()
    if(TARGET CD_MA)
      add_test(NAME cd_ma_smoke
        COMMAND CD_MA 2 2 2 0.5 ${CMAKE_SOURCE_DIR}/data/sample_close.txt)
    endif()
  endif()
  if(TARGET strategy_runner)
    add_test(NAME strategy_sma
      COMMAND strategy_runner sma ${CMAKE_SOURCE_DIR}/data/sample_ohlc.txt)
  endif()
endif()
