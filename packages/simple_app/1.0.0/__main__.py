"""
应用入口文件
当使用 pm.run('simple_app') 时会执行此文件
"""

from .app import run_sensor_demo

if __name__ == "__main__":
    run_sensor_demo()
