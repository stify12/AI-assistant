"""
存储服务模块
提供文件存储和 JSON 文件操作功能
支持文件存储和数据库存储两种模式
"""
import os
import json
from datetime import datetime

# 是否使用数据库存储（可通过环境变量控制）
USE_DB_STORAGE = os.environ.get('USE_DB_STORAGE', 'true').lower() == 'true'


class StorageService:
    """存储服务类"""
    
    # 目录常量
    ANALYSIS_TASKS_DIR = 'analysis_tasks'
    ANALYSIS_FILES_DIR = 'analysis_files'
    PROMPT_TASKS_DIR = 'prompt_tasks'
    BATCH_TASKS_DIR = 'batch_tasks'
    DATASETS_DIR = 'datasets'
    BASELINE_EFFECTS_DIR = 'baseline_effects'
    EXPORTS_DIR = 'exports'
    
    @staticmethod
    def ensure_dir(directory):
        """确保目录存在"""
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    @staticmethod
    def load_json(filepath):
        """加载 JSON 文件"""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    @staticmethod
    def save_json(filepath, data):
        """保存 JSON 文件"""
        # 确保目录存在
        directory = os.path.dirname(filepath)
        if directory:
            StorageService.ensure_dir(directory)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def list_json_files(directory):
        """列出目录下所有 JSON 文件"""
        StorageService.ensure_dir(directory)
        files = []
        for filename in os.listdir(directory):
            if filename.endswith('.json'):
                files.append(filename)
        return files
    
    @staticmethod
    def delete_file(filepath):
        """删除文件"""
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    
    @staticmethod
    def file_exists(filepath):
        """检查文件是否存在"""
        return os.path.exists(filepath)
    
    @staticmethod
    def get_file_path(directory, file_id, extension='.json'):
        """获取文件完整路径"""
        StorageService.ensure_dir(directory)
        return os.path.join(directory, f'{file_id}{extension}')
    
    # ========== 分析任务存储 ==========
    
    @staticmethod
    def load_analysis_task(task_id):
        """加载分析任务"""
        filepath = StorageService.get_file_path(StorageService.ANALYSIS_TASKS_DIR, task_id)
        return StorageService.load_json(filepath)
    
    @staticmethod
    def save_analysis_task(task_id, task_data):
        """保存分析任务"""
        task_data['updated_at'] = datetime.now().isoformat()
        filepath = StorageService.get_file_path(StorageService.ANALYSIS_TASKS_DIR, task_id)
        StorageService.save_json(filepath, task_data)
    
    @staticmethod
    def list_analysis_tasks():
        """列出所有分析任务"""
        return StorageService.list_json_files(StorageService.ANALYSIS_TASKS_DIR)
    
    # ========== Prompt 任务存储 ==========
    
    @staticmethod
    def load_prompt_task(task_id):
        """加载 Prompt 任务"""
        filepath = StorageService.get_file_path(StorageService.PROMPT_TASKS_DIR, task_id)
        return StorageService.load_json(filepath)
    
    @staticmethod
    def save_prompt_task(task_id, task_data):
        """保存 Prompt 任务"""
        task_data['updated_at'] = datetime.now().isoformat()
        filepath = StorageService.get_file_path(StorageService.PROMPT_TASKS_DIR, task_id)
        StorageService.save_json(filepath, task_data)
    
    @staticmethod
    def delete_prompt_task(task_id):
        """删除 Prompt 任务"""
        filepath = StorageService.get_file_path(StorageService.PROMPT_TASKS_DIR, task_id)
        return StorageService.delete_file(filepath)
    
    @staticmethod
    def list_prompt_tasks():
        """列出所有 Prompt 任务"""
        return StorageService.list_json_files(StorageService.PROMPT_TASKS_DIR)
    
    # ========== 批量任务存储 ==========
    
    @staticmethod
    def load_batch_task(task_id):
        """加载批量任务"""
        filepath = StorageService.get_file_path(StorageService.BATCH_TASKS_DIR, task_id)
        return StorageService.load_json(filepath)
    
    @staticmethod
    def save_batch_task(task_id, task_data):
        """保存批量任务"""
        filepath = StorageService.get_file_path(StorageService.BATCH_TASKS_DIR, task_id)
        StorageService.save_json(filepath, task_data)
    
    @staticmethod
    def delete_batch_task(task_id):
        """删除批量任务"""
        filepath = StorageService.get_file_path(StorageService.BATCH_TASKS_DIR, task_id)
        return StorageService.delete_file(filepath)
    
    @staticmethod
    def list_batch_tasks():
        """列出所有批量任务"""
        return StorageService.list_json_files(StorageService.BATCH_TASKS_DIR)
    
    # ========== 数据集存储 ==========
    
    @staticmethod
    def load_dataset(dataset_id):
        """加载数据集"""
        if USE_DB_STORAGE:
            from .database_service import AppDatabaseService
            row = AppDatabaseService.get_dataset(dataset_id)
            if row:
                # 获取基准效果
                effects = AppDatabaseService.get_baseline_effects(dataset_id)
                base_effects = {}
                for effect in effects:
                    page_key = str(effect['page_num'])
                    if page_key not in base_effects:
                        base_effects[page_key] = []
                    
                    # 解析extra_data获取额外字段
                    extra_data = effect.get('extra_data')
                    if isinstance(extra_data, str):
                        try:
                            extra_data = json.loads(extra_data)
                        except:
                            extra_data = {}
                    elif extra_data is None:
                        extra_data = {}
                    
                    base_effects[page_key].append({
                        'index': effect['question_index'],
                        'tempIndex': effect['temp_index'],
                        'type': effect['question_type'],
                        'answer': effect['answer'],
                        'userAnswer': effect['user_answer'],
                        'correct': effect['is_correct'],
                        'questionType': extra_data.get('questionType', 'objective'),
                        'bvalue': extra_data.get('bvalue', '4')
                    })
                
                pages = row['pages']
                if isinstance(pages, str):
                    pages = json.loads(pages)
                
                return {
                    'dataset_id': row['dataset_id'],
                    'book_id': row['book_id'],
                    'book_name': row['book_name'],
                    'subject_id': row['subject_id'],
                    'pages': pages,
                    'question_count': row['question_count'],
                    'base_effects': base_effects,
                    'created_at': row['created_at'].isoformat() if row['created_at'] else '',
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else ''
                }
            return None
        
        filepath = StorageService.get_file_path(StorageService.DATASETS_DIR, dataset_id)
        return StorageService.load_json(filepath)
    
    @staticmethod
    def save_dataset(dataset_id, data):
        """保存数据集"""
        if USE_DB_STORAGE:
            from .database_service import AppDatabaseService
            existing = AppDatabaseService.get_dataset(dataset_id)
            
            pages = data.get('pages', [])
            question_count = 0
            base_effects = data.get('base_effects', {})
            for page_data in base_effects.values():
                if isinstance(page_data, list):
                    question_count += len(page_data)
            
            if existing:
                AppDatabaseService.update_dataset(
                    dataset_id,
                    book_id=data.get('book_id'),
                    book_name=data.get('book_name'),
                    subject_id=data.get('subject_id'),
                    pages=pages,
                    question_count=question_count
                )
            else:
                AppDatabaseService.create_dataset(
                    dataset_id,
                    data.get('book_id'),
                    pages,
                    data.get('book_name'),
                    data.get('subject_id'),
                    question_count
                )
            
            # 保存基准效果（包含questionType和bvalue）
            for page_num, effects in base_effects.items():
                formatted_effects = []
                for effect in effects:
                    formatted_effects.append({
                        'index': effect.get('index', ''),
                        'tempIndex': effect.get('tempIndex', 0),
                        'type': effect.get('type', effect.get('questionType', 'choice')),
                        'answer': effect.get('answer', ''),
                        'userAnswer': effect.get('userAnswer', ''),
                        'correct': effect.get('correct', ''),
                        'questionType': effect.get('questionType', 'objective'),
                        'bvalue': effect.get('bvalue', '4')
                    })
                AppDatabaseService.save_baseline_effects(dataset_id, int(page_num), formatted_effects)
            return
        
        filepath = StorageService.get_file_path(StorageService.DATASETS_DIR, dataset_id)
        StorageService.save_json(filepath, data)
    
    @staticmethod
    def delete_dataset(dataset_id):
        """删除数据集"""
        if USE_DB_STORAGE:
            from .database_service import AppDatabaseService
            return AppDatabaseService.delete_dataset(dataset_id)
        
        filepath = StorageService.get_file_path(StorageService.DATASETS_DIR, dataset_id)
        return StorageService.delete_file(filepath)
    
    @staticmethod
    def list_datasets():
        """列出所有数据集"""
        if USE_DB_STORAGE:
            from .database_service import AppDatabaseService
            rows = AppDatabaseService.get_datasets()
            return [f"{row['dataset_id']}.json" for row in rows]
        
        return StorageService.list_json_files(StorageService.DATASETS_DIR)
    
    # ========== 基准效果存储 ==========
    
    @staticmethod
    def load_baseline_effect(filename):
        """加载基准效果"""
        filepath = os.path.join(StorageService.BASELINE_EFFECTS_DIR, filename)
        return StorageService.load_json(filepath)
    
    @staticmethod
    def save_baseline_effect(filename, data):
        """保存基准效果"""
        StorageService.ensure_dir(StorageService.BASELINE_EFFECTS_DIR)
        filepath = os.path.join(StorageService.BASELINE_EFFECTS_DIR, filename)
        StorageService.save_json(filepath, data)
    
    @staticmethod
    def delete_baseline_effect(filename):
        """删除基准效果"""
        filepath = os.path.join(StorageService.BASELINE_EFFECTS_DIR, filename)
        return StorageService.delete_file(filepath)
    
    @staticmethod
    def list_baseline_effects():
        """列出所有基准效果文件"""
        StorageService.ensure_dir(StorageService.BASELINE_EFFECTS_DIR)
        files = []
        for filename in os.listdir(StorageService.BASELINE_EFFECTS_DIR):
            if filename.endswith('.json') and filename != 'README.md':
                files.append(filename)
        return files
