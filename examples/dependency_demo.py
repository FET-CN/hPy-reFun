"""
依赖解析演示
演示包管理器如何自动解析和加载依赖
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


def visualize_dependency_tree(pm, package_name, version, indent=0):
    """
    可视化显示依赖树

    Args:
        pm: PackageManager 实例
        package_name: 包名
        version: 版本号
        indent: 缩进级别
    """
    prefix = "  " * indent + ("└─ " if indent > 0 else "")
    print(f"{prefix}{package_name} @ {version}")

    try:
        info = pm.info(package_name, version)
        dependencies = info.get('dependencies', {})

        if dependencies:
            for dep_name, dep_constraint in dependencies.items():
                # 获取满足约束的版本
                available_versions = pm.list_versions(dep_name)
                if available_versions:
                    # 简化：使用第一个可用版本
                    dep_version = available_versions[0]
                    visualize_dependency_tree(pm, dep_name, dep_version, indent + 1)
                else:
                    print(f"{'  ' * (indent + 1)}└─ {dep_name} {dep_constraint} (未安装)")

    except Exception as e:
        print(f"{'  ' * (indent + 1)}✗ 错误: {e}")


def main():
    """依赖解析演示"""
    print("=" * 60)
    print("  reFun 包管理器 - 依赖解析演示")
    print("=" * 60)
    print()

    pm = refun.PackageManager()

    print("步骤 1: 注册所有示例包")
    print("-" * 60)
    packages_to_register = [
        ("packages/sensor_core/1.0.0", "sensor_core", "1.0.0"),
        ("packages/sensor_tools/1.0.0", "sensor_tools", "1.0.0"),
        ("packages/simple_app/1.0.0", "simple_app", "1.0.0"),
    ]

    for path, name, version in packages_to_register:
        try:
            pm.register_local(path, name, version)
            print(f"  ✓ {name} @ {version}")
        except Exception as e:
            print(f"  ✗ {name} @ {version}: {e}")
    print()

    print("步骤 2: 查看依赖关系")
    print("-" * 60)

    print("\n【sensor_core 依赖树】")
    visualize_dependency_tree(pm, "sensor_core", "1.0.0")

    print("\n【sensor_tools 依赖树】")
    visualize_dependency_tree(pm, "sensor_tools", "1.0.0")

    print("\n【simple_app 依赖树】")
    visualize_dependency_tree(pm, "simple_app", "1.0.0")
    print()

    print("步骤 3: 解析加载顺序")
    print("-" * 60)
    try:
        # 使用 DependencyResolver 解析依赖
        from refun.resolver import DependencyResolver

        resolver = DependencyResolver(pm.registry)
        load_order = resolver.resolve("simple_app", "1.0.0")

        print("  加载顺序（拓扑排序）:")
        for i, (pkg_name, pkg_version) in enumerate(load_order, 1):
            print(f"    {i}. {pkg_name} @ {pkg_version}")

    except Exception as e:
        print(f"  ✗ 解析失败: {e}")
        import traceback
        traceback.print_exc()
    print()

    print("步骤 4: 自动加载依赖")
    print("-" * 60)
    try:
        print("  加载 simple_app（会自动加载所有依赖）...")
        app = pm.load("simple_app", "1.0.0")
        print(f"  ✓ simple_app 加载成功")
        print(f"  ✓ 所有依赖已自动加载")
        print(f"  可用功能: {[x for x in dir(app) if not x.startswith('_')]}")

    except Exception as e:
        print(f"  ✗ 加载失败: {e}")
        import traceback
        traceback.print_exc()
    print()

    print("步骤 5: 验证依赖是否可用")
    print("-" * 60)
    try:
        # 尝试导入依赖包
        import sensor_core
        import sensor_tools

        print("  ✓ sensor_core 可用")
        print(f"    - SensorBase: {sensor_core.SensorBase}")
        print(f"    - SensorData: {sensor_core.SensorData}")

        print("  ✓ sensor_tools 可用")
        print(f"    - MMC5603NJ: {sensor_tools.MMC5603NJ}")
        print(f"    - QMI8658C: {sensor_tools.QMI8658C}")

    except ImportError as e:
        print(f"  ✗ 导入失败: {e}")
    print()

    print("=" * 60)
    print("  演示完成!")
    print("=" * 60)
    print()
    print("依赖解析说明:")
    print("  1. 包管理器会自动解析依赖树")
    print("  2. 使用拓扑排序确定正确的加载顺序")
    print("  3. 加载包时会自动加载所有依赖")
    print("  4. 支持传递依赖（A -> B -> C）")
    print("  5. 检测并防止循环依赖")
    print()


if __name__ == "__main__":
    main()
