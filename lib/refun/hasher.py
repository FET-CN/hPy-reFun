"""
reFun Hash 计算和验证模块

提供文件内容的SHA256哈希计算、验证和存储路径转换功能。
使用流式读取以优化内存使用，适配MicroPython环境。
"""

import hashlib
from .exceptions import HashMismatchError


# 流式读取块大小（4KB）
CHUNK_SIZE = 4096


def compute_hash(file_path):
    """计算文件的SHA256哈希值

    使用流式读取方式计算文件哈希，避免一次性加载整个文件到内存。

    参数:
        file_path (str): 文件路径

    返回:
        str: 十六进制格式的SHA256哈希值

    示例:
        >>> compute_hash('/path/to/file.py')
        'a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890'
    """
    sha256 = hashlib.sha256()

    try:
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                sha256.update(chunk)
    except OSError as e:
        raise OSError(f"Failed to read file '{file_path}': {e}")

    return sha256.hexdigest()


def verify_hash(file_path, expected_hash):
    """验证文件的哈希值是否匹配

    参数:
        file_path (str): 文件路径
        expected_hash (str): 期望的哈希值（十六进制字符串）

    返回:
        bool: True if 哈希值匹配，False otherwise

    抛出:
        HashMismatchError: 如果哈希值不匹配

    示例:
        >>> verify_hash('/path/to/file.py', 'a1b2c3d4...')
        True
    """
    actual_hash = compute_hash(file_path)

    if actual_hash != expected_hash:
        raise HashMismatchError(file_path, expected_hash, actual_hash)

    return True


def get_hash_path(hash_value):
    """将哈希值转换为存储路径

    使用前2位作为目录名，剩余部分作为文件名，实现分片存储。

    参数:
        hash_value (str): SHA256哈希值（十六进制字符串）

    返回:
        str: 相对存储路径 (例如: 'a1/b2c3d4e5...')

    示例:
        >>> get_hash_path('a1b2c3d4e5f67890abcdef...')
        'a1/b2c3d4e5f67890abcdef...'
    """
    if len(hash_value) < 3:
        raise ValueError(f"Invalid hash value: {hash_value}")

    return f"{hash_value[:2]}/{hash_value[2:]}"


def compute_string_hash(content):
    """计算字符串内容的SHA256哈希值

    用于计算内存中字符串内容的哈希值，而不是文件。

    参数:
        content (str or bytes): 要计算哈希的内容

    返回:
        str: 十六进制格式的SHA256哈希值

    示例:
        >>> compute_string_hash('hello world')
        'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
    """
    if isinstance(content, str):
        content = content.encode('utf-8')

    sha256 = hashlib.sha256()
    sha256.update(content)

    return sha256.hexdigest()
