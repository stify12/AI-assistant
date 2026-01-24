"""
错误批量标记路由 (US-22)
"""
from flask import Blueprint, request, jsonify
from datetime import datetime

from services.database_service import AppDatabaseService

error_mark_bp = Blueprint('error_mark', __name__)


@error_mark_bp.route('/api/errors/mark', methods=['POST'])
def mark_errors():
    """批量标记错误"""
    data = request.get_json() or {}
    
    error_ids = data.get('error_ids', [])
    mark_type = data.get('mark_type', 'reviewed')  # reviewed, ignored, important, fixed
    note = data.get('note', '')
    
    if not error_ids:
        return jsonify({'success': False, 'error': '缺少error_ids'}), 400
    
    try:
        db = AppDatabaseService()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for error_id in error_ids:
            db.execute(
                """UPDATE error_samples 
                   SET mark_type=%s, mark_note=%s, marked_at=%s
                   WHERE id=%s""",
                (mark_type, note, now, error_id)
            )
        
        return jsonify({
            'success': True,
            'marked_count': len(error_ids),
            'mark_type': mark_type
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@error_mark_bp.route('/api/errors/marks', methods=['GET'])
def get_marked_errors():
    """获取已标记的错误"""
    mark_type = request.args.get('mark_type')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    
    try:
        db = AppDatabaseService()
        
        sql = "SELECT * FROM error_samples WHERE mark_type IS NOT NULL"
        params = []
        
        if mark_type:
            sql += " AND mark_type=%s"
            params.append(mark_type)
        
        sql += " ORDER BY marked_at DESC LIMIT %s OFFSET %s"
        params.extend([page_size, (page - 1) * page_size])
        
        rows = db.fetch_all(sql, tuple(params))
        
        # 获取总数
        count_sql = "SELECT COUNT(*) as cnt FROM error_samples WHERE mark_type IS NOT NULL"
        if mark_type:
            count_sql += f" AND mark_type='{mark_type}'"
        count_row = db.fetch_one(count_sql)
        total = count_row.get('cnt', 0) if count_row else 0
        
        return jsonify({
            'success': True,
            'data': rows or [],
            'total': total,
            'page': page,
            'page_size': page_size
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@error_mark_bp.route('/api/errors/unmark', methods=['POST'])
def unmark_errors():
    """取消标记"""
    data = request.get_json() or {}
    error_ids = data.get('error_ids', [])
    
    if not error_ids:
        return jsonify({'success': False, 'error': '缺少error_ids'}), 400
    
    try:
        db = AppDatabaseService()
        
        for error_id in error_ids:
            db.execute(
                "UPDATE error_samples SET mark_type=NULL, mark_note=NULL, marked_at=NULL WHERE id=%s",
                (error_id,)
            )
        
        return jsonify({'success': True, 'unmarked_count': len(error_ids)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
