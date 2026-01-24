"""
AI 智能分析 API 路由
提供分析触发、报告查询、层级下钻等接口
"""
from flask import Blueprint, jsonify, request
from services.ai_analysis_service import AIAnalysisService
from services.storage_service import StorageService

analysis_bp = Blueprint('analysis', __name__)

# 初始化分析服务
analysis_service = AIAnalysisService()


@analysis_bp.route('/api/analysis/trigger/<task_id>', methods=['POST'])
def trigger_analysis(task_id):
    """触发任务分析"""
    try:
        # 检查任务是否存在
        task_data = StorageService.load_batch_task(task_id)
        if not task_data:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        # 检查任务是否已完成
        if task_data.get('status') != 'completed':
            return jsonify({'success': False, 'error': '任务尚未完成，无法分析'}), 400
        
        # 触发分析
        result = analysis_service.trigger_analysis(task_id)
        
        return jsonify({
            'success': True,
            'message': '分析任务已加入队列',
            'queued': result.get('queued', False),
            'position': result.get('position', 0)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/report/<task_id>', methods=['GET'])
def get_analysis_report(task_id):
    """获取分析报告"""
    try:
        report = analysis_service.get_report(task_id)
        
        if not report:
            return jsonify({
                'success': True,
                'report': None,
                'message': '暂无分析报告'
            })
        
        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/drilldown/<task_id>', methods=['GET'])
def get_drilldown_data(task_id):
    """获取层级下钻数据"""
    try:
        # 获取下钻参数
        level = request.args.get('level', 'subject')  # subject, book, page, question
        subject = request.args.get('subject')
        book = request.args.get('book')
        page = request.args.get('page')
        
        report = analysis_service.get_report(task_id)
        
        if not report:
            return jsonify({
                'success': False,
                'error': '暂无分析报告'
            }), 404
        
        drill_down_data = report.get('drill_down_data', {})
        
        # 根据层级返回对应数据
        if level == 'subject':
            # 返回学科级别数据
            data = drill_down_data.get('by_subject', [])
        elif level == 'book':
            # 返回指定学科下的书本数据
            if not subject:
                return jsonify({'success': False, 'error': '缺少学科参数'}), 400
            by_book = drill_down_data.get('by_book', {})
            data = by_book.get(subject, [])
        elif level == 'page':
            # 返回指定书本下的页码数据
            if not subject or not book:
                return jsonify({'success': False, 'error': '缺少学科或书本参数'}), 400
            by_page = drill_down_data.get('by_page', {})
            key = f"{subject}|{book}"
            data = by_page.get(key, [])
        elif level == 'question':
            # 返回指定页码下的题目数据
            if not subject or not book or not page:
                return jsonify({'success': False, 'error': '缺少学科、书本或页码参数'}), 400
            by_question = drill_down_data.get('by_question', {})
            key = f"{subject}|{book}|{page}"
            data = by_question.get(key, [])
        else:
            return jsonify({'success': False, 'error': '无效的层级参数'}), 400
        
        return jsonify({
            'success': True,
            'level': level,
            'data': data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analysis_bp.route('/api/analysis/status/<task_id>', methods=['GET'])
def get_analysis_status(task_id):
    """获取分析状态"""
    try:
        status = analysis_service.get_status(task_id)
        
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
