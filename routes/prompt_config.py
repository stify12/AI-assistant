"""
提示词配置管理路由
提供提示词同步、版本管理、变更检测等功能
"""
from flask import Blueprint, request, jsonify
from services.prompt_config_service import PromptConfigService, SUBJECT_PROMPT_CONFIGS

prompt_config_bp = Blueprint('prompt_config', __name__)


@prompt_config_bp.route('/api/prompt-config/subjects', methods=['GET'])
def get_subject_prompt_mapping():
    """获取学科提示词配置映射"""
    result = {}
    for subject_id, config in SUBJECT_PROMPT_CONFIGS.items():
        result[subject_id] = {
            'name': config['name'],
            'prompts': config['prompts']
        }
    return jsonify({'success': True, 'data': result})


@prompt_config_bp.route('/api/prompt-config/list', methods=['GET'])
def list_prompt_configs():
    """获取所有本地存储的提示词配置"""
    configs = PromptConfigService.get_all_prompt_configs()
    
    # 按学科分组
    grouped = {}
    for config in configs:
        subject_id = config.get('subject_id')
        if subject_id not in grouped:
            grouped[subject_id] = {
                'subject_id': subject_id,
                'subject_name': config.get('subject_name', '未知'),
                'prompts': []
            }
        
        # 格式化时间
        synced_at = config.get('synced_at')
        if synced_at:
            synced_at = synced_at.strftime('%Y-%m-%d %H:%M:%S')
        
        grouped[subject_id]['prompts'].append({
            'config_key': config['config_key'],
            'description': config.get('description', ''),
            'current_version': config.get('current_version', 1),
            'content_hash': config.get('content_hash', ''),
            'config_preview': config.get('config_preview', ''),
            'synced_at': synced_at
        })
    
    return jsonify({
        'success': True,
        'data': list(grouped.values())
    })


@prompt_config_bp.route('/api/prompt-config/sync', methods=['POST'])
def sync_prompts():
    """同步提示词配置"""
    data = request.get_json() or {}
    subject_id = data.get('subject_id')
    
    if subject_id is not None:
        # 同步指定学科
        result = PromptConfigService.sync_subject_prompts(int(subject_id))
    else:
        # 同步所有学科
        result = PromptConfigService.sync_all_prompts()
    
    return jsonify(result)


@prompt_config_bp.route('/api/prompt-config/check', methods=['POST'])
def check_prompt_changes():
    """检查提示词是否有变更（不自动保存版本）"""
    data = request.get_json() or {}
    subject_id = data.get('subject_id')
    
    subject_config = SUBJECT_PROMPT_CONFIGS.get(subject_id)
    if not subject_config:
        return jsonify({'success': False, 'error': f'未知学科ID: {subject_id}'})
    
    results = []
    for prompt_info in subject_config['prompts']:
        config_key = prompt_info['key']
        
        # 获取远程配置
        remote = PromptConfigService.get_remote_prompt(config_key)
        if not remote:
            results.append({
                'config_key': config_key,
                'prompt_type': prompt_info['type'],
                'prompt_desc': prompt_info['desc'],
                'status': 'not_found',
                'message': '远程配置不存在'
            })
            continue
        
        remote_hash = PromptConfigService.get_content_hash(remote['config_value'])
        
        # 获取本地配置
        local = PromptConfigService.get_local_prompt(config_key)
        
        if not local:
            results.append({
                'config_key': config_key,
                'prompt_type': prompt_info['type'],
                'prompt_desc': prompt_info['desc'],
                'status': 'new',
                'message': '本地无记录，需要首次同步',
                'remote_preview': (remote['config_value'] or '')[:200]
            })
            continue
        
        local_hash = local.get('content_hash', '')
        
        if remote_hash == local_hash:
            results.append({
                'config_key': config_key,
                'prompt_type': prompt_info['type'],
                'prompt_desc': prompt_info['desc'],
                'status': 'unchanged',
                'current_version': local['current_version'],
                'message': '无变更'
            })
        else:
            # 生成变更摘要
            change_summary = PromptConfigService.generate_change_summary(
                local.get('config_value', ''),
                remote['config_value']
            )
            results.append({
                'config_key': config_key,
                'prompt_type': prompt_info['type'],
                'prompt_desc': prompt_info['desc'],
                'status': 'changed',
                'current_version': local['current_version'],
                'change_summary': change_summary,
                'message': '检测到变更'
            })
    
    has_changes = any(r['status'] in ('new', 'changed') for r in results)
    
    return jsonify({
        'success': True,
        'subject_id': subject_id,
        'subject_name': subject_config['name'],
        'has_changes': has_changes,
        'prompts': results
    })


