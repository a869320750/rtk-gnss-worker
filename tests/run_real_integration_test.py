#!/usr/bin/env python3
"""
专门运行真实端到端集成测试的Python脚本
"""

import subprocess
import time
import sys
import os
from typing import Dict, Any
import logging

# 设置彩色日志
class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[0;36m',     # Cyan
        'INFO': '\033[0;34m',      # Blue
        'WARNING': '\033[1;33m',   # Yellow
        'ERROR': '\033[0;31m',     # Red
        'CRITICAL': '\033[1;31m',  # Bold Red
        'SUCCESS': '\033[0;32m',   # Green
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}[{record.levelname}]{self.RESET}"
        return super().format(record)

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 添加SUCCESS级别
SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, 'SUCCESS')

def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL):
        self._log(SUCCESS_LEVEL, message, args, **kwargs)

logging.Logger.success = success

handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter('%(levelname)s %(message)s'))
logger.addHandler(handler)

class MockServiceManager:
    """Mock服务管理器"""
    
    def __init__(self, compose_file: str = "tests/docker-compose.unified.yml", rebuild: bool = False):
        self.compose_file = compose_file
        self.services = ["ntrip-mock", "serial-mock"]
        self.rebuild = rebuild
    
    def _run_command(self, cmd: list, check: bool = True) -> subprocess.CompletedProcess:
        """运行命令"""
        logger.debug(f"运行命令: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=check, encoding='utf-8', errors='ignore')
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"命令执行失败: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            raise
    
    def cleanup(self):
        """清理所有服务"""
        logger.info("清理测试资源...")
        cmd = ["docker-compose", "-f", self.compose_file, "down"]
        self._run_command(cmd, check=False)
        logger.success("清理完成")
    
    def build_if_needed(self):
        """构建镜像（如果需要）"""
        if self.rebuild:
            logger.info("强制重新构建Docker镜像...")
            cmd = ["docker-compose", "-f", self.compose_file, "build", "--no-cache", "rtk-base"]
            self._run_command(cmd)
            logger.success("镜像重建完成")
        else:
            # 检查镜像是否存在
            result = self._run_command(["docker", "images", "-q", "rtk-gnss-worker"], check=False)
            if not result.stdout.strip():
                logger.info("构建Docker镜像...")
                cmd = ["docker-compose", "-f", self.compose_file, "build", "rtk-base"]
                self._run_command(cmd)
                logger.success("镜像构建完成")
            else:
                logger.info("使用已有镜像（如需重建，请使用 --rebuild 参数）")
    
    def start_mock_services(self) -> bool:
        """启动Mock服务"""
        logger.info("启动Mock服务...")
        
        # 清理可能存在的服务
        self.cleanup()
        
        # 启动mock服务
        cmd = ["docker-compose", "-f", self.compose_file, "up", "-d"] + self.services
        try:
            self._run_command(cmd)
        except subprocess.CalledProcessError:
            logger.error("启动Mock服务失败")
            return False
        
        return self._wait_for_health_checks()
    
    def _wait_for_health_checks(self, timeout: int = 60) -> bool:
        """等待健康检查通过"""
        logger.info("等待Mock服务健康检查通过...")
        
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                logger.error("Mock服务健康检查超时")
                self._show_service_logs()
                return False
            
            # 检查服务健康状态
            healthy_count = 0
            for service in self.services:
                result = self._run_command(
                    ["docker-compose", "-f", self.compose_file, "ps", service],
                    check=False
                )
                if result.stdout and "healthy" in result.stdout:
                    healthy_count += 1
            
            if healthy_count == len(self.services):
                logger.success("所有Mock服务健康检查通过")
                self._show_service_status()
                return True
            
            print(f"⏳ 等待健康检查... ({elapsed:.1f}s)")
            time.sleep(3)
    
    def _show_service_status(self):
        """显示服务状态"""
        logger.info("Mock服务状态:")
        cmd = ["docker-compose", "-f", self.compose_file, "ps"] + self.services
        result = self._run_command(cmd, check=False)
        print(result.stdout)
    
    def _show_service_logs(self):
        """显示服务日志"""
        for service in self.services:
            logger.info(f"{service}日志:")
            cmd = ["docker-compose", "-f", self.compose_file, "logs", service]
            result = self._run_command(cmd, check=False)
            print(result.stdout)
    
    def run_real_integration_test(self) -> bool:
        """运行真实集成测试"""
        logger.info("运行真实端到端集成测试...")
        
        cmd = ["docker-compose", "-f", self.compose_file, "run", "--rm", "test-real-integration"]
        result = self._run_command(cmd, check=False)
        
        if result.returncode == 0:
            logger.success("真实集成测试通过")
            return True
        else:
            logger.error("真实集成测试失败")
            # 显示服务日志以便调试
            self._show_service_logs()
            return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RTK GNSS Worker 真实端到端集成测试')
    parser.add_argument('--rebuild', action='store_true', help='强制重新构建Docker镜像')
    args = parser.parse_args()
    
    print("🧪 RTK GNSS Worker 真实端到端集成测试")
    print("=" * 60)
    
    # 切换到项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    manager = MockServiceManager(rebuild=args.rebuild)
    
    try:
        # 构建镜像（如果需要）
        manager.build_if_needed()
        
        # 启动并等待mock服务
        if not manager.start_mock_services():
            logger.error("Mock服务启动失败")
            return 1
        
        # 运行真实集成测试
        if not manager.run_real_integration_test():
            logger.error("真实集成测试失败")
            return 1
        
        logger.success("所有真实集成测试通过！")
        return 0
        
    except KeyboardInterrupt:
        logger.warning("用户中断测试")
        return 1
    except Exception as e:
        logger.error(f"测试执行出错: {e}")
        return 1
    finally:
        manager.cleanup()

if __name__ == "__main__":
    sys.exit(main())
