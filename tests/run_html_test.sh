#!/bin/bash

# RTK GNSS Worker 测试脚本 - 带HTML报告
# 使用方法: bash run_html_test.sh [--type test_type] [--output-dir output_directory]

set -e

# 默认参数
TEST_TYPE="all"
OUTPUT_DIR="reports"
CONTAINER_NAME="rtk-test-runner"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            TEST_TYPE="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help)
            echo "RTK GNSS Worker HTML测试报告生成器"
            echo ""
            echo "使用方法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --type TYPE        测试类型 (all|unit|integration|real-integration|system|architecture)"
            echo "  --output-dir DIR   报告输出目录 (默认: reports)"
            echo "  --help            显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 --type unit"
            echo "  $0 --type all --output-dir ./test-reports"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

echo "🚀 RTK GNSS Worker HTML测试报告生成器"
echo "==========================================="
echo "📊 测试类型: $TEST_TYPE"
echo "📁 输出目录: $OUTPUT_DIR"
echo "🐳 容器名称: $CONTAINER_NAME"
echo ""

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 清理可能存在的容器
echo "🧹 清理环境..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# 确保镜像存在
echo "🔍 检查Docker镜像..."
if ! docker image inspect rtk-gnss-worker:clean >/dev/null 2>&1; then
    echo "❌ Docker镜像 'rtk-gnss-worker:clean' 不存在"
    echo "请先运行: docker build -t rtk-gnss-worker:clean ."
    exit 1
fi

# 启动测试容器
echo "🐳 启动测试容器..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --network host \
    -v "$(pwd):/workspace" \
    -v "$(pwd)/$OUTPUT_DIR:/workspace/reports" \
    -w /workspace \
    rtk-gnss-worker:clean \
    tail -f /dev/null

# 等待容器启动
sleep 2

# 检查容器状态
if ! docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}" | grep -q "$CONTAINER_NAME"; then
    echo "❌ 容器启动失败"
    exit 1
fi

echo "✅ 容器启动成功"

# 在容器内运行HTML测试
echo ""
echo "🔬 开始执行测试..."
echo "==================="

# 执行测试并生成HTML报告
docker exec "$CONTAINER_NAME" python -c "
import sys
sys.path.insert(0, '/workspace/tests')
sys.path.insert(0, '/workspace/src')

from html_reporter import HTMLTestReporter
import os

# 创建HTML报告器
reporter = HTMLTestReporter(output_dir='reports')

# 开始测试会话
reporter.start_test_session('$TEST_TYPE')

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
success = True
commands = test_commands.get('$TEST_TYPE', test_commands['all'])

for test_name, command in commands:
    result = reporter.run_command_with_logging(command, test_name)
    if not result:
        success = False

# 结束测试会话
overall_success = reporter.end_test_session()

# 生成HTML报告
report_path = reporter.generate_html_report()
print(f'📄 HTML报告已生成: {report_path}')

# 退出状态
if overall_success:
    sys.exit(0)
else:
    sys.exit(1)
"

# 获取测试结果
TEST_RESULT=$?

# 清理容器
echo ""
echo "🧹 清理容器..."
docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true

# 检查报告文件
echo ""
echo "📋 生成的报告文件:"
ls -la "$OUTPUT_DIR"/*.html 2>/dev/null || echo "❌ 没有找到HTML报告文件"

# 输出结果
echo ""
if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ 测试完成，所有测试通过！"
    echo "📄 HTML报告已保存到: $OUTPUT_DIR/"
    echo "🌐 在浏览器中打开HTML文件查看详细报告"
else
    echo "❌ 测试完成，部分测试失败！"
    echo "📄 详细失败信息请查看HTML报告: $OUTPUT_DIR/"
fi

exit $TEST_RESULT
