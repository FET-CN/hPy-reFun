"""
reFun MonkeyPatch 管理器模块

提供 MonkeyPatch 注册、管理和应用功能，支持全局和局部 patch。
"""

import os
import sys
import importlib

from .exceptions import PatchError


class PatchManager:
    """MonkeyPatch 管理器类

    负责管理和应用 MonkeyPatch，支持全局 patch（对所有使用者生效）
    和局部 patch（仅对特定包生效）。

    Attributes:
        _global_patches: 全局 patch 注册表
            {target_package: [(source_package, patch_module), ...]}
        _local_patches: 局部 patch 注册表
            {(source_package, target_package): patch_module}
        _applied_patches: 已应用的 patch 记录
            {(target_package, target_version): [patch_info, ...]}
    """

    def __init__(self):
        """初始化 MonkeyPatch 管理器"""
        self._global_patches = {}
        self._local_patches = {}
        self._applied_patches = {}

    def register_patch(self, source_package, source_version, target_package,
                      target_version, patch_type, patch_module_path):
        """注册 patch

        Args:
            source_package: 提供 patch 的包名
            source_version: 提供 patch 的包版本
            target_package: 目标包名（被 patch 的包）
            target_version: 目标包版本（支持版本约束）
            patch_type: patch 类型 ("global" 或 "local")
            patch_module_path: patch 模块路径（__patch__.py）

        Raises:
            PatchError: 注册失败
        """
        source_key = f"{source_package}@{source_version}"
        target_key = f"{target_package}@{target_version}"

        if patch_type == "global":
            # 全局 patch
            if target_key not in self._global_patches:
                self._global_patches[target_key] = []

            self._global_patches[target_key].append({
                "source": source_key,
                "module_path": patch_module_path
            })

        elif patch_type == "local":
            # 局部 patch
            local_key = (source_key, target_key)
            self._local_patches[local_key] = {
                "source": source_key,
                "target": target_key,
                "module_path": patch_module_path
            }

        else:
            raise PatchError(
                source_key,
                target_key,
                f"Invalid patch type: {patch_type}"
            )

    def get_global_patches(self, target_package, target_version):
        """获取针对目标包的所有全局 patch

        Args:
            target_package: 目标包名
            target_version: 目标包版本

        Returns:
            list: patch 信息列表
        """
        target_key = f"{target_package}@{target_version}"
        return self._global_patches.get(target_key, [])

    def get_local_patches(self, source_package, source_version,
                         target_package, target_version):
        """获取特定包之间的局部 patch

        Args:
            source_package: 源包名（使用依赖的包）
            source_version: 源包版本
            target_package: 目标包名（被依赖的包）
            target_version: 目标包版本

        Returns:
            dict or None: patch 信息，不存在则返回 None
        """
        source_key = f"{source_package}@{source_version}"
        target_key = f"{target_package}@{target_version}"
        local_key = (source_key, target_key)

        return self._local_patches.get(local_key)

    def load_patch_module(self, patch_module_path):
        """加载 patch 模块

        Args:
            patch_module_path: __patch__.py 文件路径

        Returns:
            module: 加载的 patch 模块

        Raises:
            PatchError: 加载失败
        """
        if not os.path.exists(patch_module_path):
            raise PatchError(
                "<unknown>",
                "<unknown>",
                f"Patch module not found: {patch_module_path}"
            )

        try:
            # 动态加载模块
            module_dir = os.path.dirname(patch_module_path)
            module_name = os.path.splitext(os.path.basename(patch_module_path))[0]

            # 添加到 sys.path
            if module_dir not in sys.path:
                sys.path.insert(0, module_dir)

            # 导入模块
            spec = importlib.util.spec_from_file_location(module_name, patch_module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            return module

        except Exception as e:
            raise PatchError(
                "<unknown>",
                "<unknown>",
                f"Failed to load patch module: {e}"
            )

    def apply_patches(self, target_module, target_package, target_version, context=None):
        """应用相关的 patch 到目标模块

        Args:
            target_module: 目标模块对象
            target_package: 目标包名
            target_version: 目标包版本
            context: 上下文信息（可包含 source_package, source_version 等）

        Raises:
            PatchError: 应用失败
        """
        target_key = f"{target_package}@{target_version}"
        applied_patches = []

        try:
            # 1. 应用全局 patch
            global_patches = self.get_global_patches(target_package, target_version)
            for patch_info in global_patches:
                self._apply_single_patch(
                    target_module,
                    patch_info["module_path"],
                    patch_info["source"],
                    target_key,
                    "global"
                )
                applied_patches.append(patch_info)

            # 2. 应用局部 patch（如果有上下文信息）
            if context and "source_package" in context and "source_version" in context:
                local_patch = self.get_local_patches(
                    context["source_package"],
                    context["source_version"],
                    target_package,
                    target_version
                )

                if local_patch:
                    self._apply_single_patch(
                        target_module,
                        local_patch["module_path"],
                        local_patch["source"],
                        target_key,
                        "local"
                    )
                    applied_patches.append(local_patch)

            # 记录已应用的 patch
            if target_key not in self._applied_patches:
                self._applied_patches[target_key] = []
            self._applied_patches[target_key].extend(applied_patches)

        except Exception as e:
            if isinstance(e, PatchError):
                raise
            raise PatchError(
                context.get("source_package", "<unknown>") if context else "<unknown>",
                target_key,
                str(e)
            )

    def _apply_single_patch(self, target_module, patch_module_path,
                           source_key, target_key, patch_type):
        """应用单个 patch

        Args:
            target_module: 目标模块对象
            patch_module_path: patch 模块路径
            source_key: 源包标识
            target_key: 目标包标识
            patch_type: patch 类型

        Raises:
            PatchError: 应用失败
        """
        try:
            # 加载 patch 模块
            patch_module = self.load_patch_module(patch_module_path)

            # 检查 PATCHES 导出
            if not hasattr(patch_module, "PATCHES"):
                raise PatchError(
                    source_key,
                    target_key,
                    "Patch module must export 'PATCHES' dictionary"
                )

            patches = patch_module.PATCHES

            # 验证 PATCHES 格式
            if not isinstance(patches, dict):
                raise PatchError(
                    source_key,
                    target_key,
                    "'PATCHES' must be a dictionary"
                )

            # 应用每个 patch 函数
            for patch_name, patch_func in patches.items():
                if not callable(patch_func):
                    raise PatchError(
                        source_key,
                        target_key,
                        f"Patch '{patch_name}' is not callable"
                    )

                # 调用 patch 函数
                patch_func(target_module)

        except Exception as e:
            if isinstance(e, PatchError):
                raise
            raise PatchError(source_key, target_key, str(e))

    def has_patches(self, target_package, target_version, context=None):
        """检查是否有可用的 patch

        Args:
            target_package: 目标包名
            target_version: 目标包版本
            context: 上下文信息

        Returns:
            bool: 是否有可用的 patch
        """
        # 检查全局 patch
        global_patches = self.get_global_patches(target_package, target_version)
        if global_patches:
            return True

        # 检查局部 patch
        if context and "source_package" in context and "source_version" in context:
            local_patch = self.get_local_patches(
                context["source_package"],
                context["source_version"],
                target_package,
                target_version
            )
            if local_patch:
                return True

        return False

    def get_applied_patches(self, target_package, target_version):
        """获取已应用到目标包的 patch 列表

        Args:
            target_package: 目标包名
            target_version: 目标包版本

        Returns:
            list: 已应用的 patch 信息列表
        """
        target_key = f"{target_package}@{target_version}"
        return self._applied_patches.get(target_key, [])

    def clear_patches(self, target_package=None, target_version=None):
        """清除 patch 注册（不撤销已应用的 patch）

        Args:
            target_package: 目标包名（None 表示清除所有）
            target_version: 目标包版本（None 表示清除该包的所有版本）
        """
        if target_package is None:
            # 清除所有
            self._global_patches.clear()
            self._local_patches.clear()
            self._applied_patches.clear()
            return

        if target_version is None:
            # 清除该包的所有版本
            # 全局 patch
            keys_to_remove = [k for k in self._global_patches.keys()
                            if k.startswith(f"{target_package}@")]
            for key in keys_to_remove:
                del self._global_patches[key]

            # 局部 patch
            keys_to_remove = [k for k in self._local_patches.keys()
                            if k[1].startswith(f"{target_package}@")]
            for key in keys_to_remove:
                del self._local_patches[key]

            # 已应用 patch
            keys_to_remove = [k for k in self._applied_patches.keys()
                            if k.startswith(f"{target_package}@")]
            for key in keys_to_remove:
                del self._applied_patches[key]
        else:
            # 清除特定版本
            target_key = f"{target_package}@{target_version}"

            # 全局 patch
            if target_key in self._global_patches:
                del self._global_patches[target_key]

            # 局部 patch
            keys_to_remove = [k for k in self._local_patches.keys()
                            if k[1] == target_key]
            for key in keys_to_remove:
                del self._local_patches[key]

            # 已应用 patch
            if target_key in self._applied_patches:
                del self._applied_patches[target_key]

    def export_patches(self):
        """导出 patch 配置

        Returns:
            dict: patch 配置数据
        """
        return {
            "global": dict(self._global_patches),
            "local": dict(self._local_patches),
            "applied": dict(self._applied_patches)
        }
