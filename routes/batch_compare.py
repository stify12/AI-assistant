"""
批量对比评估路由模块
提供批量对比分析、报告生成、导出等功能
"""
import json
import uuid
import requests
from datetime import datetime
from flask import Blueprint, request, jsonify, Response

from services.config_service import ConfigService
from utils.text_utils import remove_think_tags, extract_json_from_text

batch_compare_bp = Blueprint('batch_compare', __name__)


def analyze_error_type(item):
    """分析错误类型"""
    # 标准答案：优先取 answer，如果没有则取 mainAnswer
    standard = str(item.get('answer', '') or item.get('mainAnswer', '')).strip().lower()
    user = str(item.get('userAnswer', '')).strip().lower()
    
    if not user:
        return '识别不准确'
    if not standard:
        return '标准答案缺失'
    
    # 检查是否是格式问题
    if standard.replace(' ', '') == user.replace(' ', ''):
        return '格式错误'
    
    # 检查是否是部分正确
    if standard in user or user in standard:
        return '部分正确'
    
    # 检查是否是计算错误（数字类型）
    try:
        if abs(float(standard) - float(user)) < 0.01:
            return '精度误差'
        return '计算错误'
    except:
        pass
    
    # 检查是否是选项混淆
    if len(standard) == 1 and len(user) == 1 and standard.isalpha() and user.isalpha():
        return '选项混淆'
    
    return '规则有误'


def generate_optimization_suggestions(analysis_data):
    """根据分析数据生成优化建议"""
    suggestions = []
    
    error_types = analysis_data.get('error_types', {})
    overall_accuracy = analysis_data.get('summary', {}).get('overall_accuracy', 0)
    
    if overall_accuracy < 80:
        suggestions.append({
            'priority': '高',
            'category': '整体准确率',
            'issue': f'整体准确率{overall_accuracy}%低于80%阈值',
            'suggestion': '建议优化提示词或更换更高精度的模型'
        })
    
    if error_types.get('识别不准确', 0) > 0:
        suggestions.append({
            'priority': '高',
            'category': '识别问题',
            'issue': f'存在{error_types.get("识别不准确", 0)}个识别不准确的题目',
            'suggestion': '检查图片质量，优化OCR相关提示词，或使用视觉能力更强的模型'
        })
    
    if error_types.get('规则有误', 0) > 0:
        suggestions.append({
            'priority': '中',
            'category': '规则问题',
            'issue': f'存在{error_types.get("规则有误", 0)}个规则有误的题目',
            'suggestion': '检查批改规则配置，确保标准答案格式正确'
        })
    
    if error_types.get('格式错误', 0) > 0:
        suggestions.append({
            'priority': '低',
            'category': '格式问题',
            'issue': f'存在{error_types.get("格式错误", 0)}个格式错误',
            'suggestion': '统一答案格式要求，在提示词中明确输出格式'
        })
    
    if not suggestions:
        suggestions.append({
            'priority': '低',
            'category': '维护建议',
            'issue': '当前表现良好',
            'suggestion': '建议定期进行评估测试，持续监控模型表现'
        })
    
    return suggestions


