"""
MonkeyPatch 机制演示
演示如何使用 patch 修复和增强已有包的功能
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
    """MonkeyPatch 演示"""
    print("=" * 60)
    print("  reFun 包管理器 - MonkeyPatch 演示")
    print("=" * 60)
    print()

    pm = refun.PackageManager()

    print("步骤 1: 注册必要的包")
    print("-" * 60)
    try:
        pm.register_local("packages/sensor_core/1.0.0", "sensor_core", "1.0.0")
        pm.register_local("packages/sensor_tools/1.0.0", "sensor_tools", "1.0.0")
        pm.register_local("packages/patch_demo/1.0.0", "patch_demo", "1.0.0")
        print("  ✓ 所有包注册成功")
    except Exception as e:
        print(f"  注册失败: {e}")
        return
    print()

    print("步骤 2: 不使用 patch 时的行为")
    print("-" * 60)
    try:
        sensor_tools = pm.load("sensor_tools", "1.0.0")

        class MockI2C:
            def __init__(self):
                self.data_ready = False

            def readfrom_mem(self, addr, reg, nbytes):
                # 模拟数据未就绪的情况
                if reg == 0x18:  # STATUS register
                    return bytes([0x00])  # 数据未就绪
                return bytes([0] * nbytes)

            def writeto_mem(self, addr, reg, data):
                pass

        i2c = MockI2C()
        mag = sensor_tools.MMC5603NJ(i2c)
        mag.init()

        result = mag.read()
        print(f"  read() 返回值: {result}")
        print(f"  类型: {type(result)}")

        # 检查是否有指南针功能
        if hasattr(mag, 'get_compass_heading'):
            print("  ✓ 有 get_compass_heading 方法（patch 已应用）")
        else:
            print("  ✗ 无 get_compass_heading 方法（patch 未应用）")

    except Exception as e:
        print(f"  错误: {e}")
    print()

    print("步骤 3: 加载 patch_demo 应用全局 patch")
    print("-" * 60)
    try:
        # 加载 patch_demo 会应用全局 patch
        patch_demo = pm.load("patch_demo", "1.0.0")
        print("  ✓ patch_demo 加载成功")
        print("  全局 patch 已应用到 sensor_tools")
    except Exception as e:
        print(f"  错误: {e}")
    print()

    print("步骤 4: 重新加载 sensor_tools（应用 patch 后）")
    print("-" * 60)
    try:
        # 重新加载 sensor_tools 以应用 patch
        pm.reload("sensor_tools", "1.0.0")
        sensor_tools = pm.load("sensor_tools", "1.0.0")

        i2c = MockI2C()
        mag = sensor_tools.MMC5603NJ(i2c)
        mag.init()

        print("  测试 1: read() 方法（修复后）")
        result = mag.read()
        print(f"    返回值: {result}")
        if result is not None:
            print(f"    数据: {result.values} {result.unit}")
            print("    ✓ Patch 生效：返回默认值而不是 None")

        print()
        print("  测试 2: get_compass_heading() 方法（新增功能）")
        if hasattr(mag, 'get_compass_heading'):
            heading = mag.get_compass_heading()
            print(f"    方向角: {heading:.1f}°")
            print("    ✓ Patch 生效：新增指南针功能")
        else:
            print("    ✗ get_compass_heading 方法不存在")

    except Exception as e:
        print(f"  错误: {e}")
        import traceback
        traceback.print_exc()
    print()

    print("=" * 60)
    print("  演示完成!")
    print("=" * 60)
    print()
    print("Patch 说明:")
    print("  1. 全局 Patch: 修复 read() 返回 None 的问题")
    print("  2. 全局 Patch: 为 MMC5603NJ 添加 get_compass_heading() 方法")
    print("  3. 局部 Patch: 为 QMI8658C 添加调试日志（仅在特定上下文）")
    print()


if __name__ == "__main__":
    main()
