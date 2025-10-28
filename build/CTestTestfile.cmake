# CMake generated Testfile for 
# Source directory: /Users/vontariusfalls/testing-and-tuning-market-trading-systems
# Build directory: /Users/vontariusfalls/testing-and-tuning-market-trading-systems/build
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(strategy_sma "/Users/vontariusfalls/testing-and-tuning-market-trading-systems/build/strategy_runner" "sma" "/Users/vontariusfalls/testing-and-tuning-market-trading-systems/data/sample_ohlc.txt")
set_tests_properties(strategy_sma PROPERTIES  _BACKTRACE_TRIPLES "/Users/vontariusfalls/testing-and-tuning-market-trading-systems/CMakeLists.txt;130;add_test;/Users/vontariusfalls/testing-and-tuning-market-trading-systems/CMakeLists.txt;0;")
