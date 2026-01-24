"""
最佳实践库服务 (US-16)

支持:
- Prompt版本管理
- 最佳实践标记和收藏
- 效果对比
"""
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from .storage_service import StorageService


class BestPracticeService:
    """最佳实践库服务"""
    
    PRACTICES_DIR = 'best_practices'
    PRACTICES_FILE = 'practices.json'
    
    @staticmethod
    def _get_filepath() -> str:
        """获取存储文件路径"""
        StorageService.ensure_dir(BestPracticeService.PRACTICES_DIR)
        return os.path.join(BestPracticeService.PRACTICES_DIR, BestPracticeService.PRACTICES_FILE)
    
    @staticmethod
    def _load_practices() -> List[Dict]:
        """加载最佳实践数据"""
        filepath = BestPracticeService._get_filepath()
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    @staticmethod
    def _save_practices(practices: List[Dict]):
        """保存最佳实践数据"""
        filepath = BestPracticeService._get_filepath()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(practices, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def add_practice(
        name: str,
        category: str,
        prompt_content: str,
        description: str = '',
        tags: List[str] = None,
        metrics: Dict = None
    ) -> Dict[str, Any]:
        """
        添加最佳实践 (US-16.1)
        """
        practices = BestPracticeService._load_practices()
        
        practice_id = f"bp_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        practice = {
            'id': practice_id,
            'name': name,
            'category': category,
            'prompt_content': prompt_content,
            'description': description,
            'tags': tags or [],
            'metrics': metrics or {},
            'version': 1,
            'is_starred': False,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'usage_count': 0
        }
        
        practices.append(practice)
        BestPracticeService._save_practices(practices)
        
        return {'success': True, 'practice': practice}
    
    @staticmethod
    def get_practices(
        category: str = None,
        tag: str = None,
        starred_only: bool = False
    ) -> List[Dict]:
        """
        获取最佳实践列表 (US-16.2)
        """
        practices = BestPracticeService._load_practices()
        
        if category:
            practices = [p for p in practices if p.get('category') == category]
        if tag:
            practices = [p for p in practices if tag in p.get('tags', [])]
        if starred_only:
            practices = [p for p in practices if p.get('is_starred')]
        
        # 按使用次数和星标排序
        practices.sort(key=lambda x: (x.get('is_starred', False), x.get('usage_count', 0)), reverse=True)
        
        return practices
    
    @staticmethod
    def get_practice(practice_id: str) -> Optional[Dict]:
        """获取单个最佳实践"""
        practices = BestPracticeService._load_practices()
        for p in practices:
            if p.get('id') == practice_id:
                return p
        return None
    
    @staticmethod
    def update_practice(
        practice_id: str,
        updates: Dict
    ) -> Dict[str, Any]:
        """
        更新最佳实践 (US-16.3)
        """
        practices = BestPracticeService._load_practices()
        
        for i, p in enumerate(practices):
            if p.get('id') == practice_id:
                # 如果prompt内容变化，增加版本号
                if 'prompt_content' in updates and updates['prompt_content'] != p.get('prompt_content'):
                    p['version'] = p.get('version', 1) + 1
                
                p.update(updates)
                p['updated_at'] = datetime.now().isoformat()
                practices[i] = p
                BestPracticeService._save_practices(practices)
                return {'success': True, 'practice': p}
        
        return {'success': False, 'error': '实践不存在'}
    
    @staticmethod
    def toggle_star(practice_id: str) -> Dict[str, Any]:
        """切换星标状态"""
        practices = BestPracticeService._load_practices()
        
        for i, p in enumerate(practices):
            if p.get('id') == practice_id:
                p['is_starred'] = not p.get('is_starred', False)
                practices[i] = p
                BestPracticeService._save_practices(practices)
                return {'success': True, 'is_starred': p['is_starred']}
        
        return {'success': False, 'error': '实践不存在'}
    
    @staticmethod
    def delete_practice(practice_id: str) -> Dict[str, Any]:
        """删除最佳实践"""
        practices = BestPracticeService._load_practices()
        
        for i, p in enumerate(practices):
            if p.get('id') == practice_id:
                practices.pop(i)
                BestPracticeService._save_practices(practices)
                return {'success': True}
        
        return {'success': False, 'error': '实践不存在'}
    
    @staticmethod
    def record_usage(practice_id: str) -> Dict[str, Any]:
        """记录使用次数"""
        practices = BestPracticeService._load_practices()
        
        for i, p in enumerate(practices):
            if p.get('id') == practice_id:
                p['usage_count'] = p.get('usage_count', 0) + 1
                p['last_used_at'] = datetime.now().isoformat()
                practices[i] = p
                BestPracticeService._save_practices(practices)
                return {'success': True, 'usage_count': p['usage_count']}
        
        return {'success': False, 'error': '实践不存在'}

    
    @staticmethod
    def get_prompt_versions(practice_id: str) -> List[Dict]:
        """
        获取Prompt版本历史 (US-16.4)
        """
        # 从批量任务中查找使用该实践的记录
        batch_dir = StorageService.BATCH_TASKS_DIR
        versions = []
        
        if not os.path.exists(batch_dir):
            return versions
        
        for filename in os.listdir(batch_dir):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(batch_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    task = json.load(f)
                
                if task.get('practice_id') == practice_id:
                    report = task.get('overall_report') or {}
                    versions.append({
                        'task_id': task.get('task_id', filename.replace('.json', '')),
                        'prompt_version': task.get('prompt_version', 1),
                        'created_at': task.get('created_at', ''),
                        'accuracy': report.get('accuracy', 0),
                        'total_questions': report.get('total_questions', 0)
                    })
            except:
                continue
        
        versions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return versions
    
    @staticmethod
    def compare_practices(
        practice_id_1: str,
        practice_id_2: str
    ) -> Dict[str, Any]:
        """
        对比两个最佳实践的效果 (US-16.5)
        """
        p1 = BestPracticeService.get_practice(practice_id_1)
        p2 = BestPracticeService.get_practice(practice_id_2)
        
        if not p1 or not p2:
            return {'success': False, 'error': '实践不存在'}
        
        # 获取各自的使用记录
        v1 = BestPracticeService.get_prompt_versions(practice_id_1)
        v2 = BestPracticeService.get_prompt_versions(practice_id_2)
        
        # 计算平均准确率
        avg1 = sum(v.get('accuracy', 0) for v in v1) / len(v1) if v1 else 0
        avg2 = sum(v.get('accuracy', 0) for v in v2) / len(v2) if v2 else 0
        
        return {
            'success': True,
            'practice1': {
                'id': practice_id_1,
                'name': p1.get('name'),
                'usage_count': len(v1),
                'avg_accuracy': round(avg1 * 100, 2),
                'metrics': p1.get('metrics', {})
            },
            'practice2': {
                'id': practice_id_2,
                'name': p2.get('name'),
                'usage_count': len(v2),
                'avg_accuracy': round(avg2 * 100, 2),
                'metrics': p2.get('metrics', {})
            },
            'winner': practice_id_1 if avg1 > avg2 else practice_id_2 if avg2 > avg1 else 'tie'
        }
    
    @staticmethod
    def get_categories() -> List[str]:
        """获取所有分类"""
        practices = BestPracticeService._load_practices()
        categories = set(p.get('category', '未分类') for p in practices)
        return sorted(list(categories))
    
    @staticmethod
    def get_tags() -> List[str]:
        """获取所有标签"""
        practices = BestPracticeService._load_practices()
        tags = set()
        for p in practices:
            tags.update(p.get('tags', []))
        return sorted(list(tags))
    
    @staticmethod
    def import_from_task(task_id: str, name: str = None) -> Dict[str, Any]:
        """
        从任务导入为最佳实践
        """
        batch_dir = StorageService.BATCH_TASKS_DIR
        filepath = os.path.join(batch_dir, f'{task_id}.json')
        
        if not os.path.exists(filepath):
            return {'success': False, 'error': '任务不存在'}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                task = json.load(f)
            
            prompt_content = task.get('prompt') or task.get('system_prompt', '')
            report = task.get('overall_report') or {}
            
            return BestPracticeService.add_practice(
                name=name or f"从任务 {task_id} 导入",
                category=task.get('subject_name', '通用'),
                prompt_content=prompt_content,
                description=f"从批量任务 {task_id} 导入，准确率 {report.get('accuracy', 0)*100:.1f}%",
                tags=['imported'],
                metrics={
                    'source_task': task_id,
                    'accuracy': report.get('accuracy', 0),
                    'total_questions': report.get('total_questions', 0)
                }
            )
        except Exception as e:
            return {'success': False, 'error': str(e)}
