# reFun - MicroPython 包管理器实现计划

## 项目概述

为 ESP32S3 + MicroPython v1.24.1 环境设计的聚合工具箱包管理器，支持软件包管理、依赖解析、多版本共存、MonkeyPatch 机制和基于 Hash 寻址的内容存储。

**硬件环境：**
- labplus_Ledong_v2 with ESP32S3
- LVGL 9.3.0 320x170 (ST7789)
- MMC5603NJ (磁力计)
- QMI8658C (陀螺仪)

硬件	型号规格
CPU	ESP32-S3，高性能 Xtensa® 32位双核处理器 240 MHz
屏幕	1.47寸高清LCD彩屏，分辨率：320x170，型号：ST7789
实体按键	(A/B/reset)
触摸按键	(P/Y/T/H/O/N)
运行内存	512KB SRAM + 8MB PSRAM
存储	16MB (Flash)
环境光线传感器	LTR-308ALS-01
声音传感器(麦克风)	EM4013BTC1R16B-T0-423 双麦克风
全彩RGB灯	3颗全彩WS2812-2020 RGB-LED灯珠
贴片式喇叭扬声器	13*13*4MM 1w
地磁传感器	MMC5603NJ，3轴，最小分辨率0.0625mG，±30G量程，±1°指向精度
六轴传感器	QMI8658C，陀螺仪最高±2048°/s，加速度计最高±16G
蜂鸣器	喇叭替代蜂鸣器实现音频播放
蓝牙	BLE 5.0

---

## 目录结构

```
hPy_reFun/
├── lib/refun/                    # 核心库（可被直接导入）
│   ├── __init__.py              # 导出 PackageManager 等核心 API
│   ├── manager.py               # 包管理器（安装/卸载/加载/运行）
│   ├── loader.py                # 动态加载器（sys.path 管理）
│   ├── resolver.py              # 依赖解析器（拓扑排序）
│   ├── version.py               # 版本管理（语义化版本解析）
│   ├── registry.py              # 注册表（持久化存储）
│   ├── patcher.py               # MonkeyPatch 管理器
│   ├── fetcher.py               # 文件获取器（多源下载）
│   ├── hasher.py                # Hash 计算和验证
│   └── exceptions.py            # 自定义异常
│
├── packages/                     # 已安装包（逻辑结构，分层存储）
│   └── {pkg_name}/
│       └── {version}/
│           ├── package.json     # 包元数据（含文件 hash 列表）
│           └── __patch__.py     # patch 实现（可选）
│
├── storage/
│   ├── objects/                 # Hash 寻址对象池（内容去重）
│   │   └── {hash[:2]}/
│   │       └── {hash[2:]}       # 实际文件内容
│   ├── registry.json            # 已安装包索引
│   └── cache/                   # 下载缓存（可选）
│
├── examples/                     # 使用示例
│   ├── basic_install.py
│   ├── patch_demo.py
│   ├── dependency_demo.py
│   └── run_app.py
│
└── TODO.md                       # 本文件
```

---

## package.json 格式定义

```json
{
  "name": "sensor_tools",
  "version": "1.0.0",
  "description": "传感器工具包",
  "author": "author_name",

  "files": {
    "__init__.py": {
      "hash": "a1b2c3d4e5f67890abcdef...",
      "sources": [
        "https://pkg.refun.io/objects/a1/b2c3d4e5f67890abcdef",
        "local://storage/objects/a1/b2c3d4e5f67890abcdef"
      ]
    },
    "mmc5603.py": {
      "hash": "e5f6g7h8i9...",
      "sources": [
        "https://pkg.refun.io/objects/e5/f6g7h8i9",
        "https://mirror.example.com/objects/e5/f6g7h8i9"
      ]
    },
    "lib/utils.py": {
      "hash": "123456789abc...",
      "sources": [...]
    }
  },

  "dependencies": {
    "sensor_core": "^1.2.0",
    "math_utils": ">=2.0.0"
  },

  "patches": {
    "global": ["old_sensor@1.0.0"],
    "local": ["ui_lib@2.0.0"]
  },

  "entry": "__main__.py"
}
```

**字段说明：**
- `name`: 包名（唯一标识）
- `version`: 版本号（语义化版本）
- `files`: 文件列表，每个文件包含 hash 和多个下载源
- `dependencies`: 依赖包及版本约束
- `patches.global`: 全局 patch（对所有调用者生效）
- `patches.local`: 局部 patch（仅在当前包使用依赖时生效）
- `entry`: 可执行入口文件（可选）

