"""
最佳实践库路由 (US-16)
"""
from flask import Blueprint, request, jsonify

from services.best_practice_service import BestPracticeService

best_practice_bp = Blueprint('best_practice', __name__)


@best_practice_bp.route('/api/best-practices', methods=['GET'])
def get_practices():
    """获取最佳实践列表"""
    category = request.args.get('category')
    tag = request.args.get('tag')
    starred_only = request.args.get('starred') == 'true'
    
    practices = BestPracticeService.get_practices(category, tag, starred_only)
    return jsonify({'success': True, 'data': practices})


@best_practice_bp.route('/api/best-practices/<practice_id>', methods=['GET'])
def get_practice(practice_id):
    """获取单个最佳实践"""
    practice = BestPracticeService.get_practice(practice_id)
    if practice:
        return jsonify({'success': True, 'data': practice})
    return jsonify({'success': False, 'error': '实践不存在'}), 404


@best_practice_bp.route('/api/best-practices', methods=['POST'])
def add_practice():
    """添加最佳实践"""
    data = request.get_json() or {}
    
    name = data.get('name')
    category = data.get('category', '通用')
    prompt_content = data.get('prompt_content')
    
    if not name or not prompt_content:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    result = BestPracticeService.add_practice(
        name=name,
        category=category,
        prompt_content=prompt_content,
        description=data.get('description', ''),
        tags=data.get('tags', []),
        metrics=data.get('metrics', {})
    )
    return jsonify(result)


@best_practice_bp.route('/api/best-practices/<practice_id>', methods=['PUT'])
def update_practice(practice_id):
    """更新最佳实践"""
    data = request.get_json() or {}
    result = BestPracticeService.update_practice(practice_id, data)
    
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 404


@best_practice_bp.route('/api/best-practices/<practice_id>', methods=['DELETE'])
def delete_practice(practice_id):
    """删除最佳实践"""
    result = BestPracticeService.delete_practice(practice_id)
    
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 404


@best_practice_bp.route('/api/best-practices/<practice_id>/star', methods=['POST'])
def toggle_star(practice_id):
    """切换星标"""
    result = BestPracticeService.toggle_star(practice_id)
    return jsonify(result)


@best_practice_bp.route('/api/best-practices/<practice_id>/use', methods=['POST'])
def record_usage(practice_id):
    """记录使用"""
    result = BestPracticeService.record_usage(practice_id)
    return jsonify(result)


@best_practice_bp.route('/api/best-practices/<practice_id>/versions', methods=['GET'])
def get_versions(practice_id):
    """获取版本历史"""
    versions = BestPracticeService.get_prompt_versions(practice_id)
    return jsonify({'success': True, 'data': versions})


@best_practice_bp.route('/api/best-practices/compare', methods=['GET'])
def compare_practices():
    """对比两个实践"""
    id1 = request.args.get('id1')
    id2 = request.args.get('id2')
    
    if not id1 or not id2:
        return jsonify({'success': False, 'error': '缺少对比ID'}), 400
    
    result = BestPracticeService.compare_practices(id1, id2)
    return jsonify(result)


@best_practice_bp.route('/api/best-practices/categories', methods=['GET'])
def get_categories():
    """获取所有分类"""
    categories = BestPracticeService.get_categories()
    return jsonify({'success': True, 'data': categories})


@best_practice_bp.route('/api/best-practices/tags', methods=['GET'])
def get_tags():
    """获取所有标签"""
    tags = BestPracticeService.get_tags()
    return jsonify({'success': True, 'data': tags})


@best_practice_bp.route('/api/best-practices/import', methods=['POST'])
def import_from_task():
    """从任务导入"""
    data = request.get_json() or {}
    task_id = data.get('task_id')
    name = data.get('name')
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    result = BestPracticeService.import_from_task(task_id, name)
    return jsonify(result)
