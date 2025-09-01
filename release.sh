#!/bin/bash
# RTK GNSS Worker 发布脚本
# 功能：将项目打包为可部署的tar.gz文件

set -e  # 遇到错误立即停止

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
PROJECT_NAME="rtk-gnss-worker"
VERSION="1.0.0"
BUILD_DIR="$PROJECT_DIR/build"
RELEASE_DIR="$PROJECT_DIR/releases"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
RTK GNSS Worker 发布脚本

用法: $0 [选项]

选项:
    -v, --version VERSION    指定版本号 (默认: $VERSION)
    -o, --output DIR         指定输出目录 (默认: $RELEASE_DIR)
    -h, --help              显示此帮助信息
    --clean                 清理构建目录
    --include-tests         包含测试文件（默认排除）
    --include-docs          包含文档文件（默认排除）

示例:
    $0                          # 使用默认设置
    $0 -v 1.1.0                # 指定版本号
    $0 --include-tests          # 包含测试文件
    $0 --clean                  # 仅清理，不构建

EOF
}

# 解析命令行参数
INCLUDE_TESTS=false
INCLUDE_DOCS=false
CLEAN_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -o|--output)
            RELEASE_DIR="$2"
            shift 2
            ;;
        --include-tests)
            INCLUDE_TESTS=true
            shift
            ;;
        --include-docs)
            INCLUDE_DOCS=true
            shift
            ;;
        --clean)
            CLEAN_ONLY=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 清理函数
