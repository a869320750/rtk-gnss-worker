# -*- coding: utf-8 -*-
"""
增强的NTRIP客户端 - 支持网络诊断和错误处理
"""

import socket
import base64
import time
from logger import get_logger

class NTRIPClient:
    """简化的NTRIP客户端"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger()
        self.socket = None
        self.connected = False
        
    def connect(self, retry_count: int = 3) -> bool:
        """连接NTRIP服务器，支持重试"""
        for attempt in range(retry_count):
            try:
                self.logger.info(f"NTRIP连接尝试 {attempt + 1}/{retry_count}")
                
                # 网络连通性测试
                self.logger.info(f"正在连接服务器 {self.config['server']}:{self.config['port']}...")
                
                # 创建socket连接
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.config.get('timeout', 15))
                
                # 连接到服务器
                connect_start = time.time()
                self.socket.connect((self.config['server'], self.config['port']))
                connect_time = time.time() - connect_start
                self.logger.info(f"TCP连接成功，用时 {connect_time:.2f}秒")
                
                # 构建NTRIP请求
                auth_string = f"{self.config['username']}:{self.config['password']}"
                auth_bytes = base64.b64encode(auth_string.encode()).decode()
                
                request = (
                    f"GET /{self.config['mountpoint']} HTTP/1.1\r\n"
                    f"User-Agent: {self.config.get('user_agent', 'NTRIP Client')}\r\n"
                    f"Authorization: Basic {auth_bytes}\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                )
                
                self.logger.info(f"发送NTRIP请求到挂载点: {self.config['mountpoint']}")
                self.socket.send(request.encode())
                
                # 等待响应
                response_data = b''
                start_time = time.time()
                while time.time() - start_time < 10:  # 10秒超时
                    try:
                        data = self.socket.recv(1024)
                        if not data:
                            break
                        response_data += data
                        if b'\r\n\r\n' in response_data:
                            break
                    except socket.timeout:
                        break
                
                response = response_data.decode('utf-8', errors='ignore')
                self.logger.info(f"服务器响应: {response[:200]}...")
                
                if "ICY 200 OK" in response:
                    self.connected = True
                    self.logger.info("NTRIP连接成功")
                    return True
                elif "SOURCETABLE" in response:
                    self.logger.warning(f"接收到源表而非数据流。挂载点 '{self.config['mountpoint']}' 可能不存在。")
                    
                    # 解析源表，寻找可用的挂载点
                    mountpoints = self._parse_sourcetable(response_data.decode('utf-8', errors='ignore'))
                    
                    if mountpoints:
                        # 尝试使用第一个找到的挂载点
                        new_mountpoint = mountpoints[0]
                        self.logger.info(f"发现可用挂载点: {new_mountpoint}，尝试连接...")
                        
                        # 关闭当前连接
                        if self.socket:
                            try:
                                self.socket.close()
                            except:
                                pass
                            self.socket = None
                        
                        # 更新配置并重试（仅第一次尝试时）
                        if attempt == 0:
                            original_mountpoint = self.config['mountpoint']
                            self.config['mountpoint'] = new_mountpoint
                            result = self.connect(retry_count=1)
                            if not result:
                                self.config['mountpoint'] = original_mountpoint  # 恢复原配置
                            return result
                    else:
                        # 尝试常见的挂载点
                        if self.config['mountpoint'] not in ['RTCM33_GRC', 'RTCM33_GRCEJ'] and attempt == 0:
                            common_mountpoints = ['RTCM33_GRC', 'RTCM33_GRCEJ', 'RTCM3', 'RTCM32']
                            for mp in common_mountpoints:
                                self.logger.info(f"尝试常见挂载点: {mp}")
                                if self._try_single_connection(mp):
                                    self.config['mountpoint'] = mp
                                    return True
                    
                    # 关闭socket
                    if self.socket:
                        try:
                            self.socket.close()
                        except:
                            pass
                        self.socket = None
                elif "401" in response or "403" in response:
                    self.logger.error(f"认证失败: {response}")
                    return False
                else:
                    self.logger.error(f"NTRIP连接失败: {response}")
                
            except socket.timeout:
                self.logger.error(f"连接超时（第{attempt + 1}次尝试）")
            except socket.gaierror as e:
                self.logger.error(f"DNS解析失败: {e}")
                return False  # DNS错误通常不需要重试
            except ConnectionRefusedError:
                self.logger.error(f"连接被拒绝，服务器可能不可用")
            except Exception as e:
                self.logger.error(f"NTRIP连接错误: {e}")
            
            # 清理socket
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < retry_count - 1:
                time.sleep(1)
                self.logger.info("等待重试...")
        
        self.logger.error("NTRIP连接失败")
        return False

    def _parse_sourcetable(self, sourcetable_data):
        """解析NTRIP源表，提取可用的挂载点"""
        mountpoints = []
        
        try:
            lines = sourcetable_data.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('STR;'):
                    # NTRIP源表格式：STR;mountpoint;identifier;format;format-details;...
                    parts = line.split(';')
                    if len(parts) > 1:
                        mountpoint = parts[1].strip()
                        if mountpoint and mountpoint != '':
                            mountpoints.append(mountpoint)
                            self.logger.info(f"在源表中发现挂载点: {mountpoint}")
            
            if mountpoints:
                self.logger.info(f"共发现 {len(mountpoints)} 个挂载点: {', '.join(mountpoints[:5])}{'...' if len(mountpoints) > 5 else ''}")
            else:
                self.logger.warning("源表中未发现挂载点")
                
        except Exception as e:
            self.logger.error(f"解析源表错误: {str(e)}")
            
        return mountpoints
    
    def _try_single_connection(self, mountpoint):
        """尝试连接单个挂载点"""
        try:
            # 创建新的socket连接
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(10)
            test_socket.connect((self.config['server'], self.config['port']))
            
            # 构建请求
            auth_string = f"{self.config['username']}:{self.config['password']}"
            auth_bytes = base64.b64encode(auth_string.encode()).decode()
            
            request = (
                f"GET /{mountpoint} HTTP/1.1\r\n"
                f"User-Agent: {self.config.get('user_agent', 'NTRIP Client')}\r\n"
                f"Authorization: Basic {auth_bytes}\r\n"
                f"Connection: close\r\n"
                f"\r\n"
            )
            
            test_socket.send(request.encode())
            
            # 等待响应
            response_data = b''
            start_time = time.time()
            while time.time() - start_time < 5:  # 5秒超时
                try:
                    data = test_socket.recv(1024)
                    if not data:
                        break
                    response_data += data
                    if b'\r\n\r\n' in response_data:
                        break
                except socket.timeout:
                    break
            
            response = response_data.decode('utf-8', errors='ignore')
            
            if "ICY 200 OK" in response:
                # 成功连接，替换主socket
                if self.socket:
                    try:
                        self.socket.close()
                    except:
                        pass
                self.socket = test_socket
                self.connected = True
                self.logger.info(f"成功连接到挂载点: {mountpoint}")
                return True
            else:
                test_socket.close()
                return False
                
        except Exception as e:
            self.logger.debug(f"连接挂载点 {mountpoint} 失败: {str(e)}")
            if 'test_socket' in locals():
                try:
                    test_socket.close()
                except:
                    pass
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False
        self.logger.info("NTRIP连接已断开")
    
    def send_gga(self, gga_line: str) -> bool:
        """发送GGA心跳数据"""
        if not self.connected or not self.socket:
            return False
        
        try:
            self.socket.send(gga_line.encode())
            return True
        except Exception as e:
            self.logger.error(f"发送GGA失败: {e}")
            self.connected = False
            return False
    
    def receive_rtcm(self, timeout: float = 1.0) -> bytes:
        """接收RTCM数据"""
        if not self.connected or not self.socket:
            return b''
        
        try:
            self.socket.settimeout(timeout)
            data = self.socket.recv(4096)
            return data
        except socket.timeout:
            return b''
        except Exception as e:
            self.logger.error(f"接收RTCM失败: {e}")
            self.connected = False
            return b''
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.connected
