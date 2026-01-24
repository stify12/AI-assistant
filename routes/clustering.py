"""
错误聚类路由模块 (US-27)

提供错误聚类分析 API。
"""
from flask import Blueprint, request, jsonify
from services.clustering_service import ClusteringService

clustering_bp = Blueprint('clustering', __name__)


@clustering_bp.route('/api/clustering/clusters', methods=['GET'])
def get_clusters():
    """
    获取聚类列表
    
    Query Parameters:
        error_type: 错误类型筛选
    """
    try:
        error_type = request.args.get('error_type')
        
        clusters = ClusteringService.get_clusters(error_type)
        
        return jsonify({'success': True, 'data': clusters})
        
    except Exception as e:
        print(f'[Clustering] 获取聚类列表失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@clustering_bp.route('/api/clustering/clusters/<cluster_id>/samples', methods=['GET'])
def get_cluster_samples(cluster_id):
    """获取聚类下的样本列表"""
    try:
        if not cluster_id:
            return jsonify({'success': False, 'error': '聚类ID不能为空'}), 400
        
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        result = ClusteringService.get_cluster_samples(cluster_id, page, page_size)
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        print(f'[Clustering] 获取聚类样本失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@clustering_bp.route('/api/clustering/analyze', methods=['POST'])
def analyze_clusters():
    """
    执行聚类分析
    
    Request Body:
        {
            "error_type": "错误类型（可选）",
            "limit": 100
        }
    """
    try:
        data = request.json or {}
        error_type = data.get('error_type')
        limit = data.get('limit', 100)
        
        if limit < 10 or limit > 500:
            limit = 100
        
        result = ClusteringService.cluster_errors(error_type, limit)
        
        return jsonify({
            'success': True,
            'data': result,
            'message': f'聚类完成: 生成 {len(result["clusters"])} 个聚类'
        })
        
    except Exception as e:
        print(f'[Clustering] 聚类分析失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@clustering_bp.route('/api/clustering/clusters/<cluster_id>/label', methods=['PUT'])
def update_cluster_label(cluster_id):
    """
    更新聚类标签
    
    Request Body:
        {
            "label": "新标签"
        }
    """
    try:
        if not cluster_id:
            return jsonify({'success': False, 'error': '聚类ID不能为空'}), 400
        
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        label = data.get('label')
        if not label:
            return jsonify({'success': False, 'error': '标签不能为空'}), 400
        
        success = ClusteringService.update_cluster_label(cluster_id, label)
        
        if success:
            return jsonify({'success': True, 'message': '标签已更新'})
        else:
            return jsonify({'success': False, 'error': '更新失败'}), 400
        
    except Exception as e:
        print(f'[Clustering] 更新标签失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@clustering_bp.route('/api/clustering/merge', methods=['POST'])
def merge_clusters():
    """
    合并聚类
    
    Request Body:
        {
            "cluster_ids": ["id1", "id2"],
            "new_label": "合并后的标签"
        }
    """
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        cluster_ids = data.get('cluster_ids', [])
        new_label = data.get('new_label')
        
        if len(cluster_ids) < 2:
            return jsonify({'success': False, 'error': '至少需要2个聚类'}), 400
        
        if not new_label:
            return jsonify({'success': False, 'error': '新标签不能为空'}), 400
        
        new_cluster_id = ClusteringService.merge_clusters(cluster_ids, new_label)
        
        return jsonify({
            'success': True,
            'data': {'cluster_id': new_cluster_id},
            'message': '聚类已合并'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f'[Clustering] 合并聚类失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@clustering_bp.route('/api/clustering/clusters/<cluster_id>', methods=['DELETE'])
def delete_cluster(cluster_id):
    """删除聚类"""
    try:
        if not cluster_id:
            return jsonify({'success': False, 'error': '聚类ID不能为空'}), 400
        
        success = ClusteringService.delete_cluster(cluster_id)
        
        if success:
            return jsonify({'success': True, 'message': '聚类已删除'})
        else:
            return jsonify({'success': False, 'error': '删除失败'}), 400
        
    except Exception as e:
        print(f'[Clustering] 删除聚类失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
