"""
配置文件 - 集中管理所有可配置参数
用于安卓作业批阅一体机自动化测试
"""

import os
from datetime import datetime

# ==================== 基础路径配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
SCREENSHOT_DIR = os.path.join(BASE_DIR, 'screenshots')
REPORT_DIR = os.path.join(BASE_DIR, 'reports')

# 创建必要的目录
for dir_path in [LOG_DIR, SCREENSHOT_DIR, REPORT_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==================== 设备配置 ====================
# 安卓设备IP列表（支持无线连接）
DEVICE_IPS = [
    "10.185.247.116",
    #"10.185.247.10",
    #"10.185.247.103",
    #"10.185.247.35",
    "10.185.247.9"

]

# ADB连接配置
ADB_CONNECT_TIMEOUT = 10  # ADB连接超时时间（秒）
ADB_COMMAND_TIMEOUT = 30  # ADB命令执行超时时间（秒）

# ==================== APP配置 ====================
APP_CONFIG = {
    'package_name': 'com.zpzn.terminal',  # APP包名（根据实际修改）
    'main_activity': '.MainActivity',        # 主Activity（根据实际修改）
    'wait_timeout': 10,                      # 等待超时时间（秒）
    'start_delay': 7,                        # APP启动后等待时间（秒）
}

# ==================== 坐标点击配置 ====================
# 所有UI操作的坐标位置
CLICK_COORDINATES = {
    # 主界面
    'submit_homework_button': {
        'x': 1200,
        'y': 400,
        'description': '提交作业按钮',
        'wait_after': 2  # 点击后等待时间（秒）
    },

    # 拍照界面
    'camera_capture_button': {
        'x': 667,
        'y': 978,
        'description': '拍照按钮',
        'wait_after': 2  # 等待拍照完成
    },
    
    # 双页拍照按钮
    'double_page_button': {
        'x': 400,
        'y': 551,
        'description': '双页拍照功能按钮',
        'wait_after': 2  # 等待双页模式打开
    },

    # 提交按钮
    'submit_button': {
        'x': 1593,
        'y': 955,
        'description': '提交按钮',
        'wait_after': 2
    },

    # 确认提交
    'confirm_submit_button': {
        'x': 886,
        'y': 781,
        'description': '确定提交按钮',
        'wait_after': 3  # 等待返回主界面
    },
    
    # 发布作业流程相关坐标
    'login_entry_button': {
        'x': 370,
        'y': 600,
        'description': '登录入口按钮',
        'wait_after': 1
    },
    'teacher_login_button': {
        'x': 1800,
        'y': 70,
        'description': '教师登录按钮',
        'wait_after': 1
    },
    'username_input': {
        'x': 930,
        'y': 426,
        'description': '用户名输入框',
        'wait_after': 0.5
    },
    'password_input': {
        'x': 880,
        'y': 530,
        'description': '密码输入框',
        'wait_after': 0.5
    },
    'login_submit_button': {
        'x': 960,
        'y': 670,
        'description': '登录提交按钮',
        'wait_after': 3
    },
    'publish_homework_button': {
        'x': 400,
        'y': 560,
        'description': '发布作业按钮',
        'wait_after': 2
    },
    'select_page_button': {
        'x': 870,
        'y': 379,
        'description': '选择页码按钮',
        'wait_after': 1
    },
    'page_number_selector': {
        'x': 659,
        'y': 233,
        'description': '页码选择器',
        'wait_after': 0.5
    },
    'page_number_select_button': {
        'x': 830,
        'y': 230,
        'description': '页码确认按钮',
        'wait_after': 0.5
    },
    'confirm_page_button': {
        'x': 950,
        'y': 900,
        'description': '确认页码按钮',
        'wait_after': 1
    },
    'homework_name_input': {
        'x': 833,
        'y': 557,
        'description': '作业名称输入框',
        'wait_after': 0.5
    },
    'publish_submit_button': {
        'x': 960,
        'y': 960,
        'description': '发布作业提交按钮',
        'wait_after': 3
    }
}

# ==================== RFID配置 ====================
# RFID输入设备路径（可通过adb shell getevent -pl查看）
RFID_DEVICE_PATH = "/dev/input/event2"  # 默认值，可能需要根据实际设备调整

# RFID输入延迟配置
RFID_CONFIG = {
    'inter_char_delay': 0.005,  # 字符间延迟（秒）
    'final_enter_delay': 0.05,  # 回车前延迟（秒）
    'cmd_timeout': 3,           # 命令超时时间（秒）
    'wait_after_input': 1,      # RFID输入后等待时间（秒）
}

# ==================== RFID事件映射 ====================
# 根据实际设备抓包获得的事件映射表
# 格式：[(事件类型, 事件代码, 事件值), ...]
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

# ==================== 学生RFID卡号配置 ====================
# 自定义RFID卡号列表（不随机生成，直接配置）
RFID_CARDS = [
    "0986485457",
    "0986484961",
    "0986483889",
    "0986481393",
    "0986492065",
    "0986487473",
    "0986478369",
    "0986483409",
    "0986485937",
    "0986479841",
    "0986485953",
    "0986491585",
    "0986492609",
    "0986481873",
    "0986487937",
    "0986487953",
    "0986484465",
    "0986486977",
    "0986491601",
    "0986491089",
    "0986485473",
    "0986490033",
    "0986488529",
    "0986490593",
    "0986491105",
    "0986488545",
    "0986490577",
    "0986492081",
    "0986486497"

]

# 学生数量
STUDENT_COUNT = len(RFID_CARDS)

# ==================== 账号配置 ====================
# 教师账号配置（用于发布作业）
TEACHER_ACCOUNT = {
    'username': 'shuxue',  # 可自定义的账号名称
    'password': '123456zp.',  # 可自定义的密码
}

# ==================== 定时任务配置 ====================
# CRON表达式（每天上午9点执行）
CRON_EXPRESSION = "0 9 * * *"

# 立即执行（用于测试）
IMMEDIATE_EXECUTION = True

# ==================== 同步配置 ====================
SYNC_CONFIG = {
    'prepare_timeout': 60,      # 准备阶段超时时间（秒）
    'sync_wait_interval': 2,    # 同步等待检查间隔（秒）
    'max_retry_count': 3,       # 最大重试次数
}

# ==================== 测试配置 ====================
TEST_CONFIG = {
    'screenshot_on_error': True,     # 错误时截图
    'screenshot_on_success': False,  # 成功时截图
    'screenshot_each_student': False, # 每个学生处理后截图
    'detailed_log': True,            # 详细日志
    'parallel_execution': True,      # 并行执行
    'max_workers': 10,               # 最大并发数
    'operation_delay': 1,          # 操作间默认延迟（秒）
    'publish_homework': True,        # 是否执行发布作业操作
    'publish_on_single_device_only': True,  # 是否只在一台设备上发布作业（批量测试时）
    
}

# ==================== 报告配置 ====================
REPORT_CONFIG = {
    'csv_delimiter': ',',           # CSV分隔符
    'timestamp_format': '%Y%m%d_%H%M%S',
    'report_filename': f'test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
    'summary_filename': f'test_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
}

# ==================== 日志配置 ====================
LOG_CONFIG = {
    'level': 'INFO',  # 日志级别：DEBUG, INFO, WARNING, ERROR
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'save_to_file': True,  # 是否保存到文件
}

# ==================== 错误处理配置 ====================
ERROR_HANDLING = {
    'max_retries': 3,  # 最大重试次数
    'retry_delay': 5,  # 重试延迟（秒）
    'continue_on_error': True,  # 出错时是否继续处理下一个学生
    'min_success_count': 5,  # 最少成功处理的学生数（低于此数视为测试失败）
}
