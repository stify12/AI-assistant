"""
错误聚类服务模块

并发批量调用LLM分析错误类型
支持结果缓存、学科上下文、流式返回
"""
import json
import concurrent.futures
from typing import Dict, List, Any, Generator
from collections import defaultdict

from .llm_service import LLMService
from .storage_service import StorageService


# 学科错误类型配置
SUBJECT_ERROR_TYPES = {
    # 语文(1)
    1: [
        "汉字识别错误", "形近字混淆", "同音字混淆", "汉字遗漏", "汉字多余",
        "拼音识别错误", "标点符号错误", "语句理解错误",
        "判分错误", "正确判为错误", "错误判为正确", "得分计算错误",
        "空白误识别", "格式差异", "内容缺失", "字迹模糊误判", "其他错误"
    ],
    # 数学(2)
    2: [
        "数字识别错误", "数字遗漏", "小数点遗漏", "负号遗漏",
        "运算符错误", "括号错误", "分数识别错误", "上下标错误",
        "公式解析错误", "单位识别错误", "单位遗漏",
        "判分错误", "正确判为错误", "错误判为正确", "得分计算错误",
        "空白误识别", "格式差异", "内容缺失", "字迹模糊误判", "其他错误"
    ],
    # 英语(0)
    0: [
        "字母识别错误", "大小写错误", "单词拼写错误", "单词遗漏",
        "标点符号错误", "语法理解错误",
        "判分错误", "正确判为错误", "错误判为正确", "得分计算错误",
        "空白误识别", "格式差异", "内容缺失", "字迹模糊误判", "其他错误"
    ],
    # 物理(3)
    3: [
        "数字识别错误", "数字遗漏", "小数点遗漏", "负号遗漏",
        "单位识别错误", "单位遗漏", "公式解析错误", "上下标错误",
        "符号识别错误", "运算符错误",
        "判分错误", "正确判为错误", "错误判为正确", "得分计算错误",
        "空白误识别", "格式差异", "内容缺失", "字迹模糊误判", "其他错误"
    ],
    # 化学(4)
    4: [
        "化学式错误", "元素符号错误", "上下标错误", "化学方程式错误",
        "数字识别错误", "数字遗漏",
        "判分错误", "正确判为错误", "错误判为正确", "得分计算错误",
        "空白误识别", "格式差异", "内容缺失", "字迹模糊误判", "其他错误"
    ],
    # 生物(5)
    5: [
        "汉字识别错误", "形近字混淆", "专业术语错误",
        "数字识别错误", "符号识别错误",
        "判分错误", "正确判为错误", "错误判为正确", "得分计算错误",
        "空白误识别", "格式差异", "内容缺失", "字迹模糊误判", "其他错误"
    ],
    # 地理(6)
    6: [
        "汉字识别错误", "形近字混淆", "地名识别错误",
        "数字识别错误", "符号识别错误",
        "判分错误", "正确判为错误", "错误判为正确", "得分计算错误",
        "空白误识别", "格式差异", "内容缺失", "字迹模糊误判", "其他错误"
    ]
}

# 学科名称映射
SUBJECT_NAMES = {
    0: "英语", 1: "语文", 2: "数学", 3: "物理", 4: "化学", 5: "生物", 6: "地理"
}

# 默认错误类型（通用）
DEFAULT_ERROR_TYPES = [
    "汉字识别错误", "形近字混淆", "同音字混淆", "汉字遗漏", "汉字多余",
    "判分错误", "正确判为错误", "错误判为正确", "得分计算错误", "答案匹配错误",
    "数字识别错误", "数字遗漏", "小数点遗漏", "负号遗漏",
    "字母识别错误", "大小写错误",
    "符号识别错误", "符号遗漏", "运算符错误", "括号错误",
    "单位识别错误", "单位遗漏",
    "公式解析错误", "分数识别错误", "上下标错误",
    "化学式错误", "元素符号错误",
    "空白误识别", "格式差异", "顺序错乱",
    "内容缺失", "内容多余", "答案不完整",
    "字迹模糊误判", "语义理解错误", "其他错误"
]


