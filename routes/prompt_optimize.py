"""
Prompt 优化评测路由模块
提供 Prompt 任务管理、样本评分、版本管理功能
"""
import os
import uuid
import json
import requests
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, Response

from services.config_service import ConfigService
from services.storage_service import StorageService
from services.llm_service import LLMService
from utils.text_utils import remove_think_tags, extract_json_from_text, extract_score_from_text, extract_reason_from_text

prompt_optimize_bp = Blueprint('prompt_optimize', __name__)


@prompt_optimize_bp.route('/prompt-optimize')
def prompt_optimize_page():
    """Prompt 优化页面"""
    return render_template('prompt-optimize.html')


@prompt_optimize_bp.route('/api/prompt-tasks', methods=['GET'])
def get_prompt_tasks():
    """获取任务列表"""
    tasks = []
    for filename in StorageService.list_prompt_tasks():
        task_id = filename[:-5]
        task = StorageService.load_prompt_task(task_id)
        if task:
            tasks.append({
                'task_id': task_id,
                'name': task.get('name', '未命名'),
                'sample_count': len(task.get('samples', [])),
                'avg_score': task.get('avg_score'),
                'created_at': task.get('created_at'),
                'updated_at': task.get('updated_at')
            })
    tasks.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    return jsonify(tasks)


@prompt_optimize_bp.route('/api/prompt-task', methods=['POST'])
def create_prompt_task():
    """创建新任务"""
    data = request.json
    task_id = str(uuid.uuid4())[:8]
    
    task_data = {
        'task_id': task_id,
        'name': data.get('name', '未命名任务'),
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'current_prompt': data.get('prompt', ''),
        'model': data.get('model', 'doubao-1-5-vision-pro-32k-250115'),
        'scoring_rules': '',
        'variables': [],
        'samples': [],
        'versions': [],
        'current_version': 'current'
    }
    
    StorageService.save_prompt_task(task_id, task_data)
    return jsonify({'task_id': task_id, 'created_at': task_data['created_at']})


@prompt_optimize_bp.route('/api/prompt-task/<task_id>', methods=['GET', 'PUT', 'DELETE'])
def prompt_task_api(task_id):
    """任务详情 API"""
    if request.method == 'GET':
        task = StorageService.load_prompt_task(task_id)
        if not task:
            return jsonify({'error': '任务不存在'}), 404
        return jsonify(task)
    
    elif request.method == 'PUT':
        task = StorageService.load_prompt_task(task_id)
        if not task:
            return jsonify({'error': '任务不存在'}), 404
        
        data = request.json
        if 'prompt' in data:
            task['current_prompt'] = data['prompt']
        if 'scoring_rules' in data:
            task['scoring_rules'] = data['scoring_rules']
        if 'model' in data:
            task['model'] = data['model']
        
        StorageService.save_prompt_task(task_id, task)
        return jsonify({'success': True})
    
    else:  # DELETE
        StorageService.delete_prompt_task(task_id)
        return jsonify({'success': True})


