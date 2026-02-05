"""
RFID 模拟器路由 - HTTP API + WebSocket
WebSocket 连接存储在本模块，确保 HTTP 请求能访问
"""

import json
import logging
from flask import Blueprint, request, jsonify, render_template
from flask_sock import Sock
from datetime import datetime

from services.rfid_simulator_service import rfid_simulator_service, set_websocket_getter

logger = logging.getLogger(__name__)

rfid_simulator_bp = Blueprint('rfid_simulator', __name__)

# WebSocket 连接存储（模块级变量，HTTP 和 WebSocket 共享）
_active_websockets = {}  # client_id -> websocket


def _get_websocket_by_client_id(client_id: str):
    """根据 client_id 获取 WebSocket 连接"""
    return _active_websockets.get(client_id)


# 注入 WebSocket 获取函数到 service 层
set_websocket_getter(_get_websocket_by_client_id)


# ==================== 页面路由 ====================

@rfid_simulator_bp.route('/rfid-simulator')
def rfid_simulator_page():
    """模拟 RFID 页面"""
    return render_template('rfid-simulator.html')


# ==================== HTTP API ====================

@rfid_simulator_bp.route('/api/rfid-simulator/status', methods=['GET'])
def get_status():
    """获取连接状态"""
    try:
        status = rfid_simulator_service.get_client_status()
        task = rfid_simulator_service.get_current_task()
        
        return jsonify({
            'success': True,
            'data': {
                'connected': status.get('connected', False),
                'client': status.get('client'),
                'task': task
            }
        })
    except Exception as e:
        logger.error(f"[RfidSimulator] 获取状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@rfid_simulator_bp.route('/api/rfid-simulator/logs', methods=['GET'])
def get_logs():
    """获取日志"""
    try:
        limit = request.args.get('limit', 50, type=int)
        logs = rfid_simulator_service.get_logs(limit)
        return jsonify({'success': True, 'data': logs})
    except Exception as e:
        logger.error(f"[RfidSimulator] 获取日志失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@rfid_simulator_bp.route('/api/rfid-simulator/logs', methods=['DELETE'])
def clear_logs():
    """清空日志"""
    try:
        rfid_simulator_service.clear_logs()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@rfid_simulator_bp.route('/api/rfid-simulator/test-connection', methods=['POST'])
def test_connection():
    """测试连接"""
    try:
        ws = rfid_simulator_service.get_active_websocket()
        if not ws:
            return jsonify({
                'success': False, 
                'error': '没有可用的 ADB 客户端连接'
            })
        
        # 发送测试命令
        ws.send(json.dumps({
            'type': 'test_connection',
            'timestamp': datetime.now().isoformat()
        }))
        
        rfid_simulator_service._add_log('info', '发送连接测试请求')
        return jsonify({'success': True, 'message': '测试请求已发送'})
    except Exception as e:
        logger.error(f"[RfidSimulator] 测试连接失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@rfid_simulator_bp.route('/api/rfid-simulator/send', methods=['POST'])
def send_rfid():
    """发送单个 RFID"""
    try:
        data = request.get_json()
        rfid_code = data.get('rfid_code', '').strip()
        device_path = data.get('device_path', rfid_simulator_service.DEFAULT_DEVICE_PATH)
        send_enter = data.get('send_enter', True)
        
        if not rfid_code:
            return jsonify({'success': False, 'error': 'RFID 卡号不能为空'})
        
        # 验证卡号格式（只允许数字）
        if not rfid_code.isdigit():
            return jsonify({'success': False, 'error': 'RFID 卡号只能包含数字'})
        
        ws = rfid_simulator_service.get_active_websocket()
        if not ws:
            return jsonify({
                'success': False, 
                'error': '没有可用的 ADB 客户端连接'
            })
        
        # 构建命令
        commands = rfid_simulator_service.build_rfid_commands(rfid_code, device_path, send_enter)
        
        # 发送到客户端执行
        ws.send(json.dumps({
            'type': 'send_rfid',
            'rfid_code': rfid_code,
            'commands': commands,
            'inter_char_delay': rfid_simulator_service.DEFAULT_INTER_CHAR_DELAY,
            'enter_delay': rfid_simulator_service.DEFAULT_ENTER_DELAY,
            'timestamp': datetime.now().isoformat()
        }))
        
        rfid_simulator_service._add_log('info', f'发送 RFID: {rfid_code}')
        return jsonify({'success': True, 'message': f'已发送 RFID: {rfid_code}'})
    except Exception as e:
        logger.error(f"[RfidSimulator] 发送 RFID 失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@rfid_simulator_bp.route('/api/rfid-simulator/batch/start', methods=['POST'])
def start_batch():
    """开始批量模拟"""
    try:
        data = request.get_json()
        cards = data.get('cards', [])
        interval_seconds = data.get('interval_seconds', 5)
        send_enter = data.get('send_enter', True)
        device_path = data.get('device_path', rfid_simulator_service.DEFAULT_DEVICE_PATH)
        
        if not cards:
            return jsonify({'success': False, 'error': '卡片列表不能为空'})
        
        ws = rfid_simulator_service.get_active_websocket()
        if not ws:
            return jsonify({
                'success': False, 
                'error': '没有可用的 ADB 客户端连接'
            })
        
        # 创建任务（返回 dict）
        task = rfid_simulator_service.create_task(cards, interval_seconds, send_enter, device_path)
        
        # 发送批量任务到客户端
        ws.send(json.dumps({
            'type': 'batch_start',
            'task_id': task['task_id'],
            'cards': cards,
            'interval_seconds': interval_seconds,
            'send_enter': send_enter,
            'device_path': device_path,
            'inter_char_delay': rfid_simulator_service.DEFAULT_INTER_CHAR_DELAY,
            'enter_delay': rfid_simulator_service.DEFAULT_ENTER_DELAY,
            'event_map': rfid_simulator_service.RFID_EVENT_MAP,
            'timestamp': datetime.now().isoformat()
        }))
        
        return jsonify({
            'success': True, 
            'data': task
        })
    except Exception as e:
        logger.error(f"[RfidSimulator] 开始批量模拟失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@rfid_simulator_bp.route('/api/rfid-simulator/batch/pause', methods=['POST'])
def pause_batch():
    """暂停批量模拟"""
    try:
        ws = rfid_simulator_service.get_active_websocket()
        if ws:
            ws.send(json.dumps({'type': 'batch_pause'}))
        rfid_simulator_service.pause_task()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@rfid_simulator_bp.route('/api/rfid-simulator/batch/resume', methods=['POST'])
def resume_batch():
    """恢复批量模拟"""
    try:
        ws = rfid_simulator_service.get_active_websocket()
        if ws:
            ws.send(json.dumps({'type': 'batch_resume'}))
        rfid_simulator_service.resume_task()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@rfid_simulator_bp.route('/api/rfid-simulator/batch/stop', methods=['POST'])
def stop_batch():
    """停止批量模拟"""
    try:
        ws = rfid_simulator_service.get_active_websocket()
        if ws:
            ws.send(json.dumps({'type': 'batch_stop'}))
        rfid_simulator_service.stop_task()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@rfid_simulator_bp.route('/api/rfid-simulator/detect-device', methods=['POST'])
def detect_device():
    """检测 RFID 设备"""
    try:
        ws = rfid_simulator_service.get_active_websocket()
        if not ws:
            return jsonify({
                'success': False, 
                'error': '没有可用的 ADB 客户端连接'
            })
        
        ws.send(json.dumps({
            'type': 'detect_device',
            'timestamp': datetime.now().isoformat()
        }))
        
        rfid_simulator_service._add_log('info', '发送设备检测请求')
        return jsonify({'success': True, 'message': '设备检测请求已发送'})
    except Exception as e:
        logger.error(f"[RfidSimulator] 检测设备失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ==================== WebSocket 处理 ====================

def init_websocket(sock: Sock, app):
    """初始化 WebSocket 路由"""
    
    @sock.route('/ws/rfid-simulator')
    def rfid_simulator_ws(ws):
        """ADB 客户端 WebSocket 连接"""
        client_id = None
        logger.info("[RfidSimulator] 新的 WebSocket 连接")
        try:
            # 等待客户端注册消息
            while True:
                try:
                    message = ws.receive()  # 阻塞等待消息
                except Exception as recv_err:
                    logger.warning(f"[RfidSimulator] 接收消息错误: {recv_err}")
                    break
                    
                if not message:
                    logger.info("[RfidSimulator] 收到空消息，连接关闭")
                    break
                
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    if msg_type == 'register':
                        # 客户端注册
                        client_id = data.get('client_id', f"client_{datetime.now().timestamp()}")
                        ip_address = data.get('ip_address', 'unknown')
                        device_info = data.get('device_info')
                        
                        # 存储到路由层（唯一数据源）
                        _active_websockets[client_id] = ws
                        # 注册到服务层（只存状态，不存 WebSocket）
                        rfid_simulator_service.register_client(
                            client_id, ip_address, device_info=device_info
                        )
                        
                        ws.send(json.dumps({
                            'type': 'registered',
                            'client_id': client_id,
                            'message': '注册成功'
                        }))
                        logger.info(f"[RfidSimulator] 客户端注册成功: {client_id}")
                    
                    elif msg_type == 'heartbeat':
                        # 心跳
                        if client_id:
                            device_info = data.get('device_info')
                            seq = data.get('seq', 0)
                            rfid_simulator_service.update_heartbeat(client_id, device_info)
                            ws.send(json.dumps({'type': 'heartbeat_ack', 'seq': seq}))
                    
                    elif msg_type == 'result':
                        # 命令执行结果
                        success = data.get('success', False)
                        rfid_code = data.get('rfid_code', '')
                        name = data.get('name', '')
                        error = data.get('error', '')
                        
                        if success:
                            rfid_simulator_service._add_log(
                                'success', 
                                f'发送成功: {name} ({rfid_code})'
                            )
                        else:
                            rfid_simulator_service._add_log(
                                'error', 
                                f'发送失败: {name} ({rfid_code}) - {error}'
                            )
                        
                        # 更新任务状态
                        current_index = data.get('current_index')
                        if current_index is not None:
                            rfid_simulator_service.update_task_status(
                                'running', current_index, success
                            )
                    
                    elif msg_type == 'batch_progress':
                        # 批量进度更新
                        current_index = data.get('current_index', 0)
                        status = data.get('status', 'running')
                        rfid_simulator_service.update_task_status(status, current_index)
                    
                    elif msg_type == 'batch_complete':
                        # 批量完成
                        rfid_simulator_service.update_task_status('completed')
                        rfid_simulator_service._add_log('success', '批量模拟完成')
                    
                    elif msg_type == 'device_detected':
                        # 设备检测结果
                        device_path = data.get('device_path')
                        device_name = data.get('device_name', '')
                        if device_path:
                            rfid_simulator_service._add_log(
                                'success', 
                                f'检测到设备: {device_path} ({device_name})'
                            )
                        else:
                            rfid_simulator_service._add_log(
                                'warning', 
                                '未检测到 RFID 设备'
                            )
                    
                    elif msg_type == 'connection_test_result':
                        # 连接测试结果
                        success = data.get('success', False)
                        if success:
                            rfid_simulator_service._add_log('success', '连接测试成功')
                        else:
                            error = data.get('error', '未知错误')
                            rfid_simulator_service._add_log('error', f'连接测试失败: {error}')
                    
                    elif msg_type == 'error':
                        # 错误消息
                        error = data.get('error', '未知错误')
                        rfid_simulator_service._add_log('error', error)
                        logger.error(f"[RfidSimulator] 客户端错误: {error}")
                    
                except json.JSONDecodeError:
                    logger.warning(f"[RfidSimulator] 无效的 JSON 消息: {message}")
                except Exception as e:
                    logger.error(f"[RfidSimulator] 处理消息失败: {e}")
        
        except Exception as e:
            logger.error(f"[RfidSimulator] WebSocket 错误: {e}")
        finally:
            logger.info(f"[RfidSimulator] WebSocket 连接关闭: {client_id}")
            if client_id:
                # 从路由层移除（唯一数据源）
                _active_websockets.pop(client_id, None)
                # 从服务层注销状态
                rfid_simulator_service.unregister_client(client_id)
