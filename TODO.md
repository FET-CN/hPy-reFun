# reFun 重构为 MicroPython 1.24 User C Module 计划

## 项目概述

将 reFun 纯 Python 包管理器重构为 MicroPython 1.24 user_c_module，核心策略是：
1. **模块名**: `refun`（保持一致）
2. **复用优先**: 尽量使用 MicroPython 已有实现（uhashlib, ujson, VFS 等）

**目标平台**: ESP32S3 (240MHz, 512KB SRAM, 8MB PSRAM, 16MB Flash)
**MicroPython 版本**: v1.24.1

---

## 总体策略

### 纯 C 模块实现

**核心原则**: 所有功能在 C 模块中实现，无 Python fallback，无 `lib/` 目录

#### **直接使用 MicroPython 内置模块**
- ✅ Hash 计算: 在 C 中调用 `uhashlib.sha256()`
- ✅ JSON 解析: 在 C 中调用 `ujson.loads()/dumps()`
- ✅ 文件操作: 在 C 中使用 MicroPython VFS API
- ✅ HTTP 下载: 在 C 中调用 `urequests`（如果可用）

#### **C 模块实现的功能**
- 🔥 **核心算法** (已完成)
  - Version/Constraint 类 - 版本比较和约束匹配
  - topological_sort/detect_circular_dep - 依赖解析算法
  - path_join/normalize_path/hash_string - 工具函数

- 🔥 **包管理器功能** (待实现)
  - Registry 类 - 包注册表管理
  - Fetcher 类 - 文件下载和对象存储
  - PatchManager 类 - Monkey Patch 管理
  - PackageLoader 类 - 动态模块加载
  - PackageManager 类 - 统一的高层 API

---

## 阶段 1: 环境搭建和模块骨架 (3-5 天)

### 1.1 开发环境准备
- [ ] 下载 MicroPython v1.24.1 源码
- [ ] 配置 ESP-IDF 编译环境
- [ ] 设置交叉编译工具链 (xtensa-esp32s3)
- [ ] 准备 ESP32S3 测试设备

### 1.2 创建 user_c_module 骨架
- [x] 创建目录结构
  ```
  cmodule/
  ├── micropython.mk          # 模块编译配置
  ├── micropython.cmake       # CMake 配置
  ├── modrefun.c              # 模块入口
  ├── refun_version.c/.h      # 版本管理（核心）
  ├── refun_resolver.c/.h     # 依赖解析（核心）
  ├── refun_utils.c/.h        # 工具函数
  └── README.md               # 编译和使用说明
  ```

### 1.3 模块注册
- [x] 实现 `MP_REGISTER_MODULE("refun", ...)`
- [x] 创建模块初始化函数
- [x] 定义模块全局对象表

### 1.4 编译验证
- [ ] 配置 `USER_C_MODULES` 路径
- [ ] 编译 MicroPython 固件
- [ ] 烧录到 ESP32S3
- [ ] 验证: `import refun`

**里程碑**: 成功编译并导入空 refun 模块

---

## 阶段 2: 核心功能 C 实现 (7-10 天)

### 2.1 版本管理模块 (refun_version.c)

**优先级**: 🔥🔥🔥 最高

#### 为什么用 C 实现
- 版本比较是依赖解析的基础操作，调用频繁
- 纯字符串解析开销大
- C 实现可以用整数直接比较

#### 数据结构
```c
typedef struct {
    mp_obj_base_t base;
    uint16_t major;
    uint16_t minor;
    uint16_t patch;
    mp_obj_t prerelease;  // 字符串或 None
} refun_version_obj_t;

typedef enum {
    OP_EQ,      // ==
    OP_GTE,     // >=
    OP_GT,      // >
    OP_LTE,     // <=
    OP_LT,      // <
    OP_CARET,   // ^
    OP_TILDE    // ~
} constraint_op_t;

typedef struct {
    mp_obj_base_t base;
    constraint_op_t op;
    refun_version_obj_t *version;
} refun_constraint_obj_t;
```

#### 功能实现
- [x] `refun.Version(major, minor, patch, prerelease=None)`
  - 构造函数

