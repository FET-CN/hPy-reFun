"""
simple_app - 简单的传感器数据显示应用
演示如何使用 refun 包管理器加载依赖并运行应用
"""

__version__ = "1.0.0"
__author__ = "reFun Team"

from .app import run_sensor_demo

__all__ = ['run_sensor_demo']
