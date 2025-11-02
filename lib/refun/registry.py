"""
reFun 包注册表模块

提供包注册、查询和持久化功能，管理已安装包的元数据。
"""

import os
try:
    import ujson as json
except ImportError:
    import json

from .exceptions import PackageNotFoundError, VersionNotFoundError, RegistryError


class Registry:
    """包注册表类

    负责管理已安装包的信息，提供注册、注销、查询和持久化功能。

    Attributes:
        registry_path: registry.json 文件路径
        _data: 内存中的注册表数据
    """

    def __init__(self, registry_path="storage/registry.json"):
        """初始化注册表

        Args:
            registry_path: registry.json 文件路径
        """
        self.registry_path = registry_path
        self._data = {"packages": {}}
        self._ensure_storage_dir()
        self.load()

    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        storage_dir = os.path.dirname(self.registry_path)
        if storage_dir and not os.path.exists(storage_dir):
            try:
                os.makedirs(storage_dir)
            except OSError as e:
                raise RegistryError("create_storage_dir", str(e))

    def register(self, name, version, metadata=None):
        """注册包

        Args:
            name: 包名
            version: 版本号字符串
            metadata: 包元数据字典，可包含:
                - package_json_path: package.json 路径
                - description: 描述
                - author: 作者
                等其他自定义字段

        Raises:
            RegistryError: 注册失败
        """
        if metadata is None:
            metadata = {}

        # 初始化包条目
        if name not in self._data["packages"]:
            self._data["packages"][name] = {}

        # 注册版本
        self._data["packages"][name][version] = metadata

        # 自动保存
        try:
            self.save()
        except Exception as e:
            # 回滚
            if version in self._data["packages"][name]:
                del self._data["packages"][name][version]
            if not self._data["packages"][name]:
                del self._data["packages"][name]
            raise RegistryError("register", str(e))

    def unregister(self, name, version):
        """注销包

        Args:
            name: 包名
            version: 版本号字符串

        Raises:
            PackageNotFoundError: 包不存在
            VersionNotFoundError: 版本不存在
            RegistryError: 注销失败
        """
        if name not in self._data["packages"]:
            raise PackageNotFoundError(name)

        if version not in self._data["packages"][name]:
            raise VersionNotFoundError(name, version)

        # 删除版本
        del self._data["packages"][name][version]

        # 如果包没有其他版本，删除包条目
        if not self._data["packages"][name]:
            del self._data["packages"][name]

        # 自动保存
        try:
            self.save()
        except Exception as e:
            raise RegistryError("unregister", str(e))

    def get(self, name, version):
        """获取包信息

        Args:
            name: 包名
            version: 版本号字符串

        Returns:
            包的元数据字典

        Raises:
            PackageNotFoundError: 包不存在
            VersionNotFoundError: 版本不存在
        """
        if name not in self._data["packages"]:
            raise PackageNotFoundError(name)

        if version not in self._data["packages"][name]:
            raise VersionNotFoundError(name, version)

        return self._data["packages"][name][version]

    def has_package(self, name):
        """检查包是否存在

        Args:
            name: 包名

        Returns:
            bool: 包是否存在
        """
        return name in self._data["packages"]

    def has_version(self, name, version):
        """检查包的特定版本是否存在

        Args:
            name: 包名
            version: 版本号字符串

        Returns:
            bool: 版本是否存在
        """
        return (name in self._data["packages"] and
                version in self._data["packages"][name])

    def list_packages(self):
        """列出所有已安装的包

        Returns:
            list: 包信息列表，每个元素为 {"name": str, "versions": [str]}
        """
        packages = []
        for name, versions in self._data["packages"].items():
            packages.append({
                "name": name,
                "versions": list(versions.keys())
            })
        return packages

    def list_versions(self, name):
        """列出包的所有版本

        Args:
            name: 包名

        Returns:
            list: 版本号字符串列表

        Raises:
            PackageNotFoundError: 包不存在
        """
        if name not in self._data["packages"]:
            raise PackageNotFoundError(name)

        return list(self._data["packages"][name].keys())

    def get_latest_version(self, name):
        """获取包的最新版本号

        Args:
            name: 包名

        Returns:
            str: 最新版本号

        Raises:
            PackageNotFoundError: 包不存在
        """
        versions = self.list_versions(name)
        if not versions:
            raise PackageNotFoundError(name)

        # 导入版本模块进行比较
        from .version import Version

        version_objs = [Version(v) for v in versions]
        version_objs.sort(reverse=True)
        return str(version_objs[0])

    def save(self):
        """保存注册表到文件

        将内存中的注册表数据持久化到 registry.json 文件。

        Raises:
            RegistryError: 保存失败
        """
        self._ensure_storage_dir()

        try:
            # 先写入临时文件，然后重命名（原子操作）
            temp_path = self.registry_path + ".tmp"
            with open(temp_path, 'w') as f:
                json.dump(self._data, f, indent=2)

            # 重命名
            if os.path.exists(self.registry_path):
                os.remove(self.registry_path)
            os.rename(temp_path, self.registry_path)

        except Exception as e:
            raise RegistryError("save", str(e))

    def load(self):
        """从文件加载注册表

        从 registry.json 文件读取注册表数据到内存。
        如果文件不存在，则初始化空注册表。

        Raises:
            RegistryError: 加载失败
        """
        if not os.path.exists(self.registry_path):
            # 文件不存在，初始化空注册表
            self._data = {"packages": {}}
            return

        try:
            with open(self.registry_path, 'r') as f:
                self._data = json.load(f)

            # 验证数据结构
            if "packages" not in self._data:
                self._data = {"packages": {}}

        except Exception as e:
            raise RegistryError("load", str(e))

    def clear(self):
        """清空注册表

        删除所有已注册的包信息（仅清空内存，不删除文件）。
        """
        self._data = {"packages": {}}

    def export_data(self):
        """导出注册表数据

        Returns:
            dict: 注册表数据的深拷贝
        """
        # 简单的深拷贝（通过序列化）
        try:
            return json.loads(json.dumps(self._data))
        except:
            # fallback: 手动拷贝
            return {"packages": dict(self._data["packages"])}

    def import_data(self, data):
        """导入注册表数据

        Args:
            data: 要导入的注册表数据字典

        Raises:
            RegistryError: 数据格式无效
        """
        if not isinstance(data, dict) or "packages" not in data:
            raise RegistryError("import_data", "Invalid data format")

        self._data = data
        self.save()