- [x] `refun.Version.parse("1.2.3-alpha")`
  - 解析版本字符串
  - 返回 Version 对象

- [x] 比较运算符: `__lt__`, `__le__`, `__eq__`, `__ne__`, `__gt__`, `__ge__`
  - 整数比较，O(1) 时间复杂度

- [x] `version.to_string()` → "1.2.3"
  - 序列化回字符串

- [x] `refun.Constraint.parse("^1.2.0")`
  - 解析约束字符串
  - 返回 Constraint 对象

- [x] `constraint.matches(version)` → bool
  - 快速匹配算法
  - 支持 `^`, `~`, `>=`, `==` 等

#### 优化要点
- [x] 版本号用 uint16_t 存储（最大 65535）
- [x] 比较操作无需字符串解析

#### Python 接口示例
```python
import refun

# 创建版本
v1 = refun.Version.parse("1.2.3")
v2 = refun.Version(1, 3, 0)

# 比较
assert v1 < v2
assert v1 <= refun.Version.parse("2.0.0")

# 约束
constraint = refun.Constraint.parse("^1.2.0")
assert constraint.matches(v1)  # True
assert not constraint.matches(refun.Version.parse("2.0.0"))  # False
```

---

### 2.2 依赖解析器 (refun_resolver.c)

**优先级**: 🔥🔥 高

#### 为什么用 C 实现
- 拓扑排序是图算法，递归调用多
- 涉及大量的列表/集合操作
- C 实现可以减少对象创建开销

#### 数据结构
```c
typedef struct {
    mp_obj_t name;              // 包名（字符串）
    refun_version_obj_t *version;
    mp_obj_t deps;              // dict: {name: Constraint}
} pkg_node_t;

typedef struct {
    pkg_node_t **nodes;
    size_t count;
    size_t capacity;
} dep_graph_t;
```

#### 功能实现
- [ ] `refun.topological_sort(dep_graph)`
  - 输入: 依赖图（dict）
  - 输出: 加载顺序列表
  - 使用 Kahn 算法

- [ ] `refun.detect_circular_dep(dep_graph)`
  - 输入: 依赖图
  - 输出: 循环路径（如果有）或 None
  - 使用 DFS

- [ ] `refun.match_version(available_versions, constraint)`
  - 输入: 版本列表 + 约束
  - 输出: 匹配的版本（最高版本优先）

#### 优化要点
- [ ] 使用栈代替递归（节省栈空间）
- [ ] 邻接表表示图（节省内存）
- [ ] 结果缓存

#### Python 接口示例
```python
import refun

# 依赖图格式
dep_graph = {
    "sensor_tools@1.0.0": {
        "sensor_core": refun.Constraint.parse("^1.0.0")
    },
    "sensor_core@1.0.0": {}
}

# 拓扑排序
order = refun.topological_sort(dep_graph)
# 返回: ["sensor_core@1.0.0", "sensor_tools@1.0.0"]

# 检测循环
circular = refun.detect_circular_dep(dep_graph)
# 返回: None（无循环）
```

---

### 2.3 工具函数 (refun_utils.c)

**优先级**: 🔥 中

#### 功能实现
- [ ] `refun.path_join(*parts)`
  - 快速路径拼接
  - 处理 `/` 和 `\`
  - 避免 Python 字符串拼接开销

- [ ] `refun.normalize_path(path)`
  - 规范化路径
  - 处理 `..` 和 `.`

- [ ] `refun.hash_string(data)`
  - 包装 `uhashlib.sha256()`
  - 返回十六进制字符串
  - 方便调用

#### Python 接口示例
```python
import refun

path = refun.path_join("/storage", "objects", "a1", "b2c3d4")
# 返回: "/storage/objects/a1/b2c3d4"

normalized = refun.normalize_path("/a/b/../c/./d")
# 返回: "/a/c/d"
```

---

### 2.4 复用 MicroPython 已有功能

#### Hash 计算 - 使用 uhashlib
```python
# lib/refun/hasher.py 无需修改太多
import uhashlib

def compute_hash(file_path):
    h = uhashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(4096)
            if not data:
                break
            h.update(data)
    return h.hexdigest()
```

#### JSON 解析 - 使用 ujson
```python
# lib/refun/registry.py
import ujson

def load_registry():
    with open('registry.json', 'r') as f:
        return ujson.load(f)

def save_registry(data):
    with open('registry.json', 'w') as f:
        ujson.dump(data, f)
```

#### 文件操作 - 使用 os
```python
# lib/refun/fetcher.py
import os

def makedirs(path):
    # MicroPython os.makedirs 已经很快
    os.makedirs(path, exist_ok=True)
```

**里程碑**: 核心 C 模块实现完成，其他功能复用 MicroPython

---

## 阶段 3: 包管理器 C 实现 (10-15 天)

**核心原则**: 纯 C 模块实现，无 Python 代码，所有功能从 `import refun` 直接使用

---

### 3.1 DependencyResolver 类 (refun_resolver.c 增强)

**优先级**: 🔥🔥🔥 高

#### 数据结构
```c
typedef struct {
    mp_obj_base_t base;
    mp_obj_t registry;       // Registry 对象引用
    mp_obj_t resolved_cache; // dict: 已解析缓存
} refun_resolver_obj_t;
```

#### 功能实现
- [ ] `DependencyResolver(registry)` - 构造函数
- [ ] `resolver.resolve(pkg_name, version_constraint=None)` - 解析单个包依赖
  - 返回 `{"dependencies": {...}, "load_order": [...]}`
  - 调用已有的 `topological_sort()`
- [ ] `resolver.resolve_all(packages)` - 解析多个包
- [ ] `resolver._find_matching_version(name, constraint)` - 查找匹配版本

#### Python 接口示例
```python
import refun

registry = refun.Registry("storage/registry.json")
resolver = refun.DependencyResolver(registry)

# 解析依赖
result = resolver.resolve("sensor_tools", "^1.0.0")
print(result["load_order"])  # ['sensor_core@1.0.0', 'sensor_tools@1.0.0']
```

---

### 3.2 Registry 类 (refun_registry.c/.h)

**优先级**: 🔥🔥🔥 最高（基础设施）

#### 数据结构
```c
typedef struct {
    mp_obj_base_t base;
    mp_obj_t registry_path;  // 注册表文件路径
    mp_obj_t data;           // dict: {name: {version: metadata}}
    bool dirty;              // 数据是否已修改
} refun_registry_obj_t;
```

#### 功能实现
- [ ] `Registry(registry_path)` - 构造函数
- [ ] `registry.load()` - 从文件加载
  - 使用 VFS API 读取文件
  - 调用 `ujson.loads()` 解析
- [ ] `registry.save()` - 保存到文件
  - 调用 `ujson.dumps()` 序列化
  - 使用 VFS API 写入
- [ ] `registry.add_package(name, version, metadata)` - 注册包
  - metadata 包含: `{path, hash, deps, ...}`
- [ ] `registry.remove_package(name, version)` - 删除包
- [ ] `registry.get_package(name, version)` - 获取包元数据
- [ ] `registry.list_versions(name)` - 列出可用版本
- [ ] `registry.is_installed(name, version)` - 检查是否已安装
- [ ] `registry.get_all_packages()` - 获取所有包

#### 实现要点
- 在 C 中调用 MicroPython 的 `ujson` 模块:
  ```c
  mp_obj_t ujson_module = mp_import_name(MP_QSTR_ujson, ...);
  mp_obj_t loads_func = mp_load_attr(ujson_module, MP_QSTR_loads);
  mp_obj_t data = mp_call_function_1(loads_func, json_str);
  ```
- 使用 MicroPython dict API 操作数据
- 惰性加载：第一次访问时才读取文件

#### Python 接口示例
```python
import refun

registry = refun.Registry("storage/registry.json")
registry.load()

# 注册包
registry.add_package("sensor_core", "1.0.0", {
    "path": "packages/sensor_core/1.0.0",
    "hash": "a1b2c3...",
    "deps": {}
})

# 查询
metadata = registry.get_package("sensor_core", "1.0.0")
versions = registry.list_versions("sensor_core")

registry.save()
```

---

### 3.3 Fetcher 类 (refun_fetcher.c/.h)

**优先级**: 🔥🔥 高

#### 数据结构
```c
typedef struct {
    mp_obj_base_t base;
    mp_obj_t storage_path;  // 对象存储根目录
    mp_obj_t cache_path;    // 缓存目录（可选）
} refun_fetcher_obj_t;
```

#### 功能实现
- [ ] `Fetcher(storage_path, cache_path=None)` - 构造函数
- [ ] `fetcher.fetch(sources, expected_hash)` - 从多个源获取文件
  - 输入: `sources` 列表（URL 或本地路径）
  - 输出: 对象池中的路径
  - 自动验证 Hash
- [ ] `fetcher.get_object_path(hash_value)` - 获取对象路径
  - 使用 `refun.path_join()` 和 `refun.get_hash_path()`
- [ ] `fetcher.has_object(hash_value)` - 检查对象是否存在
- [ ] `fetcher.store_file(src_path, expected_hash)` - 存储本地文件
- [ ] `fetcher._download_http(url, dest_path)` - HTTP 下载（内部）
  - 可选调用 `urequests` 模块
  - 流式下载和哈希验证
- [ ] `fetcher._copy_local(src, dest)` - 本地文件复制（内部）
- [ ] `fetcher._verify_hash(file_path, expected_hash)` - 验证哈希（内部）
  - 调用 `uhashlib.sha256()`

#### 实现要点
- 对象存储路径：`storage_path/hash[:2]/hash[2:]`
- 支持多源 fallback（依次尝试每个源）
- 流式处理，避免大文件占用内存
- HTTP 下载可选（如果 urequests 可用）

#### Python 接口示例
```python
import refun

fetcher = refun.Fetcher("storage/objects", "storage/cache")

# 从本地安装
obj_path = fetcher.store_file("packages/sensor_core/1.0.0", "a1b2c3...")

# 从多个源下载（可选功能）
sources = [
    "http://pkg.example.com/sensor_core-1.0.0.tar",
    "/local/cache/sensor_core-1.0.0.tar"
]
obj_path = fetcher.fetch(sources, "a1b2c3...")

# 检查对象
if fetcher.has_object("a1b2c3..."):
    path = fetcher.get_object_path("a1b2c3...")
```

---

### 3.4 PatchManager 类 (refun_patcher.c/.h)

**优先级**: 🔥 中

#### 数据结构
```c
typedef struct {
    mp_obj_base_t base;
    mp_obj_t patches;  // dict: {target_module: [patch_funcs]}
} refun_patcher_obj_t;
```

#### 功能实现
- [ ] `PatchManager()` - 构造函数
- [ ] `patcher.register_patch(target_module, patch_func)` - 注册 patch
- [ ] `patcher.apply_patches(module_obj)` - 应用 patches
  - 遍历 patch 函数列表
  - 调用每个 patch(target_module)
- [ ] `patcher.load_patch_module(patch_module_path)` - 加载 __patch__.py
  - 动态导入 patch 模块
  - 自动注册其中的 patch 函数
- [ ] `patcher.get_patches(target)` - 获取某模块的 patches

#### 实现要点
- 使用 `mp_load_attr()` 和 `mp_store_attr()` 修改模块属性
- 支持 patch 链（多个 patch 叠加）
- Patch 函数签名：`def patch(target_module): ...`

#### Python 接口示例
```python
import refun

patcher = refun.PatchManager()

# 手动注册 patch
def my_patch(target):
    target.foo = lambda: print("patched!")

patcher.register_patch("some_module", my_patch)

# 加载 __patch__.py
patcher.load_patch_module("packages/my_pkg/1.0.0/__patch__.py")

# 应用 patches
import some_module
patcher.apply_patches(some_module)
```

---

### 3.5 PackageLoader 类 (refun_loader.c/.h)

**优先级**: 🔥🔥 高

#### 数据结构
```c
typedef struct {
    mp_obj_base_t base;
    mp_obj_t registry;       // Registry 对象
    mp_obj_t resolver;       // DependencyResolver 对象
    mp_obj_t patcher;        // PatchManager 对象
    mp_obj_t fetcher;        // Fetcher 对象
    mp_obj_t loaded_cache;   // dict: {(name, version): module}
} refun_loader_obj_t;
```

#### 功能实现
- [ ] `PackageLoader(registry, resolver, patcher, fetcher)` - 构造函数
- [ ] `loader.load(name, version=None)` - 加载包
  1. 检查缓存
  2. 解析依赖 (`resolver.resolve()`)
  3. 按顺序加载依赖
  4. 动态导入主包
  5. 应用 patches
  6. 缓存结果
- [ ] `loader.unload(name, version)` - 卸载包
  - 从 `sys.modules` 移除
  - 清除缓存
- [ ] `loader.is_loaded(name, version)` - 检查是否已加载
- [ ] `loader._import_module(path)` - 动态导入（内部）
  - 添加到 `sys.path`
  - 调用 `__import__()`
- [ ] `loader._load_single(name, version, metadata)` - 加载单个包（内部）

#### 实现要点
- 使用 `mp_builtin___import__()` 动态导入
- 操作 `sys.modules` 和 `sys.path`
- 处理 `__init__.py` 和 `__patch__.py`
- 异常处理（导入失败时回滚）

#### Python 接口示例
```python
import refun

# 初始化加载器
registry = refun.Registry("storage/registry.json")
resolver = refun.DependencyResolver(registry)
patcher = refun.PatchManager()
fetcher = refun.Fetcher("storage/objects")

loader = refun.PackageLoader(registry, resolver, patcher, fetcher)

# 加载包
sensor_tools = loader.load("sensor_tools", "1.0.0")
# 自动加载依赖: sensor_core, math_utils 等

# 使用包
sensor = sensor_tools.MMC5603()
```

---

### 3.6 PackageManager 类 (refun_manager.c/.h)

**优先级**: 🔥🔥🔥 最高（用户主要 API）

#### 数据结构
```c
typedef struct {
    mp_obj_base_t base;
    mp_obj_t storage_path;   // 存储根目录
    mp_obj_t packages_path;  // 包目录
    mp_obj_t registry;       // Registry 对象
    mp_obj_t fetcher;        // Fetcher 对象
    mp_obj_t patcher;        // PatchManager 对象
    mp_obj_t resolver;       // DependencyResolver 对象
    mp_obj_t loader;         // PackageLoader 对象
} refun_manager_obj_t;
```

#### 功能实现
- [ ] `PackageManager(storage_path="storage", packages_path="packages")` - 构造函数
  - 自动初始化所有子模块
  - 确保目录存在
- [ ] `manager.install_local(name, version, pkg_path)` - 从本地安装
  1. 计算包内容 Hash
  2. 存储到对象池 (`fetcher.store_file()`)
  3. 读取依赖信息
  4. 注册到 registry
- [ ] `manager.uninstall(name, version)` - 卸载包
  - 从 registry 移除
  - 可选删除对象文件
- [ ] `manager.load(name, version=None)` - 加载包
  - 委托给 `loader.load()`
- [ ] `manager.run(name, version=None)` - 运行包
  - 加载包
  - 执行 `__main__.py`
- [ ] `manager.list_installed()` - 列出已安装包
  - 返回 `[(name, version), ...]`
- [ ] `manager.list_loaded()` - 列出已加载包
  - 返回当前内存中的包
- [ ] `manager._ensure_directories()` - 确保目录存在（内部）
- [ ] `manager._read_dependencies(pkg_path)` - 读取依赖信息（内部）
  - 读取 `package.json` 或 `__init__.py` 中的元数据

#### 实现要点
- 提供最简洁的用户 API
- 整合所有子模块
- 自动管理生命周期
- 错误处理和回滚

#### Python 接口示例
```python
import refun

# 初始化包管理器
pm = refun.PackageManager()

# 从本地安装
pm.install_local("sensor_core", "1.0.0", "packages/sensor_core/1.0.0")

# 加载并使用
sensor_tools = pm.load("sensor_tools", "1.0.0")

# 运行应用
pm.run("my_app", "1.0.0")

# 列出已安装包
installed = pm.list_installed()
print(installed)  # [('sensor_core', '1.0.0'), ('sensor_tools', '1.0.0'), ...]
```

---

### 3.7 模块注册更新 (modrefun.c)

- [ ] 更新全局符号表，导出所有新类：
  ```c
  static const mp_rom_map_elem_t refun_module_globals_table[] = {
      // 已有
      { MP_ROM_QSTR(MP_QSTR_Version), MP_ROM_PTR(&refun_version_type) },
      { MP_ROM_QSTR(MP_QSTR_Constraint), MP_ROM_PTR(&refun_constraint_type) },
      { MP_ROM_QSTR(MP_QSTR_topological_sort), MP_ROM_PTR(&refun_topological_sort_obj) },
      // ... 其他函数

      // 新增
      { MP_ROM_QSTR(MP_QSTR_Registry), MP_ROM_PTR(&refun_registry_type) },
      { MP_ROM_QSTR(MP_QSTR_DependencyResolver), MP_ROM_PTR(&refun_resolver_type) },
      { MP_ROM_QSTR(MP_QSTR_Fetcher), MP_ROM_PTR(&refun_fetcher_type) },
      { MP_ROM_QSTR(MP_QSTR_PatchManager), MP_ROM_PTR(&refun_patcher_type) },
      { MP_ROM_QSTR(MP_QSTR_PackageLoader), MP_ROM_PTR(&refun_loader_type) },
      { MP_ROM_QSTR(MP_QSTR_PackageManager), MP_ROM_PTR(&refun_manager_type) },
  };
  ```

---

### 3.8 编译配置更新

- [ ] 更新 `micropython.cmake`:
  ```cmake
  set(USERMOD_REFUN_SRC
      ${CMAKE_CURRENT_LIST_DIR}/src/modrefun.c
      ${CMAKE_CURRENT_LIST_DIR}/src/refun_version.c
      ${CMAKE_CURRENT_LIST_DIR}/src/refun_resolver.c
      ${CMAKE_CURRENT_LIST_DIR}/src/refun_utils.c
      ${CMAKE_CURRENT_LIST_DIR}/src/refun_registry.c
      ${CMAKE_CURRENT_LIST_DIR}/src/refun_fetcher.c
      ${CMAKE_CURRENT_LIST_DIR}/src/refun_patcher.c
      ${CMAKE_CURRENT_LIST_DIR}/src/refun_loader.c
      ${CMAKE_CURRENT_LIST_DIR}/src/refun_manager.c
  )
  ```

- [ ] 同步更新 `micropython.mk`

---

### 3.9 C 代码量估算

| 模块 | 估算行数 | 复杂度 |
|------|---------|--------|
| refun_resolver.c（增强）| +300 | 中 |
| refun_registry.c | 550 | 中 |
| refun_fetcher.c | 700 | 高（HTTP下载）|
| refun_patcher.c | 350 | 中 |
| refun_loader.c | 600 | 高（动态导入）|
| refun_manager.c | 450 | 中 |
| modrefun.c（更新）| +100 | 低 |
| **总计** | **~3050 行 C** | |

---

**里程碑**: 纯 C 模块实现完整包管理器，无需任何 Python 代码

## 阶段 4: 性能优化和测试 (3-5 天)

### 4.1 性能基准测试

#### 版本比较性能
- [ ] 测试场景: 比较 1000 次
  ```python
  # 纯 Python vs C
  v1 = Version.parse("1.2.3")
  v2 = Version.parse("1.3.0")
  for _ in range(1000):
      result = v1 < v2
  ```
- [ ] 目标: **5-10x 提升**

#### 依赖解析性能
- [ ] 测试场景: 解析 50 个包的依赖
- [ ] 目标: **3-5x 提升**

#### 整体加载性能
- [ ] 测试场景: 加载 10 个包
- [ ] 目标: **2-3x 提升**

### 4.2 内存测试
- [ ] 测量 C 模块内存占用
  ```python
  import gc
  gc.collect()
  before = gc.mem_free()
  import refun
  after = gc.mem_free()
  print(f"C module uses: {before - after} bytes")
  ```
- [ ] 目标: **<20KB**

### 4.3 功能测试
- [ ] 所有原有测试通过
- [ ] 边界情况测试
- [ ] 错误处理测试

**里程碑**: 性能和内存目标达成

---

## 阶段 5: 文档和发布 (3-5 天)

### 5.1 编译文档
- [ ] 创建 `docs/BUILDING.md`
  - 环境搭建步骤
  - 编译命令
  - 烧录指南

### 5.2 API 文档更新
- [ ] 更新 `API.md`
  - 新增 C 模块 API
  - 标注性能提升

### 5.3 迁移指南
- [ ] 创建 `docs/MIGRATION.md`
  - 从纯 Python 迁移步骤
  - 兼容性说明
  - Fallback 机制

### 5.4 发布
- [ ] 创建发布分支 `v1.0.0-c`
- [ ] 提供预编译固件
- [ ] 发布 Release Notes

**里程碑**: 项目发布

---

## 技术决策说明

### 为什么不重新实现 Hash？
- MicroPython 的 `uhashlib.sha256()` 已经是 C 实现
- 在 ESP32S3 上已经很快（可能使用硬件加速）
- 重新实现无法带来显著提升

### 为什么不重新实现 JSON？
- `ujson` 是 MicroPython 优化的 C 实现
- JSON 解析不是性能瓶颈（只在加载注册表时使用）
- 重新实现反而增加维护成本

### 为什么不重新实现文件操作？
- MicroPython VFS 已经是高效的 C 实现
- 直接访问 Flash 需要深入 ESP-IDF，复杂度高
- 收益不明显

### 重点优化的理由

#### 版本比较
- **调用频率**: 依赖解析时每个包都要比较版本
- **当前瓶颈**: 字符串解析 "1.2.3" → 整数比较
- **优化空间**: 预解析版本为整数，比较时 O(1)

#### 拓扑排序
- **算法复杂度**: O(V+E)，涉及大量图遍历
- **当前瓶颈**: Python 列表/字典操作开销大
- **优化空间**: C 数组和指针操作，减少对象创建

---

## 成功指标

### 性能指标
- ✅ 版本比较速度提升 **5-10x**
- ✅ 依赖解析速度提升 **3-5x**
- ✅ 整体加载速度提升 **2-3x**

### 内存指标
- ✅ C 模块占用 **<20KB SRAM**
- ✅ 固件增加 **<30KB**

### 质量指标
- ✅ 所有原有测试通过
- ✅ 100% API 兼容
- ✅ 纯 C 模块实现（无 Python 代码依赖）

---

## 时间线

| 阶段 1: 环境和骨架 | 3-5 天 | 5 天 |
| 阶段 2: 核心 C 实现 | 7-10 天 | 15 天 |
| 阶段 3: 包管理器 C 实现 | 10-15 天 | 30 天 |
| 阶段 4: 性能测试 | 3-5 天 | 35 天 |
| 阶段 5: 文档发布 | 3-5 天 | 40 天 |

**总计**: **约 8 周**（40 个工作日）
---

## 资源参考

### MicroPython 官方文档
- [C Modules 开发指南](https://docs.micropython.org/en/latest/develop/cmodules.html)
- [MicroPython C API](https://docs.micropython.org/en/latest/develop/library.html)

### 参考实现
- `micropython/py/objtype.c` - 类型系统
- `micropython/py/objint.c` - 整数对象
- `micropython/extmod/modujson.c` - ujson 实现

### 工具链
- ESP-IDF v5.x
- xtensa-esp32s3-elf-gcc
- esptool.py

---

## 附录: C 模块代码量估算

| 模块 | 估算行数 | 说明 |
|-----|---------|------|
| modrefun.c | 150 | 模块入口 + 对象表 |
| refun_version.c | 400 | Version + Constraint 类 |
| refun_resolver.c | 500 | 拓扑排序 + 循环检测 |
| refun_utils.c | 150 | 路径处理工具 |
| **总计** | **~1200 行 C** | 精简实现 |

相比原计划的 2400 行，代码量减半，维护成本大幅降低。
