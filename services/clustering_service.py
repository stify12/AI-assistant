"""
错误聚类服务模块

两阶段聚类：
1. 本地按错误特征（标准化答案+判断结果）预分组
2. 对每种错误模式调用LLM分析错误类型

支持结果缓存、学科上下文、流式返回
"""
import json
import concurrent.futures
from typing import Dict, List, Any, Generator
from collections import defaultdict

from .llm_service import LLMService
from .storage_service import StorageService
from utils.text_utils import normalize_answer


# 通用错误类型（所有学科共享）
COMMON_ERROR_TYPES = [
    # === 识别类 ===
    "汉字识别错误", "形近字混淆", "同音字混淆",
    "数字识别错误", "小数点遗漏", "负号遗漏",
    "符号识别错误", "运算符错误", "括号错误",
    "字母识别错误", "大小写错误",
    # === 内容偏差类 ===
    "术语表述差异",      # 同一概念不同表述，如"垂线最短"vs"垂线段最短"
    "内容部分缺失",      # AI漏掉了部分关键词/字
    "内容部分多余",      # AI多识别了不存在的内容
    "答案不完整",        # 多个答案只识别了部分
    "顺序错乱",          # 答案内容对但顺序不同
    "同义词替换",        # 用了不同的词但意思相同
    # === 格式类（纯格式，不影响语义）===
    "标点符号差异",      # 中英文标点、逗号句号等
    "空格换行差异",      # 空格、换行、缩进等
    "书写格式差异",      # markdown、上下标格式等
    # === 判分类 ===
    "正确判为错误",      # 学生答对了但AI判错
    "错误判为正确",      # 学生答错了但AI判对（含AI幻觉）
    "得分计算错误",      # 分值给错
    # === 识别异常类 ===
    "空白误识别为有内容", # 学生没写但AI识别出了内容
    "有内容误识别为空白", # 学生写了但AI没识别到
    "字迹模糊误判",      # 因字迹潦草导致的识别错误
    # === 其他 ===
    "语义理解错误",      # AI理解了文字但理解错了意思
    "其他错误"
]

# 学科专有错误类型（追加到通用类型之后）
SUBJECT_SPECIFIC_TYPES = {
    0: ["单词拼写错误", "单词遗漏", "语法理解错误"],                          # 英语
    1: ["拼音识别错误", "汉字遗漏", "汉字多余", "语句理解错误"],              # 语文
    2: ["分数识别错误", "上下标错误", "公式解析错误", "单位识别错误", "单位遗漏"],  # 数学
    3: ["上下标错误", "公式解析错误", "单位识别错误", "单位遗漏"],             # 物理
    4: ["化学式错误", "元素符号错误", "上下标错误", "化学方程式错误"],         # 化学
    5: ["专业术语错误"],                                                       # 生物
    6: ["地名识别错误"],                                                       # 地理
}

# 组合：学科错误类型 = 通用 + 学科专有
SUBJECT_ERROR_TYPES = {
    sid: COMMON_ERROR_TYPES + specific
    for sid, specific in SUBJECT_SPECIFIC_TYPES.items()
}

# 学科名称映射
SUBJECT_NAMES = {
    0: "英语", 1: "语文", 2: "数学", 3: "物理", 4: "化学", 5: "生物", 6: "地理"
}

# 默认错误类型（通用，未知学科时使用）
DEFAULT_ERROR_TYPES = COMMON_ERROR_TYPES


