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
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional, List, Dict, Tuple

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
        self._ui_cache = None  # 缓存的 UI 结构
        self._ui_cache_time = 0  # UI 缓存时间
        
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
        发送 RFID 卡号（批量模式：所有 sendevent 合并为一条 shell 命令）
        
        Args:
            rfid_code: RFID 卡号（纯数字）
            device_path: 输入设备路径
            send_enter: 是否发送回车
            inter_char_delay: 未使用（保留参数兼容）
            enter_delay: 未使用（保留参数兼容）
        """
        device_path = device_path or self.device_path
        
        # 参数校验
        if not rfid_code or not rfid_code.strip():
            logger.error("RFID 卡号为空")
            return False
        
        rfid_code = rfid_code.strip()
        
        # 检查是否包含不支持的字符
        for char in rfid_code:
            if char not in self.RFID_EVENT_MAP:
                logger.error(f"卡号包含不支持的字符: '{char}'，卡号: {rfid_code}")
                return False
        
        try:
            logger.info(f"发送 RFID: {rfid_code}")
            
            # 构建所有字符（含回车）的 sendevent，合并为一条命令
            all_events = []
            for char in rfid_code:
                for event in self.RFID_EVENT_MAP[char]:
                    type_code, code, value = event
                    all_events.append(f"sendevent {device_path} {type_code} {code} {value}")
            
            # 追加回车
            if send_enter:
                for event in self.RFID_EVENT_MAP['enter']:
                    type_code, code, value = event
                    all_events.append(f"sendevent {device_path} {type_code} {code} {value}")
            
            # 用 ";" 拼接成一条 shell 命令，一次 adb 调用完成
            batch_cmd = "; ".join(all_events)
            
            result = subprocess.run(
                f"adb -s {self.device_ip} shell \"{batch_cmd}\"",
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"RFID 批量发送失败: {result.stderr}")
                return False
            
            logger.info(f"RFID 发送成功: {rfid_code}")
            return True
        except subprocess.TimeoutExpired:
            logger.error(f"RFID 发送超时: {rfid_code}")
            return False
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
            
            elif msg_type == 'run_workflow':
                # 执行完整流程（发布+提交联动）
                self.current_task = data
                self.paused = False
                threading.Thread(target=self.run_full_workflow, daemon=True).start()
            
            elif msg_type == 'workflow_step':
                # 处理工作流步骤
                self.handle_workflow_step(data)
            
            elif msg_type == 'dump_ui':
                # 导出 UI 结构
                summary = self.get_ui_summary()
                self.ws.send(json.dumps({
                    'type': 'ui_dump_result',
                    **summary
                }))
            
            elif msg_type == 'find_element':
                # 查找元素
                elem = self.find_element(
                    text=data.get('text'),
                    resource_id=data.get('resource_id'),
                    content_desc=data.get('content_desc'),
                    partial_match=data.get('partial_match', True)
                )
                self.ws.send(json.dumps({
                    'type': 'find_element_result',
                    'success': elem is not None,
                    'element': elem
                }))
            
            elif msg_type == 'tap_element':
                # 通过选择器点击元素
                success = self.tap_element(
                    text=data.get('text'),
                    resource_id=data.get('resource_id'),
                    content_desc=data.get('content_desc'),
                    partial_match=data.get('partial_match', True),
                    retry=data.get('retry', 3)
                )
                self.ws.send(json.dumps({
                    'type': 'tap_element_result',
                    'success': success,
                    'selector': {
                        'text': data.get('text'),
                        'resource_id': data.get('resource_id'),
                        'content_desc': data.get('content_desc')
                    }
                }))
            
            elif msg_type == 'wait_for_element':
                # 等待元素出现
                elem = self.wait_for_element(
                    text=data.get('text'),
                    resource_id=data.get('resource_id'),
                    timeout=data.get('timeout', 10)
                )
                self.ws.send(json.dumps({
                    'type': 'wait_element_result',
                    'success': elem is not None,
                    'element': elem
                }))
            
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

    def run_full_workflow(self):
        """执行完整提交作业流程（从配置读取步骤和等待时间）"""
        if not self.current_task:
            return
        
        workflow_id = self.current_task.get('workflow_id', '')
        students = self.current_task.get('students', [])
        representative = self.current_task.get('representative')  # 课代表
        photo_interval = self.current_task.get('photo_interval', 2)
        enable_double_page = self.current_task.get('enable_double_page', True)
        steps = self.current_task.get('steps', [])
        
        logger.info(f"开始执行流程: {workflow_id}, 学生数: {len(students)}, 配置步骤数: {len(steps)}")
        
        # 从 steps 构建等待时间和坐标映射（按步骤顺序对应）
        # steps 结构: [launch, tap进入提交, rfid课代表, tap双页, tap拍照, loop学生, tap提交, tap确认]
        def _get_step(index, default_wait=2, default_x=0, default_y=0):
            """从配置步骤中获取等待时间和坐标"""
            if index < len(steps):
                s = steps[index]
                return {
                    'wait': float(s.get('wait', default_wait)),
                    'x': int(s.get('x', default_x)),
                    'y': int(s.get('y', default_y)),
                }
            return {'wait': default_wait, 'x': default_x, 'y': default_y}
        
        def _get_loop_substep(loop_index, sub_index, default_wait=2):
            """从循环步骤的子步骤中获取等待时间"""
            if loop_index < len(steps):
                loop_step = steps[loop_index]
                sub_steps = loop_step.get('steps', [])
                if sub_index < len(sub_steps):
                    s = sub_steps[sub_index]
                    wait = float(s.get('wait', default_wait))
                    # 支持 use_param 引用 photo_interval
                    if s.get('use_param') == 'photo_interval':
                        wait = photo_interval
                    return wait
            return default_wait
        
        # 步骤索引（对应 workflow_config.json 中 submit_homework 的 steps 顺序）
        # 0: launch, 1: tap进入提交, 2: rfid课代表, 3: tap双页, 4: tap拍照, 5: loop, 6: tap提交, 7: tap确认
        step_launch = _get_step(0, default_wait=5)
        step_enter = _get_step(1, default_wait=2, default_x=1200, default_y=400)
        step_rfid_rep = _get_step(2, default_wait=2)
        step_double_page = _get_step(3, default_wait=1, default_x=400, default_y=551)
        step_photo_rep = _get_step(4, default_wait=2, default_x=667, default_y=978)
        # 循环子步骤: 0=刷学生卡, 1=拍照
        loop_wait_rfid = _get_loop_substep(5, 0, default_wait=3)
        loop_wait_photo = _get_loop_substep(5, 1, default_wait=4)
        step_submit = _get_step(6, default_wait=2, default_x=1593, default_y=955)
        step_confirm = _get_step(7, default_wait=3, default_x=886, default_y=781)
        
        try:
            # 1. 启动 APP
            self._send_progress('启动应用...')
            if not self.atom_launch('com.zpzn.terminal'):
                raise Exception("启动应用失败")
            time.sleep(step_launch['wait'])
            
            # 2. 点击提交作业按钮
            self._send_progress('进入提交界面...')
            if not self.atom_tap(step_enter['x'], step_enter['y']):
                raise Exception("点击提交作业按钮失败")
            time.sleep(step_enter['wait'])
            
            # 3. 刷课代表卡
            if representative:
                self._send_progress(f"刷课代表卡: {representative.get('name', '')}")
                rfid = representative.get('rfid_no', representative.get('card_number', ''))
                if not self.send_rfid(rfid, self.device_path, True):
                    raise Exception("刷课代表卡失败")
                time.sleep(step_rfid_rep['wait'])
                
                # 4. 点击双页模式（只在第一次）
                if enable_double_page:
                    self._send_progress('开启双页模式...')
                    self.atom_tap(step_double_page['x'], step_double_page['y'])
                    time.sleep(step_double_page['wait'])
                
                # 5. 拍照
                self._send_progress('课代表拍照...')
                if not self.atom_tap(step_photo_rep['x'], step_photo_rep['y']):
                    raise Exception("拍照失败")
                time.sleep(step_photo_rep['wait'])
            
            # 6. 循环处理学生
            for i, student in enumerate(students):
                if self.current_task is None:
                    logger.info("流程已停止")
                    return
                
                while self.paused and self.current_task is not None:
                    time.sleep(0.5)
                
                if self.current_task is None:
                    return
                
                name = student.get('name', '')
                rfid = student.get('rfid_no', student.get('card_number', ''))
                
                self._send_progress(f"处理学生 [{i+1}/{len(students)}]: {name}")
                
                # 刷卡
                if not self.send_rfid(rfid, self.device_path, True):
                    logger.error(f"刷卡失败: {name}")
                    self.ws.send(json.dumps({
                        'type': 'workflow_student_result',
                        'index': i,
                        'name': name,
                        'success': False,
                        'error': '刷卡失败'
                    }))
                    continue
                
                # 等待（刷卡后等待，对应子步骤0的 wait）
                time.sleep(loop_wait_rfid)
                
                # 拍照
                if not self.atom_tap(step_photo_rep['x'], step_photo_rep['y']):
                    logger.error(f"拍照失败: {name}")
                
                self.ws.send(json.dumps({
                    'type': 'workflow_student_result',
                    'index': i,
                    'name': name,
                    'success': True
                }))
                
                # 等待拍照完成（对应子步骤1的 wait）
                time.sleep(loop_wait_photo)
            
            # 7. 提交作业
            self._send_progress('提交作业...')
            if not self.atom_tap(step_submit['x'], step_submit['y']):
                raise Exception("点击提交按钮失败")
            time.sleep(step_submit['wait'])
            
            # 8. 确认提交
            self._send_progress('确认提交...')
            if not self.atom_tap(step_confirm['x'], step_confirm['y']):
                raise Exception("点击确认提交失败")
            time.sleep(step_confirm['wait'])
            
            # 完成
            self.ws.send(json.dumps({
                'type': 'workflow_complete',
                'workflow_id': workflow_id,
                'success': True,
                'student_count': len(students)
            }))
            logger.info(f"流程完成: {workflow_id}")
            
        except Exception as e:
            logger.error(f"流程执行失败: {e}")
            self.ws.send(json.dumps({
                'type': 'workflow_complete',
                'workflow_id': workflow_id,
                'success': False,
                'error': str(e)
            }))
        finally:
            self.current_task = None
    
    def _send_progress(self, message: str):
        """发送进度消息"""
        logger.info(f"[进度] {message}")
        self.ws.send(json.dumps({
            'type': 'workflow_progress',
            'message': message
        }))
    
    # ==================== 原子操作 ====================
    
    def handle_workflow_step(self, data: dict):
        """处理工作流步骤（支持坐标和元素选择器两种模式）"""
        action = data.get('action')
        step_name = data.get('desc', action)
        success = False
        error = ''
        
        try:
            # ========== 新增：元素选择器操作 ==========
            if action == 'tap_element':
                # 通过选择器点击
                success = self.tap_element(
                    text=data.get('text'),
                    resource_id=data.get('resource_id'),
                    content_desc=data.get('content_desc'),
                    partial_match=data.get('partial_match', True),
                    retry=data.get('retry', 3)
                )
                step_name = f"点击元素: {data.get('text') or data.get('resource_id') or data.get('content_desc')}"
            
            elif action == 'wait_element':
                # 等待元素出现
                elem = self.wait_for_element(
                    text=data.get('text'),
                    resource_id=data.get('resource_id'),
                    timeout=data.get('timeout', 10)
                )
                success = elem is not None
                step_name = f"等待元素: {data.get('text') or data.get('resource_id')}"
            
            elif action == 'input_to_element':
                # 先点击元素，再输入文本
                text_to_input = data.get('input_text', '')
                if self.tap_element(
                    text=data.get('text'),
                    resource_id=data.get('resource_id'),
                    content_desc=data.get('content_desc')
                ):
                    time.sleep(0.3)
                    self.atom_clear()
                    time.sleep(0.2)
                    success = self.atom_input(text_to_input)
                step_name = f"输入到元素: {text_to_input[:20]}..."
            
            # ========== 原有原子操作 ==========
            elif action == 'tap':
                x = data.get('x', 0)
                y = data.get('y', 0)
                success = self.atom_tap(x, y)
                step_name = f"点击 ({x}, {y})"
            elif action == 'long_press':
                success = self.atom_long_press(data.get('x', 0), data.get('y', 0), data.get('duration', 1000))
            elif action == 'swipe':
                success = self.atom_swipe(data.get('x1', 0), data.get('y1', 0), 
                                          data.get('x2', 0), data.get('y2', 0), data.get('duration', 300))
            elif action == 'input':
                text = data.get('text', '')
                success = self.atom_input(text)
                step_name = f"输入: {text[:20]}..."
            elif action == 'clear':
                success = self.atom_clear()
                step_name = "清除输入"
            elif action == 'key':
                key = data.get('key', 'enter')
                success = self.atom_key(key)
                step_name = f"按键: {key}"
            elif action == 'wait':
                seconds = data.get('seconds', 1)
                time.sleep(seconds)
                success = True
                step_name = f"等待 {seconds}s"
            elif action == 'launch':
                package = data.get('package', 'com.zpzn.terminal')
                success = self.atom_launch(package)
                step_name = f"启动: {package}"
            elif action == 'stop_app':
                package = data.get('package', '')
                success = self.atom_stop_app(package)
                step_name = f"停止: {package}"
            elif action == 'screenshot':
                success = self.atom_screenshot()
                step_name = "截图"
            # 兼容旧版复合操作
            elif action == 'launch_app':
                success = self.atom_launch(data.get('package_name', 'com.zpzn.terminal'))
                step_name = '打开应用'
            elif action == 'click':
                coord = data.get('coord', '')
                coord_info = self.COORDINATES.get(coord, {})
                success = self.atom_tap(coord_info.get('x', 0), coord_info.get('y', 0))
                step_name = f"点击 {coord}"
            elif action == 'input_credentials':
                success = self.input_credentials(data)
                step_name = '输入账号密码'
            elif action == 'input_homework_name':
                success = self.input_homework_name(data)
                step_name = '输入作业名称'
            elif action == 'select_page':
                success = self.select_page()
                step_name = '选择页码'
            elif action == 'send_rfid':
                rfid_code = data.get('rfid_code', '')
                success = self.send_rfid(rfid_code, self.device_path, True)
                step_name = f"发送 RFID {rfid_code}"
            else:
                error = f"未知操作: {action}"
                logger.warning(error)
        except Exception as e:
            error = str(e)
            logger.error(f"执行步骤失败: {e}")
        
        # 发送结果
        self.ws.send(json.dumps({
            'type': 'workflow_step_result',
            'step_name': step_name,
            'action': action,
            'success': success,
            'error': error
        }))
    
    # ==================== 原子操作实现 ====================
    
    def atom_tap(self, x: int, y: int) -> bool:
        """点击坐标"""
        try:
            logger.info(f"点击: ({x}, {y})")
            cmd = f"adb -s {self.device_ip} shell input tap {x} {y}"
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"点击失败: {e}")
            return False
    
    def atom_long_press(self, x: int, y: int, duration: int = 1000) -> bool:
        """长按"""
        try:
            logger.info(f"长按: ({x}, {y}) {duration}ms")
            cmd = f"adb -s {self.device_ip} shell input swipe {x} {y} {x} {y} {duration}"
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"长按失败: {e}")
            return False
    
    def atom_swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """滑动"""
        try:
            logger.info(f"滑动: ({x1}, {y1}) -> ({x2}, {y2})")
            cmd = f"adb -s {self.device_ip} shell input swipe {x1} {y1} {x2} {y2} {duration}"
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"滑动失败: {e}")
            return False
    
    def atom_input(self, text: str) -> bool:
        """输入文本"""
        try:
            logger.info(f"输入: {text[:30]}...")
            # 转义特殊字符
            escaped = text.replace(' ', '%s').replace('&', '\\&').replace('<', '\\<').replace('>', '\\>').replace('|', '\\|').replace('"', '\\"')
            cmd = f'adb -s {self.device_ip} shell input text "{escaped}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"输入失败: {e}")
            return False
    
    def atom_clear(self) -> bool:
        """清除输入框内容（全选+删除）"""
        try:
            logger.info("清除输入框")
            # 全选 Ctrl+A
            cmd1 = f"adb -s {self.device_ip} shell input keyevent 29 --longpress"  # KEYCODE_A
            subprocess.run(cmd1, shell=True, capture_output=True, timeout=5)
            time.sleep(0.1)
            # 或者用组合键
            cmd2 = f"adb -s {self.device_ip} shell input keyevent 67"  # KEYCODE_DEL 删除
            result = subprocess.run(cmd2, shell=True, capture_output=True, timeout=5)
            # 多删几次确保清空
            for _ in range(20):
                subprocess.run(cmd2, shell=True, capture_output=True, timeout=2)
            return True
        except Exception as e:
            logger.error(f"清除失败: {e}")
            return False
    
    def atom_key(self, key: str) -> bool:
        """按键"""
        key_map = {
            'enter': 66, 'back': 4, 'home': 3, 'tab': 61,
            'del': 67, 'delete': 67, 'space': 62,
            'up': 19, 'down': 20, 'left': 21, 'right': 22
        }
        keycode = key_map.get(key.lower(), key)
        try:
            logger.info(f"按键: {key} ({keycode})")
            cmd = f"adb -s {self.device_ip} shell input keyevent {keycode}"
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"按键失败: {e}")
            return False
    
    def atom_launch(self, package: str) -> bool:
        """启动应用"""
        try:
            logger.info(f"启动应用: {package}")
            # 先停止
            stop_cmd = f"adb -s {self.device_ip} shell am force-stop {package}"
            subprocess.run(stop_cmd, shell=True, capture_output=True, timeout=5)
            time.sleep(1)
            # 用 monkey 启动
            start_cmd = f"adb -s {self.device_ip} shell monkey -p {package} -c android.intent.category.LAUNCHER 1"
            result = subprocess.run(start_cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=10)
            if "No activities found" in result.stdout or "No activities found" in result.stderr:
                logger.error(f"未找到应用: {package}")
                return False
            logger.info("应用启动成功")
            return True
        except Exception as e:
            logger.error(f"启动应用失败: {e}")
            return False
    
    def atom_stop_app(self, package: str) -> bool:
        """停止应用"""
        try:
            logger.info(f"停止应用: {package}")
            cmd = f"adb -s {self.device_ip} shell am force-stop {package}"
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"停止应用失败: {e}")
            return False
    
    def atom_screenshot(self) -> bool:
        """截图并保存"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            remote_path = f"/sdcard/screenshot_{timestamp}.png"
            logger.info(f"截图: {remote_path}")
            cmd = f"adb -s {self.device_ip} shell screencap -p {remote_path}"
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return False
    
    # ==================== UI 分析功能 ====================
    
    def dump_ui(self, force_refresh: bool = False) -> Optional[str]:
        """
        导出当前界面的 UI 层级结构
        
        Args:
            force_refresh: 是否强制刷新（忽略缓存）
        
        Returns:
            XML 字符串，失败返回 None
        """
        # 检查缓存（2秒内有效）
        if not force_refresh and self._ui_cache and (time.time() - self._ui_cache_time) < 2:
            return self._ui_cache
        
        try:
            logger.info("导出 UI 结构...")
            # 导出到设备
            dump_cmd = f"adb -s {self.device_ip} shell uiautomator dump /sdcard/ui_dump.xml"
            result = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True, 
                                    encoding='utf-8', errors='ignore', timeout=10)
            
            if result.returncode != 0:
                logger.error(f"UI dump 失败: {result.stderr}")
                return None
            
            # 读取内容
            cat_cmd = f"adb -s {self.device_ip} shell cat /sdcard/ui_dump.xml"
            result = subprocess.run(cat_cmd, shell=True, capture_output=True, text=True,
                                    encoding='utf-8', errors='ignore', timeout=10)
            
            if result.returncode == 0 and result.stdout:
                self._ui_cache = result.stdout
                self._ui_cache_time = time.time()
                logger.info(f"UI 结构导出成功，大小: {len(result.stdout)} 字节")
                return result.stdout
            
            return None
        except Exception as e:
            logger.error(f"导出 UI 结构失败: {e}")
            return None
    
    def parse_ui_elements(self, xml_content: str) -> List[Dict]:
        """
        解析 UI XML，提取所有可交互元素
        
        Returns:
            元素列表，每个元素包含: text, resource_id, class, bounds, clickable, center
        """
        elements = []
        try:
            root = ET.fromstring(xml_content)
            
            def parse_node(node, depth=0):
                attrs = node.attrib
                
                # 提取关键属性
                text = attrs.get('text', '')
                resource_id = attrs.get('resource-id', '')
                class_name = attrs.get('class', '')
                bounds_str = attrs.get('bounds', '')
                clickable = attrs.get('clickable', 'false') == 'true'
                enabled = attrs.get('enabled', 'true') == 'true'
                content_desc = attrs.get('content-desc', '')
                
                # 解析 bounds: [x1,y1][x2,y2]
                center = None
                bounds = None
                if bounds_str:
                    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        bounds = (x1, y1, x2, y2)
                        center = ((x1 + x2) // 2, (y1 + y2) // 2)
                
                # 只保留有意义的元素（有文本、有 resource-id、或可点击）
                if text or resource_id or clickable or content_desc:
                    elements.append({
                        'text': text,
                        'resource_id': resource_id,
                        'class': class_name,
                        'content_desc': content_desc,
                        'bounds': bounds,
                        'center': center,
                        'clickable': clickable,
                        'enabled': enabled,
                        'depth': depth
                    })
                
                # 递归处理子节点
                for child in node:
                    parse_node(child, depth + 1)
            
            parse_node(root)
            logger.info(f"解析到 {len(elements)} 个元素")
            
        except ET.ParseError as e:
            logger.error(f"XML 解析失败: {e}")
        except Exception as e:
            logger.error(f"解析 UI 元素失败: {e}")
        
        return elements
    
    def find_element(self, 
                     text: str = None, 
                     resource_id: str = None, 
                     class_name: str = None,
                     content_desc: str = None,
                     partial_match: bool = True,
                     refresh: bool = True) -> Optional[Dict]:
        """
        查找元素
        
        Args:
            text: 按文本查找
            resource_id: 按 resource-id 查找
            class_name: 按类名查找
            content_desc: 按 content-desc 查找
            partial_match: 是否部分匹配
            refresh: 是否刷新 UI 结构
        
        Returns:
            找到的元素，包含 center 坐标
        """
        xml = self.dump_ui(force_refresh=refresh)
        if not xml:
            return None
        
        elements = self.parse_ui_elements(xml)
        
        for elem in elements:
            # 按 resource-id 匹配（优先级最高）
            if resource_id:
                if partial_match:
                    if resource_id in elem.get('resource_id', ''):
                        return elem
                else:
                    if elem.get('resource_id') == resource_id:
                        return elem
            
            # 按文本匹配
            if text:
                elem_text = elem.get('text', '')
                if partial_match:
                    if text in elem_text:
                        return elem
                else:
                    if elem_text == text:
                        return elem
            
            # 按 content-desc 匹配
            if content_desc:
                elem_desc = elem.get('content_desc', '')
                if partial_match:
                    if content_desc in elem_desc:
                        return elem
                else:
                    if elem_desc == content_desc:
                        return elem
            
            # 按类名匹配
            if class_name and not text and not resource_id and not content_desc:
                if class_name in elem.get('class', ''):
                    return elem
        
        return None
    
    def find_elements(self, 
                      text: str = None, 
                      resource_id: str = None,
                      class_name: str = None,
                      clickable_only: bool = False,
                      refresh: bool = True) -> List[Dict]:
        """
        查找所有匹配的元素
        """
        xml = self.dump_ui(force_refresh=refresh)
        if not xml:
            return []
        
        elements = self.parse_ui_elements(xml)
        results = []
        
        for elem in elements:
            if clickable_only and not elem.get('clickable'):
                continue
            
            match = True
            if text and text not in elem.get('text', ''):
                match = False
            if resource_id and resource_id not in elem.get('resource_id', ''):
                match = False
            if class_name and class_name not in elem.get('class', ''):
                match = False
            
            if match:
                results.append(elem)
        
        return results
    
    def tap_element(self, 
                    text: str = None, 
                    resource_id: str = None,
                    content_desc: str = None,
                    partial_match: bool = True,
                    retry: int = 3,
                    wait_before: float = 0.3) -> bool:
        """
        通过元素选择器点击
        
        Args:
            text: 按文本查找并点击
            resource_id: 按 resource-id 查找并点击
            content_desc: 按 content-desc 查找并点击
            partial_match: 是否部分匹配
            retry: 重试次数
            wait_before: 点击前等待时间
        
        Returns:
            是否成功
        """
        for attempt in range(retry):
            time.sleep(wait_before)
            
            elem = self.find_element(
                text=text, 
                resource_id=resource_id, 
                content_desc=content_desc,
                partial_match=partial_match,
                refresh=True
            )
            
            if elem and elem.get('center'):
                x, y = elem['center']
                logger.info(f"找到元素: text='{elem.get('text')}' id='{elem.get('resource_id')}' -> 点击 ({x}, {y})")
                if self.atom_tap(x, y):
                    return True
            
            if attempt < retry - 1:
                logger.warning(f"未找到元素，重试 {attempt + 2}/{retry}...")
                time.sleep(1)
        
        logger.error(f"点击元素失败: text={text}, resource_id={resource_id}, content_desc={content_desc}")
        return False
    
    def wait_for_element(self, 
                         text: str = None, 
                         resource_id: str = None,
                         timeout: int = 10,
                         interval: float = 0.5) -> Optional[Dict]:
        """
        等待元素出现
        
        Args:
            text: 等待的文本
            resource_id: 等待的 resource-id
            timeout: 超时时间（秒）
            interval: 检查间隔
        
        Returns:
            找到的元素，超时返回 None
        """
        start = time.time()
        while time.time() - start < timeout:
            elem = self.find_element(text=text, resource_id=resource_id, refresh=True)
            if elem:
                logger.info(f"元素已出现: text='{text}' resource_id='{resource_id}'")
                return elem
            time.sleep(interval)
        
        logger.warning(f"等待元素超时: text={text}, resource_id={resource_id}")
        return None
    
    def get_ui_summary(self) -> Dict:
        """
        获取当前界面摘要（用于调试）
        
        Returns:
            包含可点击元素列表的摘要
        """
        xml = self.dump_ui(force_refresh=True)
        if not xml:
            return {'success': False, 'error': '无法获取 UI 结构'}
        
        elements = self.parse_ui_elements(xml)
        
        # 分类整理
        clickable = []
        text_elements = []
        
        for elem in elements:
            info = {
                'text': elem.get('text', ''),
                'resource_id': elem.get('resource_id', ''),
                'content_desc': elem.get('content_desc', ''),
                'center': elem.get('center'),
                'class': elem.get('class', '').split('.')[-1]  # 只保留类名
            }
            
            if elem.get('clickable'):
                clickable.append(info)
            elif elem.get('text'):
                text_elements.append(info)
        
        return {
            'success': True,
            'clickable_count': len(clickable),
            'text_count': len(text_elements),
            'clickable_elements': clickable[:30],  # 限制数量
            'text_elements': text_elements[:20]
        }
    
    # 坐标配置（兼容旧版）
    COORDINATES = {
        'login_entry_button': {'x': 370, 'y': 600},
        'teacher_login_button': {'x': 1800, 'y': 70},
        'username_input': {'x': 930, 'y': 426},
        'password_input': {'x': 880, 'y': 530},
        'login_submit_button': {'x': 960, 'y': 670},
        'publish_homework_button': {'x': 400, 'y': 560},
        'select_page_button': {'x': 870, 'y': 379},
        'page_number_selector': {'x': 659, 'y': 233},
        'page_number_select_button': {'x': 830, 'y': 230},
        'confirm_page_button': {'x': 950, 'y': 900},
        'homework_name_input': {'x': 833, 'y': 557},
        'publish_submit_button': {'x': 960, 'y': 960}
    }
    
    def input_credentials(self, data: dict) -> bool:
        """输入账号密码（修复版：先清除再输入）"""
        username = data.get('username', 'shuxue')
        password = data.get('password', '123456zp.')
        
        try:
            # 1. 点击账号输入框
            logger.info("点击账号输入框")
            self.atom_tap(1230, 426)
            time.sleep(0.5)
            
            # 2. 清除账号内容
            logger.info("清除账号内容")
            self.atom_clear()
            time.sleep(0.3)
            
            # 3. 输入账号
            logger.info(f"输入账号: {username}")
            self.atom_input(username)
            time.sleep(0.5)
            
            # 4. 按回车
            self.atom_key('enter')
            time.sleep(0.5)
            
            # 5. 点击密码输入框
            logger.info("点击密码输入框")
            self.atom_tap(1230, 540)
            time.sleep(0.5)
            
            # 6. 清除密码内容
            logger.info("清除密码内容")
            self.atom_clear()
            time.sleep(0.3)
            
            # 7. 输入密码
            logger.info("输入密码")
            self.atom_input(password)
            time.sleep(0.5)
            
            # 8. 按回车
            self.atom_key('enter')
            time.sleep(0.5)
            
            # 9. 点击登录按钮
            logger.info("点击登录按钮")
            self.atom_tap(960, 670)
            
            logger.info("账号密码输入完成")
            return True
        except Exception as e:
            logger.error(f"输入账号密码异常: {e}")
            return False
    
    def input_homework_name(self, data: dict) -> bool:
        """输入作业名称"""
        homework_name = data.get('homework_name', '')
        
        # 如果没有指定名称，自动生成
        if not homework_name:
            homework_name = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # 点击作业名称输入框
            logger.info("点击作业名称输入框")
            self.atom_tap(833, 557)
            time.sleep(0.5)
            
            # 输入作业名称
            logger.info(f"输入作业名称: {homework_name}")
            self.atom_input(homework_name)
            time.sleep(0.5)
            
            # 按回车关闭键盘
            self.atom_key('enter')
            
            return True
        except Exception as e:
            logger.error(f"输入作业名称异常: {e}")
            return False
    
    def select_page(self) -> bool:
        """选择页码"""
        try:
            # 点击选择页码按钮
            logger.info("点击选择页码按钮")
            self.atom_tap(870, 379)
            time.sleep(1)
            
            # 点击页码选择器
            logger.info("点击页码选择器")
            self.atom_tap(659, 233)
            time.sleep(0.5)
            
            # 点击页码确认按钮
            logger.info("点击页码确认")
            self.atom_tap(830, 230)
            time.sleep(0.5)
            
            # 点击确认页码按钮
            logger.info("确认页码")
            self.atom_tap(950, 900)
            
            logger.info("页码选择完成")
            return True
        except Exception as e:
            logger.error(f"选择页码异常: {e}")
            return False
    
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
    parser.add_argument('--dump-ui', action='store_true',
                        help='导出当前界面 UI 结构并退出')
    parser.add_argument('--output', '-o', default='ui_dump.json',
                        help='UI 结构输出文件')
    
    args = parser.parse_args()
    
    # 如果是 dump-ui 模式，直接导出并退出
    if args.dump_ui:
        print("=" * 50)
        print("UI 结构导出模式")
        print("=" * 50)
        print(f"被控设备: {args.device}")
        print()
        
        client = AdbClient('', args.device)
        
        # 检查连接
        if not client.check_adb_connection():
            print("错误: ADB 设备未连接")
            return
        
        # 先截图
        screenshot_path = args.output.replace('.json', '.png')
        print(f"正在截图...")
        try:
            # 截图到设备
            subprocess.run(
                f"adb -s {args.device} shell screencap -p /sdcard/screen_dump.png",
                shell=True, capture_output=True, timeout=10
            )
            # 拉取到本地
            subprocess.run(
                f"adb -s {args.device} pull /sdcard/screen_dump.png {screenshot_path}",
                shell=True, capture_output=True, timeout=10
            )
            print(f"✓ 截图已保存到: {screenshot_path}")
        except Exception as e:
            print(f"截图失败: {e}")
        
        # 导出 UI
        print("正在导出 UI 结构...")
        summary = client.get_ui_summary()
        
        if summary.get('success'):
            # 保存到文件
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            print(f"\n✓ UI 结构已保存到: {args.output}")
            print(f"  - 可点击元素: {summary['clickable_count']} 个")
            print(f"  - 文本元素: {summary['text_count']} 个")
            print()
            print("可点击元素列表:")
            print("-" * 50)
            for i, elem in enumerate(summary.get('clickable_elements', [])[:15]):
                text = elem.get('text', '') or elem.get('content_desc', '') or '(无文本)'
                rid = elem.get('resource_id', '')
                center = elem.get('center', (0, 0))
                print(f"  {i+1}. [{text[:20]}] id={rid[-30:] if rid else ''} pos={center}")
        else:
            print(f"错误: {summary.get('error', '未知错误')}")
        return
    
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
