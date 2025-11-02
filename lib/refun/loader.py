"""
reFun 包加载器模块

提供包的动态加载、卸载、虚拟文件系统构建和 sys.path 管理功能。
"""

import os
import sys
import importlib
try:
    import ujson as json
except ImportError:
    import json

from .exceptions import (
    PackageNotFoundError,
    VersionNotFoundError,
    DependencyError
)


class PackageLoader:
    """包加载器类

    负责动态加载包到内存，管理 sys.path，构建虚拟文件系统，
    集成依赖解析和 patch 应用。

    Attributes:
        registry: Registry 实例
        resolver: DependencyResolver 实例
        patcher: PatchManager 实例
        fetcher: Fetcher 实例
        _loaded_packages: 已加载的包 {(name, version): module}
        _package_paths: 包路径映射 {(name, version): path}
        _reference_count: 包引用计数 {(name, version): count}
    """

    def __init__(self, registry, resolver, patcher, fetcher):
        """初始化包加载器

        Args:
            registry: Registry 实例
            resolver: DependencyResolver 实例
            patcher: PatchManager 实例
            fetcher: Fetcher 实例
        """
        self.registry = registry
        self.resolver = resolver
        self.patcher = patcher
        self.fetcher = fetcher

        self._loaded_packages = {}
        self._package_paths = {}
        self._reference_count = {}

    def load(self, name, version=None, context=None):
        """加载包（返回模块对象）

        Args:
            name: 包名
            version: 版本号（None 表示加载最新版本）
            context: 上下文信息（用于局部 patch）

        Returns:
            module: 包的模块对象

        Raises:
            PackageNotFoundError: 包不存在
            VersionNotFoundError: 版本不存在
            DependencyError: 依赖解析失败
        """
        # 确定版本
        if version is None:
            version = self.registry.get_latest_version(name)

        package_key = (name, version)

        # 如果已加载，增加引用计数并返回
        if package_key in self._loaded_packages:
            self._reference_count[package_key] += 1
            return self._loaded_packages[package_key]

        # 解析依赖
        resolve_result = self.resolver.resolve(name, version)
        load_order = resolve_result["load_order"]

        # 按依赖顺序加载所有包
        for dep_name, dep_version in load_order:
            dep_key = (dep_name, dep_version)

            # 如果依赖已加载，跳过
            if dep_key in self._loaded_packages:
                self._reference_count[dep_key] += 1
                continue

            # 加载依赖
            self._load_single_package(dep_name, dep_version, context)

        # 返回目标包的模块对象
        return self._loaded_packages[package_key]

    def _load_single_package(self, name, version, context=None):
        """加载单个包

        Args:
            name: 包名
            version: 版本号
            context: 上下文信息

        Raises:
            PackageNotFoundError: 包不存在
            DependencyError: 加载失败
        """
        package_key = (name, version)

        # 获取包信息
        try:
            metadata = self.registry.get(name, version)
        except (PackageNotFoundError, VersionNotFoundError) as e:
            raise e

        # 读取 package.json
        package_json_path = metadata.get("package_json_path")
        if not package_json_path or not os.path.exists(package_json_path):
            raise DependencyError(
                f"package.json not found for {name}@{version}",
                name
            )

        with open(package_json_path, 'r') as f:
            package_json = json.load(f)

        # 构建虚拟文件系统
        package_path = self.build_virtual_fs(name, version, package_json)
        self._package_paths[package_key] = package_path

        # 添加到 sys.path
        self.add_to_path(package_path)

        try:
            # 导入模块
            if name in sys.modules:
                # 模块已存在，重新加载
                module = sys.modules[name]
                importlib.reload(module)
            else:
                # 导入新模块
                module = importlib.import_module(name)

            # 应用 patches
            if self.patcher.has_patches(name, version, context):
                self.patcher.apply_patches(module, name, version, context)

            # 记录加载信息
            self._loaded_packages[package_key] = module
            self._reference_count[package_key] = 1

        except Exception as e:
            # 加载失败，清理 sys.path
            self.remove_from_path(package_path)
            raise DependencyError(
                f"Failed to load package {name}@{version}: {e}",
                name
            )

    def unload(self, name, version):
        """卸载包（清理 sys.modules）

        Args:
            name: 包名
            version: 版本号

        Raises:
            PackageNotFoundError: 包未加载
        """
        package_key = (name, version)

        if package_key not in self._loaded_packages:
            raise PackageNotFoundError(f"{name}@{version} is not loaded")

        # 减少引用计数
        self._reference_count[package_key] -= 1

        # 如果引用计数为 0，真正卸载
        if self._reference_count[package_key] <= 0:
            # 从 sys.modules 移除
            if name in sys.modules:
                del sys.modules[name]

            # 从 sys.path 移除
            package_path = self._package_paths.get(package_key)
            if package_path:
                self.remove_from_path(package_path)
                del self._package_paths[package_key]

            # 清理记录
            del self._loaded_packages[package_key]
            del self._reference_count[package_key]

    def build_virtual_fs(self, name, version, package_json):
        """根据 hash 构建虚拟文件系统

        将对象池中的文件复制或链接到包目录，重建包结构。

        Args:
            name: 包名
            version: 版本号
            package_json: package.json 内容

        Returns:
            str: 包的父目录路径（用于添加到 sys.path）

        Raises:
            DependencyError: 构建失败
        """
        # 运行时目录: packages/_runtime/{name}@{version}/
        # 包目录: packages/_runtime/{name}@{version}/{name}/
        # 这样可以通过 import {name} 正确导入
        runtime_dir = os.path.join("packages", "_runtime", f"{name}@{version}")
        package_dir = os.path.join(runtime_dir, name)

        # 确保包目录存在
        if not os.path.exists(package_dir):
            os.makedirs(package_dir)

        # 获取文件列表
        files = package_json.get("files", {})

        # 遍历每个文件
        for relative_path, file_info in files.items():
            file_hash = file_info.get("hash")
            if not file_hash:
                raise DependencyError(
                    f"No hash found for file '{relative_path}' in {name}@{version}",
                    name
                )

            # 目标文件路径
            target_path = os.path.join(package_dir, relative_path)

            # 如果文件已存在且哈希正确，跳过
            if os.path.exists(target_path):
                try:
                    from .hasher import verify_hash
                    verify_hash(target_path, file_hash)
                    continue  # 文件已存在且正确
                except:
                    pass  # 文件损坏，需要重新创建

            # 确保目标目录存在
            target_dir = os.path.dirname(target_path)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir)

            # 从对象池获取文件
            object_path = self.fetcher.get_object(file_hash)
            if not object_path:
                # 对象不存在，尝试下载
                sources = file_info.get("sources", [])
                if not sources:
                    raise DependencyError(
                        f"No sources found for file '{relative_path}' in {name}@{version}",
                        name
                    )
                object_path = self.fetcher.fetch(sources, file_hash)

            # 复制文件到包目录
            try:
                with open(object_path, 'rb') as src:
                    content = src.read()
                with open(target_path, 'wb') as dst:
                    dst.write(content)
            except Exception as e:
                raise DependencyError(
                    f"Failed to copy file '{relative_path}' for {name}@{version}: {e}",
                    name
                )

        # 返回运行时目录（父目录），这样 import {name} 可以找到包
        return runtime_dir

    def add_to_path(self, path):
        """添加路径到 sys.path

        Args:
            path: 要添加的路径
        """
        # 规范化路径
        normalized_path = os.path.abspath(path)

        # 如果路径不在 sys.path 中，添加到开头
        if normalized_path not in sys.path:
            sys.path.insert(0, normalized_path)

    def remove_from_path(self, path):
        """从 sys.path 移除路径

        Args:
            path: 要移除的路径
        """
        # 规范化路径
        normalized_path = os.path.abspath(path)

        # 移除所有匹配的路径
        while normalized_path in sys.path:
            sys.path.remove(normalized_path)

    def is_loaded(self, name, version):
        """检查包是否已加载

        Args:
            name: 包名
            version: 版本号

        Returns:
            bool: 是否已加载
        """
        return (name, version) in self._loaded_packages

    def get_loaded_packages(self):
        """获取所有已加载的包

        Returns:
            list: [(name, version), ...] 已加载的包列表
        """
        return list(self._loaded_packages.keys())

    def get_reference_count(self, name, version):
        """获取包的引用计数

        Args:
            name: 包名
            version: 版本号

        Returns:
            int: 引用计数（0 表示未加载）
        """
        return self._reference_count.get((name, version), 0)

    def reload(self, name, version, context=None):
        """重新加载包

        Args:
            name: 包名
            version: 版本号
            context: 上下文信息

        Returns:
            module: 重新加载后的模块对象
        """
        package_key = (name, version)

        # 如果已加载，先卸载
        if package_key in self._loaded_packages:
            ref_count = self._reference_count[package_key]
            self.unload(name, version)
            # 恢复引用计数为 0，因为 load 会设置为 1
            if package_key in self._reference_count:
                self._reference_count[package_key] = 0

        # 重新加载
        module = self.load(name, version, context)

        # 恢复引用计数
        if package_key in self._reference_count:
            self._reference_count[package_key] = ref_count

        return module

    def clear_all(self):
        """卸载所有已加载的包"""
        # 复制键列表，避免在迭代时修改字典
        packages = list(self._loaded_packages.keys())

        for name, version in packages:
            # 强制卸载（忽略引用计数）
            self._reference_count[(name, version)] = 1
            try:
                self.unload(name, version)
            except:
                pass  # 忽略错误
