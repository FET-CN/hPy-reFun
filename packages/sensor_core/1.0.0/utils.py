"""
传感器工具函数
"""

def validate_range(value, min_val, max_val, name="Value"):
    """
    验证数值是否在有效范围内

    Args:
        value: 要验证的值
        min_val: 最小值
        max_val: 最大值
        name: 值的名称（用于错误信息）

    Raises:
        ValueError: 如果值超出范围
    """
    if not (min_val <= value <= max_val):
        raise ValueError(f"{name} {value} 超出范围 [{min_val}, {max_val}]")
    return True


def calibrate_data(raw_value, scale=1.0, offset=0.0):
    """
    校准传感器数据

    Args:
        raw_value: 原始数据
        scale: 缩放因子
        offset: 偏移量

    Returns:
        校准后的数据
    """
    if isinstance(raw_value, (list, tuple)):
        return [v * scale + offset for v in raw_value]
    return raw_value * scale + offset


def bytes_to_int16(data, offset=0, little_endian=True):
    """
    将字节转换为有符号16位整数

    Args:
        data: 字节数据
        offset: 起始偏移
        little_endian: 是否为小端序

    Returns:
        int16值
    """
    if little_endian:
        value = data[offset] | (data[offset + 1] << 8)
    else:
        value = (data[offset] << 8) | data[offset + 1]

    # 转换为有符号数
    if value >= 0x8000:
        value -= 0x10000

    return value
