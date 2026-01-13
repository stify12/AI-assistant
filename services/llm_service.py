"""
LLM 服务模块
提供 Qwen、DeepSeek 和视觉模型的调用接口
"""
import re
import json
import requests
from .config_service import ConfigService


class LLMService:
    """LLM 服务类"""
    
    QWEN_API_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    DEEPSEEK_API_URL = 'https://api.deepseek.com/chat/completions'
    
    @staticmethod
    def call_qwen(prompt, system_prompt='你是一个专业的AI助手。', model='qwen3-max', timeout=60):
        """调用 Qwen 模型"""
        config = ConfigService.load_config()
        api_key = config.get('qwen_api_key')
        
        if not api_key:
            return {'error': '请先配置 Qwen API Key'}
        
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ]
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        try:
            response = requests.post(
                LLMService.QWEN_API_URL,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            result = response.json()
            
            if 'choices' in result:
                content = result['choices'][0]['message']['content']
                # 移除思考过程标签
                content = LLMService.remove_think_tags(content)
                return {'success': True, 'content': content, 'raw': result}
            else:
                error_msg = result.get('error', {}).get('message', '请求失败')
                return {'error': error_msg}
        except requests.Timeout:
            return {'error': '请求超时'}
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def call_deepseek(prompt, system_prompt='你是一个专业的AI助手。', model='deepseek-chat', timeout=60):
        """调用 DeepSeek 模型"""
        config = ConfigService.load_config()
        api_key = config.get('deepseek_api_key')
        
        if not api_key:
            return {'error': '请先配置 DeepSeek API Key'}
        
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ]
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        try:
            response = requests.post(
                LLMService.DEEPSEEK_API_URL,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            result = response.json()
            
            if 'choices' in result:
                content = result['choices'][0]['message']['content']
                return {'success': True, 'content': content, 'raw': result}
            else:
                error_msg = result.get('error', {}).get('message', '请求失败')
                return {'error': error_msg}
        except requests.Timeout:
            return {'error': '请求超时'}
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def call_vision_model(image, prompt, model=None, timeout=120):
        """调用视觉模型"""
        config = ConfigService.load_config()
        api_url = config.get('api_url', 'https://ark.cn-beijing.volces.com/api/v3/chat/completions')
        api_key = config.get('api_key')
        
        if not api_key:
            return {'error': '请先配置 API Key'}
        
        if model is None:
            model = config.get('model', 'doubao-1-5-vision-pro-32k-250115')
        
        messages = [{
            'role': 'user',
            'content': [
                {'type': 'image_url', 'image_url': {'url': image}},
                {'type': 'text', 'text': prompt}
            ]
        }]
        
        payload = {
            'model': model,
            'messages': messages
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        try:
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            result = response.json()
            
            if 'choices' in result:
                content = result['choices'][0]['message']['content']
                return {'success': True, 'content': content, 'raw': result}
            else:
                error_msg = result.get('error', {}).get('message', '请求失败')
                return {'error': error_msg}
        except requests.Timeout:
            return {'error': '请求超时'}
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def parse_json_response(content):
        """从响应内容中解析 JSON"""
        if not content:
            return None
        
        # 移除思考过程标签
        content = LLMService.remove_think_tags(content)
        
        try:
            # 尝试直接解析
            return json.loads(content)
        except:
            pass
        
        # 尝试提取 JSON 对象
        try:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # 尝试提取 JSON 数组
        try:
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return None
    
    @staticmethod
    def remove_think_tags(content):
        """移除思考过程标签"""
        if not content:
            return content
        return re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
    
    @staticmethod
    def extract_json_array(content):
        """从内容中提取 JSON 数组"""
        if not content:
            return None
        
        content = LLMService.remove_think_tags(content)
        
        try:
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return None
