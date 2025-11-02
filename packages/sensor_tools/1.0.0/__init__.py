"""
sensor_tools - 传感器驱动工具包
提供 MMC5603NJ 磁力计和 QMI8658C 陀螺仪驱动
"""

__version__ = "1.0.0"
__author__ = "reFun Team"

from .mmc5603 import MMC5603NJ
from .qmi8658 import QMI8658C

__all__ = ['MMC5603NJ', 'QMI8658C']
