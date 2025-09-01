# 接口规范

## 1. 对外接口规范

### 1.1 主接口 - GNSSWorker

#### 构造函数

```python
class GNSSWorker:
    def __init__(self, config: Config):
        """
        初始化GNSS工作器
        
        Args:
            config: 配置对象
            
        Raises:
            Exception: 配置无效或组件初始化失败时抛出
        """
```

#### 生命周期管理

```python
def start(self) -> None:
    """
    启动GNSS工作器
    
    连接NTRIP服务器和串口/TCP，开始数据处理
    
    Raises:
        Exception: 启动过程中发生错误
    """

def stop(self) -> None:
    """
    停止GNSS工作器
    
    清理所有连接和资源
    """

def run_once(self) -> bool:
    """
    执行一次工作循环
    
    Returns:
        bool: True表示可以继续运行，False表示应该停止
    """
    检查工作器是否正在运行
    
    Returns:
        bool: True if running, False otherwise
    """
```

#### 状态查询

```python
def get_status(self) -> WorkerStatusInfo:
    """
    获取当前工作状态
    
    Returns:
        WorkerStatusInfo: 包含详细状态信息的对象
    """

def get_metrics(self) -> WorkerMetrics:
    """
    获取运行指标
    
    Returns:
        WorkerMetrics: 包含运行统计信息的对象
    """

def get_last_location(self) -> Optional[LocationData]:
    """
    获取最后一次定位数据
    
    Returns:
        LocationData or None: 最后的定位数据，如果没有则返回None
    """
```

### 1.2 数据模型

#### LocationData

```python
@dataclass
class LocationData:
    """定位数据模型"""
    timestamp: datetime          # 时间戳
    latitude: float             # 纬度（十进制度）
    longitude: float            # 经度（十进制度）
    altitude: float             # 海拔高度（米）
    quality: int                # 定位质量（0-9）
    satellites: int             # 可见卫星数量
    hdop: float                 # 水平精度因子
    raw_nmea: str              # 原始NMEA数据
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        
    def to_json(self) -> str:
        """转换为JSON字符串"""
        
    @classmethod
    def from_dict(cls, data: dict) -> 'LocationData':
        """从字典创建对象"""
```

#### WorkerStatusInfo

```python
@dataclass
class WorkerStatusInfo:
    """工作器状态信息"""
    status: WorkerStatus        # 当前状态
    start_time: Optional[datetime]  # 启动时间
    uptime: Optional[timedelta]     # 运行时长
    ntrip_connected: bool       # NTRIP连接状态
    serial_connected: bool      # 串口连接状态
    last_error: Optional[str]   # 最后错误信息
    error_count: int           # 错误计数
    
class WorkerStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPING = "stopping"
```

#### WorkerMetrics

```python
@dataclass
class WorkerMetrics:
    """运行指标"""
    rtcm_received_count: int         # RTCM接收计数
    rtcm_bytes_received: int         # RTCM接收字节数
    nmea_processed_count: int        # NMEA处理计数
    location_published_count: int    # 位置发布计数
    error_count: int                 # 错误计数
    last_rtcm_time: Optional[datetime]    # 最后RTCM时间
    last_location_time: Optional[datetime] # 最后定位时间
    memory_usage_mb: float           # 内存使用量（MB）
    cpu_usage_percent: float         # CPU使用率（%）
```

### 1.3 回调接口

#### LocationCallback

```python
class LocationCallback(Protocol):
    """位置数据回调接口"""
    
    def __call__(self, location: LocationData) -> bool:
        """
        处理位置数据
        
        Args:
            location: 位置数据
            
        Returns:
            bool: True表示处理成功，False表示处理失败
        """

# 使用示例
def my_location_handler(location: LocationData) -> bool:
    print(f"New location: {location.latitude}, {location.longitude}")
    return True

worker = GNSSWorker(config)
worker.set_location_callback(my_location_handler)
```

#### StatusCallback

```python
class StatusCallback(Protocol):
    """状态变化回调接口"""
    
    def __call__(self, old_status: WorkerStatus, new_status: WorkerStatus) -> None:
        """
        处理状态变化
        
        Args:
            old_status: 旧状态
            new_status: 新状态
        """

# 使用示例
def status_change_handler(old_status: WorkerStatus, new_status: WorkerStatus) -> None:
    print(f"Status changed: {old_status} -> {new_status}")

worker.set_status_callback(status_change_handler)
```

