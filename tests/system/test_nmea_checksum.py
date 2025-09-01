#!/usr/bin/env python3
"""
测试NMEA校验和计算
"""

def add_nmea_checksum(nmea_sentence):
    """为NMEA语句添加校验和"""
    # 移除开头的$符号进行校验和计算
    if nmea_sentence.startswith('$'):
        sentence_for_checksum = nmea_sentence[1:]
    else:
        sentence_for_checksum = nmea_sentence
    
    # 计算校验和
    checksum = 0
    for char in sentence_for_checksum:
        checksum ^= ord(char)
    
    # 返回带校验和的完整语句
    return f"{nmea_sentence}*{checksum:02X}"

def test_nmea_checksum():
    """测试NMEA校验和"""
    test_cases = [
        "$GPGGA,073543.912,3958.7758,N,11619.4832,E,2,08,1.0,546.4,M,46.9,M,2.0,0000",
        "$GPRMC,073544.912,A,3958.7758,N,11619.4832,E,0.0,0.0,280825,0.0,E,D",
        "$GPGSA,A,3,01,02,03,04,05,06,07,08,,,,,1.0,1.0,1.0"
    ]
    
    for sentence in test_cases:
        with_checksum = add_nmea_checksum(sentence)
        print(f"Original: {sentence}")
        print(f"With checksum: {with_checksum}")
        print()

if __name__ == "__main__":
    test_nmea_checksum()
