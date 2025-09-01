#!/bin/bash
"""
专门运行真实端到端集成测试的脚本
"""

set -e

# 默认参数
REBUILD=false
COMPOSE_FILE="tests/docker-compose.unified.yml"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --rebuild)
            REBUILD=true
            shift
            ;;
        *)
            echo "未知参数: $1"
            echo "用法: $0 [--rebuild]"
            exit 1
            ;;
    esac
done

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查并启动mock服务
start_and_wait_mock_services() {
    log_info "启动Mock服务..."
    
    # 清理可能存在的服务
    docker-compose -f $COMPOSE_FILE down 2>/dev/null || true
    
    # 启动mock服务
    docker-compose -f $COMPOSE_FILE up -d ntrip-mock serial-mock
    
    if [ $? -ne 0 ]; then
        log_error "启动Mock服务失败"
        return 1
    fi
    
    log_info "等待Mock服务健康检查通过..."
    
    # 等待健康检查通过
    timeout=60
    start_time=$(date +%s)
    
    while true; do
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            log_error "Mock服务健康检查超时"
            docker-compose -f $COMPOSE_FILE logs ntrip-mock
            docker-compose -f $COMPOSE_FILE logs serial-mock
            return 1
        fi
        
        # 检查NTRIP Mock健康状态
        ntrip_healthy=$(docker-compose -f $COMPOSE_FILE ps ntrip-mock | grep -c "healthy" || echo "0")
        serial_healthy=$(docker-compose -f $COMPOSE_FILE ps serial-mock | grep -c "healthy" || echo "0")
        
        if [ "$ntrip_healthy" -gt 0 ] && [ "$serial_healthy" -gt 0 ]; then
            log_success "所有Mock服务健康检查通过"
            break
        fi
        
        echo "⏳ 等待健康检查... (${elapsed}s)"
        sleep 3
    done
    
    # 显示服务状态
    log_info "Mock服务状态:"
    docker-compose -f $COMPOSE_FILE ps ntrip-mock serial-mock
    
    return 0
}

# 运行真实集成测试
run_real_integration_test() {
    log_info "运行真实端到端集成测试..."
    
    docker-compose -f $COMPOSE_FILE run --rm test-real-integration
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_success "真实集成测试通过"
        return 0
    else
        log_error "真实集成测试失败"
        
        # 显示服务日志以便调试
        log_info "NTRIP Mock日志:"
        docker-compose -f $COMPOSE_FILE logs --tail=20 ntrip-mock
        
        log_info "Serial Mock日志:"
        docker-compose -f $COMPOSE_FILE logs --tail=20 serial-mock
        
        return 1
    fi
}

# 清理资源
cleanup() {
    log_info "清理测试资源..."
    docker-compose -f $COMPOSE_FILE down
    log_success "清理完成"
}

# 主函数
main() {
    echo "🧪 RTK GNSS Worker 真实端到端集成测试"
    echo "=" * 60
    
    # 设置错误处理
    trap cleanup EXIT
    
    # 构建或重建镜像
    if [ "$REBUILD" = true ]; then
        log_info "强制重新构建Docker镜像..."
        docker-compose -f $COMPOSE_FILE build --no-cache rtk-base
        log_success "镜像重建完成"
    elif ! docker images | grep -q "rtk-gnss-worker"; then
        log_info "构建Docker镜像..."
        docker-compose -f $COMPOSE_FILE build rtk-base
        log_success "镜像构建完成"
    else
        log_info "使用已有镜像（如需重建，请使用 --rebuild 参数）"
    fi
    
    # 启动并等待mock服务
    if ! start_and_wait_mock_services; then
        log_error "Mock服务启动失败"
        exit 1
    fi
    
    # 运行真实集成测试
    if ! run_real_integration_test; then
        log_error "真实集成测试失败"
        exit 1
    fi
    
    log_success "所有真实集成测试通过！"
}

# 运行主函数
main "$@"
