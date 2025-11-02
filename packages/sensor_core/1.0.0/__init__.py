"""
sensor_core - 通用传感器接口库
提供传感器的基础类和接口定义
"""

__version__ = "1.0.0"
__author__ = "reFun Team"

from .base import SensorBase, SensorData
from .utils import validate_range, calibrate_data

__all__ = [
    'SensorBase',
    'SensorData',
    'validate_range',
    'calibrate_data'
]
