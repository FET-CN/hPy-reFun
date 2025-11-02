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

### 在 MicroPython 设备上

```bash
# 使用 ampy 上传核心库
ampy -p /dev/ttyUSB0 put lib/refun /lib/refun

# 或使用 mpremote
mpremote fs cp -r lib/refun :/lib/refun
```

### 在 Python 开发环境

```bash
# 克隆仓库
git clone https://github.com/yourusername/hPy_reFun.git
cd hPy_reFun

# 直接使用
python examples/basic_install.py
```

---

## 基础使用

### 创建包管理器实例

```python
import refun

# 创建包管理器
pm = refun.PackageManager()

# 指定自定义存储路径（可选）
pm = refun.PackageManager(
    packages_dir="custom_packages",
    storage_dir="custom_storage"
)
```

### 注册本地包

```python
# 从本地路径注册包
pm.register_local(
    path="./my_package",
    name="my_pkg",
    version="1.0.0"
)
```

### 加载包

```python
# 加载指定版本
my_pkg = pm.load("my_pkg", "1.0.0")

# 加载最新版本
my_pkg = pm.load("my_pkg")  # version=None 时加载最新版

# 使用包
result = my_pkg.some_function()
```

### 卸载包

```python
# 卸载指定版本
pm.uninstall("my_pkg", "1.0.0")

# 卸载所有版本
pm.uninstall_all("my_pkg")
```

---

## 包管理

### 列出已安装的包

```python
# 列出所有包
packages = pm.list()
for pkg in packages:
    print(f"{pkg['name']} @ {pkg['version']}")

# 列出指定包的所有版本
versions = pm.list_versions("sensor_tools")
print(f"可用版本: {versions}")
```

### 查看包信息

```python
# 获取包的详细信息
info = pm.info("sensor_tools", "1.0.0")
print(f"名称: {info['name']}")
print(f"版本: {info['version']}")
print(f"描述: {info['description']}")
print(f"作者: {info['author']}")
print(f"依赖: {info['dependencies']}")
```

### 从 URL 安装

```python
# 从 URL 安装包
pm.install_from_url("https://example.com/my_package-1.0.0.json")
```

### 从本地文件安装

```python
# 从本地 package.json 安装
pm.install_from_local("./downloads/my_package")
```

---

## 依赖管理

### 自动依赖解析

reFun 会自动解析和加载依赖：

```python
# simple_app 依赖 sensor_tools
# sensor_tools 依赖 sensor_core
# 加载 simple_app 时会自动加载所有依赖

app = pm.load("simple_app", "1.0.0")
# ✓ sensor_core 已加载
# ✓ sensor_tools 已加载
# ✓ simple_app 已加载
```

### 版本约束

在 `package.json` 中指定依赖版本：

```json
{
  "dependencies": {
    "sensor_core": "^1.0.0",    // 兼容版本 (1.x.x)
    "math_utils": "~2.1.0",     // 近似版本 (2.1.x)
    "logger": ">=1.0.0",        // 大于等于
    "parser": "==1.2.3"         // 精确匹配
  }
}
```

### 查看依赖树

```python
from refun.resolver import DependencyResolver

resolver = DependencyResolver(pm.registry)

# 解析依赖并获取加载顺序
load_order = resolver.resolve("simple_app", "1.0.0")

for pkg_name, pkg_version in load_order:
    print(f"{pkg_name} @ {pkg_version}")
```

### 处理循环依赖

reFun 会自动检测循环依赖并报错：

```python
try:
    pm.load("pkg_a", "1.0.0")  # pkg_a -> pkg_b -> pkg_a
except refun.CircularDependencyError as e:
    print(f"检测到循环依赖: {e}")
```

---

## MonkeyPatch

### 创建 Patch

在包目录中创建 `__patch__.py`：

```python
# __patch__.py

def patch_fix_bug(target_module):
    """修复目标模块的 bug"""
    original_func = target_module.buggy_function

    def fixed_func(*args, **kwargs):
        # 添加修复逻辑
        result = original_func(*args, **kwargs)
        if result is None:
            result = []  # 修复: 返回空列表而不是 None
        return result

    target_module.buggy_function = fixed_func


def patch_add_feature(target_module):
    """为目标模块添加新功能"""
    def new_feature(self):
        return "新功能"

    target_module.SomeClass.new_feature = new_feature


# 导出 patch 函数
PATCHES = {
    "target_package": {
        "fix_bug": patch_fix_bug,
        "add_feature": patch_add_feature
    }
}
```

