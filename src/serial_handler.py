"""
串口处理器 - 简化版本，支持TCP和串口
"""

import serial
import socket
import time
from logger import get_logger
from typing import Optional

class SerialHandler:
    """简化的串口处理器，支持TCP socket和真实串口"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger()
        self.connection = None
        self.is_open = False
        self.is_tcp = False
        
        # 判断是TCP还是串口连接
        port = config.get('port', '')
        host = config.get('host')
        
        # 如果有host配置，或者port是整数（TCP端口），则使用TCP连接
        if host or isinstance(port, int):
            self.is_tcp = True
        elif isinstance(port, str) and (port.startswith('socket://') or port.startswith('tcp://')):
            self.is_tcp = True
            
            # 解析socket://或tcp://格式的URL
            url_part = port.replace('socket://', '').replace('tcp://', '')
            if ':' in url_part:
                host_part, port_str = url_part.split(':', 1)
                self.config['host'] = host_part
                self.config['tcp_port'] = int(port_str)
            else:
                self.config['host'] = url_part
                self.config['tcp_port'] = 9999  # 默认端口
        elif config.get('tcp_port'):
            # 如果直接配置了tcp_port，也使用TCP模式
            self.is_tcp = True
        else:
            self.is_tcp = False
        
    def open(self) -> bool:
        """打开连接（TCP socket或串口）"""
        try:
            if self.is_tcp:
                return self._open_tcp()
            else:
                return self._open_serial()
        except Exception as e:
            self.logger.error(f"Failed to open connection: {e}")
            return False
    
    def _open_tcp(self) -> bool:
        """打开TCP连接"""
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host = self.config['host']
            port = self.config.get('tcp_port', int(self.config.get('port', 9999)))
            self.connection.connect((host, port))
            self.connection.settimeout(self.config.get('timeout', 1.0))
            self.is_open = True
            self.logger.info(f"TCP connection to {host}:{port} opened successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to open TCP connection: {e}")
            return False
    
    def _open_serial(self) -> bool:
        """打开串口连接"""
        try:
            self.connection = serial.Serial(
                port=self.config['port'],
                baudrate=self.config.get('baudrate', 115200),
                timeout=self.config.get('timeout', 1.0),
                bytesize=self.config.get('bytesize', 8),
                parity=self.config.get('parity', 'N'),
                stopbits=self.config.get('stopbits', 1)
            )
            
            self.is_open = self.connection.is_open
            self.logger.info(f"Serial port {self.config['port']} opened successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to open serial port: {e}")
            return False
    
    def connect(self) -> bool:
        """连接串口 (与open方法相同，为了向后兼容)"""
        return self.open()
    
    def close(self):
        """关闭连接"""
        if self.connection:
            if self.is_tcp:
                self.connection.close()
            else:
                if hasattr(self.connection, 'is_open') and self.connection.is_open:
                    self.connection.close()
        self.is_open = False
        self.logger.info("Connection closed")
    
    def write_rtcm(self, data: bytes) -> bool:
        """写入RTCM数据"""
        if not self.is_open or not self.connection:
            return False
        
        try:
            if self.is_tcp:
                self.connection.sendall(data)
            else:
                self.connection.write(data)
            return True
        except Exception as e:
            self.logger.error(f"Failed to write RTCM data: {e}")
            return False
    
    def write(self, data) -> bool:
        """写入数据（向后兼容）"""
        if isinstance(data, str):
            return self.write_rtcm(data.encode('utf-8'))
        elif isinstance(data, bytes):
            return self.write_rtcm(data)
        else:
            self.logger.error(f"Unsupported data type: {type(data)}")
            return False
    
    def read_nmea(self, timeout: float = 1.0) -> Optional[str]:
        """读取NMEA数据"""
        if not self.is_open or not self.connection:
            return None
        
        try:
            if self.is_tcp:
                line = self._read_line_tcp(timeout)
            else:
                line = self._read_line_serial(timeout)
                
            # 实时打印接收到的数据
            if line:
                # 只打印NMEA语句，过滤空行
                if line.startswith('$') and len(line) > 10:
                    self.logger.info(f"📥 接收NMEA: {line}")
                elif line.strip():
                    self.logger.debug(f"📥 接收数据: {line}")
                    
            return line
        except Exception as e:
            self.logger.error(f"Failed to read NMEA data: {e}")
            return None
    
    def read_line(self) -> Optional[str]:
        """读取一行数据（向后兼容）"""
        return self.read_nmea()
    
    def _read_line_tcp(self, timeout: float) -> Optional[str]:
        """从TCP连接读取一行"""
        self.connection.settimeout(timeout)
        try:
            line = b""
            while True:
                char = self.connection.recv(1)
                if not char:
                    break
                line += char
                if char == b'\n':
                    break
            
            if line:
                return line.decode('utf-8', errors='ignore').strip()
        except socket.timeout:
            pass
        except Exception as e:
            self.logger.error(f"TCP read error: {e}")
        
        return None
    
    def _read_line_serial(self, timeout: float) -> Optional[str]:
        """从串口读取一行"""
        old_timeout = self.connection.timeout
        self.connection.timeout = timeout
        try:
            line = self.connection.readline()
            if line:
                return line.decode('utf-8', errors='ignore').strip()
        except Exception as e:
            self.logger.error(f"Serial read error: {e}")
        finally:
            self.connection.timeout = old_timeout
        
        return None
