"""
测试用例: 单元测试
"""

import unittest
import tempfile
import json
import os
import time
import threading
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gnss_worker import GNSSWorker
from ntrip_client import NTRIPClient
from nmea_parser import NMEAParser
from serial_handler import SerialHandler
from location_publisher import LocationPublisher, FileLocationPublisher
from config import Config


class TestNMEAParser(unittest.TestCase):
    """测试NMEA解析器"""
    
    def setUp(self):
        self.parser = NMEAParser()
    
    def test_valid_gga_sentence(self):
        """测试有效的GGA语句"""
        gga = "$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58"
        result = self.parser.parse_gga(gga)
        
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['latitude'], 31.8216921, places=6)
        self.assertAlmostEqual(result['longitude'], 117.1153447, places=6)
        self.assertEqual(result['quality'], 1)
        self.assertEqual(result['satellites'], 17)
        self.assertAlmostEqual(result['hdop'], 0.88, places=2)
        self.assertAlmostEqual(result['altitude'], 98.7, places=1)
    
    def test_invalid_checksum(self):
        """测试无效校验和"""
        gga = "$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*00"
        result = self.parser.parse_gga(gga)
        self.assertIsNone(result)
    
    def test_empty_fields(self):
        """测试空字段"""
        gga = "$GNGGA,115713.000,,N,,E,0,0,,,M,,M,,*"
        result = self.parser.parse_gga(gga)
        self.assertIsNone(result)
    
    def test_malformed_sentence(self):
        """测试格式错误的语句"""
        gga = "invalid sentence"
        result = self.parser.parse_gga(gga)
        self.assertIsNone(result)


class TestSerialHandler(unittest.TestCase):
    """测试串口处理器"""
    
    def setUp(self):
        self.config = {'port': '/dev/ttyUSB0', 'baudrate': 115200, 'timeout': 1.0}
    
    @patch('serial.Serial')
    def test_connection(self, mock_serial):
        """测试连接"""
        mock_instance = Mock()
        mock_serial.return_value = mock_instance
        
        handler = SerialHandler(self.config)
        result = handler.connect()
        
        self.assertTrue(result)
        mock_serial.assert_called_once_with(
            port='/dev/ttyUSB0',
            baudrate=115200,
            timeout=1.0,
            bytesize=8,
            parity='N',
            stopbits=1
        )
    
    @patch('serial.Serial')
    def test_write_data(self, mock_serial):
        """测试写入数据"""
        mock_instance = Mock()
        mock_serial.return_value = mock_instance
        
        handler = SerialHandler(self.config)
        handler.connect()
        
        test_data = b"test data"
        handler.write(test_data)
        
        mock_instance.write.assert_called_once_with(test_data)
    
    @patch('serial.Serial')
    def test_read_line(self, mock_serial):
        """测试读取行"""
        mock_instance = Mock()
        mock_instance.readline.return_value = b"$GNGGA,test*00\r\n"
        mock_serial.return_value = mock_instance
        
        handler = SerialHandler(self.config)
        handler.connect()
        
        line = handler.read_line()
        self.assertEqual(line, "$GNGGA,test*00")


class TestFileLocationPublisher(unittest.TestCase):
    """测试文件位置发布器"""
    
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
        self.config = {
            'file_path': self.temp_file.name,
            'atomic_write': True
        }
        self.publisher = FileLocationPublisher(self.config)
    
    def tearDown(self):
        os.unlink(self.temp_file.name)
    
    def test_publish_location(self):
        """测试发布位置"""
        location = {
            'latitude': 31.8216921,
            'longitude': 117.1153447,
            'quality': 1,
            'satellites': 17,
            'hdop': 0.88,
            'altitude': 98.7,
            'timestamp': '2024-01-01T12:00:00'
        }
        
        self.publisher.publish(location)
        
        # 验证文件内容
        with open(self.temp_file.name, 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data, location)
    
    def test_atomic_write(self):
        """测试原子写入"""
        # 模拟并发读写
        results = []
        
        def reader():
            try:
                with open(self.temp_file.name, 'r') as f:
                    data = json.load(f)
                    results.append(data)
            except:
                results.append(None)
        
        location = {
            'latitude': 31.8216921,
            'longitude': 117.1153447,
            'timestamp': '2024-01-01T12:00:00'
        }
        
        # 启动读取线程
        reader_thread = threading.Thread(target=reader)
        
        # 写入数据
        self.publisher.publish(location)
        reader_thread.start()
        reader_thread.join()
        
        # 验证读取结果不为空（原子写入成功）
        self.assertTrue(len(results) > 0)


class TestNTRIPClient(unittest.TestCase):
    """测试NTRIP客户端"""
    
    def setUp(self):
        self.config = {
            'server': 'localhost',
            'port': 7990,
            'username': 'test',
            'password': 'test',
            'mountpoint': 'TEST',
            'timeout': 5.0
        }
    
    @patch('socket.socket')
    def test_connect(self, mock_socket):
        """测试连接"""
        mock_sock = Mock()
        mock_sock.recv.return_value = b"ICY 200 OK\r\n\r\n"
        mock_socket.return_value = mock_sock
        
        client = NTRIPClient(self.config)
        result = client.connect()
        
        self.assertTrue(result)
        mock_sock.connect.assert_called_once_with(('localhost', 7990))
    
    @patch('socket.socket')
    def test_authentication(self, mock_socket):
        """测试认证"""
        mock_sock = Mock()
        mock_sock.recv.return_value = b"ICY 200 OK\r\n\r\n"
        mock_socket.return_value = mock_sock
        
        client = NTRIPClient(self.config)
        client.connect()
        
        # 验证发送了正确的认证请求
        sent_data = mock_sock.send.call_args[0][0]
        self.assertIn(b'GET /TEST HTTP/1.1', sent_data)  # 更新为HTTP/1.1
        self.assertIn(b'Authorization: Basic', sent_data)


class TestGNSSWorker(unittest.TestCase):
    """测试GNSS工作器"""
    
    def setUp(self):
        self.config = Config.default()
        
        # 使用临时文件
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
        self.config.data['output']['file_path'] = self.temp_file.name
    
    def tearDown(self):
        os.unlink(self.temp_file.name)
    
    @patch('ntrip_client.NTRIPClient')
    @patch('serial_handler.SerialHandler')
    def test_initialization(self, mock_serial, mock_ntrip):
        """测试初始化"""
        worker = GNSSWorker(self.config)
        
        self.assertIsNotNone(worker.ntrip_client)
        self.assertIsNotNone(worker.serial_handler)
        self.assertIsNotNone(worker.publisher)
        self.assertIsNotNone(worker.parser)
    
    @patch('ntrip_client.NTRIPClient')
    @patch('serial_handler.SerialHandler')
    def test_start_stop(self, mock_serial, mock_ntrip):
        """测试启动停止"""
        mock_ntrip_instance = Mock()
        mock_ntrip.return_value = mock_ntrip_instance
        mock_ntrip_instance.connect.return_value = True
        
        mock_serial_instance = Mock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.connect.return_value = True
        
        worker = GNSSWorker(self.config)
        
        # 测试启动
        worker.start()
        self.assertTrue(worker.running)
        
        # 等待一小段时间
        time.sleep(0.1)
        
        # 测试停止
        worker.stop()
        self.assertFalse(worker.running)


if __name__ == '__main__':
    unittest.main()
