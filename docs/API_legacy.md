# reFun API 文档

本文档详细介绍 reFun (旧版Python实现) 的所有 API。

## 目录

- [PackageManager](#packagemanager)
- [DependencyResolver](#dependencyresolver)
- [Registry](#registry)
- [Version](#version)
- [Exceptions](#exceptions)
- [辅助函数](#辅助函数)

---

## PackageManager

包管理器主类，提供统一的包管理接口。

### 构造函数

```python
PackageManager(packages_dir="packages", storage_dir="storage")
```

**参数:**
- `packages_dir` (str): 包安装目录，默认 "packages"
- `storage_dir` (str): 存储目录（objects、cache），默认 "storage"

**示例:**
```python
import refun

pm = refun.PackageManager()
# 或使用自定义路径
pm = refun.PackageManager(
    packages_dir="custom_packages",
    storage_dir="custom_storage"
)
```

---

### 安装相关

#### install(name, version, source="index")

从包索引安装包。

**参数:**
- `name` (str): 包名
- `version` (str): 版本号
- `source` (str): 安装源，默认 "index"

**返回:** None

**异常:**
- `PackageNotFoundError`: 包不存在
- `DownloadError`: 下载失败
- `HashMismatchError`: Hash 验证失败

**示例:**
```python
pm.install("sensor_tools", "1.0.0")
```

---

#### install_from_url(url)

从 URL 安装包。

**参数:**
- `url` (str): package.json 的 URL

**返回:** None

**示例:**
```python
pm.install_from_url("https://example.com/sensor_tools-1.0.0.json")
```

---

#### install_from_local(path)

从本地路径安装包。

**参数:**
- `path` (str): 包含 package.json 的本地路径

**返回:** None

**示例:**
```python
pm.install_from_local("./downloads/sensor_tools-1.0.0")
```

---

#### register_local(path, name, version)

将本地文件夹注册为包。

**参数:**
- `path` (str): 包目录路径
- `name` (str): 包名
- `version` (str): 版本号

**返回:** None

**示例:**
```python
pm.register_local("./my_package", "my_pkg", "1.0.0")
```

---

### 卸载相关

#### uninstall(name, version)

卸载指定版本的包。

**参数:**
- `name` (str): 包名
- `version` (str): 版本号

**返回:** None

**异常:**
- `PackageNotFoundError`: 包不存在

**示例:**
```python
pm.uninstall("sensor_tools", "1.0.0")
```

---

#### uninstall_all(name)

卸载包的所有版本。

**参数:**
- `name` (str): 包名

**返回:** None

**示例:**
```python
pm.uninstall_all("sensor_tools")
```

---

#### cleanup_unused_objects()

清理未被任何包引用的对象文件。

**返回:** int - 清理的文件数量

**示例:**
```python
count = pm.cleanup_unused_objects()
print(f"清理了 {count} 个未使用的文件")
```

---

### 加载相关

#### load(name, version=None)

加载包到内存。

**参数:**
- `name` (str): 包名
- `version` (str, optional): 版本号，None 时加载最新版本

**返回:** module - 已加载的模块对象

**异常:**
- `PackageNotFoundError`: 包不存在
- `DependencyError`: 依赖解析失败

**示例:**
```python
# 加载指定版本
sensor = pm.load("sensor_tools", "1.0.0")

# 加载最新版本
sensor = pm.load("sensor_tools")
```

---

#### unload(name, version)

从内存卸载包。

**参数:**
- `name` (str): 包名
- `version` (str): 版本号

**返回:** None

**示例:**
```python
pm.unload("sensor_tools", "1.0.0")
```

---

#### reload(name, version)

重新加载包（清除缓存并重新导入）。

**参数:**
- `name` (str): 包名
- `version` (str): 版本号

**返回:** module - 重新加载的模块对象

**示例:**
```python
sensor = pm.reload("sensor_tools", "1.0.0")
```

---

### 运行相关

#### run(name, version=None)

执行包的 __main__.py 入口文件。

**参数:**
- `name` (str): 包名
- `version` (str, optional): 版本号

**返回:** None

**异常:**
- `PackageNotFoundError`: 包不存在
- `ValueError`: 包没有可执行入口

**示例:**
```python
pm.run("simple_app", "1.0.0")
```

---

#### has_entry(name, version)

检查包是否有可执行入口。

**参数:**
- `name` (str): 包名
- `version` (str): 版本号

**返回:** bool

**示例:**
```python
if pm.has_entry("simple_app", "1.0.0"):
    pm.run("simple_app", "1.0.0")
```

---

### 查询相关

#### list()

列出所有已安装的包。

**返回:** list[dict] - 包信息列表

**示例:**
```python
packages = pm.list()
for pkg in packages:
    print(f"{pkg['name']} @ {pkg['version']}")
```

---

#### list_versions(name)

列出指定包的所有已安装版本。

**参数:**
- `name` (str): 包名

**返回:** list[str] - 版本号列表

**示例:**
```python
versions = pm.list_versions("sensor_tools")
print(versions)  # ['1.0.0', '1.1.0', '2.0.0']
```

---

#### info(name, version)

获取包的详细信息。

**参数:**
- `name` (str): 包名
- `version` (str): 版本号

**返回:** dict - 包元数据

**异常:**
- `PackageNotFoundError`: 包不存在

**示例:**
```python
info = pm.info("sensor_tools", "1.0.0")
print(info['description'])
print(info['dependencies'])
```

---

#### search(keyword)

搜索包（需要包索引服务器支持）。

**参数:**
- `keyword` (str): 搜索关键词

**返回:** list[dict] - 匹配的包列表

**示例:**
```python
results = pm.search("sensor")
for pkg in results:
    print(f"{pkg['name']}: {pkg['description']}")
```

---

## DependencyResolver

依赖解析器，处理包依赖关系。

### 构造函数

```python
DependencyResolver(registry)
```

**参数:**
- `registry` (Registry): 注册表实例

---

### resolve(package_name, version)

解析单个包的所有依赖。

**参数:**
- `package_name` (str): 包名
- `version` (str): 版本号

**返回:** list[tuple] - [(name, version), ...] 加载顺序列表

**异常:**
- `CircularDependencyError`: 检测到循环依赖
- `DependencyError`: 依赖解析失败

**示例:**
```python
from refun.resolver import DependencyResolver

resolver = DependencyResolver(pm.registry)
load_order = resolver.resolve("simple_app", "1.0.0")

for name, version in load_order:
    print(f"{name} @ {version}")
```

---

### resolve_all(packages)

解析多个包的依赖。

**参数:**
- `packages` (list[tuple]): [(name, version), ...]

**返回:** list[tuple] - 全局加载顺序

**示例:**
```python
packages = [
    ("sensor_tools", "1.0.0"),
    ("simple_app", "1.0.0")
]
load_order = resolver.resolve_all(packages)
```

---

### detect_circular(package_name, version)

检测循环依赖。

**参数:**
- `package_name` (str): 包名
- `version` (str): 版本号

**返回:** bool - 是否存在循环依赖

**示例:**
```python
if resolver.detect_circular("pkg_a", "1.0.0"):
    print("检测到循环依赖!")
```

---

## Registry

包注册表，管理已安装包的信息。

### 构造函数

```python
Registry(registry_file="storage/registry.json")
```

**参数:**
- `registry_file` (str): 注册表 JSON 文件路径

---

### register(name, version, metadata)

注册包。

**参数:**
- `name` (str): 包名
- `version` (str): 版本号
- `metadata` (dict): 包元数据

**返回:** None

**示例:**
```python
from refun.registry import Registry

registry = Registry()
registry.register("my_pkg", "1.0.0", {
    "description": "My package",
    "author": "Me",
    "package_json_path": "packages/my_pkg/1.0.0/package.json"
})
registry.save()
```

---

### unregister(name, version)

注销包。

**参数:**
- `name` (str): 包名
- `version` (str): 版本号

**返回:** None

---

### get(name, version)

获取包信息。

**参数:**
- `name` (str): 包名
- `version` (str): 版本号

**返回:** dict - 包元数据

**异常:**
- `PackageNotFoundError`: 包不存在

---

### list_packages()

列出所有包。

**返回:** dict - {name: {version: metadata}}

---

### list_versions(name)

列出包的所有版本。

**参数:**
- `name` (str): 包名

**返回:** list[str] - 版本列表

---

### save()

保存注册表到文件。

**返回:** None

---

### load()

从文件加载注册表。

**返回:** None

---

## Version

版本管理，解析和比较语义化版本。

### parse_version(version_str)

解析版本字符串。

**参数:**
- `version_str` (str): 版本字符串，如 "1.2.3"

**返回:** tuple - (major, minor, patch)

**示例:**
```python
from refun.version import parse_version

major, minor, patch = parse_version("1.2.3")
print(major, minor, patch)  # 1 2 3
```

---

### parse_constraint(constraint_str)

解析版本约束。

**参数:**
- `constraint_str` (str): 约束字符串，如 "^1.2.0", ">=1.0.0"

**返回:** dict - {"op": "^", "version": (1, 2, 0)}

**示例:**
```python
from refun.version import parse_constraint

constraint = parse_constraint("^1.2.0")
print(constraint)  # {"op": "^", "version": (1, 2, 0)}
```

---

### match(version, constraint)

判断版本是否满足约束。

**参数:**
- `version` (str or tuple): 版本
- `constraint` (str or dict): 约束

**返回:** bool

**示例:**
```python
from refun.version import match

match("1.2.5", "^1.2.0")  # True
match("2.0.0", "^1.2.0")  # False
match("1.5.0", ">=1.0.0") # True
```

---

### compare(v1, v2)

比较两个版本。

**参数:**
- `v1` (str or tuple): 版本1
- `v2` (str or tuple): 版本2

**返回:** int - (-1: v1<v2, 0: v1==v2, 1: v1>v2)

**示例:**
```python
from refun.version import compare

compare("1.2.3", "1.2.5")  # -1
compare("2.0.0", "1.9.9")  # 1
compare("1.0.0", "1.0.0")  # 0
```

---

## Exceptions

自定义异常类。

### RefunException

所有 reFun 异常的基类。

---

### PackageNotFoundError

包不存在。

**示例:**
```python
from refun.exceptions import PackageNotFoundError

try:
    pm.load("non_existent", "1.0.0")
except PackageNotFoundError as e:
    print(f"包不存在: {e}")
```

---

### VersionNotFoundError

版本不存在。

---

### DependencyError

依赖解析失败。

---

### CircularDependencyError

循环依赖。

---

### HashMismatchError

Hash 验证失败。

---

### DownloadError

下载失败。

---

### PatchError

Patch 应用失败。

---

### RegistryError

注册表操作失败。

---

## 辅助函数

### compute_hash(file_path)

计算文件的 SHA256 hash。

**参数:**
- `file_path` (str): 文件路径

**返回:** str - 十六进制 hash 字符串

**示例:**
```python
from refun.hasher import compute_hash

hash_value = compute_hash("my_file.py")
print(hash_value)
```

---

### verify_hash(file_path, expected_hash)

验证文件 hash。

**参数:**
- `file_path` (str): 文件路径
- `expected_hash` (str): 期望的 hash 值

**返回:** bool

**异常:**
- `HashMismatchError`: Hash 不匹配

**示例:**
```python
from refun.hasher import verify_hash

try:
    verify_hash("my_file.py", "a1b2c3...")
    print("验证通过")
except HashMismatchError:
    print("文件已被修改")
```

---

### get_hash_path(hash_value)

将 hash 转换为存储路径。

**参数:**
- `hash_value` (str): Hash 值

**返回:** str - 存储路径

**示例:**
```python
from refun.hasher import get_hash_path

path = get_hash_path("a1b2c3d4e5...")
print(path)  # "a1/b2c3d4e5..."
```

---

## 类型定义

### PackageMetadata

```python
{
    "name": str,
    "version": str,
    "description": str,
    "author": str,
    "files": {
        "filename": {
            "hash": str,
            "sources": list[str]
        }
    },
    "dependencies": {
        "package_name": str  # version constraint
    },
    "patches": {
        "global": list[str],  # ["target@version"]
        "local": list[str]
    },
    "entry": str  # optional
}
```

---

## 完整示例

```python
import refun
from refun.exceptions import PackageNotFoundError, DependencyError

# 创建包管理器
pm = refun.PackageManager()

try:
    # 注册本地包
    pm.register_local("packages/sensor_core/1.0.0", "sensor_core", "1.0.0")
    pm.register_local("packages/sensor_tools/1.0.0", "sensor_tools", "1.0.0")

    # 查看包信息
    info = pm.info("sensor_tools", "1.0.0")
    print(f"包: {info['name']}")
    print(f"版本: {info['version']}")
    print(f"依赖: {info['dependencies']}")

    # 加载包（自动解析依赖）
    sensor_tools = pm.load("sensor_tools", "1.0.0")

    # 使用包
    from sensor_tools import MMC5603NJ
    # ... 使用传感器

except PackageNotFoundError as e:
    print(f"包不存在: {e}")
except DependencyError as e:
    print(f"依赖错误: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

---

## 另见

- [README.md](README.md) - 项目概述
- [USAGE.md](USAGE.md) - 使用指南
- [TODO.md](TODO.md) - 开发计划

---

文档版本: 1.0.0
最后更新: 2025
