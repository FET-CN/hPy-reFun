# reFun C 模块 API 文档

本文档详细说明 reFun C 模块提供的所有 API。

## 模块导入

```python
import refun
```

---

## 版本管理 API

### Version 类

表示语义化版本号（SemVer）。

#### 构造函数

```python
Version(major, minor, patch, prerelease=None)
```

**参数**:
- `major` (int): 主版本号
- `minor` (int): 次版本号
- `patch` (int): 补丁版本号
- `prerelease` (str, optional): 预发布标识，如 "alpha", "beta.1"

**示例**:
```python
v = refun.Version(1, 2, 3)
v_pre = refun.Version(1, 0, 0, "alpha")
```

#### Version.parse()

从字符串解析版本号。

```python
Version.parse(version_string) -> Version
```

**参数**:
- `version_string` (str): 版本字符串，格式: "major.minor.patch" 或 "major.minor.patch-prerelease"

**返回**: `Version` 对象

**异常**:
- `ValueError`: 格式不正确

**示例**:
```python
v1 = refun.Version.parse("1.2.3")
v2 = refun.Version.parse("2.0.0-beta.1")
```

#### to_string()

将版本转换为字符串。

```python
version.to_string() -> str
```

**返回**: 版本字符串

**示例**:
```python
v = refun.Version(1, 2, 3)
print(v.to_string())  # "1.2.3"
```

#### 比较运算符

Version 对象支持所有比较运算符：

```python
v1 < v2   # 小于
v1 <= v2  # 小于等于
v1 == v2  # 等于
v1 != v2  # 不等于
v1 > v2   # 大于
v1 >= v2  # 大于等于
```

**比较规则**:
1. 首先比较 major, minor, patch（数值比较）
2. 预发布版本 < 正式版本
3. 预发布版本之间按字符串字典序比较

**示例**:
```python
v1 = refun.Version.parse("1.2.3")
v2 = refun.Version.parse("1.3.0")
v3 = refun.Version.parse("2.0.0-alpha")
v4 = refun.Version.parse("2.0.0")

print(v1 < v2)   # True
print(v3 < v4)   # True (预发布 < 正式)
print(v2 < v3)   # True (1.3.0 < 2.0.0-alpha)
```

---

### Constraint 类

表示版本约束条件。

#### Constraint.parse()

从字符串解析约束。

```python
Constraint.parse(constraint_string) -> Constraint
```

**参数**:
- `constraint_string` (str): 约束字符串

**支持的运算符**:
- `==`: 精确匹配
- `>=`: 大于等于
- `>`: 大于
- `<=`: 小于等于
- `<`: 小于
- `^`: Caret (兼容版本)
- `~`: Tilde (近似版本)

**返回**: `Constraint` 对象

**异常**:
- `ValueError`: 格式不正确

**示例**:
```python
c1 = refun.Constraint.parse("^1.2.0")
c2 = refun.Constraint.parse(">=2.0.0")
c3 = refun.Constraint.parse("~1.2.3")
```

#### matches()

检查版本是否满足约束。

```python
constraint.matches(version) -> bool
```

**参数**:
- `version` (Version): 待检查的版本

**返回**: 是否匹配

**示例**:
```python
c = refun.Constraint.parse("^1.2.0")
v1 = refun.Version.parse("1.2.5")
v2 = refun.Version.parse("2.0.0")

print(c.matches(v1))  # True (1.2.5 符合 ^1.2.0)
print(c.matches(v2))  # False (2.0.0 不符合 ^1.2.0)
```

#### 约束规则详解

**Caret (^)**:
- `^1.2.3` 匹配 `>=1.2.3 and <2.0.0`
- `^0.2.3` 匹配 `>=0.2.3 and <0.3.0` (major=0 时特殊处理)
- `^0.0.3` 匹配 `==0.0.3` (major=0, minor=0 时)

**Tilde (~)**:
- `~1.2.3` 匹配 `>=1.2.3 and <1.3.0`
- `~1.2` 匹配 `>=1.2.0 and <1.3.0`

**示例**:
```python
# Caret 约束
c = refun.Constraint.parse("^1.2.0")
print(c.matches(refun.Version.parse("1.2.0")))  # True
print(c.matches(refun.Version.parse("1.9.9")))  # True
print(c.matches(refun.Version.parse("2.0.0")))  # False

# Tilde 约束
c = refun.Constraint.parse("~1.2.3")
print(c.matches(refun.Version.parse("1.2.3")))  # True
print(c.matches(refun.Version.parse("1.2.9")))  # True
print(c.matches(refun.Version.parse("1.3.0")))  # False
```

---

## 依赖解析 API

### topological_sort()

对依赖图进行拓扑排序，返回正确的加载顺序。

```python
refun.topological_sort(dep_graph) -> list
```

**参数**:
- `dep_graph` (dict): 依赖图，格式: `{pkg_name: {dep_name: Constraint, ...}, ...}`

**返回**: 包名列表，按加载顺序排序

