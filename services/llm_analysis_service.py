"""
LLM 深度分析服务

使用 DeepSeek V3.2 模型对批量评估数据进行多维度深度分析，包括：
- 聚类分析
- 任务分析
- 维度分析（学科/书本/题型）
- 时间趋势分析
- 批次对比分析
- 异常检测分析
- 优化建议生成
"""
import json
import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any

from .llm_service import LLMService


# ============================================
# Prompt 模板定义
# ============================================

CLUSTER_ANALYSIS_PROMPT = """
你是一个专业的 AI 批改系统分析专家。请分析以下错误样本聚类，生成结构化的分析结果。

## 聚类信息
- 聚类键: {cluster_key}
- 样本数量: {sample_count}
- 错误类型: {error_type}
- 书本: {book_name}
- 页码范围: {page_range}

## 错误样本（最多展示10个）
{samples_json}

## 请生成以下分析结果（JSON格式）：
{{
    "cluster_name": "简洁的聚类名称（10字以内）",
    "cluster_description": "描述这类错误的共同特征（50字以内）",
    "root_cause": "分析这类错误的根本原因（100字以内）",
    "severity": "critical/high/medium/low（基于数量和影响判断）",
    "common_fix": "针对这类错误的通用修复建议（100字以内）",
    "pattern_insight": "深度分析这类错误的模式和规律（150字以内）"
}}

只返回 JSON，不要其他内容。
"""

TASK_ANALYSIS_PROMPT = """
你是一个专业的 AI 批改系统分析专家。请基于以下批量评估任务的统计数据和聚类分析结果，生成任务级别的综合分析报告。

## 任务统计
- 任务ID: {task_id}
- 总题目数: {total_questions}
- 错误数: {total_errors}
- 错误率: {error_rate:.2%}

## 错误类型分布
{error_type_distribution}

## 学科分布
{subject_distribution}

## 聚类分析结果（Top 5）
{clusters_summary}

## 请生成以下分析结果（JSON格式）：
{{
    "task_summary": "3-5句话总结该任务的整体情况",
    "accuracy_analysis": "分析准确率及其影响因素",
    "main_issues": [
        {{"issue": "问题描述", "count": 数量, "severity": "high/medium/low"}}
    ],
    "error_distribution": "分析错误的分布特征",
    "risk_assessment": "评估该任务暴露的风险",
    "improvement_priority": ["改进项1", "改进项2", "改进项3"],
    "actionable_suggestions": [
        {{"title": "建议标题", "description": "具体描述", "expected_impact": "预期效果"}}
    ]
}}

只返回 JSON，不要其他内容。
"""

DIMENSION_ANALYSIS_PROMPT = """
你是一个专业的 AI 批改系统分析专家。请分析以下{dimension_name}维度的错误数据。

## {dimension_name}信息
- 名称: {name}
- 错误数: {error_count}
- 总题目数: {total}
- 错误率: {error_rate:.2%}

## 错误样本摘要
{samples_summary}

## 请生成以下分析结果（JSON格式）：
{{
    "summary": "总结该{dimension_name}的整体批改情况（50字以内）",
    "common_error_patterns": ["常见错误模式1", "常见错误模式2"],
    "specific_issues": ["该{dimension_name}特有的问题1", "问题2"],
    "improvement_suggestions": ["改进建议1", "改进建议2"]
}}

只返回 JSON，不要其他内容。
"""

TREND_ANALYSIS_PROMPT = """
你是一个专业的 AI 批改系统分析专家。请分析以下时间趋势数据。

## 时间范围
{time_range}

## 数据点
{data_points}

## 准确率趋势
{accuracy_trend_data}

## 请生成以下分析结果（JSON格式）：
{{
    "trend_summary": "整体趋势总结（50字以内）",
    "accuracy_trend": "improved/declined/stable",
    "error_pattern_evolution": "错误模式的演变分析",
    "improvement_areas": ["改进的方面1", "改进的方面2"],
    "regression_areas": ["退步的方面1", "退步的方面2"],
    "prediction": "基于趋势的预测",
    "recommendations": ["建议1", "建议2"]
}}

只返回 JSON，不要其他内容。
"""