@batch_compare_bp.route('/analyze', methods=['POST'])
def batch_compare_analyze():
    """批量对比深度分析 - 返回详细评估数据"""
    data = request.json
    rows = data.get('rows', [])
    
    if not rows:
        return jsonify({'error': '无数据'}), 400
    
    # 按模型分组
    model_groups = {}
    for row in rows:
        model = row.get('model', '未知模型')
        if model not in model_groups:
            model_groups[model] = {
                'batches': [],
                'total_questions': 0,
                'correct_count': 0,
                'error_types': {},
                'questions': []
            }
        model_groups[model]['batches'].append(row.get('batch', ''))
        
        # 解析JSON数据
        json_data = row.get('json_data', [])
        if isinstance(json_data, str):
            try:
                json_data = json.loads(json_data)
            except:
                json_data = []
        
        for item in json_data:
            model_groups[model]['total_questions'] += 1
            is_correct = str(item.get('correct', '')).lower() == 'yes'
            if is_correct:
                model_groups[model]['correct_count'] += 1
            else:
                # 分析错误类型
                error_type = analyze_error_type(item)
                model_groups[model]['error_types'][error_type] = model_groups[model]['error_types'].get(error_type, 0) + 1
            
            # 标准答案：优先取 answer，如果没有则取 mainAnswer
            standard_answer = item.get('answer', '') or item.get('mainAnswer', '')
            # AI答案：优先取 mainAnswer，如果没有则取 userAnswer
            ai_answer = item.get('mainAnswer', '') or item.get('userAnswer', '')
            model_groups[model]['questions'].append({
                'index': item.get('index', ''),
                'standard_answer': standard_answer,
                'ai_answer': ai_answer,
                'user_answer': item.get('userAnswer', ''),
                'is_correct': is_correct,
                'error_type': None if is_correct else analyze_error_type(item),
                'batch': row.get('batch', '')
            })
    
    # 计算各模型统计
    model_stats = {}
    for model, data in model_groups.items():
        accuracy = round(data['correct_count'] / data['total_questions'] * 100, 2) if data['total_questions'] > 0 else 0
        model_stats[model] = {
            'total_questions': data['total_questions'],
            'correct_count': data['correct_count'],
            'error_count': data['total_questions'] - data['correct_count'],
            'accuracy': accuracy,
            'accuracy_rank': 0,
            'error_types': data['error_types'],
            'batches': list(set(data['batches'])),
            'questions': data['questions']
        }
    
    # 计算排名
    sorted_models = sorted(model_stats.items(), key=lambda x: x[1]['accuracy'], reverse=True)
    for rank, (model, _) in enumerate(sorted_models, 1):
        model_stats[model]['accuracy_rank'] = rank
    
    # 计算整体统计
    total_questions = sum(s['total_questions'] for s in model_stats.values())
    total_correct = sum(s['correct_count'] for s in model_stats.values())
    overall_accuracy = round(total_correct / total_questions * 100, 2) if total_questions > 0 else 0
    
    # 错误类型汇总
    all_error_types = {}
    for stats in model_stats.values():
        for error_type, count in stats['error_types'].items():
            all_error_types[error_type] = all_error_types.get(error_type, 0) + count
    
    # 问题定位 - 找出错误题目
    problem_questions = []
    for model, stats in model_stats.items():
        for q in stats['questions']:
            if not q['is_correct']:
                problem_questions.append({
                    'model': model,
                    'index': q['index'],
                    'standard_answer': q['standard_answer'],
                    'user_answer': q['user_answer'],
                    'error_type': q['error_type'],
                    'batch': q['batch']
                })
    
    return jsonify({
        'summary': {
            'total_models': len(model_stats),
            'total_questions': total_questions,
            'total_correct': total_correct,
            'overall_accuracy': overall_accuracy,
            'accuracy_threshold': 80,
            'pass_threshold': overall_accuracy >= 80
        },
        'model_stats': model_stats,
        'error_types': all_error_types,
        'problem_questions': problem_questions,
        'rankings': [{'model': m, **s} for m, s in sorted_models],
        'generated_at': datetime.now().isoformat()
    })


