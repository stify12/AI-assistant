"""
AI 评估路由模块
提供 Qwen、DeepSeek 评估和联合评估功能
"""
import json
import uuid
import requests
from datetime import datetime
from flask import Blueprint, request, jsonify

from services.config_service import ConfigService
from services.llm_service import LLMService
from utils.text_utils import remove_think_tags, extract_json_from_text

ai_eval_bp = Blueprint('ai_eval', __name__)


# ========== Qwen 评估 API ==========

@ai_eval_bp.route('/api/qwen/advice', methods=['POST'])
def qwen_advice():
    """Qwen3-Max提示词优化建议"""
    config = ConfigService.load_config()
    if not config.get('qwen_api_key'):
        return jsonify({'error': '请先配置Qwen API Key以使用优化建议功能'}), 400
    
    data = request.json
    test_results = data.get('test_results', {})
    current_prompt = data.get('current_prompt', '')
    
    prompt = f"""作为AI批改效果分析专家，请基于以下测试结果给出提示词优化建议：

当前提示词：
{current_prompt}

测试结果：
{json.dumps(test_results, ensure_ascii=False, indent=2)[:3000]}

请以JSON格式输出优化建议：
{{
  "current_issues": ["问题1", "问题2"],
  "optimization_suggestions": ["建议1", "建议2"],
  "optimized_prompt": "优化后的提示词",
  "expected_improvement": "预期改进效果"
}}

请直接输出JSON，不要输出思考过程。"""
    
    result = LLMService.call_qwen(prompt, '你是一个专业的提示词工程专家。请直接输出JSON格式结果。')
    
    if result.get('error'):
        return jsonify({'error': result['error']}), 400
    
    parsed = LLMService.parse_json_response(result.get('content', ''))
    if parsed:
        parsed['source'] = 'qwen3-max'
        parsed['advice_type'] = 'prompt_optimization'
        parsed['generated_at'] = datetime.now().isoformat()
        return jsonify(parsed)
    
    return jsonify({'result': result.get('content', ''), 'source': 'qwen3-max'})


@ai_eval_bp.route('/api/qwen/compare-report', methods=['POST'])
def qwen_compare_report():
    """Qwen3-Max多模型对比分析报告"""
    config = ConfigService.load_config()
    if not config.get('qwen_api_key'):
        return jsonify({'error': '请先配置Qwen API Key以使用对比分析功能'}), 400
    
    data = request.json
    model_outputs = data.get('model_outputs', {})
    base_answer = data.get('base_answer', '')
    subject = data.get('subject', '通用')
    question_type = data.get('question_type', '客观题')
    
    if not model_outputs:
        return jsonify({'error': '请提供模型输出数据'}), 400
    
    prompt = f"""作为AI批改效果分析专家，请对以下多模型对比测试结果进行深度分析：

【测试背景】
- 学科：{subject}
- 题型：{question_type}
- 基准答案：{base_answer if base_answer else '未提供'}

【各模型测试数据】
{json.dumps(model_outputs, ensure_ascii=False, indent=2)[:4000]}

请以JSON格式输出对比分析结果。"""
    
    result = LLMService.call_qwen(prompt, '你是一个专业的AI模型评测分析师。请直接输出JSON格式结果。', timeout=120)
    
    if result.get('error'):
        return jsonify({'error': result['error']}), 400
    
    parsed = LLMService.parse_json_response(result.get('content', ''))
    if parsed:
        parsed['source'] = 'qwen3-max'
        parsed['report_type'] = 'compare_report'
        parsed['generated_at'] = datetime.now().isoformat()
        return jsonify(parsed)
    
    return jsonify({'result': result.get('content', ''), 'source': 'qwen3-max'})


# ========== DeepSeek 评估 API ==========