**异常**:
- `ValueError`: 存在循环依赖
- `TypeError`: 输入格式不正确

**算法**: Kahn 算法，时间复杂度 O(V+E)

**示例**:
```python
# 定义依赖图
dep_graph = {
    "app@1.0.0": {
        "lib_a": refun.Constraint.parse("^1.0.0"),
        "lib_b": refun.Constraint.parse("^2.0.0")
    },
    "lib_a@1.0.0": {
        "lib_c": refun.Constraint.parse("^1.0.0")
    },
    "lib_b@2.0.0": {
        "lib_c": refun.Constraint.parse("^1.0.0")
    },
    "lib_c@1.0.0": {}
}

# 拓扑排序
order = refun.topological_sort(dep_graph)
print(order)
# 输出: ["lib_c@1.0.0", "lib_a@1.0.0", "lib_b@2.0.0", "app@1.0.0"]
# 或: ["lib_c@1.0.0", "lib_b@2.0.0", "lib_a@1.0.0", "app@1.0.0"]
# (可能有多个有效顺序)
```

---

### detect_circular_dep()

检测依赖图中的循环依赖。

```python
refun.detect_circular_dep(dep_graph) -> list | None
```

**参数**:
- `dep_graph` (dict): 依赖图

**返回**:
- `None`: 无循环依赖
- `list`: 循环路径，包含形成环的包名

**算法**: 深度优先搜索 (DFS)

**示例**:
```python
# 无循环依赖
dep_graph = {
    "app": {"lib_a": c1},
    "lib_a": {"lib_b": c2},
    "lib_b": {}
}
result = refun.detect_circular_dep(dep_graph)
print(result)  # None

# 有循环依赖
dep_graph = {
    "app": {"lib_a": c1},
    "lib_a": {"lib_b": c2},
    "lib_b": {"lib_a": c3}  # 循环!
}
result = refun.detect_circular_dep(dep_graph)
print(result)  # ["lib_a", "lib_b", "lib_a"]
```

---

### match_version()

从可用版本列表中找到最佳匹配版本。

```python
refun.match_version(available_versions, constraint) -> Version | None
```

**参数**:
- `available_versions` (list): 可用版本列表
- `constraint` (Constraint): 版本约束

**返回**:
- `Version`: 最高的匹配版本
- `None`: 无匹配版本

**匹配规则**: 返回满足约束的最高版本

**示例**:
```python
# 准备可用版本
versions = [
    refun.Version.parse("1.0.0"),
    refun.Version.parse("1.2.0"),
    refun.Version.parse("1.5.0"),
    refun.Version.parse("2.0.0"),
]

# 匹配 ^1.0.0
c = refun.Constraint.parse("^1.0.0")
best = refun.match_version(versions, c)
print(best.to_string())  # "1.5.0" (最高的 1.x 版本)

# 匹配 >=2.0.0
c = refun.Constraint.parse(">=2.0.0")
best = refun.match_version(versions, c)
print(best.to_string())  # "2.0.0"

# 无匹配
c = refun.Constraint.parse("^3.0.0")
best = refun.match_version(versions, c)
print(best)  # None
```

---

## 工具函数 API

### path_join()

高效拼接路径。

```python
refun.path_join(*parts) -> str
```

**参数**:
- `*parts`: 路径组件（可变参数）

**返回**: 拼接后的路径

**特点**:
- 自动处理 `/` 分隔符
- 移除重复的 `/`
- 跳过空字符串

**示例**:
```python
path = refun.path_join("/storage", "objects", "ab", "cdef")
print(path)  # "/storage/objects/ab/cdef"

path = refun.path_join("/a/", "/b", "c/")
print(path)  # "/a/b/c"

path = refun.path_join("", "a", "", "b")
print(path)  # "a/b"
```

---

### normalize_path()

规范化路径，解析 `.` 和 `..`。

```python
refun.normalize_path(path) -> str
```

**参数**:
- `path` (str): 待规范化的路径

**返回**: 规范化后的路径

**功能**:
- 解析 `.` (当前目录)
- 解析 `..` (上级目录)
- 移除多余的 `/`

**示例**:
```python
path = refun.normalize_path("/a/b/../c/./d")
print(path)  # "/a/c/d"

path = refun.normalize_path("a/b/c/../../d")
print(path)  # "a/d"

path = refun.normalize_path("/a/b/../../..")
print(path)  # "/" (绝对路径不会超出根目录)

path = refun.normalize_path(".")
print(path)  # "."
```

---

### hash_string()

计算字符串的 SHA256 Hash值。

```python
refun.hash_string(data) -> str
```

**参数**:
- `data` (str): 待Hash的字符串

**返回**: 十六进制Hash字符串 (64 字符)

**底层**: 使用 `uhashlib.sha256()`

**示例**:
```python
hash_val = refun.hash_string("hello world")
print(hash_val)
# "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

# 用于验证文件完整性
content = "package data"
expected = "abc123..."
actual = refun.hash_string(content)
if actual == expected:
    print("Integrity OK")
```

---

## 完整示例