@batch_compare_bp.route('/report', methods=['POST'])
def generate_batch_report():
    """生成批量对比评估报告"""
    config = ConfigService.load_config()
    data = request.json
    analysis_data = data.get('analysis_data', {})
    include_ai_analysis = data.get('include_ai_analysis', False)
    
    report = {
        'report_id': str(uuid.uuid4())[:8],
        'report_type': 'batch_compare_evaluation',
        'generated_at': datetime.now().isoformat(),
        'evaluation_background': {
            'purpose': '批量对比评估',
            'total_models': analysis_data.get('summary', {}).get('total_models', 0),
            'total_questions': analysis_data.get('summary', {}).get('total_questions', 0),
            'evaluation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        'configuration': {
            'accuracy_threshold': 80,
            'evaluation_dimensions': ['准确率', '错误类型分布', '模型对比', '问题定位']
        },
        'core_data': {
            'overall_accuracy': analysis_data.get('summary', {}).get('overall_accuracy', 0),
            'pass_threshold': analysis_data.get('summary', {}).get('pass_threshold', False),
            'model_rankings': analysis_data.get('rankings', []),
            'error_distribution': analysis_data.get('error_types', {})
        },
        'problem_analysis': {
            'total_errors': len(analysis_data.get('problem_questions', [])),
            'error_types': analysis_data.get('error_types', {}),
            'problem_questions': analysis_data.get('problem_questions', [])[:20]
        },
        'optimization_suggestions': generate_optimization_suggestions(analysis_data),
        'ai_analysis': None
    }
    
    # AI分析（如果配置了Qwen）
    if include_ai_analysis and config.get('qwen_api_key'):
        try:
            ai_prompt = f"""请对以下AI批改效果评估数据进行专业分析：

评估数据摘要：
- 总模型数：{analysis_data.get('summary', {}).get('total_models', 0)}
- 总题目数：{analysis_data.get('summary', {}).get('total_questions', 0)}
- 整体准确率：{analysis_data.get('summary', {}).get('overall_accuracy', 0)}%
- 错误类型分布：{json.dumps(analysis_data.get('error_types', {}), ensure_ascii=False)}
- 模型排名：{json.dumps([{'model': r['model'], 'accuracy': r['accuracy']} for r in analysis_data.get('rankings', [])[:5]], ensure_ascii=False)}

请提供：
1. 数据解读：解释各项指标的含义
2. 问题分析：分析主要错误原因
3. 优化建议：给出具体可执行的改进方案

请以JSON格式输出：
{{"data_interpretation": "...", "problem_analysis": "...", "optimization_suggestions": ["建议1", "建议2", ...]}}"""

            ai_payload = {
                'model': 'qwen3-max',
                'messages': [
                    {'role': 'system', 'content': '你是AI批改效果分析专家，请直接输出JSON格式结果，不要输出思考过程。'},
                    {'role': 'user', 'content': ai_prompt}
                ]
            }
            
            ai_response = requests.post(
                'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
                json=ai_payload,
                headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {config['qwen_api_key']}"},
                timeout=60
            )
            ai_result = ai_response.json()
            if 'choices' in ai_result:
                content = ai_result['choices'][0]['message']['content']
                content = remove_think_tags(content)
                parsed = extract_json_from_text(content)
                if parsed:
                    report['ai_analysis'] = parsed
                else:
                    report['ai_analysis'] = {'raw': content}
        except Exception as e:
            report['ai_analysis'] = {'error': str(e)}
    
    return jsonify(report)


@batch_compare_bp.route('/export-report', methods=['POST'])
def export_batch_report():
    """导出评估报告为HTML"""
    data = request.json
    report = data.get('report', {})
    
    html = generate_report_html(report)
    
    return Response(html, mimetype='text/html', 
                   headers={'Content-Disposition': f'attachment;filename=evaluation_report_{report.get("report_id", "")}.html'})


