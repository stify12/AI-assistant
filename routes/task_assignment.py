"""
测试任务分配路由 (US-13)
"""
from flask import Blueprint, request, jsonify

from services.task_assignment_service import TaskAssignmentService

task_assignment_bp = Blueprint('task_assignment', __name__)


@task_assignment_bp.route('/api/assignments', methods=['GET'])
def get_assignments():
    """获取任务分配列表"""
    plan_id = request.args.get('plan_id')
    assignee_id = request.args.get('assignee_id')
    status = request.args.get('status')
    
    assignments = TaskAssignmentService.get_assignments(plan_id, assignee_id, status)
    return jsonify({'success': True, 'data': assignments})


@task_assignment_bp.route('/api/assignments/assign', methods=['POST'])
def assign_task():
    """分配任务"""
    data = request.get_json() or {}
    
    plan_id = data.get('plan_id')
    task_id = data.get('task_id')
    assignee_id = data.get('assignee_id')
    assignee_name = data.get('assignee_name', '')
    
    if not all([plan_id, task_id, assignee_id]):
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    result = TaskAssignmentService.assign_task(
        plan_id, task_id, assignee_id, assignee_name
    )
    
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 500


@task_assignment_bp.route('/api/assignments/batch', methods=['POST'])
def batch_assign():
    """批量分配任务"""
    data = request.get_json() or {}
    
    plan_id = data.get('plan_id')
    assignments = data.get('assignments', [])
    
    if not plan_id or not assignments:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    result = TaskAssignmentService.batch_assign(plan_id, assignments)
    return jsonify(result)


@task_assignment_bp.route('/api/assignments/status', methods=['PUT'])
def update_status():
    """更新任务状态"""
    data = request.get_json() or {}
    
    plan_id = data.get('plan_id')
    task_id = data.get('task_id')
    status = data.get('status')
    comment = data.get('comment')
    
    if not all([plan_id, task_id, status]):
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    result = TaskAssignmentService.update_status(plan_id, task_id, status, comment)
    
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 500


@task_assignment_bp.route('/api/assignments/comments', methods=['GET'])
def get_comments():
    """获取任务评论"""
    plan_id = request.args.get('plan_id')
    task_id = request.args.get('task_id')
    
    if not plan_id or not task_id:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    comments = TaskAssignmentService.get_comments(plan_id, task_id)
    return jsonify({'success': True, 'data': comments})


@task_assignment_bp.route('/api/assignments/comments', methods=['POST'])
def add_comment():
    """添加任务评论"""
    data = request.get_json() or {}
    
    plan_id = data.get('plan_id')
    task_id = data.get('task_id')
    user_id = data.get('user_id', 'anonymous')
    content = data.get('content')
    
    if not all([plan_id, task_id, content]):
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    result = TaskAssignmentService.add_comment(plan_id, task_id, user_id, content)
    
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 500


@task_assignment_bp.route('/api/assignments/workload', methods=['GET'])
def get_workload():
    """获取工作量统计"""
    plan_id = request.args.get('plan_id')
    
    result = TaskAssignmentService.get_workload_summary(plan_id)
    return jsonify({'success': True, **result})
