"""
自动化任务管理 API 路由
提供任务配置、队列状态、全局控制等接口
"""
from flask import Blueprint, jsonify, request
from services.automation_service import AutomationService

automation_bp = Blueprint('automation', __name__)

# 初始化自动化服务
automation_service = AutomationService()


@automation_bp.route('/api/automation/tasks', methods=['GET'])
def get_all_tasks():
    """获取所有自动化任务列表"""
    try:
        tasks = automation_service.get_all_tasks()
        return jsonify({
            'success': True,
            'tasks': tasks
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@automation_bp.route('/api/automation/tasks/<task_type>/config', methods=['GET'])
def get_task_config(task_type):
    """获取指定任务的配置"""
    try:
        config = automation_service.get_task_config(task_type)
        if config is None:
            return jsonify({'success': False, 'error': '任务类型不存在'}), 404
        
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@automation_bp.route('/api/automation/tasks/<task_type>/config', methods=['PUT'])
def update_task_config(task_type):
    """更新指定任务的配置"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '缺少配置数据'}), 400
        
        result = automation_service.update_task_config(task_type, data)
        if not result.get('success'):
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@automation_bp.route('/api/automation/history/<task_type>', methods=['GET'])
def get_task_history(task_type):
    """获取任务执行历史"""
    try:
        limit = request.args.get('limit', 20, type=int)
        history = automation_service.get_task_history(task_type, limit)
        
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@automation_bp.route('/api/automation/queue', methods=['GET'])
def get_queue_status():
    """获取队列状态"""
    try:
        status = automation_service.get_queue_status()
        return jsonify({
            'success': True,
            'queue': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@automation_bp.route('/api/automation/pause', methods=['POST'])
def pause_all():
    """暂停所有自动化任务"""
    try:
        result = automation_service.pause_all()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@automation_bp.route('/api/automation/resume', methods=['POST'])
def resume_all():
    """恢复所有自动化任务"""
    try:
        result = automation_service.resume_all()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@automation_bp.route('/api/automation/queue/clear', methods=['POST'])
def clear_queue():
    """清空队列"""
    try:
        result = automation_service.clear_queue()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
