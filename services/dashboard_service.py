"""
看板服务模块
提供测试计划看板的核心业务逻辑，包括：
- 概览统计数据聚合
- 批量任务列表管理
- 数据集概览统计
- 学科评估概览
- 测试计划 CRUD 操作
- 内存缓存管理

遵循 NFR-34 代码质量标准
"""
import os
import json
import uuid
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from .database_service import AppDatabaseService
from .storage_service import StorageService


# 学科ID映射
SUBJECT_MAP = {
    0: '英语',
    1: '语文',
    2: '数学',
    3: '物理',
    4: '化学',
    5: '生物',
    6: '地理'
}


class DashboardService:
    """
    看板核心服务类
    
    提供测试计划看板的所有业务逻辑，包括统计数据聚合、
    测试计划管理、缓存管理等功能。
    
    Attributes:
        _cache: 内存缓存字典，存储缓存数据和过期时间
        _cache_ttl: 默认缓存过期时间（秒），默认5分钟
    """
    
    # 内存缓存 (5分钟TTL)
    _cache: Dict[str, Dict[str, Any]] = {}
    _cache_ttl: int = 300  # 5分钟
    
    # ========== 缓存管理方法 (US-29) ==========
    
    @staticmethod
    def get_cached(key: str) -> Optional[Any]:
        """
        获取缓存数据 (US-29.4)
        
        如果缓存存在且未过期，返回缓存数据；
        否则返回 None，触发懒加载重新计算。
        
        Args:
            key: 缓存键名
            
        Returns:
            缓存的数据，如果不存在或已过期则返回 None
        """
        if key in DashboardService._cache:
            cache_entry = DashboardService._cache[key]
            # 检查是否过期
            if time.time() < cache_entry.get('expires_at', 0):
                return cache_entry.get('data')
            else:
                # 缓存已过期，删除
                del DashboardService._cache[key]
        return None
    
    @staticmethod
    def set_cached(key: str, value: Any, ttl: int = None) -> None:
        """
        设置缓存数据 (US-29.1)
        
        将数据存储到内存缓存中，并设置过期时间。
        
        Args:
            key: 缓存键名
            value: 要缓存的数据
            ttl: 缓存过期时间（秒），默认使用 _cache_ttl (300秒)
        """
        if ttl is None:
            ttl = DashboardService._cache_ttl
        
        DashboardService._cache[key] = {
            'data': value,
            'expires_at': time.time() + ttl,
            'cached_at': datetime.now().isoformat()
        }
    
    @staticmethod
    def clear_cache(key: str = None) -> None:
        """
        清除缓存 (US-29.3)
        
        清除指定键的缓存，或清除所有缓存。
        
        Args:
            key: 要清除的缓存键名，如果为 None 则清除所有缓存
        """
        if key is None:
            DashboardService._cache.clear()
        elif key in DashboardService._cache:
            del DashboardService._cache[key]
    
    @staticmethod
    def get_cache_status() -> Dict[str, Any]:
        """
        获取缓存状态 (US-29.5)
        
        返回当前缓存的状态信息，包括缓存键、缓存时间、是否过期等。
        
        Returns:
            dict: 缓存状态信息
        """
        status = {
            'total_keys': len(DashboardService._cache),
            'keys': []
        }
        current_time = time.time()
        for key, entry in DashboardService._cache.items():
            status['keys'].append({
                'key': key,
                'cached_at': entry.get('cached_at'),
                'expires_at': datetime.fromtimestamp(entry.get('expires_at', 0)).isoformat(),
                'is_expired': current_time >= entry.get('expires_at', 0)
            })
        return status
    
    # ========== 批量任务数据加载 ==========
    
    @staticmethod
    def _load_all_batch_tasks() -> List[Dict[str, Any]]:
        """
        加载所有批量任务数据
        
        从 batch_tasks/ 目录扫描所有 JSON 文件并加载。
        使用缓存避免重复读取文件。
        
        Returns:
            list: 所有批量任务数据列表，按创建时间倒序排列
        """
        cache_key = 'all_batch_tasks'
        cached = DashboardService.get_cached(cache_key)
        if cached is not None:
            return cached
        
        tasks = []
        batch_tasks_dir = StorageService.BATCH_TASKS_DIR
        
        try:
            # 确保目录存在
            StorageService.ensure_dir(batch_tasks_dir)
            
            # 扫描所有 JSON 文件
            for filename in os.listdir(batch_tasks_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(batch_tasks_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            task_data = json.load(f)
                            tasks.append(task_data)
                    except Exception as e:
                        print(f"[Dashboard] 加载任务文件失败 {filename}: {e}")
                        continue
            
            # 按创建时间倒序排列
            tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 缓存结果
            DashboardService.set_cached(cache_key, tasks)
            
        except Exception as e:
            print(f"[Dashboard] 扫描批量任务目录失败: {e}")
        
        return tasks
    
    @staticmethod
    def _filter_tasks_by_time_range(tasks: List[Dict], time_range: str) -> List[Dict]:
        """
        按时间范围筛选任务
        
        Args:
            tasks: 任务列表
            time_range: 时间范围 today|week|month
            
        Returns:
            list: 筛选后的任务列表
        """
        now = datetime.now()
        
        if time_range == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'week':
            # 本周一开始
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'month':
            # 本月1号开始
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return tasks
        
        filtered = []
        for task in tasks:
            created_at = task.get('created_at', '')
            if created_at:
                try:
                    task_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    # 移除时区信息进行比较
                    if task_time.tzinfo:
                        task_time = task_time.replace(tzinfo=None)
                    if task_time >= start_date:
                        filtered.append(task)
                except:
                    continue
        
        return filtered
    
    # ========== 概览统计 (US-2) ==========
    
    @staticmethod
    def get_overview(time_range: str = 'today') -> Dict[str, Any]:
        """
        获取概览统计数据 (US-2)
        
        聚合数据集、批量任务、题目数、准确率等统计信息。
        
        Args:
            time_range: 时间范围 today|week|month，用于任务数统计
            
        Returns:
            dict: 包含以下字段的统计数据
                - datasets: 数据集统计 {total, by_subject}
                - tasks: 任务数统计 {today, week, month}
                - questions: 题目统计 {tested, total}
                - accuracy: 准确率统计 {current, previous, trend}
                - last_sync: 最后同步时间
        """
        cache_key = f'overview_{time_range}'
        cached = DashboardService.get_cached(cache_key)
        if cached is not None:
            return cached
        
        result = {
            'datasets': {'total': 0, 'by_subject': {}},
            'tasks': {'today': 0, 'week': 0, 'month': 0},
            'questions': {'tested': 0, 'total': 0},
            'accuracy': {'current': 0, 'previous': 0, 'trend': 'stable'},
            'last_sync': datetime.now().isoformat()
        }
        
        try:
            # 1. 数据集统计
            datasets = StorageService.get_all_datasets_summary()
            result['datasets']['total'] = len(datasets)
            
            # 按学科分组统计
            by_subject = {}
            total_questions_in_datasets = 0
            for ds in datasets:
                subject_id = ds.get('subject_id')
                if subject_id is not None:
                    subject_key = str(subject_id)
                    by_subject[subject_key] = by_subject.get(subject_key, 0) + 1
                total_questions_in_datasets += ds.get('question_count', 0)
            result['datasets']['by_subject'] = by_subject
            result['questions']['total'] = total_questions_in_datasets
            
            # 2. 批量任务统计
            all_tasks = DashboardService._load_all_batch_tasks()
            
            # 统计各时间范围的任务数
            result['tasks']['today'] = len(DashboardService._filter_tasks_by_time_range(all_tasks, 'today'))
            result['tasks']['week'] = len(DashboardService._filter_tasks_by_time_range(all_tasks, 'week'))
            result['tasks']['month'] = len(DashboardService._filter_tasks_by_time_range(all_tasks, 'month'))
            
            # 3. 题目数和准确率统计 - 从每个作业项的 evaluation 直接统计
            # 只统计已完成评估的作业，确保数据真实有效
            total_questions_tested = 0
            total_correct = 0
            completed_homework_count = 0
            
            for task in all_tasks:
                for hw_item in task.get('homework_items', []):
                    # 只统计已完成评估的作业
                    if hw_item.get('status') != 'completed':
                        continue
                    
                    evaluation = hw_item.get('evaluation') or {}
                    questions = evaluation.get('total_questions', 0)
                    correct = evaluation.get('correct_count', 0)
                    
                    if questions > 0:
                        total_questions_tested += questions
                        total_correct += correct
                        completed_homework_count += 1
            
            result['questions']['tested'] = total_questions_tested
            result['questions']['homework_count'] = completed_homework_count
            
            # 计算当前准确率
            if total_questions_tested > 0:
                result['accuracy']['current'] = round(total_correct / total_questions_tested, 4)
            
            # 计算上周准确率用于趋势对比 (7-14天前的数据)
            now = datetime.now()
            last_week_start = now - timedelta(days=14)
            last_week_end = now - timedelta(days=7)
            
            prev_questions = 0
            prev_correct = 0
            for task in all_tasks:
                task_time_str = task.get('created_at', '')
                if not DashboardService._is_in_date_range(task_time_str, last_week_start, last_week_end):
                    continue
                    
                for hw_item in task.get('homework_items', []):
                    if hw_item.get('status') != 'completed':
                        continue
                    evaluation = hw_item.get('evaluation') or {}
                    prev_questions += evaluation.get('total_questions', 0)
                    prev_correct += evaluation.get('correct_count', 0)
            
            if prev_questions > 0:
                result['accuracy']['previous'] = round(prev_correct / prev_questions, 4)
            
            # 计算趋势
            current_acc = result['accuracy']['current']
            prev_acc = result['accuracy']['previous']
            if current_acc > prev_acc + 0.01:
                result['accuracy']['trend'] = 'up'
            elif current_acc < prev_acc - 0.01:
                result['accuracy']['trend'] = 'down'
            else:
                result['accuracy']['trend'] = 'stable'
            
            # 添加数据来源说明
            result['accuracy']['source'] = '批量评估任务'
            result['accuracy']['correct_count'] = total_correct
            
            # 缓存结果
            DashboardService.set_cached(cache_key, result)
            
        except Exception as e:
            print(f"[Dashboard] 获取概览统计失败: {e}")
        
        return result
    
    @staticmethod
    def _is_in_date_range(date_str: str, start: datetime, end: datetime) -> bool:
        """检查日期是否在指定范围内"""
        if not date_str:
            return False
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if dt.tzinfo:
                dt = dt.replace(tzinfo=None)
            return start <= dt <= end
        except:
            return False

    
    # ========== 批量任务列表 (US-3) ==========
    
    @staticmethod
    def get_tasks(page: int = 1, page_size: int = 20, status: str = 'all') -> Dict[str, Any]:
        """
        获取批量任务列表 (US-3)
        
        从 batch_tasks/ 目录加载任务数据，支持分页和状态筛选。
        
        Args:
            page: 页码，从1开始
            page_size: 每页数量，默认20
            status: 状态筛选 all|pending|processing|completed|failed
            
        Returns:
            dict: 包含以下字段
                - tasks: 任务列表，每个任务包含 task_id, name, status, accuracy, 
                         total_questions, created_at
                - pagination: 分页信息 {page, page_size, total, total_pages}
        """
        result = {
            'tasks': [],
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': 0,
                'total_pages': 0
            }
        }
        
        try:
            # 加载所有任务
            all_tasks = DashboardService._load_all_batch_tasks()
            
            # 状态筛选
            if status and status != 'all':
                all_tasks = [t for t in all_tasks if t.get('status') == status]
            
            # 计算分页
            total = len(all_tasks)
            total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
            
            result['pagination']['total'] = total
            result['pagination']['total_pages'] = total_pages
            
            # 分页切片
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_tasks = all_tasks[start_idx:end_idx]
            
            # 格式化任务数据
            for task in page_tasks:
                # 处理 overall_report 可能为 None 的情况
                overall_report = task.get('overall_report') or {}
                
                # 格式化创建时间为 MM-DD HH:mm 格式
                created_at = task.get('created_at', '')
                formatted_time = ''
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%m-%d %H:%M')
                    except:
                        formatted_time = created_at[:16] if len(created_at) >= 16 else created_at
                
                result['tasks'].append({
                    'task_id': task.get('task_id', ''),
                    'name': task.get('name', ''),
                    'status': task.get('status', 'pending'),
                    'accuracy': overall_report.get('overall_accuracy', 0),
                    'total_questions': overall_report.get('total_questions', 0),
                    'total_homework': overall_report.get('total_homework', 0),
                    'correct_questions': overall_report.get('correct_questions', 0),
                    'created_at': task.get('created_at', ''),
                    'formatted_time': formatted_time
                })
            
        except Exception as e:
            print(f"[Dashboard] 获取任务列表失败: {e}")
        
        return result
    
    # ========== 数据集概览 (US-4) ==========
    
    @staticmethod
    def get_datasets_overview(
        subject_id: int = None, 
        sort_by: str = 'created_at', 
        order: str = 'desc'
    ) -> Dict[str, Any]:
        """
        获取数据集概览 (US-4)
        
        包含历史准确率、使用次数、难度标签等信息。
        
        Args:
            subject_id: 学科ID筛选，None 表示全部
            sort_by: 排序字段 usage|accuracy|created_at
            order: 排序方向 asc|desc
            
        Returns:
            dict: 包含以下字段
                - total: 数据集总数
                - by_subject: 按学科分布 {subject_id: count}
                - datasets: 数据集列表
                - top_usage: 使用频率排行 Top 5
        """
        cache_key = f'datasets_overview_{subject_id}_{sort_by}_{order}'
        cached = DashboardService.get_cached(cache_key)
        if cached is not None:
            return cached
        
        result = {
            'total': 0,
            'by_subject': {},
            'datasets': [],
            'top_usage': []
        }
        
        try:
            # 获取所有数据集摘要
            all_datasets = StorageService.get_all_datasets_summary()
            
            # 加载所有批量任务用于统计使用次数和历史准确率
            all_tasks = DashboardService._load_all_batch_tasks()
            
            # 统计每个数据集的使用情况
            dataset_usage = {}  # dataset_id -> {count, last_used, accuracies}
            for task in all_tasks:
                for hw_item in task.get('homework_items', []):
                    matched_dataset = hw_item.get('matched_dataset')
                    if matched_dataset:
                        if matched_dataset not in dataset_usage:
                            dataset_usage[matched_dataset] = {
                                'count': 0,
                                'last_used': '',
                                'accuracies': []
                            }
                        dataset_usage[matched_dataset]['count'] += 1
                        
                        # 更新最近使用时间
                        task_time = task.get('created_at', '')
                        if task_time > dataset_usage[matched_dataset]['last_used']:
                            dataset_usage[matched_dataset]['last_used'] = task_time
                        
                        # 收集准确率
                        accuracy = hw_item.get('accuracy')
                        if accuracy is not None:
                            dataset_usage[matched_dataset]['accuracies'].append(accuracy)
            
            # 按学科分组统计
            by_subject = {}
            
            # 处理每个数据集
            processed_datasets = []
            for ds in all_datasets:
                ds_id = ds.get('dataset_id', '')
                ds_subject_id = ds.get('subject_id')
                
                # 学科筛选
                if subject_id is not None and ds_subject_id != subject_id:
                    continue
                
                # 统计学科分布
                if ds_subject_id is not None:
                    subject_key = str(ds_subject_id)
                    by_subject[subject_key] = by_subject.get(subject_key, 0) + 1
                
                # 获取使用统计
                usage_info = dataset_usage.get(ds_id, {'count': 0, 'last_used': '', 'accuracies': []})
                
                # 计算历史准确率（平均值）
                accuracies = usage_info['accuracies']
                history_accuracy = 0
                if accuracies:
                    history_accuracy = round(sum(accuracies) / len(accuracies), 4)
                
                # 获取最近一次测试准确率
                last_accuracy = accuracies[-1] if accuracies else 0
                
                # 计算页码范围
                pages = ds.get('pages', [])
                page_range = ''
                if pages:
                    if len(pages) == 1:
                        page_range = str(pages[0])
                    else:
                        page_range = f"{min(pages)}-{max(pages)}"
                
                # 计算难度标签 (US-4.6)
                # 简单(>=90%), 中等(70%-90%), 困难(<70%)
                difficulty = 'medium'
                if history_accuracy >= 0.9:
                    difficulty = 'easy'
                elif history_accuracy < 0.7:
                    difficulty = 'hard'
                
                processed_datasets.append({
                    'dataset_id': ds_id,
                    'name': ds.get('name', ''),
                    'subject_id': ds_subject_id,
                    'subject_name': SUBJECT_MAP.get(ds_subject_id, '未知'),
                    'question_count': ds.get('question_count', 0),
                    'pages': pages,
                    'page_range': page_range,
                    'usage_count': usage_info['count'],
                    'last_used': usage_info['last_used'],
                    'history_accuracy': history_accuracy,
                    'last_accuracy': last_accuracy,
                    'last_test_time': usage_info['last_used'],
                    'difficulty': difficulty,
                    'book_id': ds.get('book_id', ''),
                    'book_name': ds.get('book_name', ''),
                    'description': ds.get('description', ''),
                    'created_at': ds.get('created_at', '')
                })
            
            # 排序 (US-4.7)
            reverse = (order == 'desc')
            if sort_by == 'usage':
                processed_datasets.sort(key=lambda x: x['usage_count'], reverse=reverse)
            elif sort_by == 'accuracy':
                processed_datasets.sort(key=lambda x: x['history_accuracy'], reverse=reverse)
            else:  # created_at
                processed_datasets.sort(key=lambda x: x['created_at'], reverse=reverse)
            
            result['total'] = len(processed_datasets)
            result['by_subject'] = by_subject
            result['datasets'] = processed_datasets
            
            # 使用频率排行 Top 5 (US-4.4)
            top_usage = sorted(processed_datasets, key=lambda x: x['usage_count'], reverse=True)[:5]
            result['top_usage'] = top_usage
            
            # 缓存结果
            DashboardService.set_cached(cache_key, result)
            
        except Exception as e:
            print(f"[Dashboard] 获取数据集概览失败: {e}")
        
        return result
    
    # ========== 学科评估概览 (US-5) ==========
    
    @staticmethod
    def get_subjects_overview() -> List[Dict[str, Any]]:
        """
        获取学科评估概览 (US-5)
        
        聚合所有批量任务中的作业数据，按学科分组统计准确率和错误类型分布。
        
        Returns:
            list: 各学科统计数据列表，每个元素包含：
                - subject_id: 学科ID
                - subject_name: 学科名称
                - task_count: 任务数
                - homework_count: 作业数
                - question_count: 题目数
                - correct_count: 正确数
                - accuracy: 准确率
                - warning: 是否低于80%警告
                - error_types: 错误类型分布
        """
        cache_key = 'subjects_overview'
        cached = DashboardService.get_cached(cache_key)
        if cached is not None:
            return cached
        
        # 初始化各学科统计
        subject_stats = {}
        for subject_id, subject_name in SUBJECT_MAP.items():
            subject_stats[subject_id] = {
                'subject_id': subject_id,
                'subject_name': subject_name,
                'task_count': 0,
                'homework_count': 0,
                'question_count': 0,
                'correct_count': 0,
                'accuracy': 0,
                'warning': False,
                'error_types': {
                    '识别错误-判断错误': 0,
                    '识别正确-判断错误': 0,
                    '缺失题目': 0,
                    'AI识别幻觉': 0,
                    '答案不匹配': 0,
                    '其他': 0
                }
            }
        
        try:
            # 加载所有批量任务
            all_tasks = DashboardService._load_all_batch_tasks()
            
            # 获取数据集信息用于确定学科
            datasets = StorageService.get_all_datasets_summary()
            dataset_subject_map = {ds['dataset_id']: ds.get('subject_id') for ds in datasets}
            
            # 统计每个任务涉及的学科
            task_subjects = {}  # task_id -> set of subject_ids
            
            for task in all_tasks:
                task_id = task.get('task_id', '')
                task_subjects[task_id] = set()
                
                for hw_item in task.get('homework_items', []):
                    # 确定学科ID
                    subject_id = None
                    
                    # 优先从匹配的数据集获取学科
                    matched_dataset = hw_item.get('matched_dataset')
                    if matched_dataset and matched_dataset in dataset_subject_map:
                        subject_id = dataset_subject_map[matched_dataset]
                    
                    # 如果没有匹配数据集，尝试从书名推断
                    if subject_id is None:
                        book_name = hw_item.get('book_name', '')
                        subject_id = DashboardService._infer_subject_from_book_name(book_name)
                    
                    if subject_id is None:
                        continue
                    
                    task_subjects[task_id].add(subject_id)
                    
                    # 统计作业数
                    subject_stats[subject_id]['homework_count'] += 1
                    
                    # 统计题目数和正确数
                    # 处理 evaluation 可能为 None 的情况
                    evaluation = hw_item.get('evaluation') or {}
                    subject_stats[subject_id]['question_count'] += evaluation.get('total_questions', 0)
                    subject_stats[subject_id]['correct_count'] += evaluation.get('correct_count', 0)
                    
                    # 统计错误类型
                    errors = evaluation.get('errors') or []
                    for error in errors:
                        error_type = error.get('error_type', '其他')
                        if error_type in subject_stats[subject_id]['error_types']:
                            subject_stats[subject_id]['error_types'][error_type] += 1
                        else:
                            subject_stats[subject_id]['error_types']['其他'] += 1
            
            # 统计任务数
            for task_id, subjects in task_subjects.items():
                for subject_id in subjects:
                    if subject_id in subject_stats:
                        subject_stats[subject_id]['task_count'] += 1
            
            # 计算准确率和警告标志
            result = []
            for subject_id, stats in subject_stats.items():
                if stats['question_count'] > 0:
                    stats['accuracy'] = round(stats['correct_count'] / stats['question_count'], 4)
                    # 准确率低于80%标红警告 (US-5.4)
                    stats['warning'] = stats['accuracy'] < 0.8
                
                # 只返回有数据的学科
                if stats['homework_count'] > 0:
                    result.append(stats)
            
            # 按准确率降序排列
            result.sort(key=lambda x: x['accuracy'], reverse=True)
            
            # 缓存结果
            DashboardService.set_cached(cache_key, result)
            
        except Exception as e:
            print(f"[Dashboard] 获取学科评估概览失败: {e}")
            result = []
        
        return result
    
    @staticmethod
    def _infer_subject_from_book_name(book_name: str) -> Optional[int]:
        """
        从书名推断学科ID
        
        Args:
            book_name: 书本名称
            
        Returns:
            int: 学科ID，无法推断时返回 None
        """
        if not book_name:
            return None
        
        book_name_lower = book_name.lower()
        
        # 学科关键词映射
        subject_keywords = {
            0: ['英语', 'english'],
            1: ['语文', 'chinese'],
            2: ['数学', 'math'],
            3: ['物理', 'physics'],
            4: ['化学', 'chemistry'],
            5: ['生物', 'biology'],
            6: ['地理', 'geography']
        }
        
        for subject_id, keywords in subject_keywords.items():
            for keyword in keywords:
                if keyword in book_name_lower:
                    return subject_id
        
        return None

    
    # ========== 测试计划 CRUD (US-6) ==========
    
    @staticmethod
    def create_plan(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建测试计划 (US-6.1)
        
        Args:
            data: 计划数据，包含以下字段：
                - name: 计划名称（必填，最大200字符）
                - description: 计划描述（可选）
                - subject_ids: 目标学科ID列表（可选）
                - target_count: 目标测试数量（可选，默认0）
                - start_date: 开始日期（可选，格式 YYYY-MM-DD）
                - end_date: 结束日期（可选，格式 YYYY-MM-DD）
                - dataset_ids: 关联数据集ID列表（可选）
                
        Returns:
            dict: 创建的计划数据，包含 plan_id
            
        Raises:
            ValueError: 参数校验失败
        """
        # 参数校验 (NFR-34.5)
        name = data.get('name', '').strip()
        if not name:
            raise ValueError('计划名称不能为空')
        if len(name) > 200:
            raise ValueError('计划名称不能超过200字符')
        
        # 生成唯一ID
        plan_id = str(uuid.uuid4())[:8]
        
        # 处理学科ID列表
        subject_ids = data.get('subject_ids', [])
        if isinstance(subject_ids, str):
            try:
                subject_ids = json.loads(subject_ids)
            except:
                subject_ids = []
        
        # 处理日期
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        try:
            # 插入测试计划
            sql = """
                INSERT INTO test_plans 
                (plan_id, name, description, subject_ids, target_count, status, 
                 start_date, end_date, ai_generated, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            now = datetime.now()
            AppDatabaseService.execute_insert(sql, (
                plan_id,
                name,
                data.get('description', ''),
                json.dumps(subject_ids),
                data.get('target_count', 0),
                'draft',  # 初始状态为草稿
                start_date,
                end_date,
                data.get('ai_generated', 0),
                now,
                now
            ))
            
            # 关联数据集 (US-6.2)
            dataset_ids = data.get('dataset_ids', [])
            if dataset_ids:
                for dataset_id in dataset_ids:
                    DashboardService._link_dataset_to_plan(plan_id, dataset_id)
            
            # 清除相关缓存（包括所有状态的缓存）
            DashboardService.clear_cache('plans_list')
            DashboardService.clear_cache('plans_list_all')
            DashboardService.clear_cache('plans_list_draft')
            DashboardService.clear_cache('plans_list_active')
            DashboardService.clear_cache('plans_list_completed')
            DashboardService.clear_cache('plans_list_archived')
            
            return {
                'plan_id': plan_id,
                'name': name,
                'description': data.get('description', ''),
                'subject_ids': subject_ids,
                'target_count': data.get('target_count', 0),
                'completed_count': 0,
                'status': 'draft',
                'start_date': start_date,
                'end_date': end_date,
                'created_at': now.isoformat()
            }
            
        except Exception as e:
            print(f"[Dashboard] 创建测试计划失败: {e}")
            raise
    
    @staticmethod
    def _link_dataset_to_plan(plan_id: str, dataset_id: str) -> bool:
        """关联数据集到计划"""
        try:
            sql = """
                INSERT IGNORE INTO test_plan_datasets (plan_id, dataset_id, created_at)
                VALUES (%s, %s, %s)
            """
            AppDatabaseService.execute_insert(sql, (plan_id, dataset_id, datetime.now()))
            return True
        except Exception as e:
            print(f"[Dashboard] 关联数据集失败: {e}")
            return False
    
    @staticmethod
    def get_plan(plan_id: str) -> Optional[Dict[str, Any]]:
        """
        获取测试计划详情 (US-6)
        
        包含关联的数据集列表和任务列表。
        
        Args:
            plan_id: 计划ID
            
        Returns:
            dict: 计划详情，包含 datasets 和 tasks 列表
            None: 计划不存在
        """
        if not plan_id:
            return None
        
        try:
            # 查询计划基本信息
            sql = "SELECT * FROM test_plans WHERE plan_id = %s"
            plan = AppDatabaseService.execute_one(sql, (plan_id,))
            
            if not plan:
                return None
            
            # 处理 JSON 字段
            subject_ids = plan.get('subject_ids', '[]')
            if isinstance(subject_ids, str):
                try:
                    subject_ids = json.loads(subject_ids)
                except:
                    subject_ids = []
            
            schedule_config = plan.get('schedule_config', '{}')
            if isinstance(schedule_config, str):
                try:
                    schedule_config = json.loads(schedule_config)
                except:
                    schedule_config = {}
            
            result = {
                'plan_id': plan['plan_id'],
                'name': plan['name'],
                'description': plan.get('description', ''),
                'subject_ids': subject_ids,
                'target_count': plan.get('target_count', 0),
                'completed_count': plan.get('completed_count', 0),
                'status': plan.get('status', 'draft'),
                'start_date': plan['start_date'].isoformat() if plan.get('start_date') else None,
                'end_date': plan['end_date'].isoformat() if plan.get('end_date') else None,
                'schedule_config': schedule_config,
                'ai_generated': plan.get('ai_generated', 0),
                'assignee_id': plan.get('assignee_id'),
                'created_at': plan['created_at'].isoformat() if plan.get('created_at') else '',
                'updated_at': plan['updated_at'].isoformat() if plan.get('updated_at') else '',
                'datasets': [],
                'tasks': [],
                'progress': 0
            }
            
            # 计算进度 (US-6.3)
            if result['target_count'] > 0:
                result['progress'] = round(result['completed_count'] / result['target_count'], 4)
            
            # 获取关联的数据集
            datasets_sql = """
                SELECT d.dataset_id, d.name, d.book_name, d.subject_id, d.question_count
                FROM test_plan_datasets tpd
                JOIN datasets d ON tpd.dataset_id = d.dataset_id
                WHERE tpd.plan_id = %s
            """
            datasets = AppDatabaseService.execute_query(datasets_sql, (plan_id,))
            result['datasets'] = [
                {
                    'dataset_id': ds['dataset_id'],
                    'name': ds['name'],
                    'book_name': ds.get('book_name', ''),
                    'subject_id': ds.get('subject_id'),
                    'subject_name': SUBJECT_MAP.get(ds.get('subject_id'), '未知'),
                    'question_count': ds.get('question_count', 0)
                }
                for ds in datasets
            ]
            
            # 获取关联的批量任务 (US-6.8)
            tasks_sql = """
                SELECT task_id, task_status, accuracy, created_at, updated_at
                FROM test_plan_tasks
                WHERE plan_id = %s
                ORDER BY created_at DESC
            """
            plan_tasks = AppDatabaseService.execute_query(tasks_sql, (plan_id,))
            
            # 加载任务详情
            for pt in plan_tasks:
                task_data = StorageService.load_batch_task(pt['task_id'])
                if task_data:
                    result['tasks'].append({
                        'task_id': pt['task_id'],
                        'name': task_data.get('name', ''),
                        'status': pt.get('task_status', task_data.get('status', 'pending')),
                        'accuracy': pt.get('accuracy') or task_data.get('overall_report', {}).get('overall_accuracy', 0),
                        'created_at': pt['created_at'].isoformat() if pt.get('created_at') else ''
                    })
            
            return result
            
        except Exception as e:
            print(f"[Dashboard] 获取测试计划详情失败: {e}")
            return None
    
    @staticmethod
    def get_plans(status: str = 'all') -> List[Dict[str, Any]]:
        """
        获取测试计划列表 (US-6) - 优化版本，使用批量查询
        
        Args:
            status: 状态筛选 all|draft|active|completed|archived
            
        Returns:
            list: 计划列表，包含简化的 workflow 流程状态
        """
        cache_key = f'plans_list_{status}'
        cached = DashboardService.get_cached(cache_key)
        if cached is not None:
            return cached
        
        try:
            sql = "SELECT * FROM test_plans WHERE 1=1"
            params = []
            
            if status and status != 'all':
                sql += " AND status = %s"
                params.append(status)
            
            sql += " ORDER BY created_at DESC"
            
            plans = AppDatabaseService.execute_query(sql, tuple(params) if params else None)
            
            if not plans:
                return []
            
            # 批量获取所有计划的数据集关联（一次查询）
            plan_ids = [p['plan_id'] for p in plans]
            datasets_map = DashboardService._batch_get_plan_datasets(plan_ids)
            
            result = []
            for plan in plans:
                # 处理 JSON 字段
                subject_ids = plan.get('subject_ids', '[]')
                if isinstance(subject_ids, str):
                    try:
                        subject_ids = json.loads(subject_ids)
                    except:
                        subject_ids = []
                
                # 计算进度
                target_count = plan.get('target_count', 0)
                completed_count = plan.get('completed_count', 0)
                progress = 0
                if target_count > 0:
                    progress = round(completed_count / target_count, 4)
                
                plan_id = plan['plan_id']
                
                # 使用预加载的数据集信息构建简化的 workflow
                plan_datasets = datasets_map.get(plan_id, [])
                workflow = DashboardService._build_simple_workflow(plan_datasets, plan)
                
                result.append({
                    'plan_id': plan_id,
                    'name': plan['name'],
                    'description': plan.get('description', ''),
                    'subject_ids': subject_ids,
                    'target_count': target_count,
                    'completed_count': completed_count,
                    'progress': progress,
                    'status': plan.get('status', 'draft'),
                    'start_date': plan['start_date'].isoformat() if plan.get('start_date') else None,
                    'end_date': plan['end_date'].isoformat() if plan.get('end_date') else None,
                    'ai_generated': plan.get('ai_generated', 0),
                    'created_at': plan['created_at'].isoformat() if plan.get('created_at') else '',
                    'workflow': workflow
                })
            
            # 缓存结果
            DashboardService.set_cached(cache_key, result)
            
            return result
            
        except Exception as e:
            print(f"[Dashboard] 获取测试计划列表失败: {e}")
            return []
    
    @staticmethod
    def _batch_get_plan_datasets(plan_ids: List[str]) -> Dict[str, List[Dict]]:
        """批量获取计划关联的数据集"""
        if not plan_ids:
            return {}
        
        try:
            placeholders = ','.join(['%s'] * len(plan_ids))
            sql = f"""
                SELECT tpd.plan_id, d.dataset_id, d.name, d.question_count 
                FROM test_plan_datasets tpd
                JOIN datasets d ON tpd.dataset_id = d.dataset_id
                WHERE tpd.plan_id IN ({placeholders})
            """
            rows = AppDatabaseService.execute_query(sql, tuple(plan_ids))
            
            result = {}
            for row in rows:
                pid = row['plan_id']
                if pid not in result:
                    result[pid] = []
                result[pid].append({
                    'id': row['dataset_id'],
                    'name': row['name'],
                    'question_count': row.get('question_count', 0)
                })
            return result
        except Exception as e:
            print(f"[Dashboard] 批量获取数据集失败: {e}")
            return {}
    
    @staticmethod
    def _build_simple_workflow(datasets: List[Dict], plan: Dict) -> Dict[str, Any]:
        """构建简化的 workflow 状态（不查询数据库）"""
        workflow = {
            'dataset': {'status': 'pending', 'datasets': [], 'total_questions': 0},
            'homework': {'status': 'pending', 'total_count': 0, 'source': ''},
            'evaluation': {'status': 'pending', 'progress': {'completed': 0, 'total': 0}, 'accuracy': None},
            'report': {'status': 'pending'}
        }
        
        if datasets:
            workflow['dataset']['status'] = 'completed'
            workflow['dataset']['datasets'] = datasets
            workflow['dataset']['total_questions'] = sum(d.get('question_count', 0) for d in datasets)
        
        # 根据计划状态推断其他节点状态
        plan_status = plan.get('status', 'draft')
        if plan_status == 'active':
            workflow['homework']['status'] = 'processing'
        elif plan_status == 'completed':
            workflow['homework']['status'] = 'completed'
            workflow['evaluation']['status'] = 'completed'
            workflow['report']['status'] = 'completed'
        
        return workflow
    
    @staticmethod
    def _build_plan_workflow(plan_id: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建测试计划的工作流状态
        
        Args:
            plan_id: 计划ID
            plan: 计划数据
            
        Returns:
            dict: workflow 状态，包含 dataset, homework, evaluation, report 四个节点
        """
        workflow = {
            'dataset': {'status': 'pending', 'datasets': [], 'total_questions': 0},
            'homework': {'status': 'pending', 'total_count': 0, 'source': ''},
            'evaluation': {'status': 'pending', 'progress': {'completed': 0, 'total': 0}, 'accuracy': None},
            'report': {'status': 'pending'}
        }
        
        try:
            # 1. 获取关联的数据集
            datasets_sql = """
                SELECT d.dataset_id, d.name, d.question_count 
                FROM test_plan_datasets tpd
                JOIN datasets d ON tpd.dataset_id = d.dataset_id
                WHERE tpd.plan_id = %s
            """
            datasets = AppDatabaseService.execute_query(datasets_sql, (plan_id,))
            
            if datasets:
                workflow['dataset']['status'] = 'completed'
                workflow['dataset']['datasets'] = [
                    {'id': ds['dataset_id'], 'name': ds['name'], 'question_count': ds.get('question_count', 0)}
                    for ds in datasets
                ]
                workflow['dataset']['total_questions'] = sum(ds.get('question_count', 0) for ds in datasets)
            
            # 2. 获取关联的批量任务
            tasks_sql = """
                SELECT t.task_id, t.status, t.overall_accuracy, t.total_questions, t.correct_count
                FROM test_plan_tasks tpt
                JOIN batch_tasks t ON tpt.task_id = t.task_id
                WHERE tpt.plan_id = %s
            """
            # 注意：batch_tasks 可能存储在文件中，这里尝试从数据库获取
            # 如果没有 batch_tasks 表，则从文件系统获取
            try:
                tasks = AppDatabaseService.execute_query(tasks_sql, (plan_id,))
            except:
                tasks = []
            
            # 从文件系统获取任务信息
            if not tasks:
                tasks = DashboardService._get_plan_tasks_from_files(plan_id)
            
            if tasks:
                total_homework = sum(t.get('total_homework', 0) for t in tasks)
                workflow['homework']['status'] = 'completed'
                workflow['homework']['total_count'] = total_homework
                workflow['homework']['source'] = f'{len(tasks)} 个批量任务'
                
                # 评估状态
                completed_tasks = [t for t in tasks if t.get('status') == 'completed']
                running_tasks = [t for t in tasks if t.get('status') == 'processing']
                
                if running_tasks:
                    workflow['evaluation']['status'] = 'running'
                elif completed_tasks:
                    workflow['evaluation']['status'] = 'completed'
                
                # 计算总体准确率
                total_questions = sum(t.get('total_questions', 0) for t in tasks)
                total_correct = sum(t.get('correct_count', 0) for t in tasks)
                
                workflow['evaluation']['progress'] = {
                    'completed': len(completed_tasks),
                    'total': len(tasks)
                }
                workflow['evaluation']['total_questions'] = total_questions
                workflow['evaluation']['correct'] = total_correct
                
                if total_questions > 0:
                    workflow['evaluation']['accuracy'] = round(total_correct / total_questions, 4)
                
                # 报告状态
                if workflow['evaluation']['status'] == 'completed':
                    workflow['report']['status'] = 'completed'
                    workflow['report']['accuracy'] = workflow['evaluation']['accuracy']
                    workflow['report']['total_questions'] = total_questions
                    workflow['report']['correct'] = total_correct
            
        except Exception as e:
            print(f"[Dashboard] 构建计划工作流失败 {plan_id}: {e}")
        
        return workflow
    
    @staticmethod
    def _get_plan_tasks_from_files(plan_id: str) -> List[Dict[str, Any]]:
        """
        从文件系统获取计划关联的任务
        
        Args:
            plan_id: 计划ID
            
        Returns:
            list: 任务列表
        """
        tasks = []
        try:
            # 查询关联表
            sql = "SELECT task_id FROM test_plan_tasks WHERE plan_id = %s"
            task_ids = AppDatabaseService.execute_query(sql, (plan_id,))
            
            if not task_ids:
                return []
            
            # 从文件加载任务数据
            batch_tasks_dir = StorageService.BATCH_TASKS_DIR
            for row in task_ids:
                task_id = row['task_id']
                filepath = os.path.join(batch_tasks_dir, f'{task_id}.json')
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            task_data = json.load(f)
                            overall_report = task_data.get('overall_report') or {}
                            tasks.append({
                                'task_id': task_id,
                                'status': task_data.get('status', 'pending'),
                                'total_homework': len(task_data.get('homework_items', [])),
                                'total_questions': overall_report.get('total_questions', 0),
                                'correct_count': overall_report.get('correct_questions', 0)
                            })
                    except Exception as e:
                        print(f"[Dashboard] 加载任务文件失败 {task_id}: {e}")
        except Exception as e:
            print(f"[Dashboard] 获取计划任务失败: {e}")
        
        return tasks
    
    @staticmethod
    def start_plan(plan_id: str) -> Optional[Dict[str, Any]]:
        """
        启动测试计划
        
        将计划状态从 draft 改为 active。
        
        Args:
            plan_id: 计划ID
            
        Returns:
            dict: 更新后的计划数据
            None: 启动失败
            
        Raises:
            ValueError: 计划不存在或状态不允许启动
        """
        if not plan_id:
            raise ValueError('计划ID不能为空')
        
        try:
            # 检查计划是否存在
            sql = "SELECT * FROM test_plans WHERE plan_id = %s"
            plans = AppDatabaseService.execute_query(sql, (plan_id,))
            
            if not plans:
                raise ValueError('计划不存在')
            
            plan = plans[0]
            current_status = plan.get('status', 'draft')
            
            # 只有 draft 状态的计划可以启动
            if current_status != 'draft':
                raise ValueError(f'计划当前状态为 {current_status}，无法启动')
            
            # 更新状态为 active
            update_sql = """
                UPDATE test_plans 
                SET status = 'active', updated_at = %s 
                WHERE plan_id = %s
            """
            AppDatabaseService.execute_insert(update_sql, (datetime.now(), plan_id))
            
            # 清除缓存
            DashboardService.clear_cache('plans_list')
            DashboardService.clear_cache(f'plans_list_all')
            DashboardService.clear_cache(f'plans_list_draft')
            DashboardService.clear_cache(f'plans_list_active')
            
            return {
                'plan_id': plan_id,
                'status': 'active',
                'message': '计划已启动'
            }
            
        except ValueError:
            raise
        except Exception as e:
            print(f"[Dashboard] 启动计划失败 {plan_id}: {e}")
            return None
    
    @staticmethod
    def update_plan(plan_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        更新测试计划 (US-6.4)
        
        Args:
            plan_id: 计划ID
            data: 要更新的字段
            
        Returns:
            dict: 更新后的计划数据
            None: 更新失败
        """
        if not plan_id:
            raise ValueError('计划ID不能为空')
        
        # 检查计划是否存在
        existing = DashboardService.get_plan(plan_id)
        if not existing:
            raise ValueError('计划不存在')
        
        try:
            # 构建更新语句
            update_fields = []
            params = []
            
            # 可更新的字段
            allowed_fields = ['name', 'description', 'target_count', 'status', 
                            'start_date', 'end_date', 'assignee_id']
            
            for field in allowed_fields:
                if field in data:
                    value = data[field]
                    # 名称校验
                    if field == 'name':
                        if not value or not value.strip():
                            raise ValueError('计划名称不能为空')
                        if len(value) > 200:
                            raise ValueError('计划名称不能超过200字符')
                        value = value.strip()
                    
                    update_fields.append(f"{field} = %s")
                    params.append(value)
            
            # 处理 subject_ids (JSON字段)
            if 'subject_ids' in data:
                subject_ids = data['subject_ids']
                if isinstance(subject_ids, list):
                    subject_ids = json.dumps(subject_ids)
                update_fields.append("subject_ids = %s")
                params.append(subject_ids)
            
            # 处理 schedule_config (JSON字段)
            if 'schedule_config' in data:
                schedule_config = data['schedule_config']
                if isinstance(schedule_config, dict):
                    schedule_config = json.dumps(schedule_config)
                update_fields.append("schedule_config = %s")
                params.append(schedule_config)
            
            if not update_fields:
                return existing
            
            # 添加更新时间
            update_fields.append("updated_at = %s")
            params.append(datetime.now())
            
            # 添加 plan_id 参数
            params.append(plan_id)
            
            sql = f"UPDATE test_plans SET {', '.join(update_fields)} WHERE plan_id = %s"
            AppDatabaseService.execute_update(sql, tuple(params))
            
            # 更新数据集关联
            if 'dataset_ids' in data:
                # 先删除旧关联
                AppDatabaseService.execute_update(
                    "DELETE FROM test_plan_datasets WHERE plan_id = %s",
                    (plan_id,)
                )
                # 添加新关联
                for dataset_id in data['dataset_ids']:
                    DashboardService._link_dataset_to_plan(plan_id, dataset_id)
            
            # 清除缓存
            DashboardService.clear_cache('plans_list')
            DashboardService.clear_cache(f'plans_list_{existing["status"]}')
            if 'status' in data:
                DashboardService.clear_cache(f'plans_list_{data["status"]}')
            
            return DashboardService.get_plan(plan_id)
            
        except ValueError:
            raise
        except Exception as e:
            print(f"[Dashboard] 更新测试计划失败: {e}")
            raise
    
    @staticmethod
    def delete_plan(plan_id: str) -> bool:
        """
        删除测试计划 (US-6.5)
        
        同时删除关联的数据集关系和任务关系。
        
        Args:
            plan_id: 计划ID
            
        Returns:
            bool: 是否删除成功
        """
        if not plan_id:
            return False
        
        try:
            # 删除关联的数据集
            AppDatabaseService.execute_update(
                "DELETE FROM test_plan_datasets WHERE plan_id = %s",
                (plan_id,)
            )
            
            # 删除关联的任务
            AppDatabaseService.execute_update(
                "DELETE FROM test_plan_tasks WHERE plan_id = %s",
                (plan_id,)
            )
            
            # 删除关联的分配
            AppDatabaseService.execute_update(
                "DELETE FROM test_plan_assignments WHERE plan_id = %s",
                (plan_id,)
            )
            
            # 删除关联的评论
            AppDatabaseService.execute_update(
                "DELETE FROM test_plan_comments WHERE plan_id = %s",
                (plan_id,)
            )
            
            # 删除关联的日志
            AppDatabaseService.execute_update(
                "DELETE FROM test_plan_logs WHERE plan_id = %s",
                (plan_id,)
            )
            
            # 删除计划本身
            affected = AppDatabaseService.execute_update(
                "DELETE FROM test_plans WHERE plan_id = %s",
                (plan_id,)
            )
            
            # 清除缓存
            DashboardService.clear_cache('plans_list')
            
            return affected > 0
            
        except Exception as e:
            print(f"[Dashboard] 删除测试计划失败: {e}")
            return False
    
    @staticmethod
    def clone_plan(plan_id: str) -> Optional[Dict[str, Any]]:
        """
        克隆测试计划 (US-6.6)
        
        复制所有字段，名称加"(副本)"后缀。
        
        Args:
            plan_id: 要克隆的计划ID
            
        Returns:
            dict: 新创建的计划数据
            None: 克隆失败
        """
        # 获取原计划
        original = DashboardService.get_plan(plan_id)
        if not original:
            raise ValueError('原计划不存在')
        
        # 准备新计划数据
        new_data = {
            'name': f"{original['name']}(副本)",
            'description': original.get('description', ''),
            'subject_ids': original.get('subject_ids', []),
            'target_count': original.get('target_count', 0),
            'start_date': original.get('start_date'),
            'end_date': original.get('end_date'),
            'dataset_ids': [ds['dataset_id'] for ds in original.get('datasets', [])]
        }
        
        # 创建新计划
        return DashboardService.create_plan(new_data)
    
    @staticmethod
    def link_task_to_plan(plan_id: str, task_id: str) -> bool:
        """
        关联批量任务到测试计划 (US-6.10)
        
        Args:
            plan_id: 计划ID
            task_id: 批量任务ID
            
        Returns:
            bool: 是否关联成功
        """
        if not plan_id or not task_id:
            return False
        
        try:
            # 检查计划是否存在
            plan = DashboardService.get_plan(plan_id)
            if not plan:
                raise ValueError('计划不存在')
            
            # 检查任务是否存在
            task_data = StorageService.load_batch_task(task_id)
            if not task_data:
                raise ValueError('任务不存在')
            
            # 获取任务状态和准确率
            task_status = task_data.get('status', 'pending')
            accuracy = task_data.get('overall_report', {}).get('overall_accuracy')
            
            # 插入关联记录
            sql = """
                INSERT INTO test_plan_tasks (plan_id, task_id, task_status, accuracy, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE task_status = VALUES(task_status), accuracy = VALUES(accuracy), updated_at = VALUES(updated_at)
            """
            now = datetime.now()
            AppDatabaseService.execute_insert(sql, (
                plan_id, task_id, task_status, accuracy, now, now
            ))
            
            # 如果任务已完成，更新计划进度
            if task_status == 'completed':
                DashboardService.update_plan_progress(plan_id)
            
            return True
            
        except Exception as e:
            print(f"[Dashboard] 关联任务到计划失败: {e}")
            return False
    
    @staticmethod
    def update_plan_progress(plan_id: str) -> None:
        """
        更新计划完成度 (US-6.9)
        
        基于关联任务的完成状态自动更新 completed_count。
        当关联的批量任务状态变为 completed 时调用。
        
        Args:
            plan_id: 计划ID
        """
        if not plan_id:
            return
        
        try:
            # 统计已完成的任务数
            sql = """
                SELECT COUNT(*) as completed_count
                FROM test_plan_tasks
                WHERE plan_id = %s AND task_status = 'completed'
            """
            result = AppDatabaseService.execute_one(sql, (plan_id,))
            completed_count = result['completed_count'] if result else 0
            
            # 更新计划的 completed_count
            update_sql = """
                UPDATE test_plans 
                SET completed_count = %s, updated_at = %s
                WHERE plan_id = %s
            """
            AppDatabaseService.execute_update(update_sql, (completed_count, datetime.now(), plan_id))
            
            # 检查是否需要更新状态为 completed
            plan = AppDatabaseService.execute_one(
                "SELECT target_count, status FROM test_plans WHERE plan_id = %s",
                (plan_id,)
            )
            if plan and plan['target_count'] > 0 and completed_count >= plan['target_count']:
                if plan['status'] == 'active':
                    AppDatabaseService.execute_update(
                        "UPDATE test_plans SET status = 'completed', updated_at = %s WHERE plan_id = %s",
                        (datetime.now(), plan_id)
                    )
            
            # 清除缓存
            DashboardService.clear_cache('plans_list')
            
        except Exception as e:
            print(f"[Dashboard] 更新计划进度失败: {e}")
    
    # ========== 数据同步 (US-9) ==========
    
    @staticmethod
    def sync_data() -> Dict[str, Any]:
        """
        同步数据 (US-9)
        
        清除所有缓存，重新加载数据。
        
        Returns:
            dict: 同步结果
                - synced_tasks: 同步的任务数
                - synced_at: 同步时间
        """
        try:
            # 清除所有缓存
            DashboardService.clear_cache()
            
            # 重新加载任务数据
            tasks = DashboardService._load_all_batch_tasks()
            
            return {
                'synced_tasks': len(tasks),
                'synced_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[Dashboard] 数据同步失败: {e}")
            raise
    
    # ========== 辅助方法 ==========
    
    @staticmethod
    def get_dataset_history_tests(dataset_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取数据集的历史测试记录 (US-4.8)
        
        用于鼠标悬停时显示历史测试摘要。
        
        Args:
            dataset_id: 数据集ID
            limit: 返回记录数，默认5条
            
        Returns:
            list: 历史测试记录列表
        """
        if not dataset_id:
            return []
        
        try:
            all_tasks = DashboardService._load_all_batch_tasks()
            
            # 收集使用该数据集的测试记录
            tests = []
            for task in all_tasks:
                for hw_item in task.get('homework_items', []):
                    if hw_item.get('matched_dataset') == dataset_id:
                        accuracy = hw_item.get('accuracy')
                        if accuracy is not None:
                            tests.append({
                                'task_id': task.get('task_id', ''),
                                'task_name': task.get('name', ''),
                                'accuracy': accuracy,
                                'created_at': task.get('created_at', '')
                            })
                        break  # 每个任务只记录一次
            
            # 按时间倒序排列，取最近的记录
            tests.sort(key=lambda x: x['created_at'], reverse=True)
            return tests[:limit]
            
        except Exception as e:
            print(f"[Dashboard] 获取数据集历史测试记录失败: {e}")
            return []
    
    # ========== AI生成测试计划 (US-7) ==========
    
    @staticmethod
    def generate_ai_plan(
        dataset_ids: List[str],
        sample_count: int = 30,
        subject_id: int = None
    ) -> Dict[str, Any]:
        """
        AI生成测试计划 (US-7)
        
        根据选定的数据集，使用 DeepSeek V3.2 模型分析数据集内容，
        自动生成测试计划建议，包含计划名称、测试目标、测试步骤、
        预期时长和验收标准。
        
        Args:
            dataset_ids: 数据集ID列表（支持多选）
            sample_count: 测试样本数量（模拟学生数），默认30
            subject_id: 学科ID，可选，用于生成更精准的计划
            
        Returns:
            dict: AI生成的测试计划数据，包含：
                - name: 计划名称
                - description: 计划描述
                - objectives: 测试目标列表（3-5条）
                - steps: 测试步骤列表
                - expected_duration: 预期时长
                - acceptance_criteria: 验收标准列表
                
        Raises:
            ValueError: 参数校验失败
            Exception: AI调用失败
        """
        from .llm_service import LLMService
        
        # 参数校验 (NFR-34.5)
        if not dataset_ids or len(dataset_ids) == 0:
            raise ValueError('请至少选择一个数据集')
        
        if sample_count < 1:
            sample_count = 30
        if sample_count > 100:
            sample_count = 100
        
        try:
            # 1. 获取数据集详细信息
            datasets_info = []
            total_questions = 0
            question_types = {'choice': 0, 'fill': 0, 'subjective': 0}
            book_names = set()
            pages_range = []
            
            for dataset_id in dataset_ids:
                # 查询数据集元数据
                sql = """
                    SELECT dataset_id, name, book_id, book_name, subject_id, 
                           pages, question_count, description
                    FROM datasets 
                    WHERE dataset_id = %s
                """
                dataset = AppDatabaseService.execute_one(sql, (dataset_id,))
                
                if not dataset:
                    continue
                
                # 解析 pages 字段
                pages = dataset.get('pages', '[]')
                if isinstance(pages, str):
                    try:
                        pages = json.loads(pages)
                    except:
                        pages = []
                
                datasets_info.append({
                    'name': dataset.get('name', ''),
                    'book_name': dataset.get('book_name', ''),
                    'subject_id': dataset.get('subject_id'),
                    'pages': pages,
                    'question_count': dataset.get('question_count', 0)
                })
                
                total_questions += dataset.get('question_count', 0)
                if dataset.get('book_name'):
                    book_names.add(dataset.get('book_name'))
                pages_range.extend(pages)
                
                # 如果没有指定学科，从数据集获取
                if subject_id is None and dataset.get('subject_id') is not None:
                    subject_id = dataset.get('subject_id')
                
                # 获取基准效果数据，分析题目类型分布
                effects_sql = """
                    SELECT question_type, extra_data
                    FROM baseline_effects
                    WHERE dataset_id = %s
                """
                effects = AppDatabaseService.execute_query(effects_sql, (dataset_id,))
                
                for effect in effects:
                    # 解析题目类型
                    extra_data = effect.get('extra_data', '{}')
                    if isinstance(extra_data, str):
                        try:
                            extra_data = json.loads(extra_data)
                        except:
                            extra_data = {}
                    
                    bvalue = str(extra_data.get('bvalue', ''))
                    q_type = extra_data.get('questionType', '')
                    
                    # 分类统计
                    if bvalue in ('1', '2', '3'):
                        question_types['choice'] += 1
                    elif q_type == 'objective' and bvalue == '4':
                        question_types['fill'] += 1
                    else:
                        question_types['subjective'] += 1
            
            if not datasets_info:
                raise ValueError('未找到有效的数据集')
            
            # 2. 构建 AI 提示词
            subject_name = SUBJECT_MAP.get(subject_id, '未知学科')
            book_names_str = '、'.join(list(book_names)[:3])
            pages_str = ''
            if pages_range:
                pages_range = sorted(set(pages_range))
                if len(pages_range) == 1:
                    pages_str = f'P{pages_range[0]}'
                else:
                    pages_str = f'P{min(pages_range)}-{max(pages_range)}'
            
            # 计算题目类型占比
            type_distribution = []
            if question_types['choice'] > 0:
                type_distribution.append(f"选择题 {question_types['choice']} 道")
            if question_types['fill'] > 0:
                type_distribution.append(f"客观填空题 {question_types['fill']} 道")
            if question_types['subjective'] > 0:
                type_distribution.append(f"主观题 {question_types['subjective']} 道")
            type_str = '、'.join(type_distribution) if type_distribution else '未知'
            
            prompt = f"""你是一个AI批改效果测试专家。请根据以下数据集信息，生成一个详细的测试计划。

## 数据集信息
- 学科: {subject_name}
- 书本: {book_names_str}
- 页码范围: {pages_str}
- 题目总数: {total_questions} 道
- 题目类型分布: {type_str}
- 测试样本数: {sample_count} 份作业

## 要求
请生成一个JSON格式的测试计划，包含以下字段：
1. name: 测试计划名称（简洁明了，如"物理八上温度章节测试计划"）
2. description: 计划描述（1-2句话说明测试目的）
3. objectives: 测试目标数组（3-5条，每条说明要验证的具体内容）
4. steps: 测试步骤数组（4-6步，说明执行流程）
5. expected_duration: 预期时长（如"2小时"）
6. acceptance_criteria: 验收标准数组（3-5条，包含具体的准确率指标）

## 验收标准参考
- 选择题准确率通常要求 >= 95%
- 客观填空题准确率通常要求 >= 85%
- 主观题准确率通常要求 >= 75%
- 整体准确率通常要求 >= 80%

请直接返回JSON格式，不要包含其他内容。"""

            # 3. 调用 DeepSeek API (NFR-34.6: 30秒超时)
            system_prompt = '你是一个专业的AI批改效果测试专家，擅长制定测试计划和验收标准。请用中文回答。'
            
            result = LLMService.call_deepseek(
                prompt=prompt,
                system_prompt=system_prompt,
                model='deepseek-v3.2',
                timeout=30
            )
            
            if 'error' in result:
                raise Exception(f"AI调用失败: {result['error']}")
            
            # 4. 解析 AI 返回的 JSON
            content = result.get('content', '')
            plan_data = LLMService.parse_json_response(content)
            
            if not plan_data:
                # 如果解析失败，返回默认模板
                plan_data = DashboardService._generate_default_plan(
                    subject_name, book_names_str, pages_str, 
                    total_questions, sample_count, question_types
                )
            
            # 5. 验证和补充必要字段
            plan_data = DashboardService._validate_plan_data(plan_data, subject_name)
            
            return plan_data
            
        except ValueError:
            raise
        except Exception as e:
            print(f"[Dashboard] AI生成测试计划失败: {e}")
            raise Exception(f"生成测试计划失败: {str(e)}")
    
    @staticmethod
    def _generate_default_plan(
        subject_name: str,
        book_names: str,
        pages_str: str,
        total_questions: int,
        sample_count: int,
        question_types: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        生成默认测试计划模板
        
        当 AI 调用失败或解析失败时使用。
        
        Args:
            subject_name: 学科名称
            book_names: 书本名称
            pages_str: 页码范围
            total_questions: 题目总数
            sample_count: 样本数量
            question_types: 题目类型分布
            
        Returns:
            dict: 默认测试计划数据
        """
        return {
            'name': f'{subject_name}{book_names[:10]}测试计划',
            'description': f'针对{book_names} {pages_str}的AI批改效果测试，共{total_questions}道题目',
            'objectives': [
                f'验证{subject_name}学科AI批改的整体准确率',
                '验证选择题判断准确率' if question_types.get('choice', 0) > 0 else '验证题目识别准确率',
                '验证填空题答案匹配准确率' if question_types.get('fill', 0) > 0 else '验证答案识别准确率',
                '验证主观题评分合理性' if question_types.get('subjective', 0) > 0 else '验证批改结果一致性',
                '分析错误类型分布，识别改进方向'
            ],
            'steps': [
                f'准备{sample_count}份学生作业样本',
                '使用AI批改系统进行批量批改',
                '与基准效果数据进行对比评估',
                '统计各题型准确率和错误分布',
                '生成评估报告并分析问题',
                '提出优化建议'
            ],
            'expected_duration': f'{max(1, sample_count // 15)}小时',
            'acceptance_criteria': [
                '选择题准确率 >= 95%' if question_types.get('choice', 0) > 0 else '题目识别准确率 >= 90%',
                '客观填空题准确率 >= 85%' if question_types.get('fill', 0) > 0 else '答案匹配准确率 >= 85%',
                '主观题准确率 >= 75%' if question_types.get('subjective', 0) > 0 else '评分一致性 >= 80%',
                '整体准确率 >= 80%',
                '无严重识别错误（AI幻觉率 < 5%）'
            ]
        }
    
    @staticmethod
    def _validate_plan_data(plan_data: Dict[str, Any], subject_name: str) -> Dict[str, Any]:
        """
        验证和补充测试计划数据
        
        确保返回的计划数据包含所有必要字段。
        
        Args:
            plan_data: AI生成的计划数据
            subject_name: 学科名称（用于生成默认值）
            
        Returns:
            dict: 验证后的计划数据
        """
        # 确保必要字段存在
        if not plan_data.get('name'):
            plan_data['name'] = f'{subject_name}测试计划'
        
        if not plan_data.get('description'):
            plan_data['description'] = f'{subject_name}学科AI批改效果测试计划'
        
        if not plan_data.get('objectives') or not isinstance(plan_data['objectives'], list):
            plan_data['objectives'] = [
                '验证AI批改整体准确率',
                '分析错误类型分布',
                '评估批改效率'
            ]
        
        if not plan_data.get('steps') or not isinstance(plan_data['steps'], list):
            plan_data['steps'] = [
                '准备测试数据',
                '执行批量批改',
                '对比评估结果',
                '生成分析报告'
            ]
        
        if not plan_data.get('expected_duration'):
            plan_data['expected_duration'] = '2小时'
        
        if not plan_data.get('acceptance_criteria') or not isinstance(plan_data['acceptance_criteria'], list):
            plan_data['acceptance_criteria'] = [
                '整体准确率 >= 80%',
                '选择题准确率 >= 95%',
                '填空题准确率 >= 85%'
            ]
        
        return plan_data

    # ========== 趋势分析 (US-15) ==========
    
    @staticmethod
    def generate_daily_statistics_snapshot(date: str = None) -> Dict[str, Any]:
        """
        生成每日统计快照 (US-15, 10.1)
        
        将指定日期的统计数据保存到 daily_statistics 表。
        包含整体统计和按学科分组的统计。
        
        Args:
            date: 统计日期，格式 YYYY-MM-DD，默认为昨天
            
        Returns:
            dict: 生成的统计数据
        """
        if not date:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        try:
            # 解析日期
            stat_date = datetime.strptime(date, '%Y-%m-%d').date()
            start_datetime = datetime.combine(stat_date, datetime.min.time())
            end_datetime = datetime.combine(stat_date, datetime.max.time())
            
            # 加载所有批量任务
            all_tasks = DashboardService._load_all_batch_tasks()
            
            # 筛选指定日期的任务
            day_tasks = []
            for task in all_tasks:
                created_at = task.get('created_at', '')
                if created_at:
                    try:
                        task_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if task_time.tzinfo:
                            task_time = task_time.replace(tzinfo=None)
                        if start_datetime <= task_time <= end_datetime:
                            day_tasks.append(task)
                    except:
                        continue
            
            # 获取数据集信息用于确定学科
            datasets = StorageService.get_all_datasets_summary()
            dataset_subject_map = {ds['dataset_id']: ds.get('subject_id') for ds in datasets}
            
            # 统计整体数据
            overall_stats = {
                'task_count': len(day_tasks),
                'homework_count': 0,
                'question_count': 0,
                'correct_count': 0,
                'error_distribution': {}
            }
            
            # 按学科统计
            subject_stats = {}
            for subject_id in SUBJECT_MAP.keys():
                subject_stats[subject_id] = {
                    'task_count': 0,
                    'homework_count': 0,
                    'question_count': 0,
                    'correct_count': 0,
                    'error_distribution': {}
                }
            
            # 遍历任务统计
            task_subjects = {}  # task_id -> set of subject_ids
            
            for task in day_tasks:
                task_id = task.get('task_id', '')
                task_subjects[task_id] = set()
                
                for hw_item in task.get('homework_items', []):
                    # 确定学科ID
                    subject_id = None
                    matched_dataset = hw_item.get('matched_dataset')
                    if matched_dataset and matched_dataset in dataset_subject_map:
                        subject_id = dataset_subject_map[matched_dataset]
                    
                    if subject_id is None:
                        book_name = hw_item.get('book_name', '')
                        subject_id = DashboardService._infer_subject_from_book_name(book_name)
                    
                    # 统计整体数据
                    overall_stats['homework_count'] += 1
                    evaluation = hw_item.get('evaluation') or {}
                    overall_stats['question_count'] += evaluation.get('total_questions', 0)
                    overall_stats['correct_count'] += evaluation.get('correct_count', 0)
                    
                    # 统计错误类型
                    errors = evaluation.get('errors') or []
                    for error in errors:
                        error_type = error.get('error_type', '其他')
                        overall_stats['error_distribution'][error_type] = \
                            overall_stats['error_distribution'].get(error_type, 0) + 1
                    
                    # 按学科统计
                    if subject_id is not None and subject_id in subject_stats:
                        task_subjects[task_id].add(subject_id)
                        subject_stats[subject_id]['homework_count'] += 1
                        subject_stats[subject_id]['question_count'] += evaluation.get('total_questions', 0)
                        subject_stats[subject_id]['correct_count'] += evaluation.get('correct_count', 0)
                        
                        for error in errors:
                            error_type = error.get('error_type', '其他')
                            subject_stats[subject_id]['error_distribution'][error_type] = \
                                subject_stats[subject_id]['error_distribution'].get(error_type, 0) + 1
            
            # 统计任务数
            for task_id, subjects in task_subjects.items():
                for subject_id in subjects:
                    if subject_id in subject_stats:
                        subject_stats[subject_id]['task_count'] += 1
            
            # 计算准确率
            overall_accuracy = 0
            if overall_stats['question_count'] > 0:
                overall_accuracy = round(overall_stats['correct_count'] / overall_stats['question_count'], 4)
            
            # 保存整体统计到数据库
            DashboardService._save_daily_statistics(
                stat_date=date,
                subject_id=None,  # NULL 表示整体
                stats=overall_stats,
                accuracy=overall_accuracy
            )
            
            # 保存各学科统计
            for subject_id, stats in subject_stats.items():
                if stats['homework_count'] > 0:
                    accuracy = 0
                    if stats['question_count'] > 0:
                        accuracy = round(stats['correct_count'] / stats['question_count'], 4)
                    
                    DashboardService._save_daily_statistics(
                        stat_date=date,
                        subject_id=subject_id,
                        stats=stats,
                        accuracy=accuracy
                    )
            
            print(f"[Dashboard] 统计快照生成成功: date={date}, tasks={overall_stats['task_count']}")
            
            return {
                'date': date,
                'overall': {
                    **overall_stats,
                    'accuracy': overall_accuracy
                },
                'by_subject': subject_stats
            }
            
        except Exception as e:
            print(f"[Dashboard] 生成统计快照失败: {e}")
            raise
    
    @staticmethod
    def _save_daily_statistics(
        stat_date: str,
        subject_id: int,
        stats: Dict[str, Any],
        accuracy: float
    ) -> None:
        """
        保存每日统计数据到数据库
        
        Args:
            stat_date: 统计日期
            subject_id: 学科ID，None 表示整体
            stats: 统计数据
            accuracy: 准确率
        """
        try:
            sql = """
                INSERT INTO daily_statistics 
                (stat_date, subject_id, task_count, homework_count, question_count, 
                 correct_count, accuracy, error_distribution, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    task_count = VALUES(task_count),
                    homework_count = VALUES(homework_count),
                    question_count = VALUES(question_count),
                    correct_count = VALUES(correct_count),
                    accuracy = VALUES(accuracy),
                    error_distribution = VALUES(error_distribution),
                    updated_at = VALUES(updated_at)
            """
            now = datetime.now()
            AppDatabaseService.execute_insert(sql, (
                stat_date,
                subject_id,
                stats.get('task_count', 0),
                stats.get('homework_count', 0),
                stats.get('question_count', 0),
                stats.get('correct_count', 0),
                accuracy,
                json.dumps(stats.get('error_distribution', {}), ensure_ascii=False),
                now,
                now
            ))
        except Exception as e:
            print(f"[Dashboard] 保存统计数据失败: {e}")
    
    @staticmethod
    def get_trends(days: int = 7, subject_id: int = None) -> Dict[str, Any]:
        """
        获取趋势分析数据 (US-15, 10.2.1)
        
        从 daily_statistics 表获取历史统计数据，
        用于绘制趋势折线图。
        
        Args:
            days: 时间范围，可选值 7|30|90
            subject_id: 学科ID筛选，None 表示整体
            
        Returns:
            dict: 趋势数据
                - trends: 整体趋势数据列表
                - by_subject: 按学科分组的趋势数据
        """
        try:
            # 计算日期范围
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            result = {
                'trends': [],
                'by_subject': {}
            }
            
            # 查询整体趋势数据
            if subject_id is None:
                sql = """
                    SELECT stat_date, task_count, homework_count, question_count, 
                           correct_count, accuracy, error_distribution
                    FROM daily_statistics
                    WHERE stat_date >= %s AND stat_date <= %s AND subject_id IS NULL
                    ORDER BY stat_date ASC
                """
                rows = AppDatabaseService.execute_query(sql, (start_date, end_date))
                
                for row in rows:
                    result['trends'].append({
                        'date': row['stat_date'].isoformat() if hasattr(row['stat_date'], 'isoformat') else str(row['stat_date']),
                        'accuracy': float(row['accuracy']) if row['accuracy'] else 0,
                        'task_count': row['task_count'] or 0,
                        'question_count': row['question_count'] or 0
                    })
                
                # 查询各学科趋势
                subject_sql = """
                    SELECT stat_date, subject_id, accuracy
                    FROM daily_statistics
                    WHERE stat_date >= %s AND stat_date <= %s AND subject_id IS NOT NULL
                    ORDER BY subject_id, stat_date ASC
                """
                subject_rows = AppDatabaseService.execute_query(subject_sql, (start_date, end_date))
                
                for row in subject_rows:
                    sid = str(row['subject_id'])
                    if sid not in result['by_subject']:
                        result['by_subject'][sid] = []
                    result['by_subject'][sid].append({
                        'date': row['stat_date'].isoformat() if hasattr(row['stat_date'], 'isoformat') else str(row['stat_date']),
                        'accuracy': float(row['accuracy']) if row['accuracy'] else 0
                    })
            else:
                # 查询指定学科的趋势
                sql = """
                    SELECT stat_date, task_count, homework_count, question_count, 
                           correct_count, accuracy, error_distribution
                    FROM daily_statistics
                    WHERE stat_date >= %s AND stat_date <= %s AND subject_id = %s
                    ORDER BY stat_date ASC
                """
                rows = AppDatabaseService.execute_query(sql, (start_date, end_date, subject_id))
                
                for row in rows:
                    result['trends'].append({
                        'date': row['stat_date'].isoformat() if hasattr(row['stat_date'], 'isoformat') else str(row['stat_date']),
                        'accuracy': float(row['accuracy']) if row['accuracy'] else 0,
                        'task_count': row['task_count'] or 0,
                        'question_count': row['question_count'] or 0
                    })
            
            # 如果数据库中没有数据，从批量任务实时计算
            if not result['trends']:
                result = DashboardService._calculate_trends_from_tasks(days, subject_id)
            
            return result
            
        except Exception as e:
            print(f"[Dashboard] 获取趋势数据失败: {e}")
            return {
                'trends': [],
                'by_subject': {}
            }
    
    @staticmethod
    def _calculate_trends_from_tasks(days: int, subject_id: int = None) -> Dict[str, Any]:
        """
        从批量任务实时计算趋势数据
        
        当 daily_statistics 表中没有数据时使用。
        
        Args:
            days: 时间范围
            subject_id: 学科ID筛选
            
        Returns:
            dict: 趋势数据
        """
        result = {
            'trends': [],
            'by_subject': {}
        }
        
        try:
            # 加载所有批量任务
            all_tasks = DashboardService._load_all_batch_tasks()
            
            # 获取数据集信息
            datasets = StorageService.get_all_datasets_summary()
            dataset_subject_map = {ds['dataset_id']: ds.get('subject_id') for ds in datasets}
            
            # 按日期分组统计
            end_date = datetime.now().date()
            daily_stats = {}
            
            for i in range(days):
                date = (end_date - timedelta(days=i)).isoformat()
                daily_stats[date] = {
                    'question_count': 0,
                    'correct_count': 0,
                    'task_count': 0,
                    'by_subject': {}
                }
            
            for task in all_tasks:
                created_at = task.get('created_at', '')
                if not created_at:
                    continue
                
                try:
                    task_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if task_time.tzinfo:
                        task_time = task_time.replace(tzinfo=None)
                    task_date = task_time.date().isoformat()
                except:
                    continue
                
                if task_date not in daily_stats:
                    continue
                
                daily_stats[task_date]['task_count'] += 1
                
                for hw_item in task.get('homework_items', []):
                    # 确定学科
                    hw_subject_id = None
                    matched_dataset = hw_item.get('matched_dataset')
                    if matched_dataset and matched_dataset in dataset_subject_map:
                        hw_subject_id = dataset_subject_map[matched_dataset]
                    
                    # 如果指定了学科筛选，跳过不匹配的
                    if subject_id is not None and hw_subject_id != subject_id:
                        continue
                    
                    evaluation = hw_item.get('evaluation') or {}
                    q_count = evaluation.get('total_questions', 0)
                    c_count = evaluation.get('correct_count', 0)
                    
                    daily_stats[task_date]['question_count'] += q_count
                    daily_stats[task_date]['correct_count'] += c_count
                    
                    # 按学科统计
                    if hw_subject_id is not None:
                        sid = str(hw_subject_id)
                        if sid not in daily_stats[task_date]['by_subject']:
                            daily_stats[task_date]['by_subject'][sid] = {
                                'question_count': 0,
                                'correct_count': 0
                            }
                        daily_stats[task_date]['by_subject'][sid]['question_count'] += q_count
                        daily_stats[task_date]['by_subject'][sid]['correct_count'] += c_count
            
            # 转换为趋势数据格式
            for date in sorted(daily_stats.keys()):
                stats = daily_stats[date]
                accuracy = 0
                if stats['question_count'] > 0:
                    accuracy = round(stats['correct_count'] / stats['question_count'], 4)
                
                result['trends'].append({
                    'date': date,
                    'accuracy': accuracy,
                    'task_count': stats['task_count'],
                    'question_count': stats['question_count']
                })
                
                # 按学科统计
                for sid, s_stats in stats['by_subject'].items():
                    if sid not in result['by_subject']:
                        result['by_subject'][sid] = []
                    
                    s_accuracy = 0
                    if s_stats['question_count'] > 0:
                        s_accuracy = round(s_stats['correct_count'] / s_stats['question_count'], 4)
                    
                    result['by_subject'][sid].append({
                        'date': date,
                        'accuracy': s_accuracy
                    })
            
        except Exception as e:
            print(f"[Dashboard] 从任务计算趋势数据失败: {e}")
        
        return result
    
    @staticmethod
    def export_trends_csv(days: int = 30, subject_id: int = None) -> str:
        """
        导出趋势数据为 CSV (US-15, 10.2.3)
        
        Args:
            days: 时间范围
            subject_id: 学科ID筛选
            
        Returns:
            str: CSV 文件路径
        """
        import csv
        import os
        
        try:
            # 获取趋势数据
            trends_data = DashboardService.get_trends(days, subject_id)
            
            # 确保导出目录存在
            export_dir = 'exports'
            StorageService.ensure_dir(export_dir)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            subject_suffix = f'_subject{subject_id}' if subject_id is not None else ''
            filename = f'trends_{days}days{subject_suffix}_{timestamp}.csv'
            filepath = os.path.join(export_dir, filename)
            
            # 写入 CSV
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                # 写入表头
                writer.writerow(['日期', '准确率', '任务数', '题目数'])
                
                # 写入数据
                for item in trends_data.get('trends', []):
                    writer.writerow([
                        item.get('date', ''),
                        f"{item.get('accuracy', 0) * 100:.2f}%",
                        item.get('task_count', 0),
                        item.get('question_count', 0)
                    ])
            
            return filepath
            
        except Exception as e:
            print(f"[Dashboard] 导出趋势数据失败: {e}")
            raise

    # ========== 智能搜索 (US-32) ==========
    
    @staticmethod
    def search(query: str, search_type: str = 'all') -> Dict[str, Any]:
        """
        智能搜索 (US-32)
        
        搜索任务名、数据集名、书本名、题号等内容，返回匹配结果并高亮关键词。
        
        Args:
            query: 搜索关键词
            search_type: 搜索类型 all|task|dataset|book|question
            
        Returns:
            dict: 包含搜索结果列表
                - results: [{type, id, name, highlight}]
        """
        results = []
        
        if not query or len(query.strip()) < 1:
            return {'results': results}
        
        query = query.strip()
        query_lower = query.lower()
        
        try:
            # 搜索批量任务 (task)
            if search_type in ['all', 'task']:
                task_results = DashboardService._search_tasks(query, query_lower)
                results.extend(task_results)
            
            # 搜索数据集 (dataset)
            if search_type in ['all', 'dataset']:
                dataset_results = DashboardService._search_datasets(query, query_lower)
                results.extend(dataset_results)
            
            # 搜索书本 (book) - 从数据集和任务中提取
            if search_type in ['all', 'book']:
                book_results = DashboardService._search_books(query, query_lower)
                results.extend(book_results)
            
            # 搜索题号 (question) - 从错误样本中搜索
            if search_type in ['all', 'question']:
                question_results = DashboardService._search_questions(query, query_lower)
                results.extend(question_results)
            
            # 去重并限制结果数量
            seen = set()
            unique_results = []
            for r in results:
                key = f"{r['type']}_{r['id']}"
                if key not in seen:
                    seen.add(key)
                    unique_results.append(r)
                    if len(unique_results) >= 20:  # 最多返回20条结果
                        break
            
            return {'results': unique_results}
            
        except Exception as e:
            print(f"[Dashboard] 搜索失败: {e}")
            return {'results': []}
    
    @staticmethod
    def _search_tasks(query: str, query_lower: str) -> List[Dict[str, Any]]:
        """
        搜索批量任务
        
        Args:
            query: 原始搜索关键词
            query_lower: 小写搜索关键词
            
        Returns:
            list: 匹配的任务列表
        """
        results = []
        
        try:
            # 加载所有批量任务
            all_tasks = DashboardService._load_all_batch_tasks()
            
            for task in all_tasks:
                task_name = task.get('name', '')
                task_id = task.get('task_id', '')
                
                # 检查任务名是否匹配
                if query_lower in task_name.lower():
                    results.append({
                        'type': 'task',
                        'id': task_id,
                        'name': task_name,
                        'highlight': DashboardService._highlight_text(task_name, query)
                    })
                    
                    if len(results) >= 10:  # 每种类型最多10条
                        break
                        
        except Exception as e:
            print(f"[Dashboard] 搜索任务失败: {e}")
        
        return results
    
    @staticmethod
    def _search_datasets(query: str, query_lower: str) -> List[Dict[str, Any]]:
        """
        搜索数据集
        
        Args:
            query: 原始搜索关键词
            query_lower: 小写搜索关键词
            
        Returns:
            list: 匹配的数据集列表
        """
        results = []
        
        try:
            # 获取所有数据集
            all_datasets = StorageService.get_all_datasets_summary()
            
            for ds in all_datasets:
                ds_name = ds.get('name', '')
                ds_id = ds.get('dataset_id', '')
                book_name = ds.get('book_name', '')
                
                # 检查数据集名或书本名是否匹配
                if query_lower in ds_name.lower() or query_lower in book_name.lower():
                    # 优先高亮数据集名，如果数据集名不匹配则高亮书本名
                    if query_lower in ds_name.lower():
                        highlight = DashboardService._highlight_text(ds_name, query)
                    else:
                        highlight = DashboardService._highlight_text(book_name, query)
                    
                    results.append({
                        'type': 'dataset',
                        'id': ds_id,
                        'name': ds_name,
                        'highlight': highlight
                    })
                    
                    if len(results) >= 10:
                        break
                        
        except Exception as e:
            print(f"[Dashboard] 搜索数据集失败: {e}")
        
        return results
    
    @staticmethod
    def _search_books(query: str, query_lower: str) -> List[Dict[str, Any]]:
        """
        搜索书本
        
        从数据集和批量任务中提取书本信息进行搜索。
        
        Args:
            query: 原始搜索关键词
            query_lower: 小写搜索关键词
            
        Returns:
            list: 匹配的书本列表
        """
        results = []
        seen_books = set()
        
        try:
            # 从数据集中提取书本
            all_datasets = StorageService.get_all_datasets_summary()
            
            for ds in all_datasets:
                book_name = ds.get('book_name', '')
                book_id = ds.get('book_id', '')
                
                if not book_name or book_id in seen_books:
                    continue
                
                if query_lower in book_name.lower():
                    seen_books.add(book_id)
                    results.append({
                        'type': 'book',
                        'id': book_id,
                        'name': book_name,
                        'highlight': DashboardService._highlight_text(book_name, query)
                    })
                    
                    if len(results) >= 10:
                        break
            
            # 如果结果不足，从批量任务中补充
            if len(results) < 10:
                all_tasks = DashboardService._load_all_batch_tasks()
                
                for task in all_tasks:
                    for hw_item in task.get('homework_items', []):
                        book_name = hw_item.get('book_name', '')
                        book_id = hw_item.get('book_id', '')
                        
                        if not book_name or book_id in seen_books:
                            continue
                        
                        if query_lower in book_name.lower():
                            seen_books.add(book_id)
                            results.append({
                                'type': 'book',
                                'id': book_id,
                                'name': book_name,
                                'highlight': DashboardService._highlight_text(book_name, query)
                            })
                            
                            if len(results) >= 10:
                                break
                    
                    if len(results) >= 10:
                        break
                        
        except Exception as e:
            print(f"[Dashboard] 搜索书本失败: {e}")
        
        return results
    
    @staticmethod
    def _search_questions(query: str, query_lower: str) -> List[Dict[str, Any]]:
        """
        搜索题号
        
        从批量任务的评估错误中搜索题号。
        
        Args:
            query: 原始搜索关键词
            query_lower: 小写搜索关键词
            
        Returns:
            list: 匹配的题目列表
        """
        results = []
        seen_questions = set()
        
        try:
            # 从批量任务中搜索题号
            all_tasks = DashboardService._load_all_batch_tasks()
            
            for task in all_tasks:
                task_id = task.get('task_id', '')
                
                for hw_item in task.get('homework_items', []):
                    evaluation = hw_item.get('evaluation') or {}
                    errors = evaluation.get('errors') or []
                    book_name = hw_item.get('book_name', '')
                    page_num = hw_item.get('page_num', '')
                    
                    for error in errors:
                        index = str(error.get('index', ''))
                        
                        if not index:
                            continue
                        
                        # 检查题号是否匹配
                        if query_lower in index.lower():
                            # 生成唯一键避免重复
                            unique_key = f"{book_name}_{page_num}_{index}"
                            if unique_key in seen_questions:
                                continue
                            
                            seen_questions.add(unique_key)
                            display_name = f"第{index}题 - {book_name} P{page_num}"
                            
                            results.append({
                                'type': 'question',
                                'id': task_id,  # 关联到任务
                                'name': display_name,
                                'highlight': DashboardService._highlight_text(display_name, query)
                            })
                            
                            if len(results) >= 10:
                                break
                    
                    if len(results) >= 10:
                        break
                
                if len(results) >= 10:
                    break
                    
        except Exception as e:
            print(f"[Dashboard] 搜索题号失败: {e}")
        
        return results
    
    @staticmethod
    def _highlight_text(text: str, query: str) -> str:
        """
        高亮文本中的匹配关键词 (US-32.4)
        
        使用 <mark> 标签包裹匹配的关键词。
        
        Args:
            text: 原始文本
            query: 搜索关键词
            
        Returns:
            str: 高亮后的文本
        """
        if not text or not query:
            return text
        
        import re
        
        # 使用正则表达式进行大小写不敏感的替换
        # 保留原始大小写
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        
        def replace_with_mark(match):
            return f'<mark>{match.group(0)}</mark>'
        
        return pattern.sub(replace_with_mark, text)


    # ========== 高级分析工具服务方法 ==========
    
    @staticmethod
    def get_advanced_tools_stats() -> Dict[str, Any]:
        """
        获取高级分析工具统计数据
        
        从批量评估任务中聚合各工具的统计数据。
        
        Returns:
            dict: 包含各工具统计数据
        """
        cache_key = 'advanced_tools_stats'
        cached = DashboardService.get_cached(cache_key)
        if cached is not None:
            return cached
        
        result = {
            'error_samples': {
                'total': 0,
                'pending': 0,
                'analyzed': 0,
                'fixed': 0
            },
            'anomalies': {
                'total': 0,
                'unconfirmed': 0,
                'today': 0
            },
            'clusters': {
                'total': 0
            },
            'suggestions': {
                'total': 0,
                'pending': 0
            }
        }
        
        try:
            all_tasks = DashboardService._load_all_batch_tasks()
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 统计错误样本（AI评分与期望评分不一致的作业）
            error_types_count = {}
            
            for task in all_tasks:
                task_time_str = task.get('created_at', '')
                is_today = False
                if task_time_str:
                    try:
                        task_time = datetime.fromisoformat(task_time_str.replace('Z', '+00:00'))
                        if task_time.tzinfo:
                            task_time = task_time.replace(tzinfo=None)
                        is_today = task_time >= today
                    except:
                        pass
                
                for hw_item in task.get('homework_items', []):
                    if hw_item.get('status') != 'completed':
                        continue
                    
                    evaluation = hw_item.get('evaluation') or {}
                    errors = evaluation.get('errors') or []
                    
                    for error in errors:
                        result['error_samples']['total'] += 1
                        result['error_samples']['pending'] += 1  # 默认待分析
                        
                        # 统计错误类型用于聚类
                        error_type = error.get('error_type', '其他')
                        error_types_count[error_type] = error_types_count.get(error_type, 0) + 1
                        
                        # 检测异常（评分偏差过大）
                        ai_score = error.get('ai_score', 0)
                        expected_score = error.get('expected_score', 0)
                        if abs(ai_score - expected_score) > 5:
                            result['anomalies']['total'] += 1
                            result['anomalies']['unconfirmed'] += 1
                            if is_today:
                                result['anomalies']['today'] += 1
            
            # 聚类数量 = 不同错误类型的数量
            result['clusters']['total'] = len(error_types_count)
            
            # 建议数量 = 基于错误类型生成的建议
            result['suggestions']['total'] = min(len(error_types_count), 10)
            result['suggestions']['pending'] = result['suggestions']['total']
            
            DashboardService.set_cached(cache_key, result, ttl=60)
            
        except Exception as e:
            print(f"[Dashboard] 获取高级工具统计失败: {e}")
        
        return result
    
    @staticmethod
    def get_batch_tasks_for_compare() -> List[Dict[str, Any]]:
        """
        获取可用于对比的批量评估任务列表
        
        Returns:
            list: 任务列表
        """
        result = []
        
        try:
            all_tasks = DashboardService._load_all_batch_tasks()
            
            for task in all_tasks:
                if task.get('status') != 'completed':
                    continue
                
                overall_report = task.get('overall_report') or {}
                
                # 推断学科
                subject_id = None
                subject_name = '未知'
                for hw_item in task.get('homework_items', []):
                    book_name = hw_item.get('book_name', '')
                    inferred = DashboardService._infer_subject_from_book_name(book_name)
                    if inferred is not None:
                        subject_id = inferred
                        subject_name = SUBJECT_MAP.get(subject_id, '未知')
                        break
                
                result.append({
                    'task_id': task.get('task_id', ''),
                    'name': task.get('name', ''),
                    'subject_id': subject_id,
                    'subject_name': subject_name,
                    'accuracy': overall_report.get('overall_accuracy', 0),
                    'total_questions': overall_report.get('total_questions', 0),
                    'created_at': task.get('created_at', '')
                })
            
            # 按创建时间倒序
            result.sort(key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            print(f"[Dashboard] 获取批量任务列表失败: {e}")
        
        return result
    
    @staticmethod
    def get_batch_compare(task_id_1: str, task_id_2: str) -> Dict[str, Any]:
        """
        对比两个批量评估任务的评估结果
        
        Args:
            task_id_1: 第一个任务ID
            task_id_2: 第二个任务ID
            
        Returns:
            dict: 对比结果
        """
        def load_task_data(task_id: str) -> Dict[str, Any]:
            """加载单个任务的数据"""
            filepath = os.path.join(StorageService.BATCH_TASKS_DIR, f'{task_id}.json')
            if not os.path.exists(filepath):
                raise ValueError(f'任务不存在: {task_id}')
            
            with open(filepath, 'r', encoding='utf-8') as f:
                task = json.load(f)
            
            overall_report = task.get('overall_report') or {}
            
            # 统计错误类型分布
            error_distribution = {}
            for hw_item in task.get('homework_items', []):
                evaluation = hw_item.get('evaluation') or {}
                for error in evaluation.get('errors') or []:
                    error_type = error.get('error_type', '其他')
                    error_distribution[error_type] = error_distribution.get(error_type, 0) + 1
            
            return {
                'task_id': task.get('task_id', ''),
                'name': task.get('name', ''),
                'accuracy': overall_report.get('overall_accuracy', 0),
                'total_questions': overall_report.get('total_questions', 0),
                'correct_count': overall_report.get('correct_questions', 0),
                'error_distribution': error_distribution,
                'created_at': task.get('created_at', '')
            }
        
        task1 = load_task_data(task_id_1)
        task2 = load_task_data(task_id_2)
        
        # 计算对比结果
        accuracy_diff = round(task2['accuracy'] - task1['accuracy'], 4)
        
        # 计算错误类型变化
        all_error_types = set(task1['error_distribution'].keys()) | set(task2['error_distribution'].keys())
        error_changes = {}
        for error_type in all_error_types:
            count1 = task1['error_distribution'].get(error_type, 0)
            count2 = task2['error_distribution'].get(error_type, 0)
            error_changes[error_type] = count2 - count1
        
        return {
            'task1': task1,
            'task2': task2,
            'comparison': {
                'accuracy_diff': accuracy_diff,
                'improvement': accuracy_diff > 0,
                'error_changes': error_changes
            }
        }
    
    @staticmethod
    def get_drilldown(dimension: str, parent_id: str = None) -> Dict[str, Any]:
        """
        获取数据下钻分析结果
        
        基于批量评估任务数据进行多维度聚合分析。
        
        Args:
            dimension: 维度 subject|book|page|question_type
            parent_id: 父级ID，用于下钻
            
        Returns:
            dict: 下钻数据
        """
        result = {
            'dimension': dimension,
            'parent_id': parent_id,
            'items': []
        }
        
        try:
            all_tasks = DashboardService._load_all_batch_tasks()
            
            # 聚合数据
            aggregated = {}
            
            for task in all_tasks:
                for hw_item in task.get('homework_items', []):
                    if hw_item.get('status') != 'completed':
                        continue
                    
                    evaluation = hw_item.get('evaluation') or {}
                    total_questions = evaluation.get('total_questions', 0)
                    correct_count = evaluation.get('correct_count', 0)
                    error_count = total_questions - correct_count
                    
                    book_name = hw_item.get('book_name', '')
                    page_num = hw_item.get('page_num', '')
                    subject_id = DashboardService._infer_subject_from_book_name(book_name)
                    
                    # 根据维度聚合
                    if dimension == 'subject':
                        if subject_id is None:
                            continue
                        key = str(subject_id)
                        name = SUBJECT_MAP.get(subject_id, '未知')
                        has_children = True
                    elif dimension == 'book':
                        # 如果有 parent_id，筛选学科
                        if parent_id and subject_id != int(parent_id):
                            continue
                        key = book_name
                        name = book_name
                        has_children = True
                    elif dimension == 'page':
                        # 如果有 parent_id，筛选书本
                        if parent_id and book_name != parent_id:
                            continue
                        key = f"{book_name}_P{page_num}"
                        name = f"第{page_num}页"
                        has_children = False
                    elif dimension == 'question_type':
                        # 按错误类型聚合
                        for error in evaluation.get('errors') or []:
                            error_type = error.get('error_type', '其他')
                            if error_type not in aggregated:
                                aggregated[error_type] = {
                                    'id': error_type,
                                    'name': error_type,
                                    'total_questions': 0,
                                    'correct_count': 0,
                                    'error_count': 0,
                                    'has_children': False
                                }
                            aggregated[error_type]['error_count'] += 1
                        continue
                    else:
                        continue
                    
                    if key not in aggregated:
                        aggregated[key] = {
                            'id': key,
                            'name': name,
                            'total_questions': 0,
                            'correct_count': 0,
                            'error_count': 0,
                            'has_children': has_children
                        }
                    
                    aggregated[key]['total_questions'] += total_questions
                    aggregated[key]['correct_count'] += correct_count
                    aggregated[key]['error_count'] += error_count
            
            # 计算准确率并排序
            items = list(aggregated.values())
            for item in items:
                if item['total_questions'] > 0:
                    item['accuracy'] = round(item['correct_count'] / item['total_questions'], 4)
                else:
                    item['accuracy'] = 0
            
            # 按错误数降序排列
            items.sort(key=lambda x: x['error_count'], reverse=True)
            result['items'] = items
            
        except Exception as e:
            print(f"[Dashboard] 获取数据下钻失败: {e}")
        
        return result
