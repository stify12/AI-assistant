#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RFID发送功能测试脚本
专注于通过设备名称"HID 413d:2107"查找输入设备并发送RFID码
"""

import time
import logging
import subprocess

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('rfid_test')

def check_adb_available():
    """检查ADB是否可用"""
    try:
        result = subprocess.run("adb version", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ ADB已安装: {result.stdout.splitlines()[0]}")
            return True
        else:
            print("❌ ADB未安装或未在环境变量中")
            print("请安装Android SDK Platform Tools并将其添加到系统PATH中")
            return False
    except Exception as e:
        print(f"检查ADB时发生错误: {e}")
        return False

def try_reconnect_device(device_ip):
    """
    尝试重新连接离线设备
    """
    try:
        print(f"\n尝试重新连接设备 {device_ip}...")
        print("1. 断开现有连接...")
        subprocess.run(f"adb disconnect {device_ip}", shell=True, capture_output=True, text=True)
        
        time.sleep(1)
        
        print("2. 重启ADB服务...")
        subprocess.run("adb kill-server", shell=True, capture_output=True, text=True)
        time.sleep(1)
        start_result = subprocess.run("adb start-server", shell=True, capture_output=True, text=True)
        print(f"ADB服务启动: {start_result.stdout.strip()}")
        
        time.sleep(2)
        
        print(f"3. 重新连接设备 {device_ip}...")
        connect_result = subprocess.run(
            f"adb connect {device_ip}", 
            shell=True, 
            capture_output=True, 
            text=True
        )
        print(f"重新连接结果: {connect_result.stdout.strip()}")
        
        # 等待设备响应
        print("等待设备响应...")
        time.sleep(3)
        
        # 检查连接状态
        devices_result = subprocess.run("adb devices", shell=True, capture_output=True, text=True)
        
        if device_ip in devices_result.stdout and 'device' in devices_result.stdout.split(device_ip)[1]:
            print(f"✓ 设备 {device_ip} 重新连接成功")
            return True
        else:
            print(f"✗ 设备 {device_ip} 重新连接失败")
            print("当前设备状态:")
            print(devices_result.stdout.strip())
            return False
            
    except Exception as e:
        print(f"✗ 重新连接设备时发生错误: {e}")
        return False

def check_device_connected(device_ip):
    """检查设备是否已连接，并在离线时尝试重新连接"""
    try:
        # 先尝试连接设备
        print(f"\n尝试连接设备 {device_ip}...")
        subprocess.run(f"adb connect {device_ip}", shell=True, timeout=5)
        
        # 检查设备是否在列表中
        result = subprocess.run("adb devices", shell=True, capture_output=True, text=True)
        output = result.stdout
        
        print(f"\n当前连接的设备:")
        print(output)
        
        if device_ip in output and 'device' in output.split(device_ip)[1]:
            print(f"✓ 设备 {device_ip} 已成功连接")
            return True
        else:
            # 检查是否为offline状态
            if device_ip in output and 'offline' in output.split(device_ip)[1]:
                print(f"❌ 设备 {device_ip} 已连接但状态为离线 (offline)")
                print("正在尝试自动重新连接...")
                return try_reconnect_device(device_ip)
            else:
                print(f"❌ 设备 {device_ip} 未连接或连接失败")
                return False
    except subprocess.TimeoutExpired:
        print("连接设备超时")
        return False
    except Exception as e:
        print(f"检查设备连接时发生错误: {e}")
        return False

def test_rfid_send():
    """测试RFID发送功能 - 专注于通过设备名称"HID 413d:2107"查找设备"""
    try:
        from rfid_sender import RfidSender
        from config import RFID_DEVICE_PATH
        
        print("\n===== RFID发送功能测试工具 =====")
        print("专注于通过设备名称'HID 413d:2107'查找输入设备")
        print("=" * 50)
        
        # 预检查 - ADB可用性
        if not check_adb_available():
            print("请先安装ADB并重试")
            return
        
        # 获取设备IP
        device_ip = input("\n请输入设备IP (格式: IP:端口，默认为 10.185.247.116): ").strip() or "10.185.247.116"
        
        # 获取测试的RFID码
        rfid_code = input("请输入要发送的RFID码 (默认为 0986485457): ").strip() or "0986485457"
        
        print(f"\n===== 测试信息 =====")
        print(f"设备IP: {device_ip}")
        print(f"当前配置的设备路径: {RFID_DEVICE_PATH}")
        print(f"要发送的RFID码: {rfid_code}")
        print(f"目标设备名称: HID 413d:2107")
        print("=" * 50)
        
        # 检查设备连接
        if not check_device_connected(device_ip):
            print("\n❌ 设备未连接！无法继续测试。")
            print("请按照以下步骤连接设备:")
            print("1. 确保设备已开启并连接到同一网络")
            print("2. 在设备上开启开发者选项和USB调试")
            print("3. 确认设备IP正确且可ping通")
            print("4. 尝试使用命令: adb connect {device_ip}")
            return
        
        # 创建RFID发送器实例
        rfid_sender = RfidSender(device_ip)
        
        # 检测RFID设备（专注于设备名称匹配）
        print(f"\n===== 检测RFID设备 (HID 413d:2107) =====")
        
        # 直接使用按名称查找的方法，提供更清晰的输出
        print("1. 尝试通过设备名称'HID 413d:2107'查找...")
        device_path = rfid_sender.find_rfid_device_by_name()
        
        if device_path:
            print(f"✓ 成功找到设备: {device_path}")
            # 确保更新rfid_sender实例中的设备路径
            rfid_sender.device_path = device_path
            print(f"✓ 已更新设备路径为: {device_path}")
        else:
            print(f"✗ 未找到设备名称为'HID 413d:2107'的设备")
            print("\n2. 尝试自动检测其他可用设备...")
            device_path = rfid_sender.detect_input_device()
        
        # 验证设备路径
        if device_path:
            print(f"\n3. 验证设备路径: {device_path}")
            if rfid_sender.verify_device_path(device_path):
                print(f"✓ 设备路径验证成功")
            else:
                print(f"✗ 设备路径验证失败")
                return
        else:
            print("\n✗ 无法找到有效设备，请检查设备连接和配置")
            return
        
        # 发送测试
        print(f"\n===== 发送RFID码 =====")
        print(f"当前使用设备路径: {rfid_sender.device_path}")
        print(f"即将发送RFID码: {rfid_code}")
        print("\n请确保应用程序正在等待输入")
        print("按下回车键开始发送...")
        input()
        
        print(f"\n正在发送: {rfid_code}...")
        start_time = time.time()
        success = rfid_sender.send_rfid_sequence(rfid_code)
        end_time = time.time()
        
        print(f"\n===== 发送结果 =====")
        print(f"耗时: {end_time - start_time:.2f} 秒")
        if success:
            print(f"✓ RFID码发送成功")
        else:
            print(f"✗ RFID码发送失败")
            print("\n可能的原因:")
            print("1. 设备权限问题")
            print("2. 应用程序未在正确界面")
            print("3. 尝试重启ADB: adb kill-server && adb start-server")
        
    except ImportError as e:
        print(f"✗ 导入模块失败: {e}")
        print("请确保rfid_sender.py和config.py文件存在且正确")
    except Exception as e:
        print(f"✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


    except Exception as e:
        print(f"检查设备连接时发生错误: {e}")
        return False

if __name__ == "__main__":
    print("RFID发送功能测试工具")
    print("-------------------")
    print("此工具帮助诊断和测试RFID码发送功能")
    print("主要检查点: ADB安装、设备连接、RFID设备检测、发送功能")
    print("\n")
    
    try:
        test_rfid_send()
    finally:
        input("\n按回车键退出...")