@prompt_config_bp.route('/api/prompt-config/<config_key>', methods=['GET'])
def get_prompt_detail(config_key):
    """获取单个提示词的详细信息"""
    local = PromptConfigService.get_local_prompt(config_key)
    remote = PromptConfigService.get_remote_prompt(config_key)
    
    if not local and not remote:
        return jsonify({'success': False, 'error': '配置不存在'})
    
    result = {
        'config_key': config_key,
        'local': None,
        'remote': None,
        'has_change': False
    }
    
    if local:
        synced_at = local.get('synced_at')
        if synced_at:
            synced_at = synced_at.strftime('%Y-%m-%d %H:%M:%S')
        
        result['local'] = {
            'config_value': local.get('config_value', ''),
            'content_hash': local.get('content_hash', ''),
            'current_version': local.get('current_version', 1),
            'description': local.get('description', ''),
            'subject_id': local.get('subject_id'),
            'subject_name': local.get('subject_name'),
            'synced_at': synced_at
        }
    
    if remote:
        remote_hash = PromptConfigService.get_content_hash(remote['config_value'])
        result['remote'] = {
            'config_value': remote.get('config_value', ''),
            'content_hash': remote_hash,
            'description': remote.get('description', '')
        }
        
        if local:
            result['has_change'] = local.get('content_hash', '') != remote_hash
    
    return jsonify({'success': True, 'data': result})


@prompt_config_bp.route('/api/prompt-config/<config_key>/versions', methods=['GET'])
def get_prompt_versions(config_key):
    """获取提示词的版本历史"""
    limit = request.args.get('limit', 10, type=int)
    versions = PromptConfigService.get_prompt_versions(config_key, limit)
    
    # 格式化时间
    for v in versions:
        if v.get('created_at'):
            v['created_at'] = v['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({'success': True, 'data': versions})


@prompt_config_bp.route('/api/prompt-config/<config_key>/versions/<int:version>', methods=['GET'])
def get_prompt_version_detail(config_key, version):
    """获取指定版本的完整内容"""
    detail = PromptConfigService.get_prompt_version_detail(config_key, version)
    
    if not detail:
        return jsonify({'success': False, 'error': '版本不存在'})
    
    if detail.get('created_at'):
        detail['created_at'] = detail['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({'success': True, 'data': detail})


@prompt_config_bp.route('/api/prompt-config/<config_key>/compare', methods=['GET'])
def compare_versions(config_key):
    """比较两个版本的差异"""
    v1 = request.args.get('v1', type=int)
    v2 = request.args.get('v2', type=int)
    
    if not v1 or not v2:
        return jsonify({'success': False, 'error': '请指定两个版本号'})
    
    result = PromptConfigService.compare_versions(config_key, v1, v2)
    
    if 'error' in result:
        return jsonify({'success': False, 'error': result['error']})
    
    return jsonify({'success': True, 'data': result})


@prompt_config_bp.route('/api/prompt-config/task-versions/<int:subject_id>', methods=['GET'])
def get_task_prompt_versions(subject_id):
    """获取指定学科当前的提示词版本信息（用于任务创建时记录）"""
    versions = PromptConfigService.get_current_prompt_versions_for_subject(subject_id)
    return jsonify({'success': True, 'data': versions})


@prompt_config_bp.route('/api/prompt-config/check-all', methods=['POST'])
def check_all_prompt_changes():
    """一键检测所有学科的提示词变更（不自动保存版本）"""
    all_results = {}
    total_changes = 0
    
    for subject_id, subject_config in SUBJECT_PROMPT_CONFIGS.items():
        results = []
        for prompt_info in subject_config['prompts']:
            config_key = prompt_info['key']
            
            # 获取远程配置
            remote = PromptConfigService.get_remote_prompt(config_key)
            if not remote:
                results.append({
                    'config_key': config_key,
                    'prompt_type': prompt_info['type'],
                    'prompt_desc': prompt_info['desc'],
                    'status': 'not_found',
                    'message': '远程配置不存在'
                })
                continue
            
            remote_hash = PromptConfigService.get_content_hash(remote['config_value'])
            
            # 获取本地配置
            local = PromptConfigService.get_local_prompt(config_key)
            
            if not local:
                results.append({
                    'config_key': config_key,
                    'prompt_type': prompt_info['type'],
                    'prompt_desc': prompt_info['desc'],
                    'status': 'new',
                    'message': '本地无记录，需要首次同步'
                })
                total_changes += 1
                continue
            
            local_hash = local.get('content_hash', '')
            
            if remote_hash == local_hash:
                results.append({
                    'config_key': config_key,
                    'prompt_type': prompt_info['type'],
                    'prompt_desc': prompt_info['desc'],
                    'status': 'unchanged',
                    'current_version': local['current_version'],
                    'message': '无变更'
                })
            else:
                # 生成变更摘要
                change_summary = PromptConfigService.generate_change_summary(
                    local.get('config_value', ''),
                    remote['config_value']
                )
                results.append({
                    'config_key': config_key,
                    'prompt_type': prompt_info['type'],
                    'prompt_desc': prompt_info['desc'],
                    'status': 'changed',
                    'current_version': local['current_version'],
                    'change_summary': change_summary,
                    'message': '检测到变更'
                })
                total_changes += 1
        
        has_changes = any(r['status'] in ('new', 'changed') for r in results)
        all_results[subject_id] = {
            'subject_id': subject_id,
            'subject_name': subject_config['name'],
            'has_changes': has_changes,
            'prompts': results
        }
    
    return jsonify({
        'success': True,
        'total_changes': total_changes,
        'subjects': all_results
    })
