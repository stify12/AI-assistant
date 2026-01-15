"""
语义级评估服务
提供基于 LLM 的语义级 AI 批改效果评估功能
"""
import json
from typing import List, Dict, Any, Tuple, Optional

from services.llm_service import LLMService
from services.config_service import ConfigService
from utils.text_utils import normalize_answer


# ========== 提示词加载 ==========

def load_prompt(key: str, default: str = '') -> str:
    """
    从 prompts.json 加载提示词
    
    Args:
        key: 提示词的 key 字段
        default: 默认值
        
    Returns:
        提示词内容
    """
    try:
        prompts = ConfigService.load_prompts()
        for prompt in prompts:
            if prompt.get('key') == key:
                return prompt.get('content', default)
        return default
    except Exception:
        return default


# ========== 默认提示词模板（作为 fallback）==========

DEFAULT_SEMANTIC_EVAL_SYSTEM = """你是 AI 批改效果评估专家，专门分析 AI 批改系统的识别能力和判断能力。
你的任务是对比「人工标注的基准效果」和「AI 批改结果」，精准定位 AI 的问题所在。
请严格按照要求的 JSON 格式输出，不要输出其他内容。"""

DEFAULT_SEMANTIC_EVAL_TEMPLATE = """【评估背景】
- 学科：{subject}
- 题型：{question_type}
- 题号：{index}

【数据对比】
┌─────────────┬────────────────────┬────────────────────┐
│    项目      │   基准效果(人工)    │    AI批改结果       │
├─────────────┼────────────────────┼────────────────────┤
│  标准答案    │ {standard_answer}                        │
├─────────────┼────────────────────┼────────────────────┤
│  学生答案    │ {base_user_answer}  │ {ai_user_answer}   │
├─────────────┼────────────────────┼────────────────────┤
│  判断结果    │ {base_correct}      │ {ai_correct}       │
└─────────────┴────────────────────┴────────────────────┘

【评估任务】
请从以下三个维度分析 AI 批改效果：

1️⃣ 识别能力分析
   - AI 识别的学生答案是否与人工识别一致？
   - 如果不一致，是完全错误还是语义等价？
   - 语义等价示例：3/4 ≈ 0.75、x+1 ≈ 1+x、ABC ≈ A,B,C

2️⃣ 判断能力分析
   - AI 的对错判断是否与人工判断一致？
   - 如果不一致，AI 判断的依据可能是什么？

3️⃣ 幻觉检测
   - 是否存在 AI 幻觉？（学生答错，但 AI 把答案"脑补"成标准答案）
   - 幻觉特征：base_correct=no + ai_user_answer≈standard_answer

【输出格式】
严格按以下 JSON 格式输出，不要输出其他内容：

{{
  "verdict": "PASS或FAIL",
  "verdict_cn": "通过或不通过",
  
  "recognition": {{
    "status": "一致或语义等价或不一致",
    "base": "人工识别的答案",
    "ai": "AI识别的答案",
    "diff_type": "无差异或格式差异或内容差异或完全错误",
    "detail": "具体差异说明"
  }},
  
  "judgment": {{
    "status": "一致或不一致",
    "base": "yes或no",
    "ai": "yes或no",
    "detail": "判断差异说明"
  }},
  
  "hallucination": {{
    "detected": true或false,
    "detail": "幻觉说明，无则为空字符串"
  }},
  
  "error_type": "完全正确或识别正确-判断错误或识别错误-判断正确或识别错误-判断错误或语义等价或AI幻觉",
  "severity": "none或low或medium或high或critical",
  "severity_cn": "无或轻微或中等或严重或致命",
  
  "summary": "一句话总结评估结果",
  "suggestion": "改进建议，无则为空字符串"
}}

【严重程度定义】
- none: 完全正确
- low: 格式差异，不影响结果
- medium: 识别有偏差但判断正确
- high: 判断错误
- critical: AI幻觉（最严重）"""

DEFAULT_BATCH_EVAL_SYSTEM = """你是 AI 批改效果评估专家，需要批量分析多道题目的 AI 批改效果。
请严格按照要求的 JSON 数组格式输出，不要输出其他内容。"""

