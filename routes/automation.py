"""
自动化任务管理 API 路由
提供任务配置、队列状态、全局控制等接口
使用统一调度服务 UnifiedScheduleService
"""
from flask import Blueprint, jsonify, request
from services.unified_schedule_service import UnifiedScheduleService

automation_bp = Blueprint('automation', __name__)


@automation_bp.route('/api/automation/tasks', methods=['GET'])
def get_all_tasks():
    """获取所有自动化任务列表"""
    try:
        tasks = UnifiedScheduleService.get_all_tasks()
        return jsonify({
            'success': True,
            'tasks': tasks
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@automation_bp.route('/api/automation/history/<task_type>', methods=['GET'])
def get_task_history(task_type):
    """获取任务执行历史"""
    try:
        limit = request.args.get('limit', 20, type=int)
        history = UnifiedScheduleService.get_task_history(task_type, limit)
        
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@automation_bp.route('/api/automation/status', methods=['GET'])
def get_scheduler_status():
    """获取调度器状态"""
    try:
        status = UnifiedScheduleService.get_scheduler_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@automation_bp.route('/api/automation/pause', methods=['POST'])
def pause_all():
    """暂停所有自动化任务"""
    try:
        UnifiedScheduleService.pause_all()
        return jsonify({'success': True, 'message': '所有自动任务已暂停'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@automation_bp.route('/api/automation/resume', methods=['POST'])
def resume_all():
    """恢复所有自动化任务"""
    try:
        UnifiedScheduleService.resume_all()
        return jsonify({'success': True, 'message': '所有自动任务已恢复'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
