"""
配置服务模块
提供配置文件和提示词文件的读写操作
支持环境变量覆盖敏感配置
支持从请求头获取API密钥（浏览器localStorage存储）
"""
import os
import json
from flask import request


class ConfigService:
    """配置服务类"""
    
    CONFIG_FILE = 'config.json'
    PROMPTS_FILE = 'prompts.json'
    SUBJECTS_FILE = 'subjects.json'
    MODELS_FILE = 'custom_models.json'
    GRADING_PROMPTS_FILE = 'grading_prompts.json'
    EVAL_CONFIG_FILE = 'eval_config.json'
    
    # 环境变量映射（环境变量名 -> 配置路径）
    ENV_MAPPINGS = {
        # API密钥
        'DOUBAO_API_KEY': 'api_key',
        'DOUBAO_API_URL': 'api_url',
        'DEEPSEEK_API_KEY': 'deepseek_api_key',
        'QWEN_API_KEY': 'qwen_api_key',
        # 主数据库
        'MYSQL_HOST': 'mysql.host',
        'MYSQL_PORT': 'mysql.port',
        'MYSQL_USER': 'mysql.user',
        'MYSQL_PASSWORD': 'mysql.password',
        'MYSQL_DATABASE': 'mysql.database',
        # 应用数据库
        'APP_MYSQL_HOST': 'app_mysql.host',
        'APP_MYSQL_PORT': 'app_mysql.port',
        'APP_MYSQL_USER': 'app_mysql.user',
        'APP_MYSQL_PASSWORD': 'app_mysql.password',
        'APP_MYSQL_DATABASE': 'app_mysql.database',
    }
    
    # 请求头映射（请求头名 -> 配置路径）
    HEADER_MAPPINGS = {
        'X-Doubao-Api-Key': 'api_key',
        'X-Gpt-Api-Key': 'gpt_api_key',
        'X-Deepseek-Api-Key': 'deepseek_api_key',
        'X-Qwen-Api-Key': 'qwen_api_key',
    }
    
    @staticmethod
    def _set_nested_value(config, path, value):
        """设置嵌套配置值"""
        keys = path.split('.')
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        # 处理端口号等数字类型
        if keys[-1] == 'port' and value:
            value = int(value)
        current[keys[-1]] = value
    
    @staticmethod
    def _apply_env_overrides(config):
        """应用环境变量覆盖"""
        for env_name, config_path in ConfigService.ENV_MAPPINGS.items():
            env_value = os.environ.get(env_name)
            if env_value:
                ConfigService._set_nested_value(config, config_path, env_value)
        return config
    
    @staticmethod
    def _apply_header_overrides(config):
        """应用请求头覆盖（用于浏览器localStorage存储的API密钥）"""
        try:
            for header_name, config_path in ConfigService.HEADER_MAPPINGS.items():
                header_value = request.headers.get(header_name)
                if header_value:
                    ConfigService._set_nested_value(config, config_path, header_value)
        except RuntimeError:
            # 不在请求上下文中，跳过
            pass
        return config
    
    @staticmethod
    def load_config(apply_headers=True, user_id=None):
        """加载配置（优先级：用户数据库配置 > 环境变量 > 文件配置）
        
        Args:
            apply_headers: 是否应用请求头中的API密钥覆盖
            user_id: 用户ID，如果提供则从数据库加载用户配置
        """
        # 先从文件加载基础配置
        if os.path.exists(ConfigService.CONFIG_FILE):
            with open(ConfigService.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {
                'api_key': '',
                'model': 'doubao-1.5-vision-pro-250328',
                'api_url': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
                'gpt_api_key': '',
                'gpt_api_url': 'https://api.gpt.ge/v1/chat/completions',
                'deepseek_api_key': '',
                'qwen_api_key': ''
            }
        
        # 应用环境变量覆盖
        config = ConfigService._apply_env_overrides(config)
        
        # 从数据库加载用户配置（优先级最高）
        if user_id:
            try:
                from services.database_service import AppDatabaseService
                user_api_keys = AppDatabaseService.get_user_api_keys(user_id)
                print(f"[Config] 加载用户 {user_id} 的配置: {list(user_api_keys.keys()) if user_api_keys else '无'}")
                if user_api_keys:
                    # 用户配置覆盖默认配置
                    for key, value in user_api_keys.items():
                        if value:  # 只覆盖非空值
                            config[key] = value
            except Exception as e:
                print(f"[Config] 加载用户配置失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 应用请求头覆盖（浏览器localStorage中的API密钥）
        if apply_headers:
            config = ConfigService._apply_header_overrides(config)
        
        return config
    
    @staticmethod
    def get_api_keys_status():
        """获取API密钥配置状态（不返回实际密钥值）"""
        config = ConfigService.load_config(apply_headers=False)
        return {
            'doubao': bool(config.get('api_key')),
            'deepseek': bool(config.get('deepseek_api_key')),
            'qwen': bool(config.get('qwen_api_key')),
        }
    
    @staticmethod
    def save_config(config):
        """保存配置"""
        with open(ConfigService.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_prompts():
        """加载提示词列表"""
        if os.path.exists(ConfigService.PROMPTS_FILE):
            with open(ConfigService.PROMPTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return [{'name': '默认批改', 'content': '请批改这份作业，指出错误并给出评分和建议。'}]
    
    @staticmethod
    def save_prompts(prompts):
        """保存提示词列表"""
        with open(ConfigService.PROMPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_subjects():
        """加载学科配置"""
        if os.path.exists(ConfigService.SUBJECTS_FILE):
            with open(ConfigService.SUBJECTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "math": {
                "name": "数学",
                "questionTypes": {
                    "objective": {"weight": 0.3},
                    "calculation": {"weight": 0.5},
                    "subjective": {"weight": 0.2}
                },
                "errorCategories": ["识别错误", "计算错误", "格式错误"]
            },
            "chinese": {
                "name": "语文",
                "questionTypes": {
                    "objective": {"weight": 0.2},
                    "subjective": {"weight": 0.5},
                    "essay": {"weight": 0.3}
                },
                "errorCategories": ["识别错误", "理解错误", "表述错误"]
            },
            "english": {
                "name": "英语",
                "questionTypes": {
                    "objective": {"weight": 0.4},
                    "subjective": {"weight": 0.4},
                    "essay": {"weight": 0.2}
                },
                "errorCategories": ["识别错误", "语法错误", "拼写错误"]
            }
        }
    
    @staticmethod
    def save_subjects(subjects):
        """保存学科配置"""
        with open(ConfigService.SUBJECTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(subjects, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_custom_models():
        """加载自定义模型配置"""
        if os.path.exists(ConfigService.MODELS_FILE):
            with open(ConfigService.MODELS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    @staticmethod
    def save_custom_models(models):
        """保存自定义模型配置"""
        with open(ConfigService.MODELS_FILE, 'w', encoding='utf-8') as f:
            json.dump(models, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_grading_prompts():
        """加载学科批改提示词配置"""
        if os.path.exists(ConfigService.GRADING_PROMPTS_FILE):
            with open(ConfigService.GRADING_PROMPTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @staticmethod
    def save_grading_prompts(prompts):
        """保存学科批改提示词配置"""
        with open(ConfigService.GRADING_PROMPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_eval_config():
        """加载评估配置"""
        if os.path.exists(ConfigService.EVAL_CONFIG_FILE):
            with open(ConfigService.EVAL_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'dimensions': {
                'accuracy_class': {'enabled': True, 'metrics': ['accuracy', 'precision', 'recall', 'f1', 'consistency']},
                'efficiency_class': {'enabled': True, 'metrics': ['single_time', 'batch_avg_time']},
                'resource_class': {'enabled': True, 'metrics': ['token_usage', 'token_cost']}
            },
            'subject_rules': {
                'math': {'objective_ratio': 0.3, 'calculation_ratio': 0.5, 'subjective_ratio': 0.2},
                'chinese': {'objective_ratio': 0.2, 'subjective_ratio': 0.5, 'essay_ratio': 0.3}
            },
            'eval_scope': 'single'
        }
    
    @staticmethod
    def save_eval_config(config):
        """保存评估配置"""
        with open(ConfigService.EVAL_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
