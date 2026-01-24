"""
异常检测服务模块 (US-26)

提供准确率异常自动检测和告警功能。
支持基于统计学方法的异常检测，自动记录异常日志。
"""
import uuid
import json
import os
import statistics
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .database_service import AppDatabaseService
from .storage_service import StorageService


class AnomalyService:
    """异常检测服务类"""
    
    # 默认阈值：2个标准差
    DEFAULT_THRESHOLD_SIGMA = 2.0
    
    # 配置缓存
    _config = {
        'threshold_sigma': 2.0,
        'min_samples': 5  # 最少需要5个历史样本才能检测
    }
    
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
