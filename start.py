#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTK GNSS Worker 启动脚本
简化版本，便于在外部环境运行
"""

import sys
import os
import logging
import signal
import argparse
import json

# 添加src目录到Python路径
src_dir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_dir)

# 现在可以导入模块
from gnss_worker import GNSSWorker
from config import Config


def setup_logging(level_str: str, log_file: str = None):
    """设置日志"""
    level = getattr(logging, level_str.upper(), logging.INFO)
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(level=level, format=log_format, handlers=handlers)


def create_default_config():
    """创建默认配置（用于快速测试）"""
    return {
        'ntrip': {
            'server': '220.180.239.212',
            'port': 7990,
            'username': 'QL_NTRIP',
            'password': '123456',
            'mountpoint': 'AUTO',
            'timeout': 30
        },
        'serial': {
            'port': '/dev/ttyUSB0',  # Linux/Mac
            'baudrate': 115200,
            'timeout': 1.0
        },
        'output': {
            'type': 'file',
            'file_path': './gnss_location.json',
            'atomic_write': True,
            'update_interval': 1.0
        },
        'logging': {
            'level': 'INFO'
        }
    }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='RTK GNSS Worker')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='日志级别')
    parser.add_argument('--log-file', help='日志文件路径')
    parser.add_argument('--port', help='串口设备路径 (覆盖配置文件)')
    parser.add_argument('--default-config', action='store_true',
                       help='使用默认配置（忽略配置文件）')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    try:
        # 加载配置
        if args.default_config:
            logger.info("使用默认配置")
            config_data = create_default_config()
            config = Config(config_data)
        elif args.config:
            logger.info(f"从文件加载配置: {args.config}")
            config = Config.from_file(args.config)
        else:
            # 尝试当前目录的config.json
            if os.path.exists('config.json'):
                logger.info("从 config.json 加载配置")
                config = Config.from_file('config.json')
            else:
                logger.info("未找到配置文件，使用默认配置")
                config_data = create_default_config()
                config = Config(config_data)
        
        # 命令行参数覆盖
        if args.port:
            logger.info(f"使用命令行指定的串口: {args.port}")
            config.serial['port'] = args.port
        
        # 验证配置
        if not config.validate():
            logger.error("配置验证失败")
            sys.exit(1)
        
        logger.info("配置验证通过")
        logger.info(f"NTRIP服务器: {config.ntrip['server']}:{config.ntrip['port']}")
        logger.info(f"串口设备: {config.serial['port']}")
        logger.info(f"输出文件: {config.output.get('file_path', 'N/A')}")
        
        # 创建GNSS Worker
        worker = GNSSWorker(config)
        
        # 设置信号处理
        def signal_handler(signum, frame):
            logger.info(f"接收到信号 {signum}，正在停止...")
            worker.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)
        
        # 启动
        logger.info("启动RTK GNSS Worker...")
        success = worker.start()
        
        if not success:
            logger.error("启动失败")
            sys.exit(1)
        
        logger.info("✅ RTK GNSS Worker 已启动")
        logger.info("按 Ctrl+C 停止程序")
        
        # 主循环 - 显示状态
        import time
        status_interval = 30  # 每30秒显示一次状态
        last_status_time = 0
        
        while worker.running:
            time.sleep(1)
            
            # 定期显示状态
            current_time = time.time()
            if current_time - last_status_time > status_interval:
                status = worker.get_status()
                logger.info(f"📊 状态更新: NTRIP={status.get('ntrip_connected', False)}, "
                          f"串口={status.get('serial_open', False)}, "
                          f"运行中={status.get('running', False)}")
                last_status_time = current_time
            
    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"运行时错误: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("程序结束")


if __name__ == '__main__':
    print("🛰️  RTK GNSS Worker 启动器")
    print("=" * 50)
    main()