### 示例 1: 版本比较和筛选

```python
import refun

# 定义可用版本
versions = [
    refun.Version.parse("1.0.0"),
    refun.Version.parse("1.2.0"),
    refun.Version.parse("1.5.0"),
    refun.Version.parse("2.0.0-beta"),
    refun.Version.parse("2.0.0"),
]

# 筛选 >= 1.2.0 的稳定版本
stable_versions = [
    v for v in versions
    if v >= refun.Version.parse("1.2.0")
    and v.prerelease is None
]

print([v.to_string() for v in stable_versions])
# ["1.2.0", "1.5.0", "2.0.0"]
```

### 示例 2: 依赖解析完整流程

```python
import refun

# 构建依赖图
packages = {
    "my_app@1.0.0": {
        "sensor_tools": refun.Constraint.parse("^1.0.0"),
        "display_lib": refun.Constraint.parse("^2.0.0")
    },
    "sensor_tools@1.2.0": {
        "sensor_core": refun.Constraint.parse("^1.0.0"),
        "math_utils": refun.Constraint.parse("^1.0.0")
    },
    "display_lib@2.1.0": {
        "graphics_core": refun.Constraint.parse("^1.0.0")
    },
    "sensor_core@1.0.0": {},
    "math_utils@1.5.0": {},
    "graphics_core@1.3.0": {}
}

# 1. 检测循环依赖
circular = refun.detect_circular_dep(packages)
if circular:
    print("错误: 检测到循环依赖:", circular)
    exit(1)

# 2. 拓扑排序得到加载顺序
load_order = refun.topological_sort(packages)
print("加载顺序:", load_order)
# 输出: ['sensor_core@1.0.0', 'math_utils@1.5.0',
#        'sensor_tools@1.2.0', 'graphics_core@1.3.0',
#        'display_lib@2.1.0', 'my_app@1.0.0']

# 3. 按顺序加载包
for pkg_name in load_order:
    print(f"Loading {pkg_name}...")
    # 实际加载逻辑
```

### 示例 3: 对象存储路径管理

```python
import refun

class ObjectStorage:
    def __init__(self, base_path):
        self.base_path = base_path

    def get_object_path(self, content):
        # 计算Hash
        hash_val = refun.hash_string(content)

        # 分层存储: /storage/ab/cdef...
        dir1 = hash_val[:2]
        dir2 = hash_val[2:4]
        filename = hash_val[4:]

        # 拼接路径
        path = refun.path_join(
            self.base_path,
            "objects",
            dir1,
            dir2,
            filename
        )

        # 规范化
        return refun.normalize_path(path)

# 使用
storage = ObjectStorage("/storage")
path = storage.get_object_path("package content")
print(path)
# "/storage/objects/5f/9c/6a8e..."
```

---

## 性能特性

| API | 时间复杂度 | 空间复杂度 | 备注 |
|-----|-----------|-----------|------|
| `Version.parse()` | O(n) | O(1) | n 为字符串长度 |
| `version1 < version2` | O(1) | O(1) | 整数比较 |
| `Constraint.matches()` | O(1) | O(1) | 快速匹配 |
| `topological_sort()` | O(V+E) | O(V) | V=节点, E=边 |
| `detect_circular_dep()` | O(V+E) | O(V) | DFS 搜索 |
| `match_version()` | O(n) | O(1) | n 为版本数 |
| `path_join()` | O(n) | O(n) | n 为总路径长度 |
| `normalize_path()` | O(n) | O(n) | 单次遍历 |
| `hash_string()` | O(n) | O(1) | n 为字符串长度 |

---

## 类型提示 (MicroPython 不支持，仅供参考)

```python
# 以下类型提示仅用于文档说明，MicroPython 运行时不检查

from typing import Dict, List, Optional

class Version:
    major: int
    minor: int
    patch: int
    prerelease: Optional[str]

    def __init__(self, major: int, minor: int, patch: int, prerelease: Optional[str] = None) -> None: ...
    @staticmethod
    def parse(version_string: str) -> 'Version': ...
    def to_string(self) -> str: ...
    def __lt__(self, other: 'Version') -> bool: ...
    # ... 其他比较运算符

class Constraint:
    @staticmethod
    def parse(constraint_string: str) -> 'Constraint': ...
    def matches(self, version: Version) -> bool: ...

def topological_sort(dep_graph: Dict[str, Dict[str, Constraint]]) -> List[str]: ...
def detect_circular_dep(dep_graph: Dict[str, Dict[str, Constraint]]) -> Optional[List[str]]: ...
def match_version(available_versions: List[Version], constraint: Constraint) -> Optional[Version]: ...
def path_join(*parts: str) -> str: ...
def normalize_path(path: str) -> str: ...
def hash_string(data: str) -> str: ...
```

---

## 另请参阅

- [集成指南](INTEGRATION.md) - 如何将模块集成到 MicroPython
- [构建文档](BUILD.md) - 编译和优化选项
- [TODO](../TODO.md) - 开发计划和路线图
