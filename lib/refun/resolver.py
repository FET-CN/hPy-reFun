"""
reFun 依赖解析器模块

提供依赖树解析、拓扑排序和循环依赖检测功能。
"""

import os
try:
    import ujson as json
except ImportError:
    import json

from .exceptions import (
    DependencyError,
    CircularDependencyError,
    PackageNotFoundError,
    VersionNotFoundError
)
from .version import parse_version, parse_constraint, Version


class DependencyResolver:
    """依赖解析器类

    负责解析包依赖关系，检测循环依赖，并生成拓扑排序的加载顺序。

    Attributes:
        registry: 包注册表实例
        _resolved: 已解析的包缓存 {(name, version): metadata}
        _resolving: 正在解析的包栈（用于检测循环依赖）
    """

    def __init__(self, registry):
        """初始化依赖解析器

        Args:
            registry: Registry 实例，用于查询已安装的包
        """
        self.registry = registry
        self._resolved = {}
        self._resolving = []

    def resolve(self, package_name, version_constraint=None):
        """解析单个包的依赖

        Args:
            package_name: 包名
            version_constraint: 版本约束字符串，None 表示最新版本

        Returns:
            dict: 解析结果，包含依赖树和加载顺序
            {
                "dependencies": {(name, version): metadata},
                "load_order": [(name, version), ...]
            }

        Raises:
            PackageNotFoundError: 包不存在
            VersionNotFoundError: 无法找到满足约束的版本
            CircularDependencyError: 检测到循环依赖
            DependencyError: 依赖解析失败
        """
        # 清空缓存
        self._resolved = {}
        self._resolving = []

        # 查找匹配的版本
        version = self._find_matching_version(package_name, version_constraint)

        # 递归解析依赖
        self._resolve_recursive(package_name, version)

        # 拓扑排序
        load_order = self._topological_sort()

        return {
            "dependencies": dict(self._resolved),
            "load_order": load_order
        }

    def resolve_all(self, packages):
        """解析多个包的依赖

        Args:
            packages: 包列表，每个元素为 (name, version_constraint) 元组

        Returns:
            dict: 解析结果
            {
                "dependencies": {(name, version): metadata},
                "load_order": [(name, version), ...]
            }

        Raises:
            DependencyError: 依赖解析失败
        """
        self._resolved = {}
        self._resolving = []

        # 解析每个包的依赖
        for package_name, version_constraint in packages:
            version = self._find_matching_version(package_name, version_constraint)
            if (package_name, version) not in self._resolved:
                self._resolve_recursive(package_name, version)

        # 拓扑排序
        load_order = self._topological_sort()

        return {
            "dependencies": dict(self._resolved),
            "load_order": load_order
        }

    def _find_matching_version(self, package_name, version_constraint):
        """查找满足约束的版本

        Args:
            package_name: 包名
            version_constraint: 版本约束字符串或 None

        Returns:
            str: 匹配的版本号

        Raises:
            PackageNotFoundError: 包不存在
            VersionNotFoundError: 无法找到满足约束的版本
        """
        if not self.registry.has_package(package_name):
            raise PackageNotFoundError(package_name)

        versions = self.registry.list_versions(package_name)
        if not versions:
            raise PackageNotFoundError(package_name)

        # 如果没有约束，返回最新版本
        if version_constraint is None:
            return self.registry.get_latest_version(package_name)

        # 如果是精确版本
        try:
            parse_version(version_constraint)
            # 是有效的版本号，直接返回
            if version_constraint in versions:
                return version_constraint
            else:
                raise VersionNotFoundError(package_name, version_constraint)
        except ValueError:
            # 不是精确版本号，是约束表达式
            pass

        # 解析约束
        try:
            constraint = parse_constraint(version_constraint)
        except ValueError as e:
            raise DependencyError(
                f"Invalid version constraint '{version_constraint}' for package '{package_name}': {e}",
                package_name
            )

        # 查找所有满足约束的版本
        matching_versions = []
        for v in versions:
            try:
                version_obj = parse_version(v)
                if constraint.match(version_obj):
                    matching_versions.append(version_obj)
            except ValueError:
                continue

        if not matching_versions:
            raise VersionNotFoundError(
                package_name,
                f"No version matches constraint '{version_constraint}'"
            )

        # 返回最高版本
        matching_versions.sort(reverse=True)
        return str(matching_versions[0])

    def _resolve_recursive(self, package_name, version):
        """递归解析依赖

        Args:
            package_name: 包名
            version: 版本号字符串

        Raises:
            CircularDependencyError: 检测到循环依赖
            DependencyError: 依赖解析失败
        """
        package_key = (package_name, version)

        # 已经解析过，跳过
        if package_key in self._resolved:
            return

        # 检测循环依赖
        if package_key in self._resolving:
            cycle = self._resolving[self._resolving.index(package_key):] + [package_key]
            cycle_str = [f"{name}@{ver}" for name, ver in cycle]
            raise CircularDependencyError(cycle_str)

        # 标记为正在解析
        self._resolving.append(package_key)

        try:
            # 获取包信息
            metadata = self.registry.get(package_name, version)

            # 读取 package.json
            package_json_path = metadata.get("package_json_path")
            if not package_json_path:
                raise DependencyError(
                    f"No package.json path found for {package_name}@{version}",
                    package_name
                )

            if not os.path.exists(package_json_path):
                raise DependencyError(
                    f"package.json not found at {package_json_path}",
                    package_name
                )

            with open(package_json_path, 'r') as f:
                package_json = json.load(f)

            # 获取依赖
            dependencies = package_json.get("dependencies", {})

            # 递归解析每个依赖
            for dep_name, dep_constraint in dependencies.items():
                # 查找满足约束的版本
                dep_version = self._find_matching_version(dep_name, dep_constraint)

                # 检查版本冲突
                dep_key = (dep_name, dep_version)
                if dep_name in [name for name, _ in self._resolved.keys()]:
                    # 已经解析过这个包的其他版本
                    existing_versions = [ver for name, ver in self._resolved.keys() if name == dep_name]
                    if dep_version not in existing_versions:
                        # 版本冲突
                        raise DependencyError(
                            f"Version conflict for '{dep_name}': "
                            f"need {dep_version} (from {package_name}@{version}), "
                            f"but already have {existing_versions}",
                            dep_name
                        )

                # 递归解析依赖的依赖
                self._resolve_recursive(dep_name, dep_version)

            # 添加到已解析列表
            self._resolved[package_key] = {
                "package_json": package_json,
                "metadata": metadata,
                "dependencies": dependencies
            }

        finally:
            # 从正在解析列表中移除
            self._resolving.remove(package_key)

    def _topological_sort(self):
        """拓扑排序，返回加载顺序

        使用 Kahn 算法进行拓扑排序。

        Returns:
            list: [(name, version), ...] 按依赖顺序排列

        Raises:
            DependencyError: 无法进行拓扑排序（理论上不应该发生）
        """
        # 构建依赖图
        graph = {}  # {package_key: [dependent_keys]}
        in_degree = {}  # {package_key: in_degree_count}

        for package_key, info in self._resolved.items():
            if package_key not in graph:
                graph[package_key] = []
            if package_key not in in_degree:
                in_degree[package_key] = 0

            # 添加依赖边
            dependencies = info.get("dependencies", {})
            for dep_name, dep_constraint in dependencies.items():
                # 查找已解析的依赖版本
                dep_key = None
                for resolved_key in self._resolved.keys():
                    if resolved_key[0] == dep_name:
                        dep_key = resolved_key
                        break

                if dep_key:
                    # 添加边: dep_key -> package_key (依赖指向被依赖者)
                    if dep_key not in graph:
                        graph[dep_key] = []
                    graph[dep_key].append(package_key)

                    # 增加入度
                    in_degree[package_key] = in_degree.get(package_key, 0) + 1

        # Kahn 算法
        queue = [key for key in in_degree.keys() if in_degree[key] == 0]
        result = []

        while queue:
            # 从队列中取出一个入度为 0 的节点
            current = queue.pop(0)
            result.append(current)

            # 移除该节点的所有出边
            for neighbor in graph.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 检查是否所有节点都已排序
        if len(result) != len(self._resolved):
            raise DependencyError("Failed to perform topological sort (cyclic dependency?)")

        return result

    def get_load_order(self, packages):
        """获取加载顺序（便捷方法）

        Args:
            packages: 包列表 [(name, version_constraint), ...]

        Returns:
            list: [(name, version), ...] 加载顺序
        """
        result = self.resolve_all(packages)
        return result["load_order"]

    def detect_circular(self, package_name, version_constraint=None):
        """检测循环依赖

        Args:
            package_name: 包名
            version_constraint: 版本约束

        Returns:
            list or None: 如果存在循环依赖，返回循环路径，否则返回 None
        """
        try:
            self.resolve(package_name, version_constraint)
            return None
        except CircularDependencyError as e:
            return e.dependency_chain
