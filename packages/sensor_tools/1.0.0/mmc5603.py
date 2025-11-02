"""
MMC5603NJ 磁力计驱动
3轴磁力计，最小分辨率0.0625mG，±30G量程
"""

try:
    from sensor_core import SensorBase, SensorData
    from sensor_core.utils import bytes_to_int16
except ImportError:
    # 用于独立测试时的 fallback
    class SensorBase:
        def __init__(self, i2c, address):
            self.i2c = i2c
            self.address = address
        def read_register(self, reg, nbytes=1):
            return self.i2c.readfrom_mem(self.address, reg, nbytes)
        def write_register(self, reg, data):
            self.i2c.writeto_mem(self.address, reg, bytes([data]) if isinstance(data, int) else data)
    class SensorData:
        def __init__(self, values, unit="", timestamp=None):
            self.values = values
            self.unit = unit
    def bytes_to_int16(data, offset=0, little_endian=True):
        if little_endian:
            value = data[offset] | (data[offset + 1] << 8)
        else:
            value = (data[offset] << 8) | data[offset + 1]
        if value >= 0x8000:
            value -= 0x10000
        return value


# MMC5603NJ 寄存器地址
REG_XOUT_0 = 0x00
REG_XOUT_1 = 0x01
REG_YOUT_0 = 0x02
REG_YOUT_1 = 0x03
REG_ZOUT_0 = 0x04
REG_ZOUT_1 = 0x05
REG_STATUS = 0x18
REG_CTRL0 = 0x1B
REG_CTRL1 = 0x1C
REG_CTRL2 = 0x1D

# 控制位
CTRL0_TMM = 0x01  # Take Measurement
CTRL0_TM_M = 0x02  # Mag Measurement
CTRL1_BW = 0x01  # Bandwidth
CTRL2_CMM_EN = 0x10  # Continuous Mode Enable


class MMC5603NJ(SensorBase):
    """MMC5603NJ 磁力计驱动类"""

    # 默认 I2C 地址
    DEFAULT_ADDRESS = 0x30

    def __init__(self, i2c, address=DEFAULT_ADDRESS):
        """
        初始化 MMC5603NJ

        Args:
            i2c: I2C 总线对象
            address: I2C 地址，默认 0x30
        """
        super().__init__(i2c, address)
        self._resolution = 0.0625  # mG per LSB

    def init(self):
        """初始化传感器"""
        # 复位传感器
        self.reset()
        # 设置带宽
        self.write_register(REG_CTRL1, CTRL1_BW)
        self._initialized = True

    def reset(self):
        """软复位传感器"""
        self.write_register(REG_CTRL1, 0x80)
        import time
        time.sleep_ms(10)

    def read(self):
        """
        读取磁力计数据

        Returns:
            SensorData: 包含 [x, y, z] 磁场强度数据，单位 mG
        """
        # 触发单次测量
        self.write_register(REG_CTRL0, CTRL0_TM_M)

        # 等待测量完成
        import time
        time.sleep_ms(10)

        # 读取状态寄存器，检查数据是否就绪
        status = self.read_register(REG_STATUS, 1)[0]
        if not (status & 0x01):
            # 数据未就绪，返回 None
            return None

        # 读取 6 字节数据 (X, Y, Z)
        data = self.read_register(REG_XOUT_0, 6)

        # 转换为 mG
        x = bytes_to_int16(data, 0, little_endian=True) * self._resolution
        y = bytes_to_int16(data, 2, little_endian=True) * self._resolution
        z = bytes_to_int16(data, 4, little_endian=True) * self._resolution

        return SensorData([x, y, z], unit="mG")

    def read_magnetometer(self):
        """
        读取磁力计数据（别名方法）

        Returns:
            SensorData 或 None
        """
        return self.read()

    def set_continuous_mode(self, enable=True):
        """
        设置连续测量模式

        Args:
            enable: True 启用，False 禁用
        """
        if enable:
            self.write_register(REG_CTRL2, CTRL2_CMM_EN)
        else:
            self.write_register(REG_CTRL2, 0x00)
