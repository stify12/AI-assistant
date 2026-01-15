"""
AI 评估路由
提供语义级评估 API
"""
from flask import Blueprint, request, jsonify
from services.semantic_eval_service import SemanticEvalService

ai_eval_bp = Blueprint('ai_eval', __name__)


@ai_eval_bp.route('/api/ai-eval/semantic', methods=['POST'])
def semantic_eval_single():
    """
    单题语义评估
    
    Request:
    {
        "subject": "数学",
        "question_type": "填空题",
        "index": "1",
        "standard_answer": "3/4",
        "base_user_answer": "0.75",
        "base_correct": "yes",
        "ai_user_answer": "0.75",
        "ai_correct": "yes",
        "eval_model": "deepseek-v3.2"  // 可选
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据为空'}), 400
        
        # 必填字段验证
        required_fields = ['subject', 'question_type', 'index', 'standard_answer',
                          'base_user_answer', 'base_correct', 'ai_user_answer', 'ai_correct']
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return jsonify({'error': f'缺少必填字段: {", ".join(missing)}'}), 400
        
        result = SemanticEvalService.evaluate_single(
            subject=data['subject'],
            question_type=data['question_type'],
            index=str(data['index']),
            standard_answer=str(data['standard_answer']),
            base_user_answer=str(data['base_user_answer']),
            base_correct=str(data['base_correct']),
            ai_user_answer=str(data['ai_user_answer']),
            ai_correct=str(data['ai_correct']),
            eval_model=data.get('eval_model', 'deepseek-v3.2')
        )
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_eval_bp.route('/api/ai-eval/semantic-batch', methods=['POST'])
def semantic_eval_batch():
    """
    批量语义评估
    
    Request:
    {
        "subject": "数学",
        "question_type": "填空题",
        "items": [
            {
                "index": "1",
                "standard_answer": "...",
                "base_user_answer": "...",
                "base_correct": "yes",
                "ai_user_answer": "...",
                "ai_correct": "yes"
            }
        ],
        "eval_model": "deepseek-v3.2",  // 可选
        "batch_size": 10  // 可选
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据为空'}), 400
        
        # 必填字段验证
        if not data.get('subject'):
            return jsonify({'error': '缺少 subject 字段'}), 400
        if not data.get('question_type'):
            return jsonify({'error': '缺少 question_type 字段'}), 400
        if not data.get('items') or not isinstance(data['items'], list):
            return jsonify({'error': 'items 字段必须是非空数组'}), 400
        
        result = SemanticEvalService.evaluate_batch(
            subject=data['subject'],
            question_type=data['question_type'],
            items=data['items'],
            eval_model=data.get('eval_model', 'deepseek-v3.2'),
            batch_size=data.get('batch_size', 10)
        )
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_eval_bp.route('/api/ai-eval/report', methods=['POST'])
def generate_report():
    """
    生成评估报告
    
    Request:
    {
        "evaluation_results": [...],  // 评估结果数组
        "use_llm": false,  // 是否使用 LLM 生成报告，可选
        "eval_model": "deepseek-v3.2"  // 可选
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据为空'}), 400
        
        results = data.get('evaluation_results', [])
        if not isinstance(results, list):
            return jsonify({'error': 'evaluation_results 必须是数组'}), 400
        
        use_llm = data.get('use_llm', False)
        eval_model = data.get('eval_model', 'deepseek-v3.2')
        
        if use_llm:
            summary = SemanticEvalService.generate_llm_summary(results, eval_model)
        else:
            summary = SemanticEvalService._generate_summary(results)
        
        return jsonify(summary)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_eval_bp.route('/api/ai-eval/precheck', methods=['POST'])
def rule_precheck():
    """
    规则预筛（快速判断，不调用 LLM）
    
    Request:
    {
        "base_item": {
            "userAnswer": "3/4",
            "correct": "yes",
            "answer": "3/4"
        },
        "ai_item": {
            "userAnswer": "0.75",
            "correct": "yes"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据为空'}), 400
        
        base_item = data.get('base_item', {})
        ai_item = data.get('ai_item', {})
        
        if not base_item or not ai_item:
            return jsonify({'error': '缺少 base_item 或 ai_item'}), 400
        
        certainty, result = SemanticEvalService.rule_based_precheck(base_item, ai_item)
        
        return jsonify({
            'certainty': certainty,
            'result': result
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
