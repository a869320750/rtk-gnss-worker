import unittest
from unittest.mock import patch, MagicMock
from src.ntrip_client import NTRIPClient

class TestNTRIPClient(unittest.TestCase):

    @patch('src.ntrip_client.socket.socket')
    def test_connect_success(self, mock_socket):
        mock_socket.return_value.connect.return_value = None
        # 使用正确的构造函数：传入config对象
        config = MagicMock()
        config.ntrip_host = "220.180.239.212"
        config.ntrip_port = 7990
        config.ntrip_user = "QL_NTRIP"
        config.ntrip_password = "123456"
        config.ntrip_mountpoint = "HeFei"
        
        client = NTRIPClient(config)
        result = client.connect()
        self.assertTrue(result)

    @patch('src.ntrip_client.socket.socket')
    def test_connect_failure(self, mock_socket):
        mock_socket.side_effect = Exception("Connection failed")
        # 使用正确的构造函数：传入config对象
        config = MagicMock()
        config.ntrip_host = "220.180.239.212"
        config.ntrip_port = 7990
        
        client = NTRIPClient(config)
        result = client.connect()
        self.assertFalse(result)

    @patch('src.ntrip_client.socket.socket')
    def test_send_gga(self, mock_socket):
        mock_socket.return_value.send = MagicMock()
        # 使用正确的构造函数
        config = MagicMock()
        config.ntrip_host = "220.180.239.212"
        config.ntrip_port = 7990
        
        client = NTRIPClient(config)
        client.connect()
        
        # 发送GGA数据
        gga_data = "$GPGGA,123456.00,3958.123,N,11629.456,E,1,08,1.5,100.0,M,50.0,M,,*7E"
        client.send_gga(gga_data)
        mock_socket.return_value.send.assert_called()

    @patch('src.ntrip_client.socket.socket')
    def test_receive_rtcm(self, mock_socket):
        mock_socket.return_value.recv.return_value = b'\x00\x01\x02\x03'
        # 使用正确的构造函数
        config = MagicMock()
        config.ntrip_host = "220.180.239.212"
        config.ntrip_port = 7990
        
        client = NTRIPClient(config)
        client.connect()
        
        # 接收RTCM数据
        data = client.receive_rtcm()
        self.assertEqual(data, b'\x00\x01\x02\x03')
        mock_socket.return_value.recv.assert_called()

    @patch('src.ntrip_client.socket.socket')
    def test_receive_rtcm(self, mock_socket):
        mock_socket.return_value.recv.return_value = b'\x00\x01\x02\x03'
        client = NTRIPClient("220.180.239.212", 7990, "QL_NTRIP", "123456", "HeFei")
        client.connect()
        data = client.receive_rtcm()
        self.assertEqual(data, b'\x00\x01\x02\x03')

if __name__ == '__main__':
    unittest.main()