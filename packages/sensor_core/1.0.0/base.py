"""
传感器基础类定义
"""

class SensorData:
    """传感器数据容器"""

    def __init__(self, values, unit="", timestamp=None):
        """
        初始化传感器数据

        Args:
            values: 数据值（可以是单个值或列表）
            unit: 单位（如 "mG", "°/s"）
            timestamp: 时间戳（可选）
        """
        self.values = values if isinstance(values, (list, tuple)) else [values]
        self.unit = unit
        self.timestamp = timestamp

    def __repr__(self):
        return f"SensorData({self.values} {self.unit})"

    def __getitem__(self, index):
        return self.values[index]


class SensorBase:
    """传感器基类"""

    def __init__(self, i2c, address):
        """
        初始化传感器

        Args:
            i2c: I2C总线对象
            address: I2C地址
        """
        self.i2c = i2c
        self.address = address
        self._initialized = False

    def init(self):
        """初始化传感器硬件"""
        raise NotImplementedError("子类必须实现 init() 方法")

    def read(self):
        """读取传感器数据"""
        raise NotImplementedError("子类必须实现 read() 方法")

    def reset(self):
        """重置传感器"""
        raise NotImplementedError("子类必须实现 reset() 方法")

    def read_register(self, reg, nbytes=1):
        """读取寄存器"""
        return self.i2c.readfrom_mem(self.address, reg, nbytes)

    def write_register(self, reg, data):
        """写入寄存器"""
        if isinstance(data, int):
            data = bytes([data])
        self.i2c.writeto_mem(self.address, reg, data)