def generate_report_html(report):
    """生成HTML格式报告"""
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>AI批改效果评估报告 - {report.get('report_id', '')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: 0 auto; padding: 40px 20px; background: #f5f5f7; }}
        .report {{ background: #fff; border-radius: 16px; padding: 40px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
        h1 {{ font-size: 28px; color: #1d1d1f; margin-bottom: 8px; }}
        h2 {{ font-size: 20px; color: #1d1d1f; margin-top: 32px; padding-bottom: 12px; border-bottom: 1px solid #e5e5e5; }}
        h3 {{ font-size: 16px; color: #424245; margin-top: 24px; }}
        .meta {{ color: #86868b; font-size: 14px; margin-bottom: 32px; }}
        .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin: 24px 0; }}
        .stat-card {{ background: #f5f5f7; border-radius: 12px; padding: 20px; text-align: center; }}
        .stat-value {{ font-size: 32px; font-weight: 700; color: #1d1d1f; }}
        .stat-label {{ font-size: 12px; color: #86868b; margin-top: 4px; }}
        .highlight {{ background: #1d1d1f; color: #fff; }}
        .highlight .stat-value {{ color: #fff; }}
        .highlight .stat-label {{ color: rgba(255,255,255,0.7); }}
        table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e5e5; }}
        th {{ background: #f5f5f7; font-weight: 600; font-size: 12px; text-transform: uppercase; color: #86868b; }}
        .pass {{ color: #1e7e34; background: #e3f9e5; padding: 2px 8px; border-radius: 4px; }}
        .fail {{ color: #d73a49; background: #ffeef0; padding: 2px 8px; border-radius: 4px; }}
        .suggestion {{ background: #f5f5f7; border-radius: 8px; padding: 16px; margin: 12px 0; }}
        .suggestion-priority {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .priority-high {{ background: #ffeef0; color: #d73a49; }}
        .priority-medium {{ background: #fff3e0; color: #e65100; }}
        .priority-low {{ background: #e3f9e5; color: #1e7e34; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e5e5; color: #86868b; font-size: 12px; text-align: center; }}
    </style>
</head>
<body>
    <div class="report">
        <h1>AI批改效果评估报告</h1>
        <div class="meta">
            报告ID: {report.get('report_id', '-')} | 生成时间: {report.get('generated_at', '-')}
        </div>
        
        <h2>一、评估背景</h2>
        <p>评估目的：{report.get('evaluation_background', {}).get('purpose', '-')}</p>
        <p>评估模型数：{report.get('evaluation_background', {}).get('total_models', 0)} | 评估题目数：{report.get('evaluation_background', {}).get('total_questions', 0)}</p>
        
        <h2>二、核心数据</h2>
        <div class="stat-grid">
            <div class="stat-card {'highlight' if report.get('core_data', {}).get('pass_threshold') else ''}">
                <div class="stat-value">{report.get('core_data', {}).get('overall_accuracy', 0)}%</div>
                <div class="stat-label">整体准确率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{report.get('evaluation_background', {}).get('total_models', 0)}</div>
                <div class="stat-label">评估模型数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{report.get('evaluation_background', {}).get('total_questions', 0)}</div>
                <div class="stat-label">评估题目数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{report.get('problem_analysis', {}).get('total_errors', 0)}</div>
                <div class="stat-label">错误题目数</div>
            </div>
        </div>
        
        <h3>模型排名</h3>
        <table>
            <thead><tr><th>排名</th><th>模型</th><th>准确率</th><th>正确数</th><th>错误数</th></tr></thead>
            <tbody>
"""
    
    for i, r in enumerate(report.get('core_data', {}).get('model_rankings', [])[:10], 1):
        html += f"""<tr>
            <td>{i}</td>
            <td>{r.get('model', '-')}</td>
            <td><span class="{'pass' if r.get('accuracy', 0) >= 80 else 'fail'}">{r.get('accuracy', 0)}%</span></td>
            <td>{r.get('correct_count', 0)}</td>
            <td>{r.get('error_count', 0)}</td>
        </tr>"""
    
    html += """</tbody></table>
        
        <h2>三、问题分析</h2>
        <h3>错误类型分布</h3>
        <table>
            <thead><tr><th>错误类型</th><th>数量</th><th>占比</th></tr></thead>
            <tbody>
"""
    
    error_types = report.get('problem_analysis', {}).get('error_types', {})
    total_errors = sum(error_types.values()) if error_types else 1
    for error_type, count in error_types.items():
        html += f"""<tr>
            <td>{error_type}</td>
            <td>{count}</td>
            <td>{round(count/total_errors*100, 1)}%</td>
        </tr>"""
    
    html += """</tbody></table>
        
        <h2>四、优化建议</h2>
"""
    
    for s in report.get('optimization_suggestions', []):
        priority_class = 'priority-high' if s.get('priority') == '高' else ('priority-medium' if s.get('priority') == '中' else 'priority-low')
        html += f"""<div class="suggestion">
            <span class="suggestion-priority {priority_class}">{s.get('priority', '-')}优先级</span>
            <strong> {s.get('category', '-')}</strong>
            <p style="margin:8px 0 0;color:#424245;">{s.get('issue', '-')}</p>
            <p style="margin:4px 0 0;color:#1d1d1f;">建议：{s.get('suggestion', '-')}</p>
        </div>"""
    
    # AI分析
    if report.get('ai_analysis'):
        ai = report['ai_analysis']
        html += """<h2>五、AI智能分析</h2>"""
        if ai.get('data_interpretation'):
            html += f"""<h3>数据解读</h3><p>{ai.get('data_interpretation', '')}</p>"""
        if ai.get('problem_analysis'):
            html += f"""<h3>问题分析</h3><p>{ai.get('problem_analysis', '')}</p>"""
        if ai.get('optimization_suggestions'):
            html += """<h3>AI优化建议</h3><ul>"""
            for s in ai.get('optimization_suggestions', []):
                html += f"""<li>{s}</li>"""
            html += """</ul>"""
    
    html += f"""
        <div class="footer">
            本报告由 AI批改效果分析平台 自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""
    
    return html
