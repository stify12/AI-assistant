"""
优化建议路由模块 (US-28)

提供AI优化建议生成和管理 API。
"""
from flask import Blueprint, request, jsonify, send_file
from services.optimization_service import OptimizationService

optimization_bp = Blueprint('optimization', __name__)


@optimization_bp.route('/api/optimization/suggestions', methods=['GET'])
def get_suggestions():
    """
    获取优化建议列表
    
    Query Parameters:
        page: 页码
        page_size: 每页数量
        status: 状态筛选
        priority: 优先级筛选
    """
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        status = request.args.get('status')
        priority = request.args.get('priority')
        
        result = OptimizationService.get_suggestions(
            status=status,
            priority=priority,
            page=page,
            page_size=page_size
        )
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f'[Optimization] 获取建议列表失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@optimization_bp.route('/api/optimization/suggestions/<suggestion_id>', methods=['GET'])
def get_suggestion_detail(suggestion_id):
    """获取建议详情"""
    try:
        if not suggestion_id:
            return jsonify({'success': False, 'error': '建议ID不能为空'}), 400
        
        result = OptimizationService.get_suggestion_detail(suggestion_id)
        
        if not result:
            return jsonify({'success': False, 'error': '建议不存在'}), 404
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f'[Optimization] 获取建议详情失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@optimization_bp.route('/api/optimization/generate', methods=['POST'])
def generate_suggestions():
    """
    生成优化建议
    
    Request Body:
        {
            "sample_ids": ["id1", "id2"],  // 可选
            "error_type": "错误类型",       // 可选
            "limit": 50
        }
    """
    try:
        data = request.json or {}
        sample_ids = data.get('sample_ids')
        error_type = data.get('error_type')
        limit = data.get('limit', 50)
        
        if limit < 10 or limit > 200:
            limit = 50
        
        result = OptimizationService.generate_suggestions(
            sample_ids=sample_ids,
            error_type=error_type,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'data': result,
            'message': f'生成 {len(result["suggestions"])} 条建议'
        })
        
    except Exception as e:
        print(f'[Optimization] 生成建议失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@optimization_bp.route('/api/optimization/suggestions/<suggestion_id>/status', methods=['PUT'])
def update_suggestion_status(suggestion_id):
    """
    更新建议状态
    
    Request Body:
        {
            "status": "in_progress"
        }
    """
    try:
        if not suggestion_id:
            return jsonify({'success': False, 'error': '建议ID不能为空'}), 400
        
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        status = data.get('status')
        if not status:
            return jsonify({'success': False, 'error': '状态不能为空'}), 400
        
        success = OptimizationService.update_status(suggestion_id, status)
        
        if success:
            return jsonify({'success': True, 'message': '状态已更新'})
        else:
            return jsonify({'success': False, 'error': '更新失败'}), 400
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f'[Optimization] 更新状态失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@optimization_bp.route('/api/optimization/suggestions/<suggestion_id>', methods=['DELETE'])
def delete_suggestion(suggestion_id):
    """删除建议"""
    try:
        if not suggestion_id:
            return jsonify({'success': False, 'error': '建议ID不能为空'}), 400
        
        success = OptimizationService.delete_suggestion(suggestion_id)
        
        if success:
            return jsonify({'success': True, 'message': '建议已删除'})
        else:
            return jsonify({'success': False, 'error': '删除失败'}), 400
        
    except Exception as e:
        print(f'[Optimization] 删除建议失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@optimization_bp.route('/api/optimization/export', methods=['POST'])
def export_suggestions():
    """
    导出优化建议报告
    
    Request Body:
        {
            "suggestion_ids": ["id1", "id2"],  // 可选
            "format": "md"  // md 或 txt
        }
    """
    try:
        data = request.json or {}
        suggestion_ids = data.get('suggestion_ids')
        format = data.get('format', 'md')
        
        if format not in ['md', 'txt']:
            return jsonify({'success': False, 'error': '不支持的导出格式'}), 400
        
        filepath = OptimizationService.export_suggestions(suggestion_ids, format)
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filepath.split('/')[-1].split('\\')[-1]
        )
        
    except Exception as e:
        print(f'[Optimization] 导出建议失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
