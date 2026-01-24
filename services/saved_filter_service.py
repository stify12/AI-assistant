"""
保存常用筛选服务 (US-24)
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any

from .storage_service import StorageService


class SavedFilterService:
    """保存筛选条件服务"""
    
    FILTERS_DIR = 'saved_filters'
    FILTERS_FILE = 'filters.json'
    
    @staticmethod
    def _get_filepath() -> str:
        """获取存储文件路径"""
        StorageService.ensure_dir(SavedFilterService.FILTERS_DIR)
        return os.path.join(SavedFilterService.FILTERS_DIR, SavedFilterService.FILTERS_FILE)
    
    @staticmethod
    def _load_filters() -> List[Dict]:
        filepath = SavedFilterService._get_filepath()
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    @staticmethod
    def _save_filters(filters: List[Dict]):
        filepath = SavedFilterService._get_filepath()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(filters, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def save_filter(
        name: str,
        filter_type: str,
        conditions: Dict,
        is_default: bool = False
    ) -> Dict[str, Any]:
        """保存筛选条件"""
        filters = SavedFilterService._load_filters()
        
        filter_id = f"filter_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 如果设为默认，取消其他默认
        if is_default:
            for f in filters:
                if f.get('filter_type') == filter_type:
                    f['is_default'] = False
        
        new_filter = {
            'id': filter_id,
            'name': name,
            'filter_type': filter_type,
            'conditions': conditions,
            'is_default': is_default,
            'usage_count': 0,
            'created_at': datetime.now().isoformat()
        }
        
        filters.append(new_filter)
        SavedFilterService._save_filters(filters)
        
        return {'success': True, 'filter': new_filter}
    
    @staticmethod
    def get_filters(filter_type: str = None) -> List[Dict]:
        """获取保存的筛选条件"""
        filters = SavedFilterService._load_filters()
        
        if filter_type:
            filters = [f for f in filters if f.get('filter_type') == filter_type]
        
        # 按使用次数排序
        filters.sort(key=lambda x: (x.get('is_default', False), x.get('usage_count', 0)), reverse=True)
        
        return filters
    
    @staticmethod
    def get_default_filter(filter_type: str) -> Dict:
        """获取默认筛选条件"""
        filters = SavedFilterService._load_filters()
        
        for f in filters:
            if f.get('filter_type') == filter_type and f.get('is_default'):
                return f
        
        return None
    
    @staticmethod
    def use_filter(filter_id: str) -> Dict[str, Any]:
        """使用筛选条件（增加使用次数）"""
        filters = SavedFilterService._load_filters()
        
        for f in filters:
            if f.get('id') == filter_id:
                f['usage_count'] = f.get('usage_count', 0) + 1
                f['last_used_at'] = datetime.now().isoformat()
                SavedFilterService._save_filters(filters)
                return {'success': True, 'filter': f}
        
        return {'success': False, 'error': '筛选条件不存在'}
    
    @staticmethod
    def delete_filter(filter_id: str) -> Dict[str, Any]:
        """删除筛选条件"""
        filters = SavedFilterService._load_filters()
        
        for i, f in enumerate(filters):
            if f.get('id') == filter_id:
                filters.pop(i)
                SavedFilterService._save_filters(filters)
                return {'success': True}
        
        return {'success': False, 'error': '筛选条件不存在'}
    
    @staticmethod
    def update_filter(filter_id: str, updates: Dict) -> Dict[str, Any]:
        """更新筛选条件"""
        filters = SavedFilterService._load_filters()
        
        for i, f in enumerate(filters):
            if f.get('id') == filter_id:
                f.update(updates)
                filters[i] = f
                SavedFilterService._save_filters(filters)
                return {'success': True, 'filter': f}
        
        return {'success': False, 'error': '筛选条件不存在'}
