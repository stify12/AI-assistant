#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
本地测试工作流步骤 - 交互式调试，可单步执行、调整坐标和等待时间
"""

import subprocess
import time
import argparse
import json
import os
from datetime import datetime

# 设备 IP（默认值）
DEVICE_IP = "192.168.4.143"

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "workflow_config.json")

# 默认坐标配置（可通过配置文件覆盖）
DEFAULT_COORDINATES = {
    'login_entry_button': {'x': 370, 'y': 600, 'wait': 2, 'desc': '登录入口按钮'},
    'teacher_login_button': {'x': 1800, 'y': 70, 'wait': 2, 'desc': '教师登录按钮'},
    'username_input': {'x': 930, 'y': 426, 'wait': 0.5, 'desc': '用户名输入框'},
    'username_input_alt': {'x': 1230, 'y': 430, 'wait': 0.5, 'desc': '用户名输入框(备用)'},
    'password_input': {'x': 880, 'y': 530, 'wait': 0.5, 'desc': '密码输入框'},
    'password_input_alt': {'x': 1230, 'y': 540, 'wait': 0.5, 'desc': '密码输入框(备用)'},
    'login_submit_button': {'x': 960, 'y': 670, 'wait': 3, 'desc': '登录提交按钮'},
    'publish_homework_button': {'x': 400, 'y': 560, 'wait': 2, 'desc': '发布作业按钮'},
    'select_page_button': {'x': 870, 'y': 379, 'wait': 1, 'desc': '选择页码按钮'},
    'page_number_selector': {'x': 659, 'y': 233, 'wait': 0.5, 'desc': '页码选择器'},
    'page_number_select_button': {'x': 830, 'y': 230, 'wait': 0.5, 'desc': '页码确认按钮'},
    'confirm_page_button': {'x': 950, 'y': 900, 'wait': 1, 'desc': '确认页码按钮'},
    'homework_name_input': {'x': 833, 'y': 557, 'wait': 0.5, 'desc': '作业名称输入框'},
    'publish_submit_button': {'x': 960, 'y': 960, 'wait': 3, 'desc': '发布作业提交按钮'},
    'final_confirm_button': {'x': 1152, 'y': 908, 'wait': 2, 'desc': '最终确认按钮'},
}

# 全局坐标配置
COORDINATES = {}


def load_config():
    """加载配置文件"""
    global COORDINATES
    COORDINATES = DEFAULT_COORDINATES.copy()
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                for key, val in saved.items():
                    if key in COORDINATES:
                        COORDINATES[key].update(val)
                    else:
                        COORDINATES[key] = val
            print(f"✓ 已加载配置: {CONFIG_FILE}")
        except Exception as e:
            print(f"⚠ 加载配置失败: {e}")
    else:
        print("✓ 使用默认配置")


def save_config():
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(COORDINATES, f, ensure_ascii=False, indent=2)
        print(f"✓ 配置已保存: {CONFIG_FILE}")
    except Exception as e:
        print(f"✗ 保存配置失败: {e}")


def run_cmd(cmd: str, timeout: int = 10) -> tuple:
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=timeout
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def check_connection(device_ip: str) -> bool:
    """检查 ADB 连接"""
    print(f"\n{'='*50}")
    print(f"检查设备连接: {device_ip}")
    print('='*50)
    
    # 连接设备
    print(f"  → adb connect {device_ip}")
    success, output = run_cmd(f"adb connect {device_ip}")
    print(f"    {output.strip()}")
    
    # 检查设备状态
    success, output = run_cmd("adb devices")
    if device_ip in output and "device" in output:
        print(f"  ✓ 设备已连接")
        return True
    else:
        print(f"  ✗ 设备未就绪")
        return False


def launch_app(device_ip: str, package_name: str = "com.zpzn.terminal", wait: float = 5) -> bool:
    """启动应用"""
    print(f"\n{'─'*50}")
    print(f"[启动应用] {package_name}")
    print(f"  等待时间: {wait}s")
    print('─'*50)
    
    # 先停止应用
    print(f"  → 停止应用...")
    run_cmd(f"adb -s {device_ip} shell am force-stop {package_name}")
    time.sleep(1)
    
    # 使用 monkey 启动
    cmd = f"adb -s {device_ip} shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
    print(f"  → {cmd}")
    success, output = run_cmd(cmd)
    
    if "No activities found" in output:
        print(f"  ✗ 未找到应用")
        return False
    
    print(f"  ✓ 应用启动命令已发送")
    print(f"  → 等待 {wait} 秒...")
    time.sleep(wait)
    return True


def click(device_ip: str, x: int, y: int, desc: str = "", wait: float = 1) -> bool:
    """点击指定坐标"""
    print(f"\n{'─'*50}")
    print(f"[点击] {desc}")
    print(f"  坐标: ({x}, {y})")
    print(f"  等待: {wait}s")
    print('─'*50)
    
    cmd = f"adb -s {device_ip} shell input tap {x} {y}"
    print(f"  → {cmd}")
    success, output = run_cmd(cmd)
    
    if success:
        print(f"  ✓ 点击成功")
        if wait > 0:
            print(f"  → 等待 {wait} 秒...")
            time.sleep(wait)
        return True
    else:
        print(f"  ✗ 点击失败: {output}")
        return False


def click_coord(device_ip: str, coord_name: str) -> bool:
    """通过坐标名点击"""
    coord = COORDINATES.get(coord_name)
    if not coord:
        print(f"  ✗ 未找到坐标配置: {coord_name}")
        return False
    
    return click(
        device_ip,
        coord['x'],
        coord['y'],
        coord.get('desc', coord_name),
        coord.get('wait', 1)
    )


def input_text(device_ip: str, text: str, wait: float = 0.5) -> bool:
    """输入文本"""
    print(f"\n{'─'*50}")
    print(f"[输入文本] {text}")
    print('─'*50)
    
    escaped = text.replace(' ', '%s')
    cmd = f'adb -s {device_ip} shell input text "{escaped}"'
    print(f"  → {cmd}")
    success, output = run_cmd(cmd)
    
    if success:
        print(f"  ✓ 输入成功")
        if wait > 0:
            time.sleep(wait)
        return True
    else:
        print(f"  ✗ 输入失败: {output}")
        return False


def press_key(device_ip: str, key: str, wait: float = 0.5) -> bool:
    """按键"""
    key_map = {'enter': 66, 'back': 4, 'home': 3, 'tab': 61}
    keycode = key_map.get(key.lower(), key)
    
    print(f"\n{'─'*50}")
    print(f"[按键] {key} (keycode: {keycode})")
    print('─'*50)
    
    cmd = f"adb -s {device_ip} shell input keyevent {keycode}"
    print(f"  → {cmd}")
    success, _ = run_cmd(cmd)
    
    if success:
        print(f"  ✓ 按键成功")
        if wait > 0:
            time.sleep(wait)
    return success


def show_coordinates():
    """显示所有坐标配置"""
    print(f"\n{'='*60}")
    print("当前坐标配置")
    print('='*60)
    print(f"{'序号':<4} {'名称':<28} {'X':<6} {'Y':<6} {'等待':<6} {'描述'}")
    print('-'*60)
    for i, (name, coord) in enumerate(COORDINATES.items(), 1):
        print(f"{i:<4} {name:<28} {coord['x']:<6} {coord['y']:<6} {coord.get('wait', 1):<6} {coord.get('desc', '')}")
    print('='*60)


def edit_coordinate(coord_name: str):
    """编辑坐标"""
    if coord_name not in COORDINATES:
        print(f"未找到坐标: {coord_name}")
        return
    
    coord = COORDINATES[coord_name]
    print(f"\n编辑坐标: {coord_name}")
    print(f"  当前值: x={coord['x']}, y={coord['y']}, wait={coord.get('wait', 1)}")
    
    try:
        new_x = input(f"  新 X 值 (回车保持 {coord['x']}): ").strip()
        if new_x:
            coord['x'] = int(new_x)
        
        new_y = input(f"  新 Y 值 (回车保持 {coord['y']}): ").strip()
        if new_y:
            coord['y'] = int(new_y)
        
        new_wait = input(f"  新等待时间 (回车保持 {coord.get('wait', 1)}): ").strip()
        if new_wait:
            coord['wait'] = float(new_wait)
        
        print(f"  ✓ 已更新: x={coord['x']}, y={coord['y']}, wait={coord.get('wait', 1)}")
    except ValueError as e:
        print(f"  ✗ 输入无效: {e}")


def interactive_mode(device_ip: str):
    """交互式模式"""
    print(f"\n{'='*60}")
    print("交互式调试模式")
    print("输入 help 查看命令列表")
    print('='*60)
    
    while True:
        try:
            cmd = input("\n> ").strip()
            if not cmd:
                continue
            
            parts = cmd.split()
            action = parts[0].lower()
            
            if action in ('q', 'quit', 'exit'):
                print("退出")
                break
            
            elif action in ('h', 'help'):
                print("""
