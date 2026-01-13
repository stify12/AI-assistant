"""
Flask API路由 - 知识点类题生成智能体
支持：每步导出Excel、并行生成类题、流式输出
"""

import os
import uuid
import base64
import json as json_module
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Blueprint, request, jsonify, render_template, send_file, Response, stream_with_context
from werkzeug.utils import secure_filename

from .models import AgentTask, TaskConfig, ImageInfo, KnowledgePoint, SimilarQuestion, ParsedQuestion, DedupeResult
from .services import (
    validate_image_format, validate_image_size,
    ModelService, SimilarityService, ExcelService, StorageService
)
from .agent import HomeworkAgent
from .tools import extract_json_from_response, safe_json_loads, DEFAULT_PROMPTS

knowledge_agent_bp = Blueprint('knowledge_agent', __name__)

UPLOAD_FOLDER = 'knowledge_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

storage_service = StorageService()
excel_service = ExcelService()
model_service = ModelService()
current_tasks = {}


@knowledge_agent_bp.route('/knowledge-agent')
def knowledge_agent_page():
    return render_template('knowledge-agent.html')


# ============ 图片上传 ============

@knowledge_agent_bp.route('/api/knowledge-agent/upload', methods=['POST'])
def upload_images():
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': '没有上传文件'}), 400
    
    files = request.files.getlist('files')
    if not files:
        return jsonify({'success': False, 'error': '没有选择文件'}), 400
    
    task_id = str(uuid.uuid4())[:8]
    task_folder = os.path.join(UPLOAD_FOLDER, task_id)
    os.makedirs(task_folder, exist_ok=True)
    
    uploaded_images = []
    errors = []
    
    for file in files:
        if file.filename == '':
            continue
        
        is_valid, error = validate_image_format(file.filename)
        if not is_valid:
            errors.append({'filename': file.filename, 'error': error})
            continue
        
        file_content = file.read()
        is_valid, error = validate_image_size(len(file_content))
        if not is_valid:
            errors.append({'filename': file.filename, 'error': error})
            continue
        
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(task_folder, unique_filename)
        
        with open(filepath, 'wb') as f:
            f.write(file_content)
        
        img_id = str(uuid.uuid4())[:8]
        uploaded_images.append({
            'id': img_id,
            'filename': file.filename,
            'path': filepath,
            'preview_url': f'/api/knowledge-agent/preview/{task_id}/{unique_filename}'
        })
    
    task = AgentTask(task_id=task_id)
    task.images = [ImageInfo(id=img['id'], filename=img['filename'], path=img['path']) 
                   for img in uploaded_images]
    current_tasks[task_id] = task
    storage_service.save_task(task)
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'images': uploaded_images,
        'errors': errors
    })


@knowledge_agent_bp.route('/api/knowledge-agent/preview/<task_id>/<filename>')
def preview_image(task_id, filename):
    filepath = os.path.join(UPLOAD_FOLDER, task_id, filename)
    if os.path.exists(filepath):
        return send_file(filepath)
    return jsonify({'error': '图片不存在'}), 404


# ============ 流式解析 ============

@knowledge_agent_bp.route('/api/knowledge-agent/parse-stream', methods=['POST'])
def parse_images_stream():
    """串行流式解析图片（保留用于单图片或需要实时输出的场景）"""
    data = request.json or {}
    task_id = data.get('task_id')
    multimodal_model = data.get('multimodal_model')
    custom_prompt = data.get('prompt', DEFAULT_PROMPTS.get('parse', ''))
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = current_tasks.get(task_id) or storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    def generate():
        total_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        
        for idx, img_info in enumerate(task.images):
            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'正在解析图片 {idx+1}/{len(task.images)}: {img_info.filename}'})}\n\n"
            
            try:
                with open(img_info.path, 'rb') as f:
                    image_base64 = base64.b64encode(f.read()).decode('utf-8')
                
                full_response = ""
                for chunk_data in model_service.call_multimodal_stream(
                    multimodal_model or 'doubao-seed-1-8-251228',
                    image_base64,
                    custom_prompt
                ):
                    if isinstance(chunk_data, dict):
                        if chunk_data.get('type') == 'content':
                            full_response += chunk_data['content']
                            yield f"data: {json_module.dumps({'type': 'chunk', 'content': chunk_data['content'], 'image': img_info.filename})}\n\n"
                        elif chunk_data.get('type') == 'usage':
                            usage = chunk_data['usage']
                            total_usage['prompt_tokens'] += usage.get('prompt_tokens', 0)
                            total_usage['completion_tokens'] += usage.get('completion_tokens', 0)
                            total_usage['total_tokens'] += usage.get('total_tokens', 0)
                            yield f"data: {json_module.dumps({'type': 'usage', 'usage': usage, 'image': img_info.filename})}\n\n"
                    else:
                        full_response += chunk_data
                        yield f"data: {json_module.dumps({'type': 'chunk', 'content': chunk_data, 'image': img_info.filename})}\n\n"
                
                yield f"data: {json_module.dumps({'type': 'image_done', 'image': img_info.filename, 'response': full_response})}\n\n"
            except Exception as e:
                yield f"data: {json_module.dumps({'type': 'error', 'image': img_info.filename, 'error': str(e)})}\n\n"
        
        yield f"data: {json_module.dumps({'type': 'done', 'total_usage': total_usage})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@knowledge_agent_bp.route('/api/knowledge-agent/parse-parallel', methods=['POST'])
