"""
存储服务模块
提供文件存储和 JSON 文件操作功能
支持文件存储和数据库存储两种模式
"""
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

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
    
    # ========== 数据集名称生成 ==========
    
    @staticmethod
    def generate_default_dataset_name(data: Dict[str, Any]) -> str:
        """
        生成默认数据集名称
        
        格式："{book_name}_P{min_page}-{max_page}_{timestamp}"
        - 单页："{book_name}_P{page}_{timestamp}"
        - 无页码："{book_name}_{timestamp}"
        - 无书名：使用 "未知书本"
        
        Args:
            data: 数据集数据字典，包含 book_name, pages 等字段
        
        Returns:
            str: 生成的默认名称
        """
        book_name = data.get('book_name') or '未知书本'
        pages = data.get('pages', [])
        
        # 处理页码部分
        page_part = ""
        if pages and isinstance(pages, list):
            valid_pages = sorted([p for p in pages if isinstance(p, int) and p > 0])
            if valid_pages:
                if len(valid_pages) == 1:
                    page_part = f"_P{valid_pages[0]}"
                else:
                    page_part = f"_P{min(valid_pages)}-{max(valid_pages)}"
        
        # 时间戳格式：MMDDHHmm
        timestamp = datetime.now().strftime('%m%d%H%M')
        
        return f"{book_name}{page_part}_{timestamp}"
    
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
        """
        加载数据集
        
        兼容无 name 字段的旧数据，自动生成默认名称
        """
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
                
                # 处理 name 字段：如果为空则生成默认名称
                name = row.get('name')
                if not name:
                    name = StorageService.generate_default_dataset_name({
                        'book_name': row.get('book_name'),
                        'pages': pages
                    })
                
                return {
                    'dataset_id': row['dataset_id'],
                    'name': name,
                    'book_id': row['book_id'],
                    'book_name': row['book_name'],
                    'subject_id': row['subject_id'],
                    'pages': pages,
                    'question_count': row['question_count'],
                    'description': row.get('description', ''),
                    'base_effects': base_effects,
                    'created_at': row['created_at'].isoformat() if row['created_at'] else '',
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else ''
                }
            return None
        
        # 文件存储模式
        filepath = StorageService.get_file_path(StorageService.DATASETS_DIR, dataset_id)
        data = StorageService.load_json(filepath)
        
        if data:
            # 处理 name 字段：如果为空则生成默认名称
            if not data.get('name'):
                data['name'] = StorageService.generate_default_dataset_name(data)
        
        return data
    
    @staticmethod
    def save_dataset(dataset_id, data):
        """
        保存数据集
        
        支持 name 字段，如果未提供或为空则自动生成默认名称
        """
        # 处理 name 字段：如果未提供或为空，生成默认名称
        name = data.get('name', '').strip() if data.get('name') else ''
        if not name:
            name = StorageService.generate_default_dataset_name(data)
        data['name'] = name
        
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
                    name=name,
                    book_id=data.get('book_id'),
                    book_name=data.get('book_name'),
                    subject_id=data.get('subject_id'),
                    pages=pages,
                    question_count=question_count,
                    description=data.get('description')
                )
            else:
                AppDatabaseService.create_dataset(
                    dataset_id,
                    data.get('book_id'),
                    pages,
                    data.get('book_name'),
                    data.get('subject_id'),
                    question_count,
                    name=name,
                    description=data.get('description')
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
        
        # 文件存储模式
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
    
    @staticmethod
    def get_all_datasets_summary():
        """
        获取所有数据集的摘要信息（不加载base_effects详情，提升性能）
        
        包含 name 字段，对于无 name 的旧数据自动生成默认名称
        """
        if USE_DB_STORAGE:
            from .database_service import AppDatabaseService
            # 直接查询数据库，一次性获取所有需要的字段
            sql = """
                SELECT dataset_id, name, book_id, book_name, subject_id, pages, question_count, description, created_at
                FROM datasets
                ORDER BY created_at DESC
            """
            rows = AppDatabaseService.execute_query(sql)
            result = []
            for row in rows:
                pages = row.get('pages', [])
                if isinstance(pages, str):
                    try:
                        pages = json.loads(pages)
                    except:
                        pages = []
                
                # 处理 name 字段：如果为空则生成默认名称
                name = row.get('name')
                if not name:
                    name = StorageService.generate_default_dataset_name({
                        'book_name': row.get('book_name'),
                        'pages': pages
                    })
                
                result.append({
                    'dataset_id': row['dataset_id'],
                    'name': name,
                    'book_id': row['book_id'],
                    'book_name': row['book_name'],
                    'subject_id': row['subject_id'],
                    'pages': pages,
                    'question_count': row.get('question_count', 0),
                    'description': row.get('description', ''),
                    'created_at': row['created_at'].isoformat() if row.get('created_at') else ''
                })
            return result
        
        # 文件存储模式：只读取必要字段
        result = []
        for filename in StorageService.list_json_files(StorageService.DATASETS_DIR):
            dataset_id = filename[:-5]
            filepath = StorageService.get_file_path(StorageService.DATASETS_DIR, dataset_id)
            data = StorageService.load_json(filepath)
            if data:
                # 计算题目数量
                question_count = 0
                for effects in data.get('base_effects', {}).values():
                    question_count += len(effects) if isinstance(effects, list) else 0
                
                # 处理 name 字段：如果为空则生成默认名称
                name = data.get('name')
                if not name:
                    name = StorageService.generate_default_dataset_name(data)
                
                result.append({
                    'dataset_id': dataset_id,
                    'name': name,
                    'book_id': data.get('book_id'),
                    'book_name': data.get('book_name', ''),
                    'subject_id': data.get('subject_id'),
                    'pages': data.get('pages', []),
                    'question_count': question_count,
                    'description': data.get('description', ''),
                    'created_at': data.get('created_at', '')
                })
        return result
    
    @staticmethod
    def get_matching_datasets(book_id: str, page_num: int) -> List[Dict[str, Any]]:
        """
        获取匹配的数据集列表
        
        根据 book_id 和 page_num 查询所有匹配的数据集，
        按创建时间倒序排列（最新的排在前面）
        
        Args:
            book_id: 书本ID
            page_num: 页码
        
        Returns:
            list: 匹配的数据集列表，包含 dataset_id, name, book_name, pages, question_count, created_at
        """
        if USE_DB_STORAGE:
            from .database_service import AppDatabaseService
            rows = AppDatabaseService.get_datasets_by_book_page(book_id, page_num)
            result = []
            for row in rows:
                pages = row.get('pages', [])
                if isinstance(pages, str):
                    try:
                        pages = json.loads(pages)
                    except:
                        pages = []
                
                # 如果没有名称，生成默认名称
                name = row.get('name')
                if not name:
                    name = StorageService.generate_default_dataset_name({
                        'book_name': row.get('book_name'),
                        'pages': pages
                    })
                
                result.append({
                    'dataset_id': row['dataset_id'],
                    'name': name,
                    'book_id': row['book_id'],
                    'book_name': row.get('book_name', ''),
                    'subject_id': row.get('subject_id'),
                    'pages': pages,
                    'question_count': row.get('question_count', 0),
                    'description': row.get('description', ''),
                    'created_at': row['created_at'].isoformat() if row.get('created_at') else ''
                })
            return result
        
        # 文件存储模式：遍历所有数据集查找匹配
        result = []
        for filename in StorageService.list_json_files(StorageService.DATASETS_DIR):
            dataset_id = filename[:-5]
            filepath = StorageService.get_file_path(StorageService.DATASETS_DIR, dataset_id)
            data = StorageService.load_json(filepath)
            if data and data.get('book_id') == book_id:
                pages = data.get('pages', [])
                if page_num in pages:
                    name = data.get('name')
                    if not name:
                        name = StorageService.generate_default_dataset_name(data)
                    
                    question_count = 0
                    for effects in data.get('base_effects', {}).values():
                        question_count += len(effects) if isinstance(effects, list) else 0
                    
                    result.append({
                        'dataset_id': dataset_id,
                        'name': name,
                        'book_id': data.get('book_id'),
                        'book_name': data.get('book_name', ''),
                        'subject_id': data.get('subject_id'),
                        'pages': pages,
                        'question_count': question_count,
                        'description': data.get('description', ''),
                        'created_at': data.get('created_at', '')
                    })
        
        # 按创建时间倒序排列
        result.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return result
    
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
