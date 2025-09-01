# RTK GNSS Worker 实际使用指南

## 🚀 直接使用方式

### 方式1: 最简单的使用 (推荐)

```bash
cd rtk-gnss-worker
python examples/run_gnss_worker.py
```

这个命令会：
- 自动加载 `config.json` 配置文件
- 连接到NTRIP服务器 (220.180.239.212:7990)
- 读取GNSS数据并输出到 `/tmp/gnss_location.json`
- 在终端显示实时位置信息

### 方式2: 使用环境变量配置

```bash
cd rtk-gnss-worker
python examples/run_gnss_worker.py --env
```

### 方式3: 直接运行主程序

```bash
cd rtk-gnss-worker
python main.py --config config.json
```

## ⚙️ 配置你的设备

编辑 `config.json` 文件中的 `rtk` 部分：

```json
{
  "rtk": {
    "ntrip": {
      "server": "你的NTRIP服务器地址",
      "port": 7990,
      "username": "你的用户名", 
      "password": "你的密码",
      "mountpoint": "你的挂载点"
    },
    "serial": {
      "port": "/dev/ttyUSB0",  // 你的GNSS设备串口
      "baudrate": 115200,
      "host": null             // 如果使用TCP则设置IP地址
    },
    "output": {
      "file_path": "/tmp/gnss_location.json"  // 输出文件路径
    }
  }
}
```

## 📱 查看实时位置

位置数据会自动写入到配置的输出文件，格式如下：

```json
{
  "latitude": 31.8216921,
  "longitude": 117.1153447,
  "quality": 1,
  "satellites": 17,
  "hdop": 0.88,
  "altitude": 98.7,
  "timestamp": "2025-08-28T12:00:00"
}
```

## 🛠️ 故障排除

### 1. 串口权限问题
```bash
sudo chmod 666 /dev/ttyUSB0
# 或者将用户加入dialout组
sudo usermod -a -G dialout $USER
```

### 2. NTRIP连接失败
- 检查网络连接
- 验证NTRIP服务器地址、用户名、密码
- 确认挂载点是否正确

### 3. 没有位置数据输出
- 检查GNSS设备是否正常连接
- 确认串口设备路径正确
- 等待GNSS设备获取卫星信号（可能需要几分钟）

## 🔧 生产环境部署

### 使用systemd服务

1. 创建服务文件 `/etc/systemd/system/rtk-gnss-worker.service`:

```ini
[Unit]
Description=RTK GNSS Worker
After=network.target

[Service]
Type=simple
User=gnss
WorkingDirectory=/opt/rtk-gnss-worker
ExecStart=/usr/bin/python3 main.py --config config.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. 启动服务:

```bash
sudo systemctl enable rtk-gnss-worker
sudo systemctl start rtk-gnss-worker
sudo systemctl status rtk-gnss-worker
```

### 使用Docker (推荐)

```bash
# 一键测试
cd tests
./run_docker_test.sh

# 生产环境运行
cd tests
docker-compose -f docker-compose.unified.yml up -d gnss-worker
```

## 📊 监控和日志

- **日志文件**: `/var/log/rtk-gnss-worker.log`
- **输出文件**: `/tmp/gnss_location.json`
- **实时监控**: `tail -f /var/log/rtk-gnss-worker.log`

## 📞 常见使用场景

### 1. 测试GNSS设备
```bash
python examples/run_gnss_worker.py
# 观察终端输出，确认位置数据正常
```

### 2. 集成到其他应用
```python
from src.gnss_worker import GNSSWorker
from src.config import Config

config = Config.from_file('config.json')
worker = GNSSWorker(config)
worker.start()

# 你的应用逻辑
# 位置数据会自动写入配置的输出文件

worker.stop()
```

### 3. 获取单次位置
```bash
python examples/run_gnss_worker.py --env
# 运行10秒后自动停止
```

这就是实际使用RTK GNSS Worker的完整方法！
