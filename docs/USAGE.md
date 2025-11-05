# reFun 使用文档

本文档详细介绍 reFun 包管理器的使用方法。

## 目录

- [安装](#安装)
- [基础使用](#基础使用)
- [包管理](#包管理)
- [依赖管理](#依赖管理)
- [MonkeyPatch](#monkeypatch)
- [多版本管理](#多版本管理)
- [创建包](#创建包)
- [常见问题](#常见问题)

---

## 安装

reFun 是一个 MicroPython C 模块，需要编译到固件中。

### 作为 git submodule 集成到 MicroPython

```bash
# 1. 进入 MicroPython 项目
cd micropython
mkdir -p modules

# 2. 添加 reFun 为 submodule
git submodule add https://github.com/your-repo/hPy_reFun.git modules/refun

# 3. 编译固件 (ESP32S3)
cd ports/esp32
make BOARD=ESP32_GENERIC_S3 \
     USER_C_MODULES=../../modules/refun/micropython.cmake

# 4. 烧录
make BOARD=ESP32_GENERIC_S3 deploy
```

### 在 Unix Port 测试

```bash
# 编译 Unix Port
cd micropython/ports/unix
make USER_C_MODULES=/path/to/hPy_reFun/micropython.mk

# 运行
./build-standard/micropython
```

更多详细信息，请参见 [集成指南](INTEGRATION.md)。

---

## 基础使用

### 创建包管理器实例

```python
import refun

# 创建包管理器（使用默认路径）
pm = refun.PackageManager()

# 指定自定义存储路径（可选）
pm = refun.PackageManager(
    storage_path="custom_storage",
    packages_path="custom_packages"
)
```

**说明**:
- `storage_path`: 存储根目录，用于保存注册表和对象存储
- `packages_path`: 包目录（当前版本暂未使用）
- PackageManager 会自动创建必要的目录和初始化子组件

### 安装本地包

```python
# 从本地路径安装包
pm.install_local(
    name="my_pkg",
    version="1.0.0",
    pkg_path="/path/to/my_package"
)
```

**说明**:
- `name`: 包名
- `version`: 版本号（语义化版本）
- `pkg_path`: 包的本地路径

### 加载包

```python
# 加载指定版本
my_pkg = pm.load("my_pkg", "1.0.0")

# 加载最新版本
my_pkg = pm.load("my_pkg")  # version=None 时加载最新版

# 使用包
result = my_pkg.some_function()
```

**说明**:
- 自动处理依赖加载
- 使用缓存避免重复加载
- 自动应用 Monkey Patch（如果有）

### 卸载包

```python
# 卸载指定版本
pm.uninstall("my_pkg", "1.0.0")
```

**注意**:
- 当前版本仅从注册表中移除包信息
- 不会删除对象存储中的文件

---

## 包管理

### 列出已安装的包

```python
# 列出所有已安装的包
packages = pm.list_installed()
for name, version in packages:
    print(f"{name} @ {version}")

# 列出已加载的包
loaded = pm.list_loaded()
for pkg_key in loaded:
    print(f"已加载: {pkg_key}")
```

**说明**:
- `list_installed()`: 返回所有已注册的包（未必已加载）
- `list_loaded()`: 返回已加载到内存的包

### 使用 Registry 查看包信息

```python
# 通过 PackageManager 的 registry 访问
registry = pm.registry

# 列出指定包的所有版本
versions = registry.list_versions("my_pkg")
print(f"可用版本: {versions}")

# 获取包的元数据
metadata = registry.get_package("my_pkg", "1.0.0")
print(f"路径: {metadata['path']}")
print(f"Hash: {metadata['hash']}")
print(f"依赖: {metadata['deps']}")

# 检查包是否已安装
if registry.is_installed("my_pkg", "1.0.0"):
    print("包已安装")
```

### 从 URL 安装（未来支持）

```python
# 注意: 当前版本暂不支持从 URL 安装
# 计划在后续版本中通过 Fetcher 实现

# 预留接口示例:
# pm.install_from_url("https://example.com/my_package-1.0.0.tar.gz")
```

---

## 依赖管理

### 自动依赖解析（计划中）

当前版本的 PackageLoader 尚未完全实现自动依赖解析，但提供了底层工具：

```python
# 注意: 当前版本需要手动管理依赖加载顺序
# 自动依赖解析将在后续版本中完善

# 手动加载依赖示例
pm.load("sensor_core", "1.0.0")     # 先加载依赖
pm.load("sensor_tools", "1.0.0")    # 再加载主包
pm.load("simple_app", "1.0.0")      # 最后加载应用
```

### 使用低层 API 进行依赖解析

```python
import refun

# 构建依赖图
dep_graph = {
    "simple_app@1.0.0": {
        "sensor_tools": refun.Constraint.parse("^1.0.0")
    },
    "sensor_tools@1.0.0": {
        "sensor_core": refun.Constraint.parse("^1.0.0")
    },
    "sensor_core@1.0.0": {}
}

# 检测循环依赖
circular = refun.detect_circular_dep(dep_graph)
if circular:
    print(f"检测到循环依赖: {circular}")
else:
    # 拓扑排序获取加载顺序
    load_order = refun.topological_sort(dep_graph)
    print(f"加载顺序: {load_order}")

    # 按顺序加载
    for pkg_key in load_order:
        # 解析包名和版本
        name, version = pkg_key.split("@")
        pm.load(name, version)
```

### 版本约束

支持的版本约束语法：

```python
# 精确匹配
c = refun.Constraint.parse("==1.2.3")

# 大于等于
c = refun.Constraint.parse(">=1.0.0")

# 兼容版本 (Caret)
c = refun.Constraint.parse("^1.2.0")  # 1.2.0 <= v < 2.0.0

# 近似版本 (Tilde)
c = refun.Constraint.parse("~1.2.3")  # 1.2.3 <= v < 1.3.0

# 检查版本是否满足约束
v = refun.Version.parse("1.5.0")
if c.matches(v):
    print("版本匹配")
```

### 在 package.json 中定义依赖

```json
{
  "name": "my_app",
  "version": "1.0.0",
  "dependencies": {
    "sensor_core": "^1.0.0",
    "math_utils": "~2.1.0",
    "logger": ">=1.0.0"
  }
}
```

**注意**: 当前版本需要在安装包时手动将依赖信息添加到元数据中。

---

## MonkeyPatch

reFun 提供了强大的 Monkey Patch 机制，允许在运行时修改模块的行为。

### 使用 PatchManager

```python
import refun

# 通过 PackageManager 访问 PatchManager
patcher = pm.patcher

# 或直接创建
patcher = refun.PatchManager()
```

### 创建和注册 Patch

```python
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
```

### 应用 Patch

```python
# 方法 1: 手动应用到已加载的模块
import target_pkg
patcher.apply_patches(target_pkg)

# 方法 2: 通过 PackageLoader 自动应用
# PackageLoader 会在加载包时自动应用已注册的 Patch
target_pkg = pm.load("target_pkg", "1.0.0")
# Patch 已自动应用
```

### 从 __patch__.py 加载 Patch

创建 Patch 模块文件：

```python
# /packages/my_patch/__patch__.py

def patch_fix_bug(target_module):
    """修复目标模块的 bug"""
    original_func = target_module.buggy_function

    def fixed_func(*args, **kwargs):
        result = original_func(*args, **kwargs)
        if result is None:
            result = []
        return result

    target_module.buggy_function = fixed_func

def patch_add_feature(target_module):
    """为目标模块添加新功能"""
    def new_feature(self):
        return "New Feature"

    target_module.SomeClass.new_feature = new_feature

# 导出 Patch 字典
PATCHES = {
    "target_package": {
        "fix_bug": patch_fix_bug,
        "add_feature": patch_add_feature
    }
}
```

加载 Patch 模块：

```python
# 从文件加载并注册所有 Patch
patcher.load_patch_module("/packages/my_patch/__patch__.py")

# 获取已注册的 Patch
patches = patcher.get_patches("target_package")
print(f"找到 {len(patches)} 个 Patch")
```

### 完整示例

```python
import refun

# 创建包管理器
pm = refun.PackageManager()

# 获取 PatchManager
patcher = pm.patcher

# 定义并注册 Patch
def my_patch(target_module):
    print("Applying patch to", target_module.__name__)
    target_module.patched = True

patcher.register_patch("my_pkg", my_patch)

# 安装并加载目标包
pm.install_local("my_pkg", "1.0.0", "/path/to/my_pkg")
my_pkg = pm.load("my_pkg", "1.0.0")

# Patch 已自动应用
print(my_pkg.patched)  # True
```

### 注意事项

**当前版本的限制**:
- 暂不支持在 package.json 中声明 Patch
- 全局/局部 Patch 的区分尚未实现
- 需要手动管理 Patch 的应用顺序

**最佳实践**:
- 为 Patch 函数添加清晰的文档
- 避免过度使用 Patch，优先考虑其他方案
- 测试 Patch 在不同版本上的兼容性

---

## 多版本管理

reFun 支持同时安装和使用一个包的多个版本。

### 安装多个版本

```python
# 安装不同版本
pm.install_local("sensor_tools", "1.0.0", "/packages/sensor_tools/1.0.0")
pm.install_local("sensor_tools", "1.1.0", "/packages/sensor_tools/1.1.0")
pm.install_local("sensor_tools", "2.0.0", "/packages/sensor_tools/2.0.0")

# 列出所有版本
versions = pm.registry.list_versions("sensor_tools")
print(f"已安装版本: {versions}")  # ['1.0.0', '1.1.0', '2.0.0']
```

### 同时使用不同版本

```python
# 加载不同版本到不同变量
sensor_v1 = pm.load("sensor_tools", "1.0.0")
sensor_v2 = pm.load("sensor_tools", "2.0.0")

# 使用不同版本的 API
data1 = sensor_v1.read()        # v1.0.0 API
data2 = sensor_v2.read_async()  # v2.0.0 新 API (如果支持)

# 查看已加载的包
loaded = pm.list_loaded()
print(loaded)  # ['sensor_tools@1.0.0', 'sensor_tools@2.0.0']
```

### 版本选择策略

```python
# 加载最新版本
latest = pm.load("sensor_tools")  # 自动选择最新版本

# 使用版本约束选择
import refun

# 获取所有版本
all_versions = [
    refun.Version.parse(v)
    for v in pm.registry.list_versions("sensor_tools")
]

# 应用约束
constraint = refun.Constraint.parse("^1.0.0")
matching = refun.match_version(all_versions, constraint)

if matching:
    sensor = pm.load("sensor_tools", matching.to_string())
    print(f"加载版本: {matching.to_string()}")
```

---

## 创建包

### 1. 创建包目录结构

```
my_package/
├── __init__.py
├── module1.py
├── module2.py
└── package.json
```

### 2. 编写 package.json

```json
{
  "name": "my_package",
  "version": "1.0.0",
  "description": "我的自定义包",
  "author": "Your Name",

  "files": {
    "__init__.py": {
      "hash": "计算后的SHA256",
      "sources": ["local://path/to/__init__.py"]
    },
    "module1.py": {
      "hash": "计算后的SHA256",
      "sources": ["local://path/to/module1.py"]
    }
  },

  "dependencies": {
    "some_lib": "^1.0.0"
  },

  "patches": {
    "global": [],
    "local": []
  },

  "entry": "__main__.py"  // 可选：可执行入口
}
```

### 3. 计算文件 Hash

```python
import hashlib

def compute_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

# 使用
hash_value = compute_hash("__init__.py")
print(hash_value)
```

### 4. 安装包

```python
pm.install_local("my_package", "1.0.0", "./my_package")
```

### 5. 创建可执行应用（可选）

如果包是可执行应用，创建 `__main__.py`：

```python
# __main__.py
from .app import main

if __name__ == "__main__":
    main()
```

在 `package.json` 中指定入口：

```json
{
  "entry": "__main__.py"
}
```

**注意**: 当前版本暂不支持 `pm.run()` 方法，需要手动导入和执行：

```python
pkg = pm.load("my_package", "1.0.0")
if hasattr(pkg, '__main__'):
    exec(open(pkg.__file__.replace('__init__.py', '__main__.py')).read())
```

---

## 常见问题

### Q: 如何清理未使用的文件？

```python
# 当前版本暂不支持自动清理
# 需要手动删除 storage/objects/ 中的未使用文件

# 计划中的接口:
# pm.cleanup_unused_objects()
```

### Q: 如何重新加载包？

```python
# 方法 1: 从 loader 缓存中卸载
pm.loader.unload("my_package", "1.0.0")
# 再次加载
pkg = pm.load("my_package", "1.0.0")

# 方法 2: 从 sys.modules 中删除（更彻底）
import sys
sys.modules.pop("my_package", None)
pkg = pm.load("my_package", "1.0.0")
```

### Q: 如何处理导入错误？

```python
try:
    pkg = pm.load("my_package", "1.0.0")
except KeyError:
    print("包不存在或未安装")
except ImportError as e:
    print(f"导入失败: {e}")
except Exception as e:
    print(f"加载错误: {e}")
```

### Q: 如何在 MicroPython 中使用？

reFun 作为 C 模块编译到固件中，使用方式与标准 Python 相同：

```python
import refun

# 创建包管理器
pm = refun.PackageManager()

# 安装包
pm.install_local("sensor_tools", "1.0.0", "/flash/packages/sensor_tools")

# 使用包
sensor = pm.load("sensor_tools", "1.0.0")
```

### Q: 如何查看已加载的包？

```python
# 方法 1: 使用 PackageManager
loaded = pm.list_loaded()
print(f"已加载的包: {loaded}")

# 方法 2: 查看 sys.modules
import sys
for module_name in sys.modules:
    print(module_name)
```

### Q: 如何查看模块版本？

```python
# 查看 reFun 模块版本
print(refun.__version__())

# 查看包的版本（通过 registry）
versions = pm.registry.list_versions("my_package")
print(f"已安装版本: {versions}")
```

### Q: 包的存储结构是什么？

```
storage/
├── registry.json          # 包注册表
└── objects/               # 对象存储池
    ├── ab/                # Hash 前2位
    │   └── cd/            # Hash 3-4位
    │       └── ef123...   # 文件内容（以 Hash 命名）
    └── ...

packages/                  # 包目录（可选，暂未使用）
```

### Q: 如何备份已安装的包？

```bash
# 在 MicroPython 设备上
# 方法 1: 使用 mpremote
mpremote fs cp -r :storage ./backup/storage

# 方法 2: 使用 ampy
ampy -p /dev/ttyUSB0 get /storage ./backup/storage

# 在 Linux/Windows 上
# 直接压缩目录
tar -czf refun_backup.tar.gz storage/
```

### Q: C 模块和 Python 实现有什么区别？

| 特性 | C 模块 | Python 实现 |
|------|--------|-------------|
| 性能 | 3-10x 更快 | 基准 |
| 内存占用 | <20KB | ~100KB |
| 安装方式 | 编译到固件 | 上传文件 |
| 调试难度 | 较高 | 较低 |
| 可定制性 | 需要重新编译 | 直接修改代码 |

### Q: 遇到问题如何调试？

```python
# 启用详细输出
import sys
sys.path.append('.')

# 查看注册表内容
registry = pm.registry
all_packages = registry.get_all_packages()
print("注册表内容:", all_packages)

# 查看已加载的包
print("已加载:", pm.list_loaded())

# 检查包路径
metadata = registry.get_package("my_pkg", "1.0.0")
print("包路径:", metadata.get("path"))
```

---

## 最佳实践

### 1. 版本管理

- **使用语义化版本号**: `Major.Minor.Patch` 格式
- **合理使用约束**:
  - `^1.2.0`: 兼容版本更新（推荐用于依赖）
  - `~1.2.3`: 补丁版本更新
  - `==1.2.3`: 精确锁定（用于测试环境）

### 2. 包结构

```
my_package/
├── __init__.py        # 包入口
├── module1.py         # 功能模块
├── module2.py
└── package.json       # 元数据
```

- 将相关功能组织到子模块
- 保持 `__init__.py` 简洁
- 避免循环导入

### 3. 性能优化

- **延迟加载**: 在需要时才加载包，而不是启动时全部加载
- **共享依赖**: 多个包共享同一个依赖版本可以节省内存
- **缓存利用**: PackageLoader 自动缓存已加载的包

```python
# 好的做法
def use_sensor():
    sensor = pm.load("sensor_tools", "1.0.0")  # 延迟加载
    return sensor.read()

# 避免
sensor = pm.load("sensor_tools", "1.0.0")  # 启动时加载
```

### 4. MonkeyPatch 使用

- **谨慎使用**: Patch 应该是最后的手段
- **文档化**: 清晰记录为什么需要 Patch
- **测试**: 充分测试 Patch 的副作用
- **版本兼容**: 确保 Patch 对不同版本的兼容性

### 5. 错误处理

```python
# 健壮的包加载
def safe_load_package(pm, name, version):
    try:
        return pm.load(name, version)
    except KeyError:
        print(f"Package {name}@{version} not found")
        return None
    except Exception as e:
        print(f"Failed to load {name}@{version}: {e}")
        return None
```

### 6. 内存管理

在内存受限的 MicroPython 环境中：

```python
# 及时卸载不需要的包
pm.loader.unload("temp_pkg", "1.0.0")

# 清理 sys.modules
import sys
import gc
sys.modules.pop("temp_pkg", None)
gc.collect()
```

### 7. 开发流程

1. **本地开发**: 先在 Unix Port 上测试
2. **版本控制**: 使用 git 管理包代码
3. **测试**: 编写单元测试和集成测试
4. **文档**: 编写 README 和使用示例
5. **发布**: 打包并安装到目标设备

---

## 下一步

- **[API 文档](API.md)** - 查看完整的 API 参考
- **[集成指南](INTEGRATION.md)** - 了解如何集成到 MicroPython
- **[构建文档](BUILD.md)** - 编译和优化选项
- **[开发计划](../TODO.md)** - 了解项目路线图

---

## 获取帮助

- **GitHub Issues**: 报告 bug 或请求新特性
- **文档**: 查看项目文档了解更多细节
- **示例**: 参考代码示例学习最佳实践

---

**提示**: reFun 仍在积极开发中，部分功能可能尚未完全实现。请参考 [TODO.md](../TODO.md) 了解当前开发状态。
