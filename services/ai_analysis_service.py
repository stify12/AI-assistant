"""
AI 智能数据分析服务

提供批量评估任务的智能分析功能，包括：
- 错误样本收集
- 多层级聚合统计（学科→书本→页码→题目）
- 错误模式识别
- 根因分析
- 优化建议生成
"""
import os
import json
import uuid
import time
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
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
    """AI 数据分析服务"""
    
    # 分析队列
    _queue: List[str] = []
    _running: Dict[str, dict] = {}
    _max_concurrent: int = 2
    _lock = threading.Lock()
    _paused: bool = False
    
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
    def trigger_analysis(cls, task_id: str) -> dict:
        """
        触发任务分析
        
        Args:
            task_id: 批量评估任务ID
            
        Returns:
            dict: {queued: bool, position: int, message: str}
        """
        config = cls.get_config()
        
        # 检查是否启用
        if not config.get('enabled', True):
            return {'queued': False, 'position': -1, 'message': 'AI 分析已禁用'}
        
        # 检查是否暂停
        if cls._paused:
            return {'queued': False, 'position': -1, 'message': '自动化任务已暂停'}
        
        with cls._lock:
            # 检查是否已在队列或正在执行
            if task_id in cls._queue:
                position = cls._queue.index(task_id) + 1
                return {'queued': True, 'position': position, 'message': f'任务已在队列中，位置 {position}'}
            
            if task_id in cls._running:
                return {'queued': True, 'position': 0, 'message': '任务正在分析中'}
            
            # 加入队列
            cls._queue.append(task_id)
            position = len(cls._queue)
            
            # 尝试启动处理
            cls._try_process_queue()
            
            return {'queued': True, 'position': position, 'message': f'分析任务已加入队列，位置 {position}'}
    
    @classmethod
    def _try_process_queue(cls):
        """尝试处理队列中的任务"""
        config = cls.get_config()
        max_concurrent = config.get('max_concurrent', 2)
        
        while len(cls._running) < max_concurrent and cls._queue and not cls._paused:
            task_id = cls._queue.pop(0)
            cls._running[task_id] = {
                'started_at': datetime.now().isoformat(),
                'progress': 0
            }
            
            # 启动分析线程
            thread = threading.Thread(target=cls._analyze_task_thread, args=(task_id,))
            thread.daemon = True
            thread.start()
    
    @classmethod
    def _analyze_task_thread(cls, task_id: str):
        """分析任务线程"""
        try:
            cls.analyze_task(task_id)
        except Exception as e:
            print(f"[AIAnalysis] 分析任务 {task_id} 失败: {e}")
            cls._save_failed_report(task_id, str(e))
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
