"""
批次对比分析路由 (US-18, US-33)
"""
from flask import Blueprint, request, jsonify

from services.batch_compare_service import BatchCompareService

batch_compare_bp = Blueprint('batch_compare', __name__)


@batch_compare_bp.route('/api/batch-compare/trend', methods=['GET'])
def get_batch_trend():
    """获取批次准确率趋势"""
    try:
        subject_id = request.args.get('subject_id', type=int)
        book_name = request.args.get('book_name')
        days = request.args.get('days', 30, type=int)
        
        result = BatchCompareService.get_batch_trend(subject_id, book_name, days)
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@batch_compare_bp.route('/api/batch-compare/periods', methods=['GET'])
def compare_periods():
    """对比两个时间段"""
    try:
        period1_start = request.args.get('period1_start')
        period1_end = request.args.get('period1_end')
        period2_start = request.args.get('period2_start')
        period2_end = request.args.get('period2_end')
        subject_id = request.args.get('subject_id', type=int)
        
        if not all([period1_start, period1_end, period2_start, period2_end]):
            return jsonify({'success': False, 'error': '缺少时间段参数'}), 400
        
        result = BatchCompareService.compare_periods(
            period1_start, period1_end,
            period2_start, period2_end,
            subject_id
        )
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@batch_compare_bp.route('/api/batch-compare/baseline', methods=['GET'])
def compare_with_baseline():
    """与基线对比"""
    try:
        task_id = request.args.get('task_id')
        baseline_task_id = request.args.get('baseline_task_id')
        
        if not task_id:
            return jsonify({'success': False, 'error': '缺少task_id参数'}), 400
        
        result = BatchCompareService.compare_with_baseline(task_id, baseline_task_id)
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 404
        
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@batch_compare_bp.route('/api/batch-compare/models', methods=['GET'])
def get_model_comparison():
    """获取模型间对比"""
    try:
        days = request.args.get('days', 30, type=int)
        result = BatchCompareService.get_model_comparison(days)
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
