"""
QMI8658C 六轴传感器驱动
陀螺仪最高±2048°/s，加速度计最高±16G
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


# QMI8658C 寄存器地址
REG_WHO_AM_I = 0x00
REG_CTRL1 = 0x02
REG_CTRL2 = 0x03
REG_CTRL3 = 0x04
REG_CTRL7 = 0x08
REG_TEMP_L = 0x33
REG_TEMP_H = 0x34
REG_AX_L = 0x35
REG_GX_L = 0x3B
REG_STATUS0 = 0x2E

# 控制位
CTRL7_ENABLE_GYRO = 0x01
CTRL7_ENABLE_ACCEL = 0x02


class QMI8658C(SensorBase):
    """QMI8658C 六轴传感器驱动类"""

    # 默认 I2C 地址
    DEFAULT_ADDRESS = 0x6B

    # 加速度计量程 (g)
    ACCEL_RANGE_2G = 0
    ACCEL_RANGE_4G = 1
    ACCEL_RANGE_8G = 2
    ACCEL_RANGE_16G = 3

    # 陀螺仪量程 (°/s)
    GYRO_RANGE_16 = 0
    GYRO_RANGE_32 = 1
    GYRO_RANGE_64 = 2
    GYRO_RANGE_128 = 3
    GYRO_RANGE_256 = 4
    GYRO_RANGE_512 = 5
    GYRO_RANGE_1024 = 6
    GYRO_RANGE_2048 = 7

    def __init__(self, i2c, address=DEFAULT_ADDRESS):
        """
        初始化 QMI8658C

        Args:
            i2c: I2C 总线对象
            address: I2C 地址，默认 0x6B
        """
        super().__init__(i2c, address)
        self.accel_range = self.ACCEL_RANGE_2G
        self.gyro_range = self.GYRO_RANGE_256
        self._accel_scale = 2.0 / 32768.0  # g per LSB
        self._gyro_scale = 256.0 / 32768.0  # °/s per LSB

    def init(self):
        """初始化传感器"""
        # 检查设备 ID
        who_am_i = self.read_register(REG_WHO_AM_I, 1)[0]
        if who_am_i != 0x05:
            raise RuntimeError(f"QMI8658C 设备 ID 错误: 0x{who_am_i:02X}")

        # 配置传感器
        self.write_register(REG_CTRL1, 0x40)  # 地址自动递增
        self.set_accel_range(self.ACCEL_RANGE_2G)
        self.set_gyro_range(self.GYRO_RANGE_256)

        # 使能加速度计和陀螺仪
        self.write_register(REG_CTRL7, CTRL7_ENABLE_GYRO | CTRL7_ENABLE_ACCEL)

        self._initialized = True

    def reset(self):
        """软复位传感器"""
        self.write_register(REG_CTRL1, 0x80)
        import time
        time.sleep_ms(10)

    def set_accel_range(self, range_val):
        """设置加速度计量程"""
        self.accel_range = range_val
        scale_map = {0: 2.0, 1: 4.0, 2: 8.0, 3: 16.0}
        self._accel_scale = scale_map[range_val] / 32768.0
        self.write_register(REG_CTRL2, range_val << 4)

    def set_gyro_range(self, range_val):
        """设置陀螺仪量程"""
        self.gyro_range = range_val
        scale_map = {0: 16, 1: 32, 2: 64, 3: 128, 4: 256, 5: 512, 6: 1024, 7: 2048}
        self._gyro_scale = scale_map[range_val] / 32768.0
        self.write_register(REG_CTRL3, range_val << 4)

    def read_accel(self):
        """
        读取加速度计数据

        Returns:
            SensorData: 包含 [x, y, z] 加速度数据，单位 g
        """
        data = self.read_register(REG_AX_L, 6)

        x = bytes_to_int16(data, 0) * self._accel_scale
        y = bytes_to_int16(data, 2) * self._accel_scale
        z = bytes_to_int16(data, 4) * self._accel_scale

        return SensorData([x, y, z], unit="g")

    def read_gyro(self):
        """
        读取陀螺仪数据

        Returns:
            SensorData: 包含 [x, y, z] 角速度数据，单位 °/s
        """
        data = self.read_register(REG_GX_L, 6)

        x = bytes_to_int16(data, 0) * self._gyro_scale
        y = bytes_to_int16(data, 2) * self._gyro_scale
        z = bytes_to_int16(data, 4) * self._gyro_scale

        return SensorData([x, y, z], unit="°/s")

    def read(self):
        """
        读取所有传感器数据

        Returns:
            dict: 包含 'accel' 和 'gyro' 数据
        """
        return {
            'accel': self.read_accel(),
            'gyro': self.read_gyro()
        }

    def read_temperature(self):
        """
        读取温度数据

        Returns:
            float: 温度值，单位 °C
        """
        data = self.read_register(REG_TEMP_L, 2)
        temp_raw = bytes_to_int16(data, 0)
        # 温度转换公式（根据数据手册）
        temp_c = temp_raw / 256.0
        return temp_c
