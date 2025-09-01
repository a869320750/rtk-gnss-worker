"""
测试用例: 集成测试
"""

import unittest
import tempfile
import json
import os
import time
import threading
import signal
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gnss_worker import GNSSWorker
from config import Config


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        # 使用测试配置
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
        
        self.config = Config({
            'ntrip': {
                'server': 'localhost',
                'port': 7990,
                'username': 'test',
                'password': 'test',
                'mountpoint': 'TEST',
                'timeout': 5.0
            },
            'serial': {
                'port': '/tmp/mock_serial',
                'baudrate': 115200,
                'timeout': 1.0
            },
            'output': {
                'type': 'file',
                'file_path': self.temp_file.name,
                'atomic_write': True
            },
            'logging': {
                'level': 'DEBUG'
            }
        })
    
    def tearDown(self):
        os.unlink(self.temp_file.name)
        
        # 清理mock串口
        mock_serial_path = '/tmp/mock_serial'
        if os.path.exists(mock_serial_path):
            try:
                os.unlink(mock_serial_path)
            except:
                pass
    
    @patch('socket.socket')
    @patch('serial.Serial')
    def test_full_workflow(self, mock_serial, mock_socket):
        """测试完整工作流程"""
        # 模拟NTRIP连接
        mock_sock = Mock()
        mock_sock.recv.return_value = b"ICY 200 OK\r\n\r\n"
        mock_socket.return_value = mock_sock
        
        # 模拟串口
        mock_serial_instance = Mock()
        mock_serial_instance.readline.side_effect = [
            b"$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58\r\n",
            b"$GNGGA,115714.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*59\r\n",
        ]
        mock_serial.return_value = mock_serial_instance
        
        # 创建工作器
        worker = GNSSWorker(self.config)
        
        # 启动工作器
        worker.start()
        
        # 等待处理
        time.sleep(1)
        
        # 停止工作器
        worker.stop()
        
        # 验证输出文件
        self.assertTrue(os.path.exists(self.temp_file.name))
        
        with open(self.temp_file.name, 'r') as f:
            location_data = json.load(f)
        
        # 验证位置数据
        self.assertIn('latitude', location_data)
        self.assertIn('longitude', location_data)
        self.assertAlmostEqual(location_data['latitude'], 31.8216921, places=6)
        self.assertAlmostEqual(location_data['longitude'], 117.1153447, places=6)
    
    @patch('socket.socket')
    @patch('serial.Serial')
    def test_reconnection(self, mock_serial, mock_socket):
        """测试重连机制"""
        # 模拟连接失败后成功
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        # 第一次连接失败，第二次成功
        mock_sock.connect.side_effect = [ConnectionRefusedError(), None]
        mock_sock.recv.return_value = b"ICY 200 OK\r\n\r\n"
        
        mock_serial_instance = Mock()
        mock_serial.return_value = mock_serial_instance
        
        worker = GNSSWorker(self.config)
        worker.start()
        
        # 等待重连
        time.sleep(2)
        
        worker.stop()
        
        # 验证重连尝试
        self.assertEqual(mock_sock.connect.call_count, 2)
    
    @patch('socket.socket')
    @patch('serial.Serial')
    def test_data_corruption_handling(self, mock_serial, mock_socket):
        """测试数据损坏处理"""
        # 模拟NTRIP连接
        mock_sock = Mock()
        mock_sock.recv.return_value = b"ICY 200 OK\r\n\r\n"
        mock_socket.return_value = mock_sock
        
        # 模拟损坏的NMEA数据
        mock_serial_instance = Mock()
        mock_serial_instance.readline.side_effect = [
            b"corrupted data\r\n",  # 损坏数据
            b"$GNGGA,invalid,checksum*00\r\n",  # 无效校验和
            b"$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58\r\n",  # 有效数据
        ]
        mock_serial.return_value = mock_serial_instance
        
        worker = GNSSWorker(self.config)
        worker.start()
        
        # 等待处理
        time.sleep(1)
        
        worker.stop()
        
        # 验证只有有效数据被处理
        with open(self.temp_file.name, 'r') as f:
            location_data = json.load(f)
        
        self.assertAlmostEqual(location_data['latitude'], 31.8216921, places=6)
    
    @patch('socket.socket')
    @patch('serial.Serial')
    def test_signal_handling(self, mock_serial, mock_socket):
        """测试信号处理"""
        mock_sock = Mock()
        mock_sock.recv.return_value = b"ICY 200 OK\r\n\r\n"
        mock_socket.return_value = mock_sock
        
        mock_serial_instance = Mock()
        mock_serial_instance.readline.return_value = b"$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58\r\n"
        mock_serial.return_value = mock_serial_instance
        
        worker = GNSSWorker(self.config)
        
        # 设置信号处理
        def signal_handler(signum, frame):
            worker.stop()
        
        signal.signal(signal.SIGTERM, signal_handler)
        
        worker.start()
        
        # 发送信号
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGTERM)
        
        # 等待停止
        time.sleep(0.5)
        
        self.assertFalse(worker.running)


