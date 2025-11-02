"""
reFun 语义化版本管理模块

实现语义化版本(Semantic Versioning)的解析、比较和约束匹配功能。
支持版本格式: major.minor.patch (例如: 1.2.3)
支持约束语法: ^, ~, >=, <=, ==
"""

import re


class Version:
    """语义化版本类

    解析和比较语义化版本号 (major.minor.patch)

    示例:
        >>> v = Version(1, 2, 3)
        >>> str(v)
        '1.2.3'
        >>> v1 = parse_version('1.2.3')
        >>> v2 = parse_version('1.3.0')
        >>> v1 < v2
        True
    """

    def __init__(self, major, minor, patch):
        """初始化版本对象

        参数:
            major (int): 主版本号
            minor (int): 次版本号
            patch (int): 补丁版本号
        """
        self.major = int(major)
        self.minor = int(minor)
        self.patch = int(patch)

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self):
        return f"Version({self.major}, {self.minor}, {self.patch})"

    def __eq__(self, other):
        if not isinstance(other, Version):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __lt__(self, other):
        if not isinstance(other, Version):
            raise TypeError(f"Cannot compare Version with {type(other)}")
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other):
        return self == other or self < other

    def __gt__(self, other):
        if not isinstance(other, Version):
            raise TypeError(f"Cannot compare Version with {type(other)}")
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __ge__(self, other):
        return self == other or self > other

    def __hash__(self):
        return hash((self.major, self.minor, self.patch))


class Constraint:
    """版本约束类

    解析和匹配版本约束表达式

    支持的约束语法:
        - ^1.2.3: 兼容版本 (1.2.3 <= v < 2.0.0)
        - ~1.2.3: 近似版本 (1.2.3 <= v < 1.3.0)
        - >=1.2.3: 大于等于
        - <=1.2.3: 小于等于
        - ==1.2.3: 精确匹配
        - 1.2.3: 默认精确匹配

    示例:
        >>> c = parse_constraint('^1.2.0')
        >>> c.match(parse_version('1.5.0'))
        True
        >>> c.match(parse_version('2.0.0'))
        False
    """

    def __init__(self, operator, version):
        """初始化约束对象

        参数:
            operator (str): 约束操作符 (^, ~, >=, <=, ==)
            version (Version): 约束版本
        """
        self.operator = operator
        self.version = version

    def __str__(self):
        return f"{self.operator}{self.version}"

    def __repr__(self):
        return f"Constraint('{self.operator}', {self.version})"

    def match(self, version):
        """判断给定版本是否满足约束

        参数:
            version (Version): 要检查的版本

        返回:
            bool: True if 版本满足约束
        """
        if not isinstance(version, Version):
            raise TypeError(f"Expected Version, got {type(version)}")

        if self.operator == '==':
            return version == self.version

        elif self.operator == '>=':
            return version >= self.version

        elif self.operator == '<=':
            return version <= self.version

        elif self.operator == '>':
            return version > self.version

        elif self.operator == '<':
            return version < self.version

        elif self.operator == '^':
            # 兼容版本: 1.2.3 <= v < 2.0.0
            # 不改变最左边非零版本号
            if self.version.major > 0:
                upper = Version(self.version.major + 1, 0, 0)
            elif self.version.minor > 0:
                upper = Version(0, self.version.minor + 1, 0)
            else:
                upper = Version(0, 0, self.version.patch + 1)

            return version >= self.version and version < upper

        elif self.operator == '~':
            # 近似版本: 1.2.3 <= v < 1.3.0
            # 允许 patch 版本变化
            upper = Version(self.version.major, self.version.minor + 1, 0)
            return version >= self.version and version < upper

        else:
            raise ValueError(f"Unknown operator: {self.operator}")


def parse_version(version_str):
    """解析版本字符串为 Version 对象

    参数:
        version_str (str): 版本字符串 (例如: "1.2.3")

    返回:
        Version: 版本对象

    抛出:
        ValueError: 如果版本字符串格式不正确

    示例:
        >>> v = parse_version('1.2.3')
        >>> v.major, v.minor, v.patch
        (1, 2, 3)
    """
    # 匹配格式: major.minor.patch
    pattern = r'^(\d+)\.(\d+)\.(\d+)$'
    match = re.match(pattern, version_str.strip())

    if not match:
        raise ValueError(f"Invalid version format: '{version_str}' (expected: major.minor.patch)")

    major, minor, patch = match.groups()
    return Version(int(major), int(minor), int(patch))


def parse_constraint(constraint_str):
    """解析约束字符串为 Constraint 对象

    参数:
        constraint_str (str): 约束字符串 (例如: "^1.2.0", ">=1.0.0")

    返回:
        Constraint: 约束对象

    抛出:
        ValueError: 如果约束字符串格式不正确

    示例:
        >>> c = parse_constraint('^1.2.0')
        >>> str(c)
        '^1.2.0'
    """
    constraint_str = constraint_str.strip()

    # 匹配约束模式: operator + version
    # 支持: ^, ~, >=, <=, ==, >, <
    pattern = r'^([\^~><=]+)?(\d+\.\d+\.\d+)$'
    match = re.match(pattern, constraint_str)

    if not match:
        raise ValueError(f"Invalid constraint format: '{constraint_str}'")

    operator, version_str = match.groups()

    # 如果没有操作符，默认为 ==
    if not operator:
        operator = '=='

    version = parse_version(version_str)
    return Constraint(operator, version)


def compare(v1, v2):
    """比较两个版本的大小

    参数:
        v1 (Version or str): 第一个版本
        v2 (Version or str): 第二个版本

    返回:
        int: -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2

    示例:
        >>> compare('1.2.3', '1.3.0')
        -1
        >>> compare('2.0.0', '1.9.9')
        1
        >>> compare('1.0.0', '1.0.0')
        0
    """
    if isinstance(v1, str):
        v1 = parse_version(v1)
    if isinstance(v2, str):
        v2 = parse_version(v2)

    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    else:
        return 0


def match(version, constraint):
    """判断版本是否满足约束

    参数:
        version (Version or str): 要检查的版本
        constraint (Constraint or str): 约束条件

    返回:
        bool: True if 版本满足约束

    示例:
        >>> match('1.5.0', '^1.2.0')
        True
        >>> match('2.0.0', '^1.2.0')
        False
    """
    if isinstance(version, str):
        version = parse_version(version)
    if isinstance(constraint, str):
        constraint = parse_constraint(constraint)

    return constraint.match(version)
