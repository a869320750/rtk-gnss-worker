"""
Docker容器内测试运行器 - 专注于容器化测试
"""

import unittest
import sys
import os
import subprocess

# 添加源代码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def run_test_modules(test_modules):
    """运行指定的测试模块"""
    suite = unittest.TestSuite()
    
    for module_name in test_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            tests = unittest.TestLoader().loadTestsFromModule(module)
            suite.addTests(tests)
        except ImportError as e:
            print(f"⚠️ Failed to import {module_name}: {e}")
            continue
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_unit_tests():
    """运行单元测试"""
    test_modules = [
        'unit.test_units'
    ]
    
    return run_test_modules(test_modules)


def run_integration_tests():
    """运行集成测试（mock测试和性能测试）"""
    test_modules = [
        'integration.test_integration'
    ]
    
    return run_test_modules(test_modules)


def run_real_integration_tests():
    """运行真正的端到端集成测试"""
    test_modules = [
        'real.test_real_integration'
    ]
    
    return run_test_modules(test_modules)


def run_system_tests():
    """运行系统测试"""
    test_modules = [
        'system.test_nmea_checksum',
        'system.test_serial_fix', 
        'system.test_unified_config',
        'system.test_system_resilience',
        'system.test_system_environment'
    ]
    
    return run_test_modules(test_modules)


def run_architecture_tests():
    """运行架构测试"""
    test_modules = [
        'architecture.test_architecture',
        'architecture.test_dual_thread',
        'architecture.test_architecture_design',
        'architecture.test_architecture_quality'
    ]
    
    return run_test_modules(test_modules)


def run_all_tests():
    """运行所有测试"""
    results = []
    results.append(("Unit Tests", run_unit_tests()))
    results.append(("Integration Tests", run_integration_tests()))
    results.append(("Real Integration Tests", run_real_integration_tests()))
    results.append(("System Tests", run_system_tests()))
    results.append(("Architecture Tests", run_architecture_tests()))
    
    # 统计结果
    passed = sum(1 for _, result in results if result)
    total = len(results)
    success = (passed == total)
    
    print(f"\n📊 Docker测试总结: {passed}/{total} 套件通过")
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    return success


if __name__ == '__main__':
    """Docker容器内的测试入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RTK GNSS Worker Docker测试套件')
    parser.add_argument('--type', choices=['all', 'unit', 'integration', 'architecture', 'system', 'real-integration'], 
                        default='all', help='测试类型')
    args = parser.parse_args()
    
    print("🐳 RTK GNSS Worker Docker Test Suite")
    print("=" * 60)
    
    success = False
    
    if args.type == 'unit':
        print("🔧 运行单元测试...")
        success = run_unit_tests()
    elif args.type == 'integration':
        print("🔗 运行集成测试...")
        success = run_integration_tests()
    elif args.type == 'real-integration':
        print("� 运行真实端到端集成测试...")
        success = run_real_integration_tests()
    elif args.type == 'system':
        print("🌐 运行系统测试...")
        success = run_system_tests()
    elif args.type == 'architecture':
        print("🏗️ 运行架构测试...")
        success = run_architecture_tests()
    else:
        print("🚀 运行所有Docker测试...")
        success = run_all_tests()
    
    if success:
        print("\n✅ Docker测试全部通过!")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败!")
        sys.exit(1)