---

## 核心功能模块

### 1. exceptions.py - 自定义异常

**职责：** 定义所有自定义异常类

**异常类型：**
- `PackageNotFoundError`: 包不存在
- `VersionNotFoundError`: 版本不存在
- `DependencyError`: 依赖解析失败
- `CircularDependencyError`: 循环依赖
- `HashMismatchError`: Hash 验证失败
- `DownloadError`: 下载失败
- `PatchError`: Patch 应用失败
- `RegistryError`: 注册表操作失败

---

### 2. hasher.py - Hash 计算和验证

**职责：** 文件内容 Hash 计算和完整性验证

**主要功能：**
- `compute_hash(file_path)`: 计算文件 SHA256 hash
- `verify_hash(file_path, expected_hash)`: 验证文件完整性
- `get_hash_path(hash)`: 将 hash 转换为存储路径（前2位/后续位）

**实现细节：**
- 使用 `hashlib.sha256`
- 支持流式读取（节省内存）
- 返回十六进制字符串

---

### 3. version.py - 语义化版本管理

**职责：** 解析和比较语义化版本

**主要功能：**
- `parse_version(version_str)`: 解析版本字符串 "1.2.3"
- `parse_constraint(constraint_str)`: 解析版本约束 "^1.2.0", ">=1.0.0"
- `match(version, constraint)`: 判断版本是否满足约束
- `compare(v1, v2)`: 比较两个版本大小

**支持的约束语法：**
- `^1.2.3`: 兼容版本（1.2.3 <= v < 2.0.0）
- `~1.2.3`: 近似版本（1.2.3 <= v < 1.3.0）
- `>=1.2.3`: 大于等于
- `<=1.2.3`: 小于等于
- `==1.2.3`: 精确匹配
- `1.2.3`: 默认为精确匹配

---

### 4. registry.py - 包注册表

**职责：** 持久化存储已安装包的信息

**主要功能：**
- `register(name, version, metadata)`: 注册包
- `unregister(name, version)`: 注销包
- `get(name, version)`: 获取包信息
- `list_packages()`: 列出所有已安装包
- `list_versions(name)`: 列出包的所有版本
- `save()`: 保存到 registry.json
- `load()`: 从 registry.json 加载

**数据结构（registry.json）：**
```json
{
  "packages": {
    "sensor_tools": {
      "1.0.0": {
        "package_json_path": "packages/sensor_tools/1.0.0/package.json",
        "description": "传感器工具包",
        "author": "author_name"
      },
      "1.1.0": { ... }
    }
  }
}
```

---

### 5. resolver.py - 依赖解析器

**职责：** 解析依赖树，确定加载顺序

**主要功能：**
- `resolve(package_name, version)`: 解析单个包的依赖
- `resolve_all(packages)`: 解析多个包的依赖
- `get_load_order(packages)`: 拓扑排序，返回加载顺序
- `detect_circular()`: 检测循环依赖

**算法：**
- DFS/BFS 遍历依赖树
- Kahn 算法拓扑排序
- 版本冲突处理（同一个包的不同版本需求）

**处理策略：**
- 优先使用已安装的最高兼容版本
- 检测到冲突时报错并提示

---

### 6. fetcher.py - 文件获取器

**职责：** 从多个源下载文件并验证

**主要功能：**
- `fetch(sources, hash)`: 从 sources 列表依次尝试下载
- `fetch_from_url(url)`: 从 HTTP/HTTPS 下载
- `fetch_from_local(path)`: 从本地路径复制
- `fetch_package_json(name, version, sources)`: 获取 package.json
- `store_object(content, hash)`: 存储到 objects/ 目录

**下载策略：**
- 多源 fallback（第一个失败则尝试下一个）
- 下载后立即验证 hash
- 自动创建 hash 路径目录
- 支持断点续传（可选）

---

### 7. patcher.py - MonkeyPatch 管理器

**职责：** 管理和应用 MonkeyPatch

**主要功能：**
- `register_patch(source_pkg, target_pkg, patch_type)`: 注册 patch
- `apply_patches(package, context)`: 应用相关 patch
- `load_patch_module(package)`: 加载 __patch__.py
- `get_global_patches(target)`: 获取针对目标包的全局 patch
- `get_local_patches(source, target)`: 获取局部 patch

