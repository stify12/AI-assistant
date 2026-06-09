"""
AI调研员 - Flask API路由

提供RESTful API和SSE流式接口：
- 任务管理（创建、查询、删除）
- 需求解析（生成提纲）
- 数据采集（联网搜索 + 文件上传）
- 数据清洗
- 智能分析
- 报告生成与导出
- 迭代优化
- 全流程自动执行（SSE流式）
"""

import os
import uuid
import json as json_module
import requests
from flask import Blueprint, request, jsonify, render_template, send_file, Response, stream_with_context
from werkzeug.utils import secure_filename

from .agent import ResearchAgent
from .models import TaskStatus, AnalysisModelType
from .services import StorageService, FileParseService, ReportService
from .analysis_models import recommend_models, get_all_models

research_agent_bp = Blueprint('research_agent', __name__)

# 全局服务实例
storage_service = StorageService()
file_parse_service = FileParseService()

UPLOAD_FOLDER = 'research_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DEER_FLOW_URL = os.environ.get('DEER_FLOW_URL', 'http://172.17.0.1:2026')

_HOP_BY_HOP_HEADERS = {
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailer',
    'transfer-encoding',
    'upgrade',
}


def _rewrite_proxy_payload(content_type: str, payload: bytes) -> bytes:
    """将 DeerFlow 根路径改写到 /research-agent 前缀，避免与主站路由冲突。"""
    if not payload:
        return payload

    ctype = (content_type or '').lower()
    if not any(k in ctype for k in ('text/html', 'javascript', 'text/css')):
        return payload

    replacements = [
        (b'"/_next/', b'"/research-agent/_next/'),
        (b"'/_next/", b"'/research-agent/_next/"),
        (b'"/api/', b'"/research-agent/api/'),
        (b"'/api/", b"'/research-agent/api/"),
    ]

    data = payload
    for old, new in replacements:
        data = data.replace(old, new)
    return data


def _proxy_deer_flow(proxy_path: str = ''):
    """同路径反代 DeerFlow（/research-agent/** -> DeerFlow /**）。"""
    upstream_base = DEER_FLOW_URL.rstrip('/')
    upstream_path = f"/{proxy_path.lstrip('/')}" if proxy_path else '/'
    upstream_url = f"{upstream_base}{upstream_path}"

    headers = {
        key: value for key, value in request.headers.items()
        if key.lower() not in _HOP_BY_HOP_HEADERS and key.lower() != 'host'
    }
    headers['X-Forwarded-Proto'] = request.scheme
    headers['X-Forwarded-Host'] = request.host

    try:
        upstream_resp = requests.request(
            method=request.method,
            url=upstream_url,
            params=request.args,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=60,
        )
    except requests.RequestException as exc:
        return jsonify({'success': False, 'error': f'DeerFlow proxy failed: {exc}'}), 502

    content_type = upstream_resp.headers.get('Content-Type', '')
    response_body = _rewrite_proxy_payload(content_type, upstream_resp.content)

    response_headers = []
    for key, value in upstream_resp.headers.items():
        k = key.lower()
        if k in _HOP_BY_HOP_HEADERS or k in {'content-length', 'content-encoding'}:
            continue
        if k == 'location' and value.startswith('/'):
            value = '/research-agent' + value
        response_headers.append((key, value))

    return Response(response_body, status=upstream_resp.status_code, headers=response_headers)


def _get_current_user_id():
    """获取当前登录用户ID"""
    try:
        from routes.auth import get_current_user_id
        return get_current_user_id()
    except:
        return None


def _get_agent(user_id: int = None) -> ResearchAgent:
    """创建Agent实例（每次新建以使用最新的用户配置）"""
    return ResearchAgent(user_id=user_id)


# ============ 页面路由 ============

@research_agent_bp.route('/research-agent', defaults={'proxy_path': ''}, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
@research_agent_bp.route('/research-agent/<path:proxy_path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
def research_agent_page(proxy_path):
    """同路径反代到 DeerFlow 调研页面"""
    return _proxy_deer_flow(proxy_path)


# ============ 任务管理API ============

@research_agent_bp.route('/api/research-agent/tasks', methods=['GET'])
def list_tasks():
    """获取所有调研任务列表"""
    tasks = storage_service.list_tasks()
    return jsonify({'success': True, 'tasks': tasks})


@research_agent_bp.route('/api/research-agent/tasks', methods=['POST'])
def create_task():
    """创建新的调研任务"""
    data = request.json or {}
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'success': False, 'error': '请输入调研需求'}), 400
    
    industry = data.get('industry', '')
    scope = data.get('scope', '')
    llm_model = data.get('llm_model', 'deepseek-v3.2')
    
    agent = _get_agent(_get_current_user_id())
    agent.llm_model = llm_model
    task = agent.create_task(query, industry, scope)
    
    return jsonify({
        'success': True,
        'task': task.to_dict()
    })


