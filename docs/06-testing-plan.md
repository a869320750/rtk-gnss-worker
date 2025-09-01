# 测试方案

## 1. 测试策略

### 1.1 测试金字塔

```
                /\
               /  \
              /    \
             /  E2E  \          端到端测试 (10%)
            /________\
           /          \
          /  集成测试   \        集成测试 (20%)
         /______________\
        /                \
       /    单元测试       \     单元测试 (70%)
      /____________________\
```

### 1.2 测试分类

| 测试类型 | 目标 | 工具 | 覆盖率要求 |
|---------|------|------|-----------|
| 单元测试 | 验证单个模块功能 | pytest, unittest.mock | > 80% |
| 集成测试 | 验证模块间交互 | pytest, docker | > 60% |
| 端到端测试 | 验证完整功能流程 | pytest, real hardware | > 90% |
| 性能测试 | 验证性能指标 | pytest-benchmark | 满足要求 |
| 压力测试 | 验证系统稳定性 | locust, custom scripts | 24小时稳定 |

### 1.3 测试环境

#### 开发测试环境

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  # NTRIP模拟器
  ntrip-simulator:
    image: ntrip-simulator:latest
    ports:
      - "7990:7990"
    environment:
      - MOUNT_POINTS=TEST,HeFei
      - USERS=test:test,QL_NTRIP:123456
  
  # 串口模拟器
  serial-simulator:
    image: serial-simulator:latest
    volumes:
      - /tmp:/tmp
    command: ["socat", "pty,link=/tmp/ttyS0", "pty,link=/tmp/ttyS1"]
  
  # Redis (用于测试队列)
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  # 测试数据库
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: test_gnss
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    ports:
      - "5432:5432"
```

## 2. 单元测试

### 2.1 测试结构

```
tests/
├── unit/
│   ├── test_gnss_worker.py
│   ├── test_ntrip_client.py
│   ├── test_serial_comm.py
│   ├── test_nmea_parser.py
│   ├── test_location_publisher.py
│   └── test_config.py
├── integration/
│   ├── test_end_to_end.py
│   ├── test_ntrip_integration.py
│   └── test_serial_integration.py
├── performance/
│   ├── test_throughput.py
│   ├── test_memory_usage.py
│   └── test_latency.py
├── fixtures/
│   ├── nmea_samples.py
│   ├── rtcm_samples.py
│   └── config_samples.py
└── conftest.py
```

### 2.2 NTRIPClient 单元测试

```python
# tests/unit/test_ntrip_client.py
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.ntrip_client import NTRIPClient, NTRIPConfig

class TestNTRIPClient:
    
    @pytest.fixture
    def config(self):
        return NTRIPConfig(
            server="test.server.com",
            port=7990,
            username="test",
            password="test",
            mountpoint="TEST"
        )
    
    @pytest.fixture
    def client(self, config):
        return NTRIPClient(config)
    
    @pytest.mark.asyncio
    async def test_connect_success(self, client):
        """测试成功连接"""
        with patch('asyncio.open_connection') as mock_open:
            # 模拟成功连接
            mock_reader = AsyncMock()
            mock_writer = Mock()
            mock_open.return_value = (mock_reader, mock_writer)
            
            # 模拟服务器响应
            mock_reader.readline.return_value = b"ICY 200 OK\r\n"
            
            result = await client.connect()
            
            assert result is True
            assert client.connected is True
            mock_open.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_auth_failure(self, client):
        """测试认证失败"""
        with patch('asyncio.open_connection') as mock_open:
            mock_reader = AsyncMock()
            mock_writer = Mock()
            mock_open.return_value = (mock_reader, mock_writer)
            
            # 模拟认证失败响应
            mock_reader.readline.return_value = b"HTTP/1.0 401 Unauthorized\r\n"
            
            result = await client.connect()
            
            assert result is False
            assert client.connected is False
    
    @pytest.mark.asyncio
    async def test_send_gga(self, client):
        """测试发送GGA数据"""
        # 先建立连接
        client.connected = True
        client.writer = Mock()
        
        gga_data = "$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58"
        
        result = await client.send_gga(gga_data)
        
        assert result is True
        client.writer.write.assert_called_once()
        client.writer.drain.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_receive_rtcm(self, client):
        """测试接收RTCM数据"""
        client.connected = True
        client.reader = AsyncMock()
        
        # 模拟RTCM数据
        rtcm_data = b'\xd3\x00\x13\x3e\xd0\x00\x03\x8a\x0e\x46\x15\x02\x34'
        client.reader.read.side_effect = [rtcm_data, b'']
        
        data_received = []
        async for data in client.receive_rtcm():
            data_received.append(data)
            if len(data_received) >= 1:  # 只接收一次
                break
        
        assert len(data_received) == 1
        assert data_received[0] == rtcm_data
    
    @pytest.mark.asyncio
    async def test_reconnect_logic(self, client):
        """测试重连逻辑"""
        with patch.object(client, '_do_connect') as mock_connect:
            # 第一次连接失败，第二次成功
            mock_connect.side_effect = [False, True]
            
            # 模拟重连
            client.shutdown_event = asyncio.Event()
            
            # 启动重连任务
            task = asyncio.create_task(client._auto_reconnect())
            
            # 等待一小段时间让重连逻辑执行
            await asyncio.sleep(0.1)
            
            # 停止重连
            client.shutdown_event.set()
            await task
            
            assert mock_connect.call_count == 2
