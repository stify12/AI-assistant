"""
批次对比分析服务 (US-18, US-33)

支持:
- 批次间准确率变化曲线
- 环比/同比对比
- 基线对比
"""
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .storage_service import StorageService


class BatchCompareService:
    """批次对比分析服务"""
    
    @staticmethod
    def get_batch_trend(
        subject_id: int = None,
        book_name: str = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取批次准确率趋势 (US-18.1)
        
        Returns:
            dict: {dates, accuracy_data, task_counts}
        """
        batch_dir = StorageService.BATCH_TASKS_DIR
        daily_stats = {}
        
        cutoff = datetime.now() - timedelta(days=days)
        
        if os.path.exists(batch_dir):
            for filename in os.listdir(batch_dir):
                if not filename.endswith('.json'):
                    continue
                filepath = os.path.join(batch_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        task = json.load(f)
                    
                    # 筛选条件
                    if subject_id is not None:
                        task_subject = task.get('subject_id')
                        if task_subject != subject_id:
                            continue
                    if book_name:
                        task_book = task.get('book_name') or task.get('dataset_name', '')
                        if book_name not in task_book:
                            continue
                    
                    # 获取日期
                    created = task.get('created_at') or task.get('start_time', '')
                    if not created:
                        continue
                    
                    try:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    except:
                        continue
                    
                    if dt < cutoff:
                        continue
                    
                    date_key = dt.strftime('%Y-%m-%d')
                    
                    if date_key not in daily_stats:
                        daily_stats[date_key] = {
                            'total_questions': 0,
                            'correct_count': 0,
                            'task_count': 0
                        }
                    
                    report = task.get('overall_report') or {}
                    daily_stats[date_key]['total_questions'] += report.get('total_questions', 0)
                    daily_stats[date_key]['correct_count'] += report.get('correct_count', 0)
                    daily_stats[date_key]['task_count'] += 1
                    
                except Exception:
                    continue
        
        # 排序并计算准确率
        dates = sorted(daily_stats.keys())
        accuracy_data = []
        task_counts = []
        
        for date in dates:
            stats = daily_stats[date]
            if stats['total_questions'] > 0:
                acc = stats['correct_count'] / stats['total_questions']
            else:
                acc = 0
            accuracy_data.append(round(acc * 100, 2))
            task_counts.append(stats['task_count'])
        
        return {
            'dates': dates,
            'accuracy_data': accuracy_data,
            'task_counts': task_counts
        }
    
    @staticmethod
    def compare_periods(
        period1_start: str,
        period1_end: str,
        period2_start: str,
        period2_end: str,
        subject_id: int = None
    ) -> Dict[str, Any]:
        """
        对比两个时间段 (US-33.1 环比/同比)
        
        Returns:
            dict: {period1, period2, change, change_percent}
        """
        def get_period_stats(start: str, end: str) -> Dict:
            batch_dir = StorageService.BATCH_TASKS_DIR
            total_q = 0
            correct = 0
            task_count = 0
            
            try:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
            except:
                return {'accuracy': 0, 'total_questions': 0, 'task_count': 0}
            
            if os.path.exists(batch_dir):
                for filename in os.listdir(batch_dir):
                    if not filename.endswith('.json'):
                        continue
                    filepath = os.path.join(batch_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            task = json.load(f)
                        
                        if subject_id is not None:
                            if task.get('subject_id') != subject_id:
                                continue
                        
                        created = task.get('created_at') or task.get('start_time', '')
                        if not created:
                            continue
                        
                        try:
                            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        except:
                            continue
                        
                        if not (start_dt <= dt <= end_dt):
                            continue
                        
                        report = task.get('overall_report') or {}
                        total_q += report.get('total_questions', 0)
                        correct += report.get('correct_count', 0)
                        task_count += 1
                    except:
                        continue
            
            return {
                'accuracy': correct / total_q if total_q > 0 else 0,
                'total_questions': total_q,
                'correct_count': correct,
                'task_count': task_count
            }
        
        p1 = get_period_stats(period1_start, period1_end)
        p2 = get_period_stats(period2_start, period2_end)
        
        change = p2['accuracy'] - p1['accuracy']
        change_percent = (change / p1['accuracy'] * 100) if p1['accuracy'] > 0 else 0
        
        return {
            'period1': {
                'start': period1_start,
                'end': period1_end,
                **p1
            },
            'period2': {
                'start': period2_start,
                'end': period2_end,
                **p2
            },
            'change': round(change * 100, 2),
            'change_percent': round(change_percent, 2)
        }

    
    @staticmethod
    def compare_with_baseline(
        task_id: str,
        baseline_task_id: str = None
    ) -> Dict[str, Any]:
        """
        与基线对比 (US-33.2)
        
        Args:
            task_id: 当前任务ID
            baseline_task_id: 基线任务ID，为空则使用最早的同类任务
            
        Returns:
            dict: {current, baseline, improvements, regressions}
        """
        batch_dir = StorageService.BATCH_TASKS_DIR
        
        # 加载当前任务
        current_path = os.path.join(batch_dir, f'{task_id}.json')
        if not os.path.exists(current_path):
            return {'error': '任务不存在'}
        
        with open(current_path, 'r', encoding='utf-8') as f:
            current_task = json.load(f)
        
        # 查找基线任务
        baseline_task = None
        if baseline_task_id:
            baseline_path = os.path.join(batch_dir, f'{baseline_task_id}.json')
            if os.path.exists(baseline_path):
                with open(baseline_path, 'r', encoding='utf-8') as f:
                    baseline_task = json.load(f)
        else:
            # 查找最早的同类任务作为基线
            book_name = current_task.get('book_name') or current_task.get('dataset_name', '')
            earliest_time = None
            
            for filename in os.listdir(batch_dir):
                if not filename.endswith('.json') or filename == f'{task_id}.json':
                    continue
                filepath = os.path.join(batch_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        task = json.load(f)
                    
                    task_book = task.get('book_name') or task.get('dataset_name', '')
                    if task_book != book_name:
                        continue
                    
                    created = task.get('created_at') or task.get('start_time', '')
                    if not created:
                        continue
                    
                    try:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    except:
                        continue
                    
                    if earliest_time is None or dt < earliest_time:
                        earliest_time = dt
                        baseline_task = task
                except:
                    continue
        
        if not baseline_task:
            return {'error': '未找到基线任务'}
        
        # 对比分析
        current_report = current_task.get('overall_report') or {}
        baseline_report = baseline_task.get('overall_report') or {}
        
        current_acc = current_report.get('correct_count', 0) / current_report.get('total_questions', 1)
        baseline_acc = baseline_report.get('correct_count', 0) / baseline_report.get('total_questions', 1)
        
        # 逐题对比
        improvements = []
        regressions = []
        
        current_results = {
            (r.get('page_number', i), q.get('question_number', j)): q
            for i, r in enumerate(current_task.get('results') or [])
            for j, q in enumerate(r.get('questions') or [])
        }
        
        baseline_results = {
            (r.get('page_number', i), q.get('question_number', j)): q
            for i, r in enumerate(baseline_task.get('results') or [])
            for j, q in enumerate(r.get('questions') or [])
        }
        
        for key, curr_q in current_results.items():
            base_q = baseline_results.get(key)
            if not base_q:
                continue
            
            curr_correct = curr_q.get('is_correct') or curr_q.get('match', False)
            base_correct = base_q.get('is_correct') or base_q.get('match', False)
            
            if curr_correct and not base_correct:
                improvements.append({
                    'page': key[0],
                    'question': key[1],
                    'baseline_answer': base_q.get('ai_answer', ''),
                    'current_answer': curr_q.get('ai_answer', '')
                })
            elif not curr_correct and base_correct:
                regressions.append({
                    'page': key[0],
                    'question': key[1],
                    'baseline_answer': base_q.get('ai_answer', ''),
                    'current_answer': curr_q.get('ai_answer', '')
                })
        
        return {
            'current': {
                'task_id': task_id,
                'accuracy': round(current_acc * 100, 2),
                'total_questions': current_report.get('total_questions', 0),
                'created_at': current_task.get('created_at', '')
            },
            'baseline': {
                'task_id': baseline_task.get('task_id', ''),
                'accuracy': round(baseline_acc * 100, 2),
                'total_questions': baseline_report.get('total_questions', 0),
                'created_at': baseline_task.get('created_at', '')
            },
            'change': round((current_acc - baseline_acc) * 100, 2),
            'improvements': improvements[:20],
            'regressions': regressions[:20],
            'improvement_count': len(improvements),
            'regression_count': len(regressions)
        }
    
    @staticmethod
    def get_model_comparison(days: int = 30) -> Dict[str, Any]:
        """
        模型间对比 (US-18.2)
        
        Returns:
            dict: {models: [{name, accuracy, task_count, trend}]}
        """
        batch_dir = StorageService.BATCH_TASKS_DIR
        model_stats = {}
        cutoff = datetime.now() - timedelta(days=days)
        
        if os.path.exists(batch_dir):
            for filename in os.listdir(batch_dir):
                if not filename.endswith('.json'):
                    continue
                filepath = os.path.join(batch_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        task = json.load(f)
                    
                    model = task.get('model') or task.get('vision_model', 'unknown')
                    
                    created = task.get('created_at') or task.get('start_time', '')
                    if created:
                        try:
                            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                            if dt < cutoff:
                                continue
                        except:
                            pass
                    
                    if model not in model_stats:
                        model_stats[model] = {
                            'name': model,
                            'total_questions': 0,
                            'correct_count': 0,
                            'task_count': 0,
                            'daily': {}
                        }
                    
                    stats = model_stats[model]
                    report = task.get('overall_report') or {}
                    stats['total_questions'] += report.get('total_questions', 0)
                    stats['correct_count'] += report.get('correct_count', 0)
                    stats['task_count'] += 1
                    
                    # 记录每日数据用于趋势
                    if created:
                        try:
                            date_key = datetime.fromisoformat(created.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                            if date_key not in stats['daily']:
                                stats['daily'][date_key] = {'q': 0, 'c': 0}
                            stats['daily'][date_key]['q'] += report.get('total_questions', 0)
                            stats['daily'][date_key]['c'] += report.get('correct_count', 0)
                        except:
                            pass
                except:
                    continue
        
        # 计算准确率和趋势
        models = []
        for model, stats in model_stats.items():
            accuracy = stats['correct_count'] / stats['total_questions'] if stats['total_questions'] > 0 else 0
            
            # 计算趋势（最近7天 vs 之前）
            dates = sorted(stats['daily'].keys())
            if len(dates) >= 7:
                recent = dates[-7:]
                earlier = dates[:-7] if len(dates) > 7 else []
                
                recent_q = sum(stats['daily'][d]['q'] for d in recent)
                recent_c = sum(stats['daily'][d]['c'] for d in recent)
                recent_acc = recent_c / recent_q if recent_q > 0 else 0
                
                if earlier:
                    earlier_q = sum(stats['daily'][d]['q'] for d in earlier)
                    earlier_c = sum(stats['daily'][d]['c'] for d in earlier)
                    earlier_acc = earlier_c / earlier_q if earlier_q > 0 else 0
                    trend = recent_acc - earlier_acc
                else:
                    trend = 0
            else:
                trend = 0
            
            models.append({
                'name': model,
                'accuracy': round(accuracy * 100, 2),
                'task_count': stats['task_count'],
                'total_questions': stats['total_questions'],
                'trend': round(trend * 100, 2)
            })
        
        models.sort(key=lambda x: x['accuracy'], reverse=True)
        
        return {'models': models}
