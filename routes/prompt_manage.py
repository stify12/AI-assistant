"""
提示词管理路由模块
提供提示词的增删改查和优化功能
"""
import requests
from flask import Blueprint, request, jsonify

from services.config_service import ConfigService
from utils.text_utils import remove_think_tags, extract_json_from_text

prompt_manage_bp = Blueprint('prompt_manage', __name__)


@prompt_manage_bp.route('/api/prompts', methods=['GET', 'POST', 'DELETE'])
def prompts():
    if request.method == 'GET':
        prompts_list = ConfigService.load_prompts()
        return jsonify({'prompts': prompts_list})
    elif request.method == 'POST':
        data = request.json
        # 支持批量更新
        if 'prompts' in data:
            ConfigService.save_prompts(data['prompts'])
            return jsonify({'success': True})
        else:
            # 兼容旧的单个添加方式
            prompts_list = ConfigService.load_prompts()
            prompts_list.append(data)
            ConfigService.save_prompts(prompts_list)
            return jsonify({'success': True})
    else:
        data = request.json
        prompts_list = ConfigService.load_prompts()
        prompts_list = [p for p in prompts_list if p['name'] != data['name']]
        ConfigService.save_prompts(prompts_list)
        return jsonify({'success': True})


@prompt_manage_bp.route('/api/optimize-prompt', methods=['POST'])
def optimize_prompt():
    """使用Qwen3-Max优化提示词"""
    config = ConfigService.load_config()
    
    if not config.get('qwen_api_key'):
        return jsonify({'error': '请先配置Qwen API Key'}), 400
    
    data = request.json
    original_prompt = data.get('prompt', '')
    
    if not original_prompt:
        return jsonify({'error': '提示词内容不能为空'}), 400
    
    # 构建优化请求
    optimize_system = """你是一位专业的提示词工程专家，擅长分析和优化AI提示词。
请分析用户提供的提示词，找出其中的弱点和可改进之处，然后给出优化后的版本。

分析维度：
1. 角色定义是否清晰
2. 任务描述是否明确
3. 输出格式是否规范
4. 约束条件是否完整
5. 示例是否充分
6. 边界情况是否考虑

请以JSON格式输出，包含以下字段：
{
  "analysis": "问题分析（简要说明原提示词的主要弱点）",
  "suggestions": "优化建议（具体的改进方向）",
  "optimized_prompt": "优化后的完整提示词"
}

注意：
- 保持原提示词的核心意图不变
- 优化后的提示词应该更加清晰、完整、有效
- 直接输出JSON，不要输出思考过程"""

    optimize_user = f"""请分析并优化以下提示词：

---原始提示词开始---
{original_prompt}
---原始提示词结束---

请输出JSON格式的分析和优化结果。"""

    try:
        response = requests.post(
            'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
            json={
                'model': 'qwen3-max',
                'messages': [
                    {'role': 'system', 'content': optimize_system},
                    {'role': 'user', 'content': optimize_user}
                ]
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {config['qwen_api_key']}"
            },
            timeout=60
        )
        
        result = response.json()
        
        if 'error' in result:
            return jsonify({'error': result['error'].get('message', '请求失败')}), 500
        
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            content = remove_think_tags(content)
            
            # 尝试解析JSON
            parsed = extract_json_from_text(content)
            if parsed:
                return jsonify({
                    'analysis': parsed.get('analysis', ''),
                    'suggestions': parsed.get('suggestions', ''),
                    'optimized_prompt': parsed.get('optimized_prompt', '')
                })
            
            # 如果无法解析JSON，返回原始内容
            return jsonify({
                'analysis': content,
                'suggestions': '',
                'optimized_prompt': ''
            })
        
        return jsonify({'error': '未获取到响应'}), 500
        
    except requests.Timeout:
        return jsonify({'error': '请求超时，请稍后重试'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
