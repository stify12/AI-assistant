"""
错误样本库路由模块 (US-19)

提供错误样本的 CRUD API 和导出功能。
"""
from flask import Blueprint, request, jsonify, send_file
from services.error_sample_service import ErrorSampleService

error_samples_bp = Blueprint('error_samples', __name__)


@error_samples_bp.route('/api/error-samples', methods=['GET'])
def get_samples():
    """
    获取错误样本列表
    
    Query Parameters:
        page: 页码，默认1
        page_size: 每页数量，默认20
        error_type: 错误类型筛选
        status: 状态筛选
        subject_id: 学科筛选
        cluster_id: 聚类筛选
        task_id: 任务筛选
        keyword: 关键词搜索
    """
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        error_type = request.args.get('error_type')
        status = request.args.get('status')
        subject_id = request.args.get('subject_id', type=int)
        cluster_id = request.args.get('cluster_id')
        task_id = request.args.get('task_id')
        keyword = request.args.get('keyword')
        
        # 参数校验
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        
        result = ErrorSampleService.get_samples(
            page=page,
            page_size=page_size,
            error_type=error_type,
            status=status,
            subject_id=subject_id,
            cluster_id=cluster_id,
            task_id=task_id,
            keyword=keyword
        )
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f'[ErrorSamples] 获取样本列表失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@error_samples_bp.route('/api/error-samples/statistics', methods=['GET'])
def get_statistics():
    """获取错误样本统计"""
    try:
        result = ErrorSampleService.get_statistics()
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        print(f'[ErrorSamples] 获取统计失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@error_samples_bp.route('/api/error-samples/<sample_id>', methods=['GET'])
def get_sample_detail(sample_id):
    """获取样本详情"""
    try:
        if not sample_id:
            return jsonify({'success': False, 'error': '样本ID不能为空'}), 400
        
        result = ErrorSampleService.get_sample_detail(sample_id)
        
        if not result:
            return jsonify({'success': False, 'error': '样本不存在'}), 404
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f'[ErrorSamples] 获取样本详情失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@error_samples_bp.route('/api/error-samples/batch-status', methods=['PUT'])
def batch_update_status():
    """
    批量更新样本状态
    
    Request Body:
        {
            "sample_ids": ["id1", "id2"],
            "status": "analyzed",
            "notes": "备注"
        }
    """
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        sample_ids = data.get('sample_ids', [])
        status = data.get('status')
        notes = data.get('notes')
        
        if not sample_ids:
            return jsonify({'success': False, 'error': '样本ID列表不能为空'}), 400
        
        if not status:
            return jsonify({'success': False, 'error': '状态不能为空'}), 400
        
        updated = ErrorSampleService.update_status(sample_ids, status, notes)
        
        return jsonify({
            'success': True,
            'data': {'updated': updated}
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f'[ErrorSamples] 批量更新状态失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@error_samples_bp.route('/api/error-samples/collect', methods=['POST'])
def collect_from_task():
    """
    从批量任务收集错误样本
    
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
        
        result = ErrorSampleService.collect_from_task(task_id)
        
        return jsonify({
            'success': True,
            'data': result,
            'message': f'收集完成: 新增 {result["collected"]} 条，跳过 {result["skipped"]} 条'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f'[ErrorSamples] 收集样本失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@error_samples_bp.route('/api/error-samples/export', methods=['POST'])
def export_samples():
    """
    导出错误样本
    
    Request Body:
        {
            "filters": {"error_type": "xxx", "status": "xxx"},
            "format": "xlsx"
        }
    """
    try:
        data = request.json or {}
        filters = data.get('filters', {})
        format = data.get('format', 'xlsx')
        
        if format not in ['xlsx', 'csv']:
            return jsonify({'success': False, 'error': '不支持的导出格式'}), 400
        
        filepath = ErrorSampleService.export_samples(filters, format)
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filepath.split('/')[-1].split('\\')[-1]
        )
        
    except Exception as e:
        print(f'[ErrorSamples] 导出样本失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
