"""
数据集管理路由模块
提供数据集管理页面和相关 API
"""
import re
import json
from flask import Blueprint, request, jsonify, render_template

from services.config_service import ConfigService
from services.database_service import DatabaseService
from services.llm_service import LLMService

dataset_manage_bp = Blueprint('dataset_manage', __name__)


@dataset_manage_bp.route('/dataset-manage')
def dataset_manage_page():
    """数据集管理页面"""
    return render_template('dataset-manage.html')


@dataset_manage_bp.route('/api/dataset/available-homework', methods=['GET'])
def get_dataset_available_homework():
    """获取指定页码的可用作业图片列表"""
    book_id = request.args.get('book_id')
    page_num = request.args.get('page_num', type=int)
    hours = request.args.get('hours', 24, type=int)
    
    if not book_id or page_num is None:
        return jsonify({'success': False, 'error': '缺少必要参数'})
    
    try:
        sql = """
            SELECT h.id, h.student_id, h.pic_path, h.homework_result, h.create_time,
                   s.name AS student_name
            FROM zp_homework h
            LEFT JOIN zp_student s ON h.student_id = s.id
            LEFT JOIN zp_homework_publish p ON h.hw_publish_id = p.id
            WHERE h.status = 3 
              AND p.book_id = %s
              AND h.page_num = %s
              AND h.pic_path IS NOT NULL
              AND h.pic_path != ''
              AND h.create_time >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            ORDER BY h.create_time DESC
            LIMIT 20
        """
        
        rows = DatabaseService.execute_query(sql, (book_id, page_num, hours))
        
        config = ConfigService.load_config()
        pic_base_url = config.get('pic_base_url', '')
        
        homework_list = []
        for row in rows:
            pic_path = row.get('pic_path', '')
            if pic_path.startswith('http'):
                pic_url = pic_path
            else:
                pic_url = f"{pic_base_url}{pic_path}" if pic_path and pic_base_url else ''
            
            question_count = 0
            try:
                homework_result = json.loads(row.get('homework_result', '[]') or '[]')
                question_count = len(homework_result) if isinstance(homework_result, list) else 0
            except:
                pass
            
            homework_list.append({
                'id': str(row['id']),
                'student_id': row.get('student_id', ''),
                'student_name': row.get('student_name', ''),
                'pic_path': pic_path,
                'pic_url': pic_url,
                'question_count': question_count,
                'create_time': row['create_time'].isoformat() if row.get('create_time') else None
            })
        
        return jsonify({'success': True, 'data': homework_list})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def build_dynamic_prompt(data_value_items, subject_id=0):
    """
    根据 data_value 构建动态提示词
    
    Args:
        data_value_items: 从 zp_homework.data_value 解析的题目列表
        subject_id: 学科ID
        
    Returns:
        动态提示词字符串
    """
    # 题目类型映射
    bvalue_map = {
        '1': '单选题',
        '2': '多选题', 
        '3': '判断题',
        '4': '填空题',
        '5': '解答题'
    }
    
    # 学科名称映射
    subject_map = {
        0: '英语',
        1: '语文',
        2: '数学',
        3: '物理',
        4: '化学',
        5: '生物'
    }
    subject_name = subject_map.get(subject_id, '通用')
    
    # 构建题目信息数组
    questions_info = []
    for item in data_value_items:
        content = item.get('content', '')
        # content 取前15个字符
        content_short = content[:15] if content else ''
        
        questions_info.append({
            'index': item.get('index', ''),
            'tempIndex': item.get('tempIndex', 0),
            'answer': item.get('jans', '').strip(),  # 标准答案，去除首尾空格
            'type': bvalue_map.get(str(item.get('bvalue', '4')), '填空题'),
            'questionType': item.get('questionType', 'objective'),
            'content': content_short
        })
    
    # 构建动态提示词
    questions_json = json.dumps(questions_info, ensure_ascii=False, indent=2)
    
    prompt = f"""你是一个专业的{subject_name}作业批改助手。请仔细识别图片中学生的手写答案。

【题目信息】
{questions_json}

【识别要求】
1. 按照上述题目顺序，逐题识别学生在图片中写的答案
2. 识别时注意：
   - 仔细辨认手写字迹，注意区分相似字母（如n/r, a/o, u/v等）
   - 对于英语单词，确保拼写完整准确
   - 对于选择题，只识别选项字母（A/B/C/D/E/F/G/H）
   - 忽略涂改痕迹，以最终答案为准
3. 将学生答案与标准答案(answer字段)对比，判断是否正确
4. 判断正确的标准：
   - 选择题：选项字母完全一致（不区分大小写）
   - 填空题：答案内容一致（忽略首尾空格，不区分大小写）
   - 对于英语单词，拼写必须完全正确

【输出格式】
返回JSON数组，每个元素包含：
- index: 题号（与上述题目信息一致）
- tempIndex: 临时索引（与上述题目信息一致）
- userAnswer: 学生的答案（识别结果，保持原始格式）
- answer: 标准答案（直接使用上述题目信息中的answer）
- correct: 判断结果，"yes"表示正确，"no"表示错误

【输出示例】
```json
[
  {{"index": "31", "tempIndex": 0, "userAnswer": "A", "answer": "C", "correct": "no"}},
  {{"index": "32", "tempIndex": 1, "userAnswer": "stopped", "answer": "stopped", "correct": "yes"}}
]
```

请直接输出JSON数组，不要添加其他说明文字。"""
    
    return prompt


