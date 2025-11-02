"""
reFun 文件获取器模块

提供从多个源下载文件、验证哈希和存储到对象池的功能。
支持 HTTP/HTTPS 下载和本地文件复制，实现多源 fallback 机制。
"""

import os
try:
    import ujson as json
except ImportError:
    import json

# 尝试导入 HTTP 库 (MicroPython/CPython 兼容)
try:
    import urequests as requests
except ImportError:
    try:
        import requests
    except ImportError:
        requests = None

from .exceptions import DownloadError, HashMismatchError
from .hasher import compute_hash, compute_string_hash, get_hash_path, verify_hash


# 下载块大小
CHUNK_SIZE = 4096


class Fetcher:
    """文件获取器类

    负责从多个源下载文件，验证完整性，并存储到哈希对象池。

    Attributes:
        storage_path: 对象存储根目录 (默认 storage/objects/)
        cache_path: 下载缓存目录 (可选)
    """

    def __init__(self, storage_path="storage/objects", cache_path=None):
        """初始化文件获取器

        Args:
            storage_path: 对象存储根目录
            cache_path: 缓存目录路径（None 表示不使用缓存）
        """
        self.storage_path = storage_path
        self.cache_path = cache_path
        self._ensure_storage_dir()

    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

        if self.cache_path and not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)

    def fetch(self, sources, expected_hash):
        """从多个源获取文件

        依次尝试每个源，直到成功下载并验证通过。
        下载后自动存储到对象池。

        Args:
            sources: 源列表，每个元素为 URL 或本地路径
            expected_hash: 期望的文件哈希值

        Returns:
            str: 对象池中的文件路径

        Raises:
            DownloadError: 所有源都下载失败
            HashMismatchError: 哈希验证失败
        """
        # 检查对象是否已存在
        object_path = self._get_object_path(expected_hash)
        if os.path.exists(object_path):
            # 验证现有文件
            try:
                verify_hash(object_path, expected_hash)
                return object_path
            except HashMismatchError:
                # 现有文件损坏，删除并重新下载
                os.remove(object_path)

        # 依次尝试每个源
        errors = []
        for source in sources:
            try:
                # 判断源类型
                if source.startswith(('http://', 'https://')):
                    content = self._fetch_from_url(source)
                elif source.startswith('local://'):
                    local_path = source[8:]  # 移除 'local://' 前缀
                    content = self._fetch_from_local(local_path)
                else:
                    # 假定为本地路径
                    content = self._fetch_from_local(source)

                # 存储到对象池
                stored_path = self.store_object(content, expected_hash)
                return stored_path

            except Exception as e:
                errors.append(f"{source}: {str(e)}")
                continue

        # 所有源都失败
        error_msg = "; ".join(errors)
        raise DownloadError(
            f"all sources ({len(sources)})",
            f"Failed to fetch from all sources: {error_msg}"
        )

    def _fetch_from_url(self, url):
        """从 URL 下载文件

        Args:
            url: HTTP/HTTPS URL

        Returns:
            bytes: 文件内容

        Raises:
            DownloadError: 下载失败
        """
        if requests is None:
            raise DownloadError(url, "No HTTP library available (urequests/requests)")

        try:
            response = requests.get(url)

            # 检查状态码
            if hasattr(response, 'status_code'):
                if response.status_code != 200:
                    raise DownloadError(url, f"HTTP {response.status_code}")
            elif hasattr(response, 'status'):
                if response.status != 200:
                    raise DownloadError(url, f"HTTP {response.status}")

            # 获取内容
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = response.read()

            # 关闭响应
            if hasattr(response, 'close'):
                response.close()

            return content

        except Exception as e:
            if isinstance(e, DownloadError):
                raise
            raise DownloadError(url, str(e))

    def _fetch_from_local(self, path):
        """从本地路径读取文件

        Args:
            path: 本地文件路径

        Returns:
            bytes: 文件内容

        Raises:
            DownloadError: 读取失败
        """
        try:
            if not os.path.exists(path):
                raise DownloadError(path, "File not found")

            with open(path, 'rb') as f:
                content = f.read()

            return content

        except Exception as e:
            if isinstance(e, DownloadError):
                raise
            raise DownloadError(path, str(e))

    def store_object(self, content, expected_hash):
        """存储内容到对象池

        Args:
            content: 文件内容 (bytes 或 str)
            expected_hash: 期望的哈希值

        Returns:
            str: 存储后的文件路径

        Raises:
            HashMismatchError: 内容哈希与期望不符
        """
        # 计算内容哈希
        if isinstance(content, str):
            content = content.encode('utf-8')

        actual_hash = compute_string_hash(content)

        # 验证哈希
        if actual_hash != expected_hash:
            raise HashMismatchError(
                "<memory>",
                expected_hash,
                actual_hash
            )

        # 获取存储路径
        object_path = self._get_object_path(expected_hash)

        # 确保目录存在
        object_dir = os.path.dirname(object_path)
        if not os.path.exists(object_dir):
            os.makedirs(object_dir)

        # 写入文件
        try:
            with open(object_path, 'wb') as f:
                f.write(content)
        except Exception as e:
            raise DownloadError(object_path, f"Failed to write file: {e}")

        return object_path

    def fetch_package_json(self, name, version, sources):
        """获取 package.json 文件

        Args:
            name: 包名
            version: 版本号
            sources: package.json 的源列表

        Returns:
            dict: 解析后的 package.json 内容

        Raises:
            DownloadError: 下载失败
        """
        errors = []
        for source in sources:
            try:
                # 判断源类型
                if source.startswith(('http://', 'https://')):
                    content = self._fetch_from_url(source)
                elif source.startswith('local://'):
                    local_path = source[8:]
                    content = self._fetch_from_local(local_path)
                else:
                    content = self._fetch_from_local(source)

                # 解析 JSON
                if isinstance(content, bytes):
                    content = content.decode('utf-8')

                package_json = json.loads(content)
                return package_json

            except Exception as e:
                errors.append(f"{source}: {str(e)}")
                continue

        # 所有源都失败
        error_msg = "; ".join(errors)
        raise DownloadError(
            f"package.json for {name}@{version}",
            f"Failed to fetch from all sources: {error_msg}"
        )

    def _get_object_path(self, hash_value):
        """获取对象在对象池中的完整路径

        Args:
            hash_value: 哈希值

        Returns:
            str: 完整路径
        """
        hash_path = get_hash_path(hash_value)
        return os.path.join(self.storage_path, hash_path.replace('/', os.sep))

    def has_object(self, hash_value):
        """检查对象是否已存在于对象池

        Args:
            hash_value: 哈希值

        Returns:
            bool: 对象是否存在
        """
        object_path = self._get_object_path(hash_value)
        if not os.path.exists(object_path):
            return False

        # 验证哈希
        try:
            verify_hash(object_path, hash_value)
            return True
        except HashMismatchError:
            # 文件存在但哈希不匹配，认为不存在
            return False

    def get_object(self, hash_value):
        """获取对象路径（不下载）

        Args:
            hash_value: 哈希值

        Returns:
            str or None: 对象路径，不存在则返回 None
        """
        if self.has_object(hash_value):
            return self._get_object_path(hash_value)
        return None

    def copy_to_object(self, file_path, expected_hash=None):
        """将本地文件复制到对象池

        Args:
            file_path: 本地文件路径
            expected_hash: 期望的哈希值（None 表示自动计算）

        Returns:
            tuple: (object_path, hash_value)

        Raises:
            HashMismatchError: 哈希不匹配
            DownloadError: 复制失败
        """
        # 计算文件哈希
        actual_hash = compute_hash(file_path)

        # 验证哈希（如果提供）
        if expected_hash and actual_hash != expected_hash:
            raise HashMismatchError(file_path, expected_hash, actual_hash)

        # 读取文件内容
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
        except Exception as e:
            raise DownloadError(file_path, f"Failed to read file: {e}")

        # 存储到对象池
        object_path = self.store_object(content, actual_hash)

        return object_path, actual_hash

    def clear_cache(self):
        """清空下载缓存"""
        if not self.cache_path or not os.path.exists(self.cache_path):
            return

        try:
            for filename in os.listdir(self.cache_path):
                file_path = os.path.join(self.cache_path, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        except Exception:
            pass  # 忽略错误