### 1.4 异常定义

```python
class GNSSWorkerError(Exception):
    """GNSS工作器基础异常"""
    pass

class ConfigurationError(GNSSWorkerError):
    """配置错误"""
    pass

class ConnectionError(GNSSWorkerError):
    """连接错误"""
    pass

class ComponentError(GNSSWorkerError):
    """组件错误"""
    pass

class StartupError(GNSSWorkerError):
    """启动错误"""
    pass

class AlreadyRunningError(GNSSWorkerError):
    """已经在运行错误"""
    pass
```

## 2. 配置接口规范

### 2.1 配置文件格式

#### JSON配置示例

```json
{
  "ntrip": {
    "server": "220.180.239.212",
    "port": 7990,
    "username": "QL_NTRIP",
    "password": "123456",
    "mountpoint": "HeFei",
    "timeout": 30.0,
    "keepalive_interval": 30.0,
    "retry_attempts": 10,
    "retry_delay": 1.0
  },
  "serial": {
    "port": "/dev/ttyUSB0",
    "baudrate": 115200,
    "timeout": 1.0,
    "bytesize": 8,
    "parity": "N",
    "stopbits": 1
  },
  "output": {
    "type": "file",
    "file_path": "/tmp/gnss_location.json",
    "atomic_write": true,
    "backup_count": 5
  },
  "logging": {
    "level": "INFO",
    "file_path": "/var/log/gnss_worker.log",
    "max_size": "10MB",
    "backup_count": 5,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  },
  "health_check": {
    "enabled": true,
    "interval": 60.0,
    "timeout": 5.0
  }
}
```

### 2.2 环境变量配置

| 环境变量名 | 说明 | 示例值 |
|-----------|------|--------|
| GNSS_NTRIP_SERVER | NTRIP服务器地址 | 220.180.239.212 |
| GNSS_NTRIP_PORT | NTRIP服务器端口 | 7990 |
| GNSS_NTRIP_USERNAME | NTRIP用户名 | QL_NTRIP |
| GNSS_NTRIP_PASSWORD | NTRIP密码 | 123456 |
| GNSS_NTRIP_MOUNTPOINT | NTRIP挂载点 | HeFei |
| GNSS_SERIAL_PORT | 串口设备 | /dev/ttyUSB0 |
| GNSS_SERIAL_BAUDRATE | 串口波特率 | 115200 |
| GNSS_OUTPUT_FILE | 输出文件路径 | /tmp/gnss_location.json |
| GNSS_LOG_LEVEL | 日志级别 | INFO |
| GNSS_LOG_FILE | 日志文件路径 | /var/log/gnss_worker.log |

### 2.3 配置验证

```python
class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate(config: Config) -> List[str]:
        """
        验证配置
        
        Args:
            config: 待验证的配置
            
        Returns:
            List[str]: 验证错误列表，空列表表示验证通过
        """
        
    @staticmethod
    def validate_ntrip_config(config: NTRIPConfig) -> List[str]:
        """验证NTRIP配置"""
        
    @staticmethod
    def validate_serial_config(config: SerialConfig) -> List[str]:
        """验证串口配置"""
```

## 3. 内部接口规范

### 3.1 组件间通信接口

#### 数据队列接口

```python
class DataQueue(Protocol):
    """数据队列接口"""
    
    async def put(self, item: Any, timeout: Optional[float] = None) -> None:
        """放入数据"""
        
    async def get(self, timeout: Optional[float] = None) -> Any:
        """获取数据"""
        
    def qsize(self) -> int:
        """队列大小"""
        
    def empty(self) -> bool:
        """是否为空"""
        
    def full(self) -> bool:
        """是否已满"""
```

#### 事件接口

```python
class EventBus:
    """事件总线"""
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """订阅事件"""
        
    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """取消订阅"""
        
    async def publish(self, event_type: str, data: Any) -> None:
        """发布事件"""

# 事件类型定义
class EventType:
    NTRIP_CONNECTED = "ntrip.connected"
    NTRIP_DISCONNECTED = "ntrip.disconnected"
    SERIAL_OPENED = "serial.opened"
    SERIAL_CLOSED = "serial.closed"
    RTCM_RECEIVED = "rtcm.received"
    NMEA_RECEIVED = "nmea.received"
    LOCATION_UPDATED = "location.updated"
    ERROR_OCCURRED = "error.occurred"
```