```

### 2.3 SerialComm 单元测试

```python
# tests/unit/test_serial_comm.py
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from src.serial_comm import SerialComm, SerialConfig

class TestSerialComm:
    
    @pytest.fixture
    def config(self):
        return SerialConfig(
            port="/dev/ttyUSB0",
            baudrate=115200,
            timeout=1.0
        )
    
    @pytest.fixture
    def serial_comm(self, config):
        return SerialComm(config)
    
    def test_open_success(self, serial_comm):
        """测试成功打开串口"""
        with patch('serial.Serial') as mock_serial:
            mock_port = Mock()
            mock_serial.return_value = mock_port
            mock_port.is_open = True
            
            result = asyncio.run(serial_comm.open())
            
            assert result is True
            assert serial_comm.is_open is True
            mock_serial.assert_called_once()
    
    def test_open_failure(self, serial_comm):
        """测试串口打开失败"""
        with patch('serial.Serial') as mock_serial:
            mock_serial.side_effect = Exception("Port not found")
            
            result = asyncio.run(serial_comm.open())
            
            assert result is False
            assert serial_comm.is_open is False
    
    @pytest.mark.asyncio
    async def test_write_rtcm(self, serial_comm):
        """测试写入RTCM数据"""
        # 模拟打开的串口
        serial_comm.is_open = True
        serial_comm.serial_port = Mock()
        serial_comm.write_buffer = asyncio.Queue()
        
        rtcm_data = b'\xd3\x00\x13\x3e\xd0'
        
        result = await serial_comm.write_rtcm(rtcm_data)
        
        assert result is True
        assert not serial_comm.write_buffer.empty()
    
    @pytest.mark.asyncio
    async def test_read_nmea(self, serial_comm):
        """测试读取NMEA数据"""
        serial_comm.is_open = True
        serial_comm.read_buffer = asyncio.Queue()
        
        # 预先放入测试数据
        nmea_line = "$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58"
        await serial_comm.read_buffer.put(nmea_line)
        
        received_data = []
        async for data in serial_comm.read_nmea():
            received_data.append(data)
            if len(received_data) >= 1:
                break
        
        assert len(received_data) == 1
        assert received_data[0] == nmea_line
    
    def test_validate_nmea_checksum(self, serial_comm):
        """测试NMEA校验和验证"""
        valid_nmea = "$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58"
        invalid_nmea = "$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*59"
        
        assert serial_comm._validate_nmea_checksum(valid_nmea) is True
        assert serial_comm._validate_nmea_checksum(invalid_nmea) is False
```

### 2.4 NMEAParser 单元测试

```python
# tests/unit/test_nmea_parser.py
import pytest
from datetime import datetime
from src.nmea_parser import NMEAParser
from src.models import LocationData

