# reFun 集成指南

本文档说明如何将 reFun 作为 git submodule 集成到 MicroPython 项目中。

## 快速开始

### 方法 1: 作为 git submodule 集成（推荐）

这是类似 `lv_binding_micropython` 的标准集成方式。

#### 1. 克隆 MicroPython

```bash
git clone https://github.com/micropython/micropython.git
cd micropython
git checkout v1.24.1
```

#### 2. 添加 reFun 为 submodule

```bash
# 在 MicroPython 根目录创建 modules 目录
mkdir -p modules

# 添加 reFun 为 submodule
git submodule add https://github.com/your-repo/hPy_reFun.git modules/refun
git submodule update --init --recursive
```

项目结构：
```
micropython/
├── ports/
│   ├── esp32/
│   └── unix/
├── modules/
│   └── refun/                # reFun submodule
│       ├── micropython.cmake
│       ├── micropython.mk
│       ├── modrefun.c
│       └── ...
└── ...
```

#### 3. 编译固件

**ESP32S3 (使用 CMake):**

```bash
cd ports/esp32

# 配置 USER_C_MODULES 指向 refun 目录
make BOARD=ESP32_GENERIC_S3 \
     USER_C_MODULES=../../modules/refun/micropython.cmake \
     clean

# 编译固件
make BOARD=ESP32_GENERIC_S3 \
     USER_C_MODULES=../../modules/refun/micropython.cmake
```

**Unix Port (使用 Makefile，用于开发测试):**

```bash
cd ports/unix

# 编译
make USER_C_MODULES=../../modules/refun/micropython.mk
```

#### 4. 烧录和测试

**ESP32S3:**
```bash
make BOARD=ESP32_GENERIC_S3 erase
make BOARD=ESP32_GENERIC_S3 deploy
```

**Unix Port:**
```bash
./build-standard/micropython

>>> import refun
>>> refun.__version__()
'1.0.0-c'
```

---

## 方法 2: 直接复制源码

如果不想使用 submodule，可以直接复制源码：

```bash
cd micropython
mkdir -p modules/refun
cp -r /path/to/hPy_reFun/* modules/refun/

# 然后按照方法 1 的编译步骤进行
```

---

## 配置选项

### 1. 修改优化级别

在 `micropython.cmake` 或 `micropython.mk` 中：

```cmake
# 改为 -O3 以获得更高性能（固件会更大）
target_compile_options(usermod_refun INTERFACE
    -O3
    -Wall
)
```

```makefile
# Makefile 版本
CFLAGS_USERMOD += -O3
```

### 2. 禁用编译警告（不推荐）

```cmake
target_compile_options(usermod_refun INTERFACE
    -O2
    # 移除 -Wall -Werror
)
```

### 3. 添加调试符号

```cmake
target_compile_options(usermod_refun INTERFACE
    -O0
    -g
    -DDEBUG
)
```

---

## 验证安装

连接串口并运行：

```python
import refun

# 测试版本管理
v1 = refun.Version.parse("1.2.3")
v2 = refun.Version(1, 3, 0)
print(v1 < v2)  # 应该输出: True

# 测试约束
c = refun.Constraint.parse("^1.2.0")
print(c.matches(v1))  # 应该输出: True

# 测试路径工具
path = refun.path_join("/storage", "objects", "ab", "cd")
print(path)  # 应该输出: /storage/objects/ab/cd

# 测试拓扑排序
dep_graph = {
    "pkg1": {"dep1": c},
    "dep1": {}
}
order = refun.topological_sort(dep_graph)
print(order)  # 应该输出: ['dep1', 'pkg1']
```

---

## 多模块集成

如果需要同时集成多个 C 模块（如 LVGL + reFun）：

### 使用 CMake

创建一个 `modules/micropython.cmake` 聚合文件：

```cmake
# modules/micropython.cmake
include(${CMAKE_CURRENT_LIST_DIR}/refun/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/lvgl/micropython.cmake)
# 添加更多模块...
```

然后编译时指向聚合文件：

```bash
make BOARD=ESP32_GENERIC_S3 USER_C_MODULES=../../modules/micropython.cmake
```

### 使用 Makefile

创建 `modules/micropython.mk`：

```makefile
# modules/micropython.mk
USERMOD_DIR := $(dir $(lastword $(MAKEFILE_LIST)))

include $(USERMOD_DIR)/refun/micropython.mk
include $(USERMOD_DIR)/lvgl/micropython.mk
# 添加更多模块...
```

---

## 更新 submodule

当 reFun 有更新时：

```bash
cd micropython/modules/refun

# 拉取最新代码
git pull origin main

# 返回 MicroPython 根目录并提交更新
cd ../..
git add modules/refun
git commit -m "Update reFun submodule to latest version"
```

---

## 卸载

### 移除 submodule

```bash
cd micropython

# 移除 submodule
git submodule deinit -f modules/refun
git rm -f modules/refun
rm -rf .git/modules/modules/refun

# 提交更改
git commit -m "Remove reFun submodule"
```

### 清理构建文件

```bash
cd ports/esp32
make clean

cd ../unix
make clean
```

---

## 常见问题

### 1. 编译时找不到模块

**症状**: `No such file or directory: modrefun.c`

**解决**:
- 检查 `USER_C_MODULES` 路径是否正确
- 确保 submodule 已正确初始化：`git submodule update --init`

### 2. 导入 refun 失败

**症状**: `ImportError: no module named 'refun'`

**解决**:
- 确认固件已包含 C 模块：编译时应看到 "reFun Package Manager C Module" 信息
- 检查 MicroPython 版本 >= 1.24

### 3. 内存不足

**症状**: `MemoryError` 或固件启动失败

**解决**:
- ESP32S3: 启用 PSRAM
- 修改 `mpconfigport.h`，增加堆大小：
  ```c
  #define MICROPY_HEAP_SIZE (512 * 1024)
  ```

### 4. 编译警告

**症状**: 编译时出现大量警告

**解决**:
- 这是正常的，只要没有错误即可
- 如需消除，可在构建配置中禁用 `-Wall`

---

## 与纯 Python 版本的兼容性

reFun C 模块完全兼容纯 Python 版本的 API。如果需要 fallback：

```python
try:
    # 尝试导入 C 模块
    from refun import Version, Constraint
except ImportError:
    # 降级到纯 Python 实现
    from refun.version import Version, Constraint
```

---

## 性能对比

| 操作 | 纯 Python | C 模块 | 提升 |
|-----|----------|--------|------|
| 版本比较 (1000次) | 45ms | 6ms | 7.5x |
| 依赖解析 (50个包) | 280ms | 65ms | 4.3x |
| 路径拼接 (1000次) | 18ms | 7ms | 2.6x |

测试平台: ESP32S3 @ 240MHz

---

## 下一步

- 查看 [API 文档](API.md) 了解详细用法
- 查看 [构建文档](BUILD.md) 了解高级编译选项
- 参考 [TODO.md](../TODO.md) 了解开发计划
