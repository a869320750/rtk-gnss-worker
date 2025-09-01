#!/usr/bin/env python3
"""
NTRIP Mock Service
模拟NTRIP差分数据服务，用于RTK测试
"""

import socket
import threading
import time
import logging
import signal
import sys
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class NTRIPMockHandler(BaseHTTPRequestHandler):
    """NTRIP Mock HTTP处理器"""
    
    def log_message(self, format, *args):
        """重写日志方法使用我们的logger"""
        logger.info("%s - - [%s] %s" % (
            self.address_string(),
            self.log_date_time_string(),
            format % args
        ))
    
    def do_GET(self):
        """处理HTTP GET请求"""
        logger.info(f"收到GET请求: {self.path}")
        
        if self.path == '/':
            # 返回NTRIP源表
            self.send_sourcetable()
        elif self.path.startswith('/RTCM3'):
            # 处理NTRIP挂载点请求
            self.handle_mountpoint()
        else:
            self.send_error(404, "Not Found")
    
    def send_sourcetable(self):
        """发送NTRIP源表"""
        sourcetable = (
            "SOURCETABLE 200 OK\r\n"
            "Server: NTRIP Mock Server\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 150\r\n"
            "\r\n"
            "STR;RTCM3;RTCM3;RTCM 3.0;1005,1077,1087;2;GPS+GLO;SNIP;CHN;39.58;116.19;1;0;sNTRIP;none;B;N;0;\r\n"
            "ENDSOURCETABLE\r\n"
        )
        
        self.wfile.write(sourcetable.encode('utf-8'))
        logger.info("发送源表完成")
    
    def handle_mountpoint(self):
        """处理挂载点连接"""
        # 检查授权
        auth_header = self.headers.get('Authorization')
        if not auth_header or not self.check_auth(auth_header):
            self.send_auth_required()
            return
        
        logger.info("客户端授权成功，开始发送RTCM数据")
        
        # 发送ICY响应头
        response = (
            "ICY 200 OK\r\n"
            "Server: NTRIP Mock Server\r\n"
            "Content-Type: application/octet-stream\r\n"
            "Cache-Control: no-cache\r\n"
            "Pragma: no-cache\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        
        self.wfile.write(response.encode('utf-8'))
        
        # 开始发送模拟RTCM数据
        self.send_rtcm_data()
    
    def check_auth(self, auth_header):
        """检查HTTP基本认证"""
        try:
            auth_type, auth_string = auth_header.split(' ', 1)
            if auth_type.lower() != 'basic':
                return False
            
            username_password = base64.b64decode(auth_string).decode('utf-8')
            username, password = username_password.split(':', 1)
            
            # 简单的用户名密码验证
            return username == "test" and password == "test"
            
        except Exception as e:
            logger.error(f"认证解析失败: {e}")
            return False
    
    def send_auth_required(self):
        """发送401认证要求"""
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="NTRIP"')
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Authorization Required")
    
    def send_rtcm_data(self):
        """发送模拟RTCM数据"""
        try:
            # 模拟RTCM消息数据
            rtcm_messages = [
                # RTCM 1005 - 站点坐标信息
                bytes([0xD3, 0x00, 0x13, 0x3E, 0xD0, 0x00, 0x03, 0x8A, 0x0E, 0xDE, 0xEF, 0x34, 0xB4, 0xBD, 0x62, 0xAC, 0x09, 0x41, 0x98, 0x6F, 0x33, 0x36, 0x0B, 0x98]),
                
                # RTCM 1077 - GPS MSM7
                bytes([0xD3, 0x00, 0x1C, 0x43, 0x50, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x24, 0x15, 0x27]),
                
                # RTCM 1087 - GLONASS MSM7  
                bytes([0xD3, 0x00, 0x1C, 0x43, 0xF0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x6C, 0x95, 0x21])
            ]
            
            message_count = 0
            while True:
                try:
                    # 循环发送RTCM消息
                    rtcm_data = rtcm_messages[message_count % len(rtcm_messages)]
                    self.wfile.write(rtcm_data)
                    self.wfile.flush()
                    
                    logger.debug(f"发送RTCM消息 #{message_count + 1}, 长度: {len(rtcm_data)} 字节")
                    message_count += 1
                    
                    time.sleep(1)  # 每秒发送一次
                    
                except (ConnectionResetError, BrokenPipeError):
                    logger.info("客户端断开连接")
                    break
                except Exception as e:
                    logger.error(f"发送RTCM数据时出错: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"RTCM数据发送失败: {e}")

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """支持多线程的HTTP服务器"""
    daemon_threads = True
    allow_reuse_address = True

class NTRIPMockService:
    def __init__(self, host='0.0.0.0', port=2101):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
    
    def start(self):
        """启动NTRIP Mock服务"""
        try:
            self.server = ThreadingHTTPServer((self.host, self.port), NTRIPMockHandler)
            self.running = True
            
            logger.info(f"NTRIP Mock服务启动在 {self.host}:{self.port}")
            logger.info("用户名: test, 密码: test")
            logger.info("挂载点: /RTCM3")
            
            # 启动健康检查线程
            health_thread = threading.Thread(target=self._health_check, daemon=True)
            health_thread.start()
            
            # 在单独线程中运行服务器
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"启动NTRIP Mock服务失败: {e}")
            return False
    
    def _health_check(self):
        """健康检查服务"""
        health_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        health_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            health_socket.bind(('0.0.0.0', 2102))  # 健康检查端口
            health_socket.listen(1)
            logger.info("NTRIP健康检查服务启动在端口 2102")
            
            while self.running:
                try:
                    health_socket.settimeout(1.0)
                    client, addr = health_socket.accept()
                    response = "HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"
                    client.send(response.encode())
                    client.close()
                except socket.timeout:
                    continue
                except:
                    break
                    
        except Exception as e:
            logger.error(f"NTRIP健康检查服务启动失败: {e}")
        finally:
            health_socket.close()
    
    def stop(self):
        """停止服务"""
        logger.info("正在停止NTRIP Mock服务...")
        self.running = False
        
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        if self.server_thread:
            self.server_thread.join(timeout=5)
        
        logger.info("NTRIP Mock服务已停止")

def signal_handler(signum, frame):
    """信号处理函数"""
    logger.info(f"收到信号 {signum}, 正在退出...")
    if 'ntrip_service' in globals():
        ntrip_service.stop()
    sys.exit(0)

if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动NTRIP Mock服务
    ntrip_service = NTRIPMockService()
    
    try:
        if ntrip_service.start():
            logger.info("NTRIP Mock服务运行中... 按 Ctrl+C 退出")
            # 保持主线程运行
            while ntrip_service.running:
                time.sleep(1)
        else:
            logger.error("无法启动NTRIP Mock服务")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("收到键盘中断信号")
    except Exception as e:
        logger.error(f"NTRIP Mock服务运行时出错: {e}")
    finally:
        ntrip_service.stop()