**Patch 类型：**
1. **全局 Patch**：
   - 在 package.json 中声明 `"global": ["target@version"]`
   - 任何人加载 target 时都会应用
   - 用于修复已知 bug 或兼容性问题

2. **局部 Patch**：
   - 在 package.json 中声明 `"local": ["target@version"]`
   - 只有当前包使用 target 时才应用
   - 用于特定场景的定制化修改

**__patch__.py 格式示例：**
```python
# __patch__.py

def patch_sensor_read(target_module):
    """Patch sensor_tools 的 read 方法"""
    original_read = target_module.read

    def patched_read(*args, **kwargs):
        print("Patched: reading sensor...")
        return original_read(*args, **kwargs)

    target_module.read = patched_read

# 导出 patch 函数
PATCHES = {
    "sensor_tools": {
        "read": patch_sensor_read
    }
}
```

---

### 8. loader.py - 动态加载器

**职责：** 动态加载包到内存，管理 sys.path

**主要功能：**
- `load(name, version)`: 加载包（返回模块对象）
- `unload(name, version)`: 卸载包（清理 sys.modules）
- `build_virtual_fs(package_json)`: 根据 hash 构建虚拟文件系统
- `add_to_path(path)`: 添加到 sys.path
- `remove_from_path(path)`: 从 sys.path 移除

**加载流程：**
1. 读取 package.json
2. 解析依赖并递归加载（按拓扑顺序）
3. 根据 files 字段，从 objects/ 重建包结构到临时目录（或直接映射）
4. 添加包路径到 sys.path
5. 应用相关 patches
6. 使用 `importlib` 导入模块
7. 返回模块对象

**内存优化：**
- 延迟加载（只在需要时加载）
- 引用计数（多个包依赖同一个包时共享）
- 支持卸载以释放内存

---

### 9. manager.py - 包管理器（统一 API）

**职责：** 对外提供统一的包管理接口

**主要功能：**

#### 安装相关
- `install(name, version, source="index")`: 从包索引安装
- `install_from_url(url)`: 从 URL 安装 package.json
- `install_from_local(path)`: 从本地路径安装
- `register_local(path, name, version)`: 将本地文件夹注册为包

#### 卸载相关
- `uninstall(name, version)`: 卸载指定版本
- `uninstall_all(name)`: 卸载所有版本
- `cleanup_unused_objects()`: 清理未被引用的 objects

#### 加载相关
- `load(name, version=None)`: 加载包（version 为 None 则加载最新版本）
- `unload(name, version)`: 卸载包
- `reload(name, version)`: 重新加载包

#### 运行相关
- `run(name, version=None)`: 执行包的 __main__.py
- `has_entry(name, version)`: 检查包是否有可执行入口

#### 查询相关
- `list()`: 列出所有已安装包
- `list_versions(name)`: 列出包的所有版本
- `info(name, version)`: 显示包详细信息
- `search(keyword)`: 搜索包（可选，需要包索引服务器）

**使用示例：**
```python
import refun

pm = refun.PackageManager()

# 安装包
pm.install("sensor_tools", "1.0.0")

# 从本地注册
pm.register_local("./my_package", "my_pkg", "0.1.0")

# 加载包
sensor = pm.load("sensor_tools", "1.0.0")
sensor.read_magnetometer()

# 运行应用
pm.run("my_game", "0.1.0")

# 列出已安装包
print(pm.list())
```

---

## Hash 寻址存储机制

### 原理
使用文件内容的 SHA256 hash 作为存储地址，实现内容去重和完整性验证。

### 存储结构
```
storage/objects/
├── a1/
│   └── b2c3d4e5f67890...  (完整文件内容)
├── e5/
│   └── f6g7h8i9...
└── ...
```

### 文件路径计算
```python
hash = "a1b2c3d4e5f67890abcdef..."
path = f"storage/objects/{hash[:2]}/{hash[2:]}"
```

### 优势
1. **去重**：相同内容的文件只存储一次
2. **完整性**：通过 hash 验证文件未被篡改
3. **多源下载**：可从多个源下载，hash 相同即可
4. **增量更新**：新版本只下载变化的文件
5. **离线友好**：可打包 objects/ 目录传输

