"""
基准合集管理路由模块
提供基准合集的 CRUD 操作和批量评估集成功能
"""
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify

from services.database_service import AppDatabaseService
from services.storage_service import StorageService

collection_manage_bp = Blueprint('collection_manage', __name__)


# ========== 合集 CRUD API ==========

@collection_manage_bp.route('/api/batch/collections', methods=['GET'])
def get_collections():
    """
    获取合集列表
    
    Returns:
        {
            "success": true,
            "data": [
                {
                    "collection_id": "col_abc123",
                    "name": "七年级英语合集",
                    "description": "...",
                    "dataset_count": 5,
                    "created_at": "2026-01-23T10:00:00"
                }
            ]
        }
    """
    try:
        collections = AppDatabaseService.get_collections()
        
        # 格式化返回数据
        result = []
        for col in collections:
            result.append({
                'collection_id': col['collection_id'],
                'name': col['name'],
                'description': col.get('description', ''),
                'dataset_count': col.get('dataset_count', 0),
                'created_at': col['created_at'].isoformat() if col.get('created_at') else None,
                'updated_at': col['updated_at'].isoformat() if col.get('updated_at') else None
            })
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        print(f"[GetCollections] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collection_manage_bp.route('/api/batch/collections', methods=['POST'])
def create_collection():
    """
    创建合集
    
    Request body:
        {
            "name": "七年级英语合集",
            "description": "包含七年级英语上册所有页码的基准数据",
            "dataset_ids": ["ds_001", "ds_002"]  // 可选，初始数据集
        }
    
    Returns:
        {
            "success": true,
            "collection_id": "col_abc123"
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': '合集名称不能为空'}), 400
        
        description = data.get('description', '').strip()
        dataset_ids = data.get('dataset_ids', [])
        
        # 生成合集ID
        collection_id = f"col_{str(uuid.uuid4())[:8]}"
        
        # 创建合集
        AppDatabaseService.create_collection(collection_id, name, description)
        
        # 如果有初始数据集，添加到合集
        if dataset_ids:
            AppDatabaseService.batch_add_datasets_to_collection(collection_id, dataset_ids)
        
        print(f"[CreateCollection] Created: {collection_id}, name={name}, datasets={len(dataset_ids)}")
        
        return jsonify({
            'success': True,
            'collection_id': collection_id
        })
    except Exception as e:
        print(f"[CreateCollection] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@collection_manage_bp.route('/api/batch/collections/<collection_id>', methods=['GET'])
def get_collection_detail(collection_id):
    """
    获取合集详情（含数据集列表）
    
    Returns:
        {
            "success": true,
            "data": {
                "collection_id": "col_abc123",
                "name": "七年级英语合集",
                "description": "...",
                "datasets": [
                    {
                        "dataset_id": "ds_001",
                        "name": "学生A基准",
                        "book_name": "七年级英语上册",
                        "pages": [30, 31, 32],
                        "question_count": 50
                    }
                ]
            }
        }
    """
    try:
        collection = AppDatabaseService.get_collection_with_datasets(collection_id)
        if not collection:
            return jsonify({'success': False, 'error': '合集不存在'}), 404
        
        # 格式化返回数据
        result = {
            'collection_id': collection['collection_id'],
            'name': collection['name'],
            'description': collection.get('description', ''),
            'created_at': collection['created_at'].isoformat() if collection.get('created_at') else None,
            'updated_at': collection['updated_at'].isoformat() if collection.get('updated_at') else None,
            'datasets': []
        }
        
        for ds in collection.get('datasets', []):
            result['datasets'].append({
                'dataset_id': ds['dataset_id'],
                'name': ds.get('name', ''),
                'book_id': ds.get('book_id', ''),
                'book_name': ds.get('book_name', ''),
                'pages': ds.get('pages', []),
                'question_count': ds.get('question_count', 0),
                'added_at': ds['added_at'].isoformat() if ds.get('added_at') else None
            })
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        print(f"[GetCollectionDetail] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collection_manage_bp.route('/api/batch/collections/<collection_id>', methods=['PUT'])
def update_collection(collection_id):
    """
    更新合集（名称、描述）
    
    Request body:
        {
            "name": "新名称",
            "description": "新描述"
        }
    """
    try:
        collection = AppDatabaseService.get_collection(collection_id)
        if not collection:
            return jsonify({'success': False, 'error': '合集不存在'}), 404
        
        data = request.get_json() or {}
        update_fields = {}
        
        if 'name' in data:
            name = data['name'].strip() if data['name'] else ''
            if not name:
                return jsonify({'success': False, 'error': '合集名称不能为空'}), 400
            update_fields['name'] = name
        
        if 'description' in data:
            update_fields['description'] = data['description'].strip() if data['description'] else ''
        
        if update_fields:
            AppDatabaseService.update_collection(collection_id, **update_fields)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"[UpdateCollection] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collection_manage_bp.route('/api/batch/collections/<collection_id>', methods=['DELETE'])
def delete_collection(collection_id):
    """删除合集"""
    try:
        collection = AppDatabaseService.get_collection(collection_id)
        if not collection:
            return jsonify({'success': False, 'error': '合集不存在'}), 404
        
        AppDatabaseService.delete_collection(collection_id)
        print(f"[DeleteCollection] Deleted: {collection_id}")
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"[DeleteCollection] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== 合集数据集管理 API ==========

@collection_manage_bp.route('/api/batch/collections/<collection_id>/datasets', methods=['POST'])
def add_datasets_to_collection(collection_id):
    """
    添加数据集到合集
    
    Request body:
        {
            "dataset_ids": ["ds_001", "ds_002"]
        }
    """
    try:
        collection = AppDatabaseService.get_collection(collection_id)
        if not collection:
            return jsonify({'success': False, 'error': '合集不存在'}), 404
        
        data = request.get_json() or {}
        dataset_ids = data.get('dataset_ids', [])
        
        if not dataset_ids:
            return jsonify({'success': False, 'error': '缺少数据集ID列表'}), 400
        
        if not isinstance(dataset_ids, list):
            dataset_ids = [dataset_ids]
        
        # 验证数据集存在
        valid_ids = []
        for ds_id in dataset_ids:
            ds = StorageService.load_dataset(ds_id)
            if ds:
                valid_ids.append(ds_id)
        
        if not valid_ids:
            return jsonify({'success': False, 'error': '没有有效的数据集'}), 400
        
        # 添加到合集
        count = AppDatabaseService.batch_add_datasets_to_collection(collection_id, valid_ids)
        
        print(f"[AddDatasetsToCollection] Added {count} datasets to {collection_id}")
        
        return jsonify({
            'success': True,
            'added_count': count
        })
    except Exception as e:
        print(f"[AddDatasetsToCollection] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@collection_manage_bp.route('/api/batch/collections/<collection_id>/datasets/<dataset_id>', methods=['DELETE'])
def remove_dataset_from_collection(collection_id, dataset_id):
    """从合集移除数据集"""
    try:
        collection = AppDatabaseService.get_collection(collection_id)
        if not collection:
            return jsonify({'success': False, 'error': '合集不存在'}), 404
        
        AppDatabaseService.remove_dataset_from_collection(collection_id, dataset_id)
        print(f"[RemoveDatasetFromCollection] Removed {dataset_id} from {collection_id}")
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"[RemoveDatasetFromCollection] Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== 批量评估集成 API ==========

@collection_manage_bp.route('/api/batch/collections/<collection_id>/match-preview', methods=['GET'])
def preview_collection_match(collection_id):
    """
    预览合集对任务的匹配情况
    
    Query params:
        task_id: 任务ID（必填）
    
    Returns:
        {
            "success": true,
            "data": {
                "total_homework": 10,
                "matched_count": 8,
                "unmatched_count": 2,
                "match_details": [
                    {
                        "homework_id": "hw1",
                        "book_id": "book123",
                        "page_num": 30,
                        "matched_dataset_id": "ds_001",
                        "matched_dataset_name": "学生A基准"
                    }
                ],
                "unmatched_items": [
                    {
                        "homework_id": "hw2",
                        "book_id": "book456",
                        "page_num": 50,
                        "reason": "合集中没有匹配的数据集"
                    }
                ]
            }
        }
    """
    try:
        task_id = request.args.get('task_id')
        if not task_id:
            return jsonify({'success': False, 'error': '缺少任务ID'}), 400
        
        # 加载合集
        collection = AppDatabaseService.get_collection_with_datasets(collection_id)
        if not collection:
            return jsonify({'success': False, 'error': '合集不存在'}), 404
        
        # 加载任务
        task_data = StorageService.load_batch_task(task_id)
        if not task_data:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        # 构建匹配索引: {(book_id, page_num): [dataset_info, ...]}
        match_index = {}
        for ds in collection.get('datasets', []):
            book_id = ds.get('book_id')
            pages = ds.get('pages', [])
            for page in pages:
                key = (str(book_id), int(page))
                if key not in match_index:
                    match_index[key] = []
                match_index[key].append({
                    'dataset_id': ds['dataset_id'],
                    'name': ds.get('name', ''),
                    'added_at': ds.get('added_at')
                })
        
        # 对每个 key 按 added_at 倒序排列（最新添加的优先）
        for key in match_index:
            match_index[key].sort(
                key=lambda x: x.get('added_at') or '', 
                reverse=True
            )
        
        # 遍历作业，预览匹配结果
        homework_items = task_data.get('homework_items', [])
        match_details = []
        unmatched_items = []
        
        for item in homework_items:
            book_id = str(item.get('book_id', ''))
            page_num = item.get('page_num')
            homework_id = item.get('homework_id')
            
            if page_num is None:
                unmatched_items.append({
                    'homework_id': homework_id,
                    'book_id': book_id,
                    'page_num': None,
                    'reason': '作业缺少页码信息'
                })
                continue
            
            key = (book_id, int(page_num))
            
            if key in match_index and match_index[key]:
                best_match = match_index[key][0]
                match_details.append({
                    'homework_id': homework_id,
                    'book_id': book_id,
                    'page_num': page_num,
                    'matched_dataset_id': best_match['dataset_id'],
                    'matched_dataset_name': best_match['name']
                })
            else:
                unmatched_items.append({
                    'homework_id': homework_id,
                    'book_id': book_id,
                    'page_num': page_num,
                    'reason': '合集中没有匹配的数据集'
                })
        
        return jsonify({
            'success': True,
            'data': {
                'total_homework': len(homework_items),
                'matched_count': len(match_details),
                'unmatched_count': len(unmatched_items),
                'match_details': match_details,
                'unmatched_items': unmatched_items
            }
        })
    except Exception as e:
        print(f"[PreviewCollectionMatch] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@collection_manage_bp.route('/api/batch/tasks/<task_id>/select-collection', methods=['POST'])
def select_collection_for_task(task_id):
    """
    为任务选择合集，自动匹配作业与数据集
    
    Request body:
        {
            "collection_id": "col_abc123"
        }
    
    Returns:
        {
            "success": true,
            "matched_count": 8,
            "unmatched_count": 2
        }
    """
    try:
        data = request.get_json() or {}
        collection_id = data.get('collection_id')
        
        if not collection_id:
            return jsonify({'success': False, 'error': '缺少合集ID'}), 400
        
        # 加载合集
        collection = AppDatabaseService.get_collection_with_datasets(collection_id)
        if not collection:
            return jsonify({'success': False, 'error': '合集不存在'}), 404
        
        # 加载任务
        task_data = StorageService.load_batch_task(task_id)
        if not task_data:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        # 构建匹配索引
        match_index = {}
        for ds in collection.get('datasets', []):
            book_id = ds.get('book_id')
            pages = ds.get('pages', [])
            for page in pages:
                key = (str(book_id), int(page))
                if key not in match_index:
                    match_index[key] = []
                match_index[key].append({
                    'dataset_id': ds['dataset_id'],
                    'name': ds.get('name', ''),
                    'added_at': ds.get('added_at')
                })
        
        # 对每个 key 按 added_at 倒序排列
        for key in match_index:
            match_index[key].sort(
                key=lambda x: x.get('added_at') or '', 
                reverse=True
            )
        
        # 遍历作业，执行匹配
        homework_items = task_data.get('homework_items', [])
        matched_count = 0
        unmatched_count = 0
        
        for item in homework_items:
            book_id = str(item.get('book_id', ''))
            page_num = item.get('page_num')
            
            if page_num is None:
                unmatched_count += 1
                continue
            
            key = (book_id, int(page_num))
            
            if key in match_index and match_index[key]:
                best_match = match_index[key][0]
                
                # 更新作业的数据集匹配信息
                item['matched_dataset'] = best_match['dataset_id']
                item['matched_dataset_name'] = best_match['name']
                item['matched_collection'] = collection_id
                item['matched_collection_name'] = collection.get('name', '')
                
                # 清除已有评估结果
                item['accuracy'] = None
                item['precision'] = None
                item['recall'] = None
                item['f1'] = None
                item['correct_count'] = None
                item['wrong_count'] = None
                item['total_count'] = None
                item['error_details'] = None
                item['evaluation'] = None
                
                # 重置状态为 pending
                item['status'] = 'pending'
                
                matched_count += 1
            else:
                unmatched_count += 1
        
        # 保存任务数据
        StorageService.save_batch_task(task_id, task_data)
        
        print(f"[SelectCollectionForTask] Task {task_id} matched {matched_count} items using collection {collection_id}")
        
        return jsonify({
            'success': True,
            'matched_count': matched_count,
            'unmatched_count': unmatched_count
        })
    except Exception as e:
        print(f"[SelectCollectionForTask] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
