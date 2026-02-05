"""
RFID 模拟器服务 - WebSocket 连接管理 + ADB 命令转发
使用 JSON 文件存储状态，确保跨进程/greenlet 状态共享
"""

import json
import os
import time
import logging
import fcntl
from typing import Dict, Optional, List, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# 状态文件路径
STATE_FILE = Path(__file__).parent.parent / 'sessions' / 'rfid_state.json'


class ClientStatus(Enum):
    """客户端状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"


@dataclass
class AdbClient:
    """ADB 客户端信息"""
    client_id: str
    ip_address: str
    connected_at: str  # ISO 格式字符串
    last_heartbeat: str  # ISO 格式字符串
    status: str
    device_info: Dict[str, Any] = None
    
    def to_dict(self) -> dict:
        return {
            'client_id': self.client_id,
            'ip_address': self.ip_address,
            'connected_at': self.connected_at,
            'last_heartbeat': self.last_heartbeat,
            'status': self.status,
            'device_info': self.device_info or {}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AdbClient':
        return cls(
            client_id=data['client_id'],
            ip_address=data['ip_address'],
            connected_at=data['connected_at'],
            last_heartbeat=data['last_heartbeat'],
            status=data['status'],
            device_info=data.get('device_info')
        )


# WebSocket 连接存储已移至路由层，避免重复存储导致状态不一致
# 通过 set_websocket_getter 注入获取函数
_websocket_getter = None


def set_websocket_getter(getter_func):
    """设置 WebSocket 获取函数（由路由层注入）"""
    global _websocket_getter
    _websocket_getter = getter_func
    logger.info("[RfidSimulator] WebSocket 获取函数已注入")


def _read_state() -> dict:
    """从文件读取状态"""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"[RfidSimulator] 读取状态文件失败: {e}")
    return {'clients': {}, 'current_task': None, 'logs': []}


def _write_state(state: dict):
    """写入状态到文件"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[RfidSimulator] 写入状态文件失败: {e}")