### 安装流程
```
1. 获取 package.json
2. 遍历 files 字段
3. 对每个文件：
   - 检查 objects/{hash[:2]}/{hash[2:]} 是否存在
   - 存在则跳过
   - 不存在则从 sources 列表下载
   - 验证 hash
   - 存储到 objects/
4. 在 packages/{name}/{version}/ 创建 package.json
5. 注册到 registry.json
```

### 虚拟文件系统（加载时）
```python
# 方案 1: 符号链接（如果系统支持）
packages/sensor_tools/1.0.0/
├── __init__.py -> ../../../storage/objects/a1/b2c3...
└── mmc5603.py -> ../../../storage/objects/e5/f6g7...

# 方案 2: 硬链接（节省空间）
# 方案 3: 临时复制（兼容性最好）
# 方案 4: 自定义 import hook（最灵活）
```

---

## 安装来源支持

### 1. 包索引服务器（默认）
```python
pm.install("sensor_tools", "1.0.0")
# 从配置的索引服务器下载
```

**索引服务器 API：**
```
GET /packages/{name}/versions/        # 获取所有版本列表
GET /packages/{name}/{version}/       # 获取 package.json
GET /objects/{hash[:2]}/{hash[2:]}/   # 下载文件对象
```

### 2. URL 直接安装
```python
pm.install_from_url("https://example.com/sensor_tools-1.0.0.json")
# package.json 中包含 files 的下载源
```

### 3. 本地路径安装
```python
pm.install_from_local("./downloads/sensor_tools-1.0.0/")
# 读取本地 package.json 并复制文件到 objects/
```

### 4. 本地文件夹注册
```python
pm.register_local("./my_package", "my_pkg", "0.1.0")
# 扫描文件夹，计算 hash，生成 package.json，注册到系统
```

---

## 多版本共存机制

### 目录结构
```
packages/
├── sensor_tools/
│   ├── 1.0.0/
│   │   └── package.json
│   ├── 1.1.0/
│   │   └── package.json
│   └── 2.0.0/
│       └── package.json
```

### 加载机制
```python
# 加载指定版本
sensor_v1 = pm.load("sensor_tools", "1.0.0")
sensor_v2 = pm.load("sensor_tools", "2.0.0")

# 同时使用不同版本
sensor_v1.read()  # 使用 1.0.0 API
sensor_v2.read()  # 使用 2.0.0 API
```

### sys.path 管理
```python
# 按需添加
sys.path.append("packages/sensor_tools/1.0.0")
sys.path.append("packages/sensor_tools/2.0.0")

# 使用不同的模块名避免冲突（可选）
import importlib
st_v1 = importlib.import_module("sensor_tools", "packages/sensor_tools/1.0.0")
st_v2 = importlib.import_module("sensor_tools", "packages/sensor_tools/2.0.0")
```

---

## 实现步骤

### 阶段 1: 基础设施（1-4）

#### ✅ TODO 1: 创建目录结构
- [ ] 创建 `lib/refun/` 目录
- [ ] 创建 `packages/` 目录
- [ ] 创建 `storage/objects/` 目录
- [ ] 创建 `storage/cache/` 目录
- [ ] 创建 `examples/` 目录

#### ✅ TODO 2: 实现 exceptions.py
- [ ] 定义 `RefunException` 基类
- [ ] 定义 `PackageNotFoundError`
- [ ] 定义 `VersionNotFoundError`
- [ ] 定义 `DependencyError`
- [ ] 定义 `CircularDependencyError`
- [ ] 定义 `HashMismatchError`
- [ ] 定义 `DownloadError`
- [ ] 定义 `PatchError`
- [ ] 定义 `RegistryError`

#### ✅ TODO 3: 实现 hasher.py
- [ ] 实现 `compute_hash(file_path)` - 计算文件 SHA256
- [ ] 实现 `verify_hash(file_path, expected_hash)` - 验证 hash
- [ ] 实现 `get_hash_path(hash)` - 转换为存储路径
- [ ] 实现流式读取（支持大文件）
- [ ] 编写单元测试

#### ✅ TODO 4: 实现 version.py
- [ ] 实现 `Version` 类（解析 "1.2.3"）
- [ ] 实现 `Constraint` 类（解析 "^1.2.0" 等）
- [ ] 实现 `compare(v1, v2)` - 版本比较
- [ ] 实现 `match(version, constraint)` - 匹配判断
- [ ] 支持 ^, ~, >=, <=, == 约束
- [ ] 编写单元测试

