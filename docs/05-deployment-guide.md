# 部署运维指南

## 1. 系统要求

### 1.1 硬件要求

| 组件 | 最低要求 | 推荐配置 | 说明 |
|------|---------|---------|------|
| CPU | ARM Cortex-A7 / x86_64 | ARM Cortex-A53+ | 单核即可满足需求 |
| 内存 | 64MB | 128MB+ | 运行时占用约20-50MB |
| 存储 | 50MB | 200MB+ | 包含代码、日志和配置 |
| 网络 | WiFi/Ethernet | 有线网络优先 | 连接NTRIP服务器 |
| 串口 | 1个可用串口 | USB转串口/硬件串口 | 连接GNSS模块 |

### 1.2 软件要求

| 软件组件 | 版本要求 | 说明 |
|---------|---------|------|
| Python | >= 3.9 | 推荐3.11.6 |
| pyserial | >= 3.5 | 串口通信 |
| 操作系统 | Linux | 嵌入式Linux发行版 |

### 1.3 依赖库（精简版）

```txt
pyserial>=3.5
```

## 2. 快速部署（嵌入式设备）

### 2.1 直接部署（推荐）

```bash
# 1. 下载或复制代码到设备
scp -r rtk-gnss-worker/ user@device:/opt/

# 2. 登录设备
ssh user@device

# 3. 安装Python依赖
cd /opt/rtk-gnss-worker
pip install -r requirements.txt

# 4. 配置
cp config.json.example config.json
vim config.json

# 5. 测试运行
python main.py

# 6. 检查输出
tail -f /tmp/gnss_location.json
```

### 2.2 systemd服务部署

创建系统服务文件：

```bash
# 创建服务文件
sudo tee /etc/systemd/system/rtk-gnss-worker.service << EOF
[Unit]
Description=RTK GNSS Worker
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/rtk-gnss-worker
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable rtk-gnss-worker
sudo systemctl start rtk-gnss-worker

# 查看状态
sudo systemctl status rtk-gnss-worker
```

### 2.3 配置文件示例

```json
{
  "rtk": {
    "ntrip": {
      "server": "220.180.239.212",
      "port": 7990,
      "username": "QL_NTRIP",
      "password": "123456",
      "mountpoint": "HeFei",
      "timeout": 30,
      "reconnect_interval": 5,
      "max_retries": 3
    },
    "serial": {
      "port": "/dev/ttyUSB0",
      "baudrate": 115200,
      "timeout": 1.0
    },
    "output": {
      "type": "file",
      "file_path": "/tmp/gnss_location.json",
      "atomic_write": true,
      "update_interval": 1.0
    },
    "logging": {
      "level": "INFO",
      "file": "/var/log/rtk-gnss-worker.log",
      "max_size": "10MB",
      "backup_count": 5
    }
  }
}
```

