"""
作业提交自动化测试模块 - 实现单个设备的完整测试流程
"""

import os
import sys
import time
import json
import logging
import traceback
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 延迟导入uiautomator2，避免环境问题导致程序无法启动
def import_uiautomator2():
    """动态导入uiautomator2模块"""
    try:
        import uiautomator2 as u2
        from uiautomator2 import Device
        return u2, Device
    except ImportError as e:
        raise ImportError(f"导入uiautomator2失败: {str(e)}")

# 立即导入必要的其他模块
try:
    from config import (
        APP_CONFIG, CLICK_COORDINATES, RFID_CARDS as DEFAULT_RFID_CARDS, STUDENT_COUNT as DEFAULT_STUDENT_COUNT,
        RFID_CONFIG, TEST_CONFIG as DEFAULT_TEST_CONFIG, ERROR_HANDLING, LOG_DIR, SCREENSHOT_DIR,
        TEACHER_ACCOUNT
    )
    print("成功导入config模块")
except ImportError as e:
    print(f"错误: 导入config模块失败 - {str(e)}")
    sys.exit(1)

try:
    from rfid_sender import RfidSender
    print("成功导入rfid_sender模块")
except ImportError as e:
    print(f"错误: 导入rfid_sender模块失败 - {str(e)}")
    sys.exit(1)

# 日志配置
logger = logging.getLogger(__name__)


