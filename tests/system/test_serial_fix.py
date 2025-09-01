#!/usr/bin/env python3
"""
快速测试SerialHandler的TCP连接修复
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from serial_handler import SerialHandler

def test_tcp_config():
    """测试TCP配置"""
    config = {
        'host': 'localhost',
        'port': 8888,  # 整数端口
        'timeout': 2.0
    }
    
    handler = SerialHandler(config)
    print(f"Is TCP: {handler.is_tcp}")
    print(f"Config: {handler.config}")
    
    try:
        success = handler.open()
        print(f"Connection success: {success}")
        if success:
            handler.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_tcp_config()