### 3.2 组件生命周期接口

```python
class Component(Protocol):
    """组件基础接口"""
    
    async def initialize(self) -> bool:
        """初始化组件"""
        
    async def start(self) -> bool:
        """启动组件"""
        
    async def stop(self) -> bool:
        """停止组件"""
        
    async def cleanup(self) -> None:
        """清理资源"""
        
    def get_status(self) -> ComponentStatus:
        """获取组件状态"""
        
    def get_health(self) -> HealthStatus:
        """获取健康状态"""

class ComponentStatus(Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
```

## 4. 扩展接口规范

### 4.1 发布器扩展接口

```python
class LocationPublisher(Protocol):
    """位置发布器接口"""
    
    async def initialize(self) -> bool:
        """初始化发布器"""
        
    async def publish(self, location: LocationData) -> bool:
        """发布位置数据"""
        
    async def cleanup(self) -> None:
        """清理资源"""

# 内置发布器实现
class FilePublisher(LocationPublisher):
    """文件发布器"""
    
class CallbackPublisher(LocationPublisher):
    """回调发布器"""
    
class SocketPublisher(LocationPublisher):
    """Socket发布器"""
    
class MQTTPublisher(LocationPublisher):
    """MQTT发布器"""
```

### 4.2 解析器扩展接口

```python
class DataParser(Protocol):
    """数据解析器接口"""
    
    def can_parse(self, data: str) -> bool:
        """检查是否能解析该数据"""
        
    def parse(self, data: str) -> Optional[LocationData]:
        """解析数据"""

# 内置解析器实现
class NMEAParser(DataParser):
    """NMEA解析器"""
    
class UBXParser(DataParser):
    """UBX格式解析器"""
```

### 4.3 健康检查接口

```python
class HealthChecker(Protocol):
    """健康检查接口"""
    
    async def check_health(self) -> HealthResult:
        """执行健康检查"""

@dataclass
class HealthResult:
    """健康检查结果"""
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime

class HealthCheckerRegistry:
    """健康检查器注册表"""
    
    def register(self, name: str, checker: HealthChecker) -> None:
        """注册健康检查器"""
        
    def unregister(self, name: str) -> None:
        """注销健康检查器"""
        
    async def check_all(self) -> Dict[str, HealthResult]:
        """执行所有健康检查"""
```

## 5. API使用示例

### 5.1 基本使用

```python
import asyncio
from gnss_worker import GNSSWorker, Config

async def main():
    # 从配置文件创建
    config = Config.from_file('config.json')
    worker = GNSSWorker(config)
    
    try:
        # 启动工作器
        await worker.start()
        
        # 运行一段时间
        await asyncio.sleep(60)
        
        # 获取状态
        status = worker.get_status()
        print(f"Status: {status.status}")
        
        # 获取最后位置
        location = worker.get_last_location()
        if location:
            print(f"Location: {location.latitude}, {location.longitude}")
            
    finally:
        # 停止工作器
        await worker.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### 5.2 回调使用

```python
def location_callback(location: LocationData) -> bool:
    """位置数据回调"""
    print(f"New location: {location.to_json()}")
    return True

def status_callback(old_status: WorkerStatus, new_status: WorkerStatus) -> None:
    """状态变化回调"""
    print(f"Status changed: {old_status} -> {new_status}")

async def main():
    config = Config.from_file('config.json')
    worker = GNSSWorker(config)
    
    # 设置回调
    worker.set_location_callback(location_callback)
    worker.set_status_callback(status_callback)
    
    await worker.start()
    # ... 运行逻辑
```

### 5.3 健康监控

```python
async def monitor_health():
    """健康监控示例"""
    worker = GNSSWorker(config)
    
    await worker.start()
    
    while True:
        status = worker.get_status()
        metrics = worker.get_metrics()
        
        # 检查连接状态
        if not status.ntrip_connected:
            print("WARNING: NTRIP disconnected")
            
        # 检查数据新鲜度
        if metrics.last_location_time:
            age = datetime.now() - metrics.last_location_time
            if age.total_seconds() > 60:
                print("WARNING: Location data is stale")
        
        await asyncio.sleep(30)
```

这份接口规范文档详细定义了RTK GNSS Worker的所有对外和内部接口，为使用者和扩展开发者提供了清晰的指导。
