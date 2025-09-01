#!/usr/bin/env python3
"""
架构设计测试 - 测试系统架构设计的正确性和性能
"""

import unittest
import time
import os
import sys
import threading
import queue
import memory_profiler
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.gnss_worker import GNSSWorker
from src.config import Config


class TestArchitectureDesign(unittest.TestCase):
    """架构设计测试套件"""
    
    def setUp(self):
        """测试前准备"""
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
        self.config = Config(config_dict)
    
    @patch('src.ntrip_client.socket')
    @patch('src.serial_handler.serial.Serial')
    def test_thread_separation(self, mock_serial, mock_socket):
        """测试线程分离架构"""
        print("🔄 Testing thread separation architecture")
        
        # 模拟连接
        mock_connection = MagicMock()
        mock_socket.socket.return_value = mock_connection
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        
        worker = GNSSWorker(self.config)
        
        # 验证双线程架构
        self.assertTrue(hasattr(worker, '_rtcm_thread'), "Should have RTCM thread")
        self.assertTrue(hasattr(worker, '_nmea_thread'), "Should have NMEA thread")
    
    def test_data_flow_architecture(self):
        """测试数据流架构"""
        print("🔄 Testing data flow architecture")
        
        with patch('src.ntrip_client.socket'), \
             patch('src.serial_handler.serial.Serial'):
            
            worker = GNSSWorker(self.config)
            
            # 验证数据流组件存在
            self.assertTrue(hasattr(worker, 'ntrip_client'), "Should have NTRIP client")
            self.assertTrue(hasattr(worker, 'serial_handler'), "Should have serial handler")
            self.assertTrue(hasattr(worker, 'nmea_parser'), "Should have NMEA parser")
            self.assertTrue(hasattr(worker, 'location_publisher'), "Should have location publisher")
    
    def test_error_isolation(self):
        """测试错误隔离架构"""
        print("🔄 Testing error isolation architecture")
        
        with patch('src.ntrip_client.socket'), \
             patch('src.serial_handler.serial.Serial'):
            
            worker = GNSSWorker(self.config)
            
            # 测试各组件可以独立初始化
            self.assertIsNotNone(worker.ntrip_client)
            self.assertIsNotNone(worker.serial_handler)
            self.assertIsNotNone(worker.nmea_parser)
            self.assertIsNotNone(worker.location_publisher)
    
    def test_resource_management(self):
        """测试资源管理架构"""
        print("🔄 Testing resource management architecture")
        
        with patch('src.ntrip_client.socket'), \
             patch('src.serial_handler.serial.Serial'):
            
            worker = GNSSWorker(self.config)
            
            # 验证资源管理方法存在
            self.assertTrue(hasattr(worker, 'start'), "Should have start method")
            self.assertTrue(hasattr(worker, 'stop'), "Should have stop method")
    
    def test_modularity_architecture(self):
        """测试模块化架构"""
        print("🔄 Testing modularity architecture")
        
        # 测试各模块可以独立导入
        modules = [
            'src.ntrip_client',
            'src.serial_handler', 
            'src.nmea_parser',
            'src.location_publisher'
        ]
        
        for module_name in modules:
            try:
                __import__(module_name)
                self.assertTrue(True, f"Module {module_name} can be imported independently")
            except ImportError as e:
                self.fail(f"Failed to import {module_name}: {e}")


class TestArchitecturePerformance(unittest.TestCase):
    """架构性能测试套件"""
    
    def setUp(self):
        """测试前准备"""
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
        self.config = Config(config_dict)
    
    def test_initialization_performance(self):
        """测试初始化性能"""
        print("🔄 Testing initialization performance")
        
        with patch('src.ntrip_client.socket'), \
             patch('src.serial_handler.serial.Serial'):
            
            start_time = time.time()
            worker = GNSSWorker(self.config)
            init_time = time.time() - start_time
            
            # 初始化应该在合理时间内完成（1秒内）
            self.assertLess(init_time, 1.0, f"Initialization took too long: {init_time:.3f}s")
    
    @patch('src.ntrip_client.socket')
    @patch('src.serial_handler.serial.Serial')
    def test_memory_architecture(self, mock_serial, mock_socket):
        """测试内存架构"""
        print("🔄 Testing memory architecture")
        
        # 测试内存使用是否合理
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        worker = GNSSWorker(self.config)
        
        after_init_memory = process.memory_info().rss
        memory_increase = after_init_memory - initial_memory
        
        # 初始化内存增长应该在合理范围内（50MB以内）
        max_memory_mb = 50 * 1024 * 1024  # 50MB
        self.assertLess(memory_increase, max_memory_mb, 
                       f"Memory increase too large: {memory_increase / 1024 / 1024:.2f}MB")


if __name__ == '__main__':
    unittest.main()
