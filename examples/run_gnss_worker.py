"""
RTK GNSS Worker 使用示例
演示如何使用统一配置运行RTK GNSS Worker
"""

import sys
import time
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from gnss_worker import GNSSWorker
from config import Config

def main():
    """使用统一配置运行RTK GNSS Worker"""
    
    # 方式1: 使用配置文件
    config_path = Path(__file__).parent.parent / 'config.json'
    if config_path.exists():
        print(f"使用配置文件: {config_path}")
        config = Config.from_file(str(config_path))
    else:
        print("配置文件不存在，使用默认配置")
        config = Config.default()
    
    # 验证配置
    if not config.validate():
        print("❌ 配置验证失败")
        return
    
    print("✅ 配置验证通过")
    print(f"NTRIP服务器: {config.ntrip.get('server')}:{config.ntrip.get('port')}")
    print(f"挂载点: {config.ntrip.get('mountpoint')}")
    print(f"输出文件: {config.output.get('file_path')}")
    
    # 创建GNSS Worker实例
    worker = GNSSWorker(config)

    try:
        print("🚀 启动RTK GNSS Worker...")
        worker.start()
        
        print("📡 开始位置数据监控...")
        print("按 Ctrl+C 停止")
        
        # 监控输出文件变化
        output_file = config.output.get('file_path')
        last_mtime = 0
        
        while True:
            # 检查输出文件是否更新
            if os.path.exists(output_file):
                mtime = os.path.getmtime(output_file)
                if mtime > last_mtime:
                    last_mtime = mtime
                    try:
                        import json
                        with open(output_file, 'r') as f:
                            location_data = json.load(f)
                        
                        print(f"📍 最新位置: "
                              f"纬度={location_data.get('latitude', 'N/A'):.6f}, "
                              f"经度={location_data.get('longitude', 'N/A'):.6f}, "
                              f"质量={location_data.get('quality', 'N/A')}, "
                              f"卫星数={location_data.get('satellites', 'N/A')}")
                              
                    except (json.JSONDecodeError, FileNotFoundError) as e:
                        print(f"⚠️  读取位置数据失败: {e}")
            
            time.sleep(2)  # 每2秒检查一次
            
    except KeyboardInterrupt:
        print("\n🛑 收到停止信号...")
    except Exception as e:
        print(f"❌ 运行错误: {e}")
    finally:
        print("🔄 正在停止RTK GNSS Worker...")
        worker.stop()
        print("✅ RTK GNSS Worker已停止")

def main_with_env():
    """使用环境变量配置运行"""
    print("使用环境变量配置")
    
    # 设置配置文件路径到环境变量
    config_path = Path(__file__).parent.parent / 'config.json'
    os.environ['GNSS_CONFIG_FILE'] = str(config_path)
    
    config = Config.from_env()
    
    if not config.validate():
        print("❌ 环境变量配置验证失败")
        return
    
    worker = GNSSWorker(config)
    
    try:
        print("🚀 启动RTK GNSS Worker (环境变量配置)...")
        worker.start()
        
        # 简单运行10秒
        for i in range(10):
            print(f"⏱️  运行中... {i+1}/10")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 收到停止信号...")
    finally:
        worker.stop()
        print("✅ RTK GNSS Worker已停止")
        # 清理环境变量
        if 'GNSS_CONFIG_FILE' in os.environ:
            del os.environ['GNSS_CONFIG_FILE']

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='RTK GNSS Worker 使用示例')
    parser.add_argument('--env', action='store_true', help='使用环境变量配置模式')
    
    args = parser.parse_args()
    
    if args.env:
        main_with_env()
    else:
        main()