class TestPerformance(unittest.TestCase):
    """性能测试"""
    
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
        
        self.config = Config({
            'ntrip': {
                'server': 'localhost',
                'port': 7990,
                'username': 'test',
                'password': 'test',
                'mountpoint': 'TEST',
                'timeout': 5.0
            },
            'serial': {
                'port': '/tmp/mock_serial',
                'baudrate': 115200,
                'timeout': 1.0
            },
            'output': {
                'type': 'file',
                'file_path': self.temp_file.name,
                'atomic_write': True
            },
            'logging': {
                'level': 'ERROR'  # 减少日志输出
            }
        })
    
    def tearDown(self):
        os.unlink(self.temp_file.name)
    
    @patch('socket.socket')
    @patch('serial.Serial')
    def test_throughput(self, mock_serial, mock_socket):
        """测试吞吐量"""
        mock_sock = Mock()
        mock_sock.recv.return_value = b"ICY 200 OK\r\n\r\n"
        mock_socket.return_value = mock_sock
        
        # 模拟高频率NMEA数据
        nmea_data = b"$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58\r\n"
        mock_serial_instance = Mock()
        mock_serial_instance.readline.return_value = nmea_data
        mock_serial.return_value = mock_serial_instance
        
        worker = GNSSWorker(self.config)
        
        start_time = time.time()
        worker.start()
        
        # 运行5秒
        time.sleep(5)
        
        worker.stop()
        end_time = time.time()
        
        # 计算处理速率
        duration = end_time - start_time
        calls = mock_serial_instance.readline.call_count
        rate = calls / duration
        
        # 验证处理速率大于1Hz（基本要求）
        self.assertGreater(rate, 1.0)
        
        print(f"处理速率: {rate:.2f} 次/秒")
    
    @patch('socket.socket')
    @patch('serial.Serial')
    def test_memory_usage(self, mock_serial, mock_socket):
        """测试内存使用"""
        import psutil
        import socket
        
        # Mock socket with proper timeout behavior
        mock_sock = Mock()
        # 首次连接返回成功响应
        mock_sock.recv.side_effect = [
            b"ICY 200 OK\r\n\r\n",  # 连接时的响应
            socket.timeout,         # 后续接收RTCM时timeout
        ] + [socket.timeout] * 100  # 持续timeout避免疯狂循环
        mock_socket.return_value = mock_sock
        
        # Mock serial with proper timeout behavior
        mock_serial_instance = Mock()
        mock_serial_instance.readline.side_effect = [
            b"$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58\r\n",
            b"",  # 后续返回空，模拟timeout
        ] * 100  # 重复多次以支持测试期间的调用
        mock_serial.return_value = mock_serial_instance
        
        # 记录初始内存
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        worker = GNSSWorker(self.config)
        worker.start()
        
        # 运行一段时间
        time.sleep(10)
        
        # 记录运行时内存
        runtime_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        worker.stop()
        
        # 记录停止后内存
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"初始内存: {initial_memory:.2f} MB")
        print(f"运行时内存: {runtime_memory:.2f} MB")
        print(f"最终内存: {final_memory:.2f} MB")
        
        # 验证内存增长不超过50MB（嵌入式设备要求）
        memory_growth = runtime_memory - initial_memory
        self.assertLess(memory_growth, 50.0)


if __name__ == '__main__':
    unittest.main()
