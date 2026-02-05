"""
增强版测试启动脚本 - 支持自定义参数和更友好的菜单操作
"""

import os
import sys
import subprocess
import json
from typing import Dict, Any

def clear_screen():
    """清屏函数"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_title():
    """打印标题"""
    print("""
╔══════════════════════════════════════════════════════════╗
║      安卓作业批阅一体机自动化测试系统                    ║
║              Test Runner v2.0                            ║
╚══════════════════════════════════════════════════════════╝
    """)

def load_custom_config() -> Dict[str, Any]:
    """加载自定义配置"""
    if os.path.exists('custom_config.json'):
        try:
            with open('custom_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告: 无法加载自定义配置文件 - {str(e)}")
    return {}

def save_custom_config(config: Dict[str, Any]):
    """保存自定义配置"""
    try:
        with open('custom_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print("✓ 自定义配置已保存")
    except Exception as e:
        print(f"错误: 保存自定义配置失败 - {str(e)}")

def show_help():
    """显示帮助信息"""
    clear_screen()
    print_title()
    print("\n使用教程:")
    print("="*60)
    print("1. 快速测试: 对单个设备进行测试")
    print("   - 输入设备IP地址（格式: IP:PORT）")
    print("   - 系统会自动检测RFID输入设备并执行测试")
    print("\n2. 批量测试: 对多个设备同时进行测试")
    print("   - 系统会自动扫描配置文件中的所有设备")
    print("   - 支持并行执行，提高测试效率")
    print("\n3. 设备扫描: 扫描当前在线的设备")
    print("   - 显示所有可连接的设备列表")
    print("\n4. 自定义参数: 配置测试参数")
    print("   - 可以设置学生数量、RFID卡号等")
    print("   - 配置会自动保存供下次使用")
    print("\n5. RFID设备检测: 单独检测RFID输入设备")
    print("   - 帮助确认设备路径是否正确")
    print("\n7. 退出: 退出程序")
    print("\n使用提示:")
    print("- 确保设备已开启USB调试模式")
    print("- 设备IP地址可以在设置-关于手机-状态信息中查看")
    print("- 测试过程中请勿操作设备")
    print("="*60)
    input("\n按回车键返回主菜单...")

def custom_parameters_menu(custom_config: Dict[str, Any]):
    """自定义参数菜单"""
    while True:
        clear_screen()
        print_title()
        print("\n自定义测试参数:")
        print("1. 设置学生数量 (当前: {})".format(custom_config.get('student_count', '默认')))
        print("2. 自定义RFID卡号列表")
        print("3. 设置操作延迟时间 (当前: {}秒)".format(custom_config.get('operation_delay', '默认')))
        print("4. 设置截图选项 (当前: {})".format(
            '开启' if custom_config.get('screenshot_on_error', True) else '关闭'
        ))
        print("5. 保存并返回主菜单")
        
        choice = input("\n请选择 (1-5): ").strip()
        
        if choice == '1':
            try:
                count = input("请输入学生数量 (默认: 30): ").strip()
                if count:
                    custom_config['student_count'] = int(count)
                    print(f"✓ 学生数量已设置为: {count}")
                    input("按回车键继续...")
            except ValueError:
                print("错误: 请输入有效的数字")
                input("按回车键继续...")
        
        elif choice == '2':
            print("\n自定义RFID卡号列表:")
            print("1. 从文件导入")
            print("2. 手动输入")
            sub_choice = input("请选择 (1-2): ").strip()
            
            if sub_choice == '1':
                filepath = input("请输入文件路径: ").strip()
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            rfid_list = [line.strip() for line in f if line.strip()]
                        if rfid_list:
                            custom_config['rfid_cards'] = rfid_list
                            print(f"✓ 成功导入 {len(rfid_list)} 个RFID卡号")
                    except Exception as e:
                        print(f"错误: 导入失败 - {str(e)}")
                else:
                    print("错误: 文件不存在")
                input("按回车键继续...")
            
            elif sub_choice == '2':
                print("请输入RFID卡号，每行一个，输入空行结束:")
                rfid_list = []
                while True:
                    rfid = input().strip()
                    if not rfid:
                        break
                    rfid_list.append(rfid)
                if rfid_list:
                    custom_config['rfid_cards'] = rfid_list
                    print(f"✓ 已设置 {len(rfid_list)} 个RFID卡号")
                input("按回车键继续...")
        
        elif choice == '3':
            try:
                delay = input("请输入操作延迟时间 (秒，默认: 0.5): ").strip()
                if delay:
                    custom_config['operation_delay'] = float(delay)
                    print(f"✓ 操作延迟已设置为: {delay}秒")
                    input("按回车键继续...")
            except ValueError:
                print("错误: 请输入有效的数字")
                input("按回车键继续...")
        
        elif choice == '4':
            screenshot_choice = input("是否在错误时截图? (y/n，默认: y): ").strip().lower()
            custom_config['screenshot_on_error'] = screenshot_choice != 'n'
            print(f"✓ 截图选项已设置为: {'开启' if custom_config['screenshot_on_error'] else '关闭'}")
            input("按回车键继续...")
        
        elif choice == '5':
            save_custom_config(custom_config)
            break

def test_rfid_detection():
    """测试RFID设备检测功能"""
    device_ip = input("请输入设备IP: ").strip()
    if device_ip:
        print(f"\n开始检测设备: {device_ip} 的RFID输入设备...")
        try:
            from rfid_sender import RfidSender
            import logging
            
            # 设置临时日志级别为INFO，确保用户能看到详细信息
            logger = logging.getLogger("rfid_sender")
            original_level = logger.level
            logger.setLevel(logging.INFO)
            
            rfid_sender = RfidSender(device_ip)
            device_path = rfid_sender.detect_input_device()
            
            # 恢复原日志级别
            logger.setLevel(original_level)
            
            if device_path:
                print(f"✓ 成功检测到RFID输入设备: {device_path}")
                print(f"✓ 设备路径已自动设置为: {device_path}")
            else:
                print("✗ 未检测到有效的RFID输入设备")
                print("\n手动配置指南:")
                print("1. 请检查设备是否已正确连接并开启USB调试")
                print("2. 尝试手动查看设备输入设备列表:")
                print(f"   adb -s {device_ip} shell ls -la /dev/input/")
                print("3. 在config.py中修改RFID_DEVICE_PATH为正确的设备路径")
                print("   通常类似: /dev/input/event0, /dev/input/event1 等")
                print("4. 如果不确定，可以尝试逐个测试可能的event设备")
        except Exception as e:
            print(f"✗ 检测失败: {str(e)}")
            print("\n请检查:")
            print("1. 设备IP地址是否正确")
            print("2. 设备是否已连接并开启USB调试")
            print("3. ADB是否已正确安装并在系统PATH中")
        input("按回车键返回主菜单...")

def view_latest_log():
    """查看最新的日志文件"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(log_dir):
        print("错误: 日志目录不存在")
        input("按回车键返回主菜单...")
        return
    
    # 获取所有日志文件并按时间排序
    log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
    if not log_files:
        print("错误: 没有找到日志文件")
        input("按回车键返回主菜单...")
        return
    
    # 按文件名排序（假设文件名包含时间戳）
    log_files.sort(reverse=True)
    latest_log = os.path.join(log_dir, log_files[0])
    
    print(f"\n显示最新日志文件: {log_files[0]}")
    print("="*60)
    try:
        # 读取日志文件的最后100行
        with open(latest_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()[-100:]
            for line in lines:
                print(line.strip())
    except Exception as e:
        print(f"错误: 无法读取日志文件 - {str(e)}")
    
    print("="*60)
    input("按回车键返回主菜单...")

def main():
    """主函数"""
    # 加载自定义配置
    custom_config = load_custom_config()
    
    while True:
        clear_screen()
        print_title()

        # 检查config.py
        if not os.path.exists('config.py'):
            print("错误: 找不到config.py文件")
            print("请确保config.py与此脚本在同一目录")
            input("按回车键退出...")
            sys.exit(1)

        # 检查其他必要文件
        required_files = ['homework_tester.py', 'rfid_sender.py', 'master_scheduler.py']
        missing_files = [file for file in required_files if not os.path.exists(file)]
        
        if missing_files:
            for file in missing_files:
                print(f"错误: 找不到{file}文件")
            input("按回车键退出...")
            sys.exit(1)

        print("✓ 所有必要文件已找到")
        print("\n请选择功能:")
        print("1. 快速测试 ")
        print("2. 批量测试 ")
        print("3. 设备扫描 ")
        print("4. 自定义参数 ")
        print("5. RFID设备检测 ")
        print("6. 查看日志 ")
     

        choice = input("\n请选择 (1-6): ").strip()

        if choice == '1':
            # 快速测试
            clear_screen()
            print_title()
            print("\n正在扫描在线设备...")
            
            # 扫描在线设备
            try:
                from master_scheduler import MasterScheduler
                scheduler = MasterScheduler()
                devices = scheduler.scan_online_devices()
                
                if devices:
                    print(f"\n发现 {len(devices)} 个在线设备:")
                    for i, device in enumerate(devices, 1):
                        print(f"  {i}. {device}")
                    
                    print("\n请选择要测试的设备:")
                    print("  输入设备编号 (1-{0}) 快速选择设备".format(len(devices)))
                    print("  或直接输入设备IP地址进行测试")
                    user_input = input("\n请输入: ").strip()
                    
                    # 处理用户输入
                    if user_input.isdigit():
                        idx = int(user_input) - 1
                        if 0 <= idx < len(devices):
                            device_ip = devices[idx]
                            print(f"\n已选择设备: {device_ip}")
                        else:
                            print("\n无效的设备编号")
                            input("按回车键继续...")
                            continue
                    elif user_input:
                        # 直接输入的IP地址
                        device_ip = user_input
                        print(f"\n将测试设备: {device_ip}")
                    else:
                        print("\n操作已取消")
                        input("按回车键继续...")
                        continue
                else:
                    print("\n未发现在线设备")
                    print("请直接输入设备IP地址进行测试，或检查设备连接")
                    device_ip = input("\n设备IP地址: ").strip()
                    if not device_ip:
                        print("\n操作已取消")
                        input("按回车键继续...")
                        continue
                
                # 开始测试
                print(f"\n开始测试设备: {device_ip}")
                print("="*60)
                try:
                    # 传递自定义配置并设置为第一台设备，以启用发布作业功能
                    from homework_tester import execute_test
                    
                    print("[步骤1] 准备开始测试...")
                    
                    # 确保在快速测试中启用发布作业
                    if 'publish_homework' not in custom_config:
                        custom_config['publish_homework'] = True
                    
                    print("[步骤2] 执行测试流程（包含发布作业、学生处理、批量提交）...")
                    result = execute_test(device_ip, custom_config, is_first_device=True)
                    
                    print("="*60)
                    print("[测试结果摘要]")
                    print(f"测试状态: {result.get('status', 'unknown')}")
                    print(f"总耗时: {result.get('duration', 0):.2f} 秒")
                    print("="*60)
                    print("[详细处理步骤]")
                    
                    # 输出详细的处理步骤
                    print("✅ 1. 发布作业: " + ("成功" if any("作业发布成功" in log for log in result.get('logs', [])) else "未执行"))
                    print(f"✅ 2. 学生处理: 共处理 {result.get('students_processed', 0)} 名学生")
                    print(f"   - 成功: {result.get('students_success', 0)} 名")
                    print(f"   - 失败: {result.get('students_failed', 0)} 名")
                    print("✅ 3. 批量提交: " + ("成功" if result.get('status') == 'success' else "失败"))
                    
                    # 显示任何错误信息
                    if result.get('errors'):
                        print("\n[错误信息]")
                        for i, error in enumerate(result.get('errors', []), 1):
                            print(f"   {i}. {error[:100]}..." if len(error) > 100 else f"   {i}. {error}")
                    
                    # 显示截图信息
                    if result.get('screenshots'):
                        print(f"\n[截图信息] 共生成 {len(result.get('screenshots', []))} 张截图")
                    
                except Exception as e:
                    print(f"\n❌ 测试过程中出错: {str(e)}")
                    import traceback
                    print("\n错误详情:")
                    traceback.print_exc()
                input("\n按回车键返回主菜单...")
            except Exception as e:
                print(f"\n❌ 设备扫描过程中出错: {str(e)}")
                input("按回车键继续...")

        elif choice == '2':
            # 批量测试
            print("\n开始批量测试...")
            try:
                from master_scheduler import MasterScheduler
                scheduler = MasterScheduler()
                scheduler.execute_test_batch(custom_config)
            except Exception as e:
                print(f"批量测试过程中出错: {str(e)}")
            input("\n按回车键返回主菜单...")

        elif choice == '3':
            # 设备扫描
            print("\n开始扫描在线设备...")
            try:
                from master_scheduler import MasterScheduler
                scheduler = MasterScheduler()
                devices = scheduler.scan_online_devices()
                if devices:
                    print(f"\n发现 {len(devices)} 个在线设备:")
                    for i, device in enumerate(devices, 1):
                        print(f"  {i}. {device}")
                    
                    # 提供快速选择功能
                    test_choice = input("\n输入设备编号进行测试，或按回车键返回: ").strip()
                    if test_choice.isdigit():
                        idx = int(test_choice) - 1
                        if 0 <= idx < len(devices):
                            print(f"\n开始测试设备: {devices[idx]}")
                            from homework_tester import execute_test
                            result = execute_test(devices[idx], custom_config)
                            print(f"\n测试完成，状态: {result.get('status')}")
                else:
                    print("未发现在线设备")
            except Exception as e:
                print(f"扫描过程中出错: {str(e)}")
            input("按回车键返回主菜单...")
        
        elif choice == '4':
            # 自定义参数
            custom_parameters_menu(custom_config)
        
        elif choice == '5':
            # RFID设备检测
            test_rfid_detection()
        
        elif choice == '6':
            # 查看日志
            view_latest_log()
        
 

        elif choice == 'q':
            print("退出")
            sys.exit(0)

        else:
            print("无效的选择")
            input("按回车键继续...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已中止")
        sys.exit(0)
    except Exception as e:
        print(f"程序异常: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
