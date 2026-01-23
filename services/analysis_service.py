"""
分析服务模块
提供测试计划看板的分析功能，包括：
- 问题热点图 (US-11)
- AI覆盖率分析 (US-12)
- A/B测试对比 (US-17)
- 错误关联分析 (US-20)
- 多维度下钻 (US-21)
- 异常检测 (US-26)
- 错误聚类 (US-27)
- AI优化建议 (US-28)

遵循 NFR-34 代码质量标准
"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .storage_service import StorageService
from .dashboard_service import DashboardService, SUBJECT_MAP


class AnalysisService:
    """
    分析服务类
    
    提供测试计划看板的各种分析功能，包括热点图、覆盖率分析、
    异常检测、错误聚类等。
    """
    
    # 热点等级阈值
    HEAT_LEVEL_CRITICAL = 10  # >= 10 次错误为 critical
    HEAT_LEVEL_HIGH = 5       # 5-9 次错误为 high
    HEAT_LEVEL_MEDIUM = 2     # 2-4 次错误为 medium
    # < 2 次错误为 low
    
    # ========== 问题热点图 (US-11) ==========
    
    @staticmethod
    def get_heatmap(subject_id: Optional[int] = None, days: int = 7) -> Dict[str, Any]:
        """
        获取问题热点图数据 (US-11)
        
        按 book -> page -> question 三级聚合错误数据，
        计算每个题目的错误次数和热点等级。
        
        Args:
            subject_id: 学科ID筛选，None 表示全部学科
            days: 时间范围，7|30|0(全部)
            
        Returns:
            dict: 热点图数据，结构如下：
                {
                    "heatmap": [
                        {
                            "book_id": "xxx",
                            "book_name": "物理八上",
                            "error_count": 50,
                            "pages": [
                                {
                                    "page_num": 76,
                                    "error_count": 20,
                                    "questions": [
                                        {
                                            "index": "1",
                                            "error_count": 8,
                                            "heat_level": "critical",
                                            "error_types": {"识别错误-判断错误": 5, ...}
                                        }
                                    ]
                                }
                            ]
                        }
                    ],
                    "total_errors": 150,
                    "time_range": "7天"
                }
        """
        # 缓存键
        cache_key = f'heatmap_{subject_id}_{days}'
        cached = DashboardService.get_cached(cache_key)
        if cached is not None:
            return cached
        
        result = {
            'heatmap': [],
            'total_errors': 0,
            'time_range': AnalysisService._get_time_range_text(days)
        }
        
        try:
            # 加载所有批量任务
            all_tasks = DashboardService._load_all_batch_tasks()
            
            # 按时间范围筛选任务
            if days > 0:
                filtered_tasks = AnalysisService._filter_tasks_by_days(all_tasks, days)
            else:
                filtered_tasks = all_tasks
            
            # 获取数据集信息用于确定学科
            datasets = StorageService.get_all_datasets_summary()
            dataset_subject_map = {ds['dataset_id']: ds.get('subject_id') for ds in datasets}
            
            # 聚合错误数据: book_id -> page_num -> question_index -> errors
            error_aggregation = {}
            
            for task in filtered_tasks:
                for hw_item in task.get('homework_items', []):
                    # 确定学科ID
                    item_subject_id = None
                    matched_dataset = hw_item.get('matched_dataset')
                    if matched_dataset and matched_dataset in dataset_subject_map:
                        item_subject_id = dataset_subject_map[matched_dataset]
                    
                    # 如果没有匹配数据集，尝试从书名推断
                    if item_subject_id is None:
                        book_name = hw_item.get('book_name', '')
                        item_subject_id = DashboardService._infer_subject_from_book_name(book_name)
                    
                    # 学科筛选
                    if subject_id is not None and item_subject_id != subject_id:
                        continue
                    
                    # 获取书本和页码信息
                    book_id = hw_item.get('book_id', 'unknown')
                    book_name = hw_item.get('book_name', '未知书本')
                    page_num = hw_item.get('page_num', 0)
                    
                    # 获取错误列表
                    evaluation = hw_item.get('evaluation') or {}
                    errors = evaluation.get('errors') or []
                    
                    # 聚合错误
                    for error in errors:
                        question_index = error.get('index', 'unknown')
                        error_type = error.get('error_type', '其他')
                        
                        # 初始化聚合结构
                        if book_id not in error_aggregation:
                            error_aggregation[book_id] = {
                                'book_name': book_name,
                                'subject_id': item_subject_id,
                                'pages': {}
                            }
                        
                        if page_num not in error_aggregation[book_id]['pages']:
                            error_aggregation[book_id]['pages'][page_num] = {}
                        
                        if question_index not in error_aggregation[book_id]['pages'][page_num]:
                            error_aggregation[book_id]['pages'][page_num][question_index] = {
                                'error_count': 0,
                                'error_types': {}
                            }
                        
                        # 累加错误计数
                        error_aggregation[book_id]['pages'][page_num][question_index]['error_count'] += 1
                        
                        # 累加错误类型计数
                        error_types = error_aggregation[book_id]['pages'][page_num][question_index]['error_types']
                        error_types[error_type] = error_types.get(error_type, 0) + 1
            
            # 转换为输出格式
            total_errors = 0
            heatmap_data = []
            
            for book_id, book_data in error_aggregation.items():
                book_error_count = 0
                pages_list = []
                
                # 按页码排序
                sorted_pages = sorted(book_data['pages'].items(), key=lambda x: x[0])
                
                for page_num, questions in sorted_pages:
                    page_error_count = 0
                    questions_list = []
                    
                    # 按题号排序
                    sorted_questions = sorted(questions.items(), key=lambda x: AnalysisService._sort_question_index(x[0]))
                    
                    for question_index, error_data in sorted_questions:
                        error_count = error_data['error_count']
                        heat_level = AnalysisService._calculate_heat_level(error_count)
                        
                        questions_list.append({
                            'index': question_index,
                            'error_count': error_count,
                            'heat_level': heat_level,
                            'error_types': error_data['error_types']
                        })
                        
                        page_error_count += error_count
                    
                    pages_list.append({
                        'page_num': page_num,
                        'error_count': page_error_count,
                        'questions': questions_list
                    })
                    
                    book_error_count += page_error_count
                
                heatmap_data.append({
                    'book_id': book_id,
                    'book_name': book_data['book_name'],
                    'subject_id': book_data['subject_id'],
                    'subject_name': SUBJECT_MAP.get(book_data['subject_id'], '未知'),
                    'error_count': book_error_count,
                    'pages': pages_list
                })
                
                total_errors += book_error_count
            
            # 按错误数量降序排列
            heatmap_data.sort(key=lambda x: x['error_count'], reverse=True)
            
            result['heatmap'] = heatmap_data
            result['total_errors'] = total_errors
            
            # 缓存结果 (1小时)
            DashboardService.set_cached(cache_key, result, ttl=3600)
            
        except Exception as e:
            print(f"[AnalysisService] 获取热点图数据失败: {e}")
        
        return result
    
    @staticmethod
    def _filter_tasks_by_days(tasks: List[Dict], days: int) -> List[Dict]:
        """
        按天数筛选任务
        
        Args:
            tasks: 任务列表
            days: 天数，0 表示全部
            
        Returns:
            list: 筛选后的任务列表
        """
        if days <= 0:
            return tasks
        
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered = []
        
        for task in tasks:
            created_at = task.get('created_at', '')
            if created_at:
                try:
                    task_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if task_time.tzinfo:
                        task_time = task_time.replace(tzinfo=None)
                    if task_time >= cutoff_date:
                        filtered.append(task)
                except:
                    continue
        
        return filtered
    
    @staticmethod
    def _calculate_heat_level(error_count: int) -> str:
        """
        计算热点等级 (US-11.2)
        
        根据错误次数计算热点等级：
        - critical: >= 10 次
        - high: 5-9 次
        - medium: 2-4 次
        - low: 1 次
        
        Args:
            error_count: 错误次数
            
        Returns:
            str: 热点等级 critical|high|medium|low
        """
        if error_count >= AnalysisService.HEAT_LEVEL_CRITICAL:
            return 'critical'
        elif error_count >= AnalysisService.HEAT_LEVEL_HIGH:
            return 'high'
        elif error_count >= AnalysisService.HEAT_LEVEL_MEDIUM:
            return 'medium'
        else:
            return 'low'
    
    @staticmethod
    def _sort_question_index(index: str) -> tuple:
        """
        题号排序辅助函数
        
        支持数字和字母混合的题号排序，如 "1", "2", "1.1", "1.2", "a", "b"
        
        Args:
            index: 题号字符串
            
        Returns:
            tuple: 排序用的元组
        """
        try:
            # 尝试按数字排序
            if '.' in index:
                parts = index.split('.')
                return tuple(int(p) if p.isdigit() else ord(p) for p in parts)
            elif index.isdigit():
                return (int(index),)
            else:
                return (ord(index[0]) if index else 0,)
        except:
            return (0,)
    
    @staticmethod
    def _get_time_range_text(days: int) -> str:
        """
        获取时间范围文本
        
        Args:
            days: 天数
            
        Returns:
            str: 时间范围文本
        """
        if days == 7:
            return '最近7天'
        elif days == 30:
            return '最近30天'
        elif days <= 0:
            return '全部'
        else:
            return f'最近{days}天'
    
    @staticmethod
    def get_question_error_details(
        book_id: str, 
        page_num: int, 
        question_index: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取题目错误详情 (US-11.3)
        
        点击热点时显示具体错误列表。
        
        Args:
            book_id: 书本ID
            page_num: 页码
            question_index: 题号
            days: 时间范围
            
        Returns:
            dict: 错误详情列表
        """
        result = {
            'errors': [],
            'total': 0
        }
        
        try:
            # 加载所有批量任务
            all_tasks = DashboardService._load_all_batch_tasks()
            
            # 按时间范围筛选
            if days > 0:
                filtered_tasks = AnalysisService._filter_tasks_by_days(all_tasks, days)
            else:
                filtered_tasks = all_tasks
            
            errors_list = []
            
            for task in filtered_tasks:
                task_id = task.get('task_id', '')
                task_name = task.get('name', '')
                
                for hw_item in task.get('homework_items', []):
                    # 匹配书本和页码
                    if hw_item.get('book_id') != book_id:
                        continue
                    if hw_item.get('page_num') != page_num:
                        continue
                    
                    # 获取错误列表
                    evaluation = hw_item.get('evaluation') or {}
                    errors = evaluation.get('errors') or []
                    
                    for error in errors:
                        # 匹配题号
                        if error.get('index') != question_index:
                            continue
                        
                        errors_list.append({
                            'task_id': task_id,
                            'task_name': task_name,
                            'homework_id': hw_item.get('homework_id', ''),
                            'student_name': hw_item.get('student_name', ''),
                            'error_type': error.get('error_type', ''),
                            'base_answer': error.get('base_answer', ''),
                            'base_user': error.get('base_user', ''),
                            'hw_user': error.get('hw_user', ''),
                            'created_at': task.get('created_at', '')
                        })
            
            # 按时间倒序排列
            errors_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            result['errors'] = errors_list
            result['total'] = len(errors_list)
            
        except Exception as e:
            print(f"[AnalysisService] 获取题目错误详情失败: {e}")
        
        return result