COMPARISON_ANALYSIS_PROMPT = """
你是一个专业的 AI 批改系统分析专家。请对比以下两个批次的评估结果。

## 批次1信息
- 任务ID: {task_id_1}
- 时间: {time_1}
- 总题目数: {total_1}
- 错误数: {errors_1}
- 错误率: {error_rate_1:.2%}
- 主要错误类型: {main_errors_1}

## 批次2信息
- 任务ID: {task_id_2}
- 时间: {time_2}
- 总题目数: {total_2}
- 错误数: {errors_2}
- 错误率: {error_rate_2:.2%}
- 主要错误类型: {main_errors_2}

## 请生成对比分析结果（JSON格式）：
{{
    "comparison_summary": "整体对比分析（100字以内）",
    "accuracy_change": {{
        "direction": "improved/declined/stable",
        "percentage": 变化百分比,
        "analysis": "变化原因分析"
    }},
    "error_pattern_changes": {{
        "new_patterns": ["新增的错误模式"],
        "reduced_patterns": ["减少的错误模式"],
        "analysis": "模式变化分析"
    }},
    "improvement_items": ["具体改进的地方"],
    "regression_items": ["退步的地方"],
    "root_cause_analysis": "导致改进或退步的根本原因分析",
    "recommendations": ["后续建议1", "建议2"]
}}

只返回 JSON，不要其他内容。
"""

ANOMALY_ANALYSIS_PROMPT = """
你是一个专业的 AI 批改系统分析专家。请分析以下批改不一致的异常情况。

## 异常信息
- 学生答案: {base_user_answer}
- 出现次数: {occurrence_count}
- 正确批改次数: {correct_count}
- 错误批改次数: {incorrect_count}
- 不一致率: {inconsistency_rate:.2%}

## 正确批改案例
{correct_cases}

## 错误批改案例
{incorrect_cases}

## 请生成以下分析结果（JSON格式）：
{{
    "description": "描述这个不一致问题（100字以内）",
    "root_cause": "分析导致不一致的根本原因",
    "suggested_action": "具体的改进建议（包括 Prompt 修改建议）",
    "severity": "critical/high/medium/low"
}}

只返回 JSON，不要其他内容。
"""

SUGGESTION_GENERATION_PROMPT = """
你是一个专业的 AI 批改系统优化专家。请基于以下分析结果，生成具体可执行的优化建议。

## 任务分析摘要
{task_summary}

## 主要问题聚类
{main_clusters}

## 异常检测结果
{anomalies}

## 请生成最多5条高价值优化建议（JSON数组格式）：
[
    {{
        "title": "建议标题（10字以内）",
        "category": "Prompt优化/数据集优化/评分逻辑优化/OCR优化",
        "description": "详细描述（100字以内）",
        "priority": "P0/P1/P2",
        "expected_impact": "预期效果（50字以内）",
        "implementation_steps": ["步骤1", "步骤2", "步骤3"],
        "prompt_template": "如果是Prompt优化，提供具体的Prompt修改建议，否则为null"
    }}
]

按优先级排序，只返回 JSON 数组，不要其他内容。
"""