class ClusteringService:
    """错误聚类服务类"""
    
    @staticmethod
    def cluster_task_errors(task_id: str, use_llm: bool = True, subject_id: int = None, user_id: str = None) -> Dict[str, Any]:
        """两阶段聚类：本地按错误特征预分组 → LLM分析错误类型"""
        task_data = StorageService.load_batch_task(task_id)
        if not task_data:
            return {'success': False, 'error': '任务不存在'}
        
        # 检查是否有缓存的聚类结果
        cached_cluster = task_data.get('cluster_result')
        if cached_cluster:
            print(f'[Clustering] 使用缓存的聚类结果')
            return {
                'success': True,
                'cached': True,
                'clusters': cached_cluster.get('clusters', []),
                'total_errors': cached_cluster.get('total_errors', 0),
                'total_questions': cached_cluster.get('total_questions', 0)
            }
        
        # 获取学科ID
        if subject_id is None:
            subject_id = task_data.get('subject_id')
        
        # 提取所有错误
        errors = ClusteringService._extract_errors(task_data)
        if not errors:
            return {
                'success': True,
                'clusters': [],
                'total_errors': 0,
                'message': '该任务没有错误样本'
            }
        
        # 阶段1：本地按错误特征预分组（相同错误模式的样本归到一起）
        pattern_groups = ClusteringService._group_by_error_pattern(errors)
        
        # 统计涉及的题目数
        all_question_keys = set()
        for err in errors:
            page = err.get('page_num', '')
            q_idx = str(err.get('question_index', '?'))
            all_question_keys.add(f"{page}_{q_idx}" if page else q_idx)
        
        print(f'[Clustering] 本地预分组完成：{len(errors)} 个错误 → {len(pattern_groups)} 种错误模式，涉及 {len(all_question_keys)} 道题')
        
        # 阶段2：对每种错误模式调用LLM分析
        llm_result = ClusteringService._batch_analyze_patterns(pattern_groups, subject_id=subject_id, user_id=user_id)
        
        if not llm_result.get('success'):
            return {
                'success': False,
                'error': llm_result.get('error', 'LLM分析失败，请重试')
            }
        
        clusters = llm_result.get('clusters', [])
        
        # 保存聚类结果到任务数据
        cluster_result = {
            'clusters': clusters,
            'total_errors': len(errors),
            'total_questions': len(all_question_keys),
            'subject_id': subject_id
        }
        task_data['cluster_result'] = cluster_result
        StorageService.save_batch_task(task_id, task_data)
        print(f'[Clustering] 聚类结果已保存到任务数据')
        
        return {
            'success': True,
            'cached': False,
            'clusters': clusters,
            'total_errors': len(errors),
            'total_questions': len(all_question_keys)
        }
    
    @staticmethod
    def cluster_task_errors_stream(task_id: str, subject_id: int = None, user_id: str = None) -> Generator[str, None, None]:
        """流式聚类：本地预分组 → 逐个LLM分析"""
        task_data = StorageService.load_batch_task(task_id)
        if not task_data:
            yield f"data: {json.dumps({'type': 'error', 'error': '任务不存在'})}\n\n"
            return
        
        # 检查缓存
        cached_cluster = task_data.get('cluster_result')
        if cached_cluster:
            yield f"data: {json.dumps({'type': 'cached', 'data': cached_cluster})}\n\n"
            return
        
        # 获取学科ID
        if subject_id is None:
            subject_id = task_data.get('subject_id')
        
        # 提取错误
        errors = ClusteringService._extract_errors(task_data)
        if not errors:
            yield f"data: {json.dumps({'type': 'complete', 'clusters': [], 'total_errors': 0})}\n\n"
            return
        
        # 阶段1：本地按错误特征预分组
        pattern_groups = ClusteringService._group_by_error_pattern(errors)
        
        # 统计涉及的题目数
        all_question_keys = set()
        for err in errors:
            page = err.get('page_num', '')
            q_idx = str(err.get('question_index', '?'))
            all_question_keys.add(f"{page}_{q_idx}" if page else q_idx)
        
        total = len(pattern_groups)
        yield f"data: {json.dumps({'type': 'start', 'total': total, 'subject': SUBJECT_NAMES.get(subject_id, '未知')})}\n\n"
        
        # 阶段2：逐个分析错误模式
        results = []
        patterns_list = list(pattern_groups.items())[:50]  # 限制50种模式
        for i, (pattern_key, group) in enumerate(patterns_list):
            result = ClusteringService._analyze_single_pattern(group, subject_id=subject_id, user_id=user_id)
            results.append(result)
            yield f"data: {json.dumps({'type': 'progress', 'current': i+1, 'total': min(total, 50), 'result': result})}\n\n"
        
        # 聚合结果：相同label的模式合并
        clusters = ClusteringService._aggregate_pattern_results(results)
        
        # 保存到任务
        cluster_result = {
            'clusters': clusters,
            'total_errors': len(errors),
            'total_questions': len(all_question_keys),
            'subject_id': subject_id
        }
        task_data['cluster_result'] = cluster_result
        StorageService.save_batch_task(task_id, task_data)
        
        yield f"data: {json.dumps({'type': 'complete', 'clusters': clusters, 'total_errors': len(errors), 'total_questions': len(all_question_keys)})}\n\n"
    
    @staticmethod
    def clear_cluster_cache(task_id: str) -> Dict[str, Any]:
        """清除任务的聚类缓存"""
        task_data = StorageService.load_batch_task(task_id)
        if not task_data:
            return {'success': False, 'error': '任务不存在'}
        
        if 'cluster_result' in task_data:
            del task_data['cluster_result']
            StorageService.save_batch_task(task_id, task_data)
            return {'success': True, 'message': '缓存已清除'}
        return {'success': True, 'message': '无缓存'}
    
    @staticmethod
    def _extract_errors(task_data: Dict) -> List[Dict]:
        """提取错误样本"""
        errors = []
        for hw in task_data.get('homework_items', []):
            evaluation = hw.get('evaluation', {})
            for err in evaluation.get('errors', []):
                errors.append({
                    'homework_id': hw.get('homework_id'),
                    'student_name': hw.get('student_name', ''),
                    'book_name': hw.get('book_name', ''),
                    'page_num': hw.get('page_num'),
                    'question_index': str(err.get('index', '')),
                    'base_effect': err.get('base_effect', {}),
                    'ai_result': err.get('ai_result', {}),
                    'explanation': err.get('explanation', '')
                })
        return errors
    
    @staticmethod
    def _get_correct_label(correct_val) -> str:
        """标准化判断结果为统一字符串"""
        if correct_val in [True, 'yes']:
            return 'yes'
        if correct_val in [False, 'no']:
            return 'no'
        return str(correct_val or '').strip().lower()
    
    @staticmethod
    def _group_by_error_pattern(errors: List[Dict]) -> Dict[str, Dict]:
        """
        按错误特征预分组：相同错误模式的样本归到一起
        
        特征key = (标准化base答案, 标准化AI答案, base判断, AI判断, 题号)
        同一题号下，答案和判断都一样的样本视为同一种错误模式
        """
        groups = defaultdict(lambda: {'samples': [], 'question_ids': set()})
        
        for err in errors:
            base = err.get('base_effect', {})
            ai = err.get('ai_result', {})
            
            # 标准化答案用于分组
            base_ans = normalize_answer(str(base.get('userAnswer', '') or ''))
            ai_ans = normalize_answer(str(ai.get('userAnswer', '') or ''))
            base_correct = ClusteringService._get_correct_label(base.get('correct'))
            ai_correct = ClusteringService._get_correct_label(ai.get('correct'))
            q_idx = str(err.get('question_index', '?'))
            
            # 特征key：同一题、同样的答案差异、同样的判断差异 → 同一种错误模式
            pattern_key = f"{q_idx}|{base_ans}|{ai_ans}|{base_correct}|{ai_correct}"
            
            groups[pattern_key]['samples'].append(err)
            page = err.get('page_num', '')
            groups[pattern_key]['question_ids'].add(f"{page}_{q_idx}" if page else q_idx)
        
        # 转换 set 为 list
        result = {}
        for key, group in groups.items():
            group['question_ids'] = list(group['question_ids'])
            result[key] = group
        
        return result
    
    @staticmethod
    def _analyze_single_pattern(group: Dict, subject_id: int = None, user_id: str = None) -> Dict:
        """分析单个错误模式的错误类型"""
        samples = group['samples']
        question_ids = group['question_ids']
        
        # 取第一个样本构建 prompt（同组内答案和判断都一样）
        representative = samples[0]
        base = representative.get('base_effect', {})
        ai = representative.get('ai_result', {})
        
        std_ans = str(base.get('answer', '') or base.get('mainAnswer', '') or '').strip()[:100]
        base_ans = str(base.get('userAnswer', '') or '').strip()[:100]
        ai_ans = str(ai.get('userAnswer', '') or '').strip()[:100]
        base_correct = base.get('correct')
        ai_correct = ai.get('correct')
        
        base_judge = '正确' if base_correct in [True, 'yes'] else ('错误' if base_correct in [False, 'no'] else '')
        ai_judge = '正确' if ai_correct in [True, 'yes'] else ('错误' if ai_correct in [False, 'no'] else '')
        
        sample_text = f"标准答案: {std_ans or '(无)'}"
        sample_text += f"\n人工标注: {base_ans or '(空)'}"
        if base_judge:
            sample_text += f" [{base_judge}]"
        sample_text += f"\nAI识别: {ai_ans or '(空)'}"
        if ai_judge:
            sample_text += f" [{ai_judge}]"
        
        if not base_ans and not ai_ans:
            return {
                'label': '数据异常',
                'reason': '无有效样本',
                'question_ids': question_ids,
                'samples': samples
            }
        
        # 根据学科选择错误类型列表
        error_types = SUBJECT_ERROR_TYPES.get(subject_id, DEFAULT_ERROR_TYPES)
        types_str = "、".join(error_types[:25])
        subject_name = SUBJECT_NAMES.get(subject_id, "")
        subject_hint = f"这是{subject_name}学科的作业。" if subject_name else ""
        
        prompt = f"""这是AI作业批改系统的错误分析任务。{subject_hint}

场景：学生手写答案 → AI识别文字并判分 → 与人工标注对比找差异。

错误样本（标准答案、人工标注、AI识别三方对比）：
{sample_text}

此错误模式影响 {len(samples)} 个学生。

分析AI识别与人工标注之间的差异，选择最准确的错误类型。
可选类型：{types_str}

返回JSON：{{"label":"错误类型","reason":"10字内原因"}}"""
        
        try:
            result = LLMService.call_deepseek(prompt, timeout=30, user_id=user_id)
            
            if isinstance(result, dict):
                if result.get('error'):
                    return {
                        'label': '分析失败', 'reason': result.get('error'),
                        'question_ids': question_ids, 'samples': samples
                    }
                response = result.get('content', '')
            else:
                response = str(result)
            
            response = response.strip()
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])
            
            parsed = json.loads(response)
            return {
                'label': parsed.get('label', '未知错误'),
                'reason': parsed.get('reason', ''),
                'question_ids': question_ids,
                'samples': samples
            }
        except Exception as e:
            print(f'[Clustering] 分析错误模式失败: {e}')
            return {
                'label': '分析失败', 'reason': str(e),
                'question_ids': question_ids, 'samples': samples
            }
    
    @staticmethod
    def _batch_analyze_patterns(pattern_groups: Dict[str, Dict], subject_id: int = None, user_id: str = None) -> Dict:
        """并发批量分析错误模式"""
        patterns_list = list(pattern_groups.values())[:50]  # 限制50种模式
        
        print(f'[Clustering] 开始并发LLM分析，共 {len(patterns_list)} 种错误模式，学科: {SUBJECT_NAMES.get(subject_id, "未知")}')
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_group = {
                executor.submit(ClusteringService._analyze_single_pattern, group, subject_id, user_id): group
                for group in patterns_list
            }
            
            for future in concurrent.futures.as_completed(future_to_group):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    group = future_to_group[future]
                    print(f'[Clustering] 并发任务失败: {e}')
                    results.append({
                        'label': '分析失败', 'reason': str(e),
                        'question_ids': group.get('question_ids', []),
                        'samples': group.get('samples', [])
                    })
        
        print(f'[Clustering] 并发分析完成，共 {len(results)} 个结果')
        
        clusters = ClusteringService._aggregate_pattern_results(results)
        
        print(f'[Clustering] 聚类完成，共 {len(clusters)} 个错误类型')
        return {'success': True, 'clusters': clusters}
    
    @staticmethod
    def _aggregate_pattern_results(results: List[Dict]) -> List[Dict]:
        """聚合错误模式分析结果：相同label的合并"""
        label_groups = defaultdict(lambda: {
            'question_ids': set(),
            'samples': [],
            'reasons': []
        })
        
        for r in results:
            label = r.get('label', '未知错误')
            for qid in r.get('question_ids', []):
                label_groups[label]['question_ids'].add(qid)
            label_groups[label]['samples'].extend(r.get('samples', []))
            reason = r.get('reason', '')
            if reason:
                label_groups[label]['reasons'].append(reason)
        
        clusters = []
        for label, group in label_groups.items():
            clusters.append({
                'label': label,
                'description': group['reasons'][0] if group['reasons'] else '',
                'question_ids': list(group['question_ids']),
                'error_count': len(group['samples']),
                'samples': group['samples']
            })
        
        clusters.sort(key=lambda x: x['error_count'], reverse=True)
        return clusters
    
    @staticmethod
    def clear_cache():
        """清除缓存（保留接口兼容）"""
        pass
