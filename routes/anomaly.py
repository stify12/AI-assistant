"""
异常检测路由模块 (US-26)

提供异常检测和告警管理 API。
"""
from flask import Blueprint, request, jsonify, send_file
from services.anomaly_service import AnomalyService
from services.storage_service import StorageService

anomaly_bp = Blueprint('anomaly', __name__)


@anomaly_bp.route('/api/anomaly/task/<task_id>/questions', methods=['GET'])
def detect_question_anomalies(task_id):
    """
    检测任务中的题目异常
    
    返回：
    - 全员错误题目
    - 不稳定判断题目
    - 高错误率题目
    """
    try:
        task_data = StorageService.load_batch_task(task_id)
        if not task_data:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        result = AnomalyService.detect_question_anomalies(task_data)
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f'[Anomaly] 题目异常检测失败: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@anomaly_bp.route('/api/anomaly/logs', methods=['GET'])
def get_anomaly_logs():
    """
    获取异常日志列表
    
    Query Parameters:
        page: 页码，默认1
        page_size: 每页数量，默认20
        anomaly_type: 异常类型筛选
        severity: 严重程度筛选
        is_acknowledged: 是否已确认筛选
    """
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        anomaly_type = request.args.get('anomaly_type')
        severity = request.args.get('severity')
        is_acknowledged = request.args.get('is_acknowledged')
        
        # 转换布尔值
        if is_acknowledged is not None:
            is_acknowledged = is_acknowledged.lower() in ('true', '1', 'yes')
        
        result = AnomalyService.get_anomaly_logs(
            page=page,
            page_size=page_size,
            anomaly_type=anomaly_type,
            severity=severity,
            is_acknowledged=is_acknowledged
        )
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f'[Anomaly] 获取异常日志失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@anomaly_bp.route('/api/anomaly/statistics', methods=['GET'])
def get_statistics():
    """获取异常统计"""
    try:
        result = AnomalyService.get_statistics()
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        print(f'[Anomaly] 获取统计失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@anomaly_bp.route('/api/anomaly/detect', methods=['POST'])
def detect_anomaly():
    """
    手动触发异常检测
    
    Request Body:
        {
            "task_id": "任务ID"
        }
    """
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        task_id = data.get('task_id')
        if not task_id:
            return jsonify({'success': False, 'error': '任务ID不能为空'}), 400
        
        result = AnomalyService.detect_task_anomaly(task_id)
        
        if result:
            return jsonify({
                'success': True,
                'data': result,
                'message': '检测到异常'
            })
        else:
            return jsonify({
                'success': True,
                'data': None,
                'message': '未检测到异常'
            })
        
    except Exception as e:
        print(f'[Anomaly] 异常检测失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@anomaly_bp.route('/api/anomaly/<anomaly_id>/acknowledge', methods=['PUT'])
def acknowledge_anomaly(anomaly_id):
    """确认异常"""
    try:
        if not anomaly_id:
            return jsonify({'success': False, 'error': '异常ID不能为空'}), 400
        
        # 获取用户ID（如果有登录系统）
        user_id = request.json.get('user_id') if request.json else None
        
        success = AnomalyService.acknowledge_anomaly(anomaly_id, user_id)
        
        if success:
            return jsonify({'success': True, 'message': '已确认'})
        else:
            return jsonify({'success': False, 'error': '确认失败'}), 400
        
    except Exception as e:
        print(f'[Anomaly] 确认异常失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@anomaly_bp.route('/api/anomaly/threshold', methods=['PUT'])
def set_threshold():
    """
    设置异常阈值
    
    Request Body:
        {
            "threshold_sigma": 2.0
        }
    """
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        threshold = data.get('threshold_sigma')
        if threshold is None:
            return jsonify({'success': False, 'error': '阈值不能为空'}), 400
        
        AnomalyService.set_threshold(float(threshold))
        
        return jsonify({
            'success': True,
            'message': f'阈值已设置为 {threshold}σ'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f'[Anomaly] 设置阈值失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@anomaly_bp.route('/api/anomaly/task/<task_id>/export', methods=['GET'])
def export_question_anomalies(task_id):
    """
    导出任务题目异常检测结果到Excel
    
    Returns:
        Excel文件下载
    """
    try:
        filepath = AnomalyService.export_question_anomalies_to_excel(task_id)
        
        if not filepath:
            return jsonify({'success': False, 'error': '任务不存在或导出失败'}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filepath.split('/')[-1].split('\\')[-1],
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        print(f'[Anomaly] 导出异常检测结果失败: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