class LLMAnalysisService:
    """LLM 深度分析服务"""
    
    MODEL = 'deepseek-v3.2'
    MAX_CONCURRENT = 10
    DEFAULT_TIMEOUT = 60
    MAX_RETRIES = 3
    TEMPERATURE = 0.2
    SYSTEM_PROMPT = '你是一个专业的 AI 批改系统分析专家，擅长数据分析和问题诊断。请用中文回答。'
    
    @classmethod
    async def analyze_cluster(cls, cluster_data: dict, task_id: str = None, user_id: str = None) -> dict:
        """
        分析单个聚类
        
        Args:
            cluster_data: {
                cluster_key: str,
                samples: [{homework_id, error_type, ai_answer, expected_answer, ...}],
                sample_count: int,
                error_type: str,
                book_name: str,
                page_range: str
            }
            task_id: 任务ID（用于日志）
            user_id: 用户ID
            
        Returns:
            dict: {
                cluster_id: str,
                cluster_name: str,
                cluster_description: str,
                root_cause: str,
                severity: str,
                common_fix: str,
                pattern_insight: str
            }
        """
        # 准备样本数据（最多10个）
        samples = cluster_data.get('samples', [])[:10]
        samples_json = json.dumps([{
            'homework_id': s.get('homework_id', ''),
            'question_index': s.get('question_index', 0),
            'ai_answer': str(s.get('ai_answer', ''))[:100],
            'expected_answer': str(s.get('expected_answer', ''))[:100],
            'error_type': s.get('error_type', '')
        } for s in samples], ensure_ascii=False, indent=2)
        
        prompt = CLUSTER_ANALYSIS_PROMPT.format(
            cluster_key=cluster_data.get('cluster_key', ''),
            sample_count=cluster_data.get('sample_count', len(samples)),
            error_type=cluster_data.get('error_type', '未知'),
            book_name=cluster_data.get('book_name', '未知'),
            page_range=cluster_data.get('page_range', '未知'),
            samples_json=samples_json
        )
        
        result = await LLMService.call_with_retry(
            prompt=prompt,
            system_prompt=cls.SYSTEM_PROMPT,
            model=cls.MODEL,
            temperature=cls.TEMPERATURE,
            timeout=cls.DEFAULT_TIMEOUT,
            max_retries=cls.MAX_RETRIES,
            user_id=user_id
        )
        
        # 记录日志
        LLMService.log_llm_call(
            task_id=task_id,
            analysis_type='cluster',
            target_id=cluster_data.get('cluster_key', ''),
            model=cls.MODEL,
            tokens=result.get('tokens', {}),
            duration_ms=result.get('duration', 0),
            status='success' if result.get('success') else 'failed',
            retry_count=result.get('retry_count', 0),
            error_type=result.get('error_type'),
            error_message=result.get('error')
        )
        
        if not result.get('success'):
            return {
                'cluster_id': str(uuid.uuid4())[:8],
                'cluster_name': cluster_data.get('error_type', '未知错误'),
                'cluster_description': '分析失败',
                'root_cause': result.get('error', '未知错误'),
                'severity': 'medium',
                'common_fix': '',
                'pattern_insight': '',
                'error': result.get('error')
            }
        
        # 解析 LLM 响应
        parsed = LLMService.parse_json_response(result.get('content', ''))
        if not parsed:
            return {
                'cluster_id': str(uuid.uuid4())[:8],
                'cluster_name': cluster_data.get('error_type', '未知错误'),
                'cluster_description': '解析失败',
                'root_cause': '无法解析 LLM 响应',
                'severity': 'medium',
                'common_fix': '',
                'pattern_insight': '',
                'error': 'parse_error'
            }
        
        return {
            'cluster_id': str(uuid.uuid4())[:8],
            'cluster_name': parsed.get('cluster_name', ''),
            'cluster_description': parsed.get('cluster_description', ''),
            'root_cause': parsed.get('root_cause', ''),
            'severity': parsed.get('severity', 'medium'),
            'common_fix': parsed.get('common_fix', ''),
            'pattern_insight': parsed.get('pattern_insight', ''),
            'tokens': result.get('tokens', {})
        }
    
    @classmethod
    async def analyze_task(cls, task_id: str, clusters: List[dict], quick_stats: dict, user_id: str = None) -> dict:
        """
        分析任务整体
        
        Args:
            task_id: 任务ID
            clusters: 聚类分析结果列表
            quick_stats: 快速统计数据
            user_id: 用户ID
            
        Returns:
            dict: 任务分析结果
        """
        # 准备错误类型分布
        error_type_dist = quick_stats.get('error_type_distribution', {})
        error_type_str = '\n'.join([f"- {k}: {v} 个" for k, v in error_type_dist.items()])
        
        # 准备学科分布
        subject_dist = quick_stats.get('subject_distribution', {})
        subject_str = '\n'.join([f"- {k}: {v} 个错误" for k, v in subject_dist.items()])
        
        # 准备聚类摘要（Top 5）
        top_clusters = sorted(clusters, key=lambda x: x.get('sample_count', 0), reverse=True)[:5]
        clusters_str = '\n'.join([
            f"- {c.get('cluster_name', '未知')}: {c.get('sample_count', 0)} 个样本，严重程度 {c.get('severity', 'medium')}"
            for c in top_clusters
        ])
        
        total_questions = quick_stats.get('total_questions', 0)
        total_errors = quick_stats.get('total_errors', 0)
        error_rate = total_errors / total_questions if total_questions > 0 else 0
        
        prompt = TASK_ANALYSIS_PROMPT.format(
            task_id=task_id,
            total_questions=total_questions,
            total_errors=total_errors,
            error_rate=error_rate,
            error_type_distribution=error_type_str or '无数据',
            subject_distribution=subject_str or '无数据',
            clusters_summary=clusters_str or '无聚类数据'
        )
        
        result = await LLMService.call_with_retry(
            prompt=prompt,
            system_prompt=cls.SYSTEM_PROMPT,
            model=cls.MODEL,
            temperature=cls.TEMPERATURE,
            timeout=cls.DEFAULT_TIMEOUT,
            max_retries=cls.MAX_RETRIES,
            user_id=user_id
        )
        
        # 记录日志
        LLMService.log_llm_call(
            task_id=task_id,
            analysis_type='task',
            target_id=task_id,
            model=cls.MODEL,
            tokens=result.get('tokens', {}),
            duration_ms=result.get('duration', 0),
            status='success' if result.get('success') else 'failed',
            retry_count=result.get('retry_count', 0),
            error_type=result.get('error_type'),
            error_message=result.get('error')
        )
        
        if not result.get('success'):
            return {'error': result.get('error', '分析失败')}
        
        parsed = LLMService.parse_json_response(result.get('content', ''))
        if not parsed:
            return {'error': '解析失败'}
        
        parsed['tokens'] = result.get('tokens', {})
        return parsed

    
    @classmethod
    async def analyze_dimension(cls, dimension: str, data: dict, task_id: str = None, user_id: str = None) -> dict:
        """
        分析特定维度（学科/书本/题型）
        
        Args:
            dimension: subject|book|question_type
            data: 该维度的统计数据
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            dict: 维度分析结果
        """
        dimension_names = {
            'subject': '学科',
            'book': '书本',
            'question_type': '题型'
        }
        dimension_name = dimension_names.get(dimension, '维度')
        
        total = data.get('total', 0)
        error_count = data.get('error_count', 0)
        error_rate = error_count / total if total > 0 else 0
        
        # 准备样本摘要
        samples = data.get('samples', [])[:5]
        samples_str = '\n'.join([
            f"- 题目{s.get('question_index', 0)}: AI答案'{str(s.get('ai_answer', ''))[:50]}' vs 期望'{str(s.get('expected_answer', ''))[:50]}'"
            for s in samples
        ]) or '无样本数据'
        
        prompt = DIMENSION_ANALYSIS_PROMPT.format(
            dimension_name=dimension_name,
            dimension=dimension,
            name=data.get('name', '未知'),
            error_count=error_count,
            total=total,
            error_rate=error_rate,
            samples_summary=samples_str
        )
        
        result = await LLMService.call_with_retry(
            prompt=prompt,
            system_prompt=cls.SYSTEM_PROMPT,
            model=cls.MODEL,
            temperature=cls.TEMPERATURE,
            timeout=cls.DEFAULT_TIMEOUT,
            max_retries=cls.MAX_RETRIES,
            user_id=user_id
        )
        
        # 记录日志
        LLMService.log_llm_call(
            task_id=task_id,
            analysis_type=dimension,
            target_id=data.get('name', ''),
            model=cls.MODEL,
            tokens=result.get('tokens', {}),
            duration_ms=result.get('duration', 0),
            status='success' if result.get('success') else 'failed',
            retry_count=result.get('retry_count', 0),
            error_type=result.get('error_type'),
            error_message=result.get('error')
        )
        
        if not result.get('success'):
            return {'error': result.get('error', '分析失败')}
        
        parsed = LLMService.parse_json_response(result.get('content', ''))
        if not parsed:
            return {'error': '解析失败'}
        
        parsed['tokens'] = result.get('tokens', {})
        return parsed
    
    @classmethod
    async def analyze_trend(cls, trend_data: List[dict], time_range: str, task_id: str = None, user_id: str = None) -> dict:
        """
        分析时间趋势
        
        Args:
            trend_data: 趋势数据点列表
            time_range: 时间范围描述
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            dict: 趋势分析结果
        """
        # 准备数据点
        data_points_str = '\n'.join([
            f"- {d.get('date', '')}: 错误率 {d.get('error_rate', 0):.2%}, 错误数 {d.get('error_count', 0)}"
            for d in trend_data
        ]) or '无数据'
        
        # 准备准确率趋势
        accuracy_data = [
            {'date': d.get('date', ''), 'accuracy': 1 - d.get('error_rate', 0)}
            for d in trend_data
        ]
        accuracy_str = json.dumps(accuracy_data, ensure_ascii=False)
        
        prompt = TREND_ANALYSIS_PROMPT.format(
            time_range=time_range,
            data_points=data_points_str,
            accuracy_trend_data=accuracy_str
        )
        
        result = await LLMService.call_with_retry(
            prompt=prompt,
            system_prompt=cls.SYSTEM_PROMPT,
            model=cls.MODEL,
            temperature=cls.TEMPERATURE,
            timeout=cls.DEFAULT_TIMEOUT,
            max_retries=cls.MAX_RETRIES,
            user_id=user_id
        )
        
        # 记录日志
        LLMService.log_llm_call(
            task_id=task_id,
            analysis_type='trend',
            target_id=time_range,
            model=cls.MODEL,
            tokens=result.get('tokens', {}),
            duration_ms=result.get('duration', 0),
            status='success' if result.get('success') else 'failed',
            retry_count=result.get('retry_count', 0),
            error_type=result.get('error_type'),
            error_message=result.get('error')
        )
        
        if not result.get('success'):
            return {'error': result.get('error', '分析失败')}
        
        parsed = LLMService.parse_json_response(result.get('content', ''))
        if not parsed:
            return {'error': '解析失败'}
        
        parsed['tokens'] = result.get('tokens', {})
        return parsed
    
    @classmethod
    async def compare_batches(cls, batch1_data: dict, batch2_data: dict, task_id: str = None, user_id: str = None) -> dict:
        """
        对比两个批次
        
        Args:
            batch1_data: 批次1数据
            batch2_data: 批次2数据
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            dict: 对比分析结果
        """
        total_1 = batch1_data.get('total_questions', 0)
        errors_1 = batch1_data.get('total_errors', 0)
        error_rate_1 = errors_1 / total_1 if total_1 > 0 else 0
        
        total_2 = batch2_data.get('total_questions', 0)
        errors_2 = batch2_data.get('total_errors', 0)
        error_rate_2 = errors_2 / total_2 if total_2 > 0 else 0
        
        prompt = COMPARISON_ANALYSIS_PROMPT.format(
            task_id_1=batch1_data.get('task_id', ''),
            time_1=batch1_data.get('created_at', ''),
            total_1=total_1,
            errors_1=errors_1,
            error_rate_1=error_rate_1,
            main_errors_1=', '.join(list(batch1_data.get('error_types', {}).keys())[:3]) or '无',
            task_id_2=batch2_data.get('task_id', ''),
            time_2=batch2_data.get('created_at', ''),
            total_2=total_2,
            errors_2=errors_2,
            error_rate_2=error_rate_2,
            main_errors_2=', '.join(list(batch2_data.get('error_types', {}).keys())[:3]) or '无'
        )
        
        result = await LLMService.call_with_retry(
            prompt=prompt,
            system_prompt=cls.SYSTEM_PROMPT,
            model=cls.MODEL,
            temperature=cls.TEMPERATURE,
            timeout=cls.DEFAULT_TIMEOUT,
            max_retries=cls.MAX_RETRIES,
            user_id=user_id
        )
        
        # 记录日志
        LLMService.log_llm_call(
            task_id=task_id,
            analysis_type='compare',
            target_id=f"{batch1_data.get('task_id', '')}_{batch2_data.get('task_id', '')}",
            model=cls.MODEL,
            tokens=result.get('tokens', {}),
            duration_ms=result.get('duration', 0),
            status='success' if result.get('success') else 'failed',
            retry_count=result.get('retry_count', 0),
            error_type=result.get('error_type'),
            error_message=result.get('error')
        )
        
        if not result.get('success'):
            return {'error': result.get('error', '分析失败')}
        
        parsed = LLMService.parse_json_response(result.get('content', ''))
        if not parsed:
            return {'error': '解析失败'}
        
        parsed['tokens'] = result.get('tokens', {})
        return parsed
    
    @classmethod
    async def analyze_anomaly(cls, anomaly_data: dict, task_id: str = None, user_id: str = None) -> dict:
        """
        分析单个异常
        
        Args:
            anomaly_data: 异常数据
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            dict: 异常分析结果
        """
        correct_cases = anomaly_data.get('correct_cases', [])
        incorrect_cases = anomaly_data.get('incorrect_cases', [])
        total = len(correct_cases) + len(incorrect_cases)
        inconsistency_rate = len(incorrect_cases) / total if total > 0 else 0
        
        correct_str = '\n'.join([
            f"- 作业 {c.get('homework_id', '')}: {c.get('ai_result', '')}"
            for c in correct_cases[:3]
        ]) or '无'
        
        incorrect_str = '\n'.join([
            f"- 作业 {c.get('homework_id', '')}: {c.get('ai_result', '')}"
            for c in incorrect_cases[:3]
        ]) or '无'
        
        prompt = ANOMALY_ANALYSIS_PROMPT.format(
            base_user_answer=anomaly_data.get('base_user_answer', '')[:200],
            occurrence_count=total,
            correct_count=len(correct_cases),
            incorrect_count=len(incorrect_cases),
            inconsistency_rate=inconsistency_rate,
            correct_cases=correct_str,
            incorrect_cases=incorrect_str
        )
        
        result = await LLMService.call_with_retry(
            prompt=prompt,
            system_prompt=cls.SYSTEM_PROMPT,
            model=cls.MODEL,
            temperature=cls.TEMPERATURE,
            timeout=cls.DEFAULT_TIMEOUT,
            max_retries=cls.MAX_RETRIES,
            user_id=user_id
        )
        
        # 记录日志
        LLMService.log_llm_call(
            task_id=task_id,
            analysis_type='anomaly',
            target_id=anomaly_data.get('anomaly_id', ''),
            model=cls.MODEL,
            tokens=result.get('tokens', {}),
            duration_ms=result.get('duration', 0),
            status='success' if result.get('success') else 'failed',
            retry_count=result.get('retry_count', 0),
            error_type=result.get('error_type'),
            error_message=result.get('error')
        )
        
        if not result.get('success'):
            return {'error': result.get('error', '分析失败')}
        
        parsed = LLMService.parse_json_response(result.get('content', ''))
        if not parsed:
            return {'error': '解析失败'}
        
        parsed['tokens'] = result.get('tokens', {})
        return parsed
    
    @classmethod
    async def generate_suggestions(cls, task_summary: str, main_clusters: List[dict], 
                                   anomalies: List[dict], task_id: str = None, user_id: str = None) -> List[dict]:
        """
        生成优化建议
        
        Args:
            task_summary: 任务分析摘要
            main_clusters: 主要聚类列表
            anomalies: 异常列表
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            list: 优化建议列表（最多5条）
        """
        # 准备聚类摘要
        clusters_str = '\n'.join([
            f"- {c.get('cluster_name', '未知')}: {c.get('sample_count', 0)} 个样本，根因: {c.get('root_cause', '未知')[:50]}"
            for c in main_clusters[:5]
        ]) or '无聚类数据'
        
        # 准备异常摘要
        anomalies_str = '\n'.join([
            f"- {a.get('anomaly_type', '未知')}: 不一致率 {a.get('inconsistency_rate', 0):.2%}"
            for a in anomalies[:5]
        ]) or '无异常数据'
        
        prompt = SUGGESTION_GENERATION_PROMPT.format(
            task_summary=task_summary or '无摘要',
            main_clusters=clusters_str,
            anomalies=anomalies_str
        )
        
        result = await LLMService.call_with_retry(
            prompt=prompt,
            system_prompt=cls.SYSTEM_PROMPT,
            model=cls.MODEL,
            temperature=cls.TEMPERATURE,
            timeout=cls.DEFAULT_TIMEOUT,
            max_retries=cls.MAX_RETRIES,
            user_id=user_id
        )
        
        # 记录日志
        LLMService.log_llm_call(
            task_id=task_id,
            analysis_type='suggestion',
            target_id=task_id or '',
            model=cls.MODEL,
            tokens=result.get('tokens', {}),
            duration_ms=result.get('duration', 0),
            status='success' if result.get('success') else 'failed',
            retry_count=result.get('retry_count', 0),
            error_type=result.get('error_type'),
            error_message=result.get('error')
        )
        
        if not result.get('success'):
            return []
        
        parsed = LLMService.extract_json_array(result.get('content', ''))
        if not parsed:
            parsed = LLMService.parse_json_response(result.get('content', ''))
            if isinstance(parsed, dict) and 'suggestions' in parsed:
                parsed = parsed['suggestions']
        
        if not isinstance(parsed, list):
            return []
        
        # 添加 ID 并限制数量
        suggestions = []
        for i, s in enumerate(parsed[:5]):
            s['suggestion_id'] = f's{i+1}'
            suggestions.append(s)
        
        return suggestions
    
    @classmethod
    async def parallel_analyze_clusters(cls, clusters: List[dict], task_id: str = None, user_id: str = None) -> List[dict]:
        """
        并行分析多个聚类
        
        Args:
            clusters: 聚类数据列表
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            list: 聚类分析结果列表
        """
        # 准备并行任务
        prompts = []
        for cluster in clusters:
            samples = cluster.get('samples', [])[:10]
            samples_json = json.dumps([{
                'homework_id': s.get('homework_id', ''),
                'question_index': s.get('question_index', 0),
                'ai_answer': str(s.get('ai_answer', ''))[:100],
                'expected_answer': str(s.get('expected_answer', ''))[:100],
                'error_type': s.get('error_type', '')
            } for s in samples], ensure_ascii=False, indent=2)
            
            prompt = CLUSTER_ANALYSIS_PROMPT.format(
                cluster_key=cluster.get('cluster_key', ''),
                sample_count=cluster.get('sample_count', len(samples)),
                error_type=cluster.get('error_type', '未知'),
                book_name=cluster.get('book_name', '未知'),
                page_range=cluster.get('page_range', '未知'),
                samples_json=samples_json
            )
            
            prompts.append({
                'id': cluster.get('cluster_key', ''),
                'prompt': prompt,
                'system_prompt': cls.SYSTEM_PROMPT
            })
        
        # 并行调用
        results = await LLMService.parallel_call(
            prompts=prompts,
            max_concurrent=cls.MAX_CONCURRENT,
            model=cls.MODEL,
            temperature=cls.TEMPERATURE,
            timeout=cls.DEFAULT_TIMEOUT,
            max_retries=cls.MAX_RETRIES,
            user_id=user_id
        )
        
        # 处理结果
        analyzed_clusters = []
        for i, result in enumerate(results):
            cluster = clusters[i] if i < len(clusters) else {}
            
            # 记录日志
            LLMService.log_llm_call(
                task_id=task_id,
                analysis_type='cluster',
                target_id=result.get('id', ''),
                model=cls.MODEL,
                tokens=result.get('tokens', {}),
                duration_ms=result.get('duration', 0),
                status='success' if result.get('success') else 'failed',
                retry_count=result.get('retry_count', 0),
                error_type=result.get('error_type'),
                error_message=result.get('error')
            )
            
            if result.get('success'):
                parsed = LLMService.parse_json_response(result.get('content', ''))
                if parsed:
                    analyzed_clusters.append({
                        'cluster_id': str(uuid.uuid4())[:8],
                        'cluster_key': cluster.get('cluster_key', ''),
                        'cluster_name': parsed.get('cluster_name', ''),
                        'cluster_description': parsed.get('cluster_description', ''),
                        'root_cause': parsed.get('root_cause', ''),
                        'severity': parsed.get('severity', 'medium'),
                        'common_fix': parsed.get('common_fix', ''),
                        'pattern_insight': parsed.get('pattern_insight', ''),
                        'sample_count': cluster.get('sample_count', 0),
                        'samples': cluster.get('samples', [])
                    })
                    continue
            
            # 失败时使用默认值
            analyzed_clusters.append({
                'cluster_id': str(uuid.uuid4())[:8],
                'cluster_key': cluster.get('cluster_key', ''),
                'cluster_name': cluster.get('error_type', '未知错误'),
                'cluster_description': '分析失败',
                'root_cause': result.get('error', '未知错误'),
                'severity': 'medium',
                'common_fix': '',
                'pattern_insight': '',
                'sample_count': cluster.get('sample_count', 0),
                'samples': cluster.get('samples', []),
                'error': result.get('error')
            })
        
        return analyzed_clusters
    
    @classmethod
    def run_parallel_analyze_clusters(cls, clusters: List[dict], task_id: str = None, user_id: str = None) -> List[dict]:
        """
        同步包装的并行聚类分析方法
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            cls.parallel_analyze_clusters(clusters, task_id, user_id)
        )