# 启动命令
CMD ["python", "-m", "src.main"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  gnss-worker:
    build: .
    container_name: rtk-gnss-worker
    restart: unless-stopped
    
    # 设备映射
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
    
    # 环境变量
    environment:
      - GNSS_NTRIP_SERVER=220.180.239.212
      - GNSS_NTRIP_PORT=7990
      - GNSS_NTRIP_USERNAME=QL_NTRIP
      - GNSS_NTRIP_PASSWORD=123456
      - GNSS_NTRIP_MOUNTPOINT=HeFei
      - GNSS_SERIAL_PORT=/dev/ttyUSB0
      - GNSS_SERIAL_BAUDRATE=115200
      - GNSS_LOG_LEVEL=INFO
    
    # 数据卷
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
      - ./data:/app/data
    
    # 网络模式
    network_mode: host
    
    # 健康检查
    healthcheck:
      test: ["CMD", "python", "-m", "src.health_check"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 2.4 SystemD服务部署

#### 服务文件 /etc/systemd/system/gnss-worker.service

```ini
[Unit]
Description=RTK GNSS Worker Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=gnss
Group=gnss
WorkingDirectory=/opt/gnss-worker
Environment=PATH=/opt/gnss-worker/venv/bin
ExecStart=/opt/gnss-worker/venv/bin/python -m src.main
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

# 环境变量
Environment=GNSS_CONFIG_FILE=/etc/gnss-worker/config.json
Environment=GNSS_LOG_FILE=/var/log/gnss-worker/app.log

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/log/gnss-worker /var/lib/gnss-worker

[Install]
WantedBy=multi-user.target
```

#### 部署脚本

```bash
#!/bin/bash
# deploy.sh

set -e

# 配置变量
APP_NAME="gnss-worker"
APP_USER="gnss"
APP_HOME="/opt/gnss-worker"
CONFIG_DIR="/etc/gnss-worker"
LOG_DIR="/var/log/gnss-worker"
DATA_DIR="/var/lib/gnss-worker"

echo "Deploying RTK GNSS Worker..."

# 创建用户
if ! id "$APP_USER" &>/dev/null; then
    sudo useradd -r -s /bin/false -d "$APP_HOME" "$APP_USER"
    echo "Created user: $APP_USER"
fi

# 创建目录
sudo mkdir -p "$APP_HOME" "$CONFIG_DIR" "$LOG_DIR" "$DATA_DIR"
sudo chown "$APP_USER:$APP_USER" "$LOG_DIR" "$DATA_DIR"

# 复制代码
sudo cp -r . "$APP_HOME/"
sudo chown -R "$APP_USER:$APP_USER" "$APP_HOME"

# 安装依赖
cd "$APP_HOME"
sudo -u "$APP_USER" python -m venv venv
sudo -u "$APP_USER" venv/bin/pip install -r requirements.txt

# 复制配置文件
sudo cp config/config.json "$CONFIG_DIR/"
sudo chown root:root "$CONFIG_DIR/config.json"
sudo chmod 644 "$CONFIG_DIR/config.json"

# 安装系统服务
sudo cp scripts/gnss-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gnss-worker

echo "Deployment completed. Use 'sudo systemctl start gnss-worker' to start the service."
```

## 3. 配置管理

### 3.1 配置文件结构

```
/etc/gnss-worker/
├── config.json          # 主配置文件
├── ntrip/               # NTRIP相关配置
│   ├── accounts.json    # 账号配置
│   └── servers.json     # 服务器配置
├── serial/              # 串口配置
│   └── devices.json     # 设备配置
└── logging/             # 日志配置
    └── logging.json     # 日志格式配置
```

### 3.2 配置模板

#### 生产环境配置

```json
{
  "ntrip": {
    "server": "${GNSS_NTRIP_SERVER}",
    "port": "${GNSS_NTRIP_PORT:7990}",
    "username": "${GNSS_NTRIP_USERNAME}",
    "password": "${GNSS_NTRIP_PASSWORD}",
    "mountpoint": "${GNSS_NTRIP_MOUNTPOINT}",
    "timeout": 30.0,
    "keepalive_interval": 30.0,
    "retry_attempts": 10,
    "retry_delay": 1.0
  },
  "serial": {
    "port": "${GNSS_SERIAL_PORT:/dev/ttyUSB0}",
    "baudrate": "${GNSS_SERIAL_BAUDRATE:115200}",
    "timeout": 1.0
  },
  "output": {
    "type": "file",
    "file_path": "/var/lib/gnss-worker/location.json",
    "atomic_write": true
  },
  "logging": {
    "level": "${GNSS_LOG_LEVEL:INFO}",
    "file_path": "/var/log/gnss-worker/app.log",
    "max_size": "50MB",
    "backup_count": 10,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  },
  "health_check": {
    "enabled": true,
    "interval": 60.0,
    "port": 8080
  },
  "monitoring": {
    "metrics_enabled": true,
    "prometheus_port": 9090
  }
}
```

#### 开发环境配置

```json
{
  "ntrip": {
    "server": "localhost",
    "port": 7990,
    "username": "test",
    "password": "test",
    "mountpoint": "TEST"
  },
  "serial": {
    "port": "/dev/pts/1",
    "baudrate": 115200
  },
  "output": {
    "type": "file",
    "file_path": "./data/location.json",
    "atomic_write": false
  },
  "logging": {
    "level": "DEBUG",
    "file_path": "./logs/debug.log"
  }
}
```

### 3.3 配置验证脚本

```bash
#!/bin/bash
# validate_config.sh

CONFIG_FILE="${1:-/etc/gnss-worker/config.json}"

echo "Validating configuration: $CONFIG_FILE"

# 检查文件存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# 检查JSON格式
if ! python -m json.tool "$CONFIG_FILE" > /dev/null 2>&1; then
    echo "ERROR: Invalid JSON format in configuration file"
    exit 1
fi

# 使用应用程序验证配置
if python -c "
import json
import sys
from src.config import ConfigValidator

with open('$CONFIG_FILE') as f:
    config_data = json.load(f)

errors = ConfigValidator.validate_dict(config_data)
if errors:
    print('Configuration validation errors:')
    for error in errors:
        print(f'  - {error}')
    sys.exit(1)
else:
    print('Configuration is valid')
"; then
    echo "SUCCESS: Configuration validation passed"
else
    echo "ERROR: Configuration validation failed"
    exit 1
fi
```

## 4. 运维监控

### 4.1 日志管理

#### 日志结构

```
/var/log/gnss-worker/
├── app.log              # 主应用日志
├── app.log.1            # 轮转日志
├── app.log.2.gz         # 压缩备份
├── error.log            # 错误日志
├── ntrip.log            # NTRIP连接日志
├── serial.log           # 串口通信日志
└── performance.log      # 性能指标日志
```

#### 日志轮转配置 /etc/logrotate.d/gnss-worker

```
/var/log/gnss-worker/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 gnss gnss
    postrotate
        systemctl reload gnss-worker
    endscript
}
```

#### 结构化日志示例

```python
import structlog

logger = structlog.get_logger()

# 信息日志
logger.info(
    "NTRIP connected",
    server="220.180.239.212",
    mountpoint="HeFei",
    connection_time=2.5
)

# 错误日志
logger.error(
    "Serial port error",
    port="/dev/ttyUSB0",
    error_code="ENODEV",
    retry_count=3
)

# 性能日志
logger.info(
    "Performance metrics",
    rtcm_rate=15.2,
    location_rate=1.0,
    memory_mb=45.6,
    cpu_percent=2.3
)
```

### 4.2 健康检查

#### 健康检查端点

```python
from fastapi import FastAPI
from src.health import HealthChecker

app = FastAPI()
health_checker = HealthChecker()

@app.get("/health")
async def health_check():
    """基础健康检查"""
    return {"status": "healthy", "timestamp": datetime.now()}

@app.get("/health/detailed")
async def detailed_health_check():
    """详细健康检查"""
    result = await health_checker.check_all()
    return {
        "overall_status": result.overall_status,
        "components": result.component_status,
        "metrics": result.metrics,
        "timestamp": datetime.now()
    }

@app.get("/metrics")
async def get_metrics():
    """获取性能指标"""
    return await health_checker.get_metrics()
```

#### 健康检查脚本

```bash
#!/bin/bash
# health_check.sh

HEALTH_URL="${HEALTH_URL:-http://localhost:8080/health}"
TIMEOUT="${TIMEOUT:-5}"

# 基础健康检查
check_basic_health() {
    if curl -s --max-time "$TIMEOUT" "$HEALTH_URL" > /dev/null 2>&1; then
        echo "✓ Service is responding"
        return 0
    else
        echo "✗ Service is not responding"
        return 1
    fi
}

# 检查进程
check_process() {
    if pgrep -f "gnss-worker" > /dev/null; then
        echo "✓ Process is running"
        return 0
    else
        echo "✗ Process is not running"
        return 1
    fi
}

# 检查日志错误
check_log_errors() {
    local log_file="/var/log/gnss-worker/app.log"
    local error_count
    
    if [ -f "$log_file" ]; then
        error_count=$(tail -100 "$log_file" | grep -c "ERROR")
        if [ "$error_count" -gt 5 ]; then
            echo "✗ Too many errors in log ($error_count)"
            return 1
        else
            echo "✓ Log error count is acceptable ($error_count)"
            return 0
        fi
    else
        echo "⚠ Log file not found"
        return 1
    fi
}

# 检查数据新鲜度
check_data_freshness() {
    local data_file="/var/lib/gnss-worker/location.json"
    local max_age=120  # 2分钟
    
    if [ -f "$data_file" ]; then
        local file_age=$(($(date +%s) - $(stat -c %Y "$data_file")))
        if [ "$file_age" -le "$max_age" ]; then
            echo "✓ Data is fresh (${file_age}s old)"
            return 0
        else
            echo "✗ Data is stale (${file_age}s old)"
            return 1
        fi
    else
        echo "✗ Data file not found"
        return 1
    fi
}

# 主检查函数
main() {
    echo "RTK GNSS Worker Health Check"
    echo "============================"
    
    local exit_code=0
    
    check_process || exit_code=1
    check_basic_health || exit_code=1
    check_log_errors || exit_code=1
    check_data_freshness || exit_code=1
    
    echo ""
    if [ $exit_code -eq 0 ]; then
        echo "Overall Status: HEALTHY"
    else
        echo "Overall Status: UNHEALTHY"
    fi
    
    return $exit_code
}

main "$@"
```

### 4.3 监控指标

#### Prometheus指标导出

```python
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# 定义指标
rtcm_received_total = Counter('gnss_rtcm_received_total', 'Total RTCM messages received')
location_published_total = Counter('gnss_location_published_total', 'Total locations published')
connection_errors_total = Counter('gnss_connection_errors_total', 'Total connection errors')

ntrip_connected = Gauge('gnss_ntrip_connected', 'NTRIP connection status')
serial_connected = Gauge('gnss_serial_connected', 'Serial connection status')
last_location_age = Gauge('gnss_last_location_age_seconds', 'Age of last location data')

data_processing_duration = Histogram('gnss_data_processing_duration_seconds', 'Data processing duration')

# 启动指标服务器
def start_metrics_server(port=9090):
    start_http_server(port)
    logger.info(f"Metrics server started on port {port}")
```

#### Grafana仪表板配置

```json
{
  "dashboard": {
    "title": "RTK GNSS Worker",
    "panels": [
      {
        "title": "Connection Status",
        "type": "stat",
        "targets": [
          {
            "expr": "gnss_ntrip_connected",
            "legendFormat": "NTRIP"
          },
          {
            "expr": "gnss_serial_connected", 
            "legendFormat": "Serial"
          }
        ]
      },
      {
        "title": "Data Rates",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(gnss_rtcm_received_total[5m])",
            "legendFormat": "RTCM Rate"
          },
          {
            "expr": "rate(gnss_location_published_total[5m])",
            "legendFormat": "Location Rate"
          }
        ]
      },
      {
        "title": "Data Age",
        "type": "graph",
        "targets": [
          {
            "expr": "gnss_last_location_age_seconds",
            "legendFormat": "Location Age"
          }
        ]
      }
    ]
  }
}
```

### 4.4 告警规则

#### Prometheus告警规则

```yaml
groups:
  - name: gnss-worker
    rules:
      - alert: GNSSWorkerDown
        expr: up{job="gnss-worker"} == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "GNSS Worker is down"
          description: "GNSS Worker has been down for more than 30 seconds"

      - alert: NTRIPDisconnected
        expr: gnss_ntrip_connected == 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "NTRIP connection lost"
          description: "NTRIP connection has been down for more than 1 minute"

      - alert: LocationDataStale
        expr: gnss_last_location_age_seconds > 120
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Location data is stale"
          description: "No new location data for more than 2 minutes"

      - alert: HighErrorRate
        expr: rate(gnss_connection_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is above 0.1 per second for 5 minutes"
```

## 5. 故障排除

### 5.1 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|---------|----------|
| 无法连接NTRIP服务器 | 网络问题、认证失败 | 检查网络连接、验证账号密码 |
| 串口打开失败 | 设备不存在、权限不足 | 检查设备路径、用户权限 |
| 数据不更新 | GNSS模块故障、配置错误 | 检查硬件连接、验证配置 |
| 内存泄漏 | 队列未正确清理 | 重启服务、检查代码逻辑 |
| CPU使用率高 | 频繁重连、死循环 | 检查日志、优化重连策略 |

### 5.2 诊断工具

#### 诊断脚本

```bash
#!/bin/bash
# diagnose.sh

echo "RTK GNSS Worker Diagnostics"
echo "=========================="

# 系统信息
echo "System Information:"
echo "  OS: $(uname -a)"
echo "  Python: $(python --version)"
echo "  Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "  Disk: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 " used)"}')"
echo ""

# 服务状态
echo "Service Status:"
systemctl is-active --quiet gnss-worker && echo "  ✓ Service is active" || echo "  ✗ Service is not active"
systemctl is-enabled --quiet gnss-worker && echo "  ✓ Service is enabled" || echo "  ✗ Service is not enabled"
echo ""

# 网络连接
echo "Network Connectivity:"
if ping -c 1 google.com > /dev/null 2>&1; then
    echo "  ✓ Internet connectivity OK"
else
    echo "  ✗ No internet connectivity"
fi

if nc -z 220.180.239.212 7990 > /dev/null 2>&1; then
    echo "  ✓ NTRIP server reachable"
else
    echo "  ✗ NTRIP server not reachable"
fi
echo ""

# 串口设备
echo "Serial Devices:"
for device in /dev/ttyUSB* /dev/ttyACM*; do
    if [ -e "$device" ]; then
        echo "  Found: $device"
        ls -l "$device"
    fi
done
echo ""

# 日志分析
echo "Recent Log Entries:"
if [ -f "/var/log/gnss-worker/app.log" ]; then
    echo "  Last 5 log entries:"
    tail -5 "/var/log/gnss-worker/app.log" | sed 's/^/    /'
    
    echo "  Error count (last 100 lines):"
    error_count=$(tail -100 "/var/log/gnss-worker/app.log" | grep -c "ERROR")
    echo "    $error_count errors"
else
    echo "  ✗ Log file not found"
fi
```

### 5.3 故障恢复

#### 自动恢复脚本

```bash
#!/bin/bash
# auto_recover.sh

LOG_FILE="/var/log/gnss-worker/recovery.log"
SERVICE_NAME="gnss-worker"

log_message() {
    echo "[$(date)] $1" | tee -a "$LOG_FILE"
}

check_and_restart() {
    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        log_message "Service is down, attempting restart..."
        systemctl restart "$SERVICE_NAME"
        sleep 10
        
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            log_message "Service restart successful"
            return 0
        else
            log_message "Service restart failed"
            return 1
        fi
    fi
    return 0
}

check_data_freshness() {
    local data_file="/var/lib/gnss-worker/location.json"
    local max_age=300  # 5分钟
    
    if [ -f "$data_file" ]; then
        local file_age=$(($(date +%s) - $(stat -c %Y "$data_file")))
        if [ "$file_age" -gt "$max_age" ]; then
            log_message "Data is stale (${file_age}s), restarting service..."
            systemctl restart "$SERVICE_NAME"
            return 1
        fi
    fi
    return 0
}

# 主恢复逻辑
main() {
    log_message "Starting recovery check..."
    
    if check_and_restart && check_data_freshness; then
        log_message "All checks passed"
    else
        log_message "Recovery actions taken"
    fi
}

main "$@"
```

#### 定时恢复任务 (crontab)

```bash
# 每5分钟检查一次
*/5 * * * * /opt/gnss-worker/scripts/auto_recover.sh

# 每天重启一次（可选）
0 2 * * * systemctl restart gnss-worker

# 每周清理老日志
0 3 * * 0 find /var/log/gnss-worker -name "*.log.*" -mtime +30 -delete
```

这份部署运维指南提供了完整的部署、配置、监控和故障排除方案，确保RTK GNSS Worker能够稳定可靠地运行在生产环境中。
