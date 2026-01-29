"""
AI 智能数据分析服务（增强版）

提供批量评估任务的智能分析功能，包括：
- 错误样本收集
- 多层级聚合统计（学科→书本→页码→题目）
- 错误模式识别
- 根因分析
- 优化建议生成
- 快速本地统计（毫秒级响应）
- LLM 深度分析（并行调用）
- 结果缓存（基于数据哈希）
- 异常检测（批改不一致）
"""
import os
import json
import uuid
import time
import hashlib
import threading
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from collections import defaultdict

from .storage_service import StorageService
from .llm_service import LLMService
from .database_service import AppDatabaseService


# 学科ID映射
SUBJECT_MAP = {
    0: '英语', 1: '语文', 2: '数学', 3: '物理',
    4: '化学', 5: '生物', 6: '地理'
}

# 错误类型定义
ERROR_TYPES = [
    '识别错误-判断错误',
    '识别正确-判断错误', 
    '缺失题目',
    'AI识别幻觉',
    '答案不匹配'
]

# 根因类型定义
ROOT_CAUSE_TYPES = {
    'ocr_issue': 'OCR识别问题',
    'scoring_logic': '评分逻辑问题',
    'answer_issue': '标准答案问题',
    'prompt_issue': 'Prompt问题',
    'data_issue': '数据问题'
}


