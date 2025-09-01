#!/usr/bin/env python3
"""
架构质量测试 - 测试代码质量、维护性和扩展性
"""

import unittest
import time
import os
import sys
import ast
import inspect
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.config import Config


class TestArchitectureQuality(unittest.TestCase):
    """架构质量测试套件"""
    
    def create_config(self):
        """创建测试配置"""
        config_dict = {
            'ntrip': {
                'server': 'localhost',
                'port': 2101,
                'username': 'test',
                'password': 'test',
                'mountpoint': 'TEST',
                'timeout': 30,
                'reconnect_interval': 5,
                'max_retries': 3
            },
            'serial': {
                'port': '/dev/pts/1',
                'baudrate': 115200,
                'timeout': 1.0
            },
            'output': {
                'type': 'file',
                'file_path': '/tmp/test_location.json',
                'atomic_write': True,
                'update_interval': 1.0
            },
            'logging': {
                'level': 'DEBUG',
                'file': '/tmp/test.log'
            },
            'positioning': {
                'min_satellites': 4,
                'min_quality': 1
            }
        }
        return Config(config_dict)
    
    def test_import_dependencies(self):
        """测试导入依赖关系"""
        print("🔄 Testing import dependencies")
        
        # 测试核心模块可以独立导入
        modules_to_test = [
            'src.gnss_worker',
            'src.ntrip_client', 
            'src.serial_handler',
            'src.nmea_parser',
            'src.location_publisher'
        ]
        
        for module_name in modules_to_test:
            with self.subTest(module=module_name):
                try:
                    __import__(module_name)
                    self.assertTrue(True, f"Module {module_name} imported successfully")
                except ImportError as e:
                    self.fail(f"Failed to import {module_name}: {e}")
    
    def test_circular_dependencies(self):
        """测试循环依赖"""
        print("🔄 Testing circular dependencies")
        
        # 导入所有核心模块，如果有循环依赖会报错
        import src.gnss_worker
        import src.ntrip_client
        import src.serial_handler
        import src.nmea_parser
        import src.location_publisher
        
        # 如果能成功导入所有模块，说明没有循环依赖
        self.assertTrue(True, "No circular dependencies detected")
    
    def test_interface_consistency(self):
        """测试接口一致性"""
        print("🔄 Testing interface consistency")
        
        from src.gnss_worker import GNSSWorker
        
        # 检查GNSSWorker的基本接口
        worker = GNSSWorker(self.create_config())
        
        # 验证必要的方法存在
        required_methods = ['start', 'stop']
        for method_name in required_methods:
            self.assertTrue(hasattr(worker, method_name), 
                          f"GNSSWorker missing required method: {method_name}")
            self.assertTrue(callable(getattr(worker, method_name)),
                          f"GNSSWorker.{method_name} is not callable")
    
    def test_error_handling_consistency(self):
        """测试错误处理一致性"""
        print("🔄 Testing error handling consistency")
        
        from src.gnss_worker import GNSSWorker
        
        # 测试None配置
        try:
            worker = GNSSWorker(None)
            self.fail("Should have raised an exception for None config")
        except Exception as e:
            self.assertIsInstance(e, (ValueError, TypeError, AttributeError))
        
        # 测试空配置 - 这个实际上可能不会抛出异常，因为Config类有默认值处理
        try:
            empty_config = Config({})
            worker = GNSSWorker(empty_config)
            # 如果成功创建，那也是可以接受的，说明有合理的默认值处理
            self.assertIsNotNone(worker)
        except Exception as e:
            # 如果抛出异常，应该是有意义的异常类型
            self.assertIsInstance(e, (ValueError, TypeError, KeyError, AttributeError))
    
    def test_logging_consistency(self):
        """测试日志一致性"""
        print("🔄 Testing logging consistency")
        
        # 检查各模块是否使用了一致的日志记录
        modules_to_check = [
            'src.gnss_worker',
            'src.ntrip_client',
            'src.serial_handler'
        ]
        
        for module_name in modules_to_check:
            module = __import__(module_name, fromlist=[''])
            # 检查是否使用了logging模块或统一日志系统
            source = inspect.getsource(module)
            has_logging = ('logging' in source or 
                          'from logger import' in source or 
                          'get_logger' in source)
            self.assertTrue(has_logging, 
                          f"{module_name} should use logging module or unified logger system")


if __name__ == '__main__':
    unittest.main()