命令列表:
  launch [wait]          - 启动应用 (默认等待5秒)
  click <name>           - 点击坐标 (使用配置名)
  tap <x> <y> [wait]     - 点击指定坐标
  text <内容>            - 输入文本
  key <键名>             - 按键 (enter/back/home)
  list                   - 显示所有坐标配置
  edit <name>            - 编辑坐标配置
  save                   - 保存配置到文件
  run                    - 执行完整发布流程
  step                   - 单步执行发布流程
  q/quit                 - 退出
                """)
            
            elif action == 'launch':
                wait = float(parts[1]) if len(parts) > 1 else 5
                launch_app(device_ip, wait=wait)
            
            elif action == 'click':
                if len(parts) < 2:
                    print("用法: click <坐标名>")
                    show_coordinates()
                else:
                    click_coord(device_ip, parts[1])
            
            elif action == 'tap':
                if len(parts) < 3:
                    print("用法: tap <x> <y> [wait]")
                else:
                    x, y = int(parts[1]), int(parts[2])
                    wait = float(parts[3]) if len(parts) > 3 else 1
                    click(device_ip, x, y, f"手动点击 ({x}, {y})", wait)
            
            elif action == 'text':
                if len(parts) < 2:
                    print("用法: text <内容>")
                else:
                    input_text(device_ip, ' '.join(parts[1:]))
            
            elif action == 'key':
                if len(parts) < 2:
                    print("用法: key <键名> (enter/back/home)")
                else:
                    press_key(device_ip, parts[1])
            
            elif action == 'list':
                show_coordinates()
            
            elif action == 'edit':
                if len(parts) < 2:
                    print("用法: edit <坐标名>")
                    show_coordinates()
                else:
                    edit_coordinate(parts[1])
            
            elif action == 'save':
                save_config()
            
            elif action == 'run':
                run_full_workflow(device_ip)
            
            elif action == 'step':
                step_by_step_workflow(device_ip)
            
            else:
                print(f"未知命令: {action}，输入 help 查看帮助")
        
        except KeyboardInterrupt:
            print("\n中断")
            break
        except Exception as e:
            print(f"错误: {e}")


def step_by_step_workflow(device_ip: str, username: str = "shuxue", password: str = "123456zp."):
    """单步执行发布流程"""
    steps = [
        ("启动应用", lambda: launch_app(device_ip, wait=5)),
        ("点击登录入口", lambda: click_coord(device_ip, 'login_entry_button')),
        ("点击教师登录", lambda: click_coord(device_ip, 'teacher_login_button')),
        ("点击用户名输入框(备用)", lambda: click_coord(device_ip, 'username_input_alt')),
        ("点击用户名输入框", lambda: click_coord(device_ip, 'username_input')),
        ("输入用户名", lambda: input_text(device_ip, username)),
        ("按回车", lambda: press_key(device_ip, 'enter')),
        ("点击密码输入框(备用)", lambda: click_coord(device_ip, 'password_input_alt')),
        ("点击密码输入框", lambda: click_coord(device_ip, 'password_input')),
        ("输入密码", lambda: input_text(device_ip, password)),
        ("按回车", lambda: press_key(device_ip, 'enter')),
        ("点击登录按钮", lambda: click_coord(device_ip, 'login_submit_button')),
        ("点击发布作业", lambda: click_coord(device_ip, 'publish_homework_button')),
        ("点击选择页码", lambda: click_coord(device_ip, 'select_page_button')),
        ("点击页码选择器", lambda: click_coord(device_ip, 'page_number_selector')),
        ("点击页码确认", lambda: click_coord(device_ip, 'page_number_select_button')),
        ("点击确认页码", lambda: click_coord(device_ip, 'confirm_page_button')),
        ("点击作业名称输入框", lambda: click_coord(device_ip, 'homework_name_input')),
        ("输入作业名称", lambda: input_text(device_ip, f"auto_{datetime.now().strftime('%H%M%S')}")),
        ("按回车", lambda: press_key(device_ip, 'enter')),
        ("点击发布提交", lambda: click_coord(device_ip, 'publish_submit_button')),
        ("点击最终确认", lambda: click_coord(device_ip, 'final_confirm_button')),
    ]
    
    print(f"\n{'='*60}")
    print("单步执行发布流程")
    print("每步执行后按回车继续，输入 s 跳过，输入 q 退出")
    print('='*60)
    
    for i, (name, action) in enumerate(steps, 1):
        print(f"\n>>> 步骤 {i}/{len(steps)}: {name}")
        user_input = input("    按回车执行 (s=跳过, q=退出): ").strip().lower()
        
        if user_input == 'q':
            print("退出流程")
            return False
        elif user_input == 's':
            print("    跳过此步骤")
            continue
        
        if not action():
            retry = input("    执行失败，是否重试? (y/n): ").strip().lower()
            if retry == 'y':
                action()
    
    print(f"\n{'='*60}")
    print("✓ 流程执行完成")
    print('='*60)
    return True


def run_full_workflow(device_ip: str, username: str = "shuxue", password: str = "123456zp."):
    """自动执行完整发布流程"""
    print(f"\n{'='*60}")
    print("自动执行完整发布流程")
    print('='*60)
    
    if not check_connection(device_ip):
        return False
    
    steps = [
        ("启动应用", lambda: launch_app(device_ip, wait=5)),
        ("点击登录入口", lambda: click_coord(device_ip, 'login_entry_button')),
        ("点击教师登录", lambda: click_coord(device_ip, 'teacher_login_button')),
        ("点击用户名输入框(备用)", lambda: click_coord(device_ip, 'username_input_alt')),
        ("点击用户名输入框", lambda: click_coord(device_ip, 'username_input')),
        ("输入用户名", lambda: input_text(device_ip, username)),
        ("按回车", lambda: press_key(device_ip, 'enter')),
        ("点击密码输入框(备用)", lambda: click_coord(device_ip, 'password_input_alt')),
        ("点击密码输入框", lambda: click_coord(device_ip, 'password_input')),
        ("输入密码", lambda: input_text(device_ip, password)),
        ("按回车", lambda: press_key(device_ip, 'enter')),
        ("点击登录按钮", lambda: click_coord(device_ip, 'login_submit_button')),
        ("点击发布作业", lambda: click_coord(device_ip, 'publish_homework_button')),
        ("点击选择页码", lambda: click_coord(device_ip, 'select_page_button')),
        ("点击页码选择器", lambda: click_coord(device_ip, 'page_number_selector')),
        ("点击页码确认", lambda: click_coord(device_ip, 'page_number_select_button')),
        ("点击确认页码", lambda: click_coord(device_ip, 'confirm_page_button')),
        ("点击作业名称输入框", lambda: click_coord(device_ip, 'homework_name_input')),
        ("输入作业名称", lambda: input_text(device_ip, f"auto_{datetime.now().strftime('%H%M%S')}")),
        ("按回车", lambda: press_key(device_ip, 'enter')),
        ("点击发布提交", lambda: click_coord(device_ip, 'publish_submit_button')),
        ("点击最终确认", lambda: click_coord(device_ip, 'final_confirm_button')),
    ]
    
    for i, (name, action) in enumerate(steps, 1):
        print(f"\n>>> 步骤 {i}/{len(steps)}: {name}")
        if not action():
            print(f"\n✗ 流程在步骤 {i} 失败")
            return False
    
    print(f"\n{'='*60}")
    print("✓ 完整流程执行成功")
    print('='*60)
    return True


def main():
    parser = argparse.ArgumentParser(description='工作流本地测试工具')
    parser.add_argument('--device', '-d', default=DEVICE_IP, help='设备 IP')
    parser.add_argument('--mode', '-m', choices=['interactive', 'run', 'step', 'launch'], 
                        default='interactive', help='模式: interactive=交互, run=自动执行, step=单步, launch=仅启动')
    parser.add_argument('--username', '-u', default='shuxue', help='登录用户名')
    parser.add_argument('--password', '-p', default='123456zp.', help='登录密码')
    
    args = parser.parse_args()
    
    # 加载配置
    load_config()
    
    print(f"\n{'='*60}")
    print("工作流本地测试工具")
    print('='*60)
    print(f"设备: {args.device}")
    print(f"模式: {args.mode}")
    
    if not check_connection(args.device):
        print("\n请检查设备连接后重试")
        return
    
    if args.mode == 'interactive':
        interactive_mode(args.device)
    elif args.mode == 'run':
        run_full_workflow(args.device, args.username, args.password)
    elif args.mode == 'step':
        step_by_step_workflow(args.device, args.username, args.password)
    elif args.mode == 'launch':
        launch_app(args.device)


if __name__ == '__main__':
    main()
