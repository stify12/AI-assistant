"""
多维度数据下钻服务 (US-21)

支持下钻路径：总体 → 学科 → 书本 → 页码 → 题目
"""
import json
import os
from typing import Optional, List, Dict, Any

from .database_service import AppDatabaseService
from .storage_service import StorageService


# 下钻层级定义
DRILLDOWN_LEVELS = ['overall', 'subject', 'book', 'page', 'question']

# 学科名称映射
SUBJECT_MAP = {
    0: '英语', 1: '语文', 2: '数学', 3: '物理',
    4: '化学', 5: '生物', 6: '地理'
}


class DrilldownService:
    """数据下钻服务类"""
    
    @staticmethod
    def get_drilldown_data(
        level: str,
        parent_id: str = None,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        获取下钻数据 (US-21.1, US-21.2)
        
        Args:
            level: 当前层级 overall|subject|book|page|question
            parent_id: 父级ID
            filters: 筛选条件
            
        Returns:
            dict: {level, parent_id, breadcrumb, data, summary}
        """
        filters = filters or {}
        
        if level == 'overall':
            return DrilldownService._get_overall_data(filters)
        elif level == 'subject':
            return DrilldownService._get_subject_data(parent_id, filters)
        elif level == 'book':
            return DrilldownService._get_book_data(parent_id, filters)
        elif level == 'page':
            return DrilldownService._get_page_data(parent_id, filters)
        elif level == 'question':
            return DrilldownService._get_question_data(parent_id, filters)
        else:
            raise ValueError(f'无效的层级: {level}')
    
    @staticmethod
    def _get_overall_data(filters: Dict) -> Dict[str, Any]:
        """获取总体数据 - 按学科分组"""
        # 从批量任务文件聚合数据
        batch_dir = StorageService.BATCH_TASKS_DIR
        subject_stats = {}
        
        if os.path.exists(batch_dir):
            for filename in os.listdir(batch_dir):
                if not filename.endswith('.json'):
                    continue
                
                filepath = os.path.join(batch_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        task = json.load(f)
                    
                    subject_id = task.get('subject_id')
                    if subject_id is None:
                        subject_id = DrilldownService._infer_subject(task)
                    
                    if subject_id not in subject_stats:
                        subject_stats[subject_id] = {
                            'id': str(subject_id),
                            'name': SUBJECT_MAP.get(subject_id, f'学科{subject_id}'),
                            'task_count': 0,
                            'question_count': 0,
                            'correct_count': 0,
                            'error_count': 0
                        }
                    
                    stats = subject_stats[subject_id]
                    stats['task_count'] += 1
                    
                    report = task.get('overall_report') or {}
                    stats['question_count'] += report.get('total_questions', 0)
                    stats['correct_count'] += report.get('correct_count', 0)
                    stats['error_count'] += report.get('error_count', 0)
                    
                except Exception:
                    continue
        
        # 计算准确率
        data = []
        total_questions = 0
        total_correct = 0
        
        for subject_id, stats in subject_stats.items():
            if stats['question_count'] > 0:
                stats['accuracy'] = stats['correct_count'] / stats['question_count']
            else:
                stats['accuracy'] = 0
            data.append(stats)
            total_questions += stats['question_count']
            total_correct += stats['correct_count']
        
        # 按题目数排序
        data.sort(key=lambda x: x['question_count'], reverse=True)
        
        return {
            'level': 'overall',
            'parent_id': None,
            'breadcrumb': [{'level': 'overall', 'id': None, 'name': '总览'}],
            'data': data,
            'summary': {
                'total_accuracy': total_correct / total_questions if total_questions > 0 else 0,
                'total_questions': total_questions,
                'total_items': len(data)
            }
        }
    
    @staticmethod
    def _get_subject_data(subject_id: str, filters: Dict) -> Dict[str, Any]:
        """获取学科数据 - 按书本分组"""
        batch_dir = StorageService.BATCH_TASKS_DIR
        book_stats = {}
        subject_id_int = int(subject_id) if subject_id else 0
        subject_name = SUBJECT_MAP.get(subject_id_int, f'学科{subject_id}')
        
        if os.path.exists(batch_dir):
            for filename in os.listdir(batch_dir):
                if not filename.endswith('.json'):
                    continue
                filepath = os.path.join(batch_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        task = json.load(f)
                    
                    task_subject = task.get('subject_id')
                    if task_subject is None:
                        task_subject = DrilldownService._infer_subject(task)
                    if str(task_subject) != str(subject_id):
                        continue
                    
                    book_name = task.get('book_name') or task.get('dataset_name', '未知书本')
                    book_id = book_name
                    
                    if book_id not in book_stats:
                        book_stats[book_id] = {
                            'id': book_id,
                            'name': book_name,
                            'task_count': 0,
                            'question_count': 0,
                            'correct_count': 0,
                            'error_count': 0,
                            'task_ids': []
                        }
                    
                    stats = book_stats[book_id]
                    stats['task_count'] += 1
                    stats['task_ids'].append(filename.replace('.json', ''))
                    
                    report = task.get('overall_report') or {}
                    stats['question_count'] += report.get('total_questions', 0)
                    stats['correct_count'] += report.get('correct_count', 0)
                    stats['error_count'] += report.get('error_count', 0)
                except Exception:
                    continue
        
        data = []
        total_questions = 0
        total_correct = 0
        
        for book_id, stats in book_stats.items():
            if stats['question_count'] > 0:
                stats['accuracy'] = stats['correct_count'] / stats['question_count']
            else:
                stats['accuracy'] = 0
            data.append(stats)
            total_questions += stats['question_count']
            total_correct += stats['correct_count']
        
        data.sort(key=lambda x: x['question_count'], reverse=True)
        
        return {
            'level': 'subject',
            'parent_id': subject_id,
            'breadcrumb': [
                {'level': 'overall', 'id': None, 'name': '总览'},
                {'level': 'subject', 'id': subject_id, 'name': subject_name}
            ],
            'data': data,
            'summary': {
                'total_accuracy': total_correct / total_questions if total_questions > 0 else 0,
                'total_questions': total_questions,
                'total_items': len(data)
            }
        }
    
    @staticmethod
    def _get_book_data(book_id: str, filters: Dict) -> Dict[str, Any]:
        """获取书本数据 - 按页码分组"""
        batch_dir = StorageService.BATCH_TASKS_DIR
        page_stats = {}
        book_name = book_id
        subject_id = None
        subject_name = ''
        
        if os.path.exists(batch_dir):
            for filename in os.listdir(batch_dir):
                if not filename.endswith('.json'):
                    continue
                filepath = os.path.join(batch_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        task = json.load(f)
                    
                    task_book = task.get('book_name') or task.get('dataset_name', '')
                    if task_book != book_id:
                        continue
                    
                    if subject_id is None:
                        subject_id = task.get('subject_id')
                        if subject_id is None:
                            subject_id = DrilldownService._infer_subject(task)
                        subject_name = SUBJECT_MAP.get(subject_id, f'学科{subject_id}')
                    
                    results = task.get('results') or []
                    for result in results:
                        page_num = result.get('page_number') or result.get('image_index', 0)
                        page_id = f"{book_id}_{page_num}"
                        
                        if page_id not in page_stats:
                            page_stats[page_id] = {
                                'id': page_id,
                                'name': f'第{page_num}页',
                                'page_number': page_num,
                                'question_count': 0,
                                'correct_count': 0,
                                'error_count': 0
                            }
                        
                        stats = page_stats[page_id]
                        questions = result.get('questions') or []
                        for q in questions:
                            stats['question_count'] += 1
                            is_correct = q.get('is_correct') or q.get('match', False)
                            if is_correct:
                                stats['correct_count'] += 1
                            else:
                                stats['error_count'] += 1
                except Exception:
                    continue
        
        data = []
        total_questions = 0
        total_correct = 0
        
        for page_id, stats in page_stats.items():
            if stats['question_count'] > 0:
                stats['accuracy'] = stats['correct_count'] / stats['question_count']
            else:
                stats['accuracy'] = 0
            data.append(stats)
            total_questions += stats['question_count']
            total_correct += stats['correct_count']
        
        data.sort(key=lambda x: x['page_number'])
        
        return {
            'level': 'book',
            'parent_id': book_id,
            'breadcrumb': [
                {'level': 'overall', 'id': None, 'name': '总览'},
                {'level': 'subject', 'id': str(subject_id), 'name': subject_name},
                {'level': 'book', 'id': book_id, 'name': book_name}
            ],
            'data': data,
            'summary': {
                'total_accuracy': total_correct / total_questions if total_questions > 0 else 0,
                'total_questions': total_questions,
                'total_items': len(data)
            }
        }
    
    @staticmethod
    def _get_page_data(page_id: str, filters: Dict) -> Dict[str, Any]:
        """获取页码数据 - 显示题目列表"""
        parts = page_id.rsplit('_', 1)
        book_id = parts[0] if len(parts) > 1 else page_id
        page_num = int(parts[1]) if len(parts) > 1 else 0
        
        batch_dir = StorageService.BATCH_TASKS_DIR
        questions = []
        subject_id = None
        subject_name = ''
        
        if os.path.exists(batch_dir):
            for filename in os.listdir(batch_dir):
                if not filename.endswith('.json'):
                    continue
                filepath = os.path.join(batch_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        task = json.load(f)
                    
                    task_book = task.get('book_name') or task.get('dataset_name', '')
                    if task_book != book_id:
                        continue
                    
                    if subject_id is None:
                        subject_id = task.get('subject_id')
                        if subject_id is None:
                            subject_id = DrilldownService._infer_subject(task)
                        subject_name = SUBJECT_MAP.get(subject_id, f'学科{subject_id}')
                    
                    results = task.get('results') or []
                    for result in results:
                        result_page = result.get('page_number') or result.get('image_index', 0)
                        if result_page != page_num:
                            continue
                        
                        qs = result.get('questions') or []
                        for idx, q in enumerate(qs):
                            is_correct = q.get('is_correct') or q.get('match', False)
                            questions.append({
                                'id': f"{page_id}_{idx}",
                                'name': q.get('question_number') or f'题目{idx+1}',
                                'question_number': q.get('question_number', str(idx+1)),
                                'ai_answer': q.get('ai_answer', ''),
                                'expected_answer': q.get('expected_answer') or q.get('baseline_answer', ''),
                                'is_correct': is_correct,
                                'error_type': q.get('error_type', '') if not is_correct else ''
                            })
                except Exception:
                    continue
        
        correct_count = sum(1 for q in questions if q['is_correct'])
        
        return {
            'level': 'page',
            'parent_id': page_id,
            'breadcrumb': [
                {'level': 'overall', 'id': None, 'name': '总览'},
                {'level': 'subject', 'id': str(subject_id), 'name': subject_name},
                {'level': 'book', 'id': book_id, 'name': book_id},
                {'level': 'page', 'id': page_id, 'name': f'第{page_num}页'}
            ],
            'data': questions,
            'summary': {
                'total_accuracy': correct_count / len(questions) if questions else 0,
                'total_questions': len(questions),
                'correct_count': correct_count,
                'error_count': len(questions) - correct_count
            }
        }
    
    @staticmethod
    def _get_question_data(question_id: str, filters: Dict) -> Dict[str, Any]:
        """获取题目详情"""
        parts = question_id.rsplit('_', 2)
        if len(parts) < 3:
            return {'level': 'question', 'parent_id': question_id, 'data': None}
        
        book_id = parts[0]
        page_num = int(parts[1])
        q_idx = int(parts[2])
        
        batch_dir = StorageService.BATCH_TASKS_DIR
        question_detail = None
        subject_id = None
        subject_name = ''
        
        if os.path.exists(batch_dir):
            for filename in os.listdir(batch_dir):
                if not filename.endswith('.json'):
                    continue
                filepath = os.path.join(batch_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        task = json.load(f)
                    
                    task_book = task.get('book_name') or task.get('dataset_name', '')
                    if task_book != book_id:
                        continue
                    
                    if subject_id is None:
                        subject_id = task.get('subject_id')
                        if subject_id is None:
                            subject_id = DrilldownService._infer_subject(task)
                        subject_name = SUBJECT_MAP.get(subject_id, f'学科{subject_id}')
                    
                    results = task.get('results') or []
                    for result in results:
                        result_page = result.get('page_number') or result.get('image_index', 0)
                        if result_page != page_num:
                            continue
                        
                        qs = result.get('questions') or []
                        if q_idx < len(qs):
                            q = qs[q_idx]
                            is_correct = q.get('is_correct') or q.get('match', False)
                            question_detail = {
                                'id': question_id,
                                'question_number': q.get('question_number', str(q_idx+1)),
                                'ai_answer': q.get('ai_answer', ''),
                                'expected_answer': q.get('expected_answer') or q.get('baseline_answer', ''),
                                'is_correct': is_correct,
                                'error_type': q.get('error_type', ''),
                                'image_url': result.get('image_url', ''),
                                'raw_response': q.get('raw_response', '')
                            }
                            break
                    if question_detail:
                        break
                except Exception:
                    continue
        
        return {
            'level': 'question',
            'parent_id': question_id,
            'breadcrumb': [
                {'level': 'overall', 'id': None, 'name': '总览'},
                {'level': 'subject', 'id': str(subject_id), 'name': subject_name},
                {'level': 'book', 'id': book_id, 'name': book_id},
                {'level': 'page', 'id': f'{book_id}_{page_num}', 'name': f'第{page_num}页'},
                {'level': 'question', 'id': question_id, 'name': f'题目{q_idx+1}'}
            ],
            'data': question_detail,
            'summary': {}
        }
    
    @staticmethod
    def _infer_subject(task: Dict) -> int:
        """从任务数据推断学科"""
        name = (task.get('book_name') or task.get('dataset_name') or '').lower()
        if '英语' in name or 'english' in name:
            return 0
        elif '语文' in name or 'chinese' in name:
            return 1
        elif '数学' in name or 'math' in name:
            return 2
        elif '物理' in name or 'physics' in name:
            return 3
        elif '化学' in name or 'chemistry' in name:
            return 4
        elif '生物' in name or 'biology' in name:
            return 5
        elif '地理' in name or 'geography' in name:
            return 6
        return 0