class HomeworkTester:
    """
    作业提交自动化测试器

    核心流程：
    1. 连接设备
    2. 启动APP
    3. 进入作业提交界面
    4. 循环处理每个学生：
       - 模拟RFID输入
       - 点击拍照按钮
    5. 提交整批作业
    6. 返回主界面
    """

    def __init__(self, device_ip: str, custom_config: Dict[str, Any] = None):
        """
        初始化测试器

        Args:
            device_ip: 设备IP地址（格式：IP:PORT）
            custom_config: 自定义配置参数
        """
        self.device_ip = device_ip
        self.device: Optional[Device] = None
        self.rfid_sender = RfidSender(device_ip)
        self.custom_config = custom_config or {}
        
        # 应用自定义配置
        self.rfid_cards = self.custom_config.get('rfid_cards', DEFAULT_RFID_CARDS)
        self.student_count = self.custom_config.get('student_count', DEFAULT_STUDENT_COUNT)
        self.test_config = DEFAULT_TEST_CONFIG.copy()
        
        # 更新测试配置
        if 'operation_delay' in self.custom_config:
            self.test_config['operation_delay'] = self.custom_config['operation_delay']
        if 'screenshot_on_error' in self.custom_config:
            self.test_config['screenshot_on_error'] = self.custom_config['screenshot_on_error']
        if 'publish_homework' in self.custom_config:
            self.test_config['publish_homework'] = self.custom_config['publish_homework']
        if 'publish_on_single_device_only' in self.custom_config:
            self.test_config['publish_on_single_device_only'] = self.custom_config['publish_on_single_device_only']
        
        # 限制学生数量不超过RFID卡数量
        self.student_count = min(self.student_count, len(self.rfid_cards))

        # 双页拍照按钮点击标志
        self.double_page_button_clicked = False
        # 是否为批量测试中的第一台设备
        self.is_first_device = self.custom_config.get('is_first_device', False)
        # 截图记录列表
        self.screenshots = []
        # 日志记录列表
        self.logs = []
        
        # 设置自定义日志处理器，将日志添加到logs列表
        class MemoryHandler(logging.Handler):
            def __init__(self, logs_list):
                super().__init__()
                self.logs_list = logs_list
                
            def emit(self, record):
                log_message = f"[{record.levelname}] {record.getMessage()}"
                self.logs_list.append(log_message)
        
        # 添加自定义处理器到logger
        self.memory_handler = MemoryHandler(self.logs)
        self.memory_handler.setLevel(logging.INFO)
        logger.addHandler(self.memory_handler)
        
        # 测试结果记录
        self.test_results = {
            'device_ip': device_ip,
            'status': 'pending',
            'start_time': None,
            'end_time': None,
            'duration': 0,
            'students_processed': 0,
            'students_success': 0,
            'students_failed': 0,
            'student_details': [],  # 每个学生的详细信息
            'errors': [],
            'screenshots': [],
            'logs': []
        }

    def connect_device(self) -> bool:
        """
        连接安卓设备

        核心步骤：
        1. 通过ADB连接设备
        2. 动态导入uiautomator2并连接
        3. 验证设备信息
        4. 自动检测RFID输入设备

        Returns:
            bool: 连接是否成功
        """
        try:
            logger.info(f"正在连接设备: {self.device_ip}")

            # 先通过ADB连接设备
            import subprocess
            connect_cmd = f"adb connect {self.device_ip}"
            result = subprocess.run(
                connect_cmd,
                shell=True,
                capture_output=True,
                text=True
            )

            if "connected" not in result.stdout.lower():
                raise Exception(f"ADB连接失败: {result.stdout}")

            time.sleep(2)

            # 动态导入uiautomator2
            u2, _ = import_uiautomator2()
            
            # 使用uiautomator2连接
            self.device = u2.connect(self.device_ip)

            # 验证连接
            device_info = self.device.info
            if not device_info:
                raise Exception("无法获取设备信息")

            logger.info(f"设备连接成功: {device_info.get('productName', 'Unknown')}")
            self._add_log('INFO', f"设备连接成功: {self.device_ip}")

            # 自动检测RFID输入设备
            input_device = self.rfid_sender.detect_input_device()
            if input_device:
                self.rfid_sender.device_path = input_device
                logger.info(f"自动检测到RFID输入设备: {input_device}")

            return True

        except Exception as e:
            error_msg = f"设备连接失败: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
            self.test_results['status'] = 'connection_failed'
            return False

    def launch_app(self) -> bool:
        """
        启动目标APP

        核心步骤：
        1. 清除设备后台进程
        2. 停止目标APP（如果正在运行）
        3. 启动APP
        4. 等待APP启动完成
        5. 验证APP是否启动成功

        Returns:
            bool: 启动是否成功
        """
        try:
            logger.info(f"正在启动APP: {APP_CONFIG['package_name']}")

            # 清除设备后台进程
            logger.info("正在清除后台进程...")
            # 使用shell命令清除后台进程
            self.device.shell("am kill-all")
            time.sleep(2)
            
            # 强制停止目标APP（确保完全停止）
            logger.info(f"强制停止APP: {APP_CONFIG['package_name']}")
            self.device.shell(f"am force-stop {APP_CONFIG['package_name']}")
            time.sleep(1)
            
            # 再次停止APP（确保没有运行实例）
            self.device.app_stop(APP_CONFIG['package_name'])
            time.sleep(1)

            # 启动APP
            self.device.app_start(
                APP_CONFIG['package_name'],
            )

            # 等待APP启动完成
            time.sleep(APP_CONFIG.get('start_delay', 3))

            # 验证APP是否启动
            if self.device.app_wait(
                APP_CONFIG['package_name'],
                timeout=APP_CONFIG['wait_timeout']
            ):
                logger.info("APP启动成功")
                self._add_log('INFO', "APP启动成功")
                return True
            else:
                raise Exception("APP启动超时")

        except Exception as e:
            error_msg = f"APP启动失败: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
            return False

    def click_coordinate(self, coord_name: str) -> bool:
        """
        点击指定坐标

        核心逻辑：
        1. 从配置中获取坐标信息
        2. 执行点击操作
        3. 等待指定时间
        4. 记录操作日志

        Args:
            coord_name: 坐标配置名称

        Returns:
            bool: 点击是否成功
        """
        try:
            coord_config = CLICK_COORDINATES.get(coord_name)
            if not coord_config:
                raise ValueError(f"未找到坐标配置: {coord_name}")

            x = coord_config['x']
            y = coord_config['y']
            description = coord_config.get('description', coord_name)
            wait_after = coord_config.get('wait_after', 1)

            logger.info(f"点击 {description}: ({x}, {y})")

            # 执行点击
            self.device.click(x, y)

            # 等待操作完成
            time.sleep(wait_after)

            self._add_log('INFO', f"点击成功: {description}")
            return True

        except Exception as e:
            error_msg = f"点击失败 {coord_name}: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
            return False

    def simulate_rfid_input(self, rfid_code: str) -> bool:
        """
        模拟RFID输入

        核心步骤：
        1. 使用RFID发送器发送序列（支持重试）
        2. 等待应用处理RFID输入
        3. 记录操作日志

        Args:
            rfid_code: RFID卡号

        Returns:
            bool: 模拟是否成功
        """
        try:
            logger.info(f"模拟RFID输入: {rfid_code}")
            
            # 检查设备路径是否有效
            if not self.rfid_sender.verify_device_path(self.rfid_sender.device_path):
                logger.warning(f"设备路径 {self.rfid_sender.device_path} 无效，尝试重新检测...")
                new_device_path = self.rfid_sender.detect_input_device()
                if new_device_path:
                    self.rfid_sender.device_path = new_device_path
                    logger.info(f"已更新设备路径为: {new_device_path}")
                else:
                    logger.error("无法找到有效的输入设备，使用默认路径继续")

            # 使用重试机制发送RFID序列
            max_retries = 3
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                retry_count += 1
                if retry_count > 1:
                    logger.info(f"第 {retry_count} 次重试...")
                    time.sleep(1)  # 重试间隔
                
                success = self.rfid_sender.send_rfid_sequence(rfid_code)
                if success:
                    break

            if not success:
                raise Exception(f"RFID序列发送失败，已重试 {max_retries} 次")

            # 增加等待时间，确保应用有足够时间处理输入
            wait_time = RFID_CONFIG.get('wait_after_input', 1) * 1.5  # 增加50%的等待时间
            logger.debug(f"等待 {wait_time:.2f} 秒让应用处理RFID输入")
            time.sleep(wait_time)

            self._add_log('INFO', f"RFID输入成功: {rfid_code}")
            return True

        except Exception as e:
            error_msg = f"RFID输入失败: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
            
            # 尝试清除输入缓冲区（模拟按键）
            try:
                logger.info("尝试清除输入缓冲区...")
                for _ in range(3):
                    self.device.press('back')
                    time.sleep(0.5)
            except:
                pass
                
            return False

    def process_student(self, student_index: int) -> Dict[str, Any]:
        """
        处理单个学生的作业提交

        核心流程：
        1. 获取学生RFID卡号
        2. 模拟RFID输入
        3. 点击拍照按钮
        4. 记录处理结果

        Args:
            student_index: 学生序号（从0开始）

        Returns:
            Dict: 学生处理结果
        """
        student_result = {
            'index': student_index + 1,
            'rfid': self.rfid_cards[student_index],
            'status': 'pending',
            'error': None,
            'timestamp': datetime.now().isoformat()
        }

        try:
            logger.info(f"开始处理第 {student_index + 1}/{self.student_count} 个学生")

            # 1. 获取学生RFID卡号
            rfid_no = self.rfid_cards[student_index]
            student_result['rfid'] = rfid_no

            # 2. 模拟RFID输入
            if not self.simulate_rfid_input(rfid_no):
                raise Exception("RFID卡号输入失败")

            logger.info(f"RFID输入成功: {rfid_no}")
            
            # 等待2秒
            logger.info("等待2秒准备拍照")
            time.sleep(2)
            
            # 3. 只在第一次处理学生时点击双页拍照功能按钮
            if not self.double_page_button_clicked:
                logger.info("点击双页拍照功能按钮")
                if not self.click_coordinate('double_page_button'):
                    raise Exception("点击双页拍照按钮失败")
                self.double_page_button_clicked = True
            
            # 4. 点击拍照按钮
            if not self.click_coordinate('camera_capture_button'):
                raise Exception("点击拍照按钮失败")

            # 5. 等待拍照完成
            time.sleep(CLICK_COORDINATES['camera_capture_button'].get('wait_after', 2))

            # 6. 如果需要，为每个学生截图
            if self.test_config.get('screenshot_each_student'):
                self.take_screenshot(f"student_{student_index + 1}_{rfid_no}")

            student_result['status'] = 'success'
            self.test_results['students_success'] += 1

            logger.info(f"学生 {student_index + 1} 处理成功")

        except Exception as e:
            error_msg = f"处理学生 {student_index + 1} 失败: {str(e)}"
            logger.error(error_msg)

            student_result['status'] = 'failed'
            student_result['error'] = str(e)
            self.test_results['students_failed'] += 1

            # 错误截图
            if self.test_config['screenshot_on_error']:
                self.take_screenshot(f"error_student_{student_index + 1}")

        finally:
            self.test_results['students_processed'] += 1
            self.test_results['student_details'].append(student_result)

        return student_result

    def submit_homework_batch(self) -> bool:
        """
        提交整批作业

        核心流程：
        1. 点击提交按钮
        2. 等待提交确认界面
        3. 点击确认提交
        4. 等待返回主界面

        Returns:
            bool: 提交是否成功
        """
        try:
            logger.info("开始提交作业批次")

            # 1. 点击提交按钮
            if not self.click_coordinate('submit_button'):
                raise Exception("点击提交按钮失败")

            # 2. 等待提交确认界面
            time.sleep(2)

            # 3. 点击确认提交
            if not self.click_coordinate('confirm_submit_button'):
                raise Exception("点击确认提交按钮失败")

            # 4. 等待返回主界面
            time.sleep(3)

            logger.info("作业批次提交成功")
            self._add_log('INFO', "作业批次提交成功")

            return True

        except Exception as e:
            error_msg = f"提交作业失败: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
            return False

    def take_screenshot(self, name: str) -> str:
        """
        截图并保存

        Args:
            name: 截图名称

        Returns:
            str: 截图文件路径
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.device_ip.replace(':', '_')}_{name}_{timestamp}.png"
            filepath = os.path.join(SCREENSHOT_DIR, filename)

            # 确保目录存在
            os.makedirs(SCREENSHOT_DIR, exist_ok=True)

            # 截图
            self.device.screenshot(filepath)

            logger.info(f"截图保存: {filepath}")
            self.test_results['screenshots'].append(filepath)
            self.screenshots.append(filepath)

            return filepath

        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            return ""

    def _add_log(self, level: str, message: str):
        """
        添加日志到测试结果

        Args:
            level: 日志级别
            message: 日志消息
        """
        self.test_results['logs'].append({
            'time': datetime.now().isoformat(),
            'level': level,
            'message': message
        })

    def publish_homework(self):
        """
        发布作业流程
        
        核心步骤：
        1. 点击登录入口
        2. 点击教师登录
        3. 输入账号密码并登录
        4. 进入发布作业界面
        5. 选择页码
        6. 输入作业名称（包含当前时间）
        7. 发布作业
        
        Returns:
            bool: 发布是否成功
        """
        try:
            logger.info(f"开始发布作业流程: {self.device_ip}")
            self._add_log('INFO', "开始发布作业流程")
            
            # 1. 点击登录入口按钮
            if not self.click_coordinate('login_entry_button'):
                logger.error("点击登录入口按钮失败")
                
                return False
            time.sleep(3)
            # 2. 点击教师登录按钮
            if not self.click_coordinate('teacher_login_button'):
                logger.error("点击教师登录按钮失败")
                return False
            time.sleep(3)
            # 3. 输入用户名
            # 先点击用户名输入框
            self.device.click(1230, 430)
            time.sleep(1)

            if not self.click_coordinate('username_input'):
                logger.error("点击用户名输入框失败")
                return False
            time.sleep(3)
            
          
            
            # 输入用户名
            self.device.send_keys(TEACHER_ACCOUNT['username'])
            time.sleep(2)
            
            # 回车
            self.device.press('enter')
            time.sleep(1)
            
            # 4. 输入密码
            # 点击密码输入框

            self.device.click(1230, 540)
            time.sleep(1)

            if not self.click_coordinate('password_input'):
                logger.error("点击密码输入框失败")
                return False
            
            self.device.send_keys(TEACHER_ACCOUNT['password'])
            time.sleep(1)
            
            # 回车
            self.device.press('enter')
            time.sleep(1)
            
            # 5. 点击登录提交按钮
            if not self.click_coordinate('login_submit_button'):
                logger.error("点击登录提交按钮失败")
                return False
            time.sleep(1)

            # 6. 点击发布作业按钮
            if not self.click_coordinate('publish_homework_button'):
                logger.error("点击发布作业按钮失败")
                return False
            time.sleep(1)

            # 7. 点击选择页码按钮
            if not self.click_coordinate('select_page_button'):
                logger.error("点击选择页码按钮失败")
                return False
            time.sleep(1)
            # 8. 点击页码选择器
            if not self.click_coordinate('page_number_selector'):
                logger.error("点击页码选择器失败")
                return False
            time.sleep(1)
            # 9. 点击页码确认按钮
            if not self.click_coordinate('page_number_select_button'):
                logger.error("点击页码确认按钮失败")
                return False
            time.sleep(1)
            # 10. 点击确认页码按钮
            if not self.click_coordinate('confirm_page_button'):
                logger.error("点击确认页码按钮失败")
                return False
            time.sleep(1)

            
            # 11. 输入作业名称
            # 点击作业名称输入框
            if not self.click_coordinate('homework_name_input'):
                logger.error("点击作业名称输入框失败")
                return False
            time.sleep(1)
            # 输入作业名称（包含当前时间）
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            homework_name = f"自动化测试_{current_time}"
            self.device.send_keys(homework_name)
            
            time.sleep(1)
            # 回车
            self.device.press('enter')
            time.sleep(1)
            
            # 12. 点击发布作业提交按钮
            if not self.click_coordinate('publish_submit_button'):
                logger.error("点击发布作业提交按钮失败")
                
                return False
            
            self.device.click(1152, 908)
            time.sleep(1)
            
            logger.info(f"作业发布成功: {homework_name}")
            self._add_log('INFO', f"作业发布成功: {homework_name}")
            return True

            
            
        except Exception as e:
            error_msg = f"发布作业失败: {str(e)}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
            return False
    
    def cleanup(self):
        """
        清理资源

        核心步骤：
        1. 停止APP
        2. 断开ADB连接
        """
        try:
            import subprocess

            # 停止APP
            if self.device:
                try:
                    self.device.app_stop(APP_CONFIG['package_name'])
                except Exception:
                    pass

            # 断开ADB连接
            try:
                subprocess.run(
                    f"adb disconnect {self.device_ip}",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            except Exception:
                pass
            
            # 移除自定义日志处理器
            try:
                if hasattr(self, 'memory_handler'):
                    logger.removeHandler(self.memory_handler)
                    self.memory_handler.close()
            except Exception:
                pass

            logger.info(f"资源清理完成: {self.device_ip}")

        except Exception as e:
            logger.error(f"清理资源失败: {str(e)}")

    def run_test(self) -> Dict:
        """
        执行完整的测试流程

        核心流程：
        1. 连接设备
        2. 根据配置执行发布作业流程（如果需要）
        3. 启动APP
        4. 进入作业提交界面
        5. 循环处理每个学生
        6. 提交整批作业
        7. 清理资源

        Returns:
            Dict: 测试结果
        """
        try:
            logger.info(f"开始测试设备: {self.device_ip}")
            self.test_results['start_time'] = datetime.now().isoformat()

            # 1. 连接设备
            if not self.connect_device():
                return self.test_results

            # 2. 根据配置执行发布作业流程
            if self.test_config.get('publish_homework', False):
                # 检查是否需要在当前设备上发布作业
                should_publish = True
                if self.test_config.get('publish_on_single_device_only', True):
                    # 批量测试模式，只在第一台设备上发布作业
                    should_publish = self.is_first_device
                
                if should_publish:
                    logger.info(f"在设备 {self.device_ip} 上执行发布作业流程")
                    # 先启动APP
                    if not self.launch_app():
                        logger.error("启动APP失败，无法执行发布作业流程")
                    else:
                        # 执行发布作业流程
                        publish_success = self.publish_homework()
                        if publish_success:
                            logger.info("发布作业流程完成，准备开始作业提交测试")
                            # 重新启动APP，回到主界面
                            self.device.app_stop(APP_CONFIG['package_name'])
                            time.sleep(2)
                        else:
                            logger.error("发布作业失败")
                            if self.test_config['screenshot_on_error']:
                                self.take_screenshot("publish_error")
                else:
                    logger.info(f"设备 {self.device_ip} 跳过发布作业流程（批量测试模式）")

            # 3. 启动APP（如果之前没有启动或需要重新启动）
            if not self.device.app_current()['package'] == APP_CONFIG['package_name']:
                if not self.launch_app():
                    if self.test_config['screenshot_on_error']:
                        self.take_screenshot("launch_error")
                    return self.test_results

            # 4. 点击提交作业按钮，进入作业提交界面
            if not self.click_coordinate('submit_homework_button'):
                if self.test_config['screenshot_on_error']:
                    self.take_screenshot("main_page_error")
                return self.test_results

            # 4. 处理每个学生的作业
            for i in range(self.student_count):
                logger.info(f"处理学生 {i + 1}/{self.student_count}")

                student_result = self.process_student(i)

                # 根据配置决定是否在失败时继续
                if student_result['status'] == 'failed':
                    if not ERROR_HANDLING['continue_on_error']:
                        logger.error("学生处理失败，停止测试")
                        break
                    else:
                        logger.warning("学生处理失败，继续下一个")

                # 添加操作间隔
                if i < self.student_count - 1:  # 不是最后一个学生
                    time.sleep(self.test_config.get('operation_delay', 0.5))

            # 5. 检查是否达到最少成功数量
            if self.test_results['students_success'] < ERROR_HANDLING['min_success_count']:
                error_msg = f"成功处理的学生数量不足: {self.test_results['students_success']}/{ERROR_HANDLING['min_success_count']}"
                logger.error(error_msg)
                self.test_results['errors'].append(error_msg)
                self.test_results['status'] = 'insufficient_success'
            else:
                # 6. 提交整批作业
                if self.submit_homework_batch():
                    self.test_results['status'] = 'success'
            
            # 添加测试完成时间和计算持续时间
            self.test_results['end_time'] = datetime.now().isoformat()
            
            # 计算测试持续时间
            if 'start_time' in self.test_results:
                start_time = datetime.fromisoformat(self.test_results['start_time'])
                end_time = datetime.fromisoformat(self.test_results['end_time'])
                duration = (end_time - start_time).total_seconds()
                self.test_results['duration'] = duration
            
            # 添加日志信息（从logger中获取）
            self.test_results['logs'] = [log for log in self.logs] if hasattr(self, 'logs') else []
            
            # 添加截图信息
            self.test_results['screenshots'] = self.screenshots if hasattr(self, 'screenshots') else []
            
            # 输出测试摘要
            self._print_test_summary()
            
            return self.test_results
        except Exception as e:
            logger.error(f"测试过程中发生异常: {str(e)}")
            import traceback
            error_details = traceback.format_exc()
            self.test_results['status'] = 'error'
            self.test_results['errors'].append(f"测试异常: {str(e)}")
            self.test_results['errors'].append(error_details)
            
            if self.test_config['screenshot_on_error']:
                self.take_screenshot("test_error")
            
            # 添加测试完成时间
            self.test_results['end_time'] = datetime.now().isoformat()
            
            # 添加截图信息
            self.test_results['screenshots'] = self.screenshots if hasattr(self, 'screenshots') else []
            
            return self.test_results
        except Exception as e:
            error_msg = f"测试执行异常: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self.test_results['errors'].append(error_msg)
            self.test_results['status'] = 'exception'

            if self.test_config['screenshot_on_error']:
                self.take_screenshot("exception")
                
            # 添加测试完成时间
            self.test_results['end_time'] = datetime.now().isoformat()
            
            # 添加截图信息
            self.test_results['screenshots'] = self.screenshots if hasattr(self, 'screenshots') else []
            
            return self.test_results
        finally:
            # 7. 清理资源
            self.cleanup()

            return self.test_results

    def _print_test_summary(self):
        """打印测试摘要"""
        logger.info("=" * 60)
        logger.info(f"测试完成: {self.device_ip}")
        logger.info(f"状态: {self.test_results['status']}")
        logger.info(f"处理学生数: {self.test_results['students_processed']}/{self.student_count}")
        logger.info(f"成功: {self.test_results['students_success']}")
        logger.info(f"失败: {self.test_results['students_failed']}")
        logger.info(f"耗时: {self.test_results['duration']:.2f} 秒")

        if self.test_results['errors']:
            logger.info(f"错误数: {len(self.test_results['errors'])}")
            for error in self.test_results['errors'][:3]:  # 只显示前3个错误
                logger.info(f"  - {error[:100]}")

        logger.info("=" * 60)


def prepare_for_test(device_ip: str) -> tuple:
    """
    准备测试环境

    核心步骤：
    1. 检查ADB连接
    2. 获取设备信息
    3. 检查APP是否安装

    Args:
        device_ip: 设备IP

    Returns:
        tuple: (是否准备就绪, 消息)
    """
    try:
        import subprocess

        logger.info(f"设备 {device_ip} 准备测试环境")

        # 检查ADB连接
        result = subprocess.run(
            f"adb connect {device_ip}",
            shell=True,
            capture_output=True,
            text=True
        )
        if "connected" not in result.stdout.lower():
            return False, f"ADB连接失败: {result.stdout}"

        # 检查设备状态
        try:
            # 动态导入uiautomator2
            u2, _ = import_uiautomator2()
            device = u2.connect(device_ip)
            if not device.info:
                return False, "设备信息获取失败"

            # 检查APP是否安装
            app_info = device.app_info(APP_CONFIG['package_name'])
            if not app_info:
                return False, f"APP未安装: {APP_CONFIG['package_name']}"

            return True, "准备就绪"
        except Exception as e:
            return False, f"设备检查失败: {str(e)}"

    except Exception as e:
        return False, str(e)


def execute_test(device_ip: str, custom_config: Dict[str, Any] = None, is_first_device: bool = False) -> Dict:
    """
    执行测试的入口函数

    Args:
        device_ip: 设备IP
        custom_config: 自定义配置参数
        is_first_device: 是否为批量测试中的第一台设备（用于控制发布作业）

    Returns:
        Dict: 测试结果
    """
    # 确保custom_config是字典
    if custom_config is None:
        custom_config = {}
    
    # 设置is_first_device标志
    custom_config['is_first_device'] = is_first_device
    
    tester = HomeworkTester(device_ip, custom_config)
    return tester.run_test()