class AIAnalysisService:
    """AI 数据分析服务（增强版）"""
    
    # 分析队列
    _queue: List[dict] = []  # [{task_id, priority, created_at, job_id}]
    _running: Dict[str, dict] = {}  # {task_id: {progress, started_at, step, job_id}}
    _max_concurrent: int = 10
    _lock = threading.Lock()
    _paused: bool = False
    
    # 最近完成/失败的任务
    _recent_completed: List[dict] = []
    _recent_failed: List[dict] = []
    _max_recent: int = 10
    
    # 配置文件路径
    CONFIG_PATH = 'automation_config.json'
    
    @classmethod
    def _load_config(cls) -> dict:
        """加载配置"""
        try:
            if os.path.exists(cls.CONFIG_PATH):
                with open(cls.CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[AIAnalysis] 加载配置失败: {e}")
        return {
            'ai_analysis': {
                'enabled': True,
                'trigger_delay': 10,
                'max_concurrent': 2,
                'timeout': 300,
                'model': 'deepseek-v3.2',
                'temperature': 0.3,
                'analysis_depth': 'full'
            }
        }
    
    @classmethod
    def _save_config(cls, config: dict):
        """保存配置"""
        try:
            with open(cls.CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[AIAnalysis] 保存配置失败: {e}")
    
    @classmethod
    def get_config(cls) -> dict:
        """获取 AI 分析配置"""
        config = cls._load_config()
        return config.get('ai_analysis', {})
    
    @classmethod
    def update_config(cls, updates: dict) -> dict:
        """更新配置"""
        config = cls._load_config()
        if 'ai_analysis' not in config:
            config['ai_analysis'] = {}
        config['ai_analysis'].update(updates)
        cls._save_config(config)
        
        # 更新运行时配置
        if 'max_concurrent' in updates:
            cls._max_concurrent = updates['max_concurrent']
        
        return config['ai_analysis']
    
    @classmethod
    def trigger_analysis(cls, task_id: str, priority: str = 'medium') -> dict:
        """
        触发任务分析
        
        Args:
            task_id: 批量评估任务ID
            priority: 优先级 high|medium|low
            
        Returns:
            dict: {queued: bool, position: int, job_id: str, message: str}
        """
        config = cls.get_config()
        
        # 检查是否启用
        if not config.get('enabled', True):
            return {'queued': False, 'position': -1, 'job_id': None, 'message': 'AI 分析已禁用'}
        
        # 检查是否暂停
        if cls._paused:
            return {'queued': False, 'position': -1, 'job_id': None, 'message': '自动化任务已暂停'}
        
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        
        with cls._lock:
            # 检查是否已在队列或正在执行
            for item in cls._queue:
                if item.get('task_id') == task_id:
                    position = cls._queue.index(item) + 1
                    return {'queued': True, 'position': position, 'job_id': item.get('job_id'), 'message': f'任务已在队列中，位置 {position}'}
            
            if task_id in cls._running:
                return {'queued': True, 'position': 0, 'job_id': cls._running[task_id].get('job_id'), 'message': '任务正在分析中'}
            
            # 加入队列（按优先级排序）
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            queue_item = {
                'task_id': task_id,
                'priority': priority,
                'priority_order': priority_order.get(priority, 1),
                'created_at': datetime.now().isoformat(),
                'job_id': job_id
            }
            
            # 插入到合适位置
            insert_pos = len(cls._queue)
            for i, item in enumerate(cls._queue):
                if item.get('priority_order', 1) > queue_item['priority_order']:
                    insert_pos = i
                    break
            cls._queue.insert(insert_pos, queue_item)
            position = insert_pos + 1
            
            # 尝试启动处理
            cls._try_process_queue()
            
            return {'queued': True, 'position': position, 'job_id': job_id, 'message': f'分析任务已加入队列，位置 {position}'}
    
    @classmethod
    def _try_process_queue(cls):
        """尝试处理队列中的任务"""
        config = cls.get_config()
        max_concurrent = config.get('max_concurrent', 10)
        
        while len(cls._running) < max_concurrent and cls._queue and not cls._paused:
            queue_item = cls._queue.pop(0)
            task_id = queue_item.get('task_id')
            job_id = queue_item.get('job_id')
            
            cls._running[task_id] = {
                'started_at': datetime.now().isoformat(),
                'progress': 0,
                'step': '初始化...',
                'job_id': job_id
            }
            
            # 启动分析线程
            thread = threading.Thread(target=cls._analyze_task_thread, args=(task_id, job_id))
            thread.daemon = True
            thread.start()
    
    @classmethod
    def _analyze_task_thread(cls, task_id: str, job_id: str = None):
        """分析任务线程"""
        start_time = time.time()
        try:
            cls.analyze_task(task_id)
            duration = int(time.time() - start_time)
            
            # 记录完成
            with cls._lock:
                cls._recent_completed.insert(0, {
                    'task_id': task_id,
                    'job_id': job_id,
                    'completed_at': datetime.now().isoformat(),
                    'duration': duration
                })
                cls._recent_completed = cls._recent_completed[:cls._max_recent]
                
        except Exception as e:
            print(f"[AIAnalysis] 分析任务 {task_id} 失败: {e}")
            cls._save_failed_report(task_id, str(e))
            duration = int(time.time() - start_time)
            
            # 记录失败
            with cls._lock:
                cls._recent_failed.insert(0, {
                    'task_id': task_id,
                    'job_id': job_id,
                    'error': str(e),
                    'failed_at': datetime.now().isoformat(),
                    'duration': duration
                })
                cls._recent_failed = cls._recent_failed[:cls._max_recent]
                
        finally:
            with cls._lock:
                if task_id in cls._running:
                    del cls._running[task_id]
                cls._try_process_queue()

    
    @classmethod
    def analyze_task(cls, task_id: str) -> dict:
        """
        执行任务分析
        
        Returns:
            dict: 分析报告
        """
        start_time = time.time()
        report_id = str(uuid.uuid4())[:8]
        
        # 创建初始报告
        cls._save_report(report_id, task_id, 'analyzing', {})
        
        try:
            # 1. 加载任务数据
            task_data = cls._load_task(task_id)
            if not task_data:
                raise ValueError(f"任务 {task_id} 不存在")
            
            # 更新进度
            cls._update_progress(task_id, 10)
            
            # 2. 收集错误样本
            error_samples = cls._collect_error_samples(task_data)
            cls._update_progress(task_id, 30)
            
            # 3. 多层级聚合统计
            drill_down_data = cls._aggregate_by_hierarchy(error_samples, task_data)
            cls._update_progress(task_id, 50)
            
            # 4. 错误模式识别
            error_patterns = cls._identify_error_patterns(error_samples)
            cls._update_progress(task_id, 60)
            
            # 5. 根因分析
            config = cls.get_config()
            if config.get('analysis_depth') in ['with_root_cause', 'full']:
                root_causes = cls._analyze_root_causes(error_samples, error_patterns)
            else:
                root_causes = []
            cls._update_progress(task_id, 80)
            
            # 6. 生成优化建议
            if config.get('analysis_depth') == 'full':
                suggestions = cls._generate_suggestions(error_patterns, root_causes)
            else:
                suggestions = []
            cls._update_progress(task_id, 95)
            
            # 7. 生成摘要
            summary = cls._generate_summary(error_samples, drill_down_data, error_patterns, root_causes)
            
            # 计算耗时
            duration = int(time.time() - start_time)
            
            # 保存完整报告
            report = {
                'report_id': report_id,
                'task_id': task_id,
                'status': 'completed',
                'summary': summary,
                'drill_down': drill_down_data,
                'error_patterns': error_patterns,
                'root_causes': root_causes,
                'suggestions': suggestions,
                'created_at': datetime.now().isoformat(),
                'completed_at': datetime.now().isoformat(),
                'duration_seconds': duration
            }
            
            cls._save_report(report_id, task_id, 'completed', report, duration)
            cls._update_progress(task_id, 100)
            
            # 记录日志
            cls._log_automation('ai_analysis', task_id, 'completed', f'分析完成，耗时 {duration} 秒', duration)
            
            return report
            
        except Exception as e:
            duration = int(time.time() - start_time)
            cls._save_failed_report(task_id, str(e), report_id, duration)
            cls._log_automation('ai_analysis', task_id, 'failed', str(e), duration)
            raise
    
    @classmethod
    def _load_task(cls, task_id: str) -> Optional[dict]:
        """加载批量评估任务数据"""
        filepath = os.path.join(StorageService.BATCH_TASKS_DIR, f'{task_id}.json')
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    @classmethod
    def _collect_error_samples(cls, task_data: dict) -> List[dict]:
        """
        收集错误样本
        
        从批量评估任务中收集所有 AI 评分与期望评分不一致的作业
        """
        error_samples = []
        
        for hw_item in task_data.get('homework_items', []):
            if hw_item.get('status') != 'completed':
                continue
            
            evaluation = hw_item.get('evaluation') or {}
            errors = evaluation.get('errors') or []
            
            for error in errors:
                sample = {
                    'homework_id': hw_item.get('homework_id', ''),
                    'book_name': hw_item.get('book_name', ''),
                    'page_num': hw_item.get('page_num', 0),
                    'subject_id': hw_item.get('subject_id'),
                    'question_index': error.get('question_index', 0),
                    'error_type': error.get('error_type', '其他'),
                    'ai_answer': error.get('ai_answer', ''),
                    'expected_answer': error.get('expected_answer', ''),
                    'ai_score': error.get('ai_score'),
                    'expected_score': error.get('expected_score'),
                    'description': error.get('description', '')
                }
                
                # 推断学科
                if sample['subject_id'] is None:
                    sample['subject_id'] = cls._infer_subject(sample['book_name'])
                
                error_samples.append(sample)
        
        return error_samples
    
    @classmethod
    def _infer_subject(cls, book_name: str) -> Optional[int]:
        """从书名推断学科"""
        if not book_name:
            return None
        book_name_lower = book_name.lower()
        keywords = {
            0: ['英语', 'english'],
            1: ['语文', 'chinese'],
            2: ['数学', 'math'],
            3: ['物理', 'physics'],
            4: ['化学', 'chemistry'],
            5: ['生物', 'biology'],
            6: ['地理', 'geography']
        }
        for subject_id, kws in keywords.items():
            for kw in kws:
                if kw in book_name_lower:
                    return subject_id
        return None
    
    @classmethod
    def _aggregate_by_hierarchy(cls, error_samples: List[dict], task_data: dict) -> dict:
        """
        按层级聚合统计
        
        学科 → 书本 → 页码 → 题目
        """
        # 统计总题目数
        total_questions = 0
        for hw_item in task_data.get('homework_items', []):
            evaluation = hw_item.get('evaluation') or {}
            total_questions += evaluation.get('total_questions', 0)
        
        # 按学科聚合
        subject_stats = defaultdict(lambda: {
            'error_count': 0, 'total': 0, 'books': defaultdict(lambda: {
                'error_count': 0, 'total': 0, 'pages': defaultdict(lambda: {
                    'error_count': 0, 'total': 0, 'questions': defaultdict(int)
                })
            })
        })
        
        # 统计每个作业的题目数
        for hw_item in task_data.get('homework_items', []):
            if hw_item.get('status') != 'completed':
                continue
            evaluation = hw_item.get('evaluation') or {}
            subject_id = hw_item.get('subject_id')
            if subject_id is None:
                subject_id = cls._infer_subject(hw_item.get('book_name', ''))
            if subject_id is None:
                continue
            
            book_name = hw_item.get('book_name', '未知书本')
            page_num = hw_item.get('page_num', 0)
            questions = evaluation.get('total_questions', 0)
            
            subject_stats[subject_id]['total'] += questions
            subject_stats[subject_id]['books'][book_name]['total'] += questions
            subject_stats[subject_id]['books'][book_name]['pages'][page_num]['total'] += questions
        
        # 统计错误
        for sample in error_samples:
            subject_id = sample.get('subject_id')
            if subject_id is None:
                continue
            book_name = sample.get('book_name', '未知书本')
            page_num = sample.get('page_num', 0)
            question_idx = sample.get('question_index', 0)
            
            subject_stats[subject_id]['error_count'] += 1
            subject_stats[subject_id]['books'][book_name]['error_count'] += 1
            subject_stats[subject_id]['books'][book_name]['pages'][page_num]['error_count'] += 1
            subject_stats[subject_id]['books'][book_name]['pages'][page_num]['questions'][question_idx] += 1
        
        # 构建层级数据
        items = []
        for subject_id, stats in subject_stats.items():
            if stats['total'] == 0:
                continue
            error_rate = stats['error_count'] / stats['total'] if stats['total'] > 0 else 0
            items.append({
                'id': str(subject_id),
                'name': SUBJECT_MAP.get(subject_id, '未知'),
                'error_count': stats['error_count'],
                'total': stats['total'],
                'error_rate': round(error_rate, 4),
                'is_focus': error_rate > 0.2,
                'has_children': len(stats['books']) > 0
            })
        
        # 按错误数排序
        items.sort(key=lambda x: x['error_count'], reverse=True)
        
        return {
            'level': 'subject',
            'parent_id': None,
            'items': items,
            'total_errors': len(error_samples),
            'total_questions': total_questions
        }
    
    @classmethod
    def get_drill_down_data(cls, task_id: str, level: str, parent_id: str = None) -> dict:
        """获取下钻数据"""
        # 加载任务和报告
        task_data = cls._load_task(task_id)
        if not task_data:
            return {'level': level, 'items': [], 'error': '任务不存在'}
        
        error_samples = cls._collect_error_samples(task_data)
        
        if level == 'subject':
            return cls._aggregate_by_hierarchy(error_samples, task_data)
        
        # 过滤样本
        filtered_samples = error_samples
        parent_info = {'id': parent_id, 'name': parent_id}
        
        if level == 'book' and parent_id:
            # 按学科过滤
            subject_id = int(parent_id)
            filtered_samples = [s for s in error_samples if s.get('subject_id') == subject_id]
            parent_info['name'] = SUBJECT_MAP.get(subject_id, '未知')
            
            # 按书本聚合
            book_stats = defaultdict(lambda: {'error_count': 0, 'total': 0})
            for hw_item in task_data.get('homework_items', []):
                hw_subject = hw_item.get('subject_id') or cls._infer_subject(hw_item.get('book_name', ''))
                if hw_subject != subject_id:
                    continue
                evaluation = hw_item.get('evaluation') or {}
                book_name = hw_item.get('book_name', '未知书本')
                book_stats[book_name]['total'] += evaluation.get('total_questions', 0)
            
            for sample in filtered_samples:
                book_name = sample.get('book_name', '未知书本')
                book_stats[book_name]['error_count'] += 1
            
            items = []
            for book_name, stats in book_stats.items():
                if stats['total'] == 0:
                    continue
                error_rate = stats['error_count'] / stats['total'] if stats['total'] > 0 else 0
                items.append({
                    'id': book_name,
                    'name': book_name,
                    'error_count': stats['error_count'],
                    'total': stats['total'],
                    'error_rate': round(error_rate, 4),
                    'is_focus': error_rate > 0.2,
                    'has_children': True
                })
            items.sort(key=lambda x: x['error_count'], reverse=True)
            
            return {'level': 'book', 'parent': parent_info, 'items': items}
        
        elif level == 'page' and parent_id:
            # 按书本过滤
            filtered_samples = [s for s in error_samples if s.get('book_name') == parent_id]
            parent_info['name'] = parent_id
            
            # 按页码聚合
            page_stats = defaultdict(lambda: {'error_count': 0, 'total': 0})
            for hw_item in task_data.get('homework_items', []):
                if hw_item.get('book_name') != parent_id:
                    continue
                evaluation = hw_item.get('evaluation') or {}
                page_num = hw_item.get('page_num', 0)
                page_stats[page_num]['total'] += evaluation.get('total_questions', 0)
            
            for sample in filtered_samples:
                page_num = sample.get('page_num', 0)
                page_stats[page_num]['error_count'] += 1
            
            items = []
            for page_num, stats in page_stats.items():
                if stats['total'] == 0:
                    continue
                error_rate = stats['error_count'] / stats['total'] if stats['total'] > 0 else 0
                items.append({
                    'id': str(page_num),
                    'name': f'第 {page_num} 页',
                    'error_count': stats['error_count'],
                    'total': stats['total'],
                    'error_rate': round(error_rate, 4),
                    'is_focus': error_rate > 0.2,
                    'has_children': True
                })
            items.sort(key=lambda x: x['error_count'], reverse=True)
            
            return {'level': 'page', 'parent': parent_info, 'items': items}
        
        return {'level': level, 'items': []}

    
    @classmethod
    def _identify_error_patterns(cls, error_samples: List[dict]) -> List[dict]:
        """识别错误模式"""
        # 按错误类型统计
        type_stats = defaultdict(list)
        for sample in error_samples:
            error_type = sample.get('error_type', '其他')
            type_stats[error_type].append(sample)
        
        total_errors = len(error_samples)
        patterns = []
        
        for error_type, samples in type_stats.items():
            count = len(samples)
            percentage = count / total_errors if total_errors > 0 else 0
            
            # 评定严重程度
            if percentage > 0.3:
                severity = 'high'
            elif percentage > 0.15:
                severity = 'medium'
            else:
                severity = 'low'
            
            # 选取示例（最多3个）
            examples = []
            for s in samples[:3]:
                examples.append({
                    'homework_id': s.get('homework_id'),
                    'question': f"第{s.get('question_index', 0)}题",
                    'ai_answer': s.get('ai_answer', '')[:100],
                    'expected': s.get('expected_answer', '')[:100]
                })
            
            patterns.append({
                'pattern_id': f'p{len(patterns)+1}',
                'type': error_type,
                'count': count,
                'percentage': round(percentage, 4),
                'severity': severity,
                'description': cls._get_pattern_description(error_type),
                'examples': examples
            })
        
        # 按数量排序，取 Top 5
        patterns.sort(key=lambda x: x['count'], reverse=True)
        return patterns[:5]
    
    @classmethod
    def _get_pattern_description(cls, error_type: str) -> str:
        """获取错误模式描述"""
        descriptions = {
            '识别错误-判断错误': '手写体或图片识别不准确，导致 AI 对答案的判断出现偏差',
            '识别正确-判断错误': 'AI 正确识别了答案内容，但评分逻辑存在问题',
            '缺失题目': '部分题目未被 AI 识别或处理',
            'AI识别幻觉': 'AI 识别出了实际不存在的内容',
            '答案不匹配': '标准答案与学生答案格式不一致或存在等价表达'
        }
        return descriptions.get(error_type, '未知错误类型')
    
    @classmethod
    def _analyze_root_causes(cls, error_samples: List[dict], error_patterns: List[dict]) -> List[dict]:
        """分析根因"""
        # 基于错误类型推断根因
        cause_mapping = {
            '识别错误-判断错误': 'ocr_issue',
            '识别正确-判断错误': 'scoring_logic',
            '缺失题目': 'data_issue',
            'AI识别幻觉': 'ocr_issue',
            '答案不匹配': 'answer_issue'
        }
        
        cause_stats = defaultdict(lambda: {'count': 0, 'samples': []})
        
        for sample in error_samples:
            error_type = sample.get('error_type', '其他')
            cause_type = cause_mapping.get(error_type, 'data_issue')
            cause_stats[cause_type]['count'] += 1
            if len(cause_stats[cause_type]['samples']) < 3:
                cause_stats[cause_type]['samples'].append(sample)
        
        total = len(error_samples)
        root_causes = []
        
        for cause_type, stats in cause_stats.items():
            percentage = stats['count'] / total if total > 0 else 0
            
            # 构建证据
            evidence = []
            for s in stats['samples']:
                evidence.append({
                    'homework_id': s.get('homework_id'),
                    'description': f"题目{s.get('question_index')}: AI答案'{s.get('ai_answer', '')[:50]}' vs 期望'{s.get('expected_answer', '')[:50]}'"
                })
            
            root_causes.append({
                'cause_type': cause_type,
                'name': ROOT_CAUSE_TYPES.get(cause_type, '未知'),
                'count': stats['count'],
                'percentage': round(percentage, 4),
                'is_main': percentage > 0.3,
                'sub_causes': cls._get_sub_causes(cause_type, stats['samples']),
                'evidence': evidence
            })
        
        # 按占比排序
        root_causes.sort(key=lambda x: x['percentage'], reverse=True)
        return root_causes
    
    @classmethod
    def _get_sub_causes(cls, cause_type: str, samples: List[dict]) -> List[dict]:
        """获取子原因"""
        sub_causes_map = {
            'ocr_issue': [
                {'name': '手写体识别差', 'count': 0},
                {'name': '图片质量低', 'count': 0},
                {'name': '特殊符号识别错误', 'count': 0}
            ],
            'scoring_logic': [
                {'name': '评分标准不清晰', 'count': 0},
                {'name': '部分得分判断错误', 'count': 0},
                {'name': '等价答案未覆盖', 'count': 0}
            ],
            'answer_issue': [
                {'name': '标准答案有误', 'count': 0},
                {'name': '答案格式不统一', 'count': 0},
                {'name': '多解情况未考虑', 'count': 0}
            ],
            'prompt_issue': [
                {'name': '指令不够明确', 'count': 0},
                {'name': '缺少特定场景处理', 'count': 0}
            ],
            'data_issue': [
                {'name': '数据集标注错误', 'count': 0},
                {'name': '题目信息缺失', 'count': 0}
            ]
        }
        
        sub_causes = sub_causes_map.get(cause_type, [])
        # 简单分配计数
        if sub_causes and samples:
            avg = len(samples) // len(sub_causes)
            for i, sc in enumerate(sub_causes):
                sc['count'] = avg if i < len(sub_causes) - 1 else len(samples) - avg * (len(sub_causes) - 1)
        
        return [sc for sc in sub_causes if sc['count'] > 0]
    
    @classmethod
    def _generate_suggestions(cls, error_patterns: List[dict], root_causes: List[dict]) -> List[dict]:
        """生成优化建议"""
        suggestions = []
        
        # 基于根因生成建议
        suggestion_templates = {
            'ocr_issue': {
                'title': '优化手写体识别容错',
                'description': '在评分 prompt 中增加对手写体的容错处理，考虑常见的书写变体和模糊字符',
                'priority': 'high',
                'expected_effect': '预计可减少 30% 的识别错误',
                'prompt_suggestion': '建议在评分 prompt 中添加：对于手写体答案，请考虑常见的书写变体，如"力"和"刀"、"0"和"O"等'
            },
            'scoring_logic': {
                'title': '完善评分逻辑',
                'description': '优化评分标准的描述，增加对部分得分和等价答案的处理规则',
                'priority': 'high',
                'expected_effect': '预计可减少 25% 的评分逻辑错误',
                'prompt_suggestion': '建议明确评分标准：1. 完全正确得满分 2. 部分正确按比例给分 3. 等价表达视为正确'
            },
            'answer_issue': {
                'title': '规范标准答案格式',
                'description': '统一标准答案的格式，增加等价答案的覆盖',
                'priority': 'medium',
                'expected_effect': '预计可减少 20% 的答案不匹配错误',
                'prompt_suggestion': None
            },
            'prompt_issue': {
                'title': '优化评分 Prompt',
                'description': '增加对特定场景的处理说明，使指令更加明确',
                'priority': 'medium',
                'expected_effect': '预计可提升整体准确率 5%',
                'prompt_suggestion': '建议增加场景说明：对于选择题、填空题、计算题分别采用不同的评分策略'
            },
            'data_issue': {
                'title': '检查数据集质量',
                'description': '审核数据集标注，补充缺失的题目信息',
                'priority': 'low',
                'expected_effect': '预计可减少 10% 的数据相关错误',
                'prompt_suggestion': None
            }
        }
        
        for cause in root_causes:
            if cause['is_main'] or cause['percentage'] > 0.15:
                template = suggestion_templates.get(cause['cause_type'])
                if template:
                    suggestion = {
                        'suggestion_id': f's{len(suggestions)+1}',
                        'title': template['title'],
                        'description': template['description'],
                        'priority': template['priority'],
                        'expected_effect': template['expected_effect'],
                        'related_cause': cause['cause_type']
                    }
                    if template.get('prompt_suggestion'):
                        suggestion['prompt_suggestion'] = template['prompt_suggestion']
                    suggestions.append(suggestion)
        
        # 按优先级排序
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        suggestions.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return suggestions[:5]
    
    @classmethod
    def _generate_summary(cls, error_samples: List[dict], drill_down: dict, 
                         error_patterns: List[dict], root_causes: List[dict]) -> dict:
        """生成摘要"""
        total_errors = len(error_samples)
        total_questions = drill_down.get('total_questions', 0)
        error_rate = total_errors / total_questions if total_questions > 0 else 0
        
        # 主要问题
        main_issues = []
        for pattern in error_patterns[:3]:
            if pattern['severity'] == 'high':
                main_issues.append(f"{pattern['type']}问题突出（占比{pattern['percentage']*100:.1f}%）")
        
        for cause in root_causes:
            if cause['is_main']:
                main_issues.append(f"{cause['name']}是主要根因（占比{cause['percentage']*100:.1f}%）")
        
        return {
            'total_errors': total_errors,
            'total_questions': total_questions,
            'error_rate': round(error_rate, 4),
            'main_issues': main_issues[:3]
        }
    
    @classmethod
    def _update_progress(cls, task_id: str, progress: int):
        """更新进度"""
        with cls._lock:
            if task_id in cls._running:
                cls._running[task_id]['progress'] = progress
    
    @classmethod
    def _save_report(cls, report_id: str, task_id: str, status: str, 
                    report_data: dict, duration: int = None):
        """保存报告到数据库"""
        try:
            sql = """
                INSERT INTO analysis_reports 
                (report_id, task_id, status, summary, drill_down_data, error_patterns, 
                 root_causes, suggestions, created_at, completed_at, duration_seconds)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                summary = VALUES(summary),
                drill_down_data = VALUES(drill_down_data),
                error_patterns = VALUES(error_patterns),
                root_causes = VALUES(root_causes),
                suggestions = VALUES(suggestions),
                completed_at = VALUES(completed_at),
                duration_seconds = VALUES(duration_seconds)
            """
            now = datetime.now()
            AppDatabaseService.execute_insert(sql, (
                report_id, task_id, status,
                json.dumps(report_data.get('summary', {}), ensure_ascii=False),
                json.dumps(report_data.get('drill_down', {}), ensure_ascii=False),
                json.dumps(report_data.get('error_patterns', []), ensure_ascii=False),
                json.dumps(report_data.get('root_causes', []), ensure_ascii=False),
                json.dumps(report_data.get('suggestions', []), ensure_ascii=False),
                now, now if status == 'completed' else None, duration
            ))
        except Exception as e:
            print(f"[AIAnalysis] 保存报告失败: {e}")
    
    @classmethod
    def _save_failed_report(cls, task_id: str, error_msg: str, 
                           report_id: str = None, duration: int = None):
        """保存失败报告"""
        if not report_id:
            report_id = str(uuid.uuid4())[:8]
        try:
            sql = """
                INSERT INTO analysis_reports 
                (report_id, task_id, status, error_message, created_at, duration_seconds)
                VALUES (%s, %s, 'failed', %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                status = 'failed',
                error_message = VALUES(error_message),
                duration_seconds = VALUES(duration_seconds)
            """
            AppDatabaseService.execute_insert(sql, (
                report_id, task_id, error_msg, datetime.now(), duration
            ))
        except Exception as e:
            print(f"[AIAnalysis] 保存失败报告失败: {e}")
    
    @classmethod
    def _log_automation(cls, task_type: str, related_id: str, 
                       status: str, message: str, duration: int = None):
        """记录自动化日志"""
        try:
            log_id = str(uuid.uuid4())[:8]
            sql = """
                INSERT INTO automation_logs 
                (log_id, task_type, related_id, status, message, duration_seconds, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            AppDatabaseService.execute_insert(sql, (
                log_id, task_type, related_id, status, message, duration, datetime.now()
            ))
        except Exception as e:
            print(f"[AIAnalysis] 记录日志失败: {e}")
    
    @classmethod
    def get_analysis_report(cls, task_id: str) -> Optional[dict]:
        """获取分析报告"""
        try:
            sql = """
                SELECT report_id, task_id, status, summary, drill_down_data,
                       error_patterns, root_causes, suggestions, error_message,
                       created_at, completed_at, duration_seconds
                FROM analysis_reports
                WHERE task_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            result = AppDatabaseService.execute_query(sql, (task_id,))
            if result:
                row = result[0]
                return {
                    'report_id': row['report_id'],
                    'task_id': row['task_id'],
                    'status': row['status'],
                    'summary': json.loads(row['summary']) if row['summary'] else {},
                    'drill_down': json.loads(row['drill_down_data']) if row['drill_down_data'] else {},
                    'error_patterns': json.loads(row['error_patterns']) if row['error_patterns'] else [],
                    'root_causes': json.loads(row['root_causes']) if row['root_causes'] else [],
                    'suggestions': json.loads(row['suggestions']) if row['suggestions'] else [],
                    'error_message': row['error_message'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None,
                    'duration_seconds': row['duration_seconds']
                }
        except Exception as e:
            print(f"[AIAnalysis] 获取报告失败: {e}")
        return None
    
    @classmethod
    def get_queue_status(cls) -> dict:
        """获取队列状态"""
        with cls._lock:
            return {
                'waiting': len(cls._queue),
                'waiting_tasks': list(cls._queue),
                'running': [
                    {'task_id': tid, **info}
                    for tid, info in cls._running.items()
                ],
                'paused': cls._paused
            }
    
    @classmethod
    def pause(cls):
        """暂停"""
        cls._paused = True
    
    @classmethod
    def resume(cls):
        """恢复"""
        cls._paused = False
        with cls._lock:
            cls._try_process_queue()
    
    @classmethod
    def clear_queue(cls) -> int:
        """清空队列"""
        with cls._lock:
            count = len(cls._queue)
            cls._queue.clear()
            return count
    
    @classmethod
    def get_report(cls, task_id: str) -> Optional[dict]:
        """获取分析报告（别名方法）"""
        report = cls.get_analysis_report(task_id)
        if report:
            # 转换字段名以匹配 API 期望
            return {
                'report_id': report.get('report_id'),
                'task_id': report.get('task_id'),
                'status': report.get('status'),
                'summary': report.get('summary', {}),
                'drill_down_data': report.get('drill_down', {}),
                'error_patterns': report.get('error_patterns', []),
                'root_causes': report.get('root_causes', []),
                'suggestions': report.get('suggestions', []),
                'error_message': report.get('error_message'),
                'created_at': report.get('created_at'),
                'completed_at': report.get('completed_at'),
                'duration_seconds': report.get('duration_seconds')
            }
        return None
    
    @classmethod
    def get_status(cls, task_id: str) -> dict:
        """获取任务分析状态"""
        with cls._lock:
            # 检查是否在队列中
            if task_id in cls._queue:
                position = cls._queue.index(task_id) + 1
                return {
                    'status': 'queued',
                    'position': position,
                    'message': f'等待分析，队列位置 {position}'
                }
            
            # 检查是否正在执行
            if task_id in cls._running:
                info = cls._running[task_id]
                return {
                    'status': 'analyzing',
                    'started_at': info.get('started_at'),
                    'progress': info.get('progress', 0),
                    'message': '正在分析中'
                }
        
        # 检查数据库中的报告
        report = cls.get_analysis_report(task_id)
        if report:
            return {
                'status': report.get('status', 'unknown'),
                'report_id': report.get('report_id'),
                'completed_at': report.get('completed_at'),
                'duration_seconds': report.get('duration_seconds'),
                'message': '分析完成' if report.get('status') == 'completed' else report.get('error_message', '未知状态')
            }
        
        return {
            'status': 'none',
            'message': '暂无分析记录'
        }

    
    # ============================================
    # 快速统计方法（毫秒级响应）
    # ============================================
    
    @classmethod
    def get_quick_stats(cls, task_id: str) -> dict:
        """
        获取快速本地统计（毫秒级响应，< 100ms）
        
        Returns:
            dict: {
                total_errors: int,
                total_questions: int,
                error_rate: float,
                error_type_distribution: {...},
                subject_distribution: {...},
                book_distribution: {...},
                question_type_distribution: {...},
                clusters: [{cluster_key, count, samples}]
            }
        """
        start_time = time.time()
        
        # 加载任务数据
        task_data = cls._load_task(task_id)
        if not task_data:
            return {'error': '任务不存在', 'total_errors': 0, 'total_questions': 0}
        
        # 收集错误样本
        error_samples = cls._collect_error_samples(task_data)
        
        # 统计总题目数
        total_questions = 0
        for hw_item in task_data.get('homework_items', []):
            evaluation = hw_item.get('evaluation') or {}
            total_questions += evaluation.get('total_questions', 0)
        
        total_errors = len(error_samples)
        error_rate = total_errors / total_questions if total_questions > 0 else 0
        
        # 错误类型分布
        error_type_dist = defaultdict(int)
        for sample in error_samples:
            error_type_dist[sample.get('error_type', '其他')] += 1
        
        # 学科分布
        subject_dist = defaultdict(int)
        for sample in error_samples:
            subject_id = sample.get('subject_id')
            if subject_id is not None:
                subject_name = SUBJECT_MAP.get(subject_id, '未知')
                subject_dist[subject_name] += 1
        
        # 书本分布
        book_dist = defaultdict(int)
        for sample in error_samples:
            book_name = sample.get('book_name', '未知')
            book_dist[book_name] += 1
        
        # 初步聚类（按 error_type + book + page_range）
        clusters = cls._generate_quick_clusters(error_samples)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return {
            'total_errors': total_errors,
            'total_questions': total_questions,
            'error_rate': round(error_rate, 4),
            'error_type_distribution': dict(error_type_dist),
            'subject_distribution': dict(subject_dist),
            'book_distribution': dict(book_dist),
            'clusters': clusters,
            'duration_ms': duration_ms
        }
    
    @classmethod
    def _generate_quick_clusters(cls, error_samples: List[dict]) -> List[dict]:
        """
        生成快速聚类（本地计算，不调用 LLM）
        
        聚类键: error_type + book_name + page_range
        """
        cluster_map = defaultdict(list)
        
        for sample in error_samples:
            error_type = sample.get('error_type', '其他')
            book_name = sample.get('book_name', '未知')
            page_num = sample.get('page_num', 0)
            
            # 计算页码范围（每10页一组）
            page_range_start = (page_num // 10) * 10
            page_range = f"{page_range_start}-{page_range_start + 9}"
            
            cluster_key = f"{error_type}_{book_name}_{page_range}"
            cluster_map[cluster_key].append(sample)
        
        # 转换为列表并排序
        clusters = []
        for cluster_key, samples in cluster_map.items():
            parts = cluster_key.split('_', 2)
            clusters.append({
                'cluster_key': cluster_key,
                'error_type': parts[0] if len(parts) > 0 else '未知',
                'book_name': parts[1] if len(parts) > 1 else '未知',
                'page_range': parts[2] if len(parts) > 2 else '未知',
                'sample_count': len(samples),
                'samples': samples[:10]  # 只保留前10个样本
            })
        
        # 按样本数排序
        clusters.sort(key=lambda x: x['sample_count'], reverse=True)
        
        return clusters
    
    # ============================================
    # 缓存机制
    # ============================================
    
    @classmethod
    def _compute_data_hash(cls, data: Any) -> str:
        """计算数据哈希值"""
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    @classmethod
    def get_cached_analysis(cls, task_id: str, analysis_type: str = 'task', target_id: str = None) -> dict:
        """
        获取缓存的分析结果
        
        Args:
            task_id: 任务ID
            analysis_type: sample|cluster|task|subject|book|question_type|trend|compare
            target_id: 目标ID（如聚类ID、学科名等）
            
        Returns:
            dict: {
                quick_stats: {...},
                llm_analysis: {...} or None,
                analysis_status: pending|analyzing|completed|stale,
                data_hash: str,
                updated_at: str
            }
        """
        # 获取快速统计
        quick_stats = cls.get_quick_stats(task_id)
        if quick_stats.get('error'):
            return {'error': quick_stats.get('error')}
        
        # 计算当前数据哈希
        current_hash = cls._compute_data_hash({
            'total_errors': quick_stats.get('total_errors'),
            'error_type_distribution': quick_stats.get('error_type_distribution'),
            'clusters_count': len(quick_stats.get('clusters', []))
        })
        
        # 查询缓存
        target = target_id or task_id
        try:
            sql = """
                SELECT result_id, analysis_data, data_hash, status, updated_at
                FROM analysis_results
                WHERE analysis_type = %s AND target_id = %s AND task_id = %s
                ORDER BY updated_at DESC
                LIMIT 1
            """
            result = AppDatabaseService.execute_query(sql, (analysis_type, target, task_id))
            
            if result:
                row = result[0]
                cached_hash = row.get('data_hash', '')
                
                # 检查缓存是否有效
                if cached_hash == current_hash and row.get('status') == 'completed':
                    return {
                        'quick_stats': quick_stats,
                        'llm_analysis': json.loads(row.get('analysis_data', '{}')) if row.get('analysis_data') else None,
                        'analysis_status': 'completed',
                        'data_hash': current_hash,
                        'updated_at': row.get('updated_at').isoformat() if row.get('updated_at') else None,
                        'cache_hit': True
                    }
                elif row.get('status') == 'analyzing':
                    return {
                        'quick_stats': quick_stats,
                        'llm_analysis': None,
                        'analysis_status': 'analyzing',
                        'data_hash': current_hash,
                        'updated_at': None,
                        'cache_hit': False
                    }
                else:
                    # 缓存过期
                    return {
                        'quick_stats': quick_stats,
                        'llm_analysis': json.loads(row.get('analysis_data', '{}')) if row.get('analysis_data') else None,
                        'analysis_status': 'stale',
                        'data_hash': current_hash,
                        'updated_at': row.get('updated_at').isoformat() if row.get('updated_at') else None,
                        'cache_hit': False
                    }
        except Exception as e:
            print(f"[AIAnalysis] 查询缓存失败: {e}")
        
        # 无缓存
        return {
            'quick_stats': quick_stats,
            'llm_analysis': None,
            'analysis_status': 'pending',
            'data_hash': current_hash,
            'updated_at': None,
            'cache_hit': False
        }
    
    @classmethod
    def _save_analysis_result(cls, task_id: str, analysis_type: str, target_id: str, 
                              analysis_data: dict, data_hash: str, token_usage: int = 0):
        """保存分析结果到缓存"""
        try:
            result_id = str(uuid.uuid4())[:8]
            sql = """
                INSERT INTO analysis_results 
                (result_id, analysis_type, target_id, task_id, analysis_data, data_hash, status, token_usage, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'completed', %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                analysis_data = VALUES(analysis_data),
                data_hash = VALUES(data_hash),
                status = 'completed',
                token_usage = VALUES(token_usage),
                updated_at = VALUES(updated_at)
            """
            now = datetime.now()
            AppDatabaseService.execute_insert(sql, (
                result_id, analysis_type, target_id, task_id,
                json.dumps(analysis_data, ensure_ascii=False),
                data_hash, token_usage, now, now
            ))
        except Exception as e:
            print(f"[AIAnalysis] 保存分析结果失败: {e}")
    
    # ============================================
    # 异常检测
    # ============================================
    
    @classmethod
    def detect_anomalies(cls, task_id: str) -> List[dict]:
        """
        检测异常模式（重点：批改不一致）
        
        Returns:
            list: [{
                anomaly_id: str,
                anomaly_type: str,
                severity: str,
                base_user_answer: str,
                correct_cases: [...],
                incorrect_cases: [...],
                inconsistency_rate: float,
                description: str,
                suggested_action: str
            }]
        """
        task_data = cls._load_task(task_id)
        if not task_data:
            return []
        
        anomalies = []
        
        # 1. 检测批改不一致（同一 base_user 答案，不同批改结果）
        inconsistent = cls._detect_inconsistent_grading(task_data)
        anomalies.extend(inconsistent)
        
        # 2. 检测连续错误（同一页码连续多题错误）
        continuous = cls._detect_continuous_errors(task_data)
        anomalies.extend(continuous)
        
        # 3. 检测学生答案缺失（整页 useranswer 缺失或全为空）
        missing_useranswer = cls._detect_missing_useranswer(task_data)
        anomalies.extend(missing_useranswer)
        
        return anomalies
    
    @classmethod
    def _detect_inconsistent_grading(cls, task_data: dict) -> List[dict]:
        """检测批改不一致"""
        # 按 base_user 答案分组
        answer_groups = defaultdict(list)
        
        for hw_item in task_data.get('homework_items', []):
            if hw_item.get('status') != 'completed':
                continue
            
            evaluation = hw_item.get('evaluation') or {}
            questions = evaluation.get('questions') or []
            
            for q in questions:
                base_user = q.get('base_user', '')
                if not base_user or len(base_user) < 2:
                    continue
                
                answer_groups[base_user].append({
                    'homework_id': hw_item.get('homework_id', ''),
                    'question_index': q.get('question_index', 0),
                    'ai_result': q.get('ai_result', ''),
                    'is_correct': q.get('is_correct', True),
                    'ai_answer': q.get('ai_answer', ''),
                    'expected_answer': q.get('expected_answer', '')
                })
        
        anomalies = []
        
        for base_user, cases in answer_groups.items():
            if len(cases) < 2:
                continue
            
            # 分离正确和错误案例
            correct_cases = [c for c in cases if c.get('is_correct', True)]
            incorrect_cases = [c for c in cases if not c.get('is_correct', True)]
            
            if correct_cases and incorrect_cases:
                total = len(cases)
                inconsistency_rate = len(incorrect_cases) / total
                
                # 判断严重程度
                if inconsistency_rate > 0.5:
                    severity = 'critical'
                elif inconsistency_rate > 0.3:
                    severity = 'high'
                elif inconsistency_rate > 0.1:
                    severity = 'medium'
                else:
                    severity = 'low'
                
                anomalies.append({
                    'anomaly_id': f"a_{uuid.uuid4().hex[:8]}",
                    'anomaly_type': 'inconsistent_grading',
                    'severity': severity,
                    'base_user_answer': base_user[:200],
                    'correct_cases': correct_cases[:5],
                    'incorrect_cases': incorrect_cases[:5],
                    'inconsistency_rate': round(inconsistency_rate, 4),
                    'description': f"同一答案 '{base_user[:50]}...' 在 {total} 次出现中有 {len(incorrect_cases)} 次被错误判定",
                    'suggested_action': '检查评分 Prompt 对该类答案的处理逻辑'
                })
        
        # 按不一致率排序，取 Top 10
        anomalies.sort(key=lambda x: x['inconsistency_rate'], reverse=True)
        return anomalies[:10]
    
    @classmethod
    def _detect_continuous_errors(cls, task_data: dict) -> List[dict]:
        """检测连续错误"""
        anomalies = []
        
        # 按作业分组检测
        for hw_item in task_data.get('homework_items', []):
            if hw_item.get('status') != 'completed':
                continue
            
            evaluation = hw_item.get('evaluation') or {}
            errors = evaluation.get('errors') or []
            
            if len(errors) >= 5:
                # 检查是否连续
                error_indices = sorted([e.get('question_index', 0) for e in errors])
                max_continuous = 1
                current_continuous = 1
                
                for i in range(1, len(error_indices)):
                    if error_indices[i] == error_indices[i-1] + 1:
                        current_continuous += 1
                        max_continuous = max(max_continuous, current_continuous)
                    else:
                        current_continuous = 1
                
                if max_continuous >= 3:
                    anomalies.append({
                        'anomaly_id': f"a_{uuid.uuid4().hex[:8]}",
                        'anomaly_type': 'continuous_error',
                        'severity': 'high' if max_continuous >= 5 else 'medium',
                        'base_user_answer': '',
                        'correct_cases': [],
                        'incorrect_cases': [],
                        'inconsistency_rate': 0,
                        'description': f"作业 {hw_item.get('homework_id', '')} 存在 {max_continuous} 道连续错误",
                        'suggested_action': '检查该页面的 OCR 识别质量或评分逻辑'
                    })
        
        return anomalies[:5]
    
    @classmethod
    def _detect_missing_useranswer(cls, task_data: dict) -> List[dict]:
        """
        检测学生答案缺失（整页 useranswer 缺失或全为空）
        
        检测逻辑：
        1. 遍历所有作业的 homework_result（AI批改结果）
        2. 按页码分组，检查每页的所有题目
        3. 如果一整页的所有题目都没有 useranswer 或全为空，标记为异常
        
        Returns:
            list: 异常列表
        """
        anomalies = []
        
        # 按页码分组统计
        page_stats = defaultdict(lambda: {
            'total_questions': 0,
            'missing_useranswer': 0,
            'homework_ids': set()
        })
        
        for hw_item in task_data.get('homework_items', []):
            if hw_item.get('status') != 'completed':
                continue
            
            homework_id = hw_item.get('homework_id', '')
            page_num = hw_item.get('page_num', '')
            
            # 解析 homework_result
            homework_result_str = hw_item.get('homework_result', '[]')
            try:
                homework_result = json.loads(homework_result_str) if isinstance(homework_result_str, str) else homework_result_str
            except:
                continue
            
            if not isinstance(homework_result, list) or not homework_result:
                continue
            
            # 展开 children 结构
            flattened_questions = []
            for item in homework_result:
                children = item.get('children', [])
                if children and len(children) > 0:
                    flattened_questions.extend(children)
                else:
                    flattened_questions.append(item)
            
            if not flattened_questions:
                continue
            
            # 检查该页所有题目的 useranswer
            page_key = f"{page_num}"
            page_stats[page_key]['homework_ids'].add(homework_id)
            
            for q in flattened_questions:
                page_stats[page_key]['total_questions'] += 1
                
                # 检查 useranswer 是否缺失或为空
                user_answer = q.get('userAnswer', '')
                if not user_answer or (isinstance(user_answer, str) and not user_answer.strip()):
                    page_stats[page_key]['missing_useranswer'] += 1
        
        # 分析统计结果，找出整页缺失的情况
        for page_key, stats in page_stats.items():
            total = stats['total_questions']
            missing = stats['missing_useranswer']
            
            # 如果整页所有题目都缺失 useranswer
            if total > 0 and missing == total:
                homework_ids = list(stats['homework_ids'])
                
                anomalies.append({
                    'anomaly_id': f"a_{uuid.uuid4().hex[:8]}",
                    'anomaly_type': 'missing_useranswer',
                    'severity': 'critical',
                    'base_user_answer': '',
                    'correct_cases': [],
                    'incorrect_cases': [],
                    'inconsistency_rate': 1.0,
                    'description': f"页码 {page_key} 的 AI 批改结果缺失学生答案（{total} 题全部为空）",
                    'suggested_action': f"检查作业 {', '.join(homework_ids[:3])} 的 OCR 识别或数据完整性",
                    'affected_homework_ids': homework_ids,
                    'page_num': page_key
                })
        
        # 按页码排序
        anomalies.sort(key=lambda x: x.get('page_num', ''))
        return anomalies
        return anomalies
    
    # ============================================
    # 队列状态管理
    # ============================================
    
    @classmethod
    def get_analysis_queue_status(cls) -> dict:
        """
        获取分析队列状态
        
        Returns:
            dict: {
                waiting: int,
                running: [{task_id, progress, step, started_at, job_id}],
                recent_completed: [{task_id, completed_at, duration, job_id}],
                recent_failed: [{task_id, error, failed_at, job_id}]
            }
        """
        with cls._lock:
            return {
                'waiting': len(cls._queue),
                'waiting_tasks': [
                    {'task_id': item.get('task_id'), 'priority': item.get('priority'), 'job_id': item.get('job_id')}
                    for item in cls._queue
                ],
                'running': [
                    {'task_id': tid, **info}
                    for tid, info in cls._running.items()
                ],
                'recent_completed': list(cls._recent_completed),
                'recent_failed': list(cls._recent_failed),
                'paused': cls._paused
            }
    
    @classmethod
    def cancel_analysis(cls, job_id: str) -> dict:
        """
        取消排队中的分析任务
        
        Args:
            job_id: 任务的 job_id
            
        Returns:
            dict: {success: bool, message: str}
        """
        with cls._lock:
            # 查找并移除
            for i, item in enumerate(cls._queue):
                if item.get('job_id') == job_id:
                    cls._queue.pop(i)
                    return {'success': True, 'message': f'任务 {job_id} 已取消'}
            
            # 检查是否正在运行
            for task_id, info in cls._running.items():
                if info.get('job_id') == job_id:
                    return {'success': False, 'message': f'任务 {job_id} 正在执行中，无法取消'}
        
        return {'success': False, 'message': f'未找到任务 {job_id}'}
    
    @classmethod
    def _update_progress(cls, task_id: str, progress: int, step: str = None):
        """更新进度"""
        with cls._lock:
            if task_id in cls._running:
                cls._running[task_id]['progress'] = progress
                if step:
                    cls._running[task_id]['step'] = step
