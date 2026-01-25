"""
LLM 服务模块
提供 Qwen、DeepSeek 和视觉模型的调用接口
支持异步并行调用和重试机制
"""
import re
import json
import time
import uuid
import asyncio
import aiohttp
import requests
from datetime import datetime
from typing import List, Dict, Optional, Any
from .config_service import ConfigService


class LLMService:
    """LLM 服务类"""
    
    QWEN_API_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    DEEPSEEK_API_URL = 'https://api.deepseek.com/chat/completions'
    ZHIPU_API_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'
    
    @staticmethod
    def call_qwen(prompt, system_prompt='你是一个专业的AI助手。', model='qwen3-max', timeout=60, user_id=None):
        """调用 Qwen 模型"""
        config = ConfigService.load_config(user_id=user_id)
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
    def call_deepseek(prompt, system_prompt='你是一个专业的AI助手。', model='deepseek-chat', timeout=60, user_id=None):
        """调用 DeepSeek 模型"""
        config = ConfigService.load_config(user_id=user_id)
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
    def call_zhipu(prompt, system_prompt='你是一个专业的AI助手。', model='glm-4', timeout=60, user_id=None):
        """调用智谱 GLM 模型"""
        config = ConfigService.load_config(user_id=user_id)
        api_key = config.get('zhipu_api_key')
        
        if not api_key:
            return {'error': '请先配置智谱 API Key'}
        
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
                LLMService.ZHIPU_API_URL,
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
    def call_vision_model(image, prompt, model=None, timeout=120, user_id=None):
        """调用视觉模型"""
        config = ConfigService.load_config(user_id=user_id)
        api_url = config.get('api_url', 'https://ark.cn-beijing.volces.com/api/v3/chat/completions')
        api_key = config.get('api_key')
        
        print(f"[Vision] user_id={user_id}, model={model}, api_key={'已配置' if api_key else '未配置'}")
        
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
        
        # 尝试直接解析整个内容
        try:
            parsed = json.loads(content.strip())
            if isinstance(parsed, list):
                return parsed
        except:
            pass
        
        # 移除 markdown 代码块标记
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        content = content.strip()
        
        # 再次尝试直接解析
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
        except:
            pass
        
        # 使用正则提取 JSON 数组
        try:
            # 贪婪匹配最外层的 JSON 数组
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
        except Exception as e:
            print(f"[ExtractJSON] Failed to parse: {str(e)}")
            # 尝试修复 LaTeX 公式中的无效转义序列
            try:
                json_match = re.search(r'\[[\s\S]*\]', content)
                if json_match:
                    json_str = json_match.group()
                    # 修复无效的反斜杠转义（LaTeX 公式常见问题）
                    fixed_str = LLMService._fix_invalid_json_escapes(json_str)
                    return json.loads(fixed_str)
            except Exception as e2:
                print(f"[ExtractJSON] Failed to parse after fix: {str(e2)}")
                pass
        
        return None
    
    @staticmethod
    def _fix_invalid_json_escapes(s):
        """修复 JSON 字符串中的无效转义序列（如 LaTeX 公式中的 \\stackrel）"""
        result = []
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                next_char = s[i + 1]
                # JSON 有效转义字符: \" \\ \/ \b \f \n \r \t \uXXXX
                if next_char in '"\\\/bfnrtu':
                    result.append(s[i])
                    result.append(next_char)
                    i += 2
                else:
                    # 无效转义，添加额外的反斜杠使其成为字面量
                    result.append('\\\\')
                    result.append(next_char)
                    i += 2
            else:
                result.append(s[i])
                i += 1
        return ''.join(result)


    # ============================================
    # 异步调用方法
    # ============================================
    
    @staticmethod
    async def call_deepseek_async(
        prompt: str,
        system_prompt: str = '你是一个专业的AI助手。',
        model: str = 'deepseek-v3.2',
        temperature: float = 0.2,
        timeout: int = 60,
        user_id: str = None
    ) -> dict:
        """
        异步调用 DeepSeek 模型
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            model: 模型名称
            temperature: 温度参数
            timeout: 超时时间（秒）
            user_id: 用户ID
            
        Returns:
            dict: {success, content, error, tokens, duration}
        """
        config = ConfigService.load_config(user_id=user_id)
        api_key = config.get('deepseek_api_key')
        
        if not api_key:
            return {'success': False, 'error': '请先配置 DeepSeek API Key', 'tokens': 0, 'duration': 0}
        
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': temperature
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    LLMService.DEEPSEEK_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    result = await response.json()
                    duration = int((time.time() - start_time) * 1000)
                    
                    if 'choices' in result:
                        content = result['choices'][0]['message']['content']
                        usage = result.get('usage', {})
                        return {
                            'success': True,
                            'content': content,
                            'tokens': {
                                'prompt': usage.get('prompt_tokens', 0),
                                'completion': usage.get('completion_tokens', 0),
                                'total': usage.get('total_tokens', 0)
                            },
                            'duration': duration
                        }
                    else:
                        error_msg = result.get('error', {}).get('message', '请求失败')
                        return {'success': False, 'error': error_msg, 'tokens': 0, 'duration': duration}
                        
        except asyncio.TimeoutError:
            duration = int((time.time() - start_time) * 1000)
            return {'success': False, 'error': '请求超时', 'error_type': 'timeout', 'tokens': 0, 'duration': duration}
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            return {'success': False, 'error': str(e), 'error_type': 'api_error', 'tokens': 0, 'duration': duration}
    
    @staticmethod
    async def call_with_retry(
        prompt: str,
        system_prompt: str = '你是一个专业的AI助手。',
        model: str = 'deepseek-v3.2',
        temperature: float = 0.2,
        timeout: int = 60,
        max_retries: int = 3,
        user_id: str = None
    ) -> dict:
        """
        带重试机制的异步调用
        
        Args:
            max_retries: 最大重试次数
            其他参数同 call_deepseek_async
            
        Returns:
            dict: {success, content, error, tokens, duration, retry_count}
        """
        last_error = None
        total_duration = 0
        
        for attempt in range(max_retries + 1):
            result = await LLMService.call_deepseek_async(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature,
                timeout=timeout,
                user_id=user_id
            )
            
            total_duration += result.get('duration', 0)
            
            if result.get('success'):
                result['retry_count'] = attempt
                result['duration'] = total_duration
                return result
            
            last_error = result.get('error', '未知错误')
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries:
                wait_time = 2 ** attempt  # 指数退避: 1, 2, 4 秒
                print(f"[LLM] 重试 {attempt + 1}/{max_retries}，等待 {wait_time} 秒...")
                await asyncio.sleep(wait_time)
        
        return {
            'success': False,
            'error': last_error,
            'error_type': result.get('error_type', 'other'),
            'tokens': 0,
            'duration': total_duration,
            'retry_count': max_retries
        }
    
    @staticmethod
    async def parallel_call(
        prompts: List[dict],
        max_concurrent: int = 10,
        model: str = 'deepseek-v3.2',
        temperature: float = 0.2,
        timeout: int = 60,
        max_retries: int = 3,
        user_id: str = None
    ) -> List[dict]:
        """
        并行调用 LLM
        
        Args:
            prompts: 提示词列表，每项为 {prompt, system_prompt?, id?}
            max_concurrent: 最大并发数
            model: 模型名称
            temperature: 温度参数
            timeout: 单次请求超时时间
            max_retries: 最大重试次数
            user_id: 用户ID
            
        Returns:
            list: [{id, success, content, error, tokens, duration}]
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def call_single(item: dict, index: int) -> dict:
            async with semaphore:
                prompt = item.get('prompt', '')
                system_prompt = item.get('system_prompt', '你是一个专业的AI助手。')
                item_id = item.get('id', str(index))
                
                result = await LLMService.call_with_retry(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=model,
                    temperature=temperature,
                    timeout=timeout,
                    max_retries=max_retries,
                    user_id=user_id
                )
                
                result['id'] = item_id
                return result
        
        # 并行执行所有请求
        tasks = [call_single(item, i) for i, item in enumerate(prompts)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'id': prompts[i].get('id', str(i)),
                    'success': False,
                    'error': str(result),
                    'error_type': 'exception',
                    'tokens': 0,
                    'duration': 0
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    @staticmethod
    def run_parallel_call(
        prompts: List[dict],
        max_concurrent: int = 10,
        model: str = 'deepseek-v3.2',
        temperature: float = 0.2,
        timeout: int = 60,
        max_retries: int = 3,
        user_id: str = None
    ) -> List[dict]:
        """
        同步包装的并行调用方法（用于非异步环境）
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            LLMService.parallel_call(
                prompts=prompts,
                max_concurrent=max_concurrent,
                model=model,
                temperature=temperature,
                timeout=timeout,
                max_retries=max_retries,
                user_id=user_id
            )
        )
    
    @staticmethod
    def log_llm_call(
        task_id: str,
        analysis_type: str,
        target_id: str,
        model: str,
        tokens: dict,
        duration_ms: int,
        status: str,
        retry_count: int = 0,
        error_type: str = None,
        error_message: str = None
    ):
        """
        记录 LLM 调用日志到数据库
        """
        try:
            from .database_service import AppDatabaseService
            
            log_id = str(uuid.uuid4())[:8]
            sql = """
                INSERT INTO llm_call_logs 
                (log_id, task_id, analysis_type, target_id, model, 
                 prompt_tokens, completion_tokens, total_tokens,
                 duration_ms, retry_count, status, error_type, error_message, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            AppDatabaseService.execute_insert(sql, (
                log_id, task_id, analysis_type, target_id, model,
                tokens.get('prompt', 0), tokens.get('completion', 0), tokens.get('total', 0),
                duration_ms, retry_count, status, error_type, error_message, datetime.now()
            ))
        except Exception as e:
            print(f"[LLM] 记录日志失败: {e}")
    
    @staticmethod
    def get_token_stats(days: int = 7) -> dict:
        """
        获取 token 使用统计
        
        Args:
            days: 统计天数
            
        Returns:
            dict: {today, week, month, by_model, by_type}
        """
        try:
            from .database_service import AppDatabaseService
            
            # 今日统计
            sql_today = """
                SELECT COALESCE(SUM(total_tokens), 0) as tokens, COUNT(*) as calls
                FROM llm_call_logs
                WHERE DATE(created_at) = CURDATE() AND status = 'success'
            """
            today_result = AppDatabaseService.execute_query(sql_today)
            
            # 本周统计
            sql_week = """
                SELECT COALESCE(SUM(total_tokens), 0) as tokens, COUNT(*) as calls
                FROM llm_call_logs
                WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) AND status = 'success'
            """
            week_result = AppDatabaseService.execute_query(sql_week)
            
            # 本月统计
            sql_month = """
                SELECT COALESCE(SUM(total_tokens), 0) as tokens, COUNT(*) as calls
                FROM llm_call_logs
                WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) AND status = 'success'
            """
            month_result = AppDatabaseService.execute_query(sql_month)
            
            # 按模型统计
            sql_by_model = """
                SELECT model, COALESCE(SUM(total_tokens), 0) as tokens, COUNT(*) as calls
                FROM llm_call_logs
                WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                GROUP BY model
            """
            model_result = AppDatabaseService.execute_query(sql_by_model, (days,))
            
            # 按类型统计
            sql_by_type = """
                SELECT analysis_type, COALESCE(SUM(total_tokens), 0) as tokens, COUNT(*) as calls
                FROM llm_call_logs
                WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                GROUP BY analysis_type
            """
            type_result = AppDatabaseService.execute_query(sql_by_type, (days,))
            
            return {
                'today': {
                    'tokens': today_result[0]['tokens'] if today_result else 0,
                    'calls': today_result[0]['calls'] if today_result else 0
                },
                'week': {
                    'tokens': week_result[0]['tokens'] if week_result else 0,
                    'calls': week_result[0]['calls'] if week_result else 0
                },
                'month': {
                    'tokens': month_result[0]['tokens'] if month_result else 0,
                    'calls': month_result[0]['calls'] if month_result else 0
                },
                'by_model': {row['model']: {'tokens': row['tokens'], 'calls': row['calls']} for row in (model_result or [])},
                'by_type': {row['analysis_type']: {'tokens': row['tokens'], 'calls': row['calls']} for row in (type_result or [])}
            }
        except Exception as e:
            print(f"[LLM] 获取统计失败: {e}")
            return {'today': {'tokens': 0, 'calls': 0}, 'week': {'tokens': 0, 'calls': 0}, 'month': {'tokens': 0, 'calls': 0}}
