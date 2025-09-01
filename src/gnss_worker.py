"""
简化的RTK GNSS Worker - 专为低功耗嵌入式设备设计
"""

import time
from logger import get_logger
import threading
from typing import Optional, Callable
from dataclasses import dataclass

@dataclass
class LocationData:
    """位置数据"""
    timestamp: float
    latitude: float
    longitude: float
    altitude: float
    quality: int
    satellites: int
    hdop: float
    raw_nmea: str

class GNSSWorker:
    """
    RTK GNSS工作器 - 简化版本
    专注于核心功能，优化功耗
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger()
        
        # 延迟导入避免循环引用
        from ntrip_client import NTRIPClient
        from serial_handler import SerialHandler
        from nmea_parser import NMEAParser
        from location_publisher import LocationPublisher
        
        # 初始化组件
        self.ntrip_client = NTRIPClient(config.ntrip)
        self.serial_handler = SerialHandler(config.serial)
        self.nmea_parser = NMEAParser()
        self.location_publisher = LocationPublisher(config.output)
        self.parser = self.nmea_parser  # 别名，向后兼容
        self.publisher = self.location_publisher  # 别名，向后兼容
        
        # 状态
        self.running = False
        self.last_gga_time = 0
        self.last_location: Optional[LocationData] = None
        
        # 双线程
        self._rtcm_thread: Optional[threading.Thread] = None
        self._nmea_thread: Optional[threading.Thread] = None
        
        # 线程锁保护共享数据
        self._location_lock = threading.Lock()
        
        # 回调
        self.location_callback: Optional[Callable[[LocationData], None]] = None
    
    def set_location_callback(self, callback: Callable[[LocationData], None]):
        """设置位置数据回调"""
        self.location_callback = callback
    
    def start(self, background=True) -> bool:
        """启动工作器 - 双线程版本"""
        try:
            self.logger.info("Starting GNSS Worker...")
            
            # 1. 连接NTRIP服务器
            if not self.ntrip_client.connect():
                self.logger.error("Failed to connect to NTRIP server")
                return False
            
            # 2. 打开串口
            if not self.serial_handler.open():
                self.logger.error("Failed to open serial port")
                return False
            
            self.running = True
            
            # 3. 启动双线程
            if background:
                self._rtcm_thread = threading.Thread(target=self._rtcm_worker, daemon=True)
                self._nmea_thread = threading.Thread(target=self._nmea_worker, daemon=True)
                self._rtcm_thread.start()
                self._nmea_thread.start()
                self.logger.info("Started dual-threaded background workers")
            else:
                # 如果不是后台模式，使用单线程run方法兼容性
                self.logger.info("Running in foreground single-threaded mode")
            
            self.logger.info("GNSS Worker started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start GNSS Worker: {e}")
            return False
    
    def stop(self):
        """停止工作器"""
        self.logger.info("Stopping GNSS Worker...")
        self.running = False
        
        # 等待工作线程结束
        if self._rtcm_thread and self._rtcm_thread.is_alive():
            self._rtcm_thread.join(timeout=5)
        
        if self._nmea_thread and self._nmea_thread.is_alive():
            self._nmea_thread.join(timeout=5)
        
        if hasattr(self, 'ntrip_client'):
            self.ntrip_client.disconnect()
        
        if hasattr(self, 'serial_handler'):
            self.serial_handler.close()
        
        self.logger.info("GNSS Worker stopped")
    
    def run_once(self) -> bool:
        """运行一次循环 - 低功耗设计"""
        if not self.running:
            return False
        
        try:
            # 1. 发送心跳GGA（每30秒）
            current_time = time.time()
            if current_time - self.last_gga_time >= 30:
                if self.last_location:
                    gga_line = self._generate_gga(self.last_location)
                    self.ntrip_client.send_gga(gga_line)
                    self.last_gga_time = current_time
            
            # 2. 接收RTCM数据并转发
            rtcm_data = self.ntrip_client.receive_rtcm(timeout=1.0)
            if rtcm_data:
                self.serial_handler.write_rtcm(rtcm_data)
            
            # 3. 读取NMEA数据并解析
            nmea_line = self.serial_handler.read_nmea(timeout=1.0)
            if nmea_line:
                location = self.nmea_parser.parse(nmea_line)
                if location:
                    self.last_location = location
                    
                    # 发布位置数据
                    self.location_publisher.publish(location)
                    
                    # 调用回调
                    if self.location_callback:
                        self.location_callback(location)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in run loop: {e}")
            return False
    
    def _rtcm_worker(self):
        """RTCM数据处理线程：NTRIP → 串口"""
        self.logger.info("RTCM worker thread started")
        while self.running:
            try:
                # 定时发送GGA心跳
                current_time = time.time()
                if current_time - self.last_gga_time >= 30:
                    # 使用锁保护 last_location 读取
                    with self._location_lock:
                        current_location = self.last_location
                    
                    if current_location:
                        gga_line = self._generate_gga(current_location)
                        self.ntrip_client.send_gga(gga_line)
                        self.last_gga_time = current_time
                
                # 接收并转发RTCM数据
                rtcm_data = self.ntrip_client.receive_rtcm(timeout=1.0)
                if rtcm_data:
                    self.serial_handler.write_rtcm(rtcm_data)
                
                # 短暂休眠避免CPU占用过高
                time.sleep(0.1)
                    
            except Exception as e:
                self.logger.error(f"RTCM worker error: {e}")
                time.sleep(1)
        
        self.logger.info("RTCM worker thread stopped")

    def _nmea_worker(self):
        """NMEA数据处理线程：串口 → JSON"""
        self.logger.info("NMEA worker thread started")
        while self.running:
            try:
                # 读取并处理NMEA数据
                nmea_line = self.serial_handler.read_nmea(timeout=1.0)
                if nmea_line:
                    location = self.nmea_parser.parse(nmea_line)
                    if location:
                        # 使用锁保护 last_location 更新
                        with self._location_lock:
                            self.last_location = location
                        
                        # 发布位置数据
                        self.location_publisher.publish(location)
                        
                        # 调用回调
                        if self.location_callback:
                            self.location_callback(location)
                
                # 短暂休眠避免CPU占用过高
                time.sleep(0.1)
                            
            except Exception as e:
                self.logger.error(f"NMEA worker error: {e}")
                time.sleep(1)
        
        self.logger.info("NMEA worker thread stopped")
    
    def run(self):
        """主运行循环 - 兼容性方法（推荐使用双线程模式）"""
        self.logger.warning("Running in legacy single-threaded mode. Consider using background=True for better performance.")
        while self.running:
            if not self.run_once():
                # 出错时短暂休眠再重试
                time.sleep(1)
            else:
                # 正常时短暂休眠节省CPU
                time.sleep(0.1)
    
    def _generate_gga(self, location: LocationData) -> str:
        """根据当前位置生成GGA语句"""
        # 简化实现，使用固定格式
        lat_deg = int(location.latitude)
        lat_min = (location.latitude - lat_deg) * 60
        lat_str = f"{lat_deg:02d}{lat_min:08.5f}"
        lat_dir = "N" if location.latitude >= 0 else "S"
        
        lon_deg = int(abs(location.longitude))
        lon_min = (abs(location.longitude) - lon_deg) * 60
        lon_str = f"{lon_deg:03d}{lon_min:08.5f}"
        lon_dir = "E" if location.longitude >= 0 else "W"
        
        # 生成时间戳
        current_time = time.time()
        time_struct = time.gmtime(current_time)
        time_str = f"{time_struct.tm_hour:02d}{time_struct.tm_min:02d}{time_struct.tm_sec:02d}.000"
        
        gga_line = (f"$GNGGA,{time_str},{lat_str},{lat_dir},{lon_str},{lon_dir},"
                   f"{location.quality},{location.satellites:02d},"
                   f"{location.hdop:.2f},{location.altitude:.1f},M,-3.6,M,,")
        
        # 计算校验和
        checksum = 0
        for char in gga_line[1:]:  # 跳过$
            checksum ^= ord(char)
        
        return f"{gga_line}*{checksum:02X}\r\n"
    
    def get_status(self) -> dict:
        """获取当前状态"""
        return {
            'running': self.running,
            'ntrip_connected': getattr(self.ntrip_client, 'connected', False),
            'serial_open': getattr(self.serial_handler, 'is_open', False),
            'rtcm_thread_alive': self._rtcm_thread.is_alive() if self._rtcm_thread else False,
            'nmea_thread_alive': self._nmea_thread.is_alive() if self._nmea_thread else False,
            'last_location': self.last_location
        }