@ai_eval_bp.route('/api/deepseek/semantic-eval', methods=['POST'])
def deepseek_semantic_eval():
    """DeepSeek语义评估 - 逐题正确性判断"""
    config = ConfigService.load_config()
    if not config.get('deepseek_api_key'):
        return jsonify({'error': '请先配置DeepSeek API Key以使用语义评估功能'}), 400
    
    data = request.json
    question = data.get('question', '')
    standard_answer = data.get('standard_answer', '')
    ai_answer = data.get('ai_answer', '')
    subject = data.get('subject', '通用')
    question_type = data.get('question_type', '客观题')
    
    prompt = f"""作为专业的答案评估专家，请对以下AI批改结果进行语义级评估：

学科：{subject}
题型：{question_type}
题目：{question}
标准答案：{standard_answer}
AI答案：{ai_answer}

请以JSON格式输出评估结果。"""
    
    result = LLMService.call_deepseek(prompt, '你是一个专业的答案评估专家。请直接输出JSON格式结果。')
    
    if result.get('error'):
        return jsonify({'error': result['error']}), 400
    
    parsed = LLMService.parse_json_response(result.get('content', ''))
    if parsed:
        parsed['source'] = 'deepseek'
        parsed['evaluation_type'] = 'semantic_eval'
        return jsonify(parsed)
    
    return jsonify({'result': result.get('content', ''), 'source': 'deepseek'})


@ai_eval_bp.route('/api/deepseek/judge', methods=['POST'])
def deepseek_judge():
    """DeepSeek模型仲裁 - 多模型输出质量评分"""
    config = ConfigService.load_config()
    if not config.get('deepseek_api_key'):
        return jsonify({'error': '请先配置DeepSeek API Key以使用模型仲裁功能'}), 400
    
    data = request.json
    question = data.get('question', '')
    standard_answer = data.get('standard_answer', '')
    model_outputs = data.get('model_outputs', {})
    
    outputs_text = '\n'.join([f"【{name}】\n{output}" for name, output in model_outputs.items()])
    
    prompt = f"""作为AI模型输出质量仲裁专家，请对以下多个模型的输出进行质量评估和排名：

题目：{question}
标准答案：{standard_answer}

各模型输出：
{outputs_text}

请以JSON格式输出评估结果。"""
    
    result = LLMService.call_deepseek(prompt, '你是一个专业的AI模型输出质量仲裁专家。请直接输出JSON格式结果。')
    
    if result.get('error'):
        return jsonify({'error': result['error']}), 400
    
    parsed = LLMService.parse_json_response(result.get('content', ''))
    if parsed:
        parsed['source'] = 'deepseek'
        parsed['evaluation_type'] = 'model_judge'
        return jsonify(parsed)
    
    return jsonify({'result': result.get('content', ''), 'source': 'deepseek'})


@ai_eval_bp.route('/api/deepseek/diagnose', methods=['POST'])
def deepseek_diagnose():
    """DeepSeek错误归因分析 - 错误原因定位"""
    config = ConfigService.load_config()
    if not config.get('deepseek_api_key'):
        return jsonify({'error': '请先配置DeepSeek API Key以使用错误归因功能'}), 400
    
    data = request.json
    question = data.get('question', '')
    standard_answer = data.get('standard_answer', '')
    ai_answer = data.get('ai_answer', '')
    error_description = data.get('error_description', '')
    
    prompt = f"""作为AI批改错误诊断专家，请分析以下批改错误的根本原因：

题目：{question}
标准答案：{standard_answer}
AI答案：{ai_answer}
错误描述：{error_description}

请以JSON格式输出诊断结果。"""
    
    result = LLMService.call_deepseek(prompt, '你是一个专业的AI批改错误诊断专家。请直接输出JSON格式结果。')
    
    if result.get('error'):
        return jsonify({'error': result['error']}), 400
    
    parsed = LLMService.parse_json_response(result.get('content', ''))
    if parsed:
        parsed['source'] = 'deepseek'
        parsed['evaluation_type'] = 'error_diagnosis'
        return jsonify(parsed)
    
    return jsonify({'result': result.get('content', ''), 'source': 'deepseek'})