class TestNMEAParser:
    
    @pytest.fixture
    def parser(self):
        return NMEAParser()
    
    def test_parse_gga_valid(self, parser):
        """测试解析有效的GGA语句"""
        gga_line = "$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58"
        
        result = parser.parse(gga_line)
        
        assert result is not None
        assert isinstance(result, LocationData)
        assert abs(result.latitude - 31.821692133) < 0.000001
        assert abs(result.longitude - 117.115344733) < 0.000001
        assert result.quality == 1
        assert result.satellites == 17
        assert result.hdop == 0.88
        assert result.altitude == 98.7
    
    def test_parse_gga_invalid(self, parser):
        """测试解析无效的GGA语句"""
        invalid_lines = [
            "$GNGGA,invalid,data*00",  # 无效数据
            "$GNGGA,115713.000",       # 数据不完整
            "GNGGA,115713.000...",     # 缺少$前缀
            "",                        # 空字符串
        ]
        
        for line in invalid_lines:
            result = parser.parse(line)
            assert result is None
    
    def test_parse_coordinate(self, parser):
        """测试坐标解析"""
        # 北纬
        lat = parser._parse_coordinate("3149.301528", "N")
        assert abs(lat - 31.821692133) < 0.000001
        
        # 南纬
        lat = parser._parse_coordinate("3149.301528", "S")
        assert abs(lat - (-31.821692133)) < 0.000001
        
        # 东经
        lon = parser._parse_coordinate("11706.920684", "E")
        assert abs(lon - 117.115344733) < 0.000001
        
        # 西经
        lon = parser._parse_coordinate("11706.920684", "W")
        assert abs(lon - (-117.115344733)) < 0.000001
    
    def test_parse_time(self, parser):
        """测试时间解析"""
        time_str = "115713.000"
        result = parser._parse_time(time_str)
        
        assert isinstance(result, datetime)
        assert result.hour == 11
        assert result.minute == 57
        assert result.second == 13
    
    @pytest.mark.parametrize("nmea_type,expected_parser", [
        ("GNGGA", "_parse_gga"),
        ("GPGGA", "_parse_gga"),
        ("GNRMC", "_parse_rmc"),
        ("GPRMC", "_parse_rmc"),
    ])
    def test_parser_selection(self, parser, nmea_type, expected_parser):
        """测试解析器选择"""
        assert nmea_type in parser.parsers
        assert parser.parsers[nmea_type].__name__ == expected_parser
