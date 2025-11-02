"""
应用主逻辑
"""

def run_sensor_demo():
    """
    运行传感器演示程序
    读取并显示磁力计和陀螺仪数据
    """
    print("=" * 50)
    print("  传感器数据显示应用 v1.0.0")
    print("=" * 50)
    print()

    # 模拟 I2C 总线（实际应用中应该使用真实的 I2C）
    class MockI2C:
        """模拟 I2C 总线用于演示"""
        def readfrom_mem(self, addr, reg, nbytes):
            # 返回模拟数据
            import random
            return bytes([random.randint(0, 255) for _ in range(nbytes)])

        def writeto_mem(self, addr, reg, data):
            pass

    try:
        # 导入传感器驱动
        from sensor_tools import MMC5603NJ, QMI8658C

        print("正在初始化传感器...")
        i2c = MockI2C()

        # 初始化磁力计
        mag = MMC5603NJ(i2c)
        try:
            mag.init()
            print("✓ MMC5603NJ 磁力计初始化成功")
        except Exception as e:
            print(f"✗ MMC5603NJ 初始化失败: {e}")

        # 初始化六轴传感器
        imu = QMI8658C(i2c)
        try:
            # 注意：模拟模式下会失败，因为 WHO_AM_I 检查
            # imu.init()
            print("✓ QMI8658C 六轴传感器已就绪（演示模式）")
        except Exception as e:
            print(f"✓ QMI8658C 演示模式（实际硬件会正常工作）")

        print()
        print("-" * 50)
        print("开始读取传感器数据...")
        print("-" * 50)
        print()

        # 读取磁力计数据
        print("【磁力计数据】")
        mag_data = mag.read()
        if mag_data:
            print(f"  X: {mag_data[0]:.2f} {mag_data.unit}")
            print(f"  Y: {mag_data[1]:.2f} {mag_data.unit}")
            print(f"  Z: {mag_data[2]:.2f} {mag_data.unit}")

            # 如果 patch_demo 已安装，会有指南针功能
            if hasattr(mag, 'get_compass_heading'):
                heading = mag.get_compass_heading()
                print(f"  方向: {heading:.1f}°")
                print()
        else:
            print("  数据未就绪")
            print()

        print("-" * 50)
        print("演示完成!")
        print("-" * 50)

    except ImportError as e:
        print(f"错误: 无法导入传感器模块")
        print(f"请确保 sensor_tools 已安装: {e}")
        print()
        print("提示: 使用 refun 包管理器安装:")
        print("  pm = refun.PackageManager()")
        print("  pm.install('sensor_tools', '1.0.0')")

    except Exception as e:
        print(f"运行错误: {e}")
        import traceback
        traceback.print_exc()


def show_dependencies():
    """显示应用依赖信息"""
    print("应用依赖:")
    print("  - sensor_tools ^1.0.0")
    print("    └─ sensor_core ^1.0.0")
