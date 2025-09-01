#!/usr/bin/env python3
"""
Serial Mock Service
模拟GNSS设备的串口通信，发送NMEA格式的GPS数据
"""

import socket
import time
import threading
import logging
import signal
import sys
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class SerialMockService:
    def __init__(self, host='0.0.0.0', port=8888):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.running = False
        self.nmea_count = 0
        
        # 模拟GPS数据模板（不包含校验和，将自动计算）
        self.nmea_templates = [
            # GGA - Global Positioning System Fix Data
            "$GPGGA,{time},3958.7758,N,11619.4832,E,2,08,1.0,546.4,M,46.9,M,2.0,0000",
            # RMC - Recommended Minimum Navigation Information
            "$GPRMC,{time},A,3958.7758,N,11619.4832,E,0.0,0.0,{date},0.0,E,D",
            # GSA - GPS DOP and active satellites
            "$GPGSA,A,3,01,02,03,04,05,06,07,08,,,,,1.0,1.0,1.0",
            # GSV - GPS Satellites in view
            "$GPGSV,3,1,12,01,85,045,47,02,75,308,47,03,65,173,47,04,54,196,47",
            "$GPGSV,3,2,12,05,45,291,47,06,35,134,47,07,25,049,47,08,15,285,47",
            "$GPGSV,3,3,12,09,05,320,47,10,85,225,47,11,75,127,47,12,65,353,47"
        ]
    
    def start(self):
        """启动Serial Mock服务"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            logger.info(f"Serial Mock服务启动在 {self.host}:{self.port}")
            logger.info("等待客户端连接...")
            
            # 启动数据发送线程
            data_thread = threading.Thread(target=self._send_nmea_data, daemon=True)
            data_thread.start()
            
            # 接受客户端连接
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    logger.info(f"客户端连接: {client_address}")
                    self.clients.append(client_socket)
                    
                    # 为每个客户端启动处理线程
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        logger.error(f"接受连接时出错: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"启动Serial Mock服务失败: {e}")
            return False
        
        return True
    
    def _handle_client(self, client_socket, client_address):
        """处理客户端连接"""
        try:
            while self.running:
                # 接收客户端数据（如果有的话）
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    logger.debug(f"收到来自 {client_address} 的数据: {data.decode('utf-8', errors='ignore')}")
                except socket.timeout:
                    continue
                except socket.error:
                    break
                    
        except Exception as e:
            logger.error(f"处理客户端 {client_address} 时出错: {e}")
        finally:
            try:
                client_socket.close()
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
                logger.info(f"客户端 {client_address} 断开连接")
            except:
                pass
    
    def _send_nmea_data(self):
        """定期发送NMEA数据"""
        while self.running:
            try:
                if self.clients:
                    nmea_data = self._generate_nmea_sentence()
                    self._broadcast_data(nmea_data)
                    self.nmea_count += 1
                
                time.sleep(1)  # 每秒发送一次数据
                
            except Exception as e:
                logger.error(f"发送NMEA数据时出错: {e}")
                time.sleep(1)
    
    def _generate_nmea_sentence(self):
        """生成NMEA语句"""
        now = datetime.utcnow()
        time_str = now.strftime("%H%M%S.%f")[:-3]  # HHMMSS.sss
        date_str = now.strftime("%d%m%y")  # DDMMYY
        
        # 循环使用不同的NMEA模板
        template = self.nmea_templates[self.nmea_count % len(self.nmea_templates)]
        
        # 填充时间和日期，先移除原有校验和
        if '*' in template:
            template = template.split('*')[0]  # 移除旧校验和
        
        nmea_sentence = template.format(time=time_str, date=date_str)
        
        # 计算并添加正确的校验和
        nmea_with_checksum = self._add_nmea_checksum(nmea_sentence)
        
        return nmea_with_checksum + "\r\n"
    
    def _add_nmea_checksum(self, nmea_sentence):
        """为NMEA语句添加校验和"""
        # 移除开头的$符号进行校验和计算
        if nmea_sentence.startswith('$'):
            sentence_for_checksum = nmea_sentence[1:]
        else:
            sentence_for_checksum = nmea_sentence
        
        # 计算校验和
        checksum = 0
        for char in sentence_for_checksum:
            checksum ^= ord(char)
        
        # 返回带校验和的完整语句
        return f"{nmea_sentence}*{checksum:02X}"
    
    def _broadcast_data(self, data):
        """向所有连接的客户端广播数据"""
        disconnected_clients = []
        
        for client in self.clients[:]:  # 创建副本以避免修改时的问题
            try:
                client.send(data.encode('utf-8'))
                logger.debug(f"发送数据: {data.strip()}")
            except socket.error as e:
                logger.warning(f"向客户端发送数据失败: {e}")
                disconnected_clients.append(client)
        
        # 移除断开连接的客户端
        for client in disconnected_clients:
            try:
                client.close()
                if client in self.clients:
                    self.clients.remove(client)
            except:
                pass
    
    def stop(self):
        """停止服务"""
        logger.info("正在停止Serial Mock服务...")
        self.running = False
        
        # 关闭所有客户端连接
        for client in self.clients[:]:
            try:
                client.close()
            except:
                pass
        self.clients.clear()
        
        # 关闭服务器socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        logger.info("Serial Mock服务已停止")

def signal_handler(signum, frame):
    """信号处理函数"""
    logger.info(f"收到信号 {signum}, 正在退出...")
    if 'mock_service' in globals():
        mock_service.stop()
    sys.exit(0)

def health_check():
    """健康检查端点"""
    health_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    health_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        health_socket.bind(('0.0.0.0', 8889))  # 健康检查端口
        health_socket.listen(1)
        logger.info("健康检查服务启动在端口 8889")
        
        while True:
            try:
                client, addr = health_socket.accept()
                response = "HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"
                client.send(response.encode())
                client.close()
            except:
                break
                
    except Exception as e:
        logger.error(f"健康检查服务启动失败: {e}")
    finally:
        health_socket.close()

if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动健康检查服务
    health_thread = threading.Thread(target=health_check, daemon=True)
    health_thread.start()
    
    # 启动Serial Mock服务
    mock_service = SerialMockService()
    
    try:
        if mock_service.start():
            logger.info("Serial Mock服务运行中... 按 Ctrl+C 退出")
            # 保持主线程运行
            while mock_service.running:
                time.sleep(1)
        else:
            logger.error("无法启动Serial Mock服务")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("收到键盘中断信号")
    except Exception as e:
        logger.error(f"Serial Mock服务运行时出错: {e}")
    finally:
        mock_service.stop()
