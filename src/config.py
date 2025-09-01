"""
简化的配置管理
"""

import json
import os
from logger import get_logger
from typing import Dict, Any, Optional

class Config:
    """简化的配置管理器"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self.data = config_dict
        self.logger = get_logger(__name__)
    
    @classmethod
    def from_file(cls, file_path: str) -> 'Config':
        """从文件加载配置"""
        logger = get_logger("config")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            logger.info(f"成功加载配置文件: {file_path}")
            
            # 如果配置文件有rtk节，使用RTK配置；否则使用整个配置
            if 'rtk' in config_data:
                return cls(config_data['rtk'])
            else:
                return cls(config_data)
                
        except Exception as e:
            logger.error(f"Failed to load config from {file_path}: {e}")
            raise
    
    @classmethod
    def from_env(cls, prefix: str = 'GNSS_') -> 'Config':
        """从环境变量加载配置"""
        
        # 首先尝试从环境变量获取配置文件路径
        config_file = os.getenv(f'{prefix}CONFIG_FILE')
        if config_file and os.path.exists(config_file):
            return cls.from_file(config_file)
        
        # 串口配置：根据是否有host判断TCP还是串口模式
        serial_config = {}
        serial_host = os.getenv(f'{prefix}SERIAL_HOST')
        
        if serial_host:
            # TCP模式
            serial_config = {
                'host': serial_host,
                'port': int(os.getenv(f'{prefix}SERIAL_PORT', '8888')),
                'timeout': float(os.getenv(f'{prefix}SERIAL_TIMEOUT', '1.0'))
            }
        else:
            # 串口模式
            serial_config = {
                'port': os.getenv(f'{prefix}SERIAL_PORT', '/dev/ttyUSB0'),
                'baudrate': int(os.getenv(f'{prefix}SERIAL_BAUDRATE', '115200')),
                'timeout': float(os.getenv(f'{prefix}SERIAL_TIMEOUT', '1.0'))
            }
        
        config_data = {
            'ntrip': {
                'server': os.getenv(f'{prefix}NTRIP_SERVER', 'localhost'),
                'port': int(os.getenv(f'{prefix}NTRIP_PORT', '7990')),
                'username': os.getenv(f'{prefix}NTRIP_USERNAME', 'test'),
                'password': os.getenv(f'{prefix}NTRIP_PASSWORD', 'test'),
                'mountpoint': os.getenv(f'{prefix}NTRIP_MOUNTPOINT', 'TEST'),
                'timeout': float(os.getenv(f'{prefix}NTRIP_TIMEOUT', '30')),
                'reconnect_interval': float(os.getenv(f'{prefix}NTRIP_RECONNECT_INTERVAL', '5')),
                'max_retries': int(os.getenv(f'{prefix}NTRIP_MAX_RETRIES', '3'))
            },
            'serial': serial_config,
            'output': {
                'type': os.getenv(f'{prefix}OUTPUT_TYPE', 'file'),
                'file_path': os.getenv(f'{prefix}OUTPUT_FILE', '/tmp/gnss_location.json'),
                'atomic_write': os.getenv(f'{prefix}ATOMIC_WRITE', 'true').lower() == 'true',
                'update_interval': float(os.getenv(f'{prefix}UPDATE_INTERVAL', '1.0'))
            },
            'logging': {
                'level': os.getenv(f'{prefix}LOG_LEVEL', 'INFO'),
                'file': os.getenv(f'{prefix}LOG_FILE', '/var/log/rtk-gnss-worker.log'),
                'max_size': os.getenv(f'{prefix}LOG_MAX_SIZE', '10MB'),
                'backup_count': int(os.getenv(f'{prefix}LOG_BACKUP_COUNT', '5'))
            },
            'positioning': {
                'min_satellites': int(os.getenv(f'{prefix}MIN_SATELLITES', '4')),
                'min_quality': int(os.getenv(f'{prefix}MIN_QUALITY', '1')),
                'gga_interval': float(os.getenv(f'{prefix}GGA_INTERVAL', '30')),
                'position_timeout': float(os.getenv(f'{prefix}POSITION_TIMEOUT', '60'))
            }
        }
        return cls(config_data)
    
    @classmethod
    def default(cls) -> 'Config':
        """默认配置"""
        config_data = {
            'ntrip': {
                'server': '220.180.239.212',
                'port': 7990,
                'username': 'QL_NTRIP',
                'password': '123456',
                'mountpoint': 'HeFei',
                'timeout': 30.0,
                'reconnect_interval': 5,
                'max_retries': 3
            },
            'serial': {
                'port': '/dev/ttyUSB0',
                'baudrate': 115200,
                'timeout': 1.0,
                'host': None  # 如果设置了host，则使用TCP连接而不是串口
            },
            'output': {
                'type': 'file',
                'file_path': '/tmp/gnss_location.json',
                'atomic_write': True,
                'update_interval': 1.0
            },
            'logging': {
                'level': 'INFO',
                'file': '/var/log/rtk-gnss-worker.log',
                'max_size': '10MB',
                'backup_count': 5
            },
            'positioning': {
                'min_satellites': 4,
                'min_quality': 1,
                'gga_interval': 30,
                'position_timeout': 60
            }
        }
        return cls(config_data)
    
    @property
    def ntrip(self) -> Dict[str, Any]:
        """NTRIP配置"""
        return self.data.get('ntrip', {})
    
    @property
    def serial(self) -> Dict[str, Any]:
        """串口配置"""
        return self.data.get('serial', {})
    
    @property
    def output(self) -> Dict[str, Any]:
        """输出配置"""
        return self.data.get('output', {})
    
    @property
    def logging(self) -> Dict[str, Any]:
        """日志配置"""
        return self.data.get('logging', {})
    
    def get_log_directory(self) -> str:
        """获取日志目录路径"""
        # 从配置中获取日志目录，如果没有则使用默认值
        log_config = self.logging
        log_file = log_config.get('file', '/var/log/rtk-gnss-worker.log')
        
        # 提取目录路径
        import os
        log_dir = os.path.dirname(log_file)
        
        # 如果是相对路径或默认路径，使用项目下的logs目录
        if log_dir in ['', '.', '/var/log']:
            log_dir = 'logs'
        
        return log_dir
    
    def ensure_log_directory(self) -> str:
        """确保日志目录存在，返回实际可用的目录路径"""
        from pathlib import Path
        
        target_dir = self.get_log_directory()
        log_path = Path(target_dir)
        
        try:
            # 检查是否存在同名文件
            if log_path.exists() and log_path.is_file():
                self.logger.warning(f"发现文件 {log_path}，将重命名为 {log_path}.bak")
                log_path.rename(log_path.with_suffix('.bak'))
            
            # 创建目录
            log_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"日志目录已准备就绪: {log_path.absolute()}")
            return str(log_path)
            
        except Exception as e:
            self.logger.warning(f"无法创建日志目录 {target_dir} ({e})，使用当前目录")
            return "."
    
    @property
    def positioning(self) -> Dict[str, Any]:
        """定位配置"""
        return self.data.get('positioning', {})
    
    def validate(self) -> bool:
        """验证配置"""
        errors = []
        
        # 验证NTRIP配置
        ntrip = self.ntrip
        if not ntrip.get('server'):
            errors.append("NTRIP server is required")
        if not ntrip.get('username'):
            errors.append("NTRIP username is required")
        if not ntrip.get('password'):
            errors.append("NTRIP password is required")
        if not ntrip.get('mountpoint'):
            errors.append("NTRIP mountpoint is required")
        
        # 验证串口配置
        serial_config = self.serial
        if not serial_config.get('port') and not serial_config.get('host'):
            errors.append("Serial port or host is required")
        
        if errors:
            for error in errors:
                self.logger.error(f"Config validation error: {error}")
            return False
        
        return True
    
    def copy(self) -> 'Config':
        """复制配置对象"""
        import copy as copy_module
        return Config(copy_module.deepcopy(self.data))
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.data[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """支持字典式设置"""
        self.data[key] = value
    
    def __contains__(self, key: str) -> bool:
        """支持 in 操作符"""
        return key in self.data
    
    def get(self, key: str, default: Any = None) -> Any:
        """类似字典的get方法"""
        return self.data.get(key, default)