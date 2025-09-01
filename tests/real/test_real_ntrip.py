#!/usr/bin/env python3
"""
测试真实NTRIP服务器连接
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rtk-gnss-worker', 'src'))

from config import Config
from ntrip_client import NTRIPClient
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)

def test_real_ntrip():
    """测试真实NTRIP服务器"""
    print("🧪 测试真实NTRIP服务器连接...")
    
    # 使用cankao.py的真实配置
    config_data = {
        'ntrip': {
            'server': '220.180.239.212',
            'port': 7990,
            'username': 'QL_NTRIP',
            'password': '123456',
            'mountpoint': 'HeFei',
            'timeout': 30
        }
    }
    
    config = Config(config_data)
    ntrip_client = NTRIPClient(config.ntrip)
    
    # 测试连接
    if ntrip_client.connect():
        print("✅ NTRIP连接成功！")
        
        # 测试发送GGA和接收RTCM
        gga_string = "$GNGGA,115713.000,3149.301528,N,11706.920684,E,1,17,0.88,98.7,M,-3.6,M,,*58"
        
        for i in range(3):
            print(f"\n📡 第{i+1}次数据交换:")
            
            # 发送GGA
            success = ntrip_client.send_gga(gga_string)
            print(f"   发送GGA: {'成功' if success else '失败'}")
            
            # 接收RTCM
            rtcm_data = ntrip_client.receive_rtcm(timeout=2.0)
            if rtcm_data:
                print(f"   接收RTCM: {len(rtcm_data)} 字节")
                hex_str = ' '.join(format(b, '02x') for b in rtcm_data[:20]).upper()
                print(f"   数据预览: {hex_str}...")
            else:
                print("   接收RTCM: 无数据")
        
        ntrip_client.disconnect()
        print("✅ 测试完成")
        
    else:
        print("❌ NTRIP连接失败")

if __name__ == "__main__":
    test_real_ntrip()
