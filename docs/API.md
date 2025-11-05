# reFun C 模块 API 文档

本文档详细说明 reFun C 模块提供的所有 API。

## 模块导入

```python
import refun
```

**模块版本**: `refun.__version__()` 返回模块版本字符串，例如 "1.0.0-c"

---

## 目录

### 核心类
- [PackageManager](#packagemanager-类) - 包管理器主接口
- [Registry](#registry-类) - 包注册表管理
- [PackageLoader](#packageloader-类) - 包加载器
- [Fetcher](#fetcher-类) - 文件获取和对象存储
- [PatchManager](#patchmanager-类) - Monkey Patch 管理
- [DependencyResolver](#dependencyresolver-类) - 依赖解析器

### 版本管理
- [Version 类](#version-类) - 语义化版本
- [Constraint 类](#constraint-类) - 版本约束

### 工具函数
- [依赖解析函数](#依赖解析-api)
- [工具函数](#工具函数-api)

---

## PackageManager 类

包管理器的统一高层 API，提供用户友好的包管理接口。

### 构造函数

```python
PackageManager(storage_path="storage", packages_path="packages")
```

**参数**:
- `storage_path` (str, optional): 存储根目录，默认 "storage"
- `packages_path` (str, optional): 包目录，默认 "packages"

**说明**:
- 自动创建 `storage_path` 和 `packages_path` 目录
- 自动初始化子组件（Registry, Fetcher, PatchManager, PackageLoader）
- 自动加载注册表

**示例**:
```python
import refun

# 使用默认路径
pm = refun.PackageManager()

# 使用自定义路径
pm = refun.PackageManager(
    storage_path="custom_storage",
    packages_path="custom_packages"
)
```

### install_local()

从本地路径安装包。

```python
pm.install_local(name, version, pkg_path) -> None
```

**参数**:
- `name` (str): 包名
- `version` (str): 版本号
- `pkg_path` (str): 包的本地路径

**说明**:
- 将包复制到对象存储
- 计算包内容的 Hash
- 在注册表中注册包信息

**示例**:
```python
pm.install_local("my_pkg", "1.0.0", "/path/to/my_pkg")
```

### uninstall()

卸载指定的包版本。

```python
pm.uninstall(name, version) -> None
```

**参数**:
- `name` (str): 包名
- `version` (str): 版本号

**示例**:
```python
pm.uninstall("my_pkg", "1.0.0")
```

### load()

加载包并返回模块对象。

```python
pm.load(name, version=None) -> module
```

**参数**:
- `name` (str): 包名
- `version` (str, optional): 版本号，默认 None（加载最新版本）

**返回**: 已加载的模块对象

**说明**:
- 如果 `version` 为 None，自动加载最新版本
- 自动处理依赖加载
- 使用缓存避免重复加载

**示例**:
```python
# 加载指定版本
my_pkg = pm.load("my_pkg", "1.0.0")

# 加载最新版本
my_pkg = pm.load("my_pkg")

# 使用包
result = my_pkg.some_function()
```

### list_installed()

列出所有已安装的包。

```python
pm.list_installed() -> list
```

**返回**: 包列表，每个元素为 `(name, version)` 元组

**示例**:
```python
packages = pm.list_installed()
for name, version in packages:
    print(f"{name} @ {version}")
```

### list_loaded()

列出所有已加载的包。

```python
pm.list_loaded() -> list
```

**返回**: 已加载包的键列表，格式为 `"name@version"`

**示例**:
```python
loaded = pm.list_loaded()
for pkg_key in loaded:
    print(f"已加载: {pkg_key}")
```

---

## Registry 类

包注册表管理，提供包的注册、查询和持久化功能。

### 构造函数

```python
Registry(registry_path)
```

**参数**:
- `registry_path` (str): 注册表文件路径

**示例**:
```python
registry = refun.Registry("storage/registry.json")
```

### load()

从文件加载注册表数据。

```python
registry.load() -> None
```

**异常**:
- `OSError`: 文件不存在或读取失败

**示例**:
```python
registry.load()
```

### save()

保存注册表数据到文件。

```python
registry.save() -> None
```

**说明**:
- 仅在数据被修改时才写入文件
- 使用 JSON 格式存储

**示例**:
```python
registry.save()
```

### add_package()

添加包到注册表。

```python
registry.add_package(name, version, metadata) -> None
```

**参数**:
- `name` (str): 包名
- `version` (str): 版本号
- `metadata` (dict): 包元数据，包含:
  - `path`: 包路径
  - `hash`: 包内容 Hash
  - `deps`: 依赖字典 `{name: constraint_str}`

**示例**:
```python
metadata = {
    "path": "/packages/my_pkg/1.0.0",
    "hash": "abc123...",
    "deps": {"dep_lib": "^1.0.0"}
}
registry.add_package("my_pkg", "1.0.0", metadata)
```

### remove_package()

从注册表移除包。

```python
registry.remove_package(name, version) -> None
```

**参数**:
- `name` (str): 包名
- `version` (str): 版本号

**示例**:
```python
registry.remove_package("my_pkg", "1.0.0")
```

### get_package()

获取包的元数据。

```python
registry.get_package(name, version) -> dict
```

**参数**:
- `name` (str): 包名
- `version` (str): 版本号

**返回**: 包元数据字典

**异常**:
- `KeyError`: 包不存在

**示例**:
```python
metadata = registry.get_package("my_pkg", "1.0.0")
print(metadata["path"])
```

### list_versions()

列出包的所有已安装版本。

```python
registry.list_versions(name) -> list
```

**参数**:
- `name` (str): 包名

**返回**: 版本号列表

**示例**:
```python
versions = registry.list_versions("my_pkg")
print(f"可用版本: {versions}")
```

### is_installed()

检查包是否已安装。

```python
registry.is_installed(name, version) -> bool
```

**参数**:
- `name` (str): 包名
- `version` (str): 版本号

**返回**: 是否已安装

**示例**:
```python
if registry.is_installed("my_pkg", "1.0.0"):
    print("已安装")
```

### get_all_packages()

获取所有包的信息。

```python
registry.get_all_packages() -> dict
```

**返回**: 嵌套字典 `{name: {version: metadata}}`

**示例**:
```python
all_packages = registry.get_all_packages()
for name, versions in all_packages.items():
    print(f"{name}: {list(versions.keys())}")
```

---

## PackageLoader 类

包的动态导入和依赖加载。

### 构造函数

```python
PackageLoader(registry, resolver, patcher, fetcher)
```

**参数**:
- `registry`: Registry 对象
- `resolver`: DependencyResolver 对象（当前可为 None）
- `patcher`: PatchManager 对象
- `fetcher`: Fetcher 对象

**示例**:
```python
loader = refun.PackageLoader(registry, resolver, patcher, fetcher)
```

### load()

加载包。

```python
loader.load(name, version=None) -> module
```

**参数**:
- `name` (str): 包名
- `version` (str, optional): 版本号

**返回**: 已加载的模块对象

**说明**:
- 自动处理依赖加载
- 应用 Monkey Patch
- 使用缓存避免重复加载

**示例**:
```python
module = loader.load("my_pkg", "1.0.0")
```

### unload()

卸载包（从缓存中移除）。

```python
loader.unload(name, version) -> None
```

**参数**:
- `name` (str): 包名
- `version` (str): 版本号

**说明**:
- 仅从加载缓存中移除
- 不影响 `sys.modules`

**示例**:
```python
loader.unload("my_pkg", "1.0.0")
```

### is_loaded()

检查包是否已加载。

```python
loader.is_loaded(name, version) -> bool
```

**参数**:
- `name` (str): 包名
- `version` (str): 版本号

**返回**: 是否已加载

**示例**:
```python
if loader.is_loaded("my_pkg", "1.0.0"):
    print("已加载")
```

---

## Fetcher 类

文件获取和对象存储管理。

### 构造函数

```python
Fetcher(storage_path, cache_path=None)
```

**参数**:
- `storage_path` (str): 对象存储根目录
- `cache_path` (str, optional): 缓存目录

**示例**:
```python
fetcher = refun.Fetcher("storage/objects")
```

### fetch()

从多个源获取文件。

```python
fetcher.fetch(sources, expected_hash=None) -> str
```

**参数**:
- `sources` (list): 源列表（URL 或本地路径）
- `expected_hash` (str, optional): 期望的 Hash 值

**返回**: 对象在本地存储中的路径

**说明**:
- 尝试从多个源下载文件
- 验证 Hash（如果提供）
- 存储到对象池

**示例**:
```python
path = fetcher.fetch(
    ["https://example.com/pkg.py", "local://backup/pkg.py"],
    expected_hash="abc123..."
)
```

### get_object_path()

获取对象在存储中的路径。

```python
fetcher.get_object_path(hash) -> str
```

**参数**:
- `hash` (str): 对象的 Hash 值

**返回**: 对象路径

**说明**:
- 使用分层存储：`{storage}/ab/cd/ef...`

**示例**:
```python
path = fetcher.get_object_path("abc123...")
# "storage/objects/ab/c1/23..."
```

### has_object()

检查对象是否存在。

```python
fetcher.has_object(hash) -> bool
```

**参数**:
- `hash` (str): 对象的 Hash 值

**返回**: 对象是否存在

**示例**:
```python
if fetcher.has_object("abc123..."):
    print("对象已存在")
```

### store_file()

将文件存储到对象池。

```python
fetcher.store_file(src_path, expected_hash) -> str
```

**参数**:
- `src_path` (str): 源文件路径
- `expected_hash` (str): 期望的 Hash 值

**返回**: 对象在存储中的路径

**说明**:
- 计算文件 Hash
- 验证与 expected_hash 是否匹配
- 复制到对象存储

**示例**:
```python
obj_path = fetcher.store_file("/tmp/pkg.py", "abc123...")
```

---

## PatchManager 类

Monkey Patch 管理，提供动态修改模块功能。

### 构造函数

```python
PatchManager()
```

**示例**:
```python
patcher = refun.PatchManager()
```

### register_patch()

注册 Patch 函数。

```python
patcher.register_patch(target_module, patch_func) -> None
```

**参数**:
- `target_module` (str): 目标模块名
- `patch_func` (callable): Patch 函数

**说明**:
- Patch 函数接收目标模块对象作为参数
- 可以修改模块的属性和方法

**示例**:
```python
def my_patch(target_module):
    original_func = target_module.some_func
    def patched_func(*args, **kwargs):
        print("Patched!")
        return original_func(*args, **kwargs)
    target_module.some_func = patched_func

patcher.register_patch("target_pkg", my_patch)
```

### apply_patches()

应用所有已注册的 Patch。

```python
patcher.apply_patches(module) -> None
```

**参数**:
- `module`: 模块对象

**说明**:
- 查找该模块的所有 Patch
- 按注册顺序应用

**示例**:
```python
import target_pkg
patcher.apply_patches(target_pkg)
```

### load_patch_module()

从 Patch 模块加载并注册 Patch。

```python
patcher.load_patch_module(patch_module_path) -> None
```

**参数**:
- `patch_module_path` (str): Patch 模块路径

**说明**:
- 导入 Patch 模块
- 查找 `PATCHES` 字典
- 自动注册所有 Patch

**示例**:
```python
patcher.load_patch_module("/packages/my_patch/__patch__.py")
```

### get_patches()

获取目标模块的所有 Patch。

```python
patcher.get_patches(target) -> list
```

**参数**:
- `target` (str): 目标模块名

**返回**: Patch 函数列表

**示例**:
```python
patches = patcher.get_patches("target_pkg")
print(f"找到 {len(patches)} 个 Patch")
```

---

## DependencyResolver 类

依赖解析器（阶段3新增，当前为占位实现）。

### 构造函数

```python
DependencyResolver(registry)
```

**参数**:
- `registry`: Registry 对象

**说明**:
- 当前版本暂未完全实现
- 后续版本将提供完整的依赖解析功能

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

### 示例 1: 使用 PackageManager 管理包

```python
import refun

# 创建包管理器
pm = refun.PackageManager(
    storage_path="storage",
    packages_path="packages"
)

# 安装本地包
pm.install_local("my_pkg", "1.0.0", "/path/to/my_pkg")
pm.install_local("dep_lib", "2.0.0", "/path/to/dep_lib")

# 列出已安装的包
packages = pm.list_installed()
for name, version in packages:
    print(f"已安装: {name} @ {version}")

# 加载包
my_pkg = pm.load("my_pkg", "1.0.0")
result = my_pkg.some_function()

# 查看已加载的包
loaded = pm.list_loaded()
print(f"已加载: {loaded}")

# 卸载包
pm.uninstall("my_pkg", "1.0.0")
```

### 示例 2: 版本比较和筛选

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

### 示例 3: 依赖解析完整流程

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

### 示例 4: 使用 Registry 直接管理

```python
import refun

# 创建注册表
registry = refun.Registry("storage/registry.json")
registry.load()

# 添加包
metadata = {
    "path": "/packages/my_pkg/1.0.0",
    "hash": "abc123...",
    "deps": {"dep_lib": "^2.0.0"}
}
registry.add_package("my_pkg", "1.0.0", metadata)

# 查询包
versions = registry.list_versions("my_pkg")
print(f"my_pkg 的版本: {versions}")

# 检查包是否安装
if registry.is_installed("my_pkg", "1.0.0"):
    pkg_info = registry.get_package("my_pkg", "1.0.0")
    print(f"包路径: {pkg_info['path']}")

# 保存注册表
registry.save()
```

### 示例 5: 使用 PatchManager 修改模块行为

```python
import refun

# 创建 PatchManager
patcher = refun.PatchManager()

# 定义 Patch 函数
def fix_bug_patch(target_module):
    """修复目标模块的 bug"""
    original_func = target_module.buggy_function

    def fixed_func(*args, **kwargs):
        # 添加修复逻辑
        result = original_func(*args, **kwargs)
        if result is None:
            result = []  # 修复: 返回空列表而不是 None
        return result

    target_module.buggy_function = fixed_func

# 注册 Patch
patcher.register_patch("target_pkg", fix_bug_patch)

# 导入目标模块
import target_pkg

# 应用 Patch
patcher.apply_patches(target_pkg)

# 现在 target_pkg.buggy_function 已被修复
result = target_pkg.buggy_function()  # 不会返回 None
```

### 示例 6: 对象存储路径管理

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
