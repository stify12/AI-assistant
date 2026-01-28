"""
提示词配置服务
从 zpsmart.zp_config 同步提示词配置，并管理版本历史
"""
import hashlib
import json
import difflib
from datetime import datetime
from .database_service import DatabaseService, AppDatabaseService


# 学科提示词配置映射
SUBJECT_PROMPT_CONFIGS = {
    # 语文 (subject_id=1)
    1: {
        'name': '语文',
        'prompts': [
            {'key': 'ChineseHomeWorkRecognition', 'type': '识别', 'desc': '语文题目识别提示词'},
            {'key': 'ChineseHomeWorkCorrect', 'type': '批改', 'desc': '语文题目批改提示词'},
            {'key': 'ChineseComposition', 'type': '作文识别', 'desc': '语文作文内容识别'},
            {'key': 'ChineseCompositionGrading', 'type': '作文批改', 'desc': '语文作文批改提示词'},
        ]
    },
    # 英语 (subject_id=0)
    0: {
        'name': '英语',
        'prompts': [
            {'key': 'EnglishHomeWorkPrompt', 'type': '识别', 'desc': '英语提取答案提示词'},
            {'key': 'EnglishHomeWorkPrompt_subjective', 'type': '主观题', 'desc': '英语作业主观题批改提示词'},
            {'key': 'EnglishCompositionPrompt', 'type': '作文', 'desc': '英语作业作文题批改提示词'},
        ]
    },
    # 物理 (subject_id=3)
    3: {
        'name': '物理',
        'prompts': [
            {'key': 'PhysicsHomeWorkPrompt2', 'type': '批改', 'desc': '物理题目批改提示词'},
            {'key': 'PhysicsHomeWorkPrompt', 'type': '批改(旧)', 'desc': '物理题目批改提示词(旧版)'},
        ]
    },
    # 化学 (subject_id=4)
    4: {
        'name': '化学',
        'prompts': [
            {'key': 'ChemistryHomeWorkPrompt', 'type': '识别', 'desc': '化学题目识别提示词'},
            {'key': 'ChemistryHomeWorkPromptSubjective', 'type': '主观题', 'desc': '化学主观题批改提示词'},
        ]
    },
    # 生物 (subject_id=5)
    5: {
        'name': '生物',
        'prompts': [
            {'key': 'BiologyHomeWorkPrompt', 'type': '批改', 'desc': '生物作业批改提示词'},
        ]
    },
    # 地理 (subject_id=6)
    6: {
        'name': '地理',
        'prompts': [
            {'key': 'GeographyHomeWorkRecognition', 'type': '识别', 'desc': '地理题目识别提示词'},
            {'key': 'GeographyHomeWorkCorrect', 'type': '批改', 'desc': '地理题目批改提示词'},
        ]
    },
    # 数学 (subject_id=2)
    2: {
        'name': '数学',
        'prompts': [
            {'key': 'HomeWorkPrompt', 'type': '批改', 'desc': '数学作业批改提示词'},
        ]
    },
}


