"""
自动化流程路由 - 流程编排、坐标配置、便捷操作 API
"""

import json
import logging
from flask import Blueprint, request, jsonify
from datetime import datetime

from services.workflow_service import workflow_service
from services.rfid_simulator_service import rfid_simulator_service

logger = logging.getLogger(__name__)

workflow_bp = Blueprint('workflow', __name__)


# ==================== 操作模块 ====================

@workflow_bp.route('/api/workflow/modules', methods=['GET'])
def get_modules():
    """获取所有操作模块"""
    try:
        modules = workflow_service.get_modules()
        return jsonify({'success': True, 'data': modules})
    except Exception as e:
        logger.error(f"获取模块失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@workflow_bp.route('/api/workflow/modules/<module_id>', methods=['GET'])
def get_module(module_id):
    """获取单个模块详情"""
    try:
        module = workflow_service.get_module(module_id)
        if module:
            return jsonify({'success': True, 'data': module})
        return jsonify({'success': False, 'error': '模块不存在'})
    except Exception as e:
        logger.error(f"获取模块详情失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ==================== 坐标配置 ====================

@workflow_bp.route('/api/workflow/coordinates', methods=['GET'])
def get_coordinates():
    """获取所有坐标配置"""
    try:
        coords = workflow_service.get_coordinates()
        return jsonify({'success': True, 'data': coords})
    except Exception as e:
        logger.error(f"获取坐标失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@workflow_bp.route('/api/workflow/coordinates/<key>', methods=['PUT'])
def update_coordinate(key):
    """更新坐标"""
    try:
        data = request.get_json()
        x = data.get('x')
        y = data.get('y')
        name = data.get('name')
        wait_after = data.get('wait_after')
        
        if x is None or y is None:
            return jsonify({'success': False, 'error': '坐标不能为空'})
        
        success = workflow_service.update_coordinate(key, x, y, name, wait_after)
        if success:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': '坐标不存在'})
    except Exception as e:
        logger.error(f"更新坐标失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@workflow_bp.route('/api/workflow/coordinates', methods=['POST'])
def add_coordinate():
    """添加新坐标"""
    try:
        data = request.get_json()
        key = data.get('key')
        x = data.get('x')
        y = data.get('y')
        name = data.get('name')
        category = data.get('category', 'custom')
        wait_after = data.get('wait_after', 1)
        
        if not key or x is None or y is None or not name:
            return jsonify({'success': False, 'error': '参数不完整'})
        
        success = workflow_service.add_coordinate(key, x, y, name, category, wait_after)
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"添加坐标失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@workflow_bp.route('/api/workflow/coordinates/<key>', methods=['DELETE'])
def delete_coordinate(key):
    """删除坐标"""
    try:
        success = workflow_service.delete_coordinate(key)
        if success:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': '无法删除系统坐标'})
    except Exception as e:
        logger.error(f"删除坐标失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@workflow_bp.route('/api/workflow/coordinates/export', methods=['GET'])
def export_coordinates():
    """导出坐标配置"""
    try:
        json_str = workflow_service.export_coordinates()
        return jsonify({'success': True, 'data': json_str})
    except Exception as e:
        logger.error(f"导出坐标失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@workflow_bp.route('/api/workflow/coordinates/import', methods=['POST'])
def import_coordinates():
    """导入坐标配置"""
    try:
        data = request.get_json()
        json_str = data.get('config')
        if not json_str:
            return jsonify({'success': False, 'error': '配置不能为空'})
        
        success = workflow_service.import_coordinates(json_str)
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"导入坐标失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ==================== 便捷操作 ====================

@workflow_bp.route('/api/workflow/recent', methods=['GET'])
def get_recent_items():
    """获取最近使用的班级和书本"""
    try:
        recent = workflow_service.get_recent_items()
        return jsonify({'success': True, 'data': recent})
    except Exception as e:
        logger.error(f"获取最近使用失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@workflow_bp.route('/api/workflow/recent', methods=['POST'])
def add_recent_item():
    """添加最近使用项"""
    try:
        data = request.get_json()
        item_type = data.get('type')  # class | book
        item = data.get('item')
        
        if not item_type or not item:
            return jsonify({'success': False, 'error': '参数不完整'})
        
        success = workflow_service.add_recent_item(item_type, item)
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"添加最近使用失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@workflow_bp.route('/api/workflow/recent', methods=['DELETE'])
def clear_recent_items():
    """清空最近使用"""
    try:
        item_type = request.args.get('type')
        success = workflow_service.clear_recent_items(item_type)
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"清空最近使用失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ==================== 流程管理 ====================

@workflow_bp.route('/api/workflow/templates', methods=['GET'])
def get_workflows():
    """获取保存的流程模板"""
    try:
        workflows = workflow_service.get_saved_workflows()
        return jsonify({'success': True, 'data': workflows})
    except Exception as e:
        logger.error(f"获取流程模板失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@workflow_bp.route('/api/workflow/templates', methods=['POST'])
def save_workflow():
    """保存流程模板"""
    try:
        data = request.get_json()
        workflow_id = workflow_service.save_workflow(data)
        return jsonify({'success': True, 'data': {'id': workflow_id}})
    except Exception as e:
        logger.error(f"保存流程模板失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@workflow_bp.route('/api/workflow/templates/<workflow_id>', methods=['DELETE'])
def delete_workflow(workflow_id):
    """删除流程模板"""
    try:
        success = workflow_service.delete_workflow(workflow_id)
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"删除流程模板失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ==================== 流程执行 ====================

@workflow_bp.route('/api/workflow/execute', methods=['POST'])
def execute_workflow():
    """执行流程"""
    try:
        data = request.get_json()
        workflow = data.get('workflow')
        params = data.get('params', {})
        
        if not workflow:
            return jsonify({'success': False, 'error': '流程不能为空'})
        
        # 检查 WebSocket 连接
        ws = rfid_simulator_service.get_active_websocket()
        if not ws:
            return jsonify({'success': False, 'error': '没有可用的 ADB 客户端连接'})
        
        # 构建命令序列
        commands = workflow_service.build_workflow_commands(workflow, params)
        
        if not commands:
            return jsonify({'success': False, 'error': '流程为空'})
        
        # 发送到客户端执行
        ws.send(json.dumps({
            'type': 'execute_workflow',
            'commands': commands,
            'params': params,
            'timestamp': datetime.now().isoformat()
        }))
        
        return jsonify({
            'success': True, 
            'data': {
                'command_count': len(commands),
                'commands': commands
            }
        })
    except Exception as e:
        logger.error(f"执行流程失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@workflow_bp.route('/api/workflow/execute/step', methods=['POST'])
def execute_single_step():
    """执行单个步骤"""
    try:
        data = request.get_json()
        step_type = data.get('type')  # click | input | rfid | wait
        
        ws = rfid_simulator_service.get_active_websocket()
        if not ws:
            return jsonify({'success': False, 'error': '没有可用的 ADB 客户端连接'})
        
        command = {
            'type': step_type,
            'timestamp': datetime.now().isoformat()
        }
        
        if step_type == 'click':
            command['x'] = data.get('x')
            command['y'] = data.get('y')
            command['wait_after'] = data.get('wait_after', 1)
        elif step_type == 'input':
            command['x'] = data.get('x')
            command['y'] = data.get('y')
            command['value'] = data.get('value')
        elif step_type == 'rfid':
            command['rfid_code'] = data.get('rfid_code')
        elif step_type == 'wait':
            command['seconds'] = data.get('seconds', 1)
        
        ws.send(json.dumps({
            'type': 'execute_step',
            'command': command
        }))
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"执行步骤失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@workflow_bp.route('/api/workflow/sync-coordinates', methods=['POST'])
def sync_coordinates_to_device():
    """同步坐标配置到手机端"""
    try:
        ws = rfid_simulator_service.get_active_websocket()
        if not ws:
            return jsonify({'success': False, 'error': '没有可用的 ADB 客户端连接'})
        
        coords = workflow_service.get_coordinates()
        
        ws.send(json.dumps({
            'type': 'sync_coordinates',
            'coordinates': coords['all'],
            'timestamp': datetime.now().isoformat()
        }))
        
        return jsonify({'success': True, 'message': '坐标同步请求已发送'})
    except Exception as e:
        logger.error(f"同步坐标失败: {e}")
        return jsonify({'success': False, 'error': str(e)})
