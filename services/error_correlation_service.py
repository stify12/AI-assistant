"""
错误关联分析服务 (US-20)

分析错误之间的关联关系，找出共同模式
"""
import json
import os
from collections import defaultdict
from typing import Optional, List, Dict, Any

from .storage_service import StorageService
from .llm_service import LLMService


class ErrorCorrelationService:
    """错误关联分析服务"""
    
    @staticmethod
    def analyze_correlations(
        subject_id: int = None,
        book_name: str = None,
        min_occurrence: int = 2
    ) -> Dict[str, Any]:
        """
        分析错误关联 (US-20.1)
        
        找出经常一起出现的错误模式
        """
        batch_dir = StorageService.BATCH_TASKS_DIR
        
        # 收集错误数据
        error_pairs = defaultdict(int)  # (error1, error2) -> count
        error_by_page = defaultdict(list)  # page_key -> [errors]
        error_types = defaultdict(int)
        
        if not os.path.exists(batch_dir):
            return {'correlations': [], 'error_types': {}}
        
        for filename in os.listdir(batch_dir):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(batch_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    task = json.load(f)
                
                # 筛选
                if subject_id is not None and task.get('subject_id') != subject_id:
                    continue
                if book_name:
                    task_book = task.get('book_name') or task.get('dataset_name', '')
                    if book_name not in task_book:
                        continue
                
                task_book = task.get('book_name') or task.get('dataset_name', 'unknown')
                
                results = task.get('results') or []
                for result in results:
                    page_num = result.get('page_number') or result.get('image_index', 0)
                    page_key = f"{task_book}_{page_num}"
                    
                    page_errors = []
                    questions = result.get('questions') or []
                    for q in questions:
                        is_correct = q.get('is_correct') or q.get('match', False)
                        if not is_correct:
                            error_type = q.get('error_type') or 'unknown'
                            page_errors.append(error_type)
                            error_types[error_type] += 1
                    
                    if len(page_errors) >= 2:
                        # 记录同页错误对
                        for i in range(len(page_errors)):
                            for j in range(i + 1, len(page_errors)):
                                pair = tuple(sorted([page_errors[i], page_errors[j]]))
                                error_pairs[pair] += 1
                    
                    error_by_page[page_key] = page_errors
                    
            except Exception:
                continue
        
        # 筛选高频关联
        correlations = []
        for (e1, e2), count in error_pairs.items():
            if count >= min_occurrence:
                # 计算关联强度
                total_e1 = error_types.get(e1, 1)
                total_e2 = error_types.get(e2, 1)
                strength = count / min(total_e1, total_e2)
                
                correlations.append({
                    'error1': e1,
                    'error2': e2,
                    'co_occurrence': count,
                    'strength': round(strength, 3),
                    'error1_total': total_e1,
                    'error2_total': total_e2
                })
        
        # 按关联强度排序
        correlations.sort(key=lambda x: x['strength'], reverse=True)
        
        return {
            'correlations': correlations[:20],
            'error_types': dict(error_types),
            'total_pages_analyzed': len(error_by_page)
        }
    
    @staticmethod
    def find_error_patterns(
        error_type: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        查找特定错误类型的模式 (US-20.2)
        """
        batch_dir = StorageService.BATCH_TASKS_DIR
        
        examples = []
        contexts = defaultdict(int)  # 上下文统计
        
        if not os.path.exists(batch_dir):
            return {'examples': [], 'contexts': {}}
        
        for filename in os.listdir(batch_dir):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(batch_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    task = json.load(f)
                
                book_name = task.get('book_name') or task.get('dataset_name', '')
                
                results = task.get('results') or []
                for result in results:
                    page_num = result.get('page_number', 0)
                    questions = result.get('questions') or []
                    
                    for q in questions:
                        q_error_type = q.get('error_type', '')
                        if q_error_type == error_type:
                            examples.append({
                                'book': book_name,
                                'page': page_num,
                                'question': q.get('question_number', ''),
                                'ai_answer': q.get('ai_answer', ''),
                                'expected': q.get('expected_answer') or q.get('baseline_answer', ''),
                                'task_id': task.get('task_id', filename.replace('.json', ''))
                            })
                            
                            # 统计上下文
                            contexts[book_name] += 1
                            
                            if len(examples) >= limit * 2:
                                break
                    
                    if len(examples) >= limit * 2:
                        break
                        
            except Exception:
                continue
        
        return {
            'error_type': error_type,
            'examples': examples[:limit],
            'total_count': len(examples),
            'contexts': dict(contexts)
        }

    
    @staticmethod
    def generate_correlation_report(
        subject_id: int = None
    ) -> Dict[str, Any]:
        """
        生成错误关联分析报告 (US-20.3)
        
        使用AI分析错误关联并给出建议
        """
        # 获取关联数据
        correlations = ErrorCorrelationService.analyze_correlations(
            subject_id=subject_id,
            min_occurrence=2
        )
        
        if not correlations.get('correlations'):
            return {
                'success': True,
                'report': '暂无足够的错误数据进行关联分析',
                'correlations': []
            }
        
        # 构建分析提示
        correlation_text = '\n'.join([
            f"- {c['error1']} 和 {c['error2']}: 共现{c['co_occurrence']}次, 关联强度{c['strength']}"
            for c in correlations['correlations'][:10]
        ])
        
        error_dist = '\n'.join([
            f"- {k}: {v}次"
            for k, v in sorted(correlations['error_types'].items(), key=lambda x: -x[1])[:10]
        ])
        
        prompt = f"""分析以下AI批改系统的错误关联数据，给出改进建议：

## 错误类型分布
{error_dist}

## 错误关联（经常一起出现的错误）
{correlation_text}

请分析：
1. 这些错误关联说明了什么问题？
2. 可能的根本原因是什么？
3. 针对性的改进建议

请用简洁的中文回答，不超过300字。"""

        try:
            llm = LLMService()
            response = llm.chat(
                messages=[{'role': 'user', 'content': prompt}],
                model='deepseek-v3.2'
            )
            
            report = response.get('content', '分析生成失败')
            
            return {
                'success': True,
                'report': report,
                'correlations': correlations['correlations'][:10],
                'error_types': correlations['error_types']
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'correlations': correlations['correlations'][:10]
            }
    
    @staticmethod
    def get_error_chain(
        task_id: str,
        page_num: int = None
    ) -> Dict[str, Any]:
        """
        获取错误链（同一任务/页面的连续错误）
        """
        batch_dir = StorageService.BATCH_TASKS_DIR
        filepath = os.path.join(batch_dir, f'{task_id}.json')
        
        if not os.path.exists(filepath):
            return {'chains': [], 'error': '任务不存在'}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                task = json.load(f)
            
            chains = []
            results = task.get('results') or []
            
            for result in results:
                result_page = result.get('page_number') or result.get('image_index', 0)
                if page_num is not None and result_page != page_num:
                    continue
                
                questions = result.get('questions') or []
                current_chain = []
                
                for q in questions:
                    is_correct = q.get('is_correct') or q.get('match', False)
                    if not is_correct:
                        current_chain.append({
                            'question': q.get('question_number', ''),
                            'error_type': q.get('error_type', 'unknown'),
                            'ai_answer': q.get('ai_answer', ''),
                            'expected': q.get('expected_answer') or q.get('baseline_answer', '')
                        })
                    else:
                        if len(current_chain) >= 2:
                            chains.append({
                                'page': result_page,
                                'length': len(current_chain),
                                'errors': current_chain
                            })
                        current_chain = []
                
                # 处理末尾的链
                if len(current_chain) >= 2:
                    chains.append({
                        'page': result_page,
                        'length': len(current_chain),
                        'errors': current_chain
                    })
            
            return {
                'task_id': task_id,
                'chains': chains,
                'total_chains': len(chains)
            }
        except Exception as e:
            return {'chains': [], 'error': str(e)}
