"""
多维度数据下钻路由 (US-21)
"""
from flask import Blueprint, request, jsonify

from services.drilldown_service import DrilldownService

drilldown_bp = Blueprint('drilldown', __name__)


@drilldown_bp.route('/api/drilldown/data', methods=['GET'])
def get_drilldown_data():
    """获取下钻数据"""
    try:
        level = request.args.get('level', 'overall')
        parent_id = request.args.get('parent_id')
        
        filters = {}
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        if request.args.get('model'):
            filters['model'] = request.args.get('model')
        
        result = DrilldownService.get_drilldown_data(level, parent_id, filters)
        return jsonify({'success': True, **result})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