clean_build() {
    print_info "清理构建目录..."
    rm -rf "$BUILD_DIR"
    rm -rf "$PROJECT_DIR"/*.egg-info
    find "$PROJECT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_DIR" -name "*.pyc" -delete 2>/dev/null || true
    print_success "清理完成"
}

# 如果只是清理，则执行清理后退出
if [ "$CLEAN_ONLY" = true ]; then
    clean_build
    exit 0
fi

# 主构建函数
build_release() {
    print_info "开始构建 RTK GNSS Worker v$VERSION"
    
    # 1. 清理并创建构建目录
    clean_build
    mkdir -p "$BUILD_DIR"
    mkdir -p "$RELEASE_DIR"
    
    # 2. 创建临时打包目录
    PACKAGE_NAME="${PROJECT_NAME}-${VERSION}"
    PACKAGE_DIR="$BUILD_DIR/$PACKAGE_NAME"
    mkdir -p "$PACKAGE_DIR"
    
    print_info "复制源文件到打包目录..."
    
    # 3. 复制核心文件
    print_info "复制核心源代码..."
    cp -r "$PROJECT_DIR/src" "$PACKAGE_DIR/"
    
    # 4. 复制配置文件
    if [ -d "$PROJECT_DIR/config" ]; then
        print_info "复制配置文件..."
        cp -r "$PROJECT_DIR/config" "$PACKAGE_DIR/"
    fi
    
    # 5. 复制主要文件
    for file in README.md requirements.txt config.json main.py Dockerfile docker-compose.yml; do
        if [ -f "$PROJECT_DIR/$file" ]; then
            print_info "复制 $file"
            cp "$PROJECT_DIR/$file" "$PACKAGE_DIR/"
        fi
    done
    
    # 6. 复制脚本目录（如果存在）
    if [ -d "$PROJECT_DIR/scripts" ]; then
        print_info "复制脚本文件..."
        cp -r "$PROJECT_DIR/scripts" "$PACKAGE_DIR/"
        # 确保脚本文件可执行
        find "$PACKAGE_DIR/scripts" -name "*.sh" -exec chmod +x {} \;
    fi
    
    # 7. 可选：复制测试文件
    if [ "$INCLUDE_TESTS" = true ] && [ -d "$PROJECT_DIR/tests" ]; then
        print_info "复制测试文件..."
        cp -r "$PROJECT_DIR/tests" "$PACKAGE_DIR/"
    fi
    
    # 8. 可选：复制文档文件
    if [ "$INCLUDE_DOCS" = true ] && [ -d "$PROJECT_DIR/docs" ]; then
        print_info "复制文档文件..."
        cp -r "$PROJECT_DIR/docs" "$PACKAGE_DIR/"
    fi
    
    # 9. 创建部署脚本
    print_info "生成部署脚本..."
    cat > "$PACKAGE_DIR/deploy.sh" << 'DEPLOY_EOF'
#!/bin/bash
# RTK GNSS Worker 部署脚本

set -e

echo "🚀 RTK GNSS Worker 部署脚本"
echo "================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3，请先安装Python 3.8+"
    exit 1
fi

# 检查pip
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo "❌ 错误: 未找到 pip，请先安装pip"
    exit 1
fi

# 安装依赖
echo "📦 安装Python依赖..."
if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt || pip install -r requirements.txt
else
    echo "⚠️  未找到requirements.txt，手动安装依赖..."
    pip3 install pyserial requests || pip install pyserial requests
fi

# 设置执行权限
if [ -d scripts ]; then
    echo "🔧 设置脚本执行权限..."
    find scripts -name "*.sh" -exec chmod +x {} \;
fi

# 创建日志目录
echo "📁 创建日志目录..."
mkdir -p logs

# 创建启动脚本
echo "📝 创建启动脚本..."
cat > start.sh << 'START_EOF'
#!/bin/bash
# RTK GNSS Worker 启动脚本

# 设置Python路径
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# 默认配置（可以通过环境变量覆盖）
export GNSS_NTRIP_SERVER="${GNSS_NTRIP_SERVER:-localhost}"
export GNSS_NTRIP_PORT="${GNSS_NTRIP_PORT:-2101}"
export GNSS_NTRIP_USERNAME="${GNSS_NTRIP_USERNAME:-test}"
export GNSS_NTRIP_PASSWORD="${GNSS_NTRIP_PASSWORD:-test}"
export GNSS_NTRIP_MOUNTPOINT="${GNSS_NTRIP_MOUNTPOINT:-TEST}"
export GNSS_SERIAL_PORT="${GNSS_SERIAL_PORT:-/dev/ttyUSB0}"
export GNSS_OUTPUT_FILE="${GNSS_OUTPUT_FILE:-/tmp/gnss_location.json}"
export GNSS_LOG_LEVEL="${GNSS_LOG_LEVEL:-INFO}"

echo "🚀 启动 RTK GNSS Worker..."
echo "📡 NTRIP服务器: $GNSS_NTRIP_SERVER:$GNSS_NTRIP_PORT"
echo "🔌 串口设备: $GNSS_SERIAL_PORT"
echo "📄 输出文件: $GNSS_OUTPUT_FILE"

# 启动主程序
python3 main.py "$@"
START_EOF

chmod +x start.sh

echo ""
echo "✅ 部署完成！"
echo ""
echo "使用方法："
echo "1. 配置环境变量（可选）："
echo "   export GNSS_NTRIP_SERVER=your-server.com"
echo "   export GNSS_NTRIP_USERNAME=your-username"
echo "   export GNSS_NTRIP_PASSWORD=your-password"
echo ""
echo "2. 启动服务："
echo "   ./start.sh"
echo ""
echo "3. 或者使用配置文件："
echo "   python3 main.py --config config.json"
echo ""
DEPLOY_EOF
    
    chmod +x "$PACKAGE_DIR/deploy.sh"
    
    # 10. 创建版本信息文件
    print_info "生成版本信息..."
    cat > "$PACKAGE_DIR/VERSION" << EOF
RTK GNSS Worker
版本: $VERSION
构建时间: $(date)
构建主机: $(hostname)
EOF
    
    # 11. 生成文件清单
    print_info "生成文件清单..."
    (cd "$PACKAGE_DIR" && find . -type f | sort > FILES.txt)
    
    # 12. 创建tar.gz包
    TAR_FILE="$RELEASE_DIR/${PACKAGE_NAME}.tar.gz"
    print_info "创建压缩包: $TAR_FILE"
    
    (cd "$BUILD_DIR" && tar -czf "../releases/$(basename "$TAR_FILE")" "$PACKAGE_NAME")
    
    # 13. 计算文件哈希
    if command -v sha256sum &> /dev/null; then
        print_info "计算SHA256校验和..."
        (cd "$RELEASE_DIR" && sha256sum "$(basename "$TAR_FILE")" > "$(basename "$TAR_FILE").sha256")
    fi
    
    # 14. 显示结果
    FILE_SIZE=$(du -h "$TAR_FILE" | cut -f1)
    print_success "构建完成！"
    echo ""
    echo "📦 发布包信息："
    echo "   文件: $TAR_FILE"
    echo "   大小: $FILE_SIZE"
    echo "   版本: $VERSION"
    echo ""
    echo "🚀 部署方法："
    echo "   1. 上传到目标服务器"
    echo "   2. tar -zxvf $(basename "$TAR_FILE")"
    echo "   3. cd $PACKAGE_NAME"
    echo "   4. ./deploy.sh"
    echo "   5. ./start.sh"
    echo ""
}

# 执行构建
build_release
