"""
RFID发送模块 - 使用底层事件精确模拟RFID读卡器
基于真实设备抓包分析，包含完整的EV_MSC扫描码等非标准事件
"""

import subprocess
import time
import logging
from typing import List, Optional, Dict

from config import RFID_CONFIG, RFID_EVENT_MAP, RFID_DEVICE_PATH

logger = logging.getLogger(__name__)


class RfidSender:
    """
    RFID读卡器模拟器

    核心原理：
    1. 通过sendevent命令直接向Linux输入子系统发送原始事件
    2. 包含EV_MSC扫描码事件，精确模拟真实读卡器行为
    3. 使用批量命令减少ADB调用次数，提高发送速度
    """

    def __init__(self, device_ip: str, device_path: str = None):
        """
        初始化RFID发送器

        Args:
            device_ip: 设备IP地址（格式：IP:PORT）
            device_path: 输入设备路径（如果为None则使用配置中的值）
        """
        self.device_ip = device_ip
        self.device_path = device_path or RFID_DEVICE_PATH
        self.event_map = RFID_EVENT_MAP
        self.inter_char_delay = RFID_CONFIG['inter_char_delay']
        self.final_enter_delay = RFID_CONFIG['final_enter_delay']
        self.cmd_timeout = RFID_CONFIG['cmd_timeout']

        logger.info(f"初始化RFID发送器: 设备={device_ip}, 输入设备={self.device_path}")

    def build_batch_commands(self, target_sequence: str) -> List[str]:
        """
        构建批量ADB命令（将所有事件合并为最少调用）

        核心逻辑：
        - 每个字符的所有事件合并为一条shell命令
        - 使用分号分隔多个sendevent命令
        - 减少ADB调用次数，提高发送速度

        Args:
            target_sequence: 目标RFID序列

        Returns:
            List[str]: 批量命令列表
        """
        batch_cmds = []

        # 1. 构建目标序列的批量命令
        for char in target_sequence:
            if char not in self.event_map:
                logger.warning(f"跳过未知字符：{char}")
                continue

            # 单个字符的所有事件合并为一条shell命令
            char_events = []
            for event in self.event_map[char]:
                type_code, code, value = event
                char_events.append(
                    f"sendevent {self.device_path} {type_code} {code} {value}"
                )

            # 拼接为单条命令（减少ADB调用次数）
            batch_cmds.append("; ".join(char_events))

        # 2. 构建回车的批量命令
        enter_events = []
        for event in self.event_map['enter']:
            type_code, code, value = event
            enter_events.append(
                f"sendevent {self.device_path} {type_code} {code} {value}"
            )

        batch_cmds.append("; ".join(enter_events))

        return batch_cmds

    def send_rfid_sequence(self, rfid_code: str) -> bool:
        """
        发送RFID序列

        核心流程：
        1. 构建批量命令
        2. 逐个字符发送事件序列
        3. 字符间保持极短延迟（硬件级间隔）
        4. 最后发送回车键确认

        Args:
            rfid_code: RFID卡号

        Returns:
            bool: 发送是否成功
        """
        try:
            logger.info(f"发送RFID序列: {rfid_code}")

            # 构建批量命令
            batch_cmds = self.build_batch_commands(rfid_code)
            total_chars = len(rfid_code)

            logger.info(f"超高速发送序列（{total_chars}字符），批量命令模式...")

            # 1. 发送目标序列（每条批量命令对应一个字符）
            has_errors = False
            for i in range(total_chars):
                cmd = ["adb", "-s", self.device_ip, "shell", batch_cmds[i]]
                try:
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=self.cmd_timeout,
                        text=True
                    )
                    
                    # 检查命令执行状态
                    if result.returncode != 0:
                        error_msg = result.stderr.strip() or "未知错误"
                        logger.error(f"字符{i + 1}发送失败，返回码: {result.returncode}")
                        logger.error(f"错误详情: {error_msg}")
                        has_errors = True
                    else:
                        logger.debug(f"字符{i + 1}发送成功")
                except Exception as e:
                    logger.error(f"字符{i + 1}发送异常：{str(e)}，继续...")
                    has_errors = True

                # 字符间仅短暂延迟（硬件级间隔）
                if i < total_chars - 1:
                    time.sleep(self.inter_char_delay)
                    logger.debug(f"已发送第{i + 1}/{total_chars}个字符")

            # 2. 发送回车（最后一条批量命令）
            logger.info(f"序列发送完成，{self.final_enter_delay * 1000}ms后发送回车...")
            time.sleep(self.final_enter_delay)

            try:
                result = subprocess.run(
                    ["adb", "-s", self.device_ip, "shell", batch_cmds[-1]],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.cmd_timeout,
                    text=True
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr.strip() or "未知错误"
                    logger.error(f"回车事件发送失败，返回码: {result.returncode}")
                    logger.error(f"错误详情: {error_msg}")
                    has_errors = True
            except Exception as e:
                logger.error(f"回车事件异常：{str(e)}")
                has_errors = True

            if has_errors:
                logger.warning("⚠️ RFID序列发送过程中出现错误")
                return False
            
            logger.info("✅ RFID序列发送完成")
            return True

        except Exception as e:
            logger.error(f"发送RFID序列失败: {str(e)}")
            return False

    def find_rfid_device_by_name(self) -> Optional[str]:
        """
        通过设备名称"HID 413d:2107"查找RFID输入设备
        优化处理带引号的设备名称格式
        
        Returns:
            Optional[str]: 找到的设备路径，失败返回None
        """
        try:
            target_device_name = "HID 413d:2107"
            logger.info(f"尝试通过设备名称 '{target_device_name}' 查找RFID设备")
            
            # 定义可能的名称模式（带引号和不带引号）
            name_patterns = [
                target_device_name,  # 不带引号
                f'"{target_device_name}"',  # 带双引号
                f"'{target_device_name}'",  # 带单引号
                "HID",  # 部分匹配
                "413d:2107"  # 部分匹配
            ]
            
            # 先尝试直接获取设备名称信息
            logger.info("尝试通过getevent -i命令获取每个设备的详细信息...")
            
            # 首先获取所有输入设备路径
            cmd = f"adb -s {self.device_ip} shell find /dev/input -name 'event*'"
            devices_result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=10
            )
            
            device_paths = [line.strip() for line in devices_result.stdout.splitlines() if line.strip()]
            logger.info(f"找到 {len(device_paths)} 个输入设备路径")
            
            # 检查每个设备的名称
            for device_path in device_paths:
                try:
                    # 获取单个设备的详细信息
                    cmd = f"adb -s {self.device_ip} shell getevent -i {device_path}"
                    device_info_result = subprocess.run(
                        cmd, 
                        shell=True, 
                        capture_output=True, 
                        text=True,
                        timeout=5
                    )
                    
                    # 查找名称行
                    for info_line in device_info_result.stdout.splitlines():
                        info_line = info_line.strip()
                        if 'name:' in info_line:
                            # 提取名称部分
                            name_part = info_line.split('name:', 1)[1].strip()
                            logger.info(f"设备 {device_path} 的名称信息: '{name_part}'")
                            
                            # 检查是否匹配任何模式
                            for pattern in name_patterns:
                                if pattern in name_part:
                                    logger.info(f"✓ 找到匹配设备! 路径: {device_path}, 名称包含: '{pattern}'")
                                    return device_path
                except Exception as e:
                    logger.debug(f"获取设备{device_path}信息失败: {str(e)}")
            
            logger.warning("未通过直接设备查询找到匹配的RFID设备")
            
            # 备用方法：使用getevent -li获取所有设备信息
            logger.info("尝试使用getevent -li获取所有设备信息...")
            cmd = f"adb -s {self.device_ip} shell getevent -li"
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.warning(f"getevent -li命令失败: {result.stderr or '未知错误'}")
                # 最后尝试getevent -p
                logger.info("尝试使用getevent -p命令...")
                cmd = f"adb -s {self.device_ip} shell getevent -p"
                result = subprocess.run(
                    cmd, 
                    shell=True, 
                    capture_output=True, 
                    text=True,
                    timeout=10
                )
            
            # 解析输出查找设备信息
            current_device = None
            logger.info("\n--- 设备列表扫描 ---")
            
            for line in result.stdout.splitlines():
                line = line.strip()
                
                # 查找设备路径
                if line.startswith('/dev/input/event'):
                    current_device = line
                # 查找名称信息
                elif current_device and 'name:' in line:
                    name_part = line.split('name:', 1)[1].strip()
                    logger.info(f"扫描到: {current_device} 名称: {name_part}")
                    
                    # 使用模式匹配
                    for pattern in name_patterns:
                        if pattern in name_part:
                            logger.info(f"✓ 通过备用方法找到匹配设备! 路径: {current_device}")
                            return current_device
                    
                    current_device = None  # 重置
                # 空行可能表示设备信息块结束
                elif line == "" and current_device:
                    current_device = None
            
            logger.warning(f"未找到名称包含 '{target_device_name}' 的设备")
            return None
        except Exception as e:
            logger.error(f"按设备名称查找失败: {str(e)}")
            return None
    
    def verify_device_path(self, device_path: str) -> bool:
        """
        验证设备路径是否有效
        
        Args:
            device_path: 要验证的设备路径
            
        Returns:
            bool: 设备路径是否有效
        """
        try:
            logger.info(f"验证设备路径 {device_path}")
            
            # 执行ls命令检查路径是否存在
            cmd = f"adb -s {self.device_ip} shell ls -la {device_path}"
            logger.debug(f"执行命令: {cmd}")
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logger.info(f"设备路径有效 {device_path}")
                logger.debug(f"命令输出: {result.stdout.strip()}")
                return True
            else:
                logger.warning(f"设备路径无效 {device_path}，返回码: {result.returncode}")
                logger.debug(f"错误输出: {result.stderr.strip() or '无错误输出'}")
                logger.debug(f"标准输出: {result.stdout.strip() or '无输出'}")
                return False
                
        except Exception as e:
            logger.error(f"验证失败: {str(e)}")
            return False

    def list_all_input_devices(self) -> List[Dict[str, str]]:
        """
        列出所有可用的输入设备路径和名称信息（扩展版本）
        
        Returns:
            List[Dict[str, str]]: 设备信息列表，每项包含path和name
        """
        try:
            from typing import Dict
            
            logger.info("列出所有输入设备")
            
            # 使用find命令直接获取所有event设备路径（更可靠）
            cmd = f"adb -s {self.device_ip} shell find /dev/input -name 'event*'"
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=5
            )
            
            device_paths = []
            if result.returncode == 0:
                device_paths = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                for path in device_paths:
                    logger.debug(f"发现输入设备: {path}")
            else:
                logger.warning(f"获取设备列表失败: {result.stderr or '未知错误'}")
                # 备用方法：使用ls命令
                cmd = f"adb -s {self.device_ip} shell ls -la /dev/input/event*"
                result = subprocess.run(
                    cmd, 
                    shell=True, 
                    capture_output=True, 
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if 'event' in line:
                            parts = line.split()
                            if parts and parts[-1].startswith("event"):
                                device_path = f"/dev/input/{parts[-1]}"
                                device_paths.append(device_path)
                                logger.debug(f"发现输入设备: {device_path}")
            
            logger.info(f"找到 {len(device_paths)} 个输入设备")
            
            # 尝试获取每个设备的名称信息
            device_infos = []
            for device_path in device_paths:
                device_info = {'path': device_path, 'name': '未知'}
                
                # 尝试通过getevent -i获取设备名称
                try:
                    cmd = f"adb -s {self.device_ip} shell getevent -i {device_path}"
                    name_result = subprocess.run(
                        cmd, 
                        shell=True, 
                        capture_output=True, 
                        text=True,
                        timeout=5
                    )
                    
                    # 解析输出查找name
                    for line in name_result.stdout.splitlines():
                        line = line.strip()
                        if 'name: ' in line:
                            name_part = line.split('name: ')[1]
                            if name_part.startswith('"') and name_part.endswith('"'):
                                device_name = name_part[1:-1]
                            else:
                                device_name = name_part.strip()
                            device_info['name'] = device_name
                            break
                except Exception as e:
                    logger.debug(f"获取设备{device_path}名称失败: {str(e)}")
                
                device_infos.append(device_info)
                logger.info(f"设备路径: {device_path}, 名称: '{device_info['name']}'")
            
            return device_infos
        except Exception as e:
            logger.error(f"列出设备失败: {str(e)}")
            return []
    
    def detect_input_device(self) -> Optional[str]:
        """
        改进的RFID输入设备检测方法
        结合设备名称查找和设备列表验证，并利用收集的设备名称信息
        
        Returns:
            Optional[str]: 检测到的输入设备路径，失败返回None
        """
        try:
            logger.info(f"开始检测 [{self.device_ip}] 的 RFID 输入设备")
            
            # 检查设备是否连接
            if not self._check_device_connection():
                logger.error(f"设备 {self.device_ip} 未连接或ADB不可用")
                return None
            
            original_path = self.device_path
            
            # 核心方法: 通过设备名称查找"HID 413d:2107"
            device_path = self.find_rfid_device_by_name()
            if device_path and self.verify_device_path(device_path):
                logger.info(f"成功检测到RFID设备: {device_path}")
                self.device_path = device_path
                # 如果检测到的路径与原路径不同，更新配置
                if device_path != original_path:
                    self._update_config_device_path(device_path)
                return device_path
            
            # 如果未找到，列出所有可能的设备作为备选
            logger.info("未找到指定名称的设备，列出所有输入设备供参考")
            device_infos = self.list_all_input_devices()
            
            # 定义目标设备标识符
            target_identifiers = ["HID", "413d:2107", "rfid", "reader"]
            
            # 先尝试查找匹配标识符的设备
            for device_info in device_infos:
                device_path = device_info['path']
                device_name = device_info['name'].lower()
                
                # 检查设备名称是否包含目标标识符
                if any(identifier.lower() in device_name for identifier in target_identifiers):
                    logger.info(f"发现潜在RFID设备: {device_path} (名称: '{device_info['name']}')")
                    if self.verify_device_path(device_path):
                        logger.info(f"找到匹配设备: {device_path} (名称: '{device_info['name']}')")
                        self.device_path = device_path
                        # 如果检测到的路径与原路径不同，更新配置
                        if device_path != original_path:
                            self._update_config_device_path(device_path)
                        return device_path
            
            # 尝试验证每个列出的设备
            if device_infos:
                for device_info in device_infos:
                    device_path = device_info['path']
                    if self.verify_device_path(device_path):
                        logger.info(f"找到可用设备: {device_path} (名称: '{device_info['name']}')")
                        self.device_path = device_path
                        # 如果检测到的路径与原路径不同，更新配置
                        if device_path != original_path:
                            self._update_config_device_path(device_path)
                        return device_path
                
                logger.info(f"发现 {len(device_infos)} 个可用输入设备")
                for device_info in device_infos:
                    logger.info(f"  - 路径: {device_info['path']}, 名称: '{device_info['name']}'")
            else:
                logger.warning("未找到任何输入设备，请检查设备连接和权限")
                
            return None
            
        except Exception as e:
            logger.error(f"检测失败: {str(e)}")
            return None
            
    def _update_config_device_path(self, device_path):
        """
        更新配置文件中的设备路径
        
        Args:
            device_path: 新的设备路径
        """
        try:
            import os
            config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
            
            if not os.path.exists(config_file):
                logger.error(f"配置文件不存在: {config_file}")
                return
            
            # 读取配置文件
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 更新RFID_DEVICE_PATH
            import re
            new_content = re.sub(
                r'RFID_DEVICE_PATH\s*=\s*["\'](.*?)["\']',
                f'RFID_DEVICE_PATH = "{device_path}"',
                content
            )
            
            # 写入配置文件
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"已更新配置文件中的设备路径为: {device_path}")
        except Exception as e:
            logger.error(f"更新配置文件时发生错误: {str(e)}")

            
    def _check_device_connection(self) -> bool:
        """
        检查设备是否已连接，并处理各种连接状态
        
        Returns:
            bool: 设备是否处于可用状态
        """
        try:
            # 运行adb devices命令检查设备状态
            cmd = "adb devices"
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"ADB命令执行失败: {result.stderr or '未知错误'}")
                return False
            
            # 解析输出，检查设备状态
            devices_output = result.stdout
            logger.info(f"可用设备列表: {devices_output}")
            
            # 查找设备及其状态
            device_line = None
            for line in devices_output.splitlines():
                if self.device_ip in line:
                    device_line = line
                    break
            
            if not device_line:
                logger.warning(f"设备 {self.device_ip} 未在连接列表中")
                return False
            
            # 检查设备状态
            parts = device_line.split()
            if len(parts) >= 2:
                status = parts[1]
                if status == "device":
                    logger.info(f"设备 {self.device_ip} 已成功连接 (状态: {status})")
                    return True
                elif status == "offline":
                    logger.warning(f"设备 {self.device_ip} 已连接但状态为离线 (offline)")
                    logger.info("建议: 尝试断开并重新连接设备，或重启ADB服务")
                    return False
                elif status == "unauthorized":
                    logger.warning(f"设备 {self.device_ip} 未授权连接")
                    logger.info("建议: 检查设备上的USB调试授权弹窗")
                    return False
                else:
                    logger.warning(f"设备 {self.device_ip} 状态未知: {status}")
                    return False
            
            logger.warning(f"无法解析设备 {self.device_ip} 的状态信息")
            return False
            
        except Exception as e:
            logger.error(f"检查设备连接时发生异常: {str(e)}")
            return False