def parse_images_parallel():
    """并行解析多张图片 - 大幅提升多图片处理速度"""
    data = request.json or {}
    task_id = data.get('task_id')
    multimodal_model = data.get('multimodal_model', 'doubao-seed-1-8-251228')
    custom_prompt = data.get('prompt', DEFAULT_PROMPTS.get('parse', ''))
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = current_tasks.get(task_id) or storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    def generate():
        total_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        total_images = len(task.images)
        
        # 处理空图片列表的情况
        if total_images == 0:
            yield f"data: {json_module.dumps({'type': 'error', 'error': '没有图片可解析'})}\n\n"
            yield f"data: {json_module.dumps({'type': 'done', 'total_usage': total_usage, 'results': {}})}\n\n"
            return
        
        yield f"data: {json_module.dumps({'type': 'progress', 'message': f'开始并行解析 {total_images} 张图片...'})}\n\n"
        
        def parse_single_image(idx, img_info):
            """解析单张图片"""
            try:
                with open(img_info.path, 'rb') as f:
                    image_base64 = base64.b64encode(f.read()).decode('utf-8')
                
                # 使用非流式调用以支持并行
                response = model_service.call_multimodal(
                    multimodal_model,
                    image_base64,
                    custom_prompt
                )
                return idx, img_info.filename, response, None
            except Exception as e:
                return idx, img_info.filename, None, str(e)
        
        # 使用线程池并行处理
        max_workers = max(1, min(4, total_images))  # 最少1个，最多4个并行
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(parse_single_image, idx, img_info) 
                for idx, img_info in enumerate(task.images)
            ]
            
            completed = 0
            for future in as_completed(futures):
                try:
                    idx, filename, response, error = future.result()
                    completed += 1
                    
                    if error:
                        yield f"data: {json_module.dumps({'type': 'error', 'image': filename, 'error': error})}\n\n"
                    else:
                        results[filename] = response
                        yield f"data: {json_module.dumps({'type': 'image_done', 'image': filename, 'response': response, 'index': idx})}\n\n"
                    
                    yield f"data: {json_module.dumps({'type': 'progress', 'message': f'已完成 {completed}/{total_images} 张图片'})}\n\n"
                except Exception as e:
                    yield f"data: {json_module.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        yield f"data: {json_module.dumps({'type': 'done', 'total_usage': total_usage, 'results': results})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@knowledge_agent_bp.route('/api/knowledge-agent/extract-stream', methods=['POST'])
def extract_knowledge_stream():
    """流式提取知识点 - 每道题只提取一个核心知识点"""
    data = request.json or {}
    task_id = data.get('task_id')
    text_model = data.get('text_model')
    custom_prompt = data.get('prompt', DEFAULT_PROMPTS.get('extract', ''))
    questions_data = data.get('questions', [])
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    def generate():
        total_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        
        for idx, q in enumerate(questions_data):
            content = q.get('content', '')
            subject = q.get('subject', '')
            
            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'正在提取知识点 {idx+1}/{len(questions_data)}'})}\n\n"
            
            prompt = custom_prompt.replace('{content}', content).replace('{subject}', subject)
            
            try:
                full_response = ""
                for chunk_data in model_service.call_text_stream(
                    text_model or 'deepseek-v3.2',
                    prompt
                ):
                    if isinstance(chunk_data, dict):
                        if chunk_data.get('type') == 'content':
                            full_response += chunk_data['content']
                            yield f"data: {json_module.dumps({'type': 'chunk', 'content': chunk_data['content'], 'question_idx': idx})}\n\n"
                        elif chunk_data.get('type') == 'usage':
                            usage = chunk_data['usage']
                            total_usage['prompt_tokens'] += usage.get('prompt_tokens', 0)
                            total_usage['completion_tokens'] += usage.get('completion_tokens', 0)
                            total_usage['total_tokens'] += usage.get('total_tokens', 0)
                            yield f"data: {json_module.dumps({'type': 'usage', 'usage': usage, 'question_idx': idx})}\n\n"
                    else:
                        full_response += chunk_data
                        yield f"data: {json_module.dumps({'type': 'chunk', 'content': chunk_data, 'question_idx': idx})}\n\n"
                
                yield f"data: {json_module.dumps({'type': 'question_done', 'question_idx': idx, 'response': full_response})}\n\n"
            except Exception as e:
                yield f"data: {json_module.dumps({'type': 'error', 'question_idx': idx, 'error': str(e)})}\n\n"
        
        yield f"data: {json_module.dumps({'type': 'done', 'total_usage': total_usage})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@knowledge_agent_bp.route('/api/knowledge-agent/generate-stream', methods=['POST'])
