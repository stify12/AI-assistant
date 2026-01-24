"""
图片对比路由模块 (US-23)

提供作业图片与识别结果的对比查看 API。
"""
import os
import json
from flask import Blueprint, request, jsonify
from services.storage_service import StorageService
from services.database_service import DatabaseService

image_compare_bp = Blueprint('image_compare', __name__)


@image_compare_bp.route('/api/image-compare/<homework_id>', methods=['GET'])
def get_homework_image(homework_id):
    """
    获取作业图片信息 (US-23.1)
    
    Args:
        homework_id: 作业ID
        
    Returns:
        {homework_id, pic_url, homework_result, base_answer, hw_user, errors}
    """
    try:
        if not homework_id:
            return jsonify({'success': False, 'error': '作业ID不能为空'}), 400
        
        # 从数据库查询作业信息
        sql = """
            SELECT homework_id, pic_path, homework_result, 
                   base_answer, base_user, hw_user
            FROM homework_data 
            WHERE homework_id = %s
        """
        row = DatabaseService.execute_one(sql, (homework_id,))
        
        if not row:
            return jsonify({'success': False, 'error': '作业不存在'}), 404
        
        # 构建图片URL
        pic_path = row.get('pic_path', '')
        pic_url = pic_path if pic_path.startswith('http') else f'/static/uploads/{pic_path}'
        
        return jsonify({
            'success': True,
            'data': {
                'homework_id': row['homework_id'],
                'pic_url': pic_url,
                'pic_path': pic_path,
                'homework_result': row.get('homework_result', ''),
                'base_answer': row.get('base_answer', ''),
                'base_user': row.get('base_user', ''),
                'hw_user': row.get('hw_user', '')
            }
        })
        
    except Exception as e:
        print(f'[ImageCompare] 获取作业图片失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@image_compare_bp.route('/api/image-compare/task/<task_id>', methods=['GET'])
def get_task_images(task_id):
    """
    获取任务下所有作业图片列表 (US-23.5)
    
    用于切换上一题/下一题。
    
    Args:
        task_id: 批量任务ID
        
    Query Parameters:
        page: 页码
        page_size: 每页数量
        error_only: 是否只显示错误项
    """
    try:
        if not task_id:
            return jsonify({'success': False, 'error': '任务ID不能为空'}), 400
        
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        error_only = request.args.get('error_only', 'false').lower() == 'true'
        
        # 加载任务数据
        task_file = os.path.join(StorageService.BATCH_TASKS_DIR, f'{task_id}.json')
        if not os.path.exists(task_file):
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        with open(task_file, 'r', encoding='utf-8') as f:
            task_data = json.load(f)
        
        homework_items = task_data.get('homework_items', [])
        
        # 筛选错误项
        if error_only:
            homework_items = [
                item for item in homework_items
                if item.get('evaluation', {}).get('errors')
            ]
        
        total = len(homework_items)
        
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        page_items = homework_items[start:end]
        
        # 格式化结果
        images = []
        for idx, item in enumerate(page_items):
            pic_path = item.get('pic_path', '')
            pic_url = pic_path if pic_path.startswith('http') else f'/static/uploads/{pic_path}'
            
            evaluation = item.get('evaluation') or {}
            errors = evaluation.get('errors') or []
            
            images.append({
                'index': start + idx,
                'homework_id': item.get('homework_id', ''),
                'pic_url': pic_url,
                'pic_path': pic_path,
                'homework_result': item.get('homework_result', ''),
                'book_name': item.get('book_name', ''),
                'page_num': item.get('page_num'),
                'base_answer': errors[0].get('base_answer', '') if errors else '',
                'base_user': errors[0].get('base_user', '') if errors else '',
                'hw_user': errors[0].get('hw_user', '') if errors else '',
                'error_type': errors[0].get('error_type', '') if errors else '',
                'error_count': len(errors),
                'errors': errors
            })
        
        return jsonify({
            'success': True,
            'data': {
                'items': images,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
        })
        
    except Exception as e:
        print(f'[ImageCompare] 获取任务图片列表失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@image_compare_bp.route('/api/image-compare/sample/<sample_id>', methods=['GET'])
def get_sample_image(sample_id):
    """
    获取错误样本的图片信息
    
    Args:
        sample_id: 错误样本ID
    """
    try:
        if not sample_id:
            return jsonify({'success': False, 'error': '样本ID不能为空'}), 400
        
        from services.error_sample_service import ErrorSampleService
        
        sample = ErrorSampleService.get_sample_detail(sample_id)
        if not sample:
            return jsonify({'success': False, 'error': '样本不存在'}), 404
        
        pic_path = sample.get('pic_path', '')
        pic_url = pic_path if pic_path.startswith('http') else f'/static/uploads/{pic_path}'
        
        return jsonify({
            'success': True,
            'data': {
                'sample_id': sample['sample_id'],
                'homework_id': sample['homework_id'],
                'pic_url': pic_url,
                'pic_path': pic_path,
                'book_name': sample.get('book_name', ''),
                'page_num': sample.get('page_num'),
                'question_index': sample['question_index'],
                'error_type': sample['error_type'],
                'base_answer': sample.get('base_answer', ''),
                'base_user': sample.get('base_user', ''),
                'hw_user': sample.get('hw_user', '')
            }
        })
        
    except Exception as e:
        print(f'[ImageCompare] 获取样本图片失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
