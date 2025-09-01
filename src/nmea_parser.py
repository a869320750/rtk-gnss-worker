"""
简化的NMEA解析器
"""

import re
import time
from logger import get_logger
from typing import Optional
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

class NMEAParser:
    """简化的NMEA解析器"""
    
    def __init__(self):
        self.logger = get_logger()
    
    def parse(self, nmea_line: str) -> Optional[LocationData]:
        """解析NMEA语句"""
        if not nmea_line or not nmea_line.startswith('$'):
            return None
        
        # 验证校验和
        if not self._validate_checksum(nmea_line):
            self.logger.warning(f"Invalid NMEA checksum: {nmea_line}")
            return None
        
        try:
            # 分割字段
            parts = nmea_line.split(',')
            if len(parts) < 6:
                return None
            
            sentence_type = parts[0][3:]  # 去掉$GP/$GN前缀
            
            if sentence_type == 'GGA':
                return self._parse_gga(parts)
            elif sentence_type == 'RMC':
                return self._parse_rmc(parts)
        except Exception as e:
            self.logger.error(f"NMEA parsing error: {e}")
        
        return None
    
    def parse_gga(self, nmea_line: str) -> Optional[dict]:
        """解析GGA语句 - 向后兼容接口"""
        result = self.parse(nmea_line)
        if result:
            return {
                'latitude': result.latitude,
                'longitude': result.longitude,
                'altitude': result.altitude,
                'quality': result.quality,
                'satellites': result.satellites,
                'hdop': result.hdop,
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(result.timestamp))
            }
        return None
    
    def _parse_gga(self, fields) -> Optional[LocationData]:
        """解析GGA语句"""
        try:
            if len(fields) < 15:
                return None
            
            # 纬度
            lat_str = fields[2]
            lat_dir = fields[3]
            latitude = self._parse_coordinate(lat_str, lat_dir)
            
            # 经度
            lon_str = fields[4]
            lon_dir = fields[5]
            longitude = self._parse_coordinate(lon_str, lon_dir)
            
            # 其他字段
            quality = int(fields[6]) if fields[6] else 0
            satellites = int(fields[7]) if fields[7] else 0
            hdop = float(fields[8]) if fields[8] else 0.0
            altitude = float(fields[9]) if fields[9] else 0.0
            
            return LocationData(
                timestamp=time.time(),
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                quality=quality,
                satellites=satellites,
                hdop=hdop,
                raw_nmea=','.join(fields)
            )
            
        except (ValueError, IndexError):
            return None
    
    def _parse_rmc(self, fields) -> Optional[LocationData]:
        """解析RMC语句"""
        try:
            if len(fields) < 12:
                return None
            
            # 检查数据有效性
            if fields[2] != 'A':  # A表示有效数据
                return None
            
            # 纬度
            lat_str = fields[3]
            lat_dir = fields[4]
            latitude = self._parse_coordinate(lat_str, lat_dir)
            
            # 经度
            lon_str = fields[5]
            lon_dir = fields[6]
            longitude = self._parse_coordinate(lon_str, lon_dir)
            
            return LocationData(
                timestamp=time.time(),
                latitude=latitude,
                longitude=longitude,
                altitude=0.0,  # RMC不包含高度信息
                quality=1,     # 假设有效
                satellites=0,  # RMC不包含卫星数
                hdop=0.0,      # RMC不包含HDOP
                raw_nmea=','.join(fields)
            )
            
        except (ValueError, IndexError):
            return None
    
    def _parse_coordinate(self, coord_str: str, direction: str) -> float:
        """解析坐标字符串"""
        if not coord_str:
            return 0.0
        
        try:
            # DDMM.MMMM格式
            if len(coord_str) >= 7:
                if '.' in coord_str:
                    dot_pos = coord_str.index('.')
                    degrees = float(coord_str[:dot_pos-2])
                    minutes = float(coord_str[dot_pos-2:])
                else:
                    degrees = float(coord_str[:-5])
                    minutes = float(coord_str[-5:]) / 100
                
                decimal_degrees = degrees + minutes / 60.0
                
                # 应用方向
                if direction in ['S', 'W']:
                    decimal_degrees = -decimal_degrees
                
                return decimal_degrees
            
        except (ValueError, IndexError):
            pass
        
        return 0.0
    
    def _validate_checksum(self, nmea_line: str) -> bool:
        """验证NMEA校验和"""
        if '*' not in nmea_line:
            return False
        
        try:
            message, checksum_str = nmea_line.rsplit('*', 1)
            expected_checksum = int(checksum_str, 16)
            
            calculated_checksum = 0
            for char in message[1:]:  # 跳过开头的$
                calculated_checksum ^= ord(char)
            
            return calculated_checksum == expected_checksum
            
        except (ValueError, IndexError):
            return False
