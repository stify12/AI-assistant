"""
保存常用筛选路由 (US-24)
"""
from flask import Blueprint, request, jsonify

from services.saved_filter_service import SavedFilterService

saved_filter_bp = Blueprint('saved_filter', __name__)


@saved_filter_bp.route('/api/filters', methods=['GET'])
def get_filters():
    """获取保存的筛选条件"""
    filter_type = request.args.get('type')
    filters = SavedFilterService.get_filters(filter_type)
    return jsonify({'success': True, 'data': filters})


@saved_filter_bp.route('/api/filters/default', methods=['GET'])
def get_default_filter():
    """获取默认筛选条件"""
    filter_type = request.args.get('type')
    if not filter_type:
        return jsonify({'success': False, 'error': '缺少type参数'}), 400
    
    f = SavedFilterService.get_default_filter(filter_type)
    return jsonify({'success': True, 'data': f})


@saved_filter_bp.route('/api/filters', methods=['POST'])
def save_filter():
    """保存筛选条件"""
    data = request.get_json() or {}
    
    name = data.get('name')
    filter_type = data.get('type')
    conditions = data.get('conditions', {})
    is_default = data.get('is_default', False)
    
    if not name or not filter_type:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400
    
    result = SavedFilterService.save_filter(name, filter_type, conditions, is_default)
    return jsonify(result)


@saved_filter_bp.route('/api/filters/<filter_id>/use', methods=['POST'])
def use_filter(filter_id):
    """使用筛选条件"""
    result = SavedFilterService.use_filter(filter_id)
    return jsonify(result)


@saved_filter_bp.route('/api/filters/<filter_id>', methods=['PUT'])
def update_filter(filter_id):
    """更新筛选条件"""
    data = request.get_json() or {}
    result = SavedFilterService.update_filter(filter_id, data)
    return jsonify(result)


@saved_filter_bp.route('/api/filters/<filter_id>', methods=['DELETE'])
def delete_filter(filter_id):
    """删除筛选条件"""
    result = SavedFilterService.delete_filter(filter_id)
    return jsonify(result)
