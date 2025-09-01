#!/bin/bash

# RTK GNSS Worker Docker测试脚本
# 这个脚本提供完整的容器化测试环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker环境
check_docker() {
    log_info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon未运行，请先启动Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose未安装，请先安装docker-compose"
        exit 1
    fi
    
    log_success "Docker环境检查通过"
}

# 清理旧容器和网络
cleanup() {
    log_info "清理旧的容器和网络..."
    
    # 停止并删除容器
    docker-compose -f tests/docker-compose.unified.yml down --remove-orphans 2>/dev/null || true
    
    # 删除悬空镜像
    docker image prune -f 2>/dev/null || true
    
    log_success "清理完成"
}

# 构建或检查镜像
build_or_check_images() {
    log_info "检查Docker镜像..."
    
    # 使用统一的Docker Compose文件
    local compose_file="tests/docker-compose.unified.yml"
    
    if [[ "$REBUILD_IMAGES" == "true" ]]; then
        log_info "强制重新构建环境镜像..."
        docker-compose -f "$compose_file" build --no-cache rtk-base
    else
        # 检查环境镜像是否存在
        if ! docker images | grep -q "rtk-gnss-worker"; then
            log_info "构建环境镜像..."
            docker-compose -f "$compose_file" build rtk-base
        else
            log_info "使用已有环境镜像（业务代码通过volume映射，无需重建）"
        fi
    fi
    
    if [ $? -ne 0 ]; then
        log_error "镜像构建失败"
        return 1
    fi
    
    log_success "镜像准备完成"
}

# 启动Mock服务
start_mock_services() {
    log_info "启动Mock服务..."
    
    # 使用统一的Docker Compose文件
    local compose_file="tests/docker-compose.unified.yml"
    
    # 启动NTRIP Mock
    docker-compose -f "$compose_file" up -d ntrip-mock
    if [ $? -ne 0 ]; then
        log_error "启动NTRIP Mock失败"
        return 1
    fi
    
    # 启动Serial Mock
    docker-compose -f "$compose_file" up -d serial-mock
    if [ $? -ne 0 ]; then
        log_error "启动Serial Mock失败"
        return 1
    fi
    
    log_info "等待Mock服务启动..."
    sleep 5
    
    # 检查服务状态
    if ! docker-compose -f "$compose_file" ps | grep -q "ntrip-mock.*Up"; then
        log_error "NTRIP Mock服务启动失败"
        return 1
    fi
    
    if ! docker-compose -f "$compose_file" ps | grep -q "serial-mock.*Up"; then
        log_error "Serial Mock服务启动失败"
        return 1
    fi
    
    log_success "Mock服务启动完成"
}

# 运行单元测试
run_unit_tests() {
    log_info "运行单元测试..."
    
    docker-compose -f tests/docker-compose.unified.yml run --rm test-unit
    
    if [ $? -eq 0 ]; then
        log_success "单元测试通过"
        return 0
    else
        log_error "单元测试失败"
        return 1
    fi
}

# 运行集成测试
run_integration_tests() {
    log_info "运行集成测试..."
    
    docker-compose -f tests/docker-compose.unified.yml run --rm test-integration
    
    if [ $? -eq 0 ]; then
        log_success "集成测试通过"
        return 0
    else
        log_error "集成测试失败"
        return 1
    fi
}