@dataset_manage_bp.route('/api/dataset/recognize', methods=['POST'])
def dataset_recognize():
    """识别作业图片的基准效果 - 使用动态提示词"""
    data = request.json
    homework_id = data.get('homework_id')
    pic_path = data.get('pic_path', '')
    subject_id = data.get('subject_id', 0)
    
    if not homework_id and not pic_path:
        return jsonify({'success': False, 'error': '缺少作业ID或图片路径'})
    
    config = ConfigService.load_config()
    
    try:
        # 从数据库获取作业信息，包括 data_value
        homework_row = None
        if homework_id:
            homework_row = DatabaseService.execute_one(
                "SELECT pic_path, data_value FROM zp_homework WHERE id = %s",
                (homework_id,)
            )
            if homework_row:
                if not pic_path:
                    pic_path = homework_row.get('pic_path', '')
        
        if not pic_path:
            return jsonify({'success': False, 'error': '未找到作业图片'})
        
        # 构建图片URL
        if pic_path.startswith('http'):
            pic_url = pic_path
        else:
            pic_base_url = config.get('pic_base_url', '')
            pic_url = f"{pic_base_url}{pic_path}" if pic_path else ''
        
        if not pic_url:
            return jsonify({'success': False, 'error': '无法获取图片URL'})
        
        # 解析 data_value 构建动态提示词
        data_value_items = []
        if homework_row and homework_row.get('data_value'):
            try:
                data_value_items = json.loads(homework_row.get('data_value', '[]'))
            except json.JSONDecodeError:
                pass
        
        # 根据是否有 data_value 选择提示词
        if data_value_items:
            # 使用动态提示词
            prompt = build_dynamic_prompt(data_value_items, subject_id)
        else:
            # 回退到静态提示词
            prompts_config = config.get('prompts', {})
            subject_prompt_map = {
                0: 'recognize_english',
                1: 'recognize_chinese',
                2: 'recognize_math',
                3: 'recognize_physics',
            }
            prompt_key = subject_prompt_map.get(subject_id, 'recognize')
            prompt = prompts_config.get(prompt_key, prompts_config.get('recognize', '请识别图片中作业的每道题答案。'))
        
        # 调用视觉模型
        result = LLMService.call_vision_model(pic_url, prompt, 'doubao-seed-1-8-251228')
        
        if result.get('error'):
            return jsonify({'success': False, 'error': result['error']})
        
        # 提取JSON数组
        base_effect = LLMService.extract_json_array(result.get('content', ''))
        if base_effect:
            # 转换字段格式，保持与 homework_result 一致
            formatted_data = []
            for item in base_effect:
                correct_val = item.get('correct', 'no')
                if isinstance(correct_val, bool):
                    correct_val = 'yes' if correct_val else 'no'
                
                # 标准化答案处理
                user_answer = str(item.get('userAnswer', '')).strip()
                answer = str(item.get('answer', '')).strip()
                
                formatted_data.append({
                    'index': str(item.get('index', '')),
                    'tempIndex': item.get('tempIndex', 0),
                    'userAnswer': user_answer,
                    'answer': answer,
                    'correct': correct_val,
                    'type': 'choice'
                })
            
            return jsonify({'success': True, 'data': formatted_data})
        else:
            return jsonify({'success': False, 'error': '无法解析识别结果', 'raw': result.get('content', '')})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
