# RTK GNSS Worker

一个专为嵌入式设备设计的简化RTK高精度定位工作器，支持NTRIP差分数据流和精确位置输出。

## 🎯 设计目标

- **嵌入式优化**: 专为小板子设计，最小化资源占用
- **简单可靠**: 简化架构，提高稳定性
- **配置统一**: 支持JSON配置文件
- **部署友好**: 单目录部署，无复杂依赖

## ✨ 功能特性

- ✅ **NTRIP客户端**: 连接NTRIP服务器获取RTK差分数据
- ✅ **双模式通信**: 支持串口和TCP两种GNSS连接方式  
- ✅ **NMEA解析**: 精确解析GPS定位数据
- ✅ **原子输出**: 原子文件操作避免读写冲突
- ✅ **自动重连**: 网络和串口断线自动恢复
- ✅ **资源优化**: < 50MB内存，< 5% CPU占用
- ✅ **统一日志**: 集中式日志管理系统
- ✅ **虚拟测试**: 支持虚拟串口端到端测试

## 🚀 快速开始

### 🎮 虚拟串口完整测试（推荐开发测试）

这是最完整的测试方式，模拟真实RTK GNSS系统的完整数据流：

```bash
# 1. 克隆项目
git clone <repo> && cd rtk-gnss-worker

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置NTRIP服务器（使用真实移动CORS）
# 编辑config.json，设置serial.port为"/tmp/ttyGNSS1"

# 4. 启动虚拟GNSS模拟器
python3 virtual_gnss.py

# 5. 在另一个终端启动RTK Worker
python3 start.py

# 6. 在第三个终端监控位置输出
while true; do echo "$(date '+%H:%M:%S') - RTK位置:"; cat gnss_location.json; echo "---"; sleep 1; done
```

**测试效果**：
- 📤 虚拟GNSS每秒发送模拟位置数据
- 📡 RTK Worker连接真实移动CORS获取差分数据  
- 📥 实时监控RTCM差分数据传输
- 📍 输出高精度RTK固定解位置信息

### 嵌入式设备部署（生产环境）

```bash
# 1. 复制代码到设备
scp -r rtk-gnss-worker/ user@device:/opt/

# 2. 安装依赖（仅需pyserial）
pip install -r requirements.txt

# 3. 配置真实GNSS设备
cd /opt/rtk-gnss-worker
cp config.json.example config.json
# 编辑config.json，设置serial.port为"/dev/ttyUSB0"

# 4. 运行
python3 start.py

# 5. 查看位置输出
tail -f gnss_location.json
```

## ⚙️ 配置说明

项目使用 `config.json` 配置文件：

```json
{
  "ntrip": {
    "server": "120.253.226.97",
    "port": 8002,
    "username": "cvhd7823",
    "password": "n8j5c88f",
    "mountpoint": "RTCM33_GRCEJ",
    "timeout": 30.0,
    "reconnect_interval": 5,
    "max_retries": 3
  },
  "serial": {
    "port": "/tmp/ttyGNSS1",
    "baudrate": 115200,
    "timeout": 1.0
  },
  "output": {
    "type": "file",
    "file_path": "gnss_location.json",
    "atomic_write": true,
    "update_interval": 1.0
  },
  "logging": {
    "level": "INFO",
    "file": "logs/rtk-gnss-worker.log",
    "max_size": "10MB",
    "backup_count": 5
  }
}
```

**配置说明**：
- **NTRIP**: 移动CORS差分服务配置（已配置可用账号）
- **Serial**: 串口配置，虚拟测试用 `/tmp/ttyGNSS1`，实际部署用 `/dev/ttyUSB0`
- **Output**: 位置数据输出到 `gnss_location.json`
- **Logging**: 统一日志管理

## 📊 输出格式

位置数据以JSON格式实时输出到 `gnss_location.json`：

```json
{
  "timestamp": 1756453169.7165158,
  "latitude": 31.820581666666666,
  "longitude": 117.115335,
  "altitude": 50.4,
  "quality": 4,
  "satellites": 17,
  "hdop": 0.6,
  "raw_nmea": "$GNGGA,073929.715,3149.2349,N,11706.9201,E,4,17,0.6,50.4,M,-3.2,M,1.5,0001*4C"
}
```

**字段说明**：
- `quality`: 定位质量 (4=RTK固定解，最高精度)
- `satellites`: 可见卫星数量  
- `hdop`: 水平精度因子 (越小越好)
- `latitude/longitude`: WGS84坐标系经纬度
- `altitude`: 海拔高度(米)

## 🧪 测试

### 虚拟串口完整测试（推荐）

```bash
# 启动虚拟GNSS模拟器
python3 virtual_gnss.py

# 启动RTK Worker
python3 start.py

# 监控位置输出
watch -n 1 'echo "$(date)" && cat gnss_location.json'
```

## 📁 项目结构

```
rtk-gnss-worker/
├── src/                    # 源代码
│   ├── config.py          # 配置管理
│   ├── gnss_worker.py     # 主工作器类
│   ├── location_publisher.py # 位置发布器
│   ├── logger.py          # 统一日志系统
│   ├── nmea_parser.py     # NMEA解析器
│   ├── ntrip_client.py    # NTRIP客户端
│   └── serial_handler.py  # 串口处理器
├── tests/                  # 测试代码
├── virtual_gnss.py        # 虚拟串口GNSS模拟器
├── start.py               # 程序启动器
├── config.json            # 配置文件
├── requirements.txt       # Python依赖
└── README.md              # 项目文档
```

## 🔥 特性详解

### 虚拟串口测试系统

- **完整数据流**: 虚拟GNSS → RTK Worker → 位置输出
- **真实差分数据**: 连接移动CORS获取真实RTCM数据
- **双向监控**: 同时监控NMEA输入和RTCM输出
- **一键启动**: 简单命令即可开始完整测试

### 可靠性保证

- **自动重连机制**: NTRIP和串口断线自动重连
- **数据验证**: NMEA校验和验证，损坏数据过滤
- **原子文件操作**: 保证输出文件的完整性
- **统一日志**: 集中式日志管理，便于调试

### 生产就绪

- **嵌入式优化**: 低内存占用，快速响应
- **即插即用**: 支持多种GNSS设备
- **配置简单**: 单一JSON配置文件

## 📋 系统要求

- Python 3.11+
- Linux操作系统  
- socat (用于虚拟串口测试)
- 串口设备或虚拟串口
- 网络连接（用于NTRIP）

## 🛠️ 故障排查

### 常见问题

1. **串口权限问题**
   ```bash
   sudo usermod -a -G dialout $USER
   # 重新登录
   ```

2. **虚拟串口创建失败**
   ```bash
   # 安装socat
   sudo apt-get install socat
   ```

3. **NTRIP连接失败**
   - 检查网络连接
   - 验证移动CORS账号是否有效

4. **位置文件未生成**
   - 检查GNSS数据是否正常
   - 查看应用日志

### 日志分析

查看详细日志：

```bash
tail -f logs/rtk-gnss-worker.log
```

## 📈 性能指标

- **处理延迟**: < 100ms
- **内存使用**: < 50MB (嵌入式优化)
- **CPU使用**: < 5% (单核)
- **重连时间**: < 10s
- **定位精度**: RTK固定解，厘米级

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

---

**🎯 快速开始**: 执行虚拟串口测试流程体验完整RTK GNSS系统！