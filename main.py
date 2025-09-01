#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTK GNSS Worker 主程序入口
简化版本，用于tar包部署
"""

import sys
import os
import signal
import argparse
from pathlib import Path

# 添加src目录到Python路径
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

try:
    from config import Config
    from logger import get_logger, setup_logging_from_config
    from gnss_worker import GNSSWorker
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保在正确的目录下运行，或检查src目录是否存在")
    sys.exit(1)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='RTK GNSS Worker')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='日志级别')
    parser.add_argument('--log-file', help='日志文件路径')
    
    args = parser.parse_args()
    try:
        # 加载配置
        if args.config:
            logger.info(f"从文件加载配置: {args.config}")
            config = Config.from_file(args.config)
        else:
            logger.info("从环境变量加载配置")
            config = Config.from_env()
        
        # 验证配置
        if not config.validate():
            logger.error("配置验证失败")
            sys.exit(1)
        
        # 创建GNSS Worker
        worker = GNSSWorker(config)
        
        # 设置信号处理
        def signal_handler(signum, frame):
            logger.info(f"接收到信号 {signum}，正在停止...")
            worker.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 启动
        logger.info("启动RTK GNSS Worker...")
        worker.start()
        
        # 等待结束
        while worker.running:
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"运行时错误: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("程序结束")


if __name__ == '__main__':
    main()
