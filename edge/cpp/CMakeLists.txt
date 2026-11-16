cmake_minimum_required(VERSION 3.16)
project(rfmon_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# release build by default, so it's optimized for speed
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

add_executable(iq_convert src/iq_convert.cpp)

# treat every warning as an error
target_compile_options(iq_convert PRIVATE -Wall -Wextra -Wpedantic -Werror)