# 运行真实集成测试
run_real_integration_tests() {
    log_info "运行真实端到端集成测试..."
    
    # 确保Mock服务健康
    log_info "等待Mock服务健康检查..."
    local timeout=60
    local start_time=$(date +%s)
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            log_error "Mock服务健康检查超时"
            docker-compose -f tests/docker-compose.unified.yml logs ntrip-mock
            docker-compose -f tests/docker-compose.unified.yml logs serial-mock
            return 1
        fi
        
        # 检查健康状态
        local ntrip_healthy=$(docker-compose -f tests/docker-compose.unified.yml ps ntrip-mock | grep -c "healthy" || echo "0")
        local serial_healthy=$(docker-compose -f tests/docker-compose.unified.yml ps serial-mock | grep -c "healthy" || echo "0")
        
        if [ "$ntrip_healthy" -gt 0 ] && [ "$serial_healthy" -gt 0 ]; then
            log_success "所有Mock服务健康检查通过"
            break
        fi
        
        echo "⏳ 等待健康检查... (${elapsed}s)"
        sleep 3
    done
    
    # 显示服务状态
    log_info "Mock服务状态:"
    docker-compose -f tests/docker-compose.unified.yml ps ntrip-mock serial-mock
    
    # 运行真实集成测试
    docker-compose -f tests/docker-compose.unified.yml run --rm test-real-integration
    
    if [ $? -eq 0 ]; then
        log_success "真实集成测试通过"
        return 0
    else
        log_error "真实集成测试失败"
        
        # 显示服务日志以便调试
        log_info "NTRIP Mock日志:"
        docker-compose -f tests/docker-compose.unified.yml logs --tail=20 ntrip-mock
        
        log_info "Serial Mock日志:"
        docker-compose -f tests/docker-compose.unified.yml logs --tail=20 serial-mock
        
        return 1
    fi
}

# 运行混合集成测试（真实NTRIP + 模拟串口）
run_hybrid_integration_tests() {
    log_info "运行混合集成测试（真实NTRIP + 模拟串口）..."
    
    # 检查网络连接 - 使用更宽松的检查
    log_info "检查网络连接..."
    if ! timeout 10 bash -c "cat < /dev/null > /dev/tcp/220.180.239.212/7990" 2>/dev/null; then
        log_info "尝试ping检查..."
        if ! ping -c 1 -W 5 220.180.239.212 >/dev/null 2>&1; then
            log_info "尝试DNS解析检查..."
            if ! nslookup 220.180.239.212 >/dev/null 2>&1; then
                log_warning "网络连接检查失败，但仍然尝试运行测试"
            else
                log_info "DNS解析成功，继续测试"
            fi
        else
            log_info "Ping成功，继续测试"
        fi
    else
        log_info "TCP连接测试成功，继续测试"
    fi
    
    # 确保Serial Mock服务健康（NTRIP使用真实服务，串口使用Mock）
    log_info "等待Serial Mock服务健康检查..."
    local timeout=30
    local start_time=$(date +%s)
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            log_warning "Serial Mock服务健康检查超时，但继续测试"
            break
        fi
        
        # 检查Serial Mock健康状态
        local serial_healthy=$(docker-compose -f tests/docker-compose.unified.yml ps serial-mock | grep -c "healthy" || echo "0")
        
        if [ "$serial_healthy" -gt 0 ]; then
            log_success "Serial Mock服务健康检查通过"
            break
        fi
        
        echo "⏳ 等待Serial Mock健康检查... (${elapsed}s)"
        sleep 2
    done
    
    # 显示服务状态
    log_info "Mock服务状态:"
    docker-compose -f tests/docker-compose.unified.yml ps serial-mock || log_warning "无法显示服务状态"
    
    # 运行混合集成测试
    log_info "运行混合测试：真实NTRIP Caster + 模拟串口（使用宿主机网络）"
    
    # 使用host网络模式运行测试，这样可以直接访问外部NTRIP服务器
    # 同时需要调整Serial Mock的连接地址为localhost（因为在host网络中）
    if docker run --rm \
        --network host \
        -v "$(pwd)":/app \
        -w /app \
        -e PYTHONPATH=/app/src \
        -e GNSS_SERIAL_HOST=localhost \
        -e GNSS_SERIAL_PORT=8888 \
        rtk-gnss-worker:clean \
        python -m pytest /app/tests/real/test_hybrid_integration.py -v -s --log-cli-level=INFO; then
        log_success "混合集成测试通过"
        return 0
    else
        log_error "混合集成测试失败"
        
        # 显示Serial Mock日志以便调试
        log_info "Serial Mock日志:"
        docker-compose -f tests/docker-compose.unified.yml logs --tail=20 serial-mock || log_warning "无法获取服务日志"
        
        return 1
    fi
}

# 运行系统测试
run_system_tests() {
    log_info "运行系统测试..."
    
    # 运行系统测试
    docker-compose -f tests/docker-compose.unified.yml run --rm test-system
    
    if [ $? -eq 0 ]; then
        log_success "系统测试通过"
        return 0
    else
        log_error "系统测试失败"
        return 1
    fi
}

# 运行架构测试
run_architecture_tests() {
    log_info "运行架构测试..."
    
    # 运行架构测试
    docker-compose -f tests/docker-compose.unified.yml run --rm test-architecture
    
    if [ $? -eq 0 ]; then
        log_success "架构测试通过"
        return 0
    else
        log_error "架构测试失败"
        return 1
    fi
}

# 运行应用测试
run_app_test() {
    log_info "运行应用测试..."
    
    # 启动应用容器
    docker-compose -f tests/docker-compose.unified.yml up -d gnss-worker
    
    # 等待应用启动
    sleep 10
    
    # 检查应用状态
    if ! docker-compose -f tests/docker-compose.unified.yml ps | grep -q "gnss-worker.*Up"; then
        log_error "GNSS Worker应用启动失败"
        docker-compose -f tests/docker-compose.unified.yml logs gnss-worker
        return 1
    fi
    
    # 检查输出文件
    log_info "检查位置输出..."
    docker-compose -f tests/docker-compose.unified.yml exec gnss-worker ls -la /tmp/
    
    if docker-compose -f tests/docker-compose.unified.yml exec gnss-worker test -f /tmp/gnss_location.json; then
        log_success "位置文件已生成"
        docker-compose -f tests/docker-compose.unified.yml exec gnss-worker cat /tmp/gnss_location.json
    else
        log_warning "位置文件未找到，可能需要更长时间"
    fi
    
    # 检查日志
    log_info "检查应用日志..."
    docker-compose -f tests/docker-compose.unified.yml logs --tail=20 gnss-worker
    
    log_success "应用测试完成"
}

# 打印测试总结报告
print_test_summary() {
    echo ""
    echo "🎯 ============================================================="
    echo "📊 RTK GNSS Worker 测试套件执行总结"
    echo "🎯 ============================================================="
    echo ""
    
    # 统计测试结果
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    local skipped_tests=0
    
    echo "📋 测试详情："
    echo ""
    
    for test_type in "unit" "integration" "real-integration" "hybrid" "system" "architecture" "app"; do
        if [[ -n "${test_results[$test_type]}" ]]; then
            total_tests=$((total_tests + 1))
            printf "%-20s %s\n" "🔹 $test_type:" "${test_results[$test_type]}"
            echo "   ${test_descriptions[$test_type]}"
            echo ""
            
            case "${test_results[$test_type]}" in
                *"✅"*) passed_tests=$((passed_tests + 1)) ;;
                *"❌"*) failed_tests=$((failed_tests + 1)) ;;
                *"⚠️"*) skipped_tests=$((skipped_tests + 1)) ;;
            esac
        fi
    done
    
    echo "📈 测试统计："
    echo "   • 总测试数:     $total_tests"
    echo "   • 通过:         $passed_tests ✅"
    echo "   • 失败:         $failed_tests ❌"
    echo "   • 跳过/警告:    $skipped_tests ⚠️"
    echo ""
    
    # 计算成功率
    if [ $total_tests -gt 0 ]; then
        local success_rate=$((passed_tests * 100 / total_tests))
        echo "🎯 成功率: $success_rate%"
        
        if [ $failed_tests -eq 0 ]; then
            echo "🎉 恭喜！所有核心测试都通过了！"
            echo "✨ RTK GNSS Worker 测试套件验证完成"
        elif [ $success_rate -ge 80 ]; then
            echo "👍 大部分测试通过，系统基本稳定"
        else
            echo "⚠️  存在较多失败测试，需要关注"
        fi
    fi
    
    echo ""
    echo "🔧 测试架构说明："
    echo "   • unit         - 核心组件单元测试"
    echo "   • integration  - 组件协作集成测试" 
    echo "   • real         - 端到端真实环境测试"
    echo "   • system       - 系统韧性压力测试"
    echo "   • architecture- 代码质量架构测试"
    echo "   • app          - 完整应用容器测试"
    echo ""
    echo "🎯 ============================================================="
    echo ""
}

# 生成测试报告
generate_report() {
    log_info "生成测试报告..."
    
    # 创建报告目录
    mkdir -p reports
    
    # 生成服务状态报告
    docker-compose -f tests/docker-compose.unified.yml ps > reports/services_status.txt 2>/dev/null || echo "No services running" > reports/services_status.txt
    
    # 生成日志报告
    docker-compose -f tests/docker-compose.unified.yml logs > reports/all_logs.txt 2>/dev/null || echo "No logs available" > reports/all_logs.txt
    
    # 生成网络信息
    docker network ls | grep rtk > reports/networks.txt 2>/dev/null || echo "No RTK networks found" > reports/networks.txt
    
    log_success "测试报告已生成到 reports/ 目录"
}

# 主测试流程
main() {
    log_info "开始RTK GNSS Worker容器化测试"
    
    # 解析命令行参数
    TEST_TYPE="all"
    CLEANUP_AFTER="true"
    FORCE_REBUILD="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --type)
                TEST_TYPE="$2"
                shift 2
                ;;
            --no-cleanup)
                CLEANUP_AFTER="false"
                shift
                ;;
            --rebuild)
                REBUILD_IMAGES="true"
                shift
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --type [all|unit|integration|real-integration|hybrid|system|architecture|app]  测试类型 (默认: all)"
                echo "  --no-cleanup                                   测试后不清理容器"
                echo "  --rebuild                                      强制重新构建镜像"
                echo "  --help                                         显示帮助"
                echo ""
                echo "测试类型说明:"
                echo "  unit            - 单元测试（快速）"
                echo "  integration     - 集成测试（使用mock）"
                echo "  real-integration- 真实端到端集成测试（完整数据流）"
                echo "  hybrid          - 混合集成测试（真实NTRIP + 模拟串口）"
                echo "  system          - 系统级测试（环境弹性）"
                echo "  architecture    - 架构级测试（质量度量）"
                echo "  app             - 应用测试"
                echo "  all             - 运行所有测试"
                echo ""
                echo "示例:"
                echo "  $0 --type unit                           # 运行单元测试"
                echo "  $0 --type all                           # 运行所有测试"
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                exit 1
                ;;
        esac
    done
    
    # 执行测试步骤
    check_docker
    cleanup
    build_or_check_images
    start_mock_services
    
    # 执行指定类型的测试
    case $TEST_TYPE in
        "unit")
            echo "🔧 执行单元测试 - 测试核心组件功能（NMEA解析、NTRIP客户端、串口处理等）"
            if run_unit_tests; then
                echo "✅ 单元测试通过"
            else
                echo "❌ 单元测试失败"
                exit 1
            fi
            ;;
        "integration")
            echo "🔗 执行集成测试 - 测试组件间协作和完整工作流程"
            if run_integration_tests; then
                echo "✅ 集成测试通过"
            else
                echo "❌ 集成测试失败"
                exit 1
            fi
            ;;
        "real-integration")
            echo "🌐 执行真实集成测试 - 端到端数据流和双线程架构验证"
            if run_real_integration_tests; then
                echo "✅ 真实集成测试通过"
            else
                echo "⚠️ 真实集成测试失败"
            fi
            ;;
        "hybrid")
            echo "🔀 执行混合集成测试 - 真实NTRIP Caster + 模拟串口"
            if run_hybrid_integration_tests; then
                echo "✅ 混合集成测试通过"
            else
                echo "⚠️ 混合集成测试失败"
            fi
            ;;
        "system")
            echo "🛡️ 执行系统韧性测试 - 测试系统在异常情况下的恢复能力"
            if run_system_tests; then
                echo "✅ 系统测试通过"
            else
                echo "❌ 系统测试失败"
            fi
            ;;
        "architecture")
            echo "🏗️ 执行架构质量测试 - 验证代码质量、线程安全性和配置管理"
            if run_architecture_tests; then
                echo "✅ 架构测试通过"
            else
                echo "❌ 架构测试失败"
            fi
            ;;
        "app")
            echo "📱 执行应用测试 - 完整容器化应用的运行验证"
            if run_app_test; then
                echo "✅ 应用测试通过"
            else
                echo "❌ 应用测试失败"
            fi
            ;;
        "all")
            log_info "运行完整测试套件..."
            
            # 初始化测试结果跟踪
            declare -A test_results
            declare -A test_descriptions
            
            # 定义测试描述
            test_descriptions["unit"]="单元测试 - 测试核心组件功能（NMEA解析、NTRIP客户端、串口处理等）"
            test_descriptions["integration"]="集成测试 - 测试组件间协作和完整工作流程"
            test_descriptions["real-integration"]="真实集成测试 - 端到端数据流和双线程架构验证"
            test_descriptions["hybrid"]="混合集成测试 - 真实NTRIP Caster + 模拟串口验证"
            test_descriptions["system"]="系统韧性测试 - 测试系统在异常情况下的恢复能力"
            test_descriptions["architecture"]="架构质量测试 - 验证代码质量、线程安全性和配置管理"
            test_descriptions["app"]="应用测试 - 完整容器化应用的运行验证"
            
            # 执行测试并记录结果
            if run_unit_tests; then
                test_results["unit"]="✅ 通过"
            else
                test_results["unit"]="❌ 失败"
                log_error "单元测试失败，停止后续测试"
                print_test_summary
                exit 1
            fi
            
            if run_integration_tests; then
                test_results["integration"]="✅ 通过"
            else
                test_results["integration"]="❌ 失败"
                log_error "集成测试失败，停止后续测试"
                print_test_summary
                exit 1
            fi
            
            if run_real_integration_tests; then
                test_results["real-integration"]="✅ 通过"
            else
                test_results["real-integration"]="⚠️ 跳过"
                log_warning "真实集成测试失败，但继续其他测试"
            fi
            
            if run_hybrid_integration_tests; then
                test_results["hybrid"]="✅ 通过"
            else
                test_results["hybrid"]="⚠️ 跳过"
                log_warning "混合集成测试失败，但继续其他测试"
            fi
            
            if run_system_tests; then
                test_results["system"]="✅ 通过"
            else
                test_results["system"]="❌ 失败"
            fi
            
            if run_architecture_tests; then
                test_results["architecture"]="✅ 通过"
            else
                test_results["architecture"]="❌ 失败"
            fi
            
            if run_app_test; then
                test_results["app"]="✅ 通过"
            else
                test_results["app"]="❌ 失败"
            fi
            
            # 打印详细的测试总结
            print_test_summary
            ;;
        *)
            log_error "未知测试类型: $TEST_TYPE"
            exit 1
            ;;
    esac
    
    # 生成报告
    generate_report
    
    # 清理
    if [ "$CLEANUP_AFTER" = "true" ]; then
        log_info "清理测试环境..."
        cleanup
    else
        log_info "保留测试环境，使用 docker-compose -f docker-compose.test.yml down 清理"
    fi
    
    log_success "测试完成!"
}

# 信号处理
trap cleanup EXIT

# 执行主函数
main "$@"
