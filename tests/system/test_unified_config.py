#!/usr/bin/env python3
"""
测试统一配置的RTK GNSS Worker
"""

import sys
import os
import logging
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Config

def test_unified_config():
    """测试使用uavcli_ird项目的统一配置文件"""
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # 使用项目根目录的配置文件
    config_file = Path(__file__).parent.parent / 'config.json'
    
    logger.info(f"尝试从配置文件加载: {config_file}")
    
    try:
        # 测试从文件加载配置
        if config_file.exists():
            config = Config.from_file(str(config_file))
            logger.info("成功从统一配置文件加载RTK配置")
        else:
            logger.warning(f"配置文件不存在: {config_file}")
            config = Config.default()
            logger.info("使用默认配置")
        
        # 验证配置
        if config.validate():
            logger.info("配置验证通过")
        else:
            logger.error("配置验证失败")
            return False
        
        # 打印配置信息
        logger.info("=== RTK配置信息 ===")
        logger.info(f"NTRIP服务器: {config.ntrip.get('server')}:{config.ntrip.get('port')}")
        logger.info(f"NTRIP用户: {config.ntrip.get('username')}")
        logger.info(f"NTRIP挂载点: {config.ntrip.get('mountpoint')}")
        logger.info(f"串口配置: {config.serial}")
        logger.info(f"输出配置: {config.output}")
        logger.info(f"日志配置: {config.logging}")
        logger.info(f"定位配置: {config.positioning}")
        
        return True
        
    except Exception as e:
        logger.error(f"配置测试失败: {e}")
        return False

def test_env_config():
    """测试环境变量配置"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # 设置配置文件路径到环境变量
    config_file = Path(__file__).parent.parent / 'config.json'
    os.environ['GNSS_CONFIG_FILE'] = str(config_file)
    
    try:
        # 通过环境变量加载配置
        config = Config.from_env()
        logger.info("成功通过环境变量加载统一配置")
        
        # 验证配置
        if config.validate():
            logger.info("环境变量配置验证通过")
            return True
        else:
            logger.error("环境变量配置验证失败")
            return False
            
    except Exception as e:
        logger.error(f"环境变量配置测试失败: {e}")
        return False
    finally:
        # 清理环境变量
        if 'GNSS_CONFIG_FILE' in os.environ:
            del os.environ['GNSS_CONFIG_FILE']

if __name__ == '__main__':
    print("=== 测试统一配置文件加载 ===")
    result1 = test_unified_config()
    
    print("\n=== 测试环境变量配置文件加载 ===")
    result2 = test_env_config()
    
    if result1 and result2:
        print("\n✅ 所有配置测试通过")
        sys.exit(0)
    else:
        print("\n❌ 配置测试失败")
        sys.exit(1)
