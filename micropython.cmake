# reFun MicroPython 用户 C 模块
#
# 当作为 git 子模块添加到 MicroPython ports 的 USER_C_MODULES 目录下时
# 此文件会被自动发现
#
# 使用方法:
#   cd micropython/ports/esp32
#   git submodule add <repo-url> ../../modules/refun
#   make BOARD=ESP32_GENERIC_S3 USER_C_MODULES=../../modules/micropython.cmake

# 模块信息
set(REFUN_MOD_DIR ${CMAKE_CURRENT_LIST_DIR})
message(STATUS "")
message(STATUS "==============================================")
message(STATUS "reFun Package Manager C Module")
message(STATUS "Version: 1.0.0")
message(STATUS "Location: ${REFUN_MOD_DIR}")
message(STATUS "==============================================")
message(STATUS "")

# 为模块创建 INTERFACE 库
add_library(usermod_refun INTERFACE)

# 添加 src/ 目录中的所有 C 源文件
target_sources(usermod_refun INTERFACE
    ${REFUN_MOD_DIR}/src/modrefun.c
    ${REFUN_MOD_DIR}/src/refun_version.c
    ${REFUN_MOD_DIR}/src/refun_resolver.c
    ${REFUN_MOD_DIR}/src/refun_utils.c
    ${REFUN_MOD_DIR}/src/refun_registry.c
    ${REFUN_MOD_DIR}/src/refun_fetcher.c
    ${REFUN_MOD_DIR}/src/refun_patcher.c
    ${REFUN_MOD_DIR}/src/refun_loader.c
    ${REFUN_MOD_DIR}/src/refun_manager.c
)

# 添加包含目录（src/ 用于头文件）
target_include_directories(usermod_refun INTERFACE
    ${REFUN_MOD_DIR}/src
)

# 编译器选项（针对性能优化）
target_compile_options(usermod_refun INTERFACE
    -O2
    -Wall
    -Werror=implicit-function-declaration
)

# 链接到主 usermod 目标
target_link_libraries(usermod INTERFACE usermod_refun)
