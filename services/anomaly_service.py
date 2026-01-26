"""
异常检测服务模块 (US-26)

提供准确率异常自动检测和告警功能。
支持基于统计学方法的异常检测，自动记录异常日志。

任务级题目异常检测：
- 全员错误：某题所有学生的AI批改结果都与基准不一致（可能是数据集标注错误）
- 高异常：有人批改对的情况下，错误类型是"识别正确-判断错误"（AI识别准确但判断错误）
- 低异常：有人批改对的情况下，其他错误类型（识别错误等）

一致性计算：
- 一致性 = 正常题数 / (总题数 - 全员错误题数) × 100%
- 排除全员错误的影响，因为可能是数据集标注问题
"""
import uuid
import json
import os
import statistics
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from collections import defaultdict

from .database_service import AppDatabaseService
from .storage_service import StorageService


class AnomalyService:
    """异常检测服务类"""
    
    # 默认阈值：2个标准差
    DEFAULT_THRESHOLD_SIGMA = 2.0
    
    # 配置缓存
    _config = {
        'threshold_sigma': 2.0,
        'min_samples': 5,  # 最少需要5个历史样本才能检测
    }
    
    # 高异常错误类型（识别正确但判断错误）
    HIGH_ANOMALY_ERROR_TYPES = ['识别正确-判断错误']
    
    # ========== 任务级题目异常检测 ==========
    
    @staticmethod
    def _collect_question_indices(data_value: list, result: set = None) -> set:
        """从 data_value 递归收集所有子题的题号（只收集叶子节点）"""
        if result is None:
            result = set()
        for item in data_value:
            children = item.get('children', [])
            if children:
                # 有子题，递归处理子题
                AnomalyService._collect_question_indices(children, result)
            else:
                # 叶子节点，收集题号
                idx = item.get('index')
                if idx:
                    result.add(str(idx))
        return result
    
    @staticmethod
    def detect_question_anomalies(task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        检测任务中的题目异常
        
        异常类型：
        1. 全员错误：同一页码的某题，所有包含该页的作业都判错
        2. 高异常：有人批改对的情况下，错误类型是"识别正确-判断错误"
        3. 低异常：有人批改对的情况下，其他错误类型
        4. 正常：所有人都做对的题目
        
        Args:
            task_data: 完整的任务数据
            
        Returns:
            {
                'summary': {...},
                'anomalies': [...]
            }
        """
        homework_items = task_data.get('homework_items', [])
        completed_items = [h for h in homework_items if h.get('status') == 'completed' and h.get('evaluation')]
        
        if not completed_items:
            return {
                'summary': {
                    'universal_errors': 0,
                    'high_anomaly': 0,
                    'low_anomaly': 0,
                    'normal': 0,
                    'total_questions': 0,
                    'anomaly_rate': 0
                },
                'anomalies': []
            }
        
        # 按页码统计作业数和收集所有题号
        page_homework_count = defaultdict(int)
        page_all_indices = defaultdict(set)  # 每个页码的所有题号
        
        for item in completed_items:
            page_num = item.get('page_num', '?')
            page_homework_count[page_num] += 1
            
            # 从 data_value 获取该页的所有题号
            data_value = item.get('data_value', '[]')
            if isinstance(data_value, str):
                try:
                    data_value = json.loads(data_value)
                except:
                    data_value = []
            
            if data_value:
                indices = AnomalyService._collect_question_indices(data_value)
                page_all_indices[page_num].update(indices)
        
        # 按题目聚合统计 (page_num + question_index)
        question_stats = defaultdict(lambda: {
            'total': 0,
            'correct': 0,
            'error': 0,
            'samples': [],
            'error_types': defaultdict(int),
            'error_samples': []
        })
        
        # 初始化所有题目的统计（从 data_value 获取）
        for page_num, indices in page_all_indices.items():
            for q_index in indices:
                q_key = f"{page_num}_{q_index}"
                question_stats[q_key]['page_num'] = page_num
                question_stats[q_key]['question_index'] = q_index
        
        # 遍历每个作业，统计正确和错误
        for item in completed_items:
            page_num = item.get('page_num', '?')
            evaluation = item.get('evaluation', {})
            student_id = item.get('student_id', item.get('homework_id', ''))
            student_name = item.get('student_name', '')
            
            # 获取该页的所有题号
            all_indices = page_all_indices.get(page_num, set())
            
            # 获取错误题目的 index 集合
            error_indices = set()
            error_info = {}  # index -> error details
            for q in evaluation.get('errors', []):
                q_index = str(q.get('index', '?'))
                error_indices.add(q_index)
                error_info[q_index] = q
            
            # 遍历该页的所有题目
            for q_index in all_indices:
                q_key = f"{page_num}_{q_index}"
                stats = question_stats[q_key]
                stats['total'] += 1
                
                if q_index in error_indices:
                    # 错误
                    stats['error'] += 1
                    q = error_info[q_index]
                    error_type = q.get('error_type', '未知错误')
                    stats['error_types'][error_type] += 1
                    
                    base_effect = q.get('base_effect', {})
                    ai_result = q.get('ai_result', {})
                    
                    error_sample = {
                        'student_id': student_id,
                        'student_name': student_name,
                        'result': 'error',
                        'hw_answer': ai_result.get('userAnswer', ''),
                        'base_answer': base_effect.get('answer', ''),
                        'base_user': base_effect.get('userAnswer', ''),
                        'error_type': error_type
                    }
                    stats['error_samples'].append(error_sample)
                    if len(stats['samples']) < 10:
                        stats['samples'].append(error_sample)
                else:
                    # 正确
                    stats['correct'] += 1
                    correct_sample = {
                        'student_id': student_id,
                        'student_name': student_name,
                        'result': 'correct'
                    }
                    if len(stats['samples']) < 10:
                        stats['samples'].append(correct_sample)
        
        # 分析异常
        anomalies = []
        universal_errors = 0
        high_anomaly = 0
        low_anomaly = 0
        normal = 0
        
        for q_key, stats in question_stats.items():
            if stats['total'] == 0:
                continue
            
            error_rate = stats['error'] / stats['total']
            page_num = stats.get('page_num', '?')
            q_index = stats.get('question_index', '?')
            
            # 获取该页码的作业总数
            page_total = page_homework_count.get(page_num, 0)
            
            anomaly = None
            
            # 1. 全员错误检测（新定义）
            # 条件：该题目所有学生的AI批改结果都与基准不一致（全部异常）
            # 即：没有任何一个学生该题是正常的
            is_universal_error = (
                error_rate == 1.0 and 
                stats['total'] >= 2 and 
                stats['correct'] == 0  # 没有任何正确的
            )
            
            if is_universal_error:
                # 统计错误类型分布
                error_type_summary = AnomalyService._format_error_types(stats['error_types'])
                anomaly = {
                    'type': 'universal_error',
                    'severity': 'critical',
                    'page_num': page_num,
                    'question_index': q_index,
                    'error_rate': error_rate,
                    'sample_count': stats['total'],
                    'correct_count': stats['correct'],
                    'error_count': stats['error'],
                    'error_types': dict(stats['error_types']),
                    'description': f'全部{stats["total"]}人判错',
                    'error_type_summary': error_type_summary,
                    'samples': stats['samples'][:5]
                }
                universal_errors += 1
            
            # 2. 有人对有人错的情况（不稳定）
            elif stats['correct'] > 0 and stats['error'] > 0 and stats['total'] >= 2:
                # 分析错误类型
                error_types = stats['error_types']
                high_anomaly_count = sum(error_types.get(t, 0) for t in AnomalyService.HIGH_ANOMALY_ERROR_TYPES)
                low_anomaly_count = stats['error'] - high_anomaly_count
                
                # 判断主要异常类型
                if high_anomaly_count > 0:
                    # 高异常：存在"识别正确-判断错误"
                    error_type_summary = AnomalyService._format_error_types(stats['error_types'])
                    anomaly = {
                        'type': 'high_anomaly',
                        'severity': 'high',
                        'page_num': page_num,
                        'question_index': q_index,
                        'error_rate': error_rate,
                        'sample_count': stats['total'],
                        'correct_count': stats['correct'],
                        'error_count': stats['error'],
                        'error_types': dict(stats['error_types']),
                        'description': f'{stats["correct"]}对/{stats["error"]}错，含识别正确-判断错误',
                        'error_type_summary': error_type_summary,
                        'samples': stats['samples'][:5]
                    }
                    high_anomaly += 1
                else:
                    # 低异常：其他错误类型
                    error_type_summary = AnomalyService._format_error_types(stats['error_types'])
                    anomaly = {
                        'type': 'low_anomaly',
                        'severity': 'medium',
                        'page_num': page_num,
                        'question_index': q_index,
                        'error_rate': error_rate,
                        'sample_count': stats['total'],
                        'correct_count': stats['correct'],
                        'error_count': stats['error'],
                        'error_types': dict(stats['error_types']),
                        'description': f'{stats["correct"]}对/{stats["error"]}错',
                        'error_type_summary': error_type_summary,
                        'samples': stats['samples'][:5]
                    }
                    low_anomaly += 1
            
            else:
                normal += 1
            
            if anomaly:
                anomalies.append(anomaly)
        
        # 按严重程度和错误率排序
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        anomalies.sort(key=lambda x: (severity_order.get(x['severity'], 99), -x['error_rate']))
        
        total_questions = len(question_stats)
        anomaly_count = universal_errors + high_anomaly + low_anomaly
        
        # 计算一致性（排除全员错误）
        effective_questions = total_questions - universal_errors  # 有效题数
        consistency_rate = round(normal / effective_questions, 4) if effective_questions > 0 else 0
        
        return {
            'summary': {
                'universal_errors': universal_errors,
                'high_anomaly': high_anomaly,
                'low_anomaly': low_anomaly,
                'normal': normal,
                'total_questions': total_questions,
                'anomaly_count': anomaly_count,
                'anomaly_rate': round(anomaly_count / total_questions, 4) if total_questions > 0 else 0,
                # 一致性相关
                'effective_questions': effective_questions,
                'consistency_rate': consistency_rate
            },
            'anomalies': anomalies
        }
    
    @staticmethod
    def _format_error_types(error_types: Dict[str, int]) -> str:
        """格式化错误类型统计为可读字符串"""
        if not error_types:
            return ''
        parts = [f'{t}({c})' for t, c in sorted(error_types.items(), key=lambda x: -x[1])]
        return '、'.join(parts[:3])  # 最多显示3种
    
    @staticmethod
    def _get_inconsistent_details(stats: Dict) -> Dict:
        """获取不稳定判断的详细信息（保留兼容）"""
        return {'description': '', 'inconsistent_answers': []}
    
    @staticmethod
    def detect_task_anomaly(task_id: str) -> Optional[Dict[str, Any]]:
        """
        检测任务准确率异常 (US-26.1)
        
        计算历史准确率的均值和标准差，
        判断当前任务准确率是否偏离均值超过阈值。
        
        Args:
            task_id: 批量任务ID
            
        Returns:
            dict: 异常信息，无异常返回 None
        """
        # 加载当前任务
        task_file = os.path.join(StorageService.BATCH_TASKS_DIR, f'{task_id}.json')
        if not os.path.exists(task_file):
            return None
        
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
        except:
            return None
        
        overall_report = task_data.get('overall_report') or {}
        current_accuracy = overall_report.get('overall_accuracy', 0)
        
        # 获取历史准确率
        history_accuracies = AnomalyService._get_history_accuracies(task_id)
        
        if len(history_accuracies) < AnomalyService._config['min_samples']:
            return None  # 样本不足，无法检测
        
        # 计算统计值
        mean_acc = statistics.mean(history_accuracies)
        std_acc = statistics.stdev(history_accuracies)
        
        if std_acc == 0:
            return None  # 标准差为0，无法检测
        
        # 计算偏差
        threshold = AnomalyService._config['threshold_sigma']
        deviation = abs(current_accuracy - mean_acc) / std_acc
        
        if deviation <= threshold:
            return None  # 在正常范围内

        # 检测到异常，记录日志
        anomaly_type = 'accuracy_drop' if current_accuracy < mean_acc else 'accuracy_spike'
        severity = 'high' if deviation > threshold * 1.5 else 'medium'
        
        anomaly = {
            'anomaly_id': str(uuid.uuid4())[:8],
            'anomaly_type': anomaly_type,
            'severity': severity,
            'task_id': task_id,
            'metric_name': 'accuracy',
            'expected_value': round(mean_acc, 4),
            'actual_value': round(current_accuracy, 4),
            'deviation': round(deviation, 4),
            'threshold': threshold,
            'message': f'准确率异常: 期望 {mean_acc:.2%}，实际 {current_accuracy:.2%}，偏离 {deviation:.1f}σ'
        }
        
        # 保存到数据库
        AnomalyService._save_anomaly(anomaly)
        
        return anomaly
    
    @staticmethod
    def _get_history_accuracies(exclude_task_id: str = None, days: int = 30) -> List[float]:
        """获取历史准确率列表"""
        accuracies = []
        batch_tasks_dir = StorageService.BATCH_TASKS_DIR
        
        if not os.path.exists(batch_tasks_dir):
            return accuracies
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for filename in os.listdir(batch_tasks_dir):
            if not filename.endswith('.json'):
                continue
            
            task_id = filename.replace('.json', '')
            if task_id == exclude_task_id:
                continue
            
            filepath = os.path.join(batch_tasks_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    task_data = json.load(f)
                
                # 检查时间
                created_at = task_data.get('created_at', '')
                if created_at:
                    try:
                        task_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if task_time.tzinfo:
                            task_time = task_time.replace(tzinfo=None)
                        if task_time < cutoff_date:
                            continue
                    except:
                        pass
                
                # 获取准确率
                overall_report = task_data.get('overall_report') or {}
                accuracy = overall_report.get('overall_accuracy')
                if accuracy is not None:
                    accuracies.append(accuracy)
            except:
                continue
        
        return accuracies
    
    @staticmethod
    def _save_anomaly(anomaly: Dict[str, Any]) -> None:
        """保存异常到数据库"""
        sql = """
            INSERT INTO anomaly_logs 
            (anomaly_id, anomaly_type, severity, task_id, metric_name,
             expected_value, actual_value, deviation, threshold, message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        AppDatabaseService.execute_insert(sql, (
            anomaly['anomaly_id'], anomaly['anomaly_type'], anomaly['severity'],
            anomaly.get('task_id'), anomaly.get('metric_name'),
            anomaly.get('expected_value'), anomaly.get('actual_value'),
            anomaly.get('deviation'), anomaly.get('threshold'),
            anomaly.get('message')
        ))

    
    @staticmethod
    def get_anomaly_logs(
        page: int = 1,
        page_size: int = 20,
        anomaly_type: str = None,
        severity: str = None,
        is_acknowledged: bool = None
    ) -> Dict[str, Any]:
        """
        获取异常日志列表 (US-26.5)
        
        Args:
            page: 页码
            page_size: 每页数量
            anomaly_type: 异常类型筛选
            severity: 严重程度筛选
            is_acknowledged: 是否已确认筛选
            
        Returns:
            dict: {items: list, total: int, page: int, page_size: int}
        """
        where_clauses = ['1=1']
        params = []
        
        if anomaly_type:
            where_clauses.append('anomaly_type = %s')
            params.append(anomaly_type)
        
        if severity:
            where_clauses.append('severity = %s')
            params.append(severity)
        
        if is_acknowledged is not None:
            where_clauses.append('is_acknowledged = %s')
            params.append(1 if is_acknowledged else 0)
        
        where_sql = ' AND '.join(where_clauses)
        
        # 查询总数
        count_sql = f'SELECT COUNT(*) as total FROM anomaly_logs WHERE {where_sql}'
        count_result = AppDatabaseService.execute_one(count_sql, tuple(params) if params else None)
        total = count_result['total'] if count_result else 0
        
        # 查询列表
        offset = (page - 1) * page_size
        list_sql = f"""
            SELECT anomaly_id, anomaly_type, severity, task_id, metric_name,
                   expected_value, actual_value, deviation, threshold, message,
                   is_acknowledged, acknowledged_by, acknowledged_at, created_at
            FROM anomaly_logs 
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        rows = AppDatabaseService.execute_query(list_sql, tuple(params))
        
        items = []
        for row in rows:
            items.append({
                'anomaly_id': row['anomaly_id'],
                'anomaly_type': row['anomaly_type'],
                'severity': row['severity'],
                'task_id': row.get('task_id'),
                'metric_name': row.get('metric_name'),
                'expected_value': float(row['expected_value']) if row.get('expected_value') else None,
                'actual_value': float(row['actual_value']) if row.get('actual_value') else None,
                'deviation': float(row['deviation']) if row.get('deviation') else None,
                'threshold': float(row['threshold']) if row.get('threshold') else None,
                'message': row.get('message', ''),
                'is_acknowledged': bool(row.get('is_acknowledged')),
                'acknowledged_by': row.get('acknowledged_by'),
                'acknowledged_at': row['acknowledged_at'].isoformat() if row.get('acknowledged_at') else None,
                'created_at': row['created_at'].isoformat() if row.get('created_at') else ''
            })
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        }
    
    @staticmethod
    def acknowledge_anomaly(anomaly_id: str, user_id: int = None) -> bool:
        """确认异常"""
        sql = """
            UPDATE anomaly_logs 
            SET is_acknowledged = 1, acknowledged_by = %s, acknowledged_at = NOW()
            WHERE anomaly_id = %s
        """
        result = AppDatabaseService.execute_update(sql, (user_id, anomaly_id))
        return result > 0
    
    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """获取异常统计"""
        # 未确认数量
        unack_sql = "SELECT COUNT(*) as count FROM anomaly_logs WHERE is_acknowledged = 0"
        unack_result = AppDatabaseService.execute_one(unack_sql)
        unacknowledged = unack_result['count'] if unack_result else 0
        
        # 今日异常数
        today_sql = """
            SELECT COUNT(*) as count FROM anomaly_logs 
            WHERE DATE(created_at) = CURDATE()
        """
        today_result = AppDatabaseService.execute_one(today_sql)
        today_count = today_result['count'] if today_result else 0
        
        # 按类型统计
        type_sql = """
            SELECT anomaly_type, COUNT(*) as count 
            FROM anomaly_logs 
            GROUP BY anomaly_type
        """
        type_rows = AppDatabaseService.execute_query(type_sql)
        by_type = {row['anomaly_type']: row['count'] for row in type_rows}
        
        # 按严重程度统计
        severity_sql = """
            SELECT severity, COUNT(*) as count 
            FROM anomaly_logs 
            GROUP BY severity
        """
        severity_rows = AppDatabaseService.execute_query(severity_sql)
        by_severity = {row['severity']: row['count'] for row in severity_rows}
        
        return {
            'unacknowledged': unacknowledged,
            'today_count': today_count,
            'by_type': by_type,
            'by_severity': by_severity
        }
    
    @staticmethod
    def set_threshold(threshold_sigma: float) -> None:
        """设置异常阈值 (US-26.3)"""
        if threshold_sigma < 1 or threshold_sigma > 5:
            raise ValueError('阈值必须在 1-5 之间')
        AnomalyService._config['threshold_sigma'] = threshold_sigma
