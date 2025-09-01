#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的虚拟串口GNSS模拟器
创建一对虚拟串口，主程序读tty1，模拟器写tty2
"""

import os
import time
import random
import subprocess
import signal
import sys
import threading
from datetime import datetime, timezone

def calculate_checksum(sentence):
    """计算NMEA校验和"""
    # 计算$符号后到*符号前的所有字符的XOR
    checksum = 0
    for char in sentence:
        checksum ^= ord(char)
    return f"{checksum:02X}"

def generate_gga():
    """生成GGA语句"""
    now = datetime.now(timezone.utc)
    time_str = now.strftime("%H%M%S.%f")[:-3]
    
    # 合肥位置 + 随机偏移模拟移动
    lat = 31.82057 + random.uniform(-0.0001, 0.0001)
    lon = 117.11530 + random.uniform(-0.0001, 0.0001)
    
    # 转换为度分格式
    lat_deg = int(lat)
    lat_min = (lat - lat_deg) * 60
    lat_str = f"{lat_deg:02d}{lat_min:07.4f}"
    
    lon_deg = int(lon)
    lon_min = (lon - lon_deg) * 60
    lon_str = f"{lon_deg:03d}{lon_min:07.4f}"
    
    # RTK固定解
    quality = "4"
    num_sats = random.randint(12, 20)
    hdop = random.uniform(0.5, 1.2)
    altitude = 50.0 + random.uniform(-0.5, 0.5)
    
    sentence = f"GNGGA,{time_str},{lat_str},N,{lon_str},E,{quality},{num_sats},{hdop:.1f},{altitude:.1f},M,-3.2,M,1.5,0001"
    checksum = calculate_checksum(sentence)
    return f"${sentence}*{checksum}"

def read_monitor_thread(tty_path):
    """监控线程：读取串口数据验证传输"""
    try:
        print(f"🔍 开始监控 {tty_path} 接收差分数据...")
        
        # 等待串口文件出现
        while not os.path.exists(tty_path):
            time.sleep(0.1)
        
        with open(tty_path, 'rb') as f:  # 用二进制模式读取
            buffer = b''
            while True:
                chunk = f.read(1024)
                if chunk:
                    buffer += chunk
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    
                    # 尝试检测数据类型
                    try:
                        # 尝试解码为文本（NMEA数据）
                        text_data = chunk.decode('ascii', errors='ignore')
                        lines = text_data.split('\n')
                        
                        has_nmea = False
                        has_binary = False
                        
                        for line in lines:
                            if line.strip().startswith('$') and '*' in line:
                                print(f"� [{timestamp}] NMEA回环: {line.strip()}")
                                has_nmea = True
                            elif len(line.strip()) > 0:
                                has_binary = True
                        
                        # 如果有二进制数据，显示为RTCM
                        if has_binary or any(b > 127 for b in chunk):
                            hex_preview = chunk[:20].hex()
                            print(f"📥 [{timestamp}] 收到RTCM差分数据: {len(chunk)}字节 | {hex_preview}...")
                    
                    except:
                        # 纯二进制数据
                        hex_preview = chunk[:20].hex()
                        print(f"📥 [{timestamp}] 收到RTCM差分数据: {len(chunk)}字节 | {hex_preview}...")
                
                else:
                    time.sleep(0.1)
                    
    except Exception as e:
        print(f"❌ 监控线程错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🛰️ 简单虚拟串口GNSS模拟器")
    print("=" * 40)
    
    # 检查socat
    try:
        subprocess.check_output(['which', 'socat'])
    except:
        print("❌ 需要安装socat:")
        print("   Ubuntu/Debian: sudo apt-get install socat")
        print("   CentOS/RHEL:   sudo yum install socat")
        return
    
    # 创建虚拟串口对
    tty1 = "/tmp/ttyGNSS1"
    tty2 = "/tmp/ttyGNSS2"
    
    print(f"🔗 创建虚拟串口对:")
    print(f"   📥 主程序读取: {tty1}")
    print(f"   📤 模拟器写入: {tty2}")
    
    # 启动socat创建串口对
    socat_cmd = [
        'socat', 
        f'pty,raw,echo=0,link={tty1}',
        f'pty,raw,echo=0,link={tty2}'
    ]
    
    socat_process = subprocess.Popen(socat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 等待串口文件创建
    for _ in range(50):  # 最多等待5秒
        if os.path.exists(tty1) and os.path.exists(tty2):
            break
        time.sleep(0.1)
    else:
        print("❌ 虚拟串口创建失败")
        socat_process.terminate()
        return
    
    print("✅ 虚拟串口创建成功")
    print(f"💡 在另一个终端运行: python3 start.py")
    print(f"💡 记得修改config.json的串口为: {tty1}")
    print("📡 开始发送GNSS数据...")
    print("🔍 同时监控差分数据接收...")
    print("-" * 40)
    
    # 启动监控线程读取tty1验证数据传输
    monitor_thread = threading.Thread(target=read_monitor_thread, args=(tty2,), daemon=True)
    monitor_thread.start()
    time.sleep(0.5)  # 让监控线程先启动
    
    def cleanup(signum, frame):
        print("\n🛑 停止模拟器...")
        try:
            socat_process.terminate()
            socat_process.wait(timeout=2)
        except:
            socat_process.kill()
        print("✅ 清理完成")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        with open(tty2, 'w') as f:
            count = 0
            while True:
                # 生成NMEA数据
                gga = generate_gga()
                
                # 写入串口
                f.write(gga + '\r\n')
                f.flush()
                
                count += 1
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"📤 [{timestamp}] send {gga}")
                
                time.sleep(1)  # 1Hz更新
                
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        cleanup(None, None)

if __name__ == "__main__":
    main()
