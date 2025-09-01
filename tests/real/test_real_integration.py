#!/usr/bin/env python3
"""
真正的端到端集成测试
使用实际的mock服务（NTRIP + Serial）进行完整数据流测试
"""

import unittest
import time
import json
import os
import sys
import socket
import tempfile
import subprocess
import threading
from dataclasses import asdict

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gnss_worker import GNSSWorker, LocationData
from config import Config

class TestRealIntegration(unittest.TestCase):
    """真正的端到端集成测试"""
    
    @classmethod
    def setUpClass(cls):
        """启动mock服务"""
        print("🚀 Starting real integration test with mock services")
        
        # 检查是否在Docker环境中
        if os.environ.get('GNSS_NTRIP_SERVER'):
            # Docker环境：使用服务名
            ntrip_host = os.environ.get('GNSS_NTRIP_SERVER', 'ntrip-mock')
            serial_host = os.environ.get('GNSS_SERIAL_HOST', 'serial-mock')
            ntrip_port = int(os.environ.get('GNSS_NTRIP_PORT', '2101'))
            serial_port = int(os.environ.get('GNSS_SERIAL_PORT', '8888'))
        else:
            # 本地环境：使用localhost
            ntrip_host = 'localhost'
            serial_host = 'localhost'
            ntrip_port = 2101
            serial_port = 8888
        
        cls.ntrip_host = ntrip_host
        cls.serial_host = serial_host
        cls.ntrip_port = ntrip_port
        cls.serial_port = serial_port
        
        # 等待mock服务就绪
        cls.wait_for_service(ntrip_host, ntrip_port, 'NTRIP Mock')
        cls.wait_for_service(serial_host, serial_port, 'Serial Mock')
        
        print("✅ All mock services are ready")
    
    @staticmethod
    def wait_for_service(host, port, service_name, timeout=60):
        """等待服务启动 - 增加超时时间"""
        print(f"⏳ Waiting for {service_name} at {host}:{port}")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)  # 增加socket超时
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    print(f"✅ {service_name} is ready")
                    return True
                    
            except Exception as e:
                print(f"   Connection attempt failed: {e}")
            
            print(f"   Retrying... ({int(time.time() - start_time)}s elapsed)")
            time.sleep(2)  # 增加重试间隔
        
        raise Exception(f"❌ {service_name} failed to start within {timeout}s")
    
    @staticmethod
    def diagnose_network():
        """诊断网络连接"""
        print("\n=== 网络诊断 ===")
        
        # 检查Docker网络
        try:
            result = subprocess.run(['docker', 'network', 'ls'], 
                                  capture_output=True, text=True, check=True)
            print("Docker网络:")
            print(result.stdout)
        except Exception as e:
            print(f"无法检查Docker网络: {e}")
        
        # 检查运行中的容器
        try:
            result = subprocess.run(['docker', 'ps'], 
                                  capture_output=True, text=True, check=True)
            print("运行中的容器:")
            print(result.stdout)
        except Exception as e:
            print(f"无法检查容器状态: {e}")
        
        # 尝试解析服务主机名
        for service in ['ntrip-mock', 'serial-mock']:
            try:
                ip = socket.gethostbyname(service)
                print(f"{service} 解析为: {ip}")
            except Exception as e:
                print(f"无法解析 {service}: {e}")
        
        # 检查端口连接
        test_hosts = [
            ('ntrip-mock', 2101),
            ('serial-mock', 8888),
            ('localhost', 2101),
            ('127.0.0.1', 2101),
        ]
        
        for host, port in test_hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                if result == 0:
                    print(f"✅ {host}:{port} 可达")
                else:
                    print(f"❌ {host}:{port} 不可达 (错误码: {result})")
            except Exception as e:
                print(f"❌ {host}:{port} 连接异常: {e}")
    
    def setUp(self):
        """测试前准备"""
        # 创建临时输出文件
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        
        # 配置连接到真实的mock服务（使用类变量）
        self.config = Config({
            'ntrip': {
                'server': self.ntrip_host,     # 动态主机名
                'port': self.ntrip_port,
                'username': 'test',
                'password': 'test',
                'mountpoint': 'RTCM3',         # Mock服务支持的挂载点
                'timeout': 5.0
            },
            'serial': {
                'host': self.serial_host,      # 动态主机名（TCP模式）
                'port': self.serial_port,      # SerialHandler会处理类型转换
                'timeout': 2.0
            },
            'output': {
                'type': 'file',
                'file_path': self.temp_file.name,
                'atomic_write': False          # 简化测试
            },
            'logging': {
                'level': 'INFO'
            }
        })
        
        self.received_locations = []
        
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def location_callback(self, location: LocationData):
        """位置数据回调"""
        self.received_locations.append(location)
        print(f"📍 Received location: {location.latitude:.6f}, {location.longitude:.6f} (Quality: {location.quality})")
    
    def test_end_to_end_data_flow(self):
        """测试端到端数据流"""
        print("\n🔄 Testing end-to-end RTK data flow")
        print("=" * 50)
        
        # 创建GNSS Worker
        worker = GNSSWorker(self.config)
        worker.set_location_callback(self.location_callback)
        
        try:
            # 启动工作器（双线程模式）
            print("🚀 Starting GNSS Worker...")
            success = worker.start(background=True)
            self.assertTrue(success, "Failed to start GNSS Worker")
            
            # 等待数据流建立
            print("⏳ Waiting for data flow to establish...")
            time.sleep(5)
            
            # 验证连接状态
            status = worker.get_status()
            print(f"📊 Worker Status: {status}")
            
            self.assertTrue(status['running'], "Worker should be running")
            self.assertTrue(status['ntrip_connected'], "NTRIP should be connected")
            self.assertTrue(status['serial_open'], "Serial should be open")
            self.assertTrue(status['rtcm_thread_alive'], "RTCM thread should be alive")
            self.assertTrue(status['nmea_thread_alive'], "NMEA thread should be alive")
            
            # 运行一段时间收集数据
            print("📡 Collecting NMEA data for 10 seconds...")
            run_duration = 10
            start_time = time.time()
            
            while time.time() - start_time < run_duration:
                time.sleep(1)
                print(f"⏱️  Running... {int(time.time() - start_time)}s, Locations: {len(self.received_locations)}")
            
            # 验证数据接收
            print(f"\n📈 Test Results:")
            print(f"   • Locations received: {len(self.received_locations)}")
            print(f"   • Average rate: {len(self.received_locations)/run_duration:.1f} locations/sec")
            
            # 断言：应该收到位置数据
            self.assertGreater(len(self.received_locations), 0, "Should receive at least one location")
            self.assertGreater(len(self.received_locations), 2, "Should receive multiple locations")  # 降低期望值到3+
            
            # 验证位置数据质量
            if self.received_locations:
                location = self.received_locations[0]
                self.assertIsInstance(location.latitude, float)
                self.assertIsInstance(location.longitude, float)
                self.assertIsInstance(location.altitude, float)
                self.assertGreaterEqual(location.quality, 0)
                self.assertGreaterEqual(location.satellites, 0)
                print(f"   • Sample location: {location.latitude:.6f}, {location.longitude:.6f}")
                print(f"   • Quality: {location.quality}, Satellites: {location.satellites}")
            
            # 验证文件输出
            self.assertTrue(os.path.exists(self.temp_file.name), "Output file should exist")
            
            if os.path.getsize(self.temp_file.name) > 0:
                with open(self.temp_file.name, 'r') as f:
                    try:
                        saved_data = json.load(f)
                        print(f"   • File output: ✅ Valid JSON saved")
                    except json.JSONDecodeError:
                        print(f"   • File output: ❌ Invalid JSON")
                        self.fail("Output file should contain valid JSON")
            
        finally:
            # 停止工作器
            print("\n🛑 Stopping GNSS Worker...")
            worker.stop()
            time.sleep(2)  # 等待线程完全停止
            
            final_status = worker.get_status()
            self.assertFalse(final_status['running'], "Worker should be stopped")
            print("✅ Worker stopped successfully")
    
    def test_rtcm_data_forwarding(self):
        """测试RTCM数据转发功能"""
        print("\n🔄 Testing RTCM data forwarding")
        print("=" * 40)
        
        worker = GNSSWorker(self.config)
        
        try:
            worker.start(background=True)
            
            # 短时间运行验证RTCM线程工作
            time.sleep(3)
            
            status = worker.get_status()
            self.assertTrue(status['rtcm_thread_alive'], "RTCM thread should be alive")
            self.assertTrue(status['ntrip_connected'], "Should connect to NTRIP mock")
            
            print("✅ RTCM thread is running and connected")
            
        finally:
            worker.stop()
    
    def test_dual_thread_architecture(self):
        """测试双线程架构在真实环境下的表现"""
        print("\n🔄 Testing dual-thread architecture")
        print("=" * 40)
        
        worker = GNSSWorker(self.config)
        worker.set_location_callback(self.location_callback)
        
        try:
            worker.start(background=True)
            time.sleep(8)  # 运行8秒
            
            status = worker.get_status()
            
            # 验证双线程都在运行
            self.assertTrue(status['rtcm_thread_alive'], "RTCM thread should be alive")
            self.assertTrue(status['nmea_thread_alive'], "NMEA thread should be alive")
            
            # 验证数据接收（证明线程工作正常）
            self.assertGreater(len(self.received_locations), 0, "Should receive location data")
            
            print(f"✅ Both threads working, received {len(self.received_locations)} locations")
            
        finally:
            worker.stop()

if __name__ == '__main__':
    print("🧪 Real Integration Test Suite")
    print("=" * 50)
    print("📋 This test requires running mock services:")
    print("   • NTRIP Mock (port 2101)")
    print("   • Serial Mock (port 8888)")
    print("=" * 50)
    
    unittest.main(verbosity=2)
