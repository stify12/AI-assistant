"""
自动化流程服务 - 管理可视化流程编排
支持模块化操作、坐标配置、便捷操作
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_DIR = Path(__file__).parent.parent / 'sessions'
WORKFLOW_CONFIG_FILE = CONFIG_DIR / 'workflow_config.json'
COORDINATES_FILE = CONFIG_DIR / 'coordinates.json'
RECENT_ITEMS_FILE = CONFIG_DIR / 'recent_items.json'

# 确保目录存在
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 默认坐标配置 ====================
DEFAULT_COORDINATES = {
    # 主界面
    'submit_homework_button': {
        'x': 1200, 'y': 400,
        'name': '提交作业按钮',
        'category': 'main',
        'wait_after': 2
    },
    
    # 拍照界面
    'camera_capture_button': {
        'x': 667, 'y': 978,
        'name': '拍照按钮',
        'category': 'camera',
        'wait_after': 2
    },
    'double_page_button': {
        'x': 400, 'y': 551,
        'name': '双页拍照按钮',
        'category': 'camera',
        'wait_after': 2
    },
    
    # 提交界面
    'submit_button': {
        'x': 1593, 'y': 955,
        'name': '提交按钮',
        'category': 'submit',
        'wait_after': 2
    },
    'confirm_submit_button': {
        'x': 886, 'y': 781,
        'name': '确认提交按钮',
        'category': 'submit',
        'wait_after': 3
    },
    
    # 登录流程
    'login_entry_button': {
        'x': 370, 'y': 600,
        'name': '登录入口按钮',
        'category': 'login',
        'wait_after': 1
    },
    'teacher_login_button': {
        'x': 1800, 'y': 70,
        'name': '教师登录按钮',
        'category': 'login',
        'wait_after': 1
    },
    'username_input': {
        'x': 930, 'y': 426,
        'name': '用户名输入框',
        'category': 'login',
        'wait_after': 0.5
    },
    'password_input': {
        'x': 880, 'y': 530,
        'name': '密码输入框',
        'category': 'login',
        'wait_after': 0.5
    },
    'login_submit_button': {
        'x': 960, 'y': 670,
        'name': '登录提交按钮',
        'category': 'login',
        'wait_after': 3
    },
    
    # 发布作业流程
    'publish_homework_button': {
        'x': 400, 'y': 560,
        'name': '发布作业按钮',
        'category': 'publish',
        'wait_after': 2
    },
    'select_page_button': {
        'x': 870, 'y': 379,
        'name': '选择页码按钮',
        'category': 'publish',
        'wait_after': 1
    },
    'page_number_selector': {
        'x': 659, 'y': 233,
        'name': '页码选择器',
        'category': 'publish',
        'wait_after': 0.5
    },
    'page_number_select_button': {
        'x': 830, 'y': 230,
        'name': '页码确认按钮',
        'category': 'publish',
        'wait_after': 0.5
    },
    'confirm_page_button': {
        'x': 950, 'y': 900,
        'name': '确认页码按钮',
        'category': 'publish',
        'wait_after': 1
    },
    'homework_name_input': {
        'x': 833, 'y': 557,
        'name': '作业名称输入框',
        'category': 'publish',
        'wait_after': 0.5
    },
    'publish_submit_button': {
        'x': 960, 'y': 960,
        'name': '发布提交按钮',
        'category': 'publish',
        'wait_after': 3
    }
}


# ==================== 预定义操作模块 ====================
OPERATION_MODULES = {
    'publish_homework': {
        'id': 'publish_homework',
        'name': '发布作业',
        'icon': 'publish',
        'color': '#1d1d1f',
        'description': '教师端一键发布作业',
        'steps': [
            {'id': 'login_entry', 'name': '点击登录入口', 'type': 'click', 'coordinate': 'login_entry_button'},
            {'id': 'teacher_login', 'name': '点击教师登录', 'type': 'click', 'coordinate': 'teacher_login_button'},
            {'id': 'input_username', 'name': '输入用户名', 'type': 'input', 'coordinate': 'username_input', 'param': 'username'},
            {'id': 'input_password', 'name': '输入密码', 'type': 'input', 'coordinate': 'password_input', 'param': 'password'},
            {'id': 'login_submit', 'name': '点击登录', 'type': 'click', 'coordinate': 'login_submit_button'},
            {'id': 'publish_entry', 'name': '点击发布作业', 'type': 'click', 'coordinate': 'publish_homework_button'},
            {'id': 'select_page', 'name': '选择页码', 'type': 'click', 'coordinate': 'select_page_button'},
            {'id': 'page_selector', 'name': '点击页码', 'type': 'click', 'coordinate': 'page_number_selector'},
            {'id': 'confirm_page_select', 'name': '确认页码选择', 'type': 'click', 'coordinate': 'page_number_select_button'},
            {'id': 'confirm_page', 'name': '确认页码', 'type': 'click', 'coordinate': 'confirm_page_button'},
            {'id': 'input_name', 'name': '输入作业名称', 'type': 'input', 'coordinate': 'homework_name_input', 'param': 'homework_name'},
            {'id': 'publish_submit', 'name': '提交发布', 'type': 'click', 'coordinate': 'publish_submit_button'}
        ],
        'params': {
            'username': {'name': '用户名', 'type': 'text', 'default': 'shuxue'},
            'password': {'name': '密码', 'type': 'password', 'default': '123456zp.'},
            'homework_name': {'name': '作业名称', 'type': 'text', 'default': '自动化测试_{timestamp}'}
        }
    },
    'student_scan': {
        'id': 'student_scan',
        'name': '学生刷卡',
        'icon': 'scan',
        'color': '#6e6e73',
        'description': 'RFID刷卡 + 拍照',
        'steps': [
            {'id': 'rfid_input', 'name': 'RFID刷卡', 'type': 'rfid', 'param': 'rfid_code'},
            {'id': 'double_page', 'name': '双页拍照', 'type': 'click', 'coordinate': 'double_page_button', 'condition': 'first_only'},
            {'id': 'capture', 'name': '拍照', 'type': 'click', 'coordinate': 'camera_capture_button'}
        ],
        'params': {
            'rfid_code': {'name': 'RFID卡号', 'type': 'text', 'required': True}
        }
    },
    'batch_submit': {
        'id': 'batch_submit',
        'name': '批量提交',
        'icon': 'submit',
        'color': '#86868b',
        'description': '提交整批作业',
        'steps': [
            {'id': 'click_submit', 'name': '点击提交', 'type': 'click', 'coordinate': 'submit_button'},
            {'id': 'confirm_submit', 'name': '确认提交', 'type': 'click', 'coordinate': 'confirm_submit_button'}
        ],
        'params': {}
    },
    'enter_homework': {
        'id': 'enter_homework',
        'name': '进入作业',
        'icon': 'enter',
        'color': '#1d1d1f',
        'description': '进入作业提交界面',
        'steps': [
            {'id': 'click_homework', 'name': '点击提交作业', 'type': 'click', 'coordinate': 'submit_homework_button'}
        ],
        'params': {}
    },
    'custom_click': {
        'id': 'custom_click',
        'name': '自定义点击',
        'icon': 'click',
        'color': '#d2d2d7',
        'description': '点击指定坐标',
        'steps': [
            {'id': 'custom', 'name': '点击', 'type': 'click', 'param': 'coordinate'}
        ],
        'params': {
            'coordinate': {'name': '坐标点', 'type': 'coordinate', 'required': True},
            'wait_after': {'name': '等待时间(秒)', 'type': 'number', 'default': 1}
        }
    },
    'custom_input': {
        'id': 'custom_input',
        'name': '自定义输入',
        'icon': 'input',
        'color': '#d2d2d7',
        'description': '在指定位置输入文本',
        'steps': [
            {'id': 'click_input', 'name': '点击输入框', 'type': 'click', 'param': 'coordinate'},
            {'id': 'input_text', 'name': '输入文本', 'type': 'input', 'param': 'text'}
        ],
        'params': {
            'coordinate': {'name': '坐标点', 'type': 'coordinate', 'required': True},
            'text': {'name': '输入内容', 'type': 'text', 'required': True}
        }
    },
    'wait': {
        'id': 'wait',
        'name': '等待',
        'icon': 'wait',
        'color': '#e5e5e5',
        'description': '等待指定时间',
        'steps': [
            {'id': 'wait', 'name': '等待', 'type': 'wait', 'param': 'seconds'}
        ],
        'params': {
            'seconds': {'name': '等待秒数', 'type': 'number', 'default': 2}
        }
    }
}


def _read_json(file_path: Path, default: Any = None) -> Any:
    """读取 JSON 文件"""
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"读取文件失败 {file_path}: {e}")
    return default if default is not None else {}


def _write_json(file_path: Path, data: Any):
    """写入 JSON 文件"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"写入文件失败 {file_path}: {e}")