@prompt_optimize_bp.route('/api/prompt-sample', methods=['POST'])
def add_prompt_sample():
    """添加样本"""
    data = request.json
    task_id = data.get('task_id')
    
    if not task_id:
        return jsonify({'error': '缺少 task_id'}), 400
    
    task = StorageService.load_prompt_task(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    sample_id = str(uuid.uuid4())[:8]
    sample = {
        'sample_id': sample_id,
        'created_at': datetime.now().isoformat(),
        'variables': data.get('variables', {}),
        'model_response': data.get('model_response', ''),
        'ideal_answer': data.get('ideal_answer', ''),
        'score': data.get('score'),
        'score_source': data.get('score_source', 'manual'),
        'score_reason': data.get('score_reason', '')
    }
    
    task['samples'].append(sample)
    StorageService.save_prompt_task(task_id, task)
    
    return jsonify({'sample_id': sample_id})


@prompt_optimize_bp.route('/api/prompt-version', methods=['POST'])
def save_prompt_version():
    """保存 Prompt 版本"""
    data = request.json
    task_id = data.get('task_id')
    
    task = StorageService.load_prompt_task(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    samples = task.get('samples', [])
    scored = [s for s in samples if s.get('score')]
    avg_score = sum(s['score'] for s in scored) / len(scored) if scored else 0
    
    version_count = len(task.get('versions', []))
    version_id = f'v{version_count + 1}'
    
    version = {
        'version_id': version_id,
        'created_at': datetime.now().isoformat(),
        'prompt': data.get('prompt', task.get('current_prompt', '')),
        'scoring_rules': data.get('scoring_rules', task.get('scoring_rules', '')),
        'statistics': {
            'sample_count': len(samples),
            'scored_count': len(scored),
            'avg_score': round(avg_score, 2)
        }
    }
    
    if 'versions' not in task:
        task['versions'] = []
    task['versions'].append(version)
    task['current_version'] = version_id
    task['current_prompt'] = version['prompt']
    task['scoring_rules'] = version['scoring_rules']
    
    StorageService.save_prompt_task(task_id, task)
    
    return jsonify({'version_id': version_id, 'avg_score': round(avg_score, 2)})


@prompt_optimize_bp.route('/api/prompt-eval/generate', methods=['POST'])
def generate_prompt_response():
    """生成模型回答"""
    config = ConfigService.load_config()
    data = request.json
    
    prompt = data.get('prompt', '')
    model = data.get('model', 'doubao-1-5-vision-pro-32k-250115')
    variables = data.get('variables', {})
    
    # 填充变量
    filled_prompt = prompt
    for var_name, var_data in variables.items():
        if var_data.get('type') == 'text':
            filled_prompt = filled_prompt.replace('{{' + var_name + '}}', var_data.get('value', ''))
    
    messages = [{'role': 'user', 'content': []}]
    
    # 添加图片
    for var_name, var_data in variables.items():
        if var_data.get('type') in ['image', 'image_url']:
            img_value = var_data.get('value', '')
            if img_value:
                messages[0]['content'].append({
                    'type': 'image_url',
                    'image_url': {'url': img_value}
                })
    
    messages[0]['content'].append({'type': 'text', 'text': filled_prompt})
    
    try:
        response = requests.post(
            config.get('api_url', 'https://ark.cn-beijing.volces.com/api/v3/chat/completions'),
            json={'model': model, 'messages': messages},
            headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {config.get('api_key', '')}"},
            timeout=120
        )
        result = response.json()
        
        if 'choices' in result:
            content = result['choices'][0]['message']['content']
            return jsonify({'success': True, 'response': content})
        else:
            return jsonify({'error': result.get('error', {}).get('message', '生成失败')}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@prompt_optimize_bp.route('/api/prompt-eval/score', methods=['POST'])
def score_prompt_sample():
    """AI 评分"""
    config = ConfigService.load_config()
    
    if not config.get('qwen_api_key'):
        return jsonify({'error': '请先配置 Qwen API Key'}), 400
    
    data = request.json
    model_response = data.get('model_response', '')
    ideal_answer = data.get('ideal_answer', '')
    scoring_rules = data.get('scoring_rules', '')
    
    scoring_prompt = f"""请根据以下评分标准对模型回答进行评分（1-10分）：

评分标准：
{scoring_rules if scoring_rules else '准确性、完整性、清晰度'}

理想回答：
{ideal_answer}

模型回答：
{model_response}

请输出：
评分: [1-10的整数]
理由: [评分理由]"""
    
    result = LLMService.call_qwen(scoring_prompt, '你是专业的评分专家。请严格按照评分标准评分。')
    
    if result.get('error'):
        return jsonify({'error': result['error']}), 500
    
    content = result.get('content', '')
    score = extract_score_from_text(content)
    reason = extract_reason_from_text(content)
    
    if score:
        return jsonify({'score': score, 'reason': reason})
    
    return jsonify({'error': '无法解析评分', 'raw': content}), 500


@prompt_optimize_bp.route('/api/prompt-generate', methods=['POST'])
def generate_prompt_from_task():
    """根据任务描述生成 Prompt"""
    config = ConfigService.load_config()
    
    if not config.get('qwen_api_key'):
        return jsonify({'error': '请先配置Qwen API Key'}), 400
    
    data = request.json
    task_description = data.get('task_description', '')
    
    if not task_description:
        return jsonify({'error': '任务描述不能为空'}), 400
    
    system_prompt = """你是一位专业的提示词工程专家，擅长根据任务描述生成高质量的AI提示词。

请根据用户的任务描述，生成一个结构清晰、指令明确的Prompt。

生成规则：
1. 使用 {{变量名}} 格式定义变量占位符
2. 明确指定输出格式
3. 包含必要的约束条件
4. 保持简洁但完整

请直接输出生成的Prompt，不要输出其他内容。"""

    result = LLMService.call_qwen(f"请根据以下任务描述生成Prompt：\n\n{task_description}", system_prompt)
    
    if result.get('error'):
        return jsonify({'error': result['error']}), 500
    
    return jsonify({'prompt': result.get('content', '')})


@prompt_optimize_bp.route('/api/prompt-optimize/analyze', methods=['POST'])
def analyze_for_optimization():
    """分析并优化 Prompt"""
    config = ConfigService.load_config()
    data = request.json
    
    prompt = data.get('prompt', '')
    samples = data.get('samples', [])
    
    if not config.get('qwen_api_key'):
        return jsonify({'error': '请先配置 Qwen API Key'}), 400
    
    scored = [s for s in samples if s.get('score')]
    before_score = sum(s['score'] for s in scored) / len(scored) if scored else 0
    low_score_samples = [s for s in scored if s.get('score', 10) <= 5]
    
    analysis_prompt = f"""请分析以下 Prompt 并提供优化建议：

当前 Prompt:
{prompt}

低分样本分析（评分 ≤ 5）：
{json.dumps([{'response': s.get('model_response', '')[:200], 'score': s.get('score'), 'reason': s.get('score_reason', '')} for s in low_score_samples[:5]], ensure_ascii=False, indent=2)}

请输出 JSON 格式：
{{
  "analysis": "问题分析",
  "optimized_prompt": "优化后的完整 Prompt",
  "expected_improvement": 1.5,
  "suggestions": ["建议1", "建议2"]
}}"""
    
    result = LLMService.call_qwen(analysis_prompt, '你是 Prompt 优化专家。请直接输出 JSON。', timeout=90)
    
    if result.get('error'):
        return jsonify({'error': result['error']}), 500
    
    parsed = LLMService.parse_json_response(result.get('content', ''))
    if parsed:
        return jsonify({
            'before_score': round(before_score, 2),
            'optimized_prompt': parsed.get('optimized_prompt', ''),
            'expected_improvement': parsed.get('expected_improvement', 0),
            'analysis': parsed.get('analysis', ''),
            'suggestions': parsed.get('suggestions', [])
        })
    
    return jsonify({'error': '优化失败'}), 500