def generate_questions_stream():
    """并行流式生成类题"""
    data = request.json or {}
    task_id = data.get('task_id')
    text_model = data.get('text_model', 'deepseek-v3.2')
    custom_prompt = data.get('prompt', DEFAULT_PROMPTS.get('generate', ''))
    knowledge_points = data.get('knowledge_points', [])
    count = data.get('count', 1)
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    def generate():
        total = len(knowledge_points)
        
        # 处理空知识点列表的情况
        if total == 0:
            yield f"data: {json_module.dumps({'type': 'error', 'error': '没有知识点可生成类题'})}\n\n"
            yield f"data: {json_module.dumps({'type': 'done'})}\n\n"
            return
        
        yield f"data: {json_module.dumps({'type': 'progress', 'message': f'开始并行生成 {total} 个知识点的类题...'})}\n\n"
        
        # 并行生成
        results = {}
        
        def generate_for_kp(idx, kp):
            primary = kp.get('primary', '')
            secondary = kp.get('secondary', '')
            solution_approach = kp.get('analysis', kp.get('solution_approach', ''))
            difficulty = kp.get('difficulty', '中等')
            q_type = kp.get('question_type', '简答题')
            
            prompt = (custom_prompt
                     .replace('{primary}', primary)
                     .replace('{secondary}', secondary)
                     .replace('{solution_approach}', solution_approach)
                     .replace('{kp}', primary)
                     .replace('{analysis}', solution_approach)
                     .replace('{difficulty}', difficulty)
                     .replace('{type}', q_type)
                     .replace('{count}', str(count)))
            
            try:
                response = model_service.call_text_generation(text_model, prompt)
                return idx, primary, response, None
            except Exception as e:
                return idx, primary, None, str(e)
        
        # 使用线程池并行执行
        max_workers = max(1, min(4, total))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(generate_for_kp, idx, kp) for idx, kp in enumerate(knowledge_points)]
            
            completed = 0
            for future in as_completed(futures):
                try:
                    idx, kp_name, response, error = future.result()
                    completed += 1
                    
                    if error:
                        yield f"data: {json_module.dumps({'type': 'error', 'kp_idx': idx, 'error': error})}\n\n"
                    else:
                        results[idx] = {'kp_name': kp_name, 'response': response}
                        yield f"data: {json_module.dumps({'type': 'kp_done', 'kp_idx': idx, 'kp_name': kp_name, 'response': response})}\n\n"
                    
                    yield f"data: {json_module.dumps({'type': 'progress', 'message': f'已完成 {completed}/{total}'})}\n\n"
                except Exception as e:
                    yield f"data: {json_module.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        yield f"data: {json_module.dumps({'type': 'done'})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


# ============ 保存结果 ============

@knowledge_agent_bp.route('/api/knowledge-agent/save-parse', methods=['POST'])
def save_parse_results():
    """保存解析结果"""
    data = request.json or {}
    task_id = data.get('task_id')
    questions = data.get('questions', [])
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = current_tasks.get(task_id) or storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    # 转换为ParsedQuestion对象
    parsed_questions = []
    for q in questions:
        kps = []
        for kp_data in q.get('knowledge_points', []):
            kp = KnowledgePoint(
                id=kp_data.get('id', str(uuid.uuid4())[:8]),
                primary=kp_data.get('primary', ''),
                secondary=kp_data.get('secondary', ''),
                analysis=kp_data.get('analysis', '')
            )
            kps.append(kp)
        
        pq = ParsedQuestion(
            id=q.get('id', str(uuid.uuid4())[:8]),
            image_source=q.get('image_source', ''),
            content=q.get('content', ''),
            subject=q.get('subject', ''),
            knowledge_points=kps
        )
        parsed_questions.append(pq)
    
    task.parsed_questions = parsed_questions
    task.status = 'parsed'
    current_tasks[task_id] = task
    storage_service.save_task(task)
    
    return jsonify({'success': True})


@knowledge_agent_bp.route('/api/knowledge-agent/save-similar', methods=['POST'])
def save_similar_results():
    """保存类题结果"""
    data = request.json or {}
    task_id = data.get('task_id')
    similar_questions = data.get('similar_questions', [])
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = current_tasks.get(task_id) or storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    # 转换为SimilarQuestion对象
    sqs = []
    for sq_data in similar_questions:
        sq = SimilarQuestion(
            id=sq_data.get('id', str(uuid.uuid4())[:8]),
            knowledge_point_id=sq_data.get('knowledge_point_id', ''),
            primary=sq_data.get('primary', ''),
            secondary=sq_data.get('secondary', ''),
            content=sq_data.get('content', ''),
            answer=sq_data.get('answer', ''),
            solution_steps=sq_data.get('solution_steps', '')
        )
        sqs.append(sq)
    
    task.similar_questions = sqs
    task.status = 'completed'
    current_tasks[task_id] = task
    storage_service.save_task(task)
    
    return jsonify({'success': True})


# ============ 去重 ============

DEDUPE_PROMPT = """你是一个专业的知识点分析专家。请分析以下知识点列表，识别出语义相似或重复的知识点，并进行智能合并。

【知识点列表】
{knowledge_points}

【任务要求】
1. 识别语义相同或高度相似的知识点（如"一元二次方程"和"一元二次方程求解"应合并）
2. 保留有明显差异的知识点（如"一元二次方程"和"二元一次方程"应保留）
3. 合并时保留更完整、更准确的描述
4. 保留每个知识点的解题思路（analysis）

【输出格式】JSON数组，每个元素代表一个唯一知识点：
[
    {
        "id": "原始ID或新生成的ID",
        "primary": "一级知识点名称",
        "secondary": "二级知识点详细描述",
        "analysis": "解题思路",
        "merged_from": ["被合并的知识点ID列表，如果没有合并则为空数组"]
    }
]

【重要要求】
1. 只合并真正语义相同的知识点
2. 不同的知识点必须保留，即使名称相似
3. 只输出JSON数组，不要任何解释文字"""


@knowledge_agent_bp.route('/api/knowledge-agent/dedupe', methods=['POST'])
def dedupe_knowledge_points():
    """使用LLM进行智能去重"""
    data = request.json or {}
    task_id = data.get('task_id')
    use_llm = data.get('use_llm', True)  # 默认使用LLM去重
    threshold = data.get('threshold', 0.85)
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = current_tasks.get(task_id) or storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    try:
        if use_llm:
            # 使用LLM进行智能去重
            unique_points, dedupe_results, usage = llm_dedupe_knowledge_points(task)
        else:
            # 使用传统相似度算法
            agent = HomeworkAgent()
            agent.current_task = task
            unique_points, dedupe_results = agent.dedupe_knowledge_points(threshold)
            usage = None
        
        task.dedupe_results = dedupe_results
        task.config.similarity_threshold = threshold
        current_tasks[task_id] = task
        storage_service.save_task(task)
        
        result = {
            'success': True,
            'unique_points': [kp.to_dict() for kp in unique_points],
            'dedupe_results': [dr.to_dict() for dr in dedupe_results]
        }
        if usage:
            result['usage'] = usage
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def llm_dedupe_knowledge_points(task):
    """使用LLM进行知识点去重"""
    import re
    
    # 收集所有知识点
    all_kps = []
    kp_map = {}
    for q in task.parsed_questions:
        for kp in q.knowledge_points:
            if kp.id not in kp_map:
                all_kps.append({
                    'id': kp.id,
                    'primary': kp.primary,
                    'secondary': kp.secondary,
                    'analysis': kp.analysis
                })
                kp_map[kp.id] = kp
    
    if len(all_kps) <= 1:
        # 只有一个或没有知识点，无需去重
        unique_points = list(kp_map.values())
        dedupe_results = [DedupeResult(
            original_point=kp.primary,
            merged_point=kp.primary,
            similarity_score=1.0,
            is_merged=False
        ) for kp in unique_points]
        return unique_points, dedupe_results, None
    
    # 构建提示词
    kp_text = "\n".join([
        f"- ID: {kp['id']}, 一级知识点: {kp['primary']}, 二级知识点: {kp['secondary']}, 解题思路: {kp['analysis'][:100]}..."
        for kp in all_kps
    ])
    prompt = DEDUPE_PROMPT.replace('{knowledge_points}', kp_text)
    
    # 调用LLM
    try:
        response = model_service.call_text_generation('deepseek-v3.2', prompt)
        
        # 解析响应
        json_match = re.search(r'\[[\s\S]*\]', response)
        if not json_match:
            raise Exception("LLM返回格式错误")
        
        result_kps = json_module.loads(json_match.group())
        
        # 构建去重结果
        unique_points = []
        dedupe_results = []
        merged_ids = set()
        
        for item in result_kps:
            kp = KnowledgePoint(
                id=item.get('id', str(uuid.uuid4())[:8]),
                primary=item.get('primary', ''),
                secondary=item.get('secondary', ''),
                analysis=item.get('analysis', '')
            )
            unique_points.append(kp)
            
            merged_from = item.get('merged_from', [])
            if merged_from:
                for mid in merged_from:
                    merged_ids.add(mid)
                    if mid in kp_map:
                        dedupe_results.append(DedupeResult(
                            original_point=kp_map[mid].primary,
                            merged_point=kp.primary,
                            similarity_score=0.95,
                            is_merged=True
                        ))
            else:
                dedupe_results.append(DedupeResult(
                    original_point=kp.primary,
                    merged_point=kp.primary,
                    similarity_score=1.0,
                    is_merged=False
                ))
        
        # 获取usage信息（如果有的话）
        usage = None
        
        return unique_points, dedupe_results, usage
        
    except Exception as e:
        # LLM调用失败，回退到传统方法
        agent = HomeworkAgent()
        agent.current_task = task
        unique_points, dedupe_results = agent.dedupe_knowledge_points(0.85)
        return unique_points, dedupe_results, None


@knowledge_agent_bp.route('/api/knowledge-agent/dedupe-stream', methods=['POST'])
def dedupe_knowledge_stream():
    """流式LLM去重 - 支持进度反馈和可视化"""
    data = request.json or {}
    task_id = data.get('task_id')
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = current_tasks.get(task_id) or storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    def generate():
        import re
        
        # 收集所有知识点
        all_kps = []
        kp_map = {}
        
        # 安全处理parsed_questions为None的情况
        parsed_questions = task.parsed_questions or []
        
        for q in parsed_questions:
            for kp in (q.knowledge_points or []):
                if kp.id not in kp_map:
                    all_kps.append({
                        'id': kp.id,
                        'primary': kp.primary,
                        'secondary': kp.secondary,
                        'analysis': kp.analysis
                    })
                    kp_map[kp.id] = kp
        
        total = len(all_kps)
        yield f"data: {json_module.dumps({'type': 'progress', 'message': f'发现 {total} 个知识点，开始智能去重...'})}\n\n"
        
        # 发送原始知识点列表
        yield f"data: {json_module.dumps({'type': 'original_kps', 'knowledge_points': all_kps})}\n\n"
        
        if total <= 1:
            # 只有一个或没有知识点，无需去重
            yield f"data: {json_module.dumps({'type': 'progress', 'message': '知识点数量不足，无需去重'})}\n\n"
            result = [{
                'id': all_kps[0]['id'] if all_kps else '',
                'primary': all_kps[0]['primary'] if all_kps else '',
                'secondary': all_kps[0]['secondary'] if all_kps else '',
                'analysis': all_kps[0]['analysis'] if all_kps else '',
                'merged_from': [],
                'is_kept': True
            }] if all_kps else []
            yield f"data: {json_module.dumps({'type': 'done', 'unique_points': result, 'merge_groups': [], 'original_count': total, 'final_count': len(result)})}\n\n"
            return
        
        # 构建提示词
        kp_text = "\n".join([
            f"- ID: {kp['id']}, 一级知识点: {kp['primary']}, 二级知识点: {kp['secondary']}"
            for kp in all_kps
        ])
        prompt = DEDUPE_PROMPT.replace('{knowledge_points}', kp_text)
        
        # 发送提示词
        yield f"data: {json_module.dumps({'type': 'prompt', 'prompt': prompt})}\n\n"
        
        yield f"data: {json_module.dumps({'type': 'progress', 'message': '正在调用LLM进行语义分析...'})}\n\n"
        
        # 流式调用LLM
        full_response = ""
        total_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        
        try:
            for chunk_data in model_service.call_text_stream('deepseek-v3.2', prompt):
                if isinstance(chunk_data, dict):
                    if chunk_data.get('type') == 'content':
                        full_response += chunk_data['content']
                        yield f"data: {json_module.dumps({'type': 'chunk', 'content': chunk_data['content']})}\n\n"
                    elif chunk_data.get('type') == 'usage':
                        usage = chunk_data['usage']
                        total_usage['prompt_tokens'] = usage.get('prompt_tokens', 0)
                        total_usage['completion_tokens'] = usage.get('completion_tokens', 0)
                        total_usage['total_tokens'] = usage.get('total_tokens', 0)
                else:
                    full_response += chunk_data
                    yield f"data: {json_module.dumps({'type': 'chunk', 'content': chunk_data})}\n\n"
            
            yield f"data: {json_module.dumps({'type': 'progress', 'message': '正在解析去重结果...'})}\n\n"
            
            # 解析响应
            json_match = re.search(r'\[[\s\S]*\]', full_response)
            if not json_match:
                raise Exception("LLM返回格式错误")
            
            result_kps = json_module.loads(json_match.group())
            
            # 构建去重结果和合并组
            unique_points = []
            merge_groups = []
            merged_ids = set()
            
            for item in result_kps:
                merged_from = item.get('merged_from', [])
                
                kp_result = {
                    'id': item.get('id', str(uuid.uuid4())[:8]),
                    'primary': item.get('primary', ''),
                    'secondary': item.get('secondary', ''),
                    'analysis': item.get('analysis', ''),
                    'merged_from': merged_from,
                    'is_kept': True
                }
                unique_points.append(kp_result)
                
                if merged_from:
                    # 创建合并组
                    group = {
                        'target': kp_result,
                        'merged': []
                    }
                    for mid in merged_from:
                        merged_ids.add(mid)
                        if mid in kp_map:
                            group['merged'].append({
                                'id': mid,
                                'primary': kp_map[mid].primary,
                                'secondary': kp_map[mid].secondary,
                                'analysis': kp_map[mid].analysis
                            })
                    if group['merged']:
                        merge_groups.append(group)
            
            # 保存到任务
            dedupe_results = []
            final_unique_points = []
            
            for item in unique_points:
                kp = KnowledgePoint(
                    id=item['id'],
                    primary=item['primary'],
                    secondary=item['secondary'],
                    analysis=item['analysis']
                )
                final_unique_points.append(kp)
                
                if item['merged_from']:
                    for mid in item['merged_from']:
                        if mid in kp_map:
                            dedupe_results.append(DedupeResult(
                                original_point=kp_map[mid].primary,
                                merged_point=item['primary'],
                                similarity_score=0.95,
                                is_merged=True
                            ))
                else:
                    dedupe_results.append(DedupeResult(
                        original_point=item['primary'],
                        merged_point=item['primary'],
                        similarity_score=1.0,
                        is_merged=False
                    ))
            
            task.dedupe_results = dedupe_results
            current_tasks[task_id] = task
            storage_service.save_task(task)
            
            yield f"data: {json_module.dumps({'type': 'usage', 'usage': total_usage})}\n\n"
            yield f"data: {json_module.dumps({'type': 'done', 'unique_points': unique_points, 'merge_groups': merge_groups, 'original_count': total, 'final_count': len(unique_points)})}\n\n"
            
        except Exception as e:
            yield f"data: {json_module.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@knowledge_agent_bp.route('/api/knowledge-agent/dedupe-confirm', methods=['POST'])
def confirm_dedupe():
    """确认去重结果 - 用户可以选择保留某些被合并的知识点"""
    data = request.json or {}
    task_id = data.get('task_id')
    final_points = data.get('final_points', [])  # 用户确认的最终知识点列表
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = current_tasks.get(task_id) or storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    try:
        # 更新去重结果
        dedupe_results = []
        for item in final_points:
            if item.get('is_kept', True):
                dedupe_results.append(DedupeResult(
                    original_point=item.get('primary', ''),
                    merged_point=item.get('primary', ''),
                    similarity_score=1.0,
                    is_merged=False
                ))
        
        task.dedupe_results = dedupe_results
        current_tasks[task_id] = task
        storage_service.save_task(task)
        
        return jsonify({
            'success': True,
            'unique_points': final_points
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 导出Excel ============

@knowledge_agent_bp.route('/api/knowledge-agent/export/<export_type>')
def export_result(export_type):
    """导出结果 - 支持每一步导出"""
    task_id = request.args.get('task_id')
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    task = current_tasks.get(task_id) or storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    try:
        if export_type == 'parse_result':
            filepath = excel_service.export_parse_result(task.parsed_questions)
        elif export_type == 'similar_questions':
            kp_map = {}
            for q in task.parsed_questions:
                for kp in q.knowledge_points:
                    kp_map[kp.id] = kp
            filepath = excel_service.export_similar_questions(task.similar_questions, kp_map)
        elif export_type == 'full_result':
            filepath = excel_service.export_full_result(task.parsed_questions, task.similar_questions)
        elif export_type == 'dedupe_result':
            filepath = excel_service.export_dedupe_result(task.dedupe_results)
        else:
            return jsonify({'success': False, 'error': '无效的导出类型'}), 400
        
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 模型和配置 ============

@knowledge_agent_bp.route('/api/knowledge-agent/models')
def get_models():
    models = model_service.get_available_models()
    preferences = storage_service.load_preferences()
    return jsonify({'success': True, 'models': models, 'preferences': preferences})


@knowledge_agent_bp.route('/api/knowledge-agent/prompts')
def get_prompts():
    from .tools import get_default_prompts
    return jsonify({'success': True, 'prompts': get_default_prompts()})


@knowledge_agent_bp.route('/api/knowledge-agent/task/<task_id>')
def get_task(task_id):
    task = current_tasks.get(task_id) or storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    return jsonify({'success': True, 'task': task.to_dict()})


# ============ 历史任务 ============

@knowledge_agent_bp.route('/api/knowledge-agent/history')
def get_task_history():
    """获取历史任务列表"""
    try:
        task_ids = storage_service.list_tasks()
        tasks = []
        
        for task_id in task_ids[-20:]:  # 最近20个任务
            task = storage_service.load_task(task_id)
            if task:
                tasks.append({
                    'task_id': task.task_id,
                    'status': task.status,
                    'created_at': task.created_at if hasattr(task, 'created_at') else None,
                    'image_count': len(task.images) if task.images else 0,
                    'question_count': len(task.parsed_questions) if task.parsed_questions else 0,
                    'similar_count': len(task.similar_questions) if task.similar_questions else 0,
                    'first_image': task.images[0].filename if task.images else None
                })
        
        # 按时间倒序
        tasks.reverse()
        
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@knowledge_agent_bp.route('/api/knowledge-agent/history/<task_id>')
def load_history_task(task_id):
    """加载历史任务详情"""
    task = storage_service.load_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    # 加载到当前任务
    current_tasks[task_id] = task
    
    # 构建图片预览URL - 使用实际存储的文件名
    images_data = []
    for img in (task.images or []):
        # 从完整路径中提取文件名
        actual_filename = os.path.basename(img.path) if img.path else img.filename
        images_data.append({
            'id': img.id,
            'filename': img.filename,
            'preview_url': f'/api/knowledge-agent/preview/{task_id}/{actual_filename}'
        })
    
    # 构建完整的任务数据
    result = {
        'success': True,
        'task_id': task.task_id,
        'status': task.status,
        'images': images_data,
        'parsed_questions': [q.to_dict() for q in (task.parsed_questions or [])],
        'similar_questions': [sq.to_dict() for sq in (task.similar_questions or [])],
        'unique_points': []
    }
    
    # 提取唯一知识点
    kp_map = {}
    for q in (task.parsed_questions or []):
        for kp in q.knowledge_points:
            if kp.id not in kp_map:
                kp_map[kp.id] = kp.to_dict()
    result['unique_points'] = list(kp_map.values())
    
    return jsonify(result)


@knowledge_agent_bp.route('/api/knowledge-agent/history/<task_id>', methods=['DELETE'])
def delete_history_task(task_id):
    """删除历史任务"""
    try:
        success = storage_service.delete_task(task_id)
        if task_id in current_tasks:
            del current_tasks[task_id]
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 兼容旧API ============

@knowledge_agent_bp.route('/api/knowledge-agent/parse', methods=['POST'])
def parse_images():
    """兼容旧的解析API"""
    return jsonify({'success': True, 'message': '请使用流式API'})


@knowledge_agent_bp.route('/api/knowledge-agent/generate', methods=['POST'])
def generate_similar_questions():
    """兼容旧的生成API"""
    return jsonify({'success': True, 'message': '请使用流式API'})


@knowledge_agent_bp.route('/api/knowledge-agent/edit', methods=['POST'])
def edit_question():
    data = request.json or {}
    task_id = data.get('task_id')
    question_id = data.get('question_id')
    updates = data.get('updates', {})
    
    if not task_id or not question_id:
        return jsonify({'success': False, 'error': '缺少参数'}), 400
    
    success = storage_service.update_similar_question(task_id, question_id, updates)
    
    if success:
        task = storage_service.load_task(task_id)
        if task:
            current_tasks[task_id] = task
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': '更新失败'}), 500


# ============ 校验API ============

VERIFY_PROMPT_DEFAULT = """你是一个专业的数学教育专家和审题专家。请仔细校验以下题目的准确性和解题步骤的合理性。

【待校验题目】
题目内容：{content}
答案：{answer}
解题步骤：{solution_steps}

【校验任务】
1. 检查题目内容是否完整、表述是否清晰
2. 验证答案是否正确
3. 检查解题步骤是否合理、逻辑是否清晰
4. 如有错误或可优化之处，请修正

【输出格式】JSON对象：
{
    "is_correct": true或false,
    "issues": ["发现的问题1", "发现的问题2"],
    "content": "优化后的题目内容",
    "answer": "正确的答案",
    "solution_steps": "优化后的解题步骤（精简、清晰、分步骤）"
}

【重要要求】
1. 解题步骤要精简，每步一行，用数字编号
2. 去除冗余的推导过程，保留关键步骤
3. 确保答案与解题步骤一致
4. 只输出JSON对象，不要任何解释文字"""


@knowledge_agent_bp.route('/api/knowledge-agent/verify-stream', methods=['POST'])
def verify_questions_stream():
    """流式校验类题 - 使用DeepSeek进行推理校验"""
    data = request.json or {}
    task_id = data.get('task_id')
    custom_prompt = data.get('prompt', VERIFY_PROMPT_DEFAULT)
    questions = data.get('questions', [])
    
    if not task_id:
        return jsonify({'success': False, 'error': '缺少task_id'}), 400
    
    def generate():
        import re
        total = len(questions)
        total_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        
        yield f"data: {json_module.dumps({'type': 'progress', 'message': f'开始校验 {total} 道类题...'})}\n\n"
        
        for idx, q in enumerate(questions):
            content = q.get('content', '')
            answer = q.get('answer', '')
            solution_steps = q.get('solution_steps', '')
            
            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'正在校验类题 {idx+1}/{total}'})}\n\n"
            
            # 构建校验提示词
            prompt = (custom_prompt
                     .replace('{content}', content)
                     .replace('{answer}', answer)
                     .replace('{solution_steps}', solution_steps))
            
            try:
                # 使用DeepSeek进行校验（流式输出）
                full_response = ""
                for chunk_data in model_service.call_text_stream('deepseek-v3.2', prompt):
                    if isinstance(chunk_data, dict):
                        if chunk_data.get('type') == 'content':
                            full_response += chunk_data['content']
                            yield f"data: {json_module.dumps({'type': 'chunk', 'content': chunk_data['content'], 'question_idx': idx})}\n\n"
                        elif chunk_data.get('type') == 'usage':
                            usage = chunk_data['usage']
                            total_usage['prompt_tokens'] += usage.get('prompt_tokens', 0)
                            total_usage['completion_tokens'] += usage.get('completion_tokens', 0)
                            total_usage['total_tokens'] += usage.get('total_tokens', 0)
                            yield f"data: {json_module.dumps({'type': 'usage', 'usage': usage, 'question_idx': idx})}\n\n"
                    else:
                        full_response += chunk_data
                        yield f"data: {json_module.dumps({'type': 'chunk', 'content': chunk_data, 'question_idx': idx})}\n\n"
                
                # 解析校验结果
                result = None
                try:
                    obj_match = re.search(r'\{[\s\S]*\}', full_response)
                    if obj_match:
                        result = json_module.loads(obj_match.group())
                except:
                    result = {
                        'is_correct': True,
                        'issues': [],
                        'content': content,
                        'answer': answer,
                        'solution_steps': solution_steps
                    }
                
                yield f"data: {json_module.dumps({'type': 'question_verified', 'question_idx': idx, 'result': result})}\n\n"
                
            except Exception as e:
                yield f"data: {json_module.dumps({'type': 'error', 'question_idx': idx, 'error': str(e)})}\n\n"
        
        yield f"data: {json_module.dumps({'type': 'done', 'total_usage': total_usage})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )
