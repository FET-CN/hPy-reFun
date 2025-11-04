# reFun 重构为 MicroPython 1.24 User C Module 计划

## 项目概述

将 reFun 纯 Python 包管理器重构为 MicroPython 1.24 user_c_module，核心策略是：
1. **模块名**: `refun`（保持一致）
2. **复用优先**: 尽量使用 MicroPython 已有实现（uhashlib, ujson, VFS 等）
3. **精准优化**: 只对真正的性能瓶颈用 C 实现

**目标平台**: ESP32S3 (240MHz, 512KB SRAM, 8MB PSRAM, 16MB Flash)
**MicroPython 版本**: v1.24.1

---

## 总体策略

### 复用 MicroPython 已有功能

#### **直接使用（无需重新实现）**
- ✅ Hash 计算: 使用 `uhashlib.sha256()`
- ✅ JSON 解析: 使用 `ujson.loads()/dumps()`
- ✅ 文件操作: 使用 MicroPython VFS API
- ✅ 字符串处理: 使用 MicroPython 内置字符串操作

#### **用 C 实现（真正的性能瓶颈）**
- 🔥 版本比较和约束匹配 (version.py) - 高频调用
- 🔥 拓扑排序算法 (resolver.py) - 算法复杂度
- 🔥 路径处理优化 - 字符串拼接频繁

#### **保留 Python 实现（灵活性）**
- 📌 高层 API (manager.py)
- 📌 Patch 管理 (patcher.py)
- 📌 动态加载 (loader.py)
- 📌 异常处理 (exceptions.py)
- 📌 注册表逻辑 (registry.py)
- 📌 文件获取 (fetcher.py)

---

## 阶段 1: 环境搭建和模块骨架 (3-5 天)

### 1.1 开发环境准备
- [ ] 下载 MicroPython v1.24.1 源码
- [ ] 配置 ESP-IDF 编译环境
- [ ] 设置交叉编译工具链 (xtensa-esp32s3)
- [ ] 准备 ESP32S3 测试设备

### 1.2 创建 user_c_module 骨架
- [ ] 创建目录结构
  ```
  micropython/usermods/refun/
  ├── micropython.mk          # 模块编译配置
  ├── micropython.cmake       # CMake 配置
  ├── modrefun.c              # 模块入口
  ├── refun_version.c/.h      # 版本管理（核心）
  ├── refun_resolver.c/.h     # 依赖解析（核心）
  └── refun_utils.c/.h        # 工具函数
  ```

### 1.3 模块注册
- [ ] 实现 `MP_REGISTER_MODULE("refun", ...)`
- [ ] 创建模块初始化函数
- [ ] 定义模块全局对象表

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
- [ ] `refun.Version(major, minor, patch, prerelease=None)`
  - 构造函数

- [ ] `refun.Version.parse("1.2.3-alpha")`
  - 解析版本字符串
  - 返回 Version 对象

- [ ] 比较运算符: `__lt__`, `__le__`, `__eq__`, `__ne__`, `__gt__`, `__ge__`
  - 整数比较，O(1) 时间复杂度

- [ ] `version.to_string()` → "1.2.3"
  - 序列化回字符串

- [ ] `refun.Constraint.parse("^1.2.0")`
  - 解析约束字符串
  - 返回 Constraint 对象

- [ ] `constraint.matches(version)` → bool
  - 快速匹配算法
  - 支持 `^`, `~`, `>=`, `==` 等

#### 优化要点
- [ ] 版本号用 uint16_t 存储（最大 65535）
- [ ] 比较操作无需字符串解析
- [ ] 缓存常用版本对象（如 "1.0.0"）

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

## 阶段 3: Python 层重构 (5-7 天)

### 3.1 更新 lib/refun/version.py
- [ ] 导入 C 版本类
  ```python
  from refun import Version, Constraint
  ```
- [ ] 保留 Python fallback（如果没有 C 模块）
  ```python
  try:
      from refun import Version, Constraint
  except ImportError:
      # 纯 Python 实现 fallback
      class Version:
          ...
  ```

### 3.2 更新 lib/refun/resolver.py
- [ ] 使用 C 拓扑排序
  ```python
  import refun

  def resolve(self, pkg_name, pkg_version):
      dep_graph = self._build_graph(pkg_name, pkg_version)
      return refun.topological_sort(dep_graph)
  ```

### 3.3 更新 lib/refun/hasher.py
- [ ] 确保使用 uhashlib
  ```python
  try:
      import uhashlib as hashlib
  except ImportError:
      import hashlib
  ```

### 3.4 更新 lib/refun/fetcher.py
- [ ] 使用 refun.path_join()
  ```python
  from refun import path_join

  def get_object_path(self, hash_val):
      return path_join(self.storage_dir, hash_val[:2], hash_val[2:])
  ```

### 3.5 保持其他模块不变
- [ ] manager.py - 完全保留
- [ ] loader.py - 完全保留
- [ ] patcher.py - 完全保留
- [ ] exceptions.py - 完全保留
- [ ] registry.py - 只改用 ujson

### 3.6 兼容性测试
- [ ] 运行所有示例
- [ ] 验证功能一致性
- [ ] 测量性能提升

**里程碑**: Python 层无缝集成 C 后端

---

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
- ✅ 提供 Python fallback

---

## 时间线

| 阶段 | 预计时间 | 累计 |
|-----|---------|------|
| 阶段 1: 环境和骨架 | 3-5 天 | 5 天 |
| 阶段 2: 核心 C 实现 | 7-10 天 | 15 天 |
| 阶段 3: Python 重构 | 5-7 天 | 22 天 |
| 阶段 4: 性能测试 | 3-5 天 | 27 天 |
| 阶段 5: 文档发布 | 3-5 天 | 32 天 |

**总计**: **约 5 周**（32 个工作日）

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