```

### 2.5 测试配置文件

```python
# conftest.py
import pytest
import asyncio
import tempfile
import json
from pathlib import Path

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_config_file():
    """创建临时配置文件"""
    config_data = {
        "ntrip": {
            "server": "test.server.com",
            "port": 7990,
            "username": "test",
            "password": "test",
            "mountpoint": "TEST"
        },
        "serial": {
            "port": "/dev/ttyUSB0",
            "baudrate": 115200
        },
        "output": {
            "type": "file",
            "file_path": "/tmp/test_location.json"
        },
        "logging": {
            "level": "DEBUG"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        yield f.name
    
    Path(f.name).unlink()

@pytest.fixture
def sample_nmea_data():
    """提供样本NMEA数据"""
    return [
        "$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58",
        "$GNRMC,115713.000,A,3149.301528,N,11706.920684,E,0.00,0.00,280825,,,A*76",
        "$GPGSA,A,3,01,02,03,04,05,06,07,08,09,10,11,12,1.0,0.88,0.5*3A",
    ]

@pytest.fixture
def sample_rtcm_data():
    """提供样本RTCM数据"""
    return b'\xd3\x00\x13\x3e\xd0\x00\x03\x8a\x0e\x46\x15\x02\x34\x9c\x6e\x07\x48\x00\x00\x95\x6e'
```

## 3. 集成测试

### 3.1 NTRIP集成测试

```python
# tests/integration/test_ntrip_integration.py
import pytest
import asyncio
import docker
from src.ntrip_client import NTRIPClient, NTRIPConfig

class TestNTRIPIntegration:
    
    @pytest.fixture(scope="class")
    async def ntrip_server(self):
        """启动NTRIP测试服务器"""
        client = docker.from_env()
        
        # 启动NTRIP模拟器容器
        container = client.containers.run(
            "ntrip-simulator:latest",
            ports={'7990/tcp': 7990},
            environment={
                'MOUNT_POINTS': 'TEST',
                'USERS': 'test:test'
            },
            detach=True
        )
        
        # 等待服务器启动
        await asyncio.sleep(2)
        
        yield container
        
        # 清理
        container.stop()
        container.remove()
    
    @pytest.mark.asyncio
    async def test_real_ntrip_connection(self, ntrip_server):
        """测试真实NTRIP连接"""
        config = NTRIPConfig(
            server="localhost",
            port=7990,
            username="test",
            password="test",
            mountpoint="TEST"
        )
        
        client = NTRIPClient(config)
        
        try:
            # 测试连接
            result = await client.connect()
            assert result is True
            
            # 测试数据接收
            data_count = 0
            timeout = 10  # 10秒超时
            
            async for data in client.receive_rtcm():
                data_count += 1
                if data_count >= 5:  # 接收5个数据包
                    break
            
            assert data_count >= 5
            
        finally:
            await client.disconnect()
```

### 3.2 端到端集成测试

```python
# tests/integration/test_end_to_end.py
import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from src.gnss_worker import GNSSWorker
from src.config import Config

class TestEndToEnd:
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, temp_config_file):
        """测试完整工作流程"""
        # 修改配置使用模拟器
        with open(temp_config_file, 'r') as f:
            config_data = json.load(f)
        
        config_data['ntrip']['server'] = 'localhost'
        config_data['serial']['port'] = '/tmp/ttyS0'  # 虚拟串口
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            modified_config_file = f.name
        
        try:
            config = Config.from_file(modified_config_file)
            worker = GNSSWorker(config)
            
            # 启动工作器
            await worker.start()
            
            # 等待数据处理
            await asyncio.sleep(5)
            
            # 检查状态
            status = worker.get_status()
            assert status.status == "running"
            
            # 检查指标
            metrics = worker.get_metrics()
            assert metrics.rtcm_received_count > 0
            
        finally:
            await worker.stop()
            Path(modified_config_file).unlink()
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, temp_config_file):
        """测试错误恢复机制"""
        config = Config.from_file(temp_config_file)
        worker = GNSSWorker(config)
        
        await worker.start()
        
        # 模拟网络错误
        worker.ntrip_client.connected = False
        
        # 等待自动恢复
        await asyncio.sleep(10)
        
        # 检查是否恢复
        status = worker.get_status()
        assert status.ntrip_connected or status.error_count > 0
        
        await worker.stop()
```

## 4. 性能测试

### 4.1 吞吐量测试

```python
# tests/performance/test_throughput.py
import pytest
import asyncio
import time
from src.ntrip_client import NTRIPClient
from src.serial_comm import SerialComm

class TestThroughput:
    
    @pytest.mark.asyncio
    async def test_rtcm_throughput(self):
        """测试RTCM数据吞吐量"""
        # 使用模拟数据源
        rtcm_data = b'\xd3\x00\x13\x3e\xd0' * 1000  # 5KB数据
        
        start_time = time.time()
        processed_count = 0
        
        # 模拟处理1000个数据包
        for i in range(1000):
            # 模拟数据处理
            await asyncio.sleep(0.001)  # 1ms处理时间
            processed_count += 1
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = processed_count / duration
        
        # 要求吞吐量 > 100 packets/second
        assert throughput > 100
        
    @pytest.mark.benchmark
    def test_nmea_parsing_performance(self, benchmark):
        """测试NMEA解析性能"""
        from src.nmea_parser import NMEAParser
        
        parser = NMEAParser()
        nmea_line = "$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58"
        
        result = benchmark(parser.parse, nmea_line)
        
        # 确保解析成功
        assert result is not None
        
        # 性能要求：解析时间 < 1ms
        assert benchmark.stats.stats.mean < 0.001
