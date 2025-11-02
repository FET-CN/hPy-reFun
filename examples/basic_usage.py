"""
reFun 基本使用示例

演示如何使用 PackageManager 进行包管理的基本操作。
"""

import os
import sys

# 添加 lib 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

import refun


def main():
    print("=" * 60)
    print("reFun 包管理器 - 基本使用示例")
    print("=" * 60)

    # 创建包管理器实例
    pm = refun.PackageManager()
    print("\n[1] 创建 PackageManager 实例")
    print(f"    - 存储路径: {pm.storage_path}")
    print(f"    - 包目录: {pm.packages_path}")

    # 创建一个示例包
    print("\n[2] 创建示例包...")
    example_pkg_dir = os.path.join(os.path.dirname(__file__), "_temp_pkg")
    os.makedirs(example_pkg_dir, exist_ok=True)

    # 创建 __init__.py
    with open(os.path.join(example_pkg_dir, "__init__.py"), 'w', encoding='utf-8') as f:
        f.write('"""示例包 - 演示 reFun 包管理器功能"""\n\n')
        f.write('__version__ = "1.0.0"\n\n')
        f.write('def greet(name="World"):\n')
        f.write('    """打招呼函数"""\n')
        f.write('    return f"Hello, {name}! 欢迎使用 reFun!"\n\n')
        f.write('def calculate(a, b, op="+"):\n')
        f.write('    """简单计算器"""\n')
        f.write('    if op == "+":\n')
        f.write('        return a + b\n')
        f.write('    elif op == "-":\n')
        f.write('        return a - b\n')
        f.write('    elif op == "*":\n')
        f.write('        return a * b\n')
        f.write('    elif op == "/":\n')
        f.write('        return a / b if b != 0 else None\n')
        f.write('    else:\n')
        f.write('        raise ValueError(f"Unsupported operation: {op}")\n')

    # 创建 utils.py
    with open(os.path.join(example_pkg_dir, "utils.py"), 'w', encoding='utf-8') as f:
        f.write('"""工具函数模块"""\n\n')
        f.write('def reverse_string(s):\n')
        f.write('    """反转字符串"""\n')
        f.write('    return s[::-1]\n\n')
        f.write('def count_words(text):\n')
        f.write('    """统计单词数量"""\n')
        f.write('    return len(text.split())\n')

    print("    - 已创建示例包文件")

    # 注册本地包
    print("\n[3] 注册本地包...")
    result = pm.register_local(example_pkg_dir, "example_pkg", "1.0.0")
    print(f"    - 包名: {result['name']}")
    print(f"    - 版本: {result['version']}")
    print(f"    - 状态: {result['status']}")

    # 查看已安装的包
    print("\n[4] 列出已安装的包...")
    packages = pm.list()
    for pkg in packages:
        print(f"    - {pkg['name']}: {', '.join(pkg['versions'])}")

    # 查看包详细信息
    print("\n[5] 查看包详细信息...")
    info = pm.info("example_pkg", "1.0.0")
    print(f"    - 名称: {info['name']}")
    print(f"    - 版本: {info['version']}")
    print(f"    - 文件数: {info['files_count']}")
    print(f"    - 描述: {info['description']}")

    # 加载包
    print("\n[6] 加载包...")
    example_pkg = pm.load("example_pkg", "1.0.0")
    print(f"    - 包已加载")
    print(f"    - 版本: {example_pkg.__version__}")

    # 使用包的功能
    print("\n[7] 使用包的功能...")
    greeting = example_pkg.greet("reFun 用户")
    print(f"    - greet(): {greeting}")

    result = example_pkg.calculate(10, 5, "+")
    print(f"    - calculate(10, 5, '+'): {result}")

    result = example_pkg.calculate(10, 5, "*")
    print(f"    - calculate(10, 5, '*'): {result}")

    # 使用 utils 模块
    from example_pkg import utils
    reversed_text = utils.reverse_string("reFun")
    print(f"    - utils.reverse_string('reFun'): {reversed_text}")

    # 搜索包
    print("\n[8] 搜索包...")
    results = pm.search("example")
    print(f"    - 搜索 'example': 找到 {len(results)} 个包")

    # 卸载包（从内存）
    print("\n[9] 卸载包...")
    pm.unload("example_pkg", "1.0.0")
    print(f"    - 包已从内存卸载")
    print(f"    - 是否仍在注册表: {pm.registry.has_version('example_pkg', '1.0.0')}")

    # 清理
    print("\n[10] 清理示例包目录...")
    import shutil
    if os.path.exists(example_pkg_dir):
        shutil.rmtree(example_pkg_dir)
    print("    - 已清理临时文件")

    print("\n" + "=" * 60)
    print("示例完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
