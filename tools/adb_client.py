#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ADB 客户端 - 连接服务器 WebSocket，执行 RFID 模拟命令
运行在本地电脑上，通过 ADB 连接被控安卓设备
"""

import json
import time
import subprocess
import threading
import logging
import argparse
import uuid
import socket
from datetime import datetime

try:
    import websocket
except ImportError:
    print("请安装 websocket-client: pip install websocket-client")
    exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('adb_client')


class AdbClient:
    """ADB 客户端"""
    
    # RFID 事件映射表
    RFID_EVENT_MAP = {
        '0': [(4, 2, 458783), (1, 11, 1), (0, 0, 0), (4, 2, 458783), (1, 11, 0), (0, 0, 0)],
        '1': [(4, 2, 458774), (1, 2, 1), (0, 0, 0), (4, 2, 458774), (1, 2, 0), (0, 0, 0)],
        '2': [(4, 2, 458775), (1, 3, 1), (0, 0, 0), (4, 2, 458775), (1, 3, 0), (0, 0, 0)],
        '3': [(4, 2, 458776), (1, 4, 1), (0, 0, 0), (4, 2, 458776), (1, 4, 0), (0, 0, 0)],
        '4': [(4, 2, 458777), (1, 5, 1), (0, 0, 0), (4, 2, 458777), (1, 5, 0), (0, 0, 0)],
        '5': [(4, 2, 458778), (1, 6, 1), (0, 0, 0), (4, 2, 458778), (1, 6, 0), (0, 0, 0)],
        '6': [(4, 2, 458779), (1, 7, 1), (0, 0, 0), (4, 2, 458779), (1, 7, 0), (0, 0, 0)],
        '7': [(4, 2, 458780), (1, 8, 1), (0, 0, 0), (4, 2, 458780), (1, 8, 0), (0, 0, 0)],
        '8': [(4, 2, 458781), (1, 9, 1), (0, 0, 0), (4, 2, 458781), (1, 9, 0), (0, 0, 0)],
        '9': [(4, 2, 458782), (1, 10, 1), (0, 0, 0), (4, 2, 458782), (1, 10, 0), (0, 0, 0)],
        'enter': [(4, 2, 458784), (1, 28, 1), (0, 0, 0), (4, 2, 458784), (1, 28, 0), (0, 0, 0)]
    }
    
    def __init__(self, server_url: str, device_ip: str):
        """
        初始化 ADB 客户端
        
        Args:
            server_url: WebSocket 服务器地址 (如 ws://47.82.64.147:5000/ws/rfid-simulator)
            device_ip: 被控安卓设备 IP (如 10.185.247.116)
        """
        self.server_url = server_url
        self.device_ip = device_ip
        self.client_id = f"adb_{uuid.uuid4().hex[:8]}"
        self.ws = None
        self.running = False
        self.paused = False
        self.current_task = None
        self.device_path = "/dev/input/event2"
        self._heartbeat_running = False  # 心跳线程控制标志
        self._cached_device_info = None  # 缓存的设备信息
        
    def get_local_ip(self) -> str:
        """获取本机 IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "unknown"
    
    def check_adb_connection(self) -> bool:
        """检查 ADB 连接"""
        try:
            # 尝试连接设备
            result = subprocess.run(
                f"adb connect {self.device_ip}",
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=10
            )
            
            # 检查设备状态
            result = subprocess.run(
                "adb devices",
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=5
            )
            
            if self.device_ip in result.stdout and 'device' in result.stdout:
                logger.info(f"ADB 设备已连接: {self.device_ip}")
                return True
            else:
                logger.warning(f"ADB 设备未连接: {self.device_ip}")
                return False
        except Exception as e:
            logger.error(f"检查 ADB 连接失败: {e}")
            return False
    
    def get_device_info(self) -> dict:
        """获取设备信息"""
        info = {
            'device_ip': self.device_ip,
            'device_path': self.device_path,
            'connected': False,
            'model': 'unknown'
        }
        
        try:
            # 获取设备型号
            result = subprocess.run(
                f"adb -s {self.device_ip} shell getprop ro.product.model",
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=5
            )
            if result.returncode == 0:
                info['model'] = result.stdout.strip()
                info['connected'] = True
        except:
            pass
        
        return info
    
    def detect_rfid_device(self) -> str:
        """检测 RFID 输入设备"""
        try:
            target_name = "HID 413d:2107"
            logger.info(f"检测 RFID 设备: {target_name}")
            
            # 获取所有输入设备
            cmd = f"adb -s {self.device_ip} shell find /dev/input -name 'event*'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=10)
            
            device_paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            
            # 检查每个设备
            for device_path in device_paths:
                try:
                    cmd = f"adb -s {self.device_ip} shell getevent -i {device_path}"
                    info_result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=5)
                    
                    for line in info_result.stdout.splitlines():
                        if 'name:' in line and target_name in line:
                            logger.info(f"找到 RFID 设备: {device_path}")
                            self.device_path = device_path
                            return device_path
                except:
                    continue
            
            logger.warning("未找到 RFID 设备，使用默认路径")
            return self.device_path
        except Exception as e:
            logger.error(f"检测设备失败: {e}")
            return self.device_path
    
    def build_char_command(self, char: str, device_path: str) -> str:
        """构建单个字符的 sendevent 命令"""
        if char not in self.RFID_EVENT_MAP:
            return None
        
        events = []
        for event in self.RFID_EVENT_MAP[char]:
            type_code, code, value = event
            events.append(f"sendevent {device_path} {type_code} {code} {value}")
        
        return "; ".join(events)
    
    def send_rfid(self, rfid_code: str, device_path: str = None, 
                  send_enter: bool = True, inter_char_delay: float = 0.005,
                  enter_delay: float = 0.05) -> bool:
        """
        发送 RFID 卡号
        
        Args:
            rfid_code: RFID 卡号
            device_path: 输入设备路径
            send_enter: 是否发送回车
            inter_char_delay: 字符间延迟（秒）
            enter_delay: 回车前延迟（秒）
        """
        device_path = device_path or self.device_path
        
        try:
            logger.info(f"发送 RFID: {rfid_code}")
            
            # 发送每个字符
            for i, char in enumerate(rfid_code):
                cmd = self.build_char_command(char, device_path)
                if not cmd:
                    logger.warning(f"跳过未知字符: {char}")
                    continue
                
                result = subprocess.run(
                    f"adb -s {self.device_ip} shell \"{cmd}\"",
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=3
                )
                
                if result.returncode != 0:
                    logger.error(f"字符 {char} 发送失败: {result.stderr}")
                    return False
                
                # 字符间延迟
                if i < len(rfid_code) - 1:
                    time.sleep(inter_char_delay)
            
            # 发送回车
            if send_enter:
                time.sleep(enter_delay)
                enter_cmd = self.build_char_command('enter', device_path)
                result = subprocess.run(
                    f"adb -s {self.device_ip} shell \"{enter_cmd}\"",
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    timeout=3
                )
                
                if result.returncode != 0:
                    logger.error(f"回车发送失败: {result.stderr}")
                    return False
            
            logger.info(f"RFID 发送成功: {rfid_code}")
            return True
        except Exception as e:
            logger.error(f"发送 RFID 失败: {e}")
            return False
    
    def on_message(self, ws, message):
        """处理服务器消息"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'registered':
                logger.info(f"注册成功: {data.get('message')}")
            
            elif msg_type == 'heartbeat_ack':
                pass  # 心跳确认
            
            elif msg_type == 'test_connection':
                # 测试连接
                success = self.check_adb_connection()
                self.ws.send(json.dumps({
                    'type': 'connection_test_result',
                    'success': success,
                    'error': '' if success else 'ADB 设备未连接'
                }))
            
            elif msg_type == 'detect_device':
                # 检测设备
                device_path = self.detect_rfid_device()
                self.ws.send(json.dumps({
                    'type': 'device_detected',
                    'device_path': device_path,
                    'device_name': 'HID 413d:2107' if device_path else ''
                }))
            
            elif msg_type == 'send_rfid':
                # 发送单个 RFID
                rfid_code = data.get('rfid_code')
                commands = data.get('commands', [])
                inter_char_delay = data.get('inter_char_delay', 0.005)
                enter_delay = data.get('enter_delay', 0.05)
                
                success = self.send_rfid(
                    rfid_code, 
                    self.device_path,
                    True,
                    inter_char_delay,
                    enter_delay
                )
                
                self.ws.send(json.dumps({
                    'type': 'result',
                    'success': success,
                    'rfid_code': rfid_code,
                    'name': '',
                    'error': '' if success else '发送失败'
                }))
            
            elif msg_type == 'batch_start':
                # 开始批量模拟
                self.current_task = data
                self.paused = False
                threading.Thread(target=self.run_batch_task, daemon=True).start()
            
            elif msg_type == 'batch_pause':
                self.paused = True
                logger.info("批量任务已暂停")
            
            elif msg_type == 'batch_resume':
                self.paused = False
                logger.info("批量任务已恢复")
            
            elif msg_type == 'batch_stop':
                self.current_task = None
                self.paused = False
                logger.info("批量任务已停止")
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            self.ws.send(json.dumps({
                'type': 'error',
                'error': str(e)
            }))
    
    def run_batch_task(self):
        """执行批量任务"""
        if not self.current_task:
            return
        
        cards = self.current_task.get('cards', [])
        interval_seconds = self.current_task.get('interval_seconds', 5)
        send_enter = self.current_task.get('send_enter', True)
        device_path = self.current_task.get('device_path', self.device_path)
        inter_char_delay = self.current_task.get('inter_char_delay', 0.005)
        enter_delay = self.current_task.get('enter_delay', 0.05)
        
        logger.info(f"开始批量任务: {len(cards)} 张卡片, 间隔 {interval_seconds}s")
        
        for i, card in enumerate(cards):
            # 检查是否停止
            if self.current_task is None:
                logger.info("批量任务已停止")
                return
            
            # 检查是否暂停
            while self.paused and self.current_task is not None:
                time.sleep(0.5)
            
            if self.current_task is None:
                return
            
            rfid_code = card.get('cardNumber', card.get('rfid_code', ''))
            name = card.get('name', '')
            
            logger.info(f"[{i+1}/{len(cards)}] 发送: {name} ({rfid_code})")
            
            # 发送进度
            self.ws.send(json.dumps({
                'type': 'batch_progress',
                'current_index': i,
                'status': 'running'
            }))
            
            # 发送 RFID
            success = self.send_rfid(rfid_code, device_path, send_enter, inter_char_delay, enter_delay)
            
            # 发送结果
            self.ws.send(json.dumps({
                'type': 'result',
                'success': success,
                'rfid_code': rfid_code,
                'name': name,
                'current_index': i,
                'error': '' if success else '发送失败'
            }))
            
            # 等待间隔
            if i < len(cards) - 1 and self.current_task is not None:
                for _ in range(interval_seconds * 10):
                    if self.current_task is None:
                        return
                    if self.paused:
                        break
                    time.sleep(0.1)
        
        # 完成
        if self.current_task is not None:
            self.ws.send(json.dumps({
                'type': 'batch_complete'
            }))
            logger.info("批量任务完成")
        
        self.current_task = None
    
    def on_error(self, ws, error):
        """处理错误"""
        self._heartbeat_running = False  # 停止心跳
        logger.error(f"WebSocket 错误: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """连接关闭"""
        self._heartbeat_running = False  # 停止心跳
        logger.info(f"WebSocket 连接关闭: {close_status_code} - {close_msg}")
    
    def on_open(self, ws):
        """连接建立"""
        logger.info("WebSocket 连接已建立")
        self._heartbeat_running = True
        
        # 发送注册消息（只在注册时获取设备信息）
        device_info = self.get_device_info()
        self._cached_device_info = device_info  # 缓存设备信息
        ws.send(json.dumps({
            'type': 'register',
            'client_id': self.client_id,
            'ip_address': self.get_local_ip(),
            'device_info': device_info
        }))
        
        # 启动心跳线程 - 15秒间隔，不调用 ADB 命令
        def heartbeat():
            heartbeat_count = 0
            while self.running and self._heartbeat_running:
                try:
                    heartbeat_count += 1
                    # 使用缓存的设备信息，不每次调用 ADB
                    ws.send(json.dumps({
                        'type': 'heartbeat',
                        'device_info': self._cached_device_info,
                        'seq': heartbeat_count
                    }))
                    if heartbeat_count % 4 == 0:  # 每分钟打印一次
                        logger.info(f"心跳 #{heartbeat_count} 已发送")
                except Exception as e:
                    logger.warning(f"心跳发送失败: {e}")
                    self._heartbeat_running = False
                    break
                time.sleep(15)  # 15秒心跳间隔
        
        threading.Thread(target=heartbeat, daemon=True).start()
    
    def on_close(self, ws, close_status_code, close_msg):
        """连接关闭"""
        self._heartbeat_running = False  # 停止心跳
        logger.info(f"WebSocket 连接关闭: {close_status_code} - {close_msg}")
        self.running = False
    
    def connect(self):
        """连接服务器（带自动重连）"""
        logger.info(f"连接服务器: {self.server_url}")
        logger.info(f"被控设备: {self.device_ip}")
        
        # 检查 ADB 连接
        if not self.check_adb_connection():
            logger.warning("ADB 设备未连接，将继续尝试...")
        
        # 检测 RFID 设备
        self.detect_rfid_device()
        
        self.running = True
        reconnect_delay = 2  # 初始重连延迟
        max_delay = 15  # 最大重连延迟（缩短）
        consecutive_failures = 0
        
        while self.running:
            try:
                logger.info("正在建立 WebSocket 连接...")
                self.ws = websocket.WebSocketApp(
                    self.server_url,
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close
                )
                # 运行 WebSocket
                # 注意：禁用 WebSocket 协议级 ping，完全依赖应用层心跳
                # 避免与服务端 flask-sock 的 ping 机制冲突
                self.ws.run_forever(
                    ping_interval=0,       # 禁用协议级 ping
                    ping_timeout=None      # 不使用 ping 超时
                )
                reconnect_delay = 2  # 重置延迟
                consecutive_failures = 0
            except Exception as e:
                logger.error(f"WebSocket 运行错误: {e}")
                consecutive_failures += 1
            
            if self.running:
                # 连续失败多次时检查 ADB 连接
                if consecutive_failures >= 3:
                    logger.info("连续失败，重新检查 ADB 连接...")
                    self.check_adb_connection()
                    consecutive_failures = 0
                
                logger.info(f"{reconnect_delay:.1f} 秒后重新连接...")
                time.sleep(reconnect_delay)
                # 指数退避，但不超过最大延迟
                reconnect_delay = min(reconnect_delay * 1.5, max_delay)


def main():
    parser = argparse.ArgumentParser(description='ADB 客户端 - RFID 模拟器')
    parser.add_argument('--server', '-s', default='ws://47.82.64.147:5000/ws/rfid-simulator',
                        help='WebSocket 服务器地址')
    parser.add_argument('--device', '-d', default='192.168.4.143',
                        help='被控安卓设备 IP')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("ADB 客户端 - RFID 模拟器")
    print("=" * 50)
    print(f"本地电脑: 192.168.4.200")
    print(f"服务器: {args.server}")
    print(f"被控设备: {args.device}")
    print("=" * 50)
    print("按 Ctrl+C 退出")
    print()
    
    client = AdbClient(args.server, args.device)
    
    try:
        client.connect()
    except KeyboardInterrupt:
        print("\n正在退出...")
        client.running = False


if __name__ == '__main__':
    main()
