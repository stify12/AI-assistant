"""
错误关联分析路由 (US-20)
"""
from flask import Blueprint, request, jsonify

from services.error_correlation_service import ErrorCorrelationService

error_correlation_bp = Blueprint('error_correlation', __name__)


@error_correlation_bp.route('/api/error-correlation/analyze', methods=['GET'])
def analyze_correlations():
    """分析错误关联"""
    subject_id = request.args.get('subject_id', type=int)
    book_name = request.args.get('book_name')
    min_occurrence = request.args.get('min_occurrence', 2, type=int)
    
    result = ErrorCorrelationService.analyze_correlations(
        subject_id, book_name, min_occurrence
    )
    return jsonify({'success': True, **result})


@error_correlation_bp.route('/api/error-correlation/patterns', methods=['GET'])
def find_patterns():
    """查找错误模式"""
    error_type = request.args.get('error_type')
    limit = request.args.get('limit', 10, type=int)
    
    if not error_type:
        return jsonify({'success': False, 'error': '缺少error_type参数'}), 400
    
    result = ErrorCorrelationService.find_error_patterns(error_type, limit)
    return jsonify({'success': True, **result})


@error_correlation_bp.route('/api/error-correlation/report', methods=['GET'])
def generate_report():
    """生成关联分析报告"""
    subject_id = request.args.get('subject_id', type=int)
    
    result = ErrorCorrelationService.generate_correlation_report(subject_id)
    return jsonify(result)


@error_correlation_bp.route('/api/error-correlation/chain', methods=['GET'])
def get_error_chain():
    """获取错误链"""
    task_id = request.args.get('task_id')
    page_num = request.args.get('page_num', type=int)
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id参数'}), 400
    
    result = ErrorCorrelationService.get_error_chain(task_id, page_num)
    return jsonify({'success': True, **result})