DEFAULT_BATCH_EVAL_TEMPLATE = """【评估数据】
学科：{subject}
题型：{question_type}

以下是需要评估的题目列表（JSON 格式）：
{questions_json}

【评估要求】
对每道题目进行独立评估，重点关注：
1. 识别是否一致或语义等价
2. 判断是否正确
3. 是否存在 AI 幻觉（学生答错但AI识别成标准答案）

【输出格式】
输出 JSON 数组，每个元素对应一道题：
[
  {{
    "index": "题号",
    "verdict": "PASS或FAIL",
    "error_type": "完全正确或识别正确-判断错误或识别错误-判断正确或识别错误-判断错误或语义等价或AI幻觉",
    "severity": "none或low或medium或high或critical",
    "recognition_status": "一致或语义等价或不一致",
    "judgment_status": "一致或不一致",
    "hallucination": true或false,
    "summary": "一句话总结"
  }}
]"""

DEFAULT_SUMMARY_REPORT_SYSTEM = """你是 AI 批改效果分析师，需要根据逐题评估结果生成整体分析报告。
请严格按照要求的 JSON 格式输出，不要输出其他内容。"""

DEFAULT_SUMMARY_REPORT_TEMPLATE = """【评估数据】
{evaluation_results_json}

【分析要求】
请从以下维度生成分析报告：

1. 整体表现：通过率、准确率、各类错误分布
2. 能力分析：识别能力评分（0-100）、判断能力评分（0-100）、幻觉率
3. 问题定位：主要问题类型、高频错误模式
4. 改进建议：针对性优化方向

【输出格式】
{{
  "overview": {{
    "total": 总题数,
    "passed": 通过数,
    "failed": 失败数,
    "pass_rate": 通过率百分比数值,
    "accuracy": 准确率百分比数值
  }},
  
  "error_distribution": {{
    "完全正确": 数量,
    "语义等价": 数量,
    "识别正确-判断错误": 数量,
    "识别错误-判断正确": 数量,
    "识别错误-判断错误": 数量,
    "AI幻觉": 数量
  }},
  
  "severity_distribution": {{
    "none": 数量,
    "low": 数量,
    "medium": 数量,
    "high": 数量,
    "critical": 数量
  }},
  
  "capability_scores": {{
    "recognition": 识别能力评分0到100,
    "judgment": 判断能力评分0到100,
    "overall": 综合评分0到100
  }},
  
  "hallucination_rate": 幻觉率百分比数值,
  
  "top_issues": [
    {{"issue": "问题描述", "count": 出现次数, "impact": "影响说明"}}
  ],
  
  "recommendations": ["改进建议1", "改进建议2"],
  
  "conclusion": "整体结论2到3句话"
}}"""


def get_prompts() -> Dict[str, str]:
    """
    获取语义评估提示词，优先从配置加载，否则使用默认值
    
    Returns:
        包含所有提示词的字典
    """
    return {
        'semantic_eval_system': load_prompt('semantic_eval_system', DEFAULT_SEMANTIC_EVAL_SYSTEM),
        'semantic_eval_template': load_prompt('semantic_eval_template', DEFAULT_SEMANTIC_EVAL_TEMPLATE),
        'batch_eval_system': DEFAULT_BATCH_EVAL_SYSTEM,  # 批量评估系统提示词使用默认值
        'batch_eval_template': load_prompt('batch_eval_template', DEFAULT_BATCH_EVAL_TEMPLATE),
        'summary_report_system': DEFAULT_SUMMARY_REPORT_SYSTEM,
        'summary_report_template': load_prompt('summary_report_template', DEFAULT_SUMMARY_REPORT_TEMPLATE)
    }


