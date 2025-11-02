"""
reFun 自定义异常类

为包管理器定义所有自定义异常，提供清晰的错误处理机制。
"""


class RefunException(Exception):
    """reFun 包管理器基础异常类"""
    pass


class PackageNotFoundError(RefunException):
    """包不存在异常

    当尝试访问或操作一个不存在的包时抛出。
    """
    def __init__(self, package_name):
        self.package_name = package_name
        super().__init__(f"Package '{package_name}' not found")


class VersionNotFoundError(RefunException):
    """版本不存在异常

    当尝试访问或操作一个包的不存在版本时抛出。
    """
    def __init__(self, package_name, version):
        self.package_name = package_name
        self.version = version
        super().__init__(f"Version '{version}' not found for package '{package_name}'")


class DependencyError(RefunException):
    """依赖解析失败异常

    当无法解析包依赖关系时抛出，例如版本冲突或依赖不满足。
    """
    def __init__(self, message, package_name=None):
        self.package_name = package_name
        super().__init__(message)


class CircularDependencyError(DependencyError):
    """循环依赖异常

    当检测到包之间存在循环依赖时抛出。
    """
    def __init__(self, dependency_chain):
        self.dependency_chain = dependency_chain
        chain_str = " -> ".join(dependency_chain)
        super().__init__(f"Circular dependency detected: {chain_str}")


class HashMismatchError(RefunException):
    """Hash 验证失败异常

    当文件内容的实际Hash与预期Hash不匹配时抛出。
    """
    def __init__(self, file_path, expected_hash, actual_hash):
        self.file_path = file_path
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        super().__init__(
            f"Hash mismatch for '{file_path}': "
            f"expected {expected_hash[:16]}..., got {actual_hash[:16]}..."
        )


class DownloadError(RefunException):
    """下载失败异常

    当从远程或本地源获取文件失败时抛出。
    """
    def __init__(self, url, reason=None):
        self.url = url
        self.reason = reason
        message = f"Failed to download from '{url}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class PatchError(RefunException):
    """Patch 应用失败异常

    当MonkeyPatch应用过程中发生错误时抛出。
    """
    def __init__(self, patch_name, target_package, reason=None):
        self.patch_name = patch_name
        self.target_package = target_package
        self.reason = reason
        message = f"Failed to apply patch '{patch_name}' to '{target_package}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class RegistryError(RefunException):
    """注册表操作失败异常

    当读取、写入或更新包注册表时发生错误时抛出。
    """
    def __init__(self, operation, reason=None):
        self.operation = operation
        self.reason = reason
        message = f"Registry operation '{operation}' failed"
        if reason:
            message += f": {reason}"
        super().__init__(message)