class PromptConfigService:
    """提示词配置服务"""
    
    @staticmethod
    def get_content_hash(content):
        """计算内容的MD5哈希"""
        if not content:
            return ''
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def get_remote_prompt(config_key):
        """从 zpsmart.zp_config 获取提示词配置"""
        try:
            sql = "SELECT config_key, config_value, description FROM zp_config WHERE config_key = %s"
            row = DatabaseService.execute_one(sql, (config_key,))
            if row:
                return {
                    'config_key': row['config_key'],
                    'config_value': row['config_value'] or '',
                    'description': row['description'] or ''
                }
            return None
        except Exception as e:
            print(f"获取远程提示词失败 [{config_key}]: {e}")
            return None
    
    @staticmethod
    def get_remote_prompts_batch(config_keys):
        """批量从 zpsmart.zp_config 获取提示词配置（性能优化）"""
        if not config_keys:
            return {}
        try:
            placeholders = ','.join(['%s'] * len(config_keys))
            sql = f"SELECT config_key, config_value, description FROM zp_config WHERE config_key IN ({placeholders})"
            rows = DatabaseService.execute_query(sql, tuple(config_keys))
            return {
                row['config_key']: {
                    'config_key': row['config_key'],
                    'config_value': row['config_value'] or '',
                    'description': row['description'] or ''
                }
                for row in rows
            }
        except Exception as e:
            print(f"批量获取远程提示词失败: {e}")
            return {}
    
    @staticmethod
    def get_local_prompt(config_key):
        """获取本地存储的提示词配置"""
        try:
            sql = "SELECT * FROM prompt_configs WHERE config_key = %s"
            return AppDatabaseService.execute_one(sql, (config_key,))
        except Exception as e:
            print(f"获取本地提示词失败 [{config_key}]: {e}")
            return None
    
    @staticmethod
    def get_local_prompts_batch(config_keys):
        """批量获取本地存储的提示词配置（性能优化）"""
        if not config_keys:
            return {}
        try:
            placeholders = ','.join(['%s'] * len(config_keys))
            sql = f"SELECT * FROM prompt_configs WHERE config_key IN ({placeholders})"
            rows = AppDatabaseService.execute_query(sql, tuple(config_keys))
            return {row['config_key']: row for row in rows}
        except Exception as e:
            print(f"批量获取本地提示词失败: {e}")
            return {}
    
    @staticmethod
    def save_local_prompt(config_key, config_value, description=None, subject_id=None, subject_name=None):
        """保存提示词到本地"""
        content_hash = PromptConfigService.get_content_hash(config_value)
        now = datetime.now()
        
        existing = PromptConfigService.get_local_prompt(config_key)
        
        if existing:
            # 更新
            sql = """UPDATE prompt_configs 
                     SET config_value = %s, content_hash = %s, description = %s,
                         subject_id = %s, subject_name = %s, synced_at = %s, updated_at = %s
                     WHERE config_key = %s"""
            AppDatabaseService.execute_update(sql, (
                config_value, content_hash, description,
                subject_id, subject_name, now, now, config_key
            ))
            return existing['id']
        else:
            # 新增
            sql = """INSERT INTO prompt_configs 
                     (config_key, config_value, content_hash, description, 
                      subject_id, subject_name, current_version, synced_at, created_at, updated_at)
                     VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s, %s)"""
            return AppDatabaseService.execute_insert(sql, (
                config_key, config_value, content_hash, description,
                subject_id, subject_name, now, now, now
            ))
    
    @staticmethod
    def save_version(config_key, config_value, version, change_summary=None):
        """保存提示词版本"""
        content_hash = PromptConfigService.get_content_hash(config_value)
        sql = """INSERT INTO prompt_config_versions 
                 (config_key, version, config_value, content_hash, change_summary, created_at)
                 VALUES (%s, %s, %s, %s, %s, %s)
                 ON DUPLICATE KEY UPDATE 
                 config_value = VALUES(config_value),
                 content_hash = VALUES(content_hash),
                 change_summary = VALUES(change_summary)"""
        return AppDatabaseService.execute_insert(sql, (
            config_key, version, config_value, content_hash, change_summary, datetime.now()
        ))
    
    @staticmethod
    def increment_version(config_key):
        """增加版本号"""
        sql = "UPDATE prompt_configs SET current_version = current_version + 1 WHERE config_key = %s"
        AppDatabaseService.execute_update(sql, (config_key,))
        
        # 返回新版本号
        local = PromptConfigService.get_local_prompt(config_key)
        return local['current_version'] if local else 1
    
    @staticmethod
    def generate_change_summary(old_content, new_content):
        """生成变更摘要"""
        if not old_content:
            return "初始版本"
        if not new_content:
            return "内容被清空"
        
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
        
        added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        
        if added == 0 and removed == 0:
            return "无实质变更"
        
        parts = []
        if added > 0:
            parts.append(f"新增 {added} 行")
        if removed > 0:
            parts.append(f"删除 {removed} 行")
        
        return "，".join(parts)
    
    @staticmethod
    def check_and_sync_prompt(config_key, subject_id=None, subject_name=None):
        """
        检查并同步单个提示词
        返回: {
            'config_key': str,
            'has_change': bool,
            'old_version': int,
            'new_version': int,
            'change_summary': str,
            'remote_value': str,
            'local_value': str
        }
        """
        # 获取远程配置
        remote = PromptConfigService.get_remote_prompt(config_key)
        if not remote:
            return {
                'config_key': config_key,
                'has_change': False,
                'error': '远程配置不存在'
            }
        
        remote_value = remote['config_value']
        remote_hash = PromptConfigService.get_content_hash(remote_value)
        
        # 获取本地配置
        local = PromptConfigService.get_local_prompt(config_key)
        
        if not local:
            # 本地不存在，首次同步
            PromptConfigService.save_local_prompt(
                config_key, remote_value, remote['description'],
                subject_id, subject_name
            )
            PromptConfigService.save_version(config_key, remote_value, 1, "初始版本")
            
            return {
                'config_key': config_key,
                'has_change': True,
                'is_new': True,
                'old_version': 0,
                'new_version': 1,
                'change_summary': '初始同步',
                'description': remote['description']
            }
        
        local_hash = local.get('content_hash', '')
        local_value = local.get('config_value', '')
        
        if remote_hash == local_hash:
            # 无变化
            return {
                'config_key': config_key,
                'has_change': False,
                'current_version': local['current_version'],
                'description': local.get('description') or remote['description']
            }
        
        # 有变化，生成变更摘要
        change_summary = PromptConfigService.generate_change_summary(local_value, remote_value)
        old_version = local['current_version']
        
        # 保存旧版本（如果还没保存过）
        PromptConfigService.save_version(config_key, local_value, old_version, "变更前版本")
        
        # 更新本地配置
        PromptConfigService.save_local_prompt(
            config_key, remote_value, remote['description'],
            subject_id, subject_name
        )
        
        # 增加版本号
        new_version = PromptConfigService.increment_version(config_key)
        
        # 保存新版本
        PromptConfigService.save_version(config_key, remote_value, new_version, change_summary)
        
        return {
            'config_key': config_key,
            'has_change': True,
            'is_new': False,
            'old_version': old_version,
            'new_version': new_version,
            'change_summary': change_summary,
            'description': remote['description']
        }
    
    @staticmethod
    def sync_subject_prompts(subject_id):
        """同步指定学科的所有提示词（批量查询优化）"""
        subject_config = SUBJECT_PROMPT_CONFIGS.get(subject_id)
        if not subject_config:
            return {'success': False, 'error': f'未知学科ID: {subject_id}'}
        
        # 收集所有需要查询的 config_key
        config_keys = [p['key'] for p in subject_config['prompts']]
        
        # 批量查询远程和本地配置（2次查询代替 N*2 次）
        remote_configs = PromptConfigService.get_remote_prompts_batch(config_keys)
        local_configs = PromptConfigService.get_local_prompts_batch(config_keys)
        
        results = []
        for prompt_info in subject_config['prompts']:
            config_key = prompt_info['key']
            remote = remote_configs.get(config_key)
            local = local_configs.get(config_key)
            
            # 使用批量查询结果进行同步
            result = PromptConfigService._sync_single_prompt(
                config_key, remote, local,
                subject_id, subject_config['name']
            )
            result['prompt_type'] = prompt_info['type']
            result['prompt_desc'] = prompt_info['desc']
            results.append(result)
        
        has_changes = any(r.get('has_change') for r in results)
        
        return {
            'success': True,
            'subject_id': subject_id,
            'subject_name': subject_config['name'],
            'has_changes': has_changes,
            'prompts': results
        }
    
    @staticmethod
    def _sync_single_prompt(config_key, remote, local, subject_id, subject_name):
        """同步单个提示词（内部方法，使用预查询的数据）"""
        if not remote:
            return {
                'config_key': config_key,
                'has_change': False,
                'error': '远程配置不存在'
            }
        
        remote_value = remote['config_value']
        remote_hash = PromptConfigService.get_content_hash(remote_value)
        
        if not local:
            # 本地不存在，首次同步
            PromptConfigService.save_local_prompt(
                config_key, remote_value, remote['description'],
                subject_id, subject_name
            )
            PromptConfigService.save_version(config_key, remote_value, 1, "初始版本")
            
            return {
                'config_key': config_key,
                'has_change': True,
                'is_new': True,
                'old_version': 0,
                'new_version': 1,
                'change_summary': '初始同步',
                'description': remote['description']
            }
        
        local_hash = local.get('content_hash', '')
        local_value = local.get('config_value', '')
        
        if remote_hash == local_hash:
            # 无变化
            return {
                'config_key': config_key,
                'has_change': False,
                'current_version': local['current_version'],
                'description': local.get('description') or remote['description']
            }
        
        # 有变化，生成变更摘要
        change_summary = PromptConfigService.generate_change_summary(local_value, remote_value)
        old_version = local['current_version']
        
        # 保存旧版本
        PromptConfigService.save_version(config_key, local_value, old_version, "变更前版本")
        
        # 更新本地配置
        PromptConfigService.save_local_prompt(
            config_key, remote_value, remote['description'],
            subject_id, subject_name
        )
        
        # 增加版本号
        new_version = PromptConfigService.increment_version(config_key)
        
        # 保存新版本
        PromptConfigService.save_version(config_key, remote_value, new_version, change_summary)
        
        return {
            'config_key': config_key,
            'has_change': True,
            'is_new': False,
            'old_version': old_version,
            'new_version': new_version,
            'change_summary': change_summary,
            'description': remote['description']
        }
    
    @staticmethod
    def sync_all_prompts():
        """同步所有学科的提示词（批量查询优化）"""
        # 收集所有需要查询的 config_key
        all_config_keys = []
        for subject_config in SUBJECT_PROMPT_CONFIGS.values():
            all_config_keys.extend([p['key'] for p in subject_config['prompts']])
        
        # 批量查询远程和本地配置（2次查询代替 N*2 次）
        remote_configs = PromptConfigService.get_remote_prompts_batch(all_config_keys)
        local_configs = PromptConfigService.get_local_prompts_batch(all_config_keys)
        
        all_results = {}
        total_changes = 0
        
        for subject_id, subject_config in SUBJECT_PROMPT_CONFIGS.items():
            results = []
            for prompt_info in subject_config['prompts']:
                config_key = prompt_info['key']
                remote = remote_configs.get(config_key)
                local = local_configs.get(config_key)
                
                result = PromptConfigService._sync_single_prompt(
                    config_key, remote, local,
                    subject_id, subject_config['name']
                )
                result['prompt_type'] = prompt_info['type']
                result['prompt_desc'] = prompt_info['desc']
                results.append(result)
                
                if result.get('has_change'):
                    total_changes += 1
            
            has_changes = any(r.get('has_change') for r in results)
            all_results[subject_id] = {
                'success': True,
                'subject_id': subject_id,
                'subject_name': subject_config['name'],
                'has_changes': has_changes,
                'prompts': results
            }
        
        return {
            'success': True,
            'total_changes': total_changes,
            'subjects': all_results
        }
    
    @staticmethod
    def get_all_prompt_configs():
        """获取所有本地存储的提示词配置"""
        try:
            sql = """SELECT config_key, subject_id, subject_name, description, 
                            current_version, content_hash, synced_at, 
                            LEFT(config_value, 200) as config_preview
                     FROM prompt_configs 
                     ORDER BY subject_id, config_key"""
            return AppDatabaseService.execute_query(sql)
        except Exception as e:
            print(f"获取提示词配置列表失败: {e}")
            return []
    
    @staticmethod
    def get_prompt_versions(config_key, limit=10):
        """获取提示词的版本历史"""
        try:
            sql = """SELECT version, content_hash, change_summary, created_at,
                            LEFT(config_value, 500) as config_preview
                     FROM prompt_config_versions 
                     WHERE config_key = %s 
                     ORDER BY version DESC 
                     LIMIT %s"""
            return AppDatabaseService.execute_query(sql, (config_key, limit))
        except Exception as e:
            print(f"获取版本历史失败 [{config_key}]: {e}")
            return []
    
    @staticmethod
    def get_prompt_version_detail(config_key, version):
        """获取指定版本的完整内容"""
        try:
            sql = """SELECT * FROM prompt_config_versions 
                     WHERE config_key = %s AND version = %s"""
            return AppDatabaseService.execute_one(sql, (config_key, version))
        except Exception as e:
            print(f"获取版本详情失败 [{config_key} v{version}]: {e}")
            return None
    
    @staticmethod
    def get_current_prompt_versions_for_subject(subject_id):
        """获取指定学科当前使用的提示词版本信息（用于任务创建时记录）"""
        subject_config = SUBJECT_PROMPT_CONFIGS.get(subject_id)
        if not subject_config:
            return {}
        
        versions = {}
        for prompt_info in subject_config['prompts']:
            local = PromptConfigService.get_local_prompt(prompt_info['key'])
            if local:
                versions[prompt_info['key']] = {
                    'version': local['current_version'],
                    'content_hash': local['content_hash'],
                    'synced_at': local['synced_at'].isoformat() if local.get('synced_at') else None
                }
        
        return versions
    
    @staticmethod
    def compare_versions(config_key, version1, version2):
        """比较两个版本的差异"""
        v1 = PromptConfigService.get_prompt_version_detail(config_key, version1)
        v2 = PromptConfigService.get_prompt_version_detail(config_key, version2)
        
        if not v1 or not v2:
            return {'error': '版本不存在'}
        
        v1_lines = (v1['config_value'] or '').splitlines()
        v2_lines = (v2['config_value'] or '').splitlines()
        
        diff = list(difflib.unified_diff(
            v1_lines, v2_lines,
            fromfile=f'v{version1}',
            tofile=f'v{version2}',
            lineterm=''
        ))
        
        return {
            'config_key': config_key,
            'version1': version1,
            'version2': version2,
            'diff': diff,
            'v1_hash': v1['content_hash'],
            'v2_hash': v2['content_hash']
        }
