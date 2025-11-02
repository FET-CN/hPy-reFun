"""
reFun 包管理器模块

提供统一的包管理 API，包括安装、卸载、加载、运行等功能。
这是 reFun 包管理器的主要对外接口。
"""

import os
import sys
try:
    import ujson as json
except ImportError:
    import json

from .exceptions import (
    PackageNotFoundError,
    VersionNotFoundError,
    DependencyError,
    RegistryError
)
from .registry import Registry
from .resolver import DependencyResolver
from .fetcher import Fetcher
from .patcher import PatchManager
from .loader import PackageLoader
from .hasher import compute_hash


class PackageManager:
    """包管理器类

    提供统一的包管理接口，整合所有核心功能模块。

    Attributes:
        registry: 包注册表
        fetcher: 文件获取器
        patcher: Patch 管理器
        resolver: 依赖解析器
        loader: 包加载器
        storage_path: 存储根目录
        packages_path: 包目录
    """

    def __init__(self, storage_path="storage", packages_path="packages"):
        """初始化包管理器

        Args:
            storage_path: 存储根目录
            packages_path: 包目录
        """
        self.storage_path = storage_path
        self.packages_path = packages_path

        # 初始化核心模块
        self.registry = Registry(os.path.join(storage_path, "registry.json"))
        self.fetcher = Fetcher(
            storage_path=os.path.join(storage_path, "objects"),
            cache_path=os.path.join(storage_path, "cache")
        )
        self.patcher = PatchManager()
        self.resolver = DependencyResolver(self.registry)
        self.loader = PackageLoader(
            self.registry,
            self.resolver,
            self.patcher,
            self.fetcher
        )

        # 确保目录存在
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要的目录存在"""
        dirs = [
            self.storage_path,
            os.path.join(self.storage_path, "objects"),
            os.path.join(self.storage_path, "cache"),
            self.packages_path
        ]
        for dir_path in dirs:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

    # ==================== 安装相关 ====================

    def install(self, name, version, source="index"):
        """从包索引安装包

        Args:
            name: 包名
            version: 版本号
            source: 索引服务器 URL（默认为 "index"）

        Raises:
            DownloadError: 下载失败
            RegistryError: 注册失败
        """
        # TODO: 实现从索引服务器下载
        # 这里暂时抛出未实现错误
        raise NotImplementedError(
            "Install from index server not implemented yet. "
            "Use install_from_local() or install_from_url() instead."
        )

    def install_from_url(self, url, name=None, version=None):
        """从 URL 安装 package.json

        Args:
            url: package.json 的 URL
            name: 包名（可选，从 package.json 读取）
            version: 版本号（可选，从 package.json 读取）

        Returns:
            dict: 安装信息 {"name": str, "version": str}

        Raises:
            DownloadError: 下载失败
            RegistryError: 注册失败
        """
        # 下载 package.json
        package_json = self.fetcher.fetch_package_json(
            name or "unknown",
            version or "unknown",
            [url]
        )

        # 从 package.json 获取包信息
        pkg_name = package_json.get("name")
        pkg_version = package_json.get("version")

        if not pkg_name or not pkg_version:
            raise DependencyError(
                "package.json must contain 'name' and 'version' fields",
                pkg_name or "unknown"
            )

        # 安装包
        return self._install_from_package_json(package_json, pkg_name, pkg_version)

    def install_from_local(self, path):
        """从本地路径安装

        Args:
            path: 本地 package.json 文件路径或包目录

        Returns:
            dict: 安装信息 {"name": str, "version": str}

        Raises:
            PackageNotFoundError: 文件不存在
            RegistryError: 注册失败
        """
        # 确定 package.json 路径
        if os.path.isdir(path):
            package_json_path = os.path.join(path, "package.json")
        else:
            package_json_path = path

        if not os.path.exists(package_json_path):
            raise PackageNotFoundError(f"package.json not found at {path}")

        # 读取 package.json
        with open(package_json_path, 'r') as f:
            package_json = json.load(f)

        pkg_name = package_json.get("name")
        pkg_version = package_json.get("version")

        if not pkg_name or not pkg_version:
            raise DependencyError(
                "package.json must contain 'name' and 'version' fields",
                pkg_name or "unknown"
            )

        # 安装包
        return self._install_from_package_json(
            package_json,
            pkg_name,
            pkg_version,
            local_base_path=os.path.dirname(package_json_path)
        )

    def register_local(self, path, name=None, version=None):
        """将本地文件夹注册为包

        扫描文件夹，计算 hash，生成 package.json，注册到系统。

        Args:
            path: 本地文件夹路径
            name: 包名（None 表示使用文件夹名）
            version: 版本号（None 表示使用 "0.1.0"）

        Returns:
            dict: 注册信息 {"name": str, "version": str}

        Raises:
            PackageNotFoundError: 路径不存在
            RegistryError: 注册失败
        """
        if not os.path.exists(path) or not os.path.isdir(path):
            raise PackageNotFoundError(f"Directory not found: {path}")

        # 确定包名和版本
        if name is None:
            name = os.path.basename(os.path.abspath(path))
        if version is None:
            version = "0.1.0"

        # 扫描文件并计算 hash
        files = {}
        for root, dirs, filenames in os.walk(path):
            # 跳过隐藏目录和特殊目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

            for filename in filenames:
                # 跳过隐藏文件和编译文件
                if filename.startswith('.') or filename.endswith('.pyc'):
                    continue

                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, path)

                # 计算文件 hash 并复制到对象池
                try:
                    object_path, file_hash = self.fetcher.copy_to_object(file_path)
                    files[relative_path] = {
                        "hash": file_hash,
                        "sources": [f"local://{object_path}"]
                    }
                except Exception as e:
                    print(f"Warning: Failed to process {relative_path}: {e}")
                    continue

        # 生成 package.json
        package_json = {
            "name": name,
            "version": version,
            "description": f"Local package registered from {path}",
            "files": files,
            "dependencies": {}
        }

        # 安装包
        return self._install_from_package_json(package_json, name, version)

    def _install_from_package_json(self, package_json, name, version, local_base_path=None):
        """从 package.json 安装包

        Args:
            package_json: package.json 内容
            name: 包名
            version: 版本号
            local_base_path: 本地基础路径（用于本地安装）

        Returns:
            dict: 安装信息
        """
        # 检查是否已安装
        if self.registry.has_version(name, version):
            print(f"Package {name}@{version} is already installed")
            return {"name": name, "version": version, "status": "already_installed"}

        # 创建包目录
        package_dir = os.path.join(self.packages_path, name, version)
        if not os.path.exists(package_dir):
            os.makedirs(package_dir)

        # 保存 package.json
        package_json_path = os.path.join(package_dir, "package.json")
        with open(package_json_path, 'w') as f:
            json.dump(package_json, f, indent=2)

        # 下载/复制文件到对象池
        files = package_json.get("files", {})
        for relative_path, file_info in files.items():
            file_hash = file_info.get("hash")
            sources = file_info.get("sources", [])

            # 如果是本地安装，添加本地路径到源
            if local_base_path:
                local_file_path = os.path.join(local_base_path, relative_path)
                if os.path.exists(local_file_path):
                    sources.insert(0, f"local://{local_file_path}")

            # 检查对象是否已存在
            if not self.fetcher.has_object(file_hash):
                # 下载/复制文件
                try:
                    self.fetcher.fetch(sources, file_hash)
                except Exception as e:
                    print(f"Warning: Failed to fetch {relative_path}: {e}")
                    continue

        # 处理 patches
        patches = package_json.get("patches", {})
        if patches:
            # 注册 global patches
            for target in patches.get("global", []):
                if "@" in target:
                    target_name, target_version = target.split("@", 1)
                    patch_path = os.path.join(package_dir, "__patch__.py")
                    if os.path.exists(patch_path):
                        self.patcher.register_patch(
                            name, version,
                            target_name, target_version,
                            "global",
                            patch_path
                        )

            # 注册 local patches
            for target in patches.get("local", []):
                if "@" in target:
                    target_name, target_version = target.split("@", 1)
                    patch_path = os.path.join(package_dir, "__patch__.py")
                    if os.path.exists(patch_path):
                        self.patcher.register_patch(
                            name, version,
                            target_name, target_version,
                            "local",
                            patch_path
                        )

        # 注册到注册表
        metadata = {
            "package_json_path": package_json_path,
            "description": package_json.get("description", ""),
            "author": package_json.get("author", ""),
        }
        self.registry.register(name, version, metadata)

        return {"name": name, "version": version, "status": "installed"}

    # ==================== 卸载相关 ====================

    def uninstall(self, name, version):
        """卸载指定版本

        Args:
            name: 包名
            version: 版本号

        Raises:
            PackageNotFoundError: 包不存在
        """
        # 检查包是否存在
        if not self.registry.has_version(name, version):
            raise PackageNotFoundError(f"{name}@{version}")

        # 如果包已加载，先卸载
        if self.loader.is_loaded(name, version):
            self.loader.unload(name, version)

        # 从注册表注销
        self.registry.unregister(name, version)

        # 删除包目录（可选，这里保留文件）
        # package_dir = os.path.join(self.packages_path, name, version)
        # if os.path.exists(package_dir):
        #     shutil.rmtree(package_dir)

        print(f"Uninstalled {name}@{version}")

    def uninstall_all(self, name):
        """卸载包的所有版本

        Args:
            name: 包名
        """
        if not self.registry.has_package(name):
            raise PackageNotFoundError(name)

        versions = self.registry.list_versions(name)
        for version in versions:
            try:
                self.uninstall(name, version)
            except Exception as e:
                print(f"Failed to uninstall {name}@{version}: {e}")

    def cleanup_unused_objects(self):
        """清理未被引用的对象

        扫描对象池，删除未被任何包引用的对象。

        Returns:
            dict: 清理统计 {"removed": int, "kept": int, "errors": int}
        """
        # 收集所有被引用的 hash
        referenced_hashes = set()

        for pkg_info in self.registry.list_packages():
            name = pkg_info["name"]
            for version in pkg_info["versions"]:
                try:
                    metadata = self.registry.get(name, version)
                    package_json_path = metadata.get("package_json_path")

                    if package_json_path and os.path.exists(package_json_path):
                        with open(package_json_path, 'r') as f:
                            package_json = json.load(f)

                        files = package_json.get("files", {})
                        for file_info in files.values():
                            file_hash = file_info.get("hash")
                            if file_hash:
                                referenced_hashes.add(file_hash)
                except Exception:
                    continue

        # 扫描对象池
        objects_path = os.path.join(self.storage_path, "objects")
        removed = 0
        kept = 0
        errors = 0

        if not os.path.exists(objects_path):
            return {"removed": 0, "kept": 0, "errors": 0}

        for dir_name in os.listdir(objects_path):
            dir_path = os.path.join(objects_path, dir_name)
            if not os.path.isdir(dir_path):
                continue

            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                if not os.path.isfile(file_path):
                    continue

                # 重建 hash
                file_hash = dir_name + filename

                # 检查是否被引用
                if file_hash in referenced_hashes:
                    kept += 1
                else:
                    # 删除未引用的文件
                    try:
                        os.remove(file_path)
                        removed += 1
                    except Exception:
                        errors += 1

        return {"removed": removed, "kept": kept, "errors": errors}

    # ==================== 加载相关 ====================

    def load(self, name, version=None, context=None):
        """加载包

        Args:
            name: 包名
            version: 版本号（None 表示加载最新版本）
            context: 上下文信息

        Returns:
            module: 包的模块对象
        """
        return self.loader.load(name, version, context)

    def unload(self, name, version):
        """卸载包（从内存）

        Args:
            name: 包名
            version: 版本号
        """
        self.loader.unload(name, version)

    def reload(self, name, version, context=None):
        """重新加载包

        Args:
            name: 包名
            version: 版本号
            context: 上下文信息

        Returns:
            module: 重新加载后的模块对象
        """
        return self.loader.reload(name, version, context)

    # ==================== 运行相关 ====================

    def run(self, name, version=None):
        """执行包的 __main__.py 或 entry 文件

        Args:
            name: 包名
            version: 版本号（None 表示最新版本）

        Raises:
            PackageNotFoundError: 包不存在
            DependencyError: 没有可执行入口
        """
        # 确定版本
        if version is None:
            version = self.registry.get_latest_version(name)

        # 检查是否有入口文件
        metadata = self.registry.get(name, version)
        package_json_path = metadata.get("package_json_path")

        if not package_json_path or not os.path.exists(package_json_path):
            raise DependencyError(
                f"package.json not found for {name}@{version}",
                name
            )

        with open(package_json_path, 'r') as f:
            package_json = json.load(f)

        # 获取入口文件
        entry = package_json.get("entry", "__main__.py")

        # 构建入口文件路径
        package_dir = os.path.join(self.packages_path, name, version)
        entry_path = os.path.join(package_dir, entry)

        if not os.path.exists(entry_path):
            raise DependencyError(
                f"Entry file '{entry}' not found for {name}@{version}",
                name
            )

        # 加载包（包括依赖）
        self.load(name, version)

        # 执行入口文件
        try:
            with open(entry_path, 'r') as f:
                code = f.read()

            # 创建执行环境
            exec_globals = {
                "__name__": "__main__",
                "__file__": entry_path,
            }

            # 执行代码
            exec(code, exec_globals)

        except Exception as e:
            raise DependencyError(
                f"Failed to run {name}@{version}: {e}",
                name
            )

    def has_entry(self, name, version):
        """检查包是否有可执行入口

        Args:
            name: 包名
            version: 版本号

        Returns:
            bool: 是否有入口文件
        """
        try:
            metadata = self.registry.get(name, version)
            package_json_path = metadata.get("package_json_path")

            if not package_json_path or not os.path.exists(package_json_path):
                return False

            with open(package_json_path, 'r') as f:
                package_json = json.load(f)

            entry = package_json.get("entry", "__main__.py")
            package_dir = os.path.join(self.packages_path, name, version)
            entry_path = os.path.join(package_dir, entry)

            return os.path.exists(entry_path)

        except Exception:
            return False

    # ==================== 查询相关 ====================

    def list(self):
        """列出所有已安装的包

        Returns:
            list: 包信息列表
        """
        return self.registry.list_packages()

    def list_versions(self, name):
        """列出包的所有版本

        Args:
            name: 包名

        Returns:
            list: 版本号列表
        """
        return self.registry.list_versions(name)

    def info(self, name, version):
        """显示包详细信息

        Args:
            name: 包名
            version: 版本号

        Returns:
            dict: 包的详细信息
        """
        metadata = self.registry.get(name, version)
        package_json_path = metadata.get("package_json_path")

        info = {
            "name": name,
            "version": version,
            "description": metadata.get("description", ""),
            "author": metadata.get("author", ""),
            "loaded": self.loader.is_loaded(name, version),
        }

        if package_json_path and os.path.exists(package_json_path):
            with open(package_json_path, 'r') as f:
                package_json = json.load(f)

            info["dependencies"] = package_json.get("dependencies", {})
            info["files_count"] = len(package_json.get("files", {}))
            info["has_entry"] = self.has_entry(name, version)
            info["entry"] = package_json.get("entry", "__main__.py")
            info["patches"] = package_json.get("patches", {})

        return info

    def search(self, keyword):
        """搜索包（本地搜索）

        Args:
            keyword: 搜索关键词

        Returns:
            list: 匹配的包列表
        """
        keyword_lower = keyword.lower()
        results = []

        for pkg_info in self.registry.list_packages():
            name = pkg_info["name"]
            if keyword_lower in name.lower():
                results.append(pkg_info)
                continue

            # 搜索描述
            for version in pkg_info["versions"]:
                try:
                    metadata = self.registry.get(name, version)
                    description = metadata.get("description", "")
                    if keyword_lower in description.lower():
                        results.append(pkg_info)
                        break
                except Exception:
                    continue

        return results
