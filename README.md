# reFun - MicroPython 包管理器

> 为 ESP32S3 + MicroPython 设计的轻量级包管理器和聚合工具箱

[![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)
[![MicroPython](https://img.shields.io/badge/MicroPython-v1.24.1-green.svg)](https://micropython.org/)
[![Platform](https://img.shields.io/badge/platform-ESP32S3-orange.svg)](https://www.espressif.com/en/products/socs/esp32-s3)

## 特性

- 📦 **包管理**: 安装、卸载、版本管理
- 🔗 **依赖解析**: 自动解析和加载依赖
- 🐵 **MonkeyPatch**: 灵活的运行时代码修补机制
- 🔄 **多版本共存**: 同时使用同一个包的不同版本
- 🎯 **Hash 寻址**: 基于内容 Hash 的存储，自动去重
- 💾 **空间优化**: 为嵌入式设备优化的存储机制
- 🚀 **即插即用**: 简单易用的 API

## 硬件环境

- **开发板**: labplus_Ledong_v2 with ESP32S3
- **CPU**: ESP32-S3 双核处理器 @ 240MHz
- **内存**: 512KB SRAM + 8MB PSRAM
- **存储**: 16MB Flash
- **屏幕**: 1.47寸 LCD (ST7789) 320x170
- **传感器**:
  - MMC5603NJ (3轴磁力计)
  - QMI8658C (6轴 IMU)
  - LTR-308ALS-01 (环境光)

## 快速开始

### 1. 安装

将 `lib/refun` 目录复制到你的 MicroPython 设备：

```bash
# 使用 ampy 或其他工具上传
ampy -p /dev/ttyUSB0 put lib/refun /lib/refun
```

### 2. 基础使用

```python
import refun

# 创建包管理器实例
pm = refun.PackageManager()

# 从本地注册包
pm.register_local("./my_package", "my_pkg", "1.0.0")

# 加载包
my_pkg = pm.load("my_pkg", "1.0.0")

# 使用包
my_pkg.some_function()
```

### 3. 运行示例

```python
# 安装应用
pm.install("simple_app", "1.0.0")

# 运行应用
pm.run("simple_app", "1.0.0")
```

## 项目结构

```
hPy_reFun/
├── lib/refun/              # 核心库
│   ├── __init__.py
│   ├── manager.py          # 包管理器
│   ├── loader.py           # 动态加载器
│   ├── resolver.py         # 依赖解析器
│   ├── version.py          # 版本管理
│   ├── registry.py         # 注册表
│   ├── patcher.py          # MonkeyPatch
│   ├── fetcher.py          # 文件获取器
│   ├── hasher.py           # Hash 计算
│   └── exceptions.py       # 自定义异常
│
├── packages/               # 已安装包
│   ├── sensor_core/        # 传感器核心库
│   ├── sensor_tools/       # 传感器驱动
│   ├── patch_demo/         # Patch 演示
│   └── simple_app/         # 示例应用
│
├── storage/
│   ├── objects/            # Hash 寻址对象池
│   ├── registry.json       # 包注册表
│   └── cache/              # 下载缓存
│
├── examples/               # 使用示例
│   ├── basic_install.py    # 基础安装
│   ├── patch_demo.py       # Patch 演示
│   ├── dependency_demo.py  # 依赖解析
│   └── run_app.py          # 运行应用
│
├── README.md               # 本文件
├── USAGE.md                # 使用文档
├── API.md                  # API 文档
└── TODO.md                 # 实现计划
```

## 核心概念

### 包结构

每个包包含一个 `package.json` 文件：

```json
{
  "name": "sensor_tools",
  "version": "1.0.0",
  "description": "传感器驱动工具包",
  "author": "reFun Team",
  "files": {
    "__init__.py": {
      "hash": "a1b2c3...",
      "sources": ["local://...", "https://..."]
    }
  },
  "dependencies": {
    "sensor_core": "^1.0.0"
  },
  "patches": {
    "global": ["old_pkg@1.0.0"],
    "local": []
  },
  "entry": "__main__.py"
}
```

### Hash 寻址存储

使用文件内容的 SHA256 hash 作为存储地址：

- **去重**: 相同内容的文件只存储一次
- **完整性**: 通过 hash 验证文件未被篡改
- **多源下载**: 支持从多个源下载同一文件
- **离线友好**: 可打包 objects 目录传输

### MonkeyPatch 机制

支持运行时修补和增强已有包：

- **全局 Patch**: 对所有调用者生效
- **局部 Patch**: 仅在特定上下文生效
- **非侵入式**: 不修改原始包文件

示例：

```python
# __patch__.py
def patch_sensor_read(target_module):
    original_read = target_module.read
    def patched_read(*args, **kwargs):
        print("Patched!")
        return original_read(*args, **kwargs)
    target_module.read = patched_read

PATCHES = {
    "sensor_tools": {
        "read_fix": patch_sensor_read
    }
}
```

## 示例包

项目包含 4 个示例包：

1. **sensor_core** (v1.0.0) - 传感器基础库
   - `SensorBase`: 传感器基类
   - `SensorData`: 数据容器
   - 工具函数

2. **sensor_tools** (v1.0.0) - 传感器驱动
   - `MMC5603NJ`: 磁力计驱动
   - `QMI8658C`: 6轴 IMU 驱动
   - 依赖: sensor_core ^1.0.0

3. **patch_demo** (v1.0.0) - Patch 演示
   - 修复 sensor_tools 的已知问题
   - 添加指南针功能
   - 演示全局和局部 patch

4. **simple_app** (v1.0.0) - 示例应用
   - 传感器数据显示应用
   - 演示依赖加载
   - 可执行入口

## 文档

- [USAGE.md](USAGE.md) - 详细使用文档
- [API.md](API.md) - API 参考文档
- [TODO.md](TODO.md) - 实现计划和进度

## 运行示例

```bash
# 基础安装示例
python examples/basic_install.py

# Patch 机制演示
python examples/patch_demo.py

# 依赖解析演示
python examples/dependency_demo.py

# 运行应用演示
python examples/run_app.py
```

## 开发状态

- [x] 阶段 1: 基础设施 (exceptions, hasher, version)
- [x] 阶段 2: 核心功能 (registry, resolver, fetcher, patcher)
- [x] 阶段 3: 集成与 API (loader, manager)
- [x] 阶段 4: 示例与文档

详见 [TODO.md](TODO.md)

## 许可证

本项目采用 GPLv3(or-later) 许可证 - 详见 [LICENSE](LICENSE) 文件

## 贡献

欢迎提交 Issue 和 Pull Request！

## 致谢

感谢 MicroPython 社区和 ESP32 开源生态

---

Made with ❤️ for MicroPython & ESP32S3