class WorkflowService:
    """流程编排服务"""
    
    def __init__(self):
        self._init_coordinates()
    
    def _init_coordinates(self):
        """初始化坐标配置"""
        coords = _read_json(COORDINATES_FILE)
        if not coords:
            _write_json(COORDINATES_FILE, DEFAULT_COORDINATES)
    
    # ==================== 坐标管理 ====================
    
    def get_coordinates(self) -> Dict[str, Any]:
        """获取所有坐标配置"""
        coords = _read_json(COORDINATES_FILE, DEFAULT_COORDINATES)
        # 按类别分组
        grouped = {}
        for key, coord in coords.items():
            category = coord.get('category', 'other')
            if category not in grouped:
                grouped[category] = []
            grouped[category].append({**coord, 'key': key})
        return {'all': coords, 'grouped': grouped}
    
    def update_coordinate(self, key: str, x: int, y: int, name: str = None, wait_after: float = None) -> bool:
        """更新单个坐标"""
        coords = _read_json(COORDINATES_FILE, DEFAULT_COORDINATES)
        if key in coords:
            coords[key]['x'] = x
            coords[key]['y'] = y
            if name:
                coords[key]['name'] = name
            if wait_after is not None:
                coords[key]['wait_after'] = wait_after
            _write_json(COORDINATES_FILE, coords)
            return True
        return False
    
    def add_coordinate(self, key: str, x: int, y: int, name: str, category: str = 'custom', wait_after: float = 1) -> bool:
        """添加新坐标"""
        coords = _read_json(COORDINATES_FILE, DEFAULT_COORDINATES)
        coords[key] = {
            'x': x, 'y': y,
            'name': name,
            'category': category,
            'wait_after': wait_after
        }
        _write_json(COORDINATES_FILE, coords)
        return True
    
    def delete_coordinate(self, key: str) -> bool:
        """删除坐标"""
        coords = _read_json(COORDINATES_FILE, DEFAULT_COORDINATES)
        if key in coords and coords[key].get('category') == 'custom':
            del coords[key]
            _write_json(COORDINATES_FILE, coords)
            return True
        return False
    
    def export_coordinates(self) -> str:
        """导出坐标配置为 JSON 字符串"""
        coords = _read_json(COORDINATES_FILE, DEFAULT_COORDINATES)
        return json.dumps(coords, ensure_ascii=False, indent=2)
    
    def import_coordinates(self, json_str: str) -> bool:
        """导入坐标配置"""
        try:
            coords = json.loads(json_str)
            _write_json(COORDINATES_FILE, coords)
            return True
        except Exception as e:
            logger.error(f"导入坐标失败: {e}")
            return False
    
    # ==================== 操作模块 ====================
    
    def get_modules(self) -> List[Dict[str, Any]]:
        """获取所有操作模块"""
        return list(OPERATION_MODULES.values())
    
    def get_module(self, module_id: str) -> Optional[Dict[str, Any]]:
        """获取单个模块详情"""
        return OPERATION_MODULES.get(module_id)
    
    # ==================== 便捷操作（最近使用） ====================
    
    def get_recent_items(self) -> Dict[str, List[Dict]]:
        """获取最近使用的班级和书本"""
        return _read_json(RECENT_ITEMS_FILE, {'classes': [], 'books': []})
    
    def add_recent_item(self, item_type: str, item: Dict) -> bool:
        """添加最近使用项"""
        recent = _read_json(RECENT_ITEMS_FILE, {'classes': [], 'books': []})
        key = 'classes' if item_type == 'class' else 'books'
        
        # 移除已存在的相同项
        recent[key] = [i for i in recent[key] if i.get('id') != item.get('id')]
        
        # 添加到开头
        recent[key].insert(0, {
            **item,
            'used_at': datetime.now().isoformat()
        })
        
        # 只保留最近 10 个
        recent[key] = recent[key][:10]
        
        _write_json(RECENT_ITEMS_FILE, recent)
        return True
    
    def clear_recent_items(self, item_type: str = None) -> bool:
        """清空最近使用"""
        recent = _read_json(RECENT_ITEMS_FILE, {'classes': [], 'books': []})
        if item_type == 'class':
            recent['classes'] = []
        elif item_type == 'book':
            recent['books'] = []
        else:
            recent = {'classes': [], 'books': []}
        _write_json(RECENT_ITEMS_FILE, recent)
        return True
    
    # ==================== 流程管理 ====================
    
    def get_saved_workflows(self) -> List[Dict]:
        """获取保存的流程模板"""
        config = _read_json(WORKFLOW_CONFIG_FILE, {'workflows': []})
        return config.get('workflows', [])
    
    def save_workflow(self, workflow: Dict) -> str:
        """保存流程模板"""
        import uuid
        config = _read_json(WORKFLOW_CONFIG_FILE, {'workflows': []})
        
        workflow_id = workflow.get('id') or str(uuid.uuid4())[:8]
        workflow['id'] = workflow_id
        workflow['updated_at'] = datetime.now().isoformat()
        
        # 更新或添加
        existing = next((i for i, w in enumerate(config['workflows']) if w.get('id') == workflow_id), None)
        if existing is not None:
            config['workflows'][existing] = workflow
        else:
            workflow['created_at'] = datetime.now().isoformat()
            config['workflows'].append(workflow)
        
        _write_json(WORKFLOW_CONFIG_FILE, config)
        return workflow_id
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """删除流程模板"""
        config = _read_json(WORKFLOW_CONFIG_FILE, {'workflows': []})
        config['workflows'] = [w for w in config['workflows'] if w.get('id') != workflow_id]
        _write_json(WORKFLOW_CONFIG_FILE, config)
        return True
    
    # ==================== 构建执行命令 ====================
    
    def build_workflow_commands(self, workflow: Dict, params: Dict = None) -> List[Dict]:
        """
        将流程转换为可执行的命令序列
        
        Args:
            workflow: 流程定义 {'modules': [...], 'params': {...}}
            params: 运行时参数
        
        Returns:
            命令序列
        """
        commands = []
        coords = _read_json(COORDINATES_FILE, DEFAULT_COORDINATES)
        runtime_params = params or {}
        
        for module_item in workflow.get('modules', []):
            module_id = module_item.get('module_id')
            module_params = {**module_item.get('params', {}), **runtime_params}
            
            module_def = OPERATION_MODULES.get(module_id)
            if not module_def:
                continue
            
            for step in module_def.get('steps', []):
                cmd = {
                    'module_id': module_id,
                    'step_id': step['id'],
                    'step_name': step['name'],
                    'type': step['type']
                }
                
                # 处理坐标
                if step.get('coordinate'):
                    coord_key = step['coordinate']
                    if coord_key in coords:
                        cmd['x'] = coords[coord_key]['x']
                        cmd['y'] = coords[coord_key]['y']
                        cmd['wait_after'] = coords[coord_key].get('wait_after', 1)
                
                # 处理参数
                if step.get('param'):
                    param_key = step['param']
                    if param_key in module_params:
                        cmd['value'] = module_params[param_key]
                    elif param_key in module_def.get('params', {}):
                        default = module_def['params'][param_key].get('default')
                        if default:
                            # 处理模板变量
                            if '{timestamp}' in str(default):
                                default = default.replace('{timestamp}', datetime.now().strftime('%Y%m%d_%H%M%S'))
                            cmd['value'] = default
                
                # 处理条件
                if step.get('condition'):
                    cmd['condition'] = step['condition']
                
                commands.append(cmd)
        
        return commands


# 全局服务实例
workflow_service = WorkflowService()
