# reFun MicroPython 用户 C 模块 Makefile
#
# 当作为 git 子模块添加到 MicroPython ports 的 USER_C_MODULES 目录下时
# 此文件会被自动发现
#
# 使用方法:
#   cd micropython/ports/unix
#   git submodule add <repo-url> ../../modules/refun
#   make USER_C_MODULES=../../modules all

# 获取此 makefile 的目录
REFUN_MOD_DIR := $(USERMOD_DIR)

$(info )
$(info ==============================================)
$(info reFun Package Manager C Module)
$(info Version: 1.0.0)
$(info Location: $(REFUN_MOD_DIR))
$(info ==============================================)
$(info )

# 将 src/ 目录中的所有 C 源文件添加到构建中
SRC_USERMOD += $(REFUN_MOD_DIR)/src/modrefun.c
SRC_USERMOD += $(REFUN_MOD_DIR)/src/refun_version.c
SRC_USERMOD += $(REFUN_MOD_DIR)/src/refun_resolver.c
SRC_USERMOD += $(REFUN_MOD_DIR)/src/refun_utils.c

# 添加包含目录（src/ 用于头文件）
CFLAGS_USERMOD += -I$(REFUN_MOD_DIR)/src

# 编译器优化和警告选项
CFLAGS_USERMOD += -O2
CFLAGS_USERMOD += -Wall
CFLAGS_USERMOD += -Werror=implicit-function-declaration