# ========== 联合评估 API ==========

@ai_eval_bp.route('/api/eval/config-status', methods=['GET'])
def eval_config_status():
    """获取评估模型配置状态"""
    config = ConfigService.load_config()
    return jsonify({
        'qwen_configured': bool(config.get('qwen_api_key')),
        'deepseek_configured': bool(config.get('deepseek_api_key')),
        'joint_available': bool(config.get('qwen_api_key')) and bool(config.get('deepseek_api_key'))
    })


@ai_eval_bp.route('/api/eval/joint-report', methods=['POST'])
def joint_evaluation_report():
    """联合评估报告 - 整合Qwen3-Max和DeepSeek结果"""
    config = ConfigService.load_config()
    
    data = request.json
    test_results = data.get('test_results', {})
    
    has_qwen = bool(config.get('qwen_api_key'))
    has_deepseek = bool(config.get('deepseek_api_key'))
    
    if not has_qwen and not has_deepseek:
        return jsonify({'error': '请至少配置一个评估模型（Qwen或DeepSeek）的API Key'}), 400
    
    report = {
        'report_type': 'joint_evaluation',
        'test_id': str(uuid.uuid4())[:8],
        'generated_at': datetime.now().isoformat(),
        'macro_analysis': None,
        'micro_evaluation': None,
        'discrepancies': [],
        'final_conclusion': {
            'evaluation_mode': 'joint' if (has_qwen and has_deepseek) else ('qwen_only' if has_qwen else 'deepseek_only'),
            'macro_available': has_qwen,
            'micro_available': has_deepseek
        }
    }
    
    return jsonify(report)


@ai_eval_bp.route('/api/ai-eval/unified', methods=['POST'])
def unified_ai_eval():
    """统一AI评估入口"""
    config = ConfigService.load_config()
    data = request.json
    
    test_type = data.get('test_type', 'single')
    eval_model = data.get('eval_model', 'joint')
    test_results = data.get('test_results', {})
    
    qwen_available = bool(config.get('qwen_api_key'))
    deepseek_available = bool(config.get('deepseek_api_key'))
    
    if eval_model == 'qwen3-max' and not qwen_available:
        return jsonify({'error': '请先配置Qwen API Key'}), 400
    if eval_model == 'deepseek' and not deepseek_available:
        return jsonify({'error': '请先配置DeepSeek API Key'}), 400
    
    result = {
        'test_type': test_type,
        'eval_model': eval_model,
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify(result)


@ai_eval_bp.route('/api/eval/quantify', methods=['POST'])
def quantify_eval():
    """量化数据输出"""
    data = request.json
    test_results = data.get('test_results', {})
    thresholds = data.get('thresholds', {
        'accuracy': 80,
        'consistency': 80,
        'avg_time': 5,
        'token_cost': 2000
    })
    
    metrics = {}
    
    accuracy = test_results.get('avgAccuracy') or test_results.get('summary', {}).get('overall_accuracy')
    if accuracy is not None:
        metrics['accuracy'] = {
            'value': accuracy,
            'threshold': thresholds.get('accuracy', 80),
            'pass': accuracy >= thresholds.get('accuracy', 80)
        }
    
    consistency = test_results.get('consistency')
    if consistency is not None:
        metrics['consistency'] = {
            'value': consistency,
            'threshold': thresholds.get('consistency', 80),
            'pass': consistency >= thresholds.get('consistency', 80)
        }
    
    pass_count = sum(1 for m in metrics.values() if m.get('pass'))
    total_count = len(metrics)
    
    return jsonify({
        'dimensions': metrics,
        'threshold_comparison': {
            'pass_count': pass_count,
            'total_count': total_count,
            'overall_pass': pass_count == total_count if total_count > 0 else False
        },
        'generated_at': datetime.now().isoformat()
    })