---

### 阶段 2: 核心功能（5-8）

#### ✅ TODO 5: 实现 registry.py
- [ ] 实现 `Registry` 类
- [ ] 实现 `register(name, version, metadata)`
- [ ] 实现 `unregister(name, version)`
- [ ] 实现 `get(name, version)`
- [ ] 实现 `list_packages()`
- [ ] 实现 `list_versions(name)`
- [ ] 实现 `save()` - 保存到 JSON
- [ ] 实现 `load()` - 从 JSON 加载
- [ ] 处理并发写入（可选）
- [ ] 编写单元测试

#### ✅ TODO 6: 实现 resolver.py
- [ ] 实现 `DependencyResolver` 类
- [ ] 实现 `resolve(package, version)` - 递归解析依赖
- [ ] 实现 `get_load_order(packages)` - 拓扑排序
- [ ] 实现 `detect_circular()` - 检测循环依赖
- [ ] 处理版本冲突
- [ ] 编写单元测试（包括循环依赖测试）

#### ✅ TODO 7: 实现 fetcher.py
- [ ] 实现 `Fetcher` 类
- [ ] 实现 `fetch(sources, hash)` - 多源下载
- [ ] 实现 `fetch_from_url(url)` - HTTP 下载
- [ ] 实现 `fetch_from_local(path)` - 本地复制
- [ ] 实现 `fetch_package_json(name, version, sources)`
- [ ] 实现 `store_object(content, hash)` - 存储到 objects/
- [ ] 集成 hash 验证
- [ ] 实现 fallback 机制
- [ ] 编写单元测试

#### ✅ TODO 8: 实现 patcher.py
- [ ] 实现 `PatchManager` 类
- [ ] 实现 `register_patch(source, target, type)`
- [ ] 实现 `get_global_patches(target)`
- [ ] 实现 `get_local_patches(source, target)`
- [ ] 实现 `load_patch_module(package)` - 加载 __patch__.py
- [ ] 实现 `apply_patches(package, context)` - 应用 patch
- [ ] 处理 patch 冲突（独立 patch）
- [ ] 编写单元测试

---

### 阶段 3: 集成与 API（9-10）

#### ✅ TODO 9: 实现 loader.py
- [ ] 实现 `PackageLoader` 类
- [ ] 实现 `load(name, version)` - 加载包
- [ ] 实现 `unload(name, version)` - 卸载包
- [ ] 实现 `build_virtual_fs(package_json)` - 构建虚拟 FS
- [ ] 实现 sys.path 管理
- [ ] 集成依赖解析器
- [ ] 集成 patch 管理器
- [ ] 实现延迟加载
- [ ] 实现引用计数
- [ ] 编写单元测试

#### ✅ TODO 10: 实现 manager.py
- [ ] 实现 `PackageManager` 类
- [ ] 实现 `install(name, version, source)`
- [ ] 实现 `install_from_url(url)`
- [ ] 实现 `install_from_local(path)`
- [ ] 实现 `register_local(path, name, version)`
- [ ] 实现 `uninstall(name, version)`
- [ ] 实现 `load(name, version)`
- [ ] 实现 `unload(name, version)`
- [ ] 实现 `run(name, version)` - 执行 __main__.py
- [ ] 实现 `list()` / `list_versions(name)`
- [ ] 实现 `info(name, version)`
- [ ] 实现 `cleanup_unused_objects()`
- [ ] 编写单元测试

---

### 阶段 4: 示例与文档（11-12）

#### ✅ TODO 11: 创建示例包
- [ ] 创建 `sensor_tools` 示例包
  - [ ] 实现 MMC5603NJ 磁力计驱动
  - [ ] 实现 QMI8658C 陀螺仪驱动
  - [ ] 编写 package.json
- [ ] 创建 `sensor_core` 依赖包
  - [ ] 实现通用传感器接口
  - [ ] 编写 package.json
- [ ] 创建 `patch_demo` 示例包
  - [ ] 实现全局 patch 示例
  - [ ] 实现局部 patch 示例
  - [ ] 编写 __patch__.py
  - [ ] 编写 package.json
- [ ] 创建 `simple_app` 可执行应用
  - [ ] 实现 __main__.py
  - [ ] 演示依赖加载
  - [ ] 编写 package.json

