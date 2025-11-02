"""
基础安装示例
演示如何使用 refun 包管理器安装和加载包
"""

import sys
import os

# 添加 lib 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

try:
    import refun
except ImportError:
    print("错误: 无法导入 refun 模块")
    print("请确保 lib/refun/ 目录存在且包含核心模块")
    sys.exit(1)


def main():
    """基础安装演示"""
    print("=" * 60)
    print("  reFun 包管理器 - 基础安装示例")
    print("=" * 60)
    print()

    # 创建包管理器实例
    pm = refun.PackageManager()

    print("1. 列出已安装的包")
    print("-" * 60)
    packages = pm.list()
    if packages:
        for pkg in packages:
            print(f"  - {pkg['name']} @ {pkg['version']}")
    else:
        print("  （暂无已安装的包）")
    print()

    print("2. 从本地路径注册包")
    print("-" * 60)
    try:
        # 注册 sensor_core
        print("  正在注册 sensor_core...")
        pm.register_local(
            path="packages/sensor_core/1.0.0",
            name="sensor_core",
            version="1.0.0"
        )
        print("  ✓ sensor_core 1.0.0 注册成功")

        # 注册 sensor_tools
        print("  正在注册 sensor_tools...")
        pm.register_local(
            path="packages/sensor_tools/1.0.0",
            name="sensor_tools",
            version="1.0.0"
        )
        print("  ✓ sensor_tools 1.0.0 注册成功")

    except Exception as e:
        print(f"  ✗ 注册失败: {e}")
    print()

    print("3. 查看包信息")
    print("-" * 60)
    try:
        info = pm.info("sensor_tools", "1.0.0")
        print(f"  名称: {info.get('name')}")
        print(f"  版本: {info.get('version')}")
        print(f"  描述: {info.get('description')}")
        print(f"  作者: {info.get('author')}")
        if info.get('dependencies'):
            print("  依赖:")
            for dep_name, dep_version in info['dependencies'].items():
                print(f"    - {dep_name} {dep_version}")
    except Exception as e:
        print(f"  ✗ 获取信息失败: {e}")
    print()

    print("4. 加载包")
    print("-" * 60)
    try:
        print("  正在加载 sensor_tools...")
        sensor_tools = pm.load("sensor_tools", "1.0.0")
        print(f"  ✓ 加载成功: {sensor_tools}")
        print(f"  可用类: {dir(sensor_tools)}")
    except Exception as e:
        print(f"  ✗ 加载失败: {e}")
        import traceback
        traceback.print_exc()
    print()

    print("5. 使用已加载的包")
    print("-" * 60)
    try:
        # 创建模拟 I2C 用于演示
        class MockI2C:
            def readfrom_mem(self, addr, reg, nbytes):
                return bytes([0] * nbytes)
            def writeto_mem(self, addr, reg, data):
                pass

        i2c = MockI2C()
        mag = sensor_tools.MMC5603NJ(i2c)
        print(f"  ✓ 创建 MMC5603NJ 实例: {mag}")
        print(f"  I2C 地址: 0x{mag.address:02X}")
    except Exception as e:
        print(f"  ✗ 使用失败: {e}")
    print()

    print("=" * 60)
    print("  演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
