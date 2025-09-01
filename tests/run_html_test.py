#!/usr/bin/env python3
"""
RTK GNSS Worker HTML测试运行器
"""

import sys
import os
import argparse
from pathlib import Path

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.dirname(__file__))

from html_reporter import HTMLTestReporter


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='RTK GNSS Worker HTML测试报告生成器')
    parser.add_argument('--type', choices=['all', 'unit', 'integration', 'real-integration', 'system', 'architecture'], 
                        default='all', help='测试类型')
    parser.add_argument('--output-dir', default='reports', help='报告输出目录')
    
    args = parser.parse_args()
    
    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # 创建HTML报告器
    reporter = HTMLTestReporter(output_dir=args.output_dir)
    
    # 开始测试会话
    reporter.start_test_session(args.type)
    
    # 定义测试命令
    test_commands = {
        'unit': [
            ('单元测试', 'python -m pytest tests/unit/ -v --tb=short')
        ],
        'integration': [
            ('集成测试', 'python -m pytest tests/integration/ -v --tb=short')
        ],
        'real-integration': [
            ('真实集成测试', 'python -m pytest tests/real/ -v --tb=short')  
        ],
        'system': [
            ('系统测试', 'python -m pytest tests/system/ -v --tb=short')
        ],
        'architecture': [
            ('架构测试', 'python -m pytest tests/architecture/ -v --tb=short')
        ],
        'all': [
            ('单元测试', 'python -m pytest tests/unit/ -v --tb=short'),
            ('集成测试', 'python -m pytest tests/integration/ -v --tb=short'),
            ('真实集成测试', 'python -m pytest tests/real/ -v --tb=short'),
            ('系统测试', 'python -m pytest tests/system/ -v --tb=short'),
            ('架构测试', 'python -m pytest tests/architecture/ -v --tb=short')
        ]
    }
    
    # 执行测试
    commands = test_commands.get(args.type, test_commands['all'])
    
    for test_name, command in commands:
        reporter.run_command_with_logging(command, test_name)
    
    # 结束测试会话
    overall_success = reporter.end_test_session()
    
    # 生成HTML报告
    report_path = reporter.generate_html_report()
    
    print(f"\n🌐 在浏览器中打开以查看详细报告: {report_path}")
    
    # 尝试自动打开浏览器（可选）
    try:
        import webbrowser
        webbrowser.open(f'file://{report_path.absolute()}')
        print("🌐 已在默认浏览器中打开报告")
    except Exception as e:
        print(f"💡 无法自动打开浏览器: {e}")
        print(f"💡 请手动在浏览器中打开: {report_path.absolute()}")
    
    return 0 if overall_success else 1


if __name__ == '__main__':
    sys.exit(main())
