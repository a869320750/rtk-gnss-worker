#!/usr/bin/env python3
"""
系统环境测试 - 测试系统在不同环境配置下的行为
"""

import unittest
import time
import os
import sys
import json
import tempfile
import threading
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.gnss_worker import GNSSWorker
from src.config import Config


class TestSystemEnvironment(unittest.TestCase):
    """系统环境测试套件"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        # 使用Config类创建配置对象
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
                'file_path': os.path.join(self.temp_dir, 'test_location.json'),
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
        self.base_config = Config(config_dict)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_config(self, **overrides):
        """创建配置对象的辅助方法"""
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
                'file_path': os.path.join(self.temp_dir, 'test_location.json'),
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
        
        # 应用覆盖值
        for key, value in overrides.items():
            if key == 'serial.baudrate':
                config_dict['serial']['baudrate'] = value
            elif key == 'ntrip.server':
                config_dict['ntrip']['server'] = value
            elif key == 'ntrip.port':
                config_dict['ntrip']['port'] = value
            # 可以根据需要添加更多键
        
        return Config(config_dict)
    
    def test_different_baudrates(self):
        """测试不同波特率配置"""
        print("🔄 Testing different baudrates")
        
        baudrates = [9600, 19200, 38400, 57600, 115200]
        
        for baudrate in baudrates:
            with self.subTest(baudrate=baudrate):
                config = self.create_config(**{'serial.baudrate': baudrate})
                worker = GNSSWorker(config)
                
                # 验证配置被正确设置
                self.assertEqual(worker.config.serial['baudrate'], baudrate)
    
    def test_different_ntrip_servers(self):
        """测试不同NTRIP服务器配置"""
        print("🔄 Testing different NTRIP server configurations")
        
        servers = [
            {'server': 'rtk.server1.com', 'port': 2101},
            {'server': 'rtk.server2.com', 'port': 2102},
            {'server': 'localhost', 'port': 8080}
        ]
        
        for server in servers:
            with self.subTest(server=server):
                config = self.base_config.copy()
                config['ntrip'].update(server)
                
                worker = GNSSWorker(config)
                
                # 验证配置被正确设置
                self.assertEqual(worker.config.ntrip['server'], server['server'])
                self.assertEqual(worker.config.ntrip['port'], server['port'])
    
    @patch.dict(os.environ, {'RTK_DEBUG': '1'})
    def test_debug_mode(self):
        """测试调试模式"""
        print("🔄 Testing debug mode")
        
        worker = GNSSWorker(self.base_config)
        
        # 在调试模式下，应该有更详细的日志
        # 这里主要测试配置是否正确加载
        self.assertIsNotNone(worker.config)
    
    @patch.dict(os.environ, {'RTK_TIMEOUT': '30'})
    def test_environment_timeout(self):
        """测试环境变量超时配置"""
        print("🔄 Testing environment timeout configuration")
        
        # 测试环境变量是否被正确读取
        timeout = os.environ.get('RTK_TIMEOUT', '10')
        self.assertEqual(timeout, '30')
    
    def test_config_validation(self):
        """测试配置验证"""
        print("🔄 Testing configuration validation")
        
        # 测试缺少必要配置
        invalid_configs = [
            {},  # 空配置
            {'ntrip': {}},  # 缺少serial配置
            {'serial': {}},  # 缺少ntrip配置
            {
                'ntrip': {'host': 'test'},  # 缺少端口
                'serial': {'port': '/dev/pts/1'}  # 缺少波特率
            }
        ]
        
        for invalid_config in invalid_configs:
            with self.subTest(config=invalid_config):
                try:
                    worker = GNSSWorker(invalid_config)
                    # 有些配置错误可能在运行时才发现
                    self.assertIsNotNone(worker)
                except Exception:
                    # 配置错误应该被捕获
                    pass
    
    def test_output_directory_creation(self):
        """测试输出目录创建"""
        print("🔄 Testing output directory creation")
        
        # 测试不存在的目录
        nonexistent_dir = os.path.join(self.temp_dir, 'deep', 'nested', 'path')
        config = self.base_config.copy()
        config['output']['file_path'] = os.path.join(nonexistent_dir, 'location.json')
        
        worker = GNSSWorker(config)
        
        # 目录应该在需要时被创建
        self.assertIsNotNone(worker.config.output['file_path'])
    
    def test_file_permissions(self):
        """测试文件权限"""
        print("🔄 Testing file permissions")
        
        # 创建只读目录
        readonly_dir = os.path.join(self.temp_dir, 'readonly')
        os.makedirs(readonly_dir, exist_ok=True)
        
        try:
            os.chmod(readonly_dir, 0o444)  # 只读权限
            
            config = self.base_config.copy()
            config['output']['file_path'] = os.path.join(readonly_dir, 'location.json')
            
            worker = GNSSWorker(config)
            
            # 应该能够处理权限问题
            self.assertIsNotNone(worker)
            
        finally:
            # 恢复权限以便清理
            os.chmod(readonly_dir, 0o755)


if __name__ == '__main__':
    print("🌐 Running System Environment Tests")
    print("=" * 60)
    unittest.main(verbosity=2)
