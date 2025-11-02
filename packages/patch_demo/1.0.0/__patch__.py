"""
MonkeyPatch 实现文件
演示如何修复 sensor_tools 1.0.0 的已知问题
"""

def patch_mmc5603_read(target_module):
    """
    全局 Patch: 修复 MMC5603NJ.read() 方法
    问题: 当数据未就绪时返回 None，可能导致调用者出错
    修复: 返回默认值 [0, 0, 0] 而不是 None
    """
    # 保存原始方法
    OriginalClass = target_module.MMC5603NJ
    original_read = OriginalClass.read

    def patched_read(self):
        """修复后的 read 方法"""
        result = original_read(self)
        if result is None:
            # 返回默认值而不是 None
            print("[Patch] MMC5603NJ: 数据未就绪，返回默认值")
            try:
                from sensor_core import SensorData
            except ImportError:
                class SensorData:
                    def __init__(self, values, unit=""):
                        self.values = values
                        self.unit = unit
            return SensorData([0.0, 0.0, 0.0], unit="mG")
        return result

    # 替换方法
    OriginalClass.read = patched_read
    OriginalClass.read_magnetometer = patched_read  # 同时修复别名方法


def patch_qmi8658_logging(target_module):
    """
    局部 Patch: 为 QMI8658C 添加调试日志
    仅在当前包使用 sensor_tools 时生效
    """
    OriginalClass = target_module.QMI8658C
    original_read_accel = OriginalClass.read_accel
    original_read_gyro = OriginalClass.read_gyro

    def patched_read_accel(self):
        """添加日志的加速度计读取方法"""
        result = original_read_accel(self)
        print(f"[Patch] QMI8658C Accel: {result.values} {result.unit}")
        return result

    def patched_read_gyro(self):
        """添加日志的陀螺仪读取方法"""
        result = original_read_gyro(self)
        print(f"[Patch] QMI8658C Gyro: {result.values} {result.unit}")
        return result

    OriginalClass.read_accel = patched_read_accel
    OriginalClass.read_gyro = patched_read_gyro


def patch_add_compass_feature(target_module):
    """
    全局 Patch: 为 MMC5603NJ 添加指南针功能
    计算磁场方向角度
    """
    OriginalClass = target_module.MMC5603NJ

    def get_compass_heading(self):
        """
        计算指南针方向角度

        Returns:
            float: 方向角度 (0-360°), 0° 为北
        """
        import math
        data = self.read()
        if data is None:
            return 0.0

        x, y = data[0], data[1]

        # 计算方位角
        heading = math.atan2(y, x) * 180 / math.pi

        # 转换为 0-360° 范围
        if heading < 0:
            heading += 360

        return heading

    # 添加新方法
    OriginalClass.get_compass_heading = get_compass_heading


# 导出 patch 函数映射
PATCHES = {
    "sensor_tools": {
        "mmc5603_read_fix": patch_mmc5603_read,
        "mmc5603_compass": patch_add_compass_feature,
        "qmi8658_logging": patch_qmi8658_logging
    }
}


# 全局 patch 列表（对所有调用者生效）
GLOBAL_PATCHES = [
    "mmc5603_read_fix",
    "mmc5603_compass"
]

# 局部 patch 列表（仅在当前包使用时生效）
LOCAL_PATCHES = [
    "qmi8658_logging"
]