class ClusteringService:
    """错误聚类服务类"""
    
    @staticmethod
    def cluster_task_errors(task_id: str, use_llm: bool = True, subject_id: int = None, user_id: str = None) -> Dict[str, Any]:
        """智能聚类：并发调用LLM分析错误类型（支持缓存）"""
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
        
        # 按页码+题号分组
        by_question = defaultdict(list)
        for err in errors:
            page = err.get('page_num', '')
            q_idx = str(err.get('question_index', '?'))
            key = f"{page}_{q_idx}" if page else q_idx
            by_question[key].append(err)
        
        # 准备每道题的分析数据
        questions = []
        for key, q_errors in by_question.items():
            samples = ClusteringService._pick_representative(q_errors, max_count=2)
            if '_' in key:
                page, q_idx = key.rsplit('_', 1)
            else:
                page, q_idx = '', key
            
            questions.append({
                'key': key,
                'page': page,
                'question': q_idx,
                'count': len(q_errors),
                'samples': samples,
                'all_errors': q_errors
            })
        
        print(f'[Clustering] 开始并发LLM分析，共 {len(questions)} 道题，学科: {SUBJECT_NAMES.get(subject_id, "未知")}')
        
        # 并发批量调用LLM
        llm_result = ClusteringService._batch_analyze_with_llm(questions, subject_id=subject_id, user_id=user_id)
        
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
            'total_questions': len(by_question),
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
            'total_questions': len(by_question)
        }
    
    @staticmethod
    def cluster_task_errors_stream(task_id: str, subject_id: int = None, user_id: str = None) -> Generator[str, None, None]:
        """流式聚类：逐个返回分析结果"""
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
        
        # 按题号分组
        by_question = defaultdict(list)
        for err in errors:
            page = err.get('page_num', '')
            q_idx = str(err.get('question_index', '?'))
            key = f"{page}_{q_idx}" if page else q_idx
            by_question[key].append(err)
        
        questions = []
        for key, q_errors in by_question.items():
            samples = ClusteringService._pick_representative(q_errors, max_count=2)
            if '_' in key:
                page, q_idx = key.rsplit('_', 1)
            else:
                page, q_idx = '', key
            questions.append({
                'key': key, 'page': page, 'question': q_idx,
                'count': len(q_errors), 'samples': samples, 'all_errors': q_errors
            })
        
        total = len(questions)
        yield f"data: {json.dumps({'type': 'start', 'total': total, 'subject': SUBJECT_NAMES.get(subject_id, '未知')})}\n\n"
        
        # 逐个分析并返回
        results = []
        for i, q in enumerate(questions[:50]):  # 限制50道
            result = ClusteringService._analyze_single_question(q, subject_id=subject_id, user_id=user_id)
            results.append(result)
            yield f"data: {json.dumps({'type': 'progress', 'current': i+1, 'total': min(total, 50), 'result': result})}\n\n"
        
        # 聚合结果
        clusters = ClusteringService._aggregate_results(results, {q['key']: q for q in questions})
        
        # 保存到任务
        cluster_result = {
            'clusters': clusters,
            'total_errors': len(errors),
            'total_questions': len(by_question),
            'subject_id': subject_id
        }
        task_data['cluster_result'] = cluster_result
        StorageService.save_batch_task(task_id, task_data)
        
        yield f"data: {json.dumps({'type': 'complete', 'clusters': clusters, 'total_errors': len(errors), 'total_questions': len(by_question)})}\n\n"
    
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
    def _pick_representative(errors: List[Dict], max_count: int = 2) -> List[Dict]:
        """挑选代表性样本"""
        if len(errors) <= max_count:
            return errors
        
        def diff_score(err):
            base = str(err.get('base_effect', {}).get('userAnswer', '') or '')
            ai = str(err.get('ai_result', {}).get('userAnswer', '') or '')
            return abs(len(base) - len(ai)) + (10 if base != ai else 0)
        
        sorted_errors = sorted(errors, key=diff_score, reverse=True)
        return sorted_errors[:max_count]
    
    @staticmethod
    def _analyze_single_question(question: Dict, subject_id: int = None, user_id: str = None) -> Dict:
        """分析单道题的错误类型（带学科上下文）"""
        samples_text = []
        for s in question['samples']:
            base = s.get('base_effect', {})
            ai = s.get('ai_result', {})
            base_ans = str(base.get('userAnswer', '') or '').strip()[:100]
            ai_ans = str(ai.get('userAnswer', '') or '').strip()[:100]
            base_correct = base.get('correct')
            ai_correct = ai.get('correct')
            
            base_judge = '正确' if base_correct in [True, 'yes'] else ('错误' if base_correct in [False, 'no'] else '')
            ai_judge = '正确' if ai_correct in [True, 'yes'] else ('错误' if ai_correct in [False, 'no'] else '')
            
            if base_ans or ai_ans:
                line = f"人工标注: {base_ans or '(空)'}"
                if base_judge:
                    line += f" [{base_judge}]"
                line += f"\nAI识别: {ai_ans or '(空)'}"
                if ai_judge:
                    line += f" [{ai_judge}]"
                samples_text.append(line)
        
        if not samples_text:
            return {'key': question['key'], 'label': '数据异常', 'reason': '无有效样本'}
        
        # 根据学科选择错误类型列表
        error_types = SUBJECT_ERROR_TYPES.get(subject_id, DEFAULT_ERROR_TYPES)
        types_str = "、".join(error_types[:25])
        subject_name = SUBJECT_NAMES.get(subject_id, "")
        subject_hint = f"这是{subject_name}学科的作业。" if subject_name else ""
        
        prompt = f"""这是AI作业批改系统的错误分析任务。{subject_hint}

场景：学生手写答案，AI识别并判分。

错误样本：
{chr(10).join(samples_text)}

分析差异，选择最准确的错误类型。
可选类型：{types_str}

返回JSON：{{"label":"错误类型","reason":"10字内原因"}}"""
        
        try:
            result = LLMService.call_deepseek(prompt, timeout=30, user_id=user_id)
            
            if isinstance(result, dict):
                if result.get('error'):
                    return {'key': question['key'], 'label': '分析失败', 'reason': result.get('error')}
                response = result.get('content', '')
            else:
                response = str(result)
            
            response = response.strip()
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])
            
            parsed = json.loads(response)
            return {
                'key': question['key'],
                'label': parsed.get('label', '未知错误'),
                'reason': parsed.get('reason', '')
            }
        except Exception as e:
            print(f'[Clustering] 分析题目 {question["key"]} 失败: {e}')
            return {'key': question['key'], 'label': '分析失败', 'reason': str(e)}
    
    @staticmethod
    def _batch_analyze_with_llm(questions: List[Dict], subject_id: int = None, user_id: str = None) -> Dict:
        """并发批量调用LLM分析每道题"""
        questions_to_analyze = questions[:50]
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_q = {
                executor.submit(ClusteringService._analyze_single_question, q, subject_id, user_id): q 
                for q in questions_to_analyze
            }
            
            for future in concurrent.futures.as_completed(future_to_q):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    q = future_to_q[future]
                    print(f'[Clustering] 并发任务失败 {q["key"]}: {e}')
                    results.append({'key': q['key'], 'label': '分析失败', 'reason': str(e)})
        
        print(f'[Clustering] 并发分析完成，共 {len(results)} 个结果')
        
        question_map = {q['key']: q for q in questions}
        clusters = ClusteringService._aggregate_results(results, question_map)
        
        print(f'[Clustering] 聚类完成，共 {len(clusters)} 个错误类型')
        return {'success': True, 'clusters': clusters}
    
    @staticmethod
    def _aggregate_results(results: List[Dict], question_map: Dict) -> List[Dict]:
        """聚合分析结果"""
        label_groups = defaultdict(list)
        
        for r in results:
            label = r.get('label', '未知错误')
            key = r.get('key')
            if key:
                label_groups[label].append({
                    'key': key,
                    'reason': r.get('reason', '')
                })
        
        clusters = []
        for label, items in label_groups.items():
            question_ids = [item['key'] for item in items]
            reasons = [item['reason'] for item in items if item.get('reason')]
            
            all_samples = []
            error_count = 0
            for qid in question_ids:
                if qid in question_map:
                    q = question_map[qid]
                    all_samples.extend(q['all_errors'])
                    error_count += q['count']
            
            clusters.append({
                'label': label,
                'description': reasons[0] if reasons else '',
                'question_ids': question_ids,
                'error_count': error_count,
                'samples': all_samples
            })
        
        clusters.sort(key=lambda x: x['error_count'], reverse=True)
        return clusters
    
    @staticmethod
    def clear_cache():
        """清除缓存（保留接口兼容）"""
        pass
