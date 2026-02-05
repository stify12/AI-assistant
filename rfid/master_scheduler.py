"""
主控调度脚本 - 管理多设备并行测试
实现设备发现、同步执行、结果汇总
"""

import os
import sys
import time
import json
import csv
import logging
import subprocess
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import schedule
except ImportError:
    print("警告: 未安装schedule库，将使用简化模式")
    schedule = None

try:
    import uiautomator2 as u2
except ImportError:
    print("错误: 未安装uiautomator2库")
    print("请运行: pip install uiautomator2")
    sys.exit(1)

# 导入配置
try:
    from config import (
        DEVICE_IPS, LOG_DIR, REPORT_DIR, SCREENSHOT_DIR, TEST_CONFIG, SYNC_CONFIG,
        REPORT_CONFIG, LOG_CONFIG, ADB_CONNECT_TIMEOUT, IMMEDIATE_EXECUTION,
        CRON_EXPRESSION, STUDENT_COUNT
    )
except ImportError as e:
    print(f"错误: 无法导入config模块 - {str(e)}")
    print("请确保config.py文件存在于当前目录")
    sys.exit(1)

# 配置日志
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_CONFIG['level'], logging.INFO),
    format=LOG_CONFIG['format'],
    datefmt=LOG_CONFIG['date_format'],
    handlers=[
        logging.FileHandler(
            os.path.join(LOG_DIR, f"master_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
            encoding='utf-8'
        ),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MasterScheduler:
    """
    主控调度器

    核心职责：
    1. 设备发现和在线检测
    2. 设备准备和同步
    3. 并行测试执行
    4. 结果汇总和报告生成
    """

    def __init__(self):
        """初始化调度器"""
        self.devices = DEVICE_IPS
        self.online_devices = []
        self.test_results = {}
        self.sync_event = threading.Event()
        self.prepare_status = {}
        self.student_count = STUDENT_COUNT  # 初始化学生数量为全局配置值

        logger.info("主控调度器初始化完成")
        logger.info(f"配置设备数: {len(self.devices)}")
        logger.info(f"每批学生数: {self.student_count}")

    def check_device_online(self, device_ip: str) -> bool:
        """
        检查设备是否在线

        核心逻辑：
        1. 尝试ADB连接
        2. 验证设备状态
        3. 返回在线状态

        Args:
            device_ip: 设备IP地址

        Returns:
            bool: 设备是否在线
        """
        try:
            logger.debug(f"检查设备状态: {device_ip}")

            # 尝试ADB连接
            result = subprocess.run(
                f"adb connect {device_ip}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=ADB_CONNECT_TIMEOUT
            )

            if "connected" in result.stdout.lower() or "already" in result.stdout.lower():
                # 验证设备状态
                result = subprocess.run(
                    f"adb -s {device_ip} shell echo 'test'",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    logger.info(f"✓ 设备在线: {device_ip}")
                    return True

            logger.warning(f"✗ 设备离线: {device_ip}")
            return False

        except subprocess.TimeoutExpired:
            logger.warning(f"✗ 设备连接超时: {device_ip}")
            return False
        except Exception as e:
            logger.warning(f"✗ 检查设备失败: {device_ip}, 错误: {str(e)}")
            return False

    def scan_online_devices(self) -> List[str]:
        """
        扫描所有在线设备

        核心流程：
        1. 使用线程池并行检测所有设备
        2. 收集在线设备列表
        3. 返回在线设备

        Returns:
            List[str]: 在线设备列表
        """
        logger.info("=" * 80)
        logger.info("开始扫描在线设备")
        logger.info("=" * 80)

        online_devices = []

        with ThreadPoolExecutor(max_workers=min(10, len(self.devices))) as executor:
            future_to_device = {
                executor.submit(self.check_device_online, device): device
                for device in self.devices
            }

            for future in as_completed(future_to_device):
                device = future_to_device[future]
                try:
                    if future.result():
                        online_devices.append(device)
                except Exception as e:
                    logger.error(f"检查设备 {device} 时出错: {str(e)}")

        self.online_devices = online_devices
        logger.info(f"在线设备数量: {len(online_devices)}/{len(self.devices)}")

        if not online_devices:
            logger.error("没有发现在线设备！")
            logger.error("请检查:")
            logger.error("1. 设备IP地址是否正确")
            logger.error("2. 设备是否已通过USB连接并启用USB调试")
            logger.error("3. 网络连接是否正常")
            logger.error("4. ADB是否已安装并在PATH中")

        return online_devices

    def prepare_device(self, device_ip: str) -> Tuple[str, bool, str]:
        """
        准备单个设备

        Args:
            device_ip: 设备IP

        Returns:
            Tuple[str, bool, str]: (设备IP, 是否准备就绪, 消息)
        """
        try:
            logger.info(f"准备设备: {device_ip}")

            # 导入测试模块
            try:
                from homework_tester import prepare_for_test
            except ImportError:
                logger.error("无法导入homework_tester模块")
                return device_ip, False, "无法导入测试模块"

            # 调用测试脚本的准备函数
            ready, msg = prepare_for_test(device_ip)

            if ready:
                logger.info(f"✓ 设备准备就绪: {device_ip}")
            else:
                logger.warning(f"✗ 设备未准备好: {device_ip} - {msg}")

            return device_ip, ready, msg

        except Exception as e:
            logger.error(f"准备设备 {device_ip} 异常: {str(e)}")
            return device_ip, False, str(e)

    def sync_prepare_devices(self) -> bool:
        """
        同步准备所有设备

        核心流程：
        1. 使用线程池并行准备所有设备
        2. 统计准备情况
        3. 返回是否全部准备就绪

        Returns:
            bool: 是否所有设备都准备就绪
        """
        logger.info("=" * 80)
        logger.info("开始同步准备所有设备")
        logger.info("=" * 80)

        self.prepare_status = {}

        with ThreadPoolExecutor(max_workers=min(10, len(self.online_devices))) as executor:
            futures = [
                executor.submit(self.prepare_device, device)
                for device in self.online_devices
            ]

            for future in as_completed(futures):
                device_ip, ready, msg = future.result()
                self.prepare_status[device_ip] = {
                    'ready': ready,
                    'message': msg
                }

        # 统计准备情况
        ready_count = sum(1 for status in self.prepare_status.values() if status['ready'])
        total_count = len(self.online_devices)

        logger.info(f"设备准备情况: {ready_count}/{total_count}")

        # 输出未准备好的设备
        for device, status in self.prepare_status.items():
            if not status['ready']:
                logger.warning(f"✗ 设备 {device} 未准备好: {status['message']}")

        return ready_count == total_count

    def execute_device_test(self, device_ip: str) -> Dict:
        """
        执行单个设备的测试

        核心流程：
        1. 等待同步信号
        2. 创建测试器实例
        3. 执行测试
        4. 返回结果

        Args:
            device_ip: 设备IP

        Returns:
            Dict: 测试结果
        """
        try:
            logger.info(f"[{device_ip}] 等待同步信号...")

            # 等待同步信号（所有设备同时开始）
            self.sync_event.wait()

            logger.info(f"[{device_ip}] 收到同步信号，开始测试")

            # 导入测试模块
            try:
                from homework_tester import HomeworkTester
            except ImportError:
                logger.error(f"[{device_ip}] 无法导入HomeworkTester模块")
                return {
                    'device_ip': device_ip,
                    'status': 'import_error',
                    'errors': ['无法导入测试模块']
                }

            # 创建测试器并执行测试
            tester = HomeworkTester(device_ip)
            test_result = tester.run_test()

            logger.info(f"[{device_ip}] 测试完成，状态: {test_result.get('status')}")
            return test_result

        except Exception as e:
            logger.error(f"[{device_ip}] 测试异常: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'device_ip': device_ip,
                'status': 'exception',
                'errors': [str(e)]
            }

    def run_parallel_tests(self) -> Dict[str, Dict]:
            """
            并行执行所有设备的测试

            核心流程：
            1. 获取准备就绪的设备
            2. 使用线程池并行执行测试
            3. 倒计时后触发同步执行
            4. 收集所有测试结果

            Returns:
                Dict[str, Dict]: 所有设备的测试结果
            """
            logger.info("=" * 80)
            logger.info("开始并行执行测试")
            logger.info("=" * 80)

            test_results = {}

            # 获取准备就绪的设备
            ready_devices = [
                device for device, status in self.prepare_status.items()
                if status['ready']
            ]

            if not ready_devices:
                logger.error("没有设备准备就绪")
                return test_results

            logger.info(f"准备执行测试的设备数: {len(ready_devices)}")

            with ThreadPoolExecutor(max_workers=len(ready_devices)) as executor:
                # 提交所有测试任务
                future_to_device = {
                    executor.submit(self.execute_device_test, device): device
                    for device in ready_devices
                }

                # 倒计时后触发同步执行
                logger.info("=" * 80)
                for i in range(3, 0, -1):
                    logger.info(f"测试将在 {i} 秒后同时开始...")
                    time.sleep(1)

                # 触发同步信号，所有设备同时开始
                logger.info("=" * 80)
                logger.info("✓ 触发同步测试信号 - 所有设备同时开始")
                logger.info("=" * 80)
                self.sync_event.set()

                # 收集测试结果
                completed = 0
                for future in as_completed(future_to_device):
                    device = future_to_device[future]
                    try:
                        result = future.result()
                        test_results[device] = result
                        completed += 1

                        # 实时输出测试状态
                        status = result.get('status', 'unknown')
                        success = result.get('students_success', 0)
                        failed = result.get('students_failed', 0)

                        logger.info(f"[{device}] 测试完成 ({completed}/{len(ready_devices)})")
                        logger.info(f"  状态: {status}")
                        logger.info(f"  成功: {success}, 失败: {failed}")

                    except Exception as e:
                        logger.error(f"获取设备 {device} 测试结果失败: {str(e)}")
                        test_results[device] = {
                            'device_ip': device,
                            'status': 'result_error',
                            'errors': [str(e)]
                        }

            # 重置同步事件
            self.sync_event.clear()

            self.test_results = test_results
            return test_results

    def execute_test_batch(self, custom_config: Dict = None):
        """
        执行批量测试
        
        核心流程：
        1. 扫描在线设备
        2. 准备所有设备
        3. 先让一台设备执行发布作业
        4. 等待发布作业完成
        5. 并行执行测试
        6. 生成报告
        
        Args:
            custom_config: 自定义配置参数
        """
        # 如果有自定义配置，更新模块配置
        if custom_config:
            # 更新测试配置
            if 'operation_delay' in custom_config:
                TEST_CONFIG['operation_delay'] = custom_config['operation_delay']
            if 'screenshot_on_error' in custom_config:
                TEST_CONFIG['screenshot_on_error'] = custom_config['screenshot_on_error']
            if 'student_count' in custom_config:
                # 使用实例变量存储修改后的学生数量
                self.student_count = custom_config['student_count']
            else:
                # 如果没有自定义值，使用全局配置
                self.student_count = STUDENT_COUNT
            if 'rfid_cards' in custom_config:
                TEST_CONFIG['rfid_cards'] = custom_config['rfid_cards']
            
        # 1. 扫描在线设备
        online_devices = self.scan_online_devices()
        if not online_devices:
            logger.error("没有发现在线设备，无法进行批量测试")
            return
        
        # 2. 准备所有设备
        all_ready = self.sync_prepare_devices()
        if not all_ready:
            logger.warning("部分设备未准备就绪，将继续测试已准备好的设备")
        
        # 3. 选择一台设备先执行发布作业
        publish_device = None
        ready_devices = [device for device, status in self.prepare_status.items() if status['ready']]
        
        if ready_devices:
            # 选择第一台准备好的设备作为发布作业的设备
            publish_device = ready_devices[0]
            logger.info(f"选择设备 {publish_device} 执行发布作业")
            
            try:
                # 导入测试模块
                from homework_tester import HomeworkTester
                
                # 创建发布作业专用的配置
                publish_config = custom_config.copy() if custom_config else {}
                publish_config['publish_homework'] = True
                publish_config['is_first_device'] = True
                
                # 创建测试器实例
                publisher_tester = HomeworkTester(publish_device, publish_config)
                
                # 只执行发布作业，不执行完整测试
                if publisher_tester.connect_device():
                    # 启动APP
                    if publisher_tester.launch_app():
                        # 执行发布作业
                        publish_success = publisher_tester.publish_homework()
                        if publish_success:
                            logger.info(f"设备 {publish_device} 发布作业成功，等待其他设备开始测试")
                            # 重新启动APP，回到主界面
                            publisher_tester.device.app_stop(APP_CONFIG['package_name'])
                        else:
                            logger.error(f"设备 {publish_device} 发布作业失败")
                    
                    # 清理资源
                    publisher_tester.cleanup()
                
                # 等待一段时间，确保作业发布完全生效
                logger.info("等待作业发布生效...")
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"执行发布作业过程中出错: {str(e)}")
        
        # 4. 并行执行测试
        # 为所有设备创建配置，确保不重复发布作业
        test_config = custom_config.copy() if custom_config else {}
        test_config['publish_homework'] = False
        
        # 更新模块配置
        if 'operation_delay' in test_config:
            TEST_CONFIG['operation_delay'] = test_config['operation_delay']
        if 'screenshot_on_error' in test_config:
            TEST_CONFIG['screenshot_on_error'] = test_config['screenshot_on_error']
        if 'rfid_cards' in test_config:
            TEST_CONFIG['rfid_cards'] = test_config['rfid_cards']
        
        results = self.run_parallel_tests()
        
        # 5. 生成报告
        if results:
            csv_file = self.generate_csv_report(results)
            logger.info(f"测试报告已生成: {csv_file}")
            
            # 统计总体结果
            total_success = sum(r.get('students_success', 0) for r in results.values())
            total_failed = sum(r.get('students_failed', 0) for r in results.values())
            logger.info(f"总体测试结果: 成功 {total_success}, 失败 {total_failed}")
        
    def generate_csv_report(self, results: Dict[str, Dict]) -> str:
        """
        生成CSV格式的测试报告

        核心步骤：
        1. 遍历所有测试结果
        2. 提取关键数据
        3. 写入CSV文件

        Args:
            results: 测试结果

        Returns:
            str: 报告文件路径
        """
        report_path = os.path.join(REPORT_DIR, REPORT_CONFIG['report_filename'])

        try:
            os.makedirs(REPORT_DIR, exist_ok=True)

            with open(report_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    '设备IP', '测试状态', '开始时间', '结束时间',
                    '持续时间(秒)', '处理学生数', '成功数', '失败数', '错误数', '错误信息'
                ]

                writer = csv.DictWriter(
                    csvfile,
                    fieldnames=fieldnames,
                    delimiter=REPORT_CONFIG['csv_delimiter']
                )

                writer.writeheader()

                for device_ip, result in results.items():
                    errors = result.get('errors', [])
                    error_msg = '; '.join(errors[:3]) if errors else ''

                    writer.writerow({
                        '设备IP': device_ip,
                        '测试状态': result.get('status', 'unknown'),
                        '开始时间': result.get('start_time', ''),
                        '结束时间': result.get('end_time', ''),
                        '持续时间(秒)': f"{result.get('duration', 0):.2f}",
                        '处理学生数': result.get('students_processed', 0),
                        '成功数': result.get('students_success', 0),
                        '失败数': result.get('students_failed', 0),
                        '错误数': len(errors),
                        '错误信息': error_msg[:100]
                    })

                logger.info(f"✓ CSV报告已生成: {report_path}")
                return report_path

        except Exception as e:
            logger.error(f"生成CSV报告失败: {str(e)}")
            return ""

    def generate_summary_report(self, results: Dict[str, Dict]) -> str:
        """
        生成测试摘要报告

        核心步骤：
        1. 统计汇总数据
        2. 生成摘要内容
        3. 写入文件并输出

        Args:
            results: 测试结果

        Returns:
            str: 摘要报告路径
        """
        summary_path = os.path.join(REPORT_DIR, REPORT_CONFIG['summary_filename'])

        try:
            os.makedirs(REPORT_DIR, exist_ok=True)

            # 统计数据
            total_devices = len(results)
            success_count = sum(1 for r in results.values() if r.get('status') == 'success')
            failed_count = total_devices - success_count

            total_students = sum(r.get('students_processed', 0) for r in results.values())
            total_success = sum(r.get('students_success', 0) for r in results.values())
            total_failed = sum(r.get('students_failed', 0) for r in results.values())

            total_duration = sum(r.get('duration', 0) for r in results.values())
            avg_duration = total_duration / total_devices if total_devices > 0 else 0

            # 计算成功率
            device_success_rate = (success_count / total_devices * 100) if total_devices > 0 else 0
            student_success_rate = (total_success / total_students * 100) if total_students > 0 else 0

            # 生成摘要内容
            summary_content = f"""
{'=' * 80}
                            批量作业上传测试报告
{'=' * 80}

测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
配置设备数: {len(DEVICE_IPS)}
在线设备数: {len(self.online_devices)}
执行测试数: {total_devices}

{'-' * 80}
测试结果统计:
{'-' * 80}
成功设备数: {success_count}
失败设备数: {failed_count}
设备成功率: {device_success_rate:.2f}%

处理学生总数: {total_students}
成功上传学生数: {total_success}
失败上传学生数: {total_failed}
学生处理成功率: {student_success_rate:.2f}%

平均每设备处理: {total_students / total_devices:.1f} 个学生
总耗时: {total_duration:.2f} 秒
平均耗时: {avg_duration:.2f} 秒/设备

{'-' * 80}
设备详情:
{'-' * 80}
"""

            # 添加每个设备的详细信息
            for device_ip, result in results.items():
                status_emoji = "✓" if result.get('status') == 'success' else "✗"
                summary_content += f"\n{status_emoji} {device_ip}:"
                summary_content += f"\n  状态: {result.get('status', 'unknown')}"
                summary_content += f"\n  处理学生数: {result.get('students_processed', 0)}"
                summary_content += f"\n  成功数: {result.get('students_success', 0)}"
                summary_content += f"\n  失败数: {result.get('students_failed', 0)}"
                summary_content += f"\n  耗时: {result.get('duration', 0):.2f} 秒"

                if result.get('errors'):
                    error_preview = result['errors'][0][:80]
                    summary_content += f"\n  错误: {error_preview}..."

                summary_content += "\n"

            summary_content += f"""
{'-' * 80}
报告文件:
{'-' * 80}
CSV详细报告: {REPORT_CONFIG['report_filename']}
日志目录: {LOG_DIR}
截图目录: {SCREENSHOT_DIR}

{'=' * 80}
"""

            # 写入文件
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary_content)

            # 同时输出到控制台
            print(summary_content)

            logger.info(f"✓ 摘要报告已生成: {summary_path}")
            return summary_path

        except Exception as e:
            logger.error(f"生成摘要报告失败: {str(e)}")
            return ""

        def schedule_tests(self):
            """
            配置定时任务

            核心逻辑：
            - 如果IMMEDIATE_EXECUTION为True，立即执行
            - 否则根据CRON表达式设置定时任务
            """
            if IMMEDIATE_EXECUTION:
                logger.info("立即执行模式，直接开始测试")
                self.execute_test_batch()
            else:
                if schedule is None:
                    logger.warning("schedule库未安装，将直接执行测试")
                    self.execute_test_batch()
                    return

                logger.info(f"定时任务模式，CRON表达式: {CRON_EXPRESSION}")

                # 解析CRON表达式并设置定时任务
                parts = CRON_EXPRESSION.split()
                if len(parts) >= 2:
                    try:
                        hour = int(parts[1])
                        minute = int(parts[0])

                        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self.execute_test_batch)

                        logger.info(f"定时任务已设置: 每天 {hour:02d}:{minute:02d} 执行")

                        # 持续运行
                        while True:
                            schedule.run_pending()
                            time.sleep(60)  # 每分钟检查一次
                    except Exception as e:
                        logger.error(f"设置定时任务失败: {str(e)}")
                        self.execute_test_batch()
                else:
                    logger.error("CRON表达式格式错误")
                    self.execute_test_batch()  # 出错时直接执行

                def run(self):
                    """
                    运行主控调度器

                    核心流程：
                    1. 初始化调度器
                    2. 配置定时任务或立即执行
                    3. 处理异常和中断
                    """
                    logger.info("=" * 80)
                    logger.info("主控调度器启动")
                    logger.info("=" * 80)

                    try:
                        self.schedule_tests()
                    except KeyboardInterrupt:
                        logger.info("\n收到中断信号，正在退出...")
                    except Exception as e:
                        logger.error(f"主控调度器异常: {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())
                    finally:
                        logger.info("主控调度器退出")

                def check_environment():
                    """
                    检查运行环境

                    检查项：
                    1. Python版本
                    2. 必要的依赖库
                    3. ADB工具
                    4. 配置文件
                    """
                    print("\n" + "=" * 80)
                    print("环境检查")
                    print("=" * 80)

                    # 检查Python版本
                    print(f"✓ Python版本: {sys.version.split()[0]}")
                    if sys.version_info < (3, 6):
                        print("✗ Python版本过低，需要3.6或更高")
                        return False

                    # 检查依赖库
                    print("\n检查依赖库:")

                    try:
                        import uiautomator2
                        print("✓ uiautomator2 已安装")
                    except ImportError:
                        print("✗ uiautomator2 未安装")
                        print("  请运行: pip install uiautomator2")
                        return False

                    try:
                        import schedule
                        print("✓ schedule 已安装")
                    except ImportError:
                        print("⚠ schedule 未安装（可选，不影响基本功能）")
                        print("  请运行: pip install schedule")

                    # 检查ADB工具
                    print("\n检查ADB工具:")
                    try:
                        result = subprocess.run(
                            "adb version",
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if result.returncode == 0:
                            print("✓ ADB 已安装")
                        else:
                            print("✗ ADB 未正确安装")
                            return False
                    except Exception as e:
                        print(f"✗ ADB 检查失败: {str(e)}")
                        return False

                    # 检查配置文件
                    print("\n检查配置文件:")
                    if os.path.exists('config.py'):
                        print("✓ config.py 已存在")
                    else:
                        print("✗ config.py 不存在")
                        return False

                    if os.path.exists('homework_tester.py'):
                        print("✓ homework_tester.py 已存在")
                    else:
                        print("✗ homework_tester.py 不存在")
                        return False

                    if os.path.exists('rfid_sender.py'):
                        print("✓ rfid_sender.py 已存在")
                    else:
                        print("✗ rfid_sender.py 不存在")
                        return False

                    print("\n" + "=" * 80)
                    print("✓ 环境检查完成，所有依赖已就绪")
                    print("=" * 80 + "\n")

                    return True

                def main():
                    """主函数"""
                    print("""
                    ╔══════════════════════════════════════════════════════════╗
                    ║      安卓作业批阅一体机自动化测试系统                    ║
                    ║              Master Scheduler v1.0                       ║
                    ╚══════════════════════════════════════════════════════════╝
                        """)

                    # 检查环境
                    if not check_environment():
                        print("环境检查失败，请按照提示安装必要的依赖")
                        sys.exit(1)

                    # 启动调度器
                    try:
                        scheduler = MasterScheduler()
                        scheduler.run()
                    except KeyboardInterrupt:
                        print("\n程序已中止")
                        sys.exit(0)
                    except Exception as e:
                        print(f"程序异常: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        sys.exit(1)

                if __name__ == "__main__":
                    main()