@research_agent_bp.route('/api/research-agent/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务详情"""
    task = storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    return jsonify({'success': True, 'task': task.to_dict()})


@research_agent_bp.route('/api/research-agent/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    success = storage_service.delete_task(task_id)
    return jsonify({'success': success})


# ============ 步骤1：需求解析 ============

@research_agent_bp.route('/api/research-agent/parse', methods=['POST'])
def parse_requirement():
    """解析调研需求，生成提纲"""
    data = request.json or {}
    task_id = data.get('task_id')
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    try:
        agent = _get_agent(_get_current_user_id())
        agent.llm_model = task.llm_model
        outline = agent.parse_requirement(task)
        
        return jsonify({
            'success': True,
            'outline': outline.to_dict(),
            'recommended_models': recommend_models(task.query, task.industry)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 步骤2：数据采集 ============

@research_agent_bp.route('/api/research-agent/collect', methods=['POST'])
def collect_data():
    """执行数据采集（联网搜索）"""
    data = request.json or {}
    task_id = data.get('task_id')
    max_queries = data.get('max_queries', 15)
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    try:
        agent = _get_agent(_get_current_user_id())
        agent.llm_model = task.llm_model
        collected = agent.collect_data(task, max_queries)
        
        return jsonify({
            'success': True,
            'collected_count': len(collected),
            'collected_data': [d.to_dict() for d in collected[:50]]  # 最多返回50条
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@research_agent_bp.route('/api/research-agent/upload', methods=['POST'])
def upload_file():
    """上传用户自有数据文件"""
    task_id = request.form.get('task_id')
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有上传文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '没有选择文件'}), 400
    
    # 验证文件
    file_content = file.read()
    is_valid, error = file_parse_service.validate_file(file.filename, len(file_content))
    if not is_valid:
        return jsonify({'success': False, 'error': error}), 400
    
    # 保存文件
    task_folder = os.path.join(UPLOAD_FOLDER, task_id)
    os.makedirs(task_folder, exist_ok=True)
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
    filepath = os.path.join(task_folder, unique_filename)
    
    with open(filepath, 'wb') as f:
        f.write(file_content)
    
    # 加载任务并处理文件
    task = storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    try:
        agent = _get_agent(_get_current_user_id())
        agent.llm_model = task.llm_model
        extracted = agent.add_uploaded_data(task, filepath, file.filename)
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'extracted_count': len(extracted),
            'extracted_data': [d.to_dict() for d in extracted]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 步骤3：数据清洗 ============

@research_agent_bp.route('/api/research-agent/clean', methods=['POST'])
def clean_data():
    """清洗采集到的数据"""
    data = request.json or {}
    task_id = data.get('task_id')
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    try:
        agent = _get_agent(_get_current_user_id())
        agent.llm_model = task.llm_model
        cleaned = agent.clean_data(task)
        
        return jsonify({
            'success': True,
            'cleaned_count': len(cleaned),
            'cleaned_data': [d.to_dict() for d in cleaned[:50]]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 步骤4：智能分析 ============

@research_agent_bp.route('/api/research-agent/analyze', methods=['POST'])
def run_analysis():
    """执行智能分析"""
    data = request.json or {}
    task_id = data.get('task_id')
    model_types = data.get('model_types', [])  # 分析模型列表
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    try:
        agent = _get_agent(_get_current_user_id())
        agent.llm_model = task.llm_model
        results = agent.run_analysis(task, model_types if model_types else None)
        
        return jsonify({
            'success': True,
            'analysis_count': len(results),
            'analysis_results': [r.to_dict() for r in results]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@research_agent_bp.route('/api/research-agent/analysis-models', methods=['GET'])
def get_analysis_models():
    """获取所有可用的分析模型"""
    query = request.args.get('query', '')
    industry = request.args.get('industry', '')
    
    all_models = get_all_models()
    recommendations = recommend_models(query, industry) if query else []
    
    return jsonify({
        'success': True,
        'all_models': all_models,
        'recommendations': recommendations
    })


# ============ 步骤5：报告生成 ============

@research_agent_bp.route('/api/research-agent/generate-report', methods=['POST'])
def generate_report():
    """生成调研报告"""
    data = request.json or {}
    task_id = data.get('task_id')
    format_type = data.get('format', 'markdown')
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    try:
        agent = _get_agent(_get_current_user_id())
        agent.llm_model = task.llm_model
        report = agent.generate_report(task, format_type)
        
        return jsonify({
            'success': True,
            'report': report.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 步骤6：迭代优化 ============

@research_agent_bp.route('/api/research-agent/iterate', methods=['POST'])
def iterate_report():
    """基于用户反馈迭代优化报告"""
    data = request.json or {}
    task_id = data.get('task_id')
    feedback = data.get('feedback', '').strip()
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    if not feedback:
        return jsonify({'success': False, 'error': '请输入修改意见'}), 400
    
    task = storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    try:
        agent = _get_agent(_get_current_user_id())
        agent.llm_model = task.llm_model
        report = agent.iterate_report(task, feedback)
        
        return jsonify({
            'success': True,
            'report': report.to_dict(),
            'version': report.version
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 导出 ============

@research_agent_bp.route('/api/research-agent/export', methods=['POST'])
def export_report():
    """导出调研报告"""
    data = request.json or {}
    task_id = data.get('task_id')
    format_type = data.get('format', 'markdown')
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    if not task.report:
        return jsonify({'success': False, 'error': '还没有生成报告'}), 400
    
    try:
        agent = _get_agent(_get_current_user_id())
        output_path = agent.export_report(task, format_type)
        return send_file(output_path, as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 全流程自动执行（SSE流式） ============

@research_agent_bp.route('/api/research-agent/run-pipeline', methods=['POST'])
def run_pipeline():
    """全流程自动执行 - SSE流式返回进度"""
    data = request.json or {}
    task_id = data.get('task_id')
    model_types = data.get('model_types', [])
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    def generate():
        try:
            agent = _get_agent(_get_current_user_id())
            agent.llm_model = task.llm_model
            
            for event in agent.run_full_pipeline_stream(task, model_types):
                yield f"data: {json_module.dumps(event, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            yield f"data: {json_module.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


# ============ 单步骤SSE流式执行 ============

@research_agent_bp.route('/api/research-agent/step-stream', methods=['POST'])
def run_step_stream():
    """单步骤流式执行"""
    data = request.json or {}
    task_id = data.get('task_id')
    step = data.get('step', '')  # parse / collect / clean / analyze / generate
    model_types = data.get('model_types', [])
    
    if not task_id or not step:
        return jsonify({'success': False, 'error': '缺少task_id或step'}), 400
    
    task = storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    def generate():
        try:
            agent = _get_agent(_get_current_user_id())
            agent.llm_model = task.llm_model
            
            yield f"data: {json_module.dumps({'type': 'start', 'step': step}, ensure_ascii=False)}\n\n"
            
            if step == 'parse':
                outline = agent.parse_requirement(task)
                recommendations = recommend_models(task.query, task.industry)
                yield f"data: {json_module.dumps({'type': 'result', 'step': 'parse', 'outline': outline.to_dict(), 'recommended_models': recommendations}, ensure_ascii=False)}\n\n"
                
            elif step == 'collect':
                collected = agent.collect_data(task)
                yield f"data: {json_module.dumps({'type': 'result', 'step': 'collect', 'count': len(collected), 'data': [d.to_dict() for d in collected[:30]]}, ensure_ascii=False)}\n\n"
                
            elif step == 'clean':
                cleaned = agent.clean_data(task)
                yield f"data: {json_module.dumps({'type': 'result', 'step': 'clean', 'count': len(cleaned), 'data': [d.to_dict() for d in cleaned[:30]]}, ensure_ascii=False)}\n\n"
                
            elif step == 'analyze':
                results = agent.run_analysis(task, model_types if model_types else None)
                yield f"data: {json_module.dumps({'type': 'result', 'step': 'analyze', 'results': [r.to_dict() for r in results]}, ensure_ascii=False)}\n\n"
                
            elif step == 'generate':
                report = agent.generate_report(task)
                yield f"data: {json_module.dumps({'type': 'result', 'step': 'generate', 'report': report.to_dict()}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json_module.dumps({'type': 'done', 'step': step}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            yield f"data: {json_module.dumps({'type': 'error', 'step': step, 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )
