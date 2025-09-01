#!/bin/bash
"""
简单的HTML报告生成脚本
"""

# 设置错误处理
set -e

# 日志函数
log_info() {
    echo "[INFO] $1"
}

log_success() {
    echo "[SUCCESS] $1"
}

log_error() {
    echo "[ERROR] $1"
}

# 生成HTML报告
generate_html_report() {
    local test_type="${1:-unit}"
    
    log_info "生成 $test_type 测试的HTML报告..."
    
    # 确定测试路径
    local test_path
    case "$test_type" in
        "unit")
            test_path="/app/tests/unit/"
            ;;
        "integration")
            test_path="/app/tests/integration/"
            ;;
        "all")
            test_path="/app/tests/"
            ;;
        *)
            log_error "未知的测试类型: $test_type"
            exit 1
            ;;
    esac
    
    # 时间戳
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local html_file="${test_type}_test_report_${timestamp}.html"
    local json_file="${test_type}_test_report_${timestamp}.json"
    
    # 创建输出目录
    local output_dir="html_reports"
    rm -rf "$output_dir" 2>/dev/null || true
    mkdir -p "$output_dir"
    
    log_info "准备Docker环境..."
    
    # 确保Docker环境清洁
    docker-compose -f tests/docker-compose.unified.yml down -v 2>/dev/null || true
    
    # 构建Docker镜像
    if ! docker-compose -f tests/docker-compose.unified.yml build test-unit --no-cache; then
        log_error "Docker镜像构建失败"
        exit 1
    fi
    
    log_info "运行测试并生成HTML报告..."
    
    # 运行Docker容器并保存输出
    docker-compose -f tests/docker-compose.unified.yml run --rm test-unit bash -c "
        # 设置Python路径
        export PYTHONPATH=/app/src:/app:\$PYTHONPATH
        
        # 切换到工作目录
        cd /app
        
        # 创建临时报告目录
        mkdir -p /tmp/reports
        
        echo '⚡ 运行pytest生成HTML报告...'
        pytest $test_path \
            --html=/tmp/reports/$html_file \
            --self-contained-html \
            --json-report \
            --json-report-file=/tmp/reports/$json_file \
            -v --tb=short
        
        exit_code=\$?
        
        echo ''
        echo '📋 生成的文件:'
        ls -la /tmp/reports/
        
        # 输出文件内容的base64编码
        if [ -f /tmp/reports/$html_file ]; then
            echo '=== HTML_START ==='
            base64 /tmp/reports/$html_file
            echo '=== HTML_END ==='
        fi
        
        if [ -f /tmp/reports/$json_file ]; then
            echo '=== JSON_START ==='
            base64 /tmp/reports/$json_file
            echo '=== JSON_END ==='
        fi
        
        exit \$exit_code
    " > "$output_dir/docker_output.log" 2>&1
    
    local docker_exit_code=$?
    
    log_info "提取生成的报告文件..."
    
    # 从Docker输出中提取文件
    if [ -f "$output_dir/docker_output.log" ]; then
        # 显示测试输出（过滤掉base64数据）
        echo ""
        echo "=== 测试执行输出 ==="
        sed '/=== HTML_START ===/,/=== HTML_END ===/d; /=== JSON_START ===/,/=== JSON_END ===/d' "$output_dir/docker_output.log"
        echo "================="
        
        # 提取HTML文件
        if grep -q "HTML_START" "$output_dir/docker_output.log"; then
            sed -n '/=== HTML_START ===/,/=== HTML_END ===/p' "$output_dir/docker_output.log" | \
                sed '1d;$d' | base64 -d > "$output_dir/$html_file"
            
            if [ -f "$output_dir/$html_file" ]; then
                log_success "HTML报告已生成: $output_dir/$html_file"
                log_info "文件大小: $(du -h "$output_dir/$html_file" | cut -f1)"
            fi
        fi
        
        # 提取JSON文件
        if grep -q "JSON_START" "$output_dir/docker_output.log"; then
            sed -n '/=== JSON_START ===/,/=== JSON_END ===/p' "$output_dir/docker_output.log" | \
                sed '1d;$d' | base64 -d > "$output_dir/$json_file"
            
            if [ -f "$output_dir/$json_file" ]; then
                log_success "JSON报告已生成: $output_dir/$json_file"
            fi
        fi
    fi
    
    # 清理Docker环境
    log_info "清理Docker环境..."
    docker-compose -f tests/docker-compose.unified.yml down -v 2>/dev/null || true
    
    # 检查结果
    if [ -f "$output_dir/$html_file" ]; then
        log_success "HTML测试报告生成完成！"
        
        # 尝试打开报告
        if command -v explorer.exe >/dev/null 2>&1; then
            log_info "正在打开HTML报告..."
            explorer.exe "$(wslpath -w "$(realpath "$output_dir/$html_file")")" 2>/dev/null || true
        fi
        
        return 0
    else
        log_error "HTML报告生成失败"
        return 1
    fi
}

# 主函数
main() {
    local test_type="${1:-unit}"
    
    echo "🔧 RTK GNSS Worker HTML报告生成器"
    echo "=============================================="
    
    # 切换到项目根目录
    cd "$(dirname "$0")/.."
    
    generate_html_report "$test_type"
}

# 运行主函数
main "$@"
