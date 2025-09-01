#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的日志管理器
RTK GNSS Worker 项目的日志系统
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict


class RTKLogger:
    """RTK GNSS Worker 统一日志管理器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(RTKLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, log_dir: Optional[str] = None):
        if not self._initialized:
            self._setup_logging(log_dir)
            RTKLogger._initialized = True
    
    def _setup_logging(self, log_dir_override: Optional[str] = None):
        """设置日志系统"""
        # 创建logs目录
        if log_dir_override:
            log_dir = Path(log_dir_override)
        else:
            log_dir = Path("logs")
            
        try:
            # 检查是否存在同名文件
            if log_dir.exists() and log_dir.is_file():
                print(f"警告: 发现文件 {log_dir}，将重命名为 logs.bak")
                log_dir.rename(log_dir.with_suffix('.bak'))
            
            # 创建目录
            log_dir.mkdir(parents=True, exist_ok=True)
            
        except Exception as e:
            print(f"警告: 无法创建logs目录 ({e})，使用当前目录保存日志")
            log_dir = Path(".")
        
        # 配置日志格式
        self.log_format = logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 配置控制台输出格式（带颜色和图标）
        self.console_format = logging.Formatter(
            fmt='%(asctime)s [%(levelname_icon)s] [%(name)s] [%(filename)s:%(funcName)s:%(lineno)d] %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # 创建根logger
        self.root_logger = logging.getLogger('rtk_gnss_worker')
        self.root_logger.setLevel(logging.DEBUG)
        
        # 清除现有handlers
        self.root_logger.handlers.clear()
        
        # 添加控制台handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.addFilter(self._add_level_icons)
        console_handler.setFormatter(self.console_format)
        self.root_logger.addHandler(console_handler)
        
        # 添加文件handler（所有日志）
        today = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"rtk_gnss_{today}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(self.log_format)
        self.root_logger.addHandler(file_handler)
        
        # 添加错误文件handler（仅错误和警告）
        error_file = log_dir / f"rtk_gnss_errors_{today}.log"
        error_handler = logging.FileHandler(error_file, encoding='utf-8')
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(self.log_format)
        self.root_logger.addHandler(error_handler)
        
        # 设置第三方库日志级别
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
    
    def _add_level_icons(self, record):
        """为日志级别添加图标"""
        icons = {
            'DEBUG': '🔍',
            'INFO': '📡',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '💥'
        }
        record.levelname_icon = f"{icons.get(record.levelname, '📝')} {record.levelname}"
        return True
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取指定模块的logger"""
        # 确保name是相对于rtk_gnss_worker的
        if not name.startswith('rtk_gnss_worker'):
            if name.startswith('src.'):
                name = f'rtk_gnss_worker.{name[4:]}'  # 移除src.前缀
            elif '.' not in name:
                name = f'rtk_gnss_worker.{name}'
            else:
                name = f'rtk_gnss_worker.{name}'
        
        logger = logging.getLogger(name)
        
        # 防止重复添加handlers
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
        
        return logger
    
    def set_level(self, level: str):
        """设置日志级别"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level.upper() in level_map:
            self.root_logger.setLevel(level_map[level.upper()])
            # 同时设置控制台handler的级别
            for handler in self.root_logger.handlers:
                if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                    handler.setLevel(level_map[level.upper()])
    
    def set_console_level(self, level: str):
        """单独设置控制台日志级别"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level.upper() in level_map:
            for handler in self.root_logger.handlers:
                if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                    handler.setLevel(level_map[level.upper()])
                    break


# 全局实例
_rtk_logger_instance = None

def get_logger(name: Optional[str] = None, log_dir: Optional[str] = None) -> logging.Logger:
    """
    获取RTK GNSS Worker项目的logger
    
    Args:
        name: 模块名称，如果为None则使用调用者的模块名
        log_dir: 日志目录路径，仅在首次调用时有效
    
    Returns:
        配置好的logger实例
    
    Example:
        # 在模块中使用
        from logger import get_logger
        logger = get_logger(__name__)
        logger.info("这是一条信息")
        
        # 或者自定义名称和日志目录
        logger = get_logger("ntrip_client", "custom_logs")
        logger.error("NTRIP连接失败")
    """
    global _rtk_logger_instance
    
    if _rtk_logger_instance is None:
        _rtk_logger_instance = RTKLogger(log_dir)
    
    if name is None:
        # 尝试从调用栈获取模块名
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    
    return _rtk_logger_instance.get_logger(name)


def set_log_level(level: str):
    """设置全局日志级别"""
    global _rtk_logger_instance
    
    if _rtk_logger_instance is None:
        _rtk_logger_instance = RTKLogger()
    
    _rtk_logger_instance.set_level(level)


def set_console_log_level(level: str):
    """设置控制台日志级别"""
    global _rtk_logger_instance
    
    if _rtk_logger_instance is None:
        _rtk_logger_instance = RTKLogger()
    
    _rtk_logger_instance.set_console_level(level)


# 便捷函数，用于快速记录日志
def log_info(message: str, module: str = "main"):
    """快速记录信息日志"""
    logger = get_logger(module)
    logger.info(message)


def log_error(message: str, module: str = "main", exc_info: bool = False):
    """快速记录错误日志"""
    logger = get_logger(module)
    logger.error(message, exc_info=exc_info)


def log_warning(message: str, module: str = "main"):
    """快速记录警告日志"""
    logger = get_logger(module)
    logger.warning(message)


def log_debug(message: str, module: str = "main"):
    """快速记录调试日志"""
    logger = get_logger(module)
    logger.debug(message)


def setup_logging_from_config(config_dict: Optional[Dict] = None, config_file: Optional[str] = None):
    """
    从配置文件或配置字典设置日志系统
    
    Args:
        config_dict: 配置字典，包含logging节
        config_file: 配置文件路径
    """
    global _rtk_logger_instance
    
    log_dir = "logs"  # 默认日志目录
    
    if config_file:
        try:
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            config_dict = config_data.get('logging', {})
        except Exception as e:
            print(f"警告: 无法读取配置文件 {config_file}: {e}")
    
    if config_dict and 'logging' in config_dict:
        logging_config = config_dict['logging']
        log_file = logging_config.get('file', '/var/log/rtk-gnss-worker.log')
        
        # 提取目录路径
        import os
        log_dir = os.path.dirname(log_file)
        
        # 如果是系统路径，改为项目本地路径
        if log_dir in ['', '.', '/var/log']:
            log_dir = 'logs'
    
    # 重新初始化日志系统
    if _rtk_logger_instance is not None:
        # 清理现有实例
        _rtk_logger_instance = None
        RTKLogger._initialized = False
    
    _rtk_logger_instance = RTKLogger(log_dir)
    return _rtk_logger_instance


if __name__ == "__main__":
    # 测试日志系统
    print("🧪 测试RTK日志系统")
    print("-" * 40)
    
    # 测试不同模块的日志
    ntrip_logger = get_logger("ntrip_client")
    serial_logger = get_logger("serial_handler")
    main_logger = get_logger("main")
    
    # 测试不同级别的日志
    main_logger.debug("这是调试信息")
    main_logger.info("🚀 RTK GNSS Worker 启动")
    ntrip_logger.info("📡 连接NTRIP服务器...")
    serial_logger.info("🔌 打开串口连接...")
    main_logger.warning("⚠️ 这是一个警告")
    main_logger.error("❌ 这是一个错误")
    
    # 测试便捷函数
    log_info("使用便捷函数记录日志", "test")
    log_error("测试错误日志", "test")
    
    print("-" * 40)
    print("✅ 日志测试完成，检查logs目录中的日志文件")
