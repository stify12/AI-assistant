"""
通用路由模块
包含首页、配置、会话管理等通用路由
"""
import uuid
import io
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from services.config_service import ConfigService
from services.session_service import SessionService

common_bp = Blueprint('common', __name__)


# ========== 页面路由 ==========

@common_bp.route('/')
def index():
    return render_template('index.html')


@common_bp.route('/compare')
def compare():
    return render_template('compare.html')


@common_bp.route('/subject-grading')
def subject_grading():
    return render_template('subject-grading.html')


@common_bp.route('/batch-evaluation')
def batch_evaluation():
    return render_template('batch-evaluation.html')


# ========== 配置 API ==========

@common_bp.route('/api/config', methods=['GET', 'POST'])
def config():
    if request.method == 'GET':
        return jsonify(ConfigService.load_config())
    else:
        ConfigService.save_config(request.json)
        return jsonify({'success': True})


# ========== 会话管理 API ==========

@common_bp.route('/api/session', methods=['POST', 'DELETE'])
def session_api():
    """会话管理API"""
    if request.method == 'POST':
        # 创建新会话
        session_id = str(uuid.uuid4())[:8]
        SessionService.save_session(session_id, {'messages': [], 'created_at': datetime.now().isoformat()})
        return jsonify({'session_id': session_id})
    else:
        # 清除会话
        session_id = request.json.get('session_id')
        if session_id:
            SessionService.clear_session(session_id)
        return jsonify({'success': True})


@common_bp.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """获取会话历史"""
    session_data = SessionService.load_session(session_id)
    return jsonify(session_data)


@common_bp.route('/api/all-sessions', methods=['GET'])
def get_all_sessions():
    """获取所有会话列表"""
    sessions = SessionService.get_all_sessions()
    return jsonify(sessions)


@common_bp.route('/api/session/<session_id>/rename', methods=['POST'])
def rename_session(session_id):
    """重命名会话"""
    data = request.json
    new_title = data.get('title', '新对话')
    SessionService.rename_session(session_id, new_title)
    return jsonify({'success': True})


@common_bp.route('/api/session/save-parallel', methods=['POST'])
def save_parallel_result():
    """保存并行处理结果到会话"""
    data = request.json
    session_id = data.get('session_id')
    user_message = data.get('user_message', '')
    has_image = data.get('has_image', False)
    assistant_message = data.get('assistant_message', '')
    model = data.get('model', '')
    
    if not session_id:
        return jsonify({'error': '缺少session_id'}), 400
    
    session_data = SessionService.load_session(session_id)
    
    # 添加用户消息
    user_msg = {'role': 'user', 'content': user_message}
    if has_image:
        user_msg['has_image'] = True
    session_data['messages'].append(user_msg)
    
    # 添加助手消息
    session_data['messages'].append({
        'role': 'assistant',
        'content': assistant_message,
        'model': model
    })
    
    SessionService.save_session(session_id, session_data)
    return jsonify({'success': True})


# ========== 模板下载 ==========

@common_bp.route('/api/download-template')
def download_template():
    """下载批量对比Excel模板 - 模型+批次+JSON数组格式"""
    wb = Workbook()
    ws = wb.active
    ws.title = "批量对比模板"
    
    # 样式
    header_font = Font(bold=True, size=12, color="FFFFFF")
    header_fill = PatternFill(start_color="1D6F8C", end_color="1D6F8C", fill_type="solid")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    center_align = Alignment(horizontal='center', vertical='center')
    left_align = Alignment(horizontal='left', vertical='top', wrap_text=True)
    
    # 表头：模型 | 批次名称 | JSON数组
    headers = ['模型', '批次名称', 'JSON数组（直接粘贴完整JSON）']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = center_align
    
    # 示例JSON数据
    example_json = '''[
  {
    "answer": "",
    "correct": "yes",
    "index": "17",
    "mainAnswer": "①√抬起 ③√朋友",
    "tempIndex": 0,
    "userAnswer": ""
  },
  {
    "answer": "",
    "correct": "yes",
    "index": "18",
    "mainAnswer": "《祖父的园子》，《呼兰河传》",
    "tempIndex": 1,
    "userAnswer": "呼兰河传；生死场"
  },
  {
    "answer": "①",
    "correct": "no",
    "index": "20",
    "mainAnswer": "①",
    "tempIndex": 4,
    "userAnswer": "②"
  }
]'''
    
    # 示例数据
    example_data = [
        ['1.6vision', '批次1', example_json],
        ['1.7vision', '批次2', example_json],
    ]
    for row_idx, row_data in enumerate(example_data, 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = border
            cell.alignment = center_align if col_idx <= 2 else left_align
    
    # 设置列宽
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 80
    
    # 设置行高
    ws.row_dimensions[1].height = 25
    ws.row_dimensions[2].height = 200
    ws.row_dimensions[3].height = 200
    
    # 保存到内存
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='batch_compare_template.xlsx')


# ========== 学科配置 API ==========

@common_bp.route('/api/subjects', methods=['GET', 'POST', 'PUT'])
def subjects_api():
    if request.method == 'GET':
        return jsonify(ConfigService.load_subjects())
    elif request.method == 'POST':
        subjects = ConfigService.load_subjects()
        data = request.json
        subjects[data['id']] = data['config']
        ConfigService.save_subjects(subjects)
        return jsonify({'success': True})
    else:  # PUT
        ConfigService.save_subjects(request.json)
        return jsonify({'success': True})


# ========== 自定义模型配置 API ==========

@common_bp.route('/api/models', methods=['GET', 'POST', 'PUT', 'DELETE'])
def models_api():
    if request.method == 'GET':
        return jsonify(ConfigService.load_custom_models())
    elif request.method == 'POST':
        models = ConfigService.load_custom_models()
        data = request.json
        data['id'] = str(uuid.uuid4())[:8]
        models.append(data)
        ConfigService.save_custom_models(models)
        return jsonify({'success': True, 'id': data['id']})
    elif request.method == 'PUT':
        models = ConfigService.load_custom_models()
        data = request.json
        for i, m in enumerate(models):
            if m['id'] == data['id']:
                models[i] = data
                break
        ConfigService.save_custom_models(models)
        return jsonify({'success': True})
    else:  # DELETE
        models = ConfigService.load_custom_models()
        model_id = request.json.get('id')
        models = [m for m in models if m['id'] != model_id]
        ConfigService.save_custom_models(models)
        return jsonify({'success': True})


# ========== 评估配置 API ==========

@common_bp.route('/api/eval-config', methods=['GET', 'POST'])
def eval_config_api():
    if request.method == 'GET':
        return jsonify(ConfigService.load_eval_config())
    else:
        ConfigService.save_eval_config(request.json)
        return jsonify({'success': True})