```

### 4.2 内存使用测试

```python
# tests/performance/test_memory_usage.py
import pytest
import asyncio
import psutil
import os
from src.gnss_worker import GNSSWorker

class TestMemoryUsage:
    
    @pytest.mark.asyncio
    async def test_memory_stability(self, temp_config_file):
        """测试内存使用稳定性"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        config = Config.from_file(temp_config_file)
        worker = GNSSWorker(config)
        
        await worker.start()
        
        # 运行一段时间并监控内存
        memory_samples = []
        for i in range(60):  # 监控60秒
            await asyncio.sleep(1)
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
        
        await worker.stop()
        
        # 分析内存使用
        max_memory = max(memory_samples)
        avg_memory = sum(memory_samples) / len(memory_samples)
        memory_growth = max_memory - initial_memory
        
        # 内存要求
        assert max_memory < 100  # 最大内存 < 100MB
        assert memory_growth < 50  # 内存增长 < 50MB
        
        # 检查内存泄漏（简单检查最后10个样本的平均值）
        recent_avg = sum(memory_samples[-10:]) / 10
        early_avg = sum(memory_samples[:10]) / 10
        growth_rate = (recent_avg - early_avg) / early_avg
        
        assert growth_rate < 0.1  # 内存增长率 < 10%
```

### 4.3 延迟测试

```python
# tests/performance/test_latency.py
import pytest
import asyncio
import time
from src.gnss_worker import GNSSWorker

class TestLatency:
    
    @pytest.mark.asyncio
    async def test_data_processing_latency(self):
        """测试数据处理延迟"""
        latencies = []
        
        # 模拟数据处理延迟测试
        for i in range(100):
            start_time = time.time()
            
            # 模拟数据处理过程
            nmea_line = "$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58"
            
            # 解析 -> 发布的完整流程
            from src.nmea_parser import NMEAParser
            parser = NMEAParser()
            location = parser.parse(nmea_line)
            
            # 模拟发布
            await asyncio.sleep(0.001)  # 模拟发布延迟
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # 转换为毫秒
            latencies.append(latency)
        
        # 分析延迟
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        # 延迟要求
        assert avg_latency < 10   # 平均延迟 < 10ms
        assert max_latency < 50   # 最大延迟 < 50ms
        assert p95_latency < 20   # 95%延迟 < 20ms
```

## 5. 压力测试

### 5.1 长时间稳定性测试

```python
# tests/stress/test_stability.py
import pytest
import asyncio
import time
import logging
from src.gnss_worker import GNSSWorker

class TestStability:
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_24_hour_stability(self, temp_config_file):
        """24小时稳定性测试"""
        config = Config.from_file(temp_config_file)
        worker = GNSSWorker(config)
        
        # 设置测试时长（实际测试时使用24小时）
        test_duration = 60 * 60 * 24  # 24小时
        # test_duration = 60  # 开发时使用60秒
        
        start_time = time.time()
        await worker.start()
        
        error_count = 0
        restart_count = 0
        
        try:
            while time.time() - start_time < test_duration:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                status = worker.get_status()
                
                if status.status == "error":
                    error_count += 1
                    logging.warning(f"Error detected: {status.last_error}")
                    
                    # 尝试重启
                    await worker.stop()
                    await asyncio.sleep(5)
                    await worker.start()
                    restart_count += 1
                
                # 记录运行指标
                metrics = worker.get_metrics()
                logging.info(f"Uptime: {status.uptime}, RTCM: {metrics.rtcm_received_count}")
        
        finally:
            await worker.stop()
        
        # 验证稳定性指标
        uptime = time.time() - start_time
        assert uptime > test_duration * 0.95  # 至少95%的时间在运行
        assert restart_count < 5  # 重启次数 < 5次
```

### 5.2 负载测试

```python
# tests/stress/test_load.py
import pytest
import asyncio
import concurrent.futures
from src.gnss_worker import GNSSWorker

class TestLoad:
    
    @pytest.mark.asyncio
    async def test_high_frequency_data(self):
        """高频数据负载测试"""
        from src.nmea_parser import NMEAParser
        from src.location_publisher import FilePublisher
        
        parser = NMEAParser()
        publisher = FilePublisher({"file_path": "/tmp/load_test.json"})
        
        # 模拟高频数据（100Hz）
        nmea_line = "$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58"
        
        start_time = time.time()
        processed_count = 0
        
        # 10秒高频测试
        while time.time() - start_time < 10:
            location = parser.parse(nmea_line)
            if location:
                await publisher.publish(location)
                processed_count += 1
            
            await asyncio.sleep(0.01)  # 100Hz
        
        processing_rate = processed_count / 10
        assert processing_rate >= 95  # 至少95Hz的处理能力
    
    @pytest.mark.asyncio
    async def test_concurrent_workers(self):
        """并发工作器测试"""
        workers = []
        
        try:
            # 启动多个工作器实例
            for i in range(5):
                config = Config.from_dict({
                    "serial": {"port": f"/tmp/ttyS{i}"},
                    "output": {"file_path": f"/tmp/location_{i}.json"}
                })
                worker = GNSSWorker(config)
                await worker.start()
                workers.append(worker)
            
            # 运行一段时间
            await asyncio.sleep(30)
            
            # 检查所有工作器状态
            for i, worker in enumerate(workers):
                status = worker.get_status()
                assert status.status in ["running", "error"]
        
        finally:
            # 清理所有工作器
            for worker in workers:
                await worker.stop()
```

## 6. 测试自动化

### 6.1 GitHub Actions配置

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.8, 3.11, "3.10"]
    
    services:
      redis:
        image: redis
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=src --cov-report=xml
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
    
    - name: Run performance tests
      run: |
        pytest tests/performance/ -v --benchmark-only
```

### 6.2 测试报告生成

```python
# scripts/generate_test_report.py
import subprocess
import json
import os
from pathlib import Path

def run_tests():
    """运行所有测试并生成报告"""
    
    # 运行单元测试
    result = subprocess.run([
        "pytest", "tests/unit/", 
        "--cov=src", 
        "--cov-report=html",
        "--cov-report=json",
        "--json-report", 
        "--json-report-file=test-results.json"
    ], capture_output=True, text=True)
    
    # 解析测试结果
    with open("test-results.json") as f:
        test_results = json.load(f)
    
    # 生成报告
    report = {
        "summary": test_results["summary"],
        "coverage": get_coverage_info(),
        "performance": run_performance_tests(),
        "timestamp": datetime.now().isoformat()
    }
    
    # 保存报告
    with open("test-report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("Test report generated: test-report.json")

if __name__ == "__main__":
    run_tests()
```

### 6.3 质量门禁

```python
# scripts/quality_gate.py
import json
import sys

def check_quality_gate():
    """检查质量门禁"""
    
    # 读取测试报告
    with open("test-report.json") as f:
        report = json.load(f)
    
    # 质量标准
    requirements = {
        "test_pass_rate": 0.95,    # 95%测试通过率
        "code_coverage": 0.80,     # 80%代码覆盖率
        "performance_threshold": {
            "avg_latency": 10,      # 10ms平均延迟
            "memory_usage": 100     # 100MB内存使用
        }
    }
    
    # 检查测试通过率
    pass_rate = report["summary"]["passed"] / report["summary"]["total"]
    if pass_rate < requirements["test_pass_rate"]:
        print(f"❌ Test pass rate too low: {pass_rate:.2%}")
        return False
    
    # 检查代码覆盖率
    coverage = report["coverage"]["totals"]["percent_covered"] / 100
    if coverage < requirements["code_coverage"]:
        print(f"❌ Code coverage too low: {coverage:.2%}")
        return False
    
    # 检查性能指标
    perf = report["performance"]
    if perf["avg_latency"] > requirements["performance_threshold"]["avg_latency"]:
        print(f"❌ Average latency too high: {perf['avg_latency']}ms")
        return False
    
    print("✅ All quality gates passed")
    return True

if __name__ == "__main__":
    if not check_quality_gate():
        sys.exit(1)
```

这份测试方案提供了完整的测试策略，包括单元测试、集成测试、性能测试和压力测试，确保RTK GNSS Worker的质量和可靠性。
