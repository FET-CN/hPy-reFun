"""
reFun - MicroPython 包管理器

为 ESP32S3 + MicroPython v1.24.1 环境设计的聚合工具箱包管理器。

特性:
- 软件包管理（安装/卸载/加载）
- 依赖解析（拓扑排序）
- 多版本共存
- MonkeyPatch 机制
- 基于 Hash 寻址的内容存储

使用示例:
    >>> import refun
    >>> pm = refun.PackageManager()
    >>> pm.install('sensor_tools', '1.0.0')
    >>> sensor = pm.load('sensor_tools', '1.0.0')
"""

__version__ = '0.1.0'
__author__ = 'reFun Team'


# 导入异常类
from .exceptions import (
    RefunException,
    PackageNotFoundError,
    VersionNotFoundError,
    DependencyError,
    CircularDependencyError,
    HashMismatchError,
    DownloadError,
    PatchError,
    RegistryError,
)

# 导入 hasher 模块
from .hasher import (
    compute_hash,
    verify_hash,
    get_hash_path,
    compute_string_hash,
)

# 导入 version 模块
from .version import (
    Version,
    Constraint,
    parse_version,
    parse_constraint,
    compare,
    match,
)

# 导入阶段2核心模块
from .registry import Registry
from .resolver import DependencyResolver
from .fetcher import Fetcher
from .patcher import PatchManager

# 导入阶段3模块
from .loader import PackageLoader
from .manager import PackageManager


# 定义公开 API
__all__ = [
    # 版本信息
    '__version__',

    # 异常类
    'RefunException',
    'PackageNotFoundError',
    'VersionNotFoundError',
    'DependencyError',
    'CircularDependencyError',
    'HashMismatchError',
    'DownloadError',
    'PatchError',
    'RegistryError',

    # Hash 工具
    'compute_hash',
    'verify_hash',
    'get_hash_path',
    'compute_string_hash',

    # 版本工具
    'Version',
    'Constraint',
    'parse_version',
    'parse_constraint',
    'compare',
    'match',

    # 核心功能模块（阶段2）
    'Registry',
    'DependencyResolver',
    'Fetcher',
    'PatchManager',

    # 包管理器（阶段3）
    'PackageManager',
    'PackageLoader',
]