class SemanticEvalService:
    """语义级评估服务"""
    
    @staticmethod
    def rule_based_precheck(base_item: Dict, ai_item: Dict) -> Tuple[str, Optional[Dict]]:
        """
        规则预筛：快速判断明确的匹配/不匹配情况
        
        Args:
            base_item: 基准效果数据
            ai_item: AI 批改结果
            
        Returns:
            (certainty, result)
            - certainty: 'high' | 'low'
            - result: 预判结果（certainty='high' 时有值）
        """
        base_user = normalize_answer(str(base_item.get('userAnswer', '')))
        ai_user = normalize_answer(str(ai_item.get('userAnswer', '')))
        
        base_correct = SemanticEvalService._normalize_correct(base_item.get('correct', ''))
        ai_correct = SemanticEvalService._normalize_correct(ai_item.get('correct', ''))
        
        standard_answer = str(base_item.get('answer', '') or base_item.get('mainAnswer', '')).strip()
        
        # 情况1: 完全一致 → 明确通过
        if base_user == ai_user and base_correct == ai_correct:
            return ('high', {
                'verdict': 'PASS',
                'verdict_cn': '通过',
                'recognition': {
                    'status': '一致',
                    'base': base_item.get('userAnswer', ''),
                    'ai': ai_item.get('userAnswer', ''),
                    'diff_type': '无差异',
                    'detail': '识别结果完全一致'
                },
                'judgment': {
                    'status': '一致',
                    'base': base_correct,
                    'ai': ai_correct,
                    'detail': '判断结果一致'
                },
                'hallucination': {
                    'detected': False,
                    'detail': ''
                },
                'error_type': '完全正确',
                'severity': 'none',
                'severity_cn': '无',
                'summary': 'AI 批改完全正确',
                'suggestion': ''
            })
        
        # 情况2: 判断不一致 → 明确失败
        if base_correct != ai_correct:
            # 检测 AI 幻觉
            norm_ai_user = normalize_answer(ai_user)
            norm_standard = normalize_answer(standard_answer)
            is_hallucination = (base_correct == 'no' and norm_ai_user == norm_standard)
            
            if is_hallucination:
                return ('high', {
                    'verdict': 'FAIL',
                    'verdict_cn': '不通过',
                    'recognition': {
                        'status': '不一致',
                        'base': base_item.get('userAnswer', ''),
                        'ai': ai_item.get('userAnswer', ''),
                        'diff_type': '完全错误',
                        'detail': f'AI 将学生答案识别为标准答案 "{standard_answer}"'
                    },
                    'judgment': {
                        'status': '不一致',
                        'base': base_correct,
                        'ai': ai_correct,
                        'detail': '学生答错但 AI 判断为正确'
                    },
                    'hallucination': {
                        'detected': True,
                        'detail': f'AI 将学生的错误答案 "{base_item.get("userAnswer", "")}" 脑补成标准答案 "{standard_answer}"'
                    },
                    'error_type': 'AI幻觉',
                    'severity': 'critical',
                    'severity_cn': '致命',
                    'summary': 'AI 存在幻觉，将错误答案识别为标准答案',
                    'suggestion': '检查识别模型是否过度依赖标准答案进行"修正"'
                })
            
            # 普通判断错误
            if base_user == ai_user:
                return ('high', {
                    'verdict': 'FAIL',
                    'verdict_cn': '不通过',
                    'recognition': {
                        'status': '一致',
                        'base': base_item.get('userAnswer', ''),
                        'ai': ai_item.get('userAnswer', ''),
                        'diff_type': '无差异',
                        'detail': '识别结果一致'
                    },
                    'judgment': {
                        'status': '不一致',
                        'base': base_correct,
                        'ai': ai_correct,
                        'detail': f'人工判断为 {base_correct}，AI 判断为 {ai_correct}'
                    },
                    'hallucination': {
                        'detected': False,
                        'detail': ''
                    },
                    'error_type': '识别正确-判断错误',
                    'severity': 'high',
                    'severity_cn': '严重',
                    'summary': 'AI 识别正确但判断错误',
                    'suggestion': '检查判断逻辑是否正确'
                })
        
        # 情况3: 用户答案不一致但判断一致 → 需要 LLM 判断语义等价性
        return ('low', None)
    
    @staticmethod
    def _normalize_correct(value) -> str:
        """标准化 correct 字段值"""
        if isinstance(value, bool):
            return 'yes' if value else 'no'
        if isinstance(value, str):
            val_lower = value.lower().strip()
            if val_lower in ('yes', 'true', '1'):
                return 'yes'
            elif val_lower in ('no', 'false', '0'):
                return 'no'
        return str(value).lower()
    
    @staticmethod
    def evaluate_single(
        subject: str,
        question_type: str,
        index: str,
        standard_answer: str,
        base_user_answer: str,
        base_correct: str,
        ai_user_answer: str,
        ai_correct: str,
        eval_model: str = 'deepseek-v3.2'
    ) -> Dict[str, Any]:
        """
        单题语义评估
        
        Args:
            subject: 学科
            question_type: 题型
            index: 题号
            standard_answer: 标准答案
            base_user_answer: 人工识别的学生答案
            base_correct: 人工判断结果
            ai_user_answer: AI 识别的学生答案
            ai_correct: AI 判断结果
            eval_model: 评估模型
            
        Returns:
            评估结果字典
        """
        # 先进行规则预筛
        base_item = {
            'userAnswer': base_user_answer,
            'correct': base_correct,
            'answer': standard_answer
        }
        ai_item = {
            'userAnswer': ai_user_answer,
            'correct': ai_correct
        }
        
        certainty, result = SemanticEvalService.rule_based_precheck(base_item, ai_item)
        if certainty == 'high' and result:
            result['eval_method'] = 'rule'
            return result
        
        # 规则无法确定，调用 LLM
        prompts = get_prompts()
        prompt = prompts['semantic_eval_template'].format(
            subject=subject,
            question_type=question_type,
            index=index,
            standard_answer=standard_answer,
            base_user_answer=base_user_answer,
            base_correct=base_correct,
            ai_user_answer=ai_user_answer,
            ai_correct=ai_correct
        )
        
        llm_result = LLMService.call_deepseek(
            prompt,
            system_prompt=prompts['semantic_eval_system'],
            model=eval_model,
            timeout=60
        )
        
        if llm_result.get('error'):
            return {
                'error': llm_result['error'],
                'verdict': 'ERROR',
                'verdict_cn': '评估失败'
            }
        
        parsed = LLMService.parse_json_response(llm_result.get('content', ''))
        if parsed:
            parsed['eval_method'] = 'llm'
            return parsed
        
        return {
            'error': '无法解析 LLM 响应',
            'raw_response': llm_result.get('content', ''),
            'verdict': 'ERROR',
            'verdict_cn': '评估失败'
        }

    
    @staticmethod
    def evaluate_batch(
        subject: str,
        question_type: str,
        items: List[Dict[str, Any]],
        eval_model: str = 'deepseek-v3.2',
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        批量语义评估
        
        Args:
            subject: 学科
            question_type: 题型
            items: 题目列表，每个元素包含:
                - index: 题号
                - standard_answer: 标准答案
                - base_user_answer: 人工识别的学生答案
                - base_correct: 人工判断结果
                - ai_user_answer: AI 识别的学生答案
                - ai_correct: AI 判断结果
            eval_model: 评估模型
            batch_size: 每批处理的题目数量
            
        Returns:
            {
                'results': [...],  # 逐题评估结果
                'summary': {...}   # 汇总报告
            }
        """
        all_results = []
        uncertain_items = []
        
        # 阶段1: 规则预筛
        for item in items:
            base_item = {
                'userAnswer': item.get('base_user_answer', ''),
                'correct': item.get('base_correct', ''),
                'answer': item.get('standard_answer', '')
            }
            ai_item = {
                'userAnswer': item.get('ai_user_answer', ''),
                'correct': item.get('ai_correct', '')
            }
            
            certainty, result = SemanticEvalService.rule_based_precheck(base_item, ai_item)
            
            if certainty == 'high' and result:
                result['index'] = item.get('index', '')
                result['eval_method'] = 'rule'
                all_results.append(result)
            else:
                uncertain_items.append(item)
        
        # 阶段2: LLM 评估不确定的题目
        if uncertain_items:
            # 分批处理
            for i in range(0, len(uncertain_items), batch_size):
                batch = uncertain_items[i:i + batch_size]
                batch_results = SemanticEvalService._evaluate_batch_llm(
                    subject, question_type, batch, eval_model
                )
                all_results.extend(batch_results)
        
        # 按题号排序
        all_results.sort(key=lambda x: str(x.get('index', '')))
        
        # 阶段3: 生成汇总报告
        summary = SemanticEvalService._generate_summary(all_results)
        
        return {
            'results': all_results,
            'summary': summary
        }
    
    @staticmethod
    def _evaluate_batch_llm(
        subject: str,
        question_type: str,
        items: List[Dict[str, Any]],
        eval_model: str
    ) -> List[Dict[str, Any]]:
        """调用 LLM 批量评估"""
        # 构建题目 JSON
        questions_data = []
        for item in items:
            questions_data.append({
                'index': item.get('index', ''),
                'standard_answer': item.get('standard_answer', ''),
                'base_user_answer': item.get('base_user_answer', ''),
                'base_correct': item.get('base_correct', ''),
                'ai_user_answer': item.get('ai_user_answer', ''),
                'ai_correct': item.get('ai_correct', '')
            })
        
        prompts = get_prompts()
        prompt = prompts['batch_eval_template'].format(
            subject=subject,
            question_type=question_type,
            questions_json=json.dumps(questions_data, ensure_ascii=False, indent=2)
        )
        
        llm_result = LLMService.call_deepseek(
            prompt,
            system_prompt=prompts['batch_eval_system'],
            model=eval_model,
            timeout=120
        )
        
        if llm_result.get('error'):
            # LLM 调用失败，返回错误结果
            return [{
                'index': item.get('index', ''),
                'verdict': 'ERROR',
                'verdict_cn': '评估失败',
                'error': llm_result['error'],
                'eval_method': 'llm_error'
            } for item in items]
        
        content = llm_result.get('content', '')
        
        # 优先尝试提取 JSON 数组
        parsed = LLMService.extract_json_array(content)
        if parsed and isinstance(parsed, list):
            for result in parsed:
                result['eval_method'] = 'llm'
            return parsed
        
        # 如果返回的是单个对象，包装成数组
        parsed = LLMService.parse_json_response(content)
        if parsed:
            if isinstance(parsed, dict):
                parsed['eval_method'] = 'llm'
                return [parsed]
            elif isinstance(parsed, list):
                for result in parsed:
                    result['eval_method'] = 'llm'
                return parsed
        
        # 解析失败，返回错误结果
        return [{
            'index': item.get('index', ''),
            'verdict': 'ERROR',
            'verdict_cn': '评估失败',
            'error': '无法解析 LLM 响应',
            'raw_response': content[:500] if content else '',
            'eval_method': 'llm_error'
        } for item in items]
    
    @staticmethod
    def _generate_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成本地汇总报告（不调用 LLM）"""
        total = len(results)
        passed = sum(1 for r in results if r.get('verdict') == 'PASS')
        failed = total - passed
        
        # 错误分布统计
        error_distribution = {
            '完全正确': 0,
            '语义等价': 0,
            '识别正确-判断错误': 0,
            '识别错误-判断正确': 0,
            '识别错误-判断错误': 0,
            'AI幻觉': 0
        }
        
        severity_distribution = {
            'none': 0,
            'low': 0,
            'medium': 0,
            'high': 0,
            'critical': 0
        }
        
        hallucination_count = 0
        recognition_correct = 0
        judgment_correct = 0
        
        for r in results:
            error_type = r.get('error_type', '')
            if error_type in error_distribution:
                error_distribution[error_type] += 1
            
            severity = r.get('severity', 'none')
            if severity in severity_distribution:
                severity_distribution[severity] += 1
            
            # 统计幻觉
            hallucination_field = r.get('hallucination')
            is_hallucination = False
            if isinstance(hallucination_field, dict):
                is_hallucination = hallucination_field.get('detected', False)
            elif isinstance(hallucination_field, bool):
                is_hallucination = hallucination_field
            
            if is_hallucination or error_type == 'AI幻觉':
                hallucination_count += 1
            
            # 统计识别和判断正确数
            recognition_status = r.get('recognition', {}).get('status', '') or r.get('recognition_status', '')
            if recognition_status in ('一致', '语义等价'):
                recognition_correct += 1
            
            judgment_status = r.get('judgment', {}).get('status', '') or r.get('judgment_status', '')
            if judgment_status == '一致':
                judgment_correct += 1
        
        # 计算能力评分
        recognition_score = round(recognition_correct / total * 100, 1) if total > 0 else 0
        judgment_score = round(judgment_correct / total * 100, 1) if total > 0 else 0
        overall_score = round((recognition_score * 0.4 + judgment_score * 0.6), 1)
        
        # 计算幻觉率
        hallucination_rate = round(hallucination_count / total * 100, 2) if total > 0 else 0
        
        # 识别主要问题
        top_issues = []
        for error_type, count in error_distribution.items():
            if count > 0 and error_type != '完全正确' and error_type != '语义等价':
                impact = '严重' if error_type in ('AI幻觉', '识别正确-判断错误', '识别错误-判断错误') else '中等'
                top_issues.append({
                    'issue': error_type,
                    'count': count,
                    'impact': impact
                })
        top_issues.sort(key=lambda x: x['count'], reverse=True)
        
        # 生成建议
        recommendations = []
        if error_distribution.get('AI幻觉', 0) > 0:
            recommendations.append('检查识别模型是否过度依赖标准答案进行"修正"，减少幻觉现象')
        if error_distribution.get('识别正确-判断错误', 0) > 0:
            recommendations.append('优化判断逻辑，确保识别正确时判断也正确')
        if error_distribution.get('识别错误-判断错误', 0) > 0:
            recommendations.append('提升手写识别能力，特别是数学符号和特殊字符')
        if error_distribution.get('识别错误-判断正确', 0) > 0:
            recommendations.append('虽然判断正确，但识别偏差可能影响用户体验')
        
        if not recommendations:
            recommendations.append('整体表现良好，继续保持')
        
        # 生成结论
        pass_rate = round(passed / total * 100, 1) if total > 0 else 0
        if pass_rate >= 90:
            conclusion = f'AI 批改整体表现优秀，通过率 {pass_rate}%。'
        elif pass_rate >= 80:
            conclusion = f'AI 批改整体表现良好，通过率 {pass_rate}%。'
        elif pass_rate >= 60:
            conclusion = f'AI 批改表现一般，通过率 {pass_rate}%，需要关注问题并优化。'
        else:
            conclusion = f'AI 批改表现较差，通过率 {pass_rate}%，需要重点优化。'
        
        if hallucination_rate > 5:
            conclusion += f' 幻觉率 {hallucination_rate}% 偏高，需要重点关注。'
        elif hallucination_rate > 0:
            conclusion += f' 幻觉率 {hallucination_rate}% 处于可接受范围。'
        
        return {
            'overview': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': pass_rate,
                'accuracy': pass_rate
            },
            'error_distribution': error_distribution,
            'severity_distribution': severity_distribution,
            'capability_scores': {
                'recognition': recognition_score,
                'judgment': judgment_score,
                'overall': overall_score
            },
            'hallucination_rate': hallucination_rate,
            'top_issues': top_issues[:5],
            'recommendations': recommendations[:5],
            'conclusion': conclusion
        }
    
    @staticmethod
    def generate_llm_summary(results: List[Dict[str, Any]], eval_model: str = 'deepseek-v3.2') -> Dict[str, Any]:
        """使用 LLM 生成更详细的汇总报告"""
        prompts = get_prompts()
        prompt = prompts['summary_report_template'].format(
            evaluation_results_json=json.dumps(results, ensure_ascii=False, indent=2)[:8000]
        )
        
        llm_result = LLMService.call_deepseek(
            prompt,
            system_prompt=prompts['summary_report_system'],
            model=eval_model,
            timeout=90
        )
        
        if llm_result.get('error'):
            # LLM 调用失败，使用本地汇总
            return SemanticEvalService._generate_summary(results)
        
        parsed = LLMService.parse_json_response(llm_result.get('content', ''))
        if parsed:
            parsed['generated_by'] = 'llm'
            return parsed
        
        # 解析失败，使用本地汇总
        return SemanticEvalService._generate_summary(results)
