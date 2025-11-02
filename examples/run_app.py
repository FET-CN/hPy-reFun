"""
运行应用示例
演示如何使用 pm.run() 执行可执行包
"""

import sys
import os

# 添加 lib 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

try:
    import refun
except ImportError:
    print("错误: 无法导入 refun 模块")
    sys.exit(1)


def main():
    """运行应用演示"""
    print("=" * 60)
    print("  reFun 包管理器 - 运行应用示例")
    print("=" * 60)
    print()

    pm = refun.PackageManager()

    print("步骤 1: 注册应用包及其依赖")
    print("-" * 60)
    packages = [
        ("packages/sensor_core/1.0.0", "sensor_core", "1.0.0"),
        ("packages/sensor_tools/1.0.0", "sensor_tools", "1.0.0"),
        ("packages/simple_app/1.0.0", "simple_app", "1.0.0"),
    ]

    for path, name, version in packages:
        try:
            pm.register_local(path, name, version)
            print(f"  ✓ {name} @ {version}")
        except Exception as e:
            print(f"  ✗ {name} @ {version}: {e}")
    print()

    print("步骤 2: 检查应用是否有可执行入口")
    print("-" * 60)
    try:
        has_entry = pm.has_entry("simple_app", "1.0.0")
        if has_entry:
            print("  ✓ simple_app 有可执行入口 (__main__.py)")
            info = pm.info("simple_app", "1.0.0")
            entry_file = info.get("entry", "__main__.py")
            print(f"  入口文件: {entry_file}")
        else:
            print("  ✗ simple_app 没有可执行入口")
            return
    except Exception as e:
        print(f"  错误: {e}")
        return
    print()

    print("步骤 3: 运行应用")
    print("-" * 60)
    print()

    try:
        # 运行应用（会执行 __main__.py）
        pm.run("simple_app", "1.0.0")

    except Exception as e:
        print(f"\n✗ 运行失败: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 60)
    print("  演示完成!")
    print("=" * 60)
    print()
    print("运行应用说明:")
    print("  1. 应用必须在 package.json 中定义 'entry' 字段")
    print("  2. 入口文件通常是 __main__.py")
    print("  3. pm.run() 会自动加载所有依赖后执行入口文件")
    print("  4. 应用可以像普通 Python 程序一样运行")
    print()


if __name__ == "__main__":
    main()