### 在 package.json 中声明 Patch

```json
{
  "name": "my_patch",
  "version": "1.0.0",
  "patches": {
    "global": ["target_package@1.0.0"],  // 全局 patch
    "local": ["another_package@2.0.0"]   // 局部 patch
  }
}
```

### 应用 Patch

```python
# 1. 注册并加载 patch 包
pm.register_local("packages/my_patch/1.0.0", "my_patch", "1.0.0")
pm.load("my_patch", "1.0.0")

# 2. 重新加载目标包以应用 patch
pm.reload("target_package", "1.0.0")

# 3. 使用修补后的功能
target = pm.load("target_package", "1.0.0")
target.buggy_function()  # 已修复
```

### 全局 vs 局部 Patch

**全局 Patch**:
- 对所有加载目标包的调用者生效
- 用于修复已知 bug 或兼容性问题

**局部 Patch**:
- 仅在当前包使用目标包时生效
- 用于特定场景的定制化修改

---

## 多版本管理

### 安装多个版本

```python
# 安装不同版本
pm.register_local("packages/sensor_tools/1.0.0", "sensor_tools", "1.0.0")
pm.register_local("packages/sensor_tools/1.1.0", "sensor_tools", "1.1.0")
pm.register_local("packages/sensor_tools/2.0.0", "sensor_tools", "2.0.0")
```

### 同时使用不同版本

```python
# 加载不同版本到不同变量
sensor_v1 = pm.load("sensor_tools", "1.0.0")
sensor_v2 = pm.load("sensor_tools", "2.0.0")

# 使用不同版本的 API
data1 = sensor_v1.read()        # v1.0.0 API
data2 = sensor_v2.read_async()  # v2.0.0 新 API
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

### 4. 注册包

```python
pm.register_local("./my_package", "my_package", "1.0.0")
```

### 5. 创建可执行应用

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

运行应用：

```python
pm.run("my_package", "1.0.0")
```

---

## 常见问题

### Q: 如何清理未使用的文件？

```python
# 清理 storage/objects/ 中未被任何包引用的文件
pm.cleanup_unused_objects()
```

### Q: 如何重新加载包？

```python
# 重新加载包（清除缓存并重新导入）
pm.reload("my_package", "1.0.0")
```

### Q: 如何处理导入错误？

```python
try:
    pkg = pm.load("my_package", "1.0.0")
except refun.PackageNotFoundError:
    print("包不存在")
except refun.DependencyError:
    print("依赖解析失败")
except refun.HashMismatchError:
    print("文件完整性验证失败")
```

### Q: 如何在 MicroPython 中使用？

```python
import sys
sys.path.append('/lib')  # 确保 refun 在路径中

import refun
pm = refun.PackageManager()

# 注册包
pm.register_local("/packages/sensor_tools/1.0.0", "sensor_tools", "1.0.0")

# 使用包
sensor = pm.load("sensor_tools", "1.0.0")
```

### Q: 如何查看已加载的包？

```python
import sys

# 查看所有已导入的模块
for module_name in sys.modules:
    print(module_name)
```

### Q: 如何设置包索引服务器？

在 `refun.conf` 中配置（如果实现了配置功能）：

```json
{
  "index_servers": [
    "https://pkg.refun.io",
    "https://mirror.example.com"
  ]
}
```

### Q: 如何备份已安装的包？

```bash
# 备份整个 packages 和 storage 目录
tar -czf refun_backup.tar.gz packages/ storage/
```

---

## 最佳实践

1. **版本管理**: 使用语义化版本号（Major.Minor.Patch）
2. **依赖约束**: 使用 `^` 允许小版本更新，使用 `==` 锁定版本
3. **文件组织**: 将相关功能组织到子模块中
4. **Patch 隔离**: 优先使用局部 patch，避免影响其他包
5. **测试**: 在注册包前测试所有功能
6. **文档**: 为包编写清晰的文档和示例

---

## 下一步

- 查看 [API.md](API.md) 了解详细的 API 文档
- 查看 [examples/](examples/) 目录了解更多示例
- 查看 [TODO.md](TODO.md) 了解开发计划

---

有问题？查看 [README.md](README.md) 或提交 Issue！
