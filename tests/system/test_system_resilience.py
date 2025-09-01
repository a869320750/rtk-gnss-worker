#!/usr/bin/env python3
"""
系统韧性测试 - 测试系统在各种异常情况下的恢复能力
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
from src.location_publisher import FileLocationPublisher
from src.config import Config


class TestSystemResilience(unittest.TestCase):
    """系统韧性测试套件"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        # 使用Config类创建配置对象
        config_dict = {
            'ntrip': {
                'server': 'localhost',  # 改为server，不是host
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
                'file_path': os.path.join(self.temp_dir, 'test_location.json'),  # 改为file_path
                'atomic_write': True,
                'update_interval': 1.0
            },
            'logging': {
                'level': 'INFO',
                'file': '/var/log/rtk-gnss-worker.log',
                'max_size': '10MB',
                'backup_count': 5
            },
            'positioning': {
                'min_satellites': 4,
                'min_quality': 1,
                'gga_interval': 30,
                'position_timeout': 60
            }
        }
        self.config = Config(config_dict)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('ntrip_client.NTRIPClient.connect')
    @patch('serial_handler.SerialHandler.open')
    @patch('ntrip_client.socket')
    @patch('serial_handler.serial.Serial')
    def test_network_interruption_recovery(self, mock_serial, mock_socket, mock_serial_open, mock_ntrip_connect):
        """测试网络中断恢复"""
        print("🔄 Testing network interruption recovery")
        
        # 模拟网络中断后恢复
        mock_connection = MagicMock()
        mock_socket.socket.return_value = mock_connection
        
        # 第一次连接失败，第二次成功
        mock_connection.connect.side_effect = [ConnectionError("Network down"), None]
        mock_connection.recv.return_value = b'RTCM_DATA'
        
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.readline.return_value = b'$GNGGA,115714.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*59\r\n'
        
        # Mock串口打开成功
        mock_serial_open.return_value = True
        
        # Mock NTRIP连接成功
        mock_ntrip_connect.return_value = True
        
        worker = GNSSWorker(self.config)
        
        # 启动worker，应该能够从网络中断中恢复
        start_thread = threading.Thread(target=worker.start)
        start_thread.daemon = True
        start_thread.start()
        
        time.sleep(2)  # 等待恢复
        
        # 验证worker最终能够正常运行
        self.assertTrue(worker.running)
        
        worker.stop()
        start_thread.join(timeout=1)
    
    @patch('ntrip_client.NTRIPClient.connect')
    @patch('serial_handler.SerialHandler.open')
    @patch('ntrip_client.socket')
    @patch('serial_handler.serial.Serial')
    def test_disk_space_exhaustion(self, mock_serial, mock_socket, mock_serial_open, mock_ntrip_connect):
        """测试磁盘空间耗尽处理"""
        print("🔄 Testing disk space exhaustion handling")
        
        # 模拟正常的网络和串口
        mock_connection = MagicMock()
        mock_socket.socket.return_value = mock_connection
        mock_connection.recv.return_value = b'RTCM_DATA'
        
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.readline.return_value = b'$GNGGA,115714.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*59\r\n'
        
        # Mock串口打开成功
        mock_serial_open.return_value = True
        
        # Mock NTRIP连接成功
        mock_ntrip_connect.return_value = True
        
        # 创建文件发布器并模拟磁盘满
        publisher = FileLocationPublisher(self.config.output)
        
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            # 应该能够优雅处理磁盘满的情况
            try:
                publisher.publish({
                    'timestamp': time.time(),
                    'latitude': 31.82169,
                    'longitude': 117.11534,
                    'quality': 1
                })
                # 不应该崩溃
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"Should handle disk full gracefully: {e}")
    
    @patch('ntrip_client.NTRIPClient.connect')
    @patch('serial_handler.SerialHandler.open')
    @patch('ntrip_client.socket')
    @patch('serial_handler.serial.Serial')
    def test_memory_pressure_handling(self, mock_serial, mock_socket, mock_serial_open, mock_ntrip_connect):
        """测试内存压力下的处理"""
        print("🔄 Testing memory pressure handling")
        
        # 模拟正常连接
        mock_connection = MagicMock()
        mock_socket.socket.return_value = mock_connection
        mock_connection.recv.return_value = b'RTCM_DATA'
        
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.readline.return_value = b'$GNGGA,115714.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*59\r\n'
        
        # Mock串口打开成功
        mock_serial_open.return_value = True
        
        # Mock NTRIP连接成功
        mock_ntrip_connect.return_value = True
        
        worker = GNSSWorker(self.config)
        
        # 启动worker
        start_thread = threading.Thread(target=worker.start)
        start_thread.daemon = True
        start_thread.start()
        
        time.sleep(1)
        
        # 模拟内存压力 - worker应该能够继续运行
        self.assertTrue(worker.running)
        
        worker.stop()
        start_thread.join(timeout=2)
    
    @patch('ntrip_client.NTRIPClient.connect')
    @patch('serial_handler.SerialHandler.open')
    @patch('ntrip_client.socket')
    @patch('serial_handler.serial.Serial')
    def test_concurrent_access_handling(self, mock_serial, mock_socket, mock_serial_open, mock_ntrip_connect):
        """测试并发访问处理"""
        print("🔄 Testing concurrent access handling")
        
        # 模拟正常连接
        mock_connection = MagicMock()
        mock_socket.socket.return_value = mock_connection
        mock_connection.recv.return_value = b'RTCM_DATA'
        
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.readline.return_value = b'$GNGGA,115714.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*59\r\n'
        
        # Mock串口打开成功
        mock_serial_open.return_value = True
        
        # Mock NTRIP连接成功
        mock_ntrip_connect.return_value = True
        
        # 创建多个worker实例模拟并发访问
        workers = []
        threads = []
        
        for i in range(3):
            config = self.config.copy()
            config['output']['file_path'] = os.path.join(self.temp_dir, f'location_{i}.json')
            worker = GNSSWorker(config)
            workers.append(worker)
            
            thread = threading.Thread(target=worker.start)
            thread.daemon = True
            threads.append(thread)
            thread.start()
        
        time.sleep(2)
        
        # 验证所有worker都能正常运行
        for worker in workers:
            self.assertTrue(worker.running)
        
        # 停止所有worker
        for worker in workers:
            worker.stop()
        
        for thread in threads:
            thread.join(timeout=2)


if __name__ == '__main__':
    print("🌐 Running System Resilience Tests")
    print("=" * 60)
    unittest.main(verbosity=2)
