"""
位置发布器 - 简化版本
"""

import json
import time
from logger import get_logger
import os
from typing import Any, Dict

class LocationPublisher:
    """简化的位置发布器"""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger()
        self.output_type = getattr(config, 'type', 'file')
        self.update_interval = config.get('update_interval', 1.0)  # 默认1秒更新一次
        self.last_publish_time = 0
        
    def publish(self, location) -> bool:
        """发布位置数据"""
        try:
            # 检查发布间隔
            current_time = time.time()
            if current_time - self.last_publish_time < self.update_interval:
                return True  # 跳过本次发布，但返回成功
            
            self.last_publish_time = current_time
            
            if self.output_type == 'file':
                self.logger.info(f"📍 发布位置数据 (质量:{getattr(location, 'quality', 'N/A')}, 卫星:{getattr(location, 'satellites', 'N/A')})")
                return self._publish_to_file(location)
            elif self.output_type == 'callback':
                self.logger.info(f"📍 通过回调发布位置数据")
                return self._publish_to_callback(location)
            else:
                self.logger.warning(f"Unknown output type: {self.output_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to publish location: {e}")
            return False
    
    def _publish_to_file(self, location) -> bool:
        """发布到文件"""
        file_path = self.config.get('file_path', '/tmp/gnss_location.json')
        atomic_write = self.config.get('atomic_write', True)
        
        # 构建数据 - 兼容字典和对象两种格式
        if isinstance(location, dict):
            data = location
        else:
            data = {
                'timestamp': location.timestamp,
                'latitude': location.latitude,
                'longitude': location.longitude,
                'altitude': location.altitude,
                'quality': location.quality,
                'satellites': location.satellites,
                'hdop': location.hdop,
                'raw_nmea': getattr(location, 'raw_nmea', '')
            }
        
        json_data = json.dumps(data, indent=2)
        
        if atomic_write:
            return self._atomic_write(file_path, json_data)
        else:
            return self._direct_write(file_path, json_data)
    
    def _atomic_write(self, file_path: str, data: str) -> bool:
        """原子写入文件"""
        temp_path = f"{file_path}.tmp"
        
        try:
            # 写入临时文件
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())  # 确保写入磁盘
            
            # Windows系统需要特殊处理
            if os.name == 'nt':  # Windows
                # 如果目标文件存在，先删除
                if os.path.exists(file_path):
                    os.unlink(file_path)
            
            # 原子性重命名
            os.rename(temp_path, file_path)
            return True
            
        except Exception as e:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e
    
    def _direct_write(self, file_path: str, data: str) -> bool:
        """直接写入文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(data)
            return True
        except Exception as e:
            self.logger.error(f"Direct write failed: {e}")
            return False
    
    def _publish_to_callback(self, location) -> bool:
        """发布到回调函数"""
        callback = self.config.get('callback')
        if callback and callable(callback):
            try:
                callback(location)
                return True
            except Exception as e:
                self.logger.error(f"Callback failed: {e}")
                return False
        else:
            self.logger.error("No valid callback provided")
            return False


class FileLocationPublisher(LocationPublisher):
    """文件位置发布器 - 为了向后兼容性"""
    
    def __init__(self, config):
        super().__init__(config)
        # 确保使用文件输出类型
        self.config['type'] = 'file'