#### ✅ TODO 12: 编写使用示例和文档
- [ ] 创建 `examples/basic_install.py` - 基础安装示例
- [ ] 创建 `examples/patch_demo.py` - Patch 机制示例
- [ ] 创建 `examples/dependency_demo.py` - 依赖解析示例
- [ ] 创建 `examples/run_app.py` - 运行应用示例
- [ ] 创建 `README.md` - 项目说明
- [ ] 创建 `USAGE.md` - 使用文档
- [ ] 创建 `API.md` - API 文档
- [ ] 添加代码注释

---

## 使用示例

### 基础使用
```python
import refun

# 创建包管理器实例
pm = refun.PackageManager()

# 从包索引安装
pm.install("sensor_tools", "1.0.0")

# 加载包
sensor = pm.load("sensor_tools", "1.0.0")

# 使用包
data = sensor.read_magnetometer()
print(data)

# 列出已安装包
for pkg in pm.list():
    print(f"{pkg['name']} @ {pkg['version']}")

# 卸载包
pm.uninstall("sensor_tools", "1.0.0")
```

### 从本地注册
```python
# 将本地开发的包注册到系统
pm.register_local("./my_sensor_driver", "my_sensor", "0.1.0")

# 加载使用
my_sensor = pm.load("my_sensor", "0.1.0")
```

### 运行应用
```python
# 安装游戏应用
pm.install("snake_game", "1.0.0")

# 运行应用（执行 __main__.py）
pm.run("snake_game", "1.0.0")
```

### 多版本使用
```python
# 同时加载不同版本
sensor_v1 = pm.load("sensor_tools", "1.0.0")
sensor_v2 = pm.load("sensor_tools", "2.0.0")

# 使用不同版本的 API
data1 = sensor_v1.read()  # 旧版 API
data2 = sensor_v2.read_advanced()  # 新版 API
```

### MonkeyPatch 示例

**场景：** 修复 sensor_tools 1.0.0 的已知 bug

**patch_package/package.json:**
```json
{
  "name": "sensor_fix",
  "version": "1.0.0",
  "patches": {
    "global": ["sensor_tools@1.0.0"]
  }
}
```

**patch_package/__patch__.py:**
```python
def patch_read_function(target_module):
    original_read = target_module.read_magnetometer

    def fixed_read(*args, **kwargs):
        # 修复：添加数据校验
        result = original_read(*args, **kwargs)
        if result is None:
            result = [0, 0, 0]  # 返回默认值
        return result

    target_module.read_magnetometer = fixed_read

PATCHES = {
    "sensor_tools": {
        "read_magnetometer": patch_read_function
    }
}
```

**使用：**
```python
# 安装 patch 包
pm.install("sensor_fix", "1.0.0")

# 加载 sensor_tools 时自动应用 patch
sensor = pm.load("sensor_tools", "1.0.0")
data = sensor.read_magnetometer()  # 已应用 patch
```

---

## 配置文件（可选）

### refun.conf
```json
{
  "index_servers": [
    "https://pkg.refun.io",
    "https://mirror.example.com"
  ],
  "cache_enabled": true,
  "auto_cleanup": true,
  "patch_isolation": true
}
```

---

## 下一步计划

1. **核心实现**：按照 TODO 1-10 顺序实现核心功能
2. **测试验证**：为每个模块编写单元测试
3. **示例创建**：创建示例包和应用（TODO 11-12）
4. **文档完善**：编写完整的使用文档
5. **性能优化**：内存占用、加载速度优化
6. **包索引服务器**：搭建简单的包索引服务器（可选）
7. **GUI 工具箱**：基于 LVGL 的可视化包管理界面（未来）

---

## 技术细节

### MicroPython 兼容性注意事项
- 使用 `uos` 而非 `os`（如果需要）
- 使用 `ujson` 而非 `json`（如果需要）
- 避免使用 MicroPython 不支持的标准库
- 注意内存限制，优先使用流式处理
- 文件路径使用 `/` 而非 `\`

### ESP32S3 存储管理
- Flash 空间有限，需要合理管理
- 优先使用 hash 去重节省空间
- 支持按需下载和延迟加载
- 提供清理未使用文件的工具

### LVGL 集成（未来）
- 创建可视化的包管理界面
- 显示已安装包、依赖关系图
- 提供安装/卸载操作界面
- 监控内存和存储使用情况

---

## 许可证

GPLv3(ot-later)