class RfidSimulatorService:
    """RFID 模拟器服务 - 使用文件存储状态"""
    
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
    
    DEFAULT_DEVICE_PATH = "/dev/input/event2"
    DEFAULT_INTER_CHAR_DELAY = 0.005
    DEFAULT_ENTER_DELAY = 0.05
    HEARTBEAT_TIMEOUT = 90  # 心跳超时延长到 90 秒，容错网络抖动
    MAX_LOGS = 100
    CLEANUP_INTERVAL = 30  # 清理间隔 30 秒，避免频繁清理
    _last_cleanup_time = 0  # 上次清理时间
        
    # ==================== 客户端管理 ====================
    
    def register_client(self, client_id: str, ip_address: str, websocket: Any = None, device_info: dict = None) -> AdbClient:
        """注册 ADB 客户端（WebSocket 由路由层管理）"""
        now = datetime.now().isoformat()
        client = AdbClient(
            client_id=client_id,
            ip_address=ip_address,
            connected_at=now,
            last_heartbeat=now,
            status=ClientStatus.ONLINE.value,
            device_info=device_info
        )
        
        # 保存客户端信息到文件（WebSocket 由路由层管理，不在此存储）
        state = _read_state()
        state['clients'][client_id] = client.to_dict()
        _write_state(state)
        
        self._add_log('info', f'客户端已连接: {ip_address}')
        logger.info(f"[RfidSimulator] 客户端注册: {client_id} ({ip_address})")
        return client
    
    def unregister_client(self, client_id: str):
        """注销 ADB 客户端"""
        # 从文件移除客户端（WebSocket 由路由层管理）
        state = _read_state()
        if client_id in state['clients']:
            client_data = state['clients'].pop(client_id)
            _write_state(state)
            self._add_log('warning', f"客户端已断开: {client_data.get('ip_address', 'unknown')}")
            logger.info(f"[RfidSimulator] 客户端注销: {client_id}")
    
    def update_heartbeat(self, client_id: str, device_info: dict = None):
        """更新心跳"""
        state = _read_state()
        if client_id in state['clients']:
            now = datetime.now().isoformat()
            state['clients'][client_id]['last_heartbeat'] = now
            state['clients'][client_id]['status'] = ClientStatus.ONLINE.value
            if device_info:
                state['clients'][client_id]['device_info'] = device_info
            _write_state(state)
            logger.debug(f"[RfidSimulator] 心跳更新: {client_id}")
        else:
            logger.warning(f"[RfidSimulator] 心跳更新失败: 客户端 {client_id} 不存在")
    
    def get_client_status(self) -> dict:
        """获取客户端状态"""
        # 限制清理频率，避免每次请求都清理
        now = time.time()
        if now - self._last_cleanup_time > self.CLEANUP_INTERVAL:
            self._cleanup_stale_clients()
            RfidSimulatorService._last_cleanup_time = now
        
        state = _read_state()
        clients = list(state['clients'].values())
        
        if not clients:
            return {'connected': False, 'client': None}
        
        client = clients[0]
        return {
            'connected': client['status'] == ClientStatus.ONLINE.value,
            'client': client
        }
    
    def _cleanup_stale_clients(self):
        """清理心跳超时的客户端"""
        now = datetime.now()
        state = _read_state()
        stale_clients = []
        
        for client_id, client in state['clients'].items():
            try:
                last_heartbeat = datetime.fromisoformat(client['last_heartbeat'])
                elapsed = (now - last_heartbeat).total_seconds()
                if elapsed > self.HEARTBEAT_TIMEOUT:
                    stale_clients.append(client_id)
                    logger.warning(f"[RfidSimulator] 客户端心跳超时: {client_id} ({elapsed:.0f}s)")
            except Exception as e:
                logger.error(f"[RfidSimulator] 解析心跳时间失败: {e}")
                stale_clients.append(client_id)
        
        if stale_clients:
            for client_id in stale_clients:
                state['clients'].pop(client_id, None)
            _write_state(state)
            self._add_log('warning', f'清理超时客户端: {len(stale_clients)} 个')
    
    def get_active_websocket(self) -> Optional[Any]:
        """获取活跃的 WebSocket 连接（通过路由层注入的获取函数）"""
        if _websocket_getter is None:
            logger.warning("[RfidSimulator] WebSocket 获取函数未注入")
            return None
        
        state = _read_state()
        for client_id, client in state['clients'].items():
            if client['status'] == ClientStatus.ONLINE.value:
                ws = _websocket_getter(client_id)
                if ws:
                    return ws
        return None
    
    # ==================== 命令构建 ====================
    
    def build_char_command(self, char: str, device_path: str) -> Optional[str]:
        """构建单个字符的 sendevent 命令"""
        if char not in self.RFID_EVENT_MAP:
            return None
        events = []
        for event in self.RFID_EVENT_MAP[char]:
            type_code, code, value = event
            events.append(f"sendevent {device_path} {type_code} {code} {value}")
        return "; ".join(events)
    
    def build_rfid_commands(self, rfid_code: str, device_path: str, send_enter: bool = True) -> List[str]:
        """构建完整的 RFID 发送命令序列"""
        commands = []
        for char in rfid_code:
            cmd = self.build_char_command(char, device_path)
            if cmd:
                commands.append(cmd)
        if send_enter:
            enter_cmd = self.build_char_command('enter', device_path)
            if enter_cmd:
                commands.append(enter_cmd)
        return commands
    
    # ==================== 日志管理 ====================
    
    def _add_log(self, level: str, message: str, data: dict = None):
        """添加日志"""
        log_entry = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'data': data
        }
        state = _read_state()
        state['logs'].insert(0, log_entry)
        if len(state['logs']) > self.MAX_LOGS:
            state['logs'] = state['logs'][:self.MAX_LOGS]
        _write_state(state)
    
    def get_logs(self, limit: int = 50) -> List[dict]:
        """获取日志"""
        state = _read_state()
        return state['logs'][:limit]
    
    def clear_logs(self):
        """清空日志"""
        state = _read_state()
        state['logs'] = []
        _write_state(state)
    
    # ==================== 任务管理 ====================
    
    def create_task(self, cards: List[Dict[str, str]], interval_seconds: int, 
                    send_enter: bool, device_path: str) -> dict:
        """创建模拟任务"""
        import uuid
        task = {
            'task_id': str(uuid.uuid4())[:8],
            'cards': cards,
            'total_count': len(cards),
            'interval_seconds': interval_seconds,
            'send_enter': send_enter,
            'device_path': device_path,
            'status': 'pending',
            'current_index': 0,
            'success_count': 0,
            'failed_count': 0,
            'created_at': datetime.now().isoformat()
        }
        state = _read_state()
        state['current_task'] = task
        _write_state(state)
        self._add_log('info', f'创建任务: {len(cards)} 张卡片, 间隔 {interval_seconds}s')
        return task
    
    def get_current_task(self) -> Optional[dict]:
        """获取当前任务"""
        state = _read_state()
        return state.get('current_task')
    
    def update_task_status(self, status: str, current_index: int = None, success: bool = None):
        """更新任务状态"""
        state = _read_state()
        task = state.get('current_task')
        if not task:
            return
        task['status'] = status
        if current_index is not None:
            task['current_index'] = current_index
        if success is not None:
            if success:
                task['success_count'] = task.get('success_count', 0) + 1
            else:
                task['failed_count'] = task.get('failed_count', 0) + 1
        state['current_task'] = task
        _write_state(state)
    
    def stop_task(self):
        """停止任务"""
        state = _read_state()
        if state.get('current_task'):
            state['current_task']['status'] = 'stopped'
            _write_state(state)
            self._add_log('warning', '任务已停止')
    
    def pause_task(self):
        """暂停任务"""
        state = _read_state()
        task = state.get('current_task')
        if task and task['status'] == 'running':
            task['status'] = 'paused'
            _write_state(state)
            self._add_log('info', '任务已暂停')
    
    def resume_task(self):
        """恢复任务"""
        state = _read_state()
        task = state.get('current_task')
        if task and task['status'] == 'paused':
            task['status'] = 'running'
            _write_state(state)
            self._add_log('info', '任务已恢复')


# 全局服务实例
rfid_simulator_service = RfidSimulatorService()
logger.info(f"[RfidSimulator Service] 初始化完成, 状态文件: {STATE_FILE}")
