"""
模型推荐路由模块
提供智能模型推荐、多模型对比和统计功能
"""
import os
import json
import uuid
import time
import requests
import concurrent.futures
from datetime import datetime
from flask import Blueprint, request, jsonify

from services.config_service import ConfigService
from services.storage_service import StorageService

model_recommend_bp = Blueprint('model_recommend', __name__)

MODEL_STATS_FILE = 'model_stats.json'


def load_model_stats():
    """加载模型统计数据"""
    if os.path.exists(MODEL_STATS_FILE):
        with open(MODEL_STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_model_stats(stats):
    """保存模型统计数据"""
    with open(MODEL_STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def update_model_stats(model_id, accuracy=None, time_cost=None, consistency=None, success=True):
    """更新模型统计数据"""
    stats = load_model_stats()
    
    if model_id not in stats:
        stats[model_id] = {
            'total_tests': 0,
            'success_count': 0,
            'accuracy_sum': 0,
            'accuracy_count': 0,
            'time_sum': 0,
            'time_count': 0,
            'consistency_sum': 0,
            'consistency_count': 0,
            'last_updated': None
        }
    
    s = stats[model_id]
    s['total_tests'] += 1
    if success:
        s['success_count'] += 1
    if accuracy is not None:
        s['accuracy_sum'] += accuracy
        s['accuracy_count'] += 1
    if time_cost is not None:
        s['time_sum'] += time_cost
        s['time_count'] += 1
    if consistency is not None:
        s['consistency_sum'] += consistency
        s['consistency_count'] += 1
    s['last_updated'] = datetime.now().isoformat()
    
    save_model_stats(stats)
    return stats


def get_model_performance():
    """获取所有模型的性能数据"""
    stats = load_model_stats()
    
    model_info = {
        'doubao-1-5-vision-pro-32k-250115': {'name': 'Vision Pro 1.5', 'base_cost': 80},
        'doubao-seed-1-6-vision-250815': {'name': 'Seed Vision 1.6', 'base_cost': 60},
        'doubao-seed-1-6-251015': {'name': 'Seed 1.6', 'base_cost': 65},
        'doubao-seed-1-6-thinking-250715': {'name': 'Seed Thinking', 'base_cost': 40},
        'qwen-vl-plus': {'name': 'Qwen VL', 'base_cost': 70}
    }
    
    performance = {}
    for model_id, info in model_info.items():
        s = stats.get(model_id, {})
        
        avg_accuracy = round(s['accuracy_sum'] / s['accuracy_count'], 1) if s.get('accuracy_count', 0) > 0 else None
        avg_time = round(s['time_sum'] / s['time_count'], 2) if s.get('time_count', 0) > 0 else None
        avg_consistency = round(s['consistency_sum'] / s['consistency_count'], 1) if s.get('consistency_count', 0) > 0 else None
        success_rate = round(s['success_count'] / s['total_tests'] * 100, 1) if s.get('total_tests', 0) > 0 else None
        
        speed_score = max(0, min(100, 100 - avg_time * 5)) if avg_time is not None else None
        
        performance[model_id] = {
            'name': info['name'],
            'total_tests': s.get('total_tests', 0),
            'success_rate': success_rate,
            'avg_accuracy': avg_accuracy,
            'avg_time': avg_time,
            'avg_consistency': avg_consistency,
            'speed_score': round(speed_score, 1) if speed_score else None,
            'cost_score': info['base_cost'],
            'last_updated': s.get('last_updated'),
            'has_data': s.get('total_tests', 0) > 0
        }
    
    return performance


@model_recommend_bp.route('/api/recommend', methods=['POST'])
def recommend_model_api():
    """基于历史数据的智能模型推荐"""
    config = ConfigService.load_config()
    data = request.json
    scenario = data.get('scenario', 'balanced')
    subject = data.get('subject', '')
    
    performance = get_model_performance()
    
    default_profiles = {
        'doubao-1-5-vision-pro-32k-250115': {
            'accuracy': 85, 'speed': 95, 'cost': 80,
            'strengths': ['速度最快', '成本低', '稳定性好'],
            'weaknesses': ['复杂题型准确率一般'],
            'best_for': ['客观题', '简单识别', '大批量处理']
        },
        'doubao-seed-1-6-vision-250815': {
            'accuracy': 92, 'speed': 75, 'cost': 60,
            'strengths': ['视觉识别准确率高', '复杂题型表现好'],
            'weaknesses': ['速度较慢', '成本较高'],
            'best_for': ['计算题', '主观题', '复杂识别']
        },
        'doubao-seed-1-6-251015': {
            'accuracy': 90, 'speed': 80, 'cost': 65,
            'strengths': ['综合能力强', '推理能力好'],
            'weaknesses': ['非视觉专用'],
            'best_for': ['综合分析', '推理题']
        },
        'doubao-seed-1-6-thinking-250715': {
            'accuracy': 95, 'speed': 50, 'cost': 40,
            'strengths': ['深度思考', '复杂推理最强', '准确率最高'],
            'weaknesses': ['速度最慢', '成本最高'],
            'best_for': ['复杂计算', '多步推理', '难题']
        },
        'qwen-vl-plus': {
            'accuracy': 88, 'speed': 85, 'cost': 70,
            'strengths': ['中文理解好', '性价比高', '多模态融合'],
            'weaknesses': ['部分格式支持不完善'],
            'best_for': ['语文', '英语', '文字识别']
        }
    }
    
    def calc_score(accuracy, speed, cost, scenario):
        if scenario == 'accuracy':
            return accuracy * 0.7 + speed * 0.15 + cost * 0.15
        elif scenario == 'cost':
            return accuracy * 0.3 + speed * 0.2 + cost * 0.5
        elif scenario == 'speed':
            return accuracy * 0.3 + speed * 0.5 + cost * 0.2
        else:
            return accuracy * 0.5 + speed * 0.25 + cost * 0.25
    
    rankings = []
    
    for model_id, perf in performance.items():
        default = default_profiles.get(model_id, {})
        
        accuracy = perf['avg_accuracy'] if perf['has_data'] and perf['avg_accuracy'] else default.get('accuracy', 80)
        speed = perf['speed_score'] if perf['speed_score'] else default.get('speed', 70)
        cost = perf['cost_score'] or default.get('cost', 60)
        
        score = calc_score(accuracy, speed, cost, scenario)
        
        rankings.append({
            'model_id': model_id,
            'name': perf['name'],
            'score': round(score, 1),
            'accuracy': round(accuracy, 1),
            'speed': round(speed, 1),
            'cost': cost,
            'total_tests': perf['total_tests'],
            'strengths': default.get('strengths', []),
            'weaknesses': default.get('weaknesses', []),
            'best_for': default.get('best_for', []),
            'data_source': '历史数据' if perf['has_data'] else '默认估计'
        })
    
    rankings.sort(key=lambda x: x['score'], reverse=True)
    
    scenario_names = {'accuracy': '准确性优先', 'cost': '成本优先', 'speed': '速度优先', 'balanced': '均衡模式'}
    
    return jsonify({
        'scenario': scenario,
        'scenario_name': scenario_names.get(scenario, '均衡模式'),
        'recommended': rankings[0] if rankings else None,
        'rankings': rankings,
        'has_history_data': any(p['has_data'] for p in performance.values())
    })


@model_recommend_bp.route('/api/model-stats', methods=['GET', 'POST'])
def model_stats_api():
    """模型统计数据API"""
    if request.method == 'GET':
        return jsonify(get_model_performance())
    else:
        data = request.json
        model_id = data.get('model_id')
        if model_id:
            update_model_stats(
                model_id,
                accuracy=data.get('accuracy'),
                time_cost=data.get('time'),
                consistency=data.get('consistency'),
                success=data.get('success', True)
            )
        return jsonify({'success': True})


@model_recommend_bp.route('/api/model-stats/reset', methods=['POST'])
def reset_model_stats():
    """重置模型统计数据"""
    save_model_stats({})
    return jsonify({'success': True})


@model_recommend_bp.route('/api/multi-model-compare', methods=['POST'])
def multi_model_compare_api():
    """多模型并行对比API"""
    config = ConfigService.load_config()
    data = request.json
    image = data.get('image')
    prompt = data.get('prompt', '')
    models = data.get('models', [])
    repeat = min(data.get('repeat', 3), 10)
    
    if not image:
        return jsonify({'error': '请上传图片'}), 400
    if len(models) < 1:
        return jsonify({'error': '请选择至少一个模型'}), 400
    
    results = {}
    
    def call_model(model_id, idx):
        try:
            is_qwen = 'qwen' in model_id.lower()
            if is_qwen:
                if not config.get('qwen_api_key'):
                    return {'model': model_id, 'idx': idx, 'error': '未配置Qwen API Key'}
                api_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
                api_key = config['qwen_api_key']
            else:
                if not config.get('api_key'):
                    return {'model': model_id, 'idx': idx, 'error': '未配置API Key'}
                api_url = config['api_url']
                api_key = config['api_key']
            
            content = [
                {'type': 'image_url', 'image_url': {'url': image}},
                {'type': 'text', 'text': prompt}
            ]
            
            payload = {
                'model': model_id,
                'messages': [{'role': 'user', 'content': content}]
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {api_key}"
            }
            
            start = time.time()
            response = requests.post(api_url, json=payload, headers=headers, timeout=120)
            elapsed = round(time.time() - start, 2)
            result = response.json()
            
            if 'choices' in result:
                return {
                    'model': model_id,
                    'idx': idx,
                    'result': result['choices'][0]['message']['content'],
                    'time': elapsed,
                    'tokens': result.get('usage', {}).get('total_tokens', 0),
                    'success': True
                }
            else:
                return {
                    'model': model_id,
                    'idx': idx,
                    'error': result.get('error', {}).get('message', '请求失败'),
                    'success': False
                }
        except Exception as e:
            return {'model': model_id, 'idx': idx, 'error': str(e), 'success': False}
    
    tasks = []
    for model_id in models:
        for i in range(repeat):
            tasks.append((model_id, i))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(call_model, m, i) for m, i in tasks]
        all_results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    for model_id in models:
        results[model_id] = {
            'outputs': [],
            'times': [],
            'tokens': [],
            'errors': []
        }
    
    for r in all_results:
        model_id = r['model']
        if r.get('success'):
            results[model_id]['outputs'].append(r['result'])
            results[model_id]['times'].append(r['time'])
            results[model_id]['tokens'].append(r.get('tokens', 0))
        else:
            results[model_id]['errors'].append(r.get('error', '未知错误'))
    
    for model_id in models:
        r = results[model_id]
        r['success_count'] = len(r['outputs'])
        r['error_count'] = len(r['errors'])
        r['avg_time'] = round(sum(r['times']) / len(r['times']), 2) if r['times'] else 0
        r['avg_tokens'] = round(sum(r['tokens']) / len(r['tokens'])) if r['tokens'] else 0
        
        if r['outputs']:
            norm = [o.replace(' ', '').replace('\n', '').lower() for o in r['outputs']]
            unique = len(set(norm))
            r['consistency'] = round((1 - (unique - 1) / len(norm)) * 100) if len(norm) > 1 else 100
            r['unique_outputs'] = unique
        else:
            r['consistency'] = 0
            r['unique_outputs'] = 0
    
    return jsonify({
        'results': results,
        'models': models,
        'repeat': repeat,
        'timestamp': datetime.now().isoformat()
    })
