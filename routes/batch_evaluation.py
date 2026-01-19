"""
批量评估任务路由模块
提供批量评估任务管理、数据集管理和评估执行功能
"""
import os
import io
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, Response, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side

from services.config_service import ConfigService
from services.database_service import DatabaseService, AppDatabaseService
from services.storage_service import StorageService
from services.llm_service import LLMService
from services.semantic_eval_service import SemanticEvalService
from utils.text_utils import normalize_answer, has_format_diff

batch_evaluation_bp = Blueprint('batch_evaluation', __name__)

DATASETS_DIR = 'datasets'
BATCH_TASKS_DIR = 'batch_tasks'


# ========== 辅助函数 ==========

def normalize_index(index_str):
    """
    标准化题号，统一中英文符号
    - 中文括号 （） -> 英文括号 ()
    - 中文逗号 ， -> 英文逗号 ,
    - 中文句号 。 -> 英文句号 .
    - 去除多余空格
    
    Args:
        index_str: 原始题号字符串
        
    Returns:
        标准化后的题号字符串
    """
    if not index_str:
        return ''
    s = str(index_str)
    # 中文括号转英文
    s = s.replace('（', '(').replace('）', ')')
    # 中文标点转英文
    s = s.replace('，', ',').replace('。', '.').replace('：', ':')
    # 去除空格
    s = s.replace(' ', '')
    return s


def flatten_homework_result(homework_result):
    """
    展开 homework_result 中的嵌套 children 结构为扁平数组
    
    Args:
        homework_result: AI批改结果列表（可能包含children嵌套结构）
        
    Returns:
        扁平化后的题目列表，每个小题一条记录
    """
    if not homework_result:
        return []
    
    flattened = []
    for item in homework_result:
        children = item.get('children', [])
        if children and len(children) > 0:
            # 有子题时，只取子题（父题是汇总，不参与匹配）
            for child in children:
                flattened.append(child)
        else:
            # 无子题，直接加入
            flattened.append(item)
    return flattened


def get_correct_value(item):
    """
    获取判断结果字段值，兼容多种格式：
    - correct: "yes"/"no" 字符串
    - isRight: true/false 布尔值
    - isCorrect: true/false 布尔值
    统一返回 "yes" 或 "no" 字符串
    """
    if not item:
        return ''
    
    # 优先检查 correct 字段
    if 'correct' in item:
        val = item['correct']
        if isinstance(val, bool):
            return 'yes' if val else 'no'
        if isinstance(val, str):
            val_lower = val.lower().strip()
            if val_lower in ('yes', 'true', '1'):
                return 'yes'
            elif val_lower in ('no', 'false', '0'):
                return 'no'
            return val_lower
    
    # 检查 isRight 字段
    if 'isRight' in item:
        val = item['isRight']
        if isinstance(val, bool):
            return 'yes' if val else 'no'
        if isinstance(val, str):
            return 'yes' if val.lower() in ('true', 'yes', '1') else 'no'
    
    # 检查 isCorrect 字段
    if 'isCorrect' in item:
        val = item['isCorrect']
        if isinstance(val, bool):
            return 'yes' if val else 'no'
        if isinstance(val, str):
            return 'yes' if val.lower() in ('true', 'yes', '1') else 'no'
    
    return ''


def classify_question_type(question_data):
    """
    根据题目数据判断题目类型
    
    支持多种数据格式：
    1. questionType + bvalue 格式（数据库原始格式）
       - bvalue: 1=单选, 2=多选, 3=判断, 4=填空, 5=解答
    2. type 字段格式（数据集格式）
       - type: "choice" 表示客观题（需要批改的题目）
    3. 根据答案内容智能判断选择题（单个字母A-H视为选择题）
    
    Args:
        question_data: 题目数据
        
    Returns:
        {
            "is_objective": bool,  # 是否客观题
            "is_choice": bool,     # 是否选择题
            "is_fill": bool,       # 是否填空题 (bvalue=4)
            "choice_type": str     # "single" | "multiple" | None
        }
    """
    if not question_data:
        return {
            'is_objective': False,
            'is_choice': False,
            'is_fill': False,
            'choice_type': None
        }
    
    # 方式1：检查 questionType 和 bvalue 字段（数据库原始格式）
    question_type = question_data.get('questionType', '')
    bvalue = str(question_data.get('bvalue', ''))
    
    # 方式2：检查 type 字段（数据集格式）
    # type: "choice" 在数据集中表示客观题（需要批改的题目），不是选择题
    type_field = question_data.get('type', '')
    
    # 判断是否为填空题 (bvalue=4)
    is_fill = bvalue == '4'
    
    # 判断是否为选择题
    is_choice = False
    choice_type = None
    
    # 优先使用 bvalue 判断（最可靠）
    # bvalue: 1=单选, 2=多选, 3=判断, 4=填空, 5=解答
    if bvalue in ('1', '2'):
        is_choice = True
        choice_type = 'single' if bvalue == '1' else 'multiple'
    else:
        # 方式3：根据答案内容智能判断选择题
        # 只有当答案是单个或多个大写字母A-H时才视为选择题
        answer = str(question_data.get('answer', '') or question_data.get('mainAnswer', '')).strip().upper()
        user_answer = str(question_data.get('userAnswer', '')).strip().upper()
        
        # 检查答案是否为选择题格式（单个字母A-H，或多个字母如AB、ABC）
        def is_choice_answer(ans):
            if not ans:
                return False, None
            # 去除空格
            ans_clean = ans.replace(' ', '')
            # 检查是否全部是A-H的字母，且长度不超过4（避免误判）
            if ans_clean and len(ans_clean) <= 4 and all(c in 'ABCDEFGH' for c in ans_clean):
                if len(ans_clean) == 1:
                    return True, 'single'
                else:
                    return True, 'multiple'
            return False, None
        
        # 优先检查标准答案，其次检查用户答案
        is_choice_ans, choice_type_ans = is_choice_answer(answer)
        if is_choice_ans:
            is_choice = True
            choice_type = choice_type_ans
        else:
            is_choice_user, choice_type_user = is_choice_answer(user_answer)
            if is_choice_user:
                is_choice = True
                choice_type = choice_type_user
    
    # 判断是否为客观题
    # 客观题条件（满足任一即可）：
    # 1. questionType === "objective"
    # 2. bvalue 为 1/2/3/4（选择/判断/填空）
    # 3. type === "choice"（数据集格式，表示客观题）
    # 4. 是选择题
    is_objective = (
        question_type == 'objective' or 
        bvalue in ('1', '2', '3', '4') or 
        type_field == 'choice' or
        is_choice
    )
    
    return {
        'is_objective': is_objective,
        'is_choice': is_choice,
        'is_fill': is_fill,
        'choice_type': choice_type
    }


def calculate_type_statistics(questions, results):
    """
    计算按题目类型分类的统计数据
    
    Args:
        questions: 题目列表（包含 questionType 和 bvalue）
        results: 评估结果列表（包含 is_correct）
        
    Returns:
        {
            "objective": {"total": int, "correct": int, "accuracy": float},
            "subjective": {"total": int, "correct": int, "accuracy": float},
            "choice": {"total": int, "correct": int, "accuracy": float},
            "non_choice": {"total": int, "correct": int, "accuracy": float}
        }
    """
    stats = {
        'objective': {'total': 0, 'correct': 0, 'accuracy': 0},
        'subjective': {'total': 0, 'correct': 0, 'accuracy': 0},
        'choice': {'total': 0, 'correct': 0, 'accuracy': 0},
        'non_choice': {'total': 0, 'correct': 0, 'accuracy': 0}
    }
    
    for i, q in enumerate(questions):
        category = classify_question_type(q)
        is_correct = results[i].get('is_correct', False) if i < len(results) else False
        
        # 主观/客观分类
        if category['is_objective']:
            stats['objective']['total'] += 1
            if is_correct:
                stats['objective']['correct'] += 1
        else:
            stats['subjective']['total'] += 1
            if is_correct:
                stats['subjective']['correct'] += 1
        
        # 选择/非选择分类
        if category['is_choice']:
            stats['choice']['total'] += 1
            if is_correct:
                stats['choice']['correct'] += 1
        else:
            stats['non_choice']['total'] += 1
            if is_correct:
                stats['non_choice']['correct'] += 1
    
    # 计算准确率
    for key in stats:
        total = stats[key]['total']
        correct = stats[key]['correct']
        stats[key]['accuracy'] = correct / total if total > 0 else 0
    
    return stats


def enrich_base_effects_with_question_types(book_id, base_effects):
    """
    为基准效果数据自动添加题目类型信息
    从 zp_homework.data_value 中读取 questionType 和 bvalue 字段
    
    Args:
        book_id: 书本ID
        base_effects: 基准效果数据 {page_num: [questions]}
        
    Returns:
        添加了题目类型信息的基准效果数据
    """
    if not base_effects:
        return base_effects
    
    enriched_effects = {}
    
    for page_num, questions in base_effects.items():
        # 查询该书本页码最近的作业数据
        try:
            sql = """
                SELECT h.data_value
                FROM zp_homework h
                LEFT JOIN zp_homework_publish p ON h.hw_publish_id = p.id
                WHERE p.book_id = %s AND h.page_num = %s AND h.status = 3
                AND h.data_value IS NOT NULL AND h.data_value != ''
                ORDER BY h.create_time DESC
                LIMIT 1
            """
            rows = DatabaseService.execute_query(sql, (book_id, int(page_num)))
            
            # 解析题目类型信息
            type_map = {}
            if rows:
                data_value = rows[0].get('data_value', '[]')
                try:
                    data_items = json.loads(data_value) if data_value else []
                    for item in data_items:
                        temp_idx = item.get('tempIndex', 0)
                        idx = str(item.get('index', ''))
                        type_info = {
                            'questionType': item.get('questionType', ''),
                            'bvalue': str(item.get('bvalue', ''))
                        }
                        type_map[temp_idx] = type_info
                        type_map[f'idx_{idx}'] = type_info
                except json.JSONDecodeError:
                    pass
            
            # 为每个题目添加类型信息
            enriched_questions = []
            for i, q in enumerate(questions):
                enriched = dict(q)
                temp_idx = q.get('tempIndex', i)
                idx = str(q.get('index', ''))
                
                # 优先按tempIndex匹配，其次按index匹配
                type_info = type_map.get(temp_idx) or type_map.get(f'idx_{idx}')
                
                if type_info:
                    enriched['questionType'] = type_info.get('questionType', '')
                    enriched['bvalue'] = type_info.get('bvalue', '')
                else:
                    # 智能判断：根据答案内容判断是否为选择题
                    answer = str(q.get('answer', '') or q.get('mainAnswer', '')).strip().upper()
                    user_answer = str(q.get('userAnswer', '')).strip().upper()
                    
                    # 检查是否为选择题答案（单个字母A-H）
                    def is_choice_answer(ans):
                        if not ans:
                            return False
                        ans_clean = ans.replace(' ', '')
                        return ans_clean and len(ans_clean) <= 4 and all(c in 'ABCDEFGH' for c in ans_clean)
                    
                    if is_choice_answer(answer) or is_choice_answer(user_answer):
                        enriched['questionType'] = 'objective'
                        enriched['bvalue'] = '1'  # 单选题
                    else:
                        # 默认设置为客观题填空题
                        enriched['questionType'] = 'objective'
                        enriched['bvalue'] = '4'  # 填空题
                
                # 移除旧的 type 字段（如果存在）
                if 'type' in enriched:
                    del enriched['type']
                
                enriched_questions.append(enriched)
            
            enriched_effects[page_num] = enriched_questions
            
        except Exception as e:
            # 如果查询失败，保留原始数据
            print(f"获取页码 {page_num} 的题目类型信息失败: {e}")
            enriched_effects[page_num] = questions
    
    return enriched_effects


def classify_error(base_item, hw_item):
    """
    详细的错误分类逻辑
    返回: (is_match, error_type, explanation, severity)
    """
    idx = str(base_item.get('index', ''))
    
    # 基准效果的标准答案：优先取 answer，没有则取 mainAnswer
    base_answer = str(base_item.get('answer', '') or base_item.get('mainAnswer', '')).strip()
    base_user = str(base_item.get('userAnswer', '')).strip()
    base_correct = get_correct_value(base_item)
    
    # AI批改结果
    hw_answer = str(hw_item.get('answer', '') or hw_item.get('mainAnswer', '')).strip() if hw_item else ''
    hw_user = str(hw_item.get('userAnswer', '')).strip() if hw_item else ''
    hw_correct = get_correct_value(hw_item) if hw_item else ''
    
    is_match = True
    error_type = None
    explanation = ''
    severity = 'medium'
    
    if not hw_item:
        is_match = False
        error_type = '缺失题目'
        explanation = f'AI批改结果中缺少第{idx}题'
        severity = 'high'
    elif not base_correct:
        # 基准效果缺少correct字段，只能比较userAnswer
        norm_base_user = normalize_answer(base_user)
        norm_hw_user = normalize_answer(hw_user)
        
        if norm_base_user == norm_hw_user:
            is_match = True
            explanation = '用户答案识别一致（基准效果缺少判断结果）'
        else:
            is_match = False
            error_type = '识别错误-判断错误'
            explanation = f'用户答案不一致：基准="{base_user}"，AI="{hw_user}"'
            severity = 'high'
    else:
        # 标准化答案进行比较
        norm_base_user = normalize_answer(base_user)
        norm_hw_user = normalize_answer(hw_user)
        norm_base_answer = normalize_answer(base_answer)
        
        user_match = norm_base_user == norm_hw_user
        correct_match = base_correct == hw_correct
        
        # 检测AI识别幻觉：学生答错了 + AI识别的用户答案≠基准用户答案 + AI识别的用户答案=标准答案
        # 即AI把学生的错误手写答案"脑补"成了标准答案
        if base_correct == 'no' and not user_match and norm_hw_user == norm_base_answer:
            is_match = False
            error_type = 'AI识别幻觉'
            explanation = f'AI将学生答案"{base_user}"识别为"{hw_user}"（标准答案），属于识别幻觉'
            severity = 'high'
        elif user_match and correct_match:
            is_match = True
        elif user_match and not correct_match:
            # 用户答案识别正确，但判断结果不同
            # 这是"识别正确-判断错误"，格式差异只是次要问题
            is_match = False
            error_type = '识别正确-判断错误'
            if has_format_diff(base_user, hw_user):
                explanation = f'识别正确（有格式差异）但判断错误：基准={base_correct}，AI={hw_correct}'
            else:
                explanation = f'识别正确但判断错误：基准={base_correct}，AI={hw_correct}'
            severity = 'high'
        elif not user_match and correct_match:
            is_match = False
            error_type = '识别错误-判断正确'
            explanation = f'识别不准确但判断结果正确：基准="{base_user}"，AI="{hw_user}"'
            severity = 'medium'
        else:
            is_match = False
            error_type = '识别错误-判断错误'
            explanation = f'识别和判断都有误：基准="{base_user}/{base_correct}"，AI="{hw_user}/{hw_correct}"'
            severity = 'high'
    
    return is_match, error_type, explanation, severity


# ========== 测试条件 API ==========

@batch_evaluation_bp.route('/test-conditions', methods=['GET'])
def get_test_conditions():
    """获取测试条件列表"""
    try:
        sql = "SELECT id, name, description, is_system FROM test_conditions ORDER BY is_system DESC, id ASC"
        rows = AppDatabaseService.execute_query(sql)
        return jsonify({'success': True, 'data': rows or []})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@batch_evaluation_bp.route('/test-conditions', methods=['POST'])
def create_test_condition():
    """创建自定义测试条件"""
    data = request.json
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'success': False, 'error': '测试条件名称不能为空'})
    
    try:
        # 检查是否已存在
        check_sql = "SELECT id FROM test_conditions WHERE name = %s"
        existing = AppDatabaseService.execute_query(check_sql, (name,))
        if existing:
            return jsonify({'success': False, 'error': '该测试条件已存在'})
        
        # 插入新条件
        insert_sql = "INSERT INTO test_conditions (name, description, is_system) VALUES (%s, %s, 0)"
        new_id = AppDatabaseService.execute_insert(insert_sql, (name, data.get('description', '')))
        
        return jsonify({'success': True, 'data': {'id': new_id, 'name': name}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ========== 图书和页码 API ==========

@batch_evaluation_bp.route('/books', methods=['GET'])
def get_books():
    """获取图书列表"""
    subject_id = request.args.get('subject_id', type=int)
    
    try:
        sql = """
            SELECT DISTINCT b.id as book_id, b.book_name as book_name, b.subject_id,
                   COUNT(DISTINCT c.page_num) as page_count
            FROM zp_make_book b
            LEFT JOIN zp_book_chapter c ON b.id = c.book_id
            WHERE 1=1
        """
        params = []
        if subject_id is not None:
            sql += " AND b.subject_id = %s"
            params.append(subject_id)
        sql += " GROUP BY b.id, b.book_name, b.subject_id ORDER BY b.subject_id, b.book_name"
        
        rows = DatabaseService.execute_query(sql, tuple(params) if params else None)
        
        result = {}
        for row in rows:
            sid = str(row['subject_id'])
            if sid not in result:
                result[sid] = []
            result[sid].append({
                'book_id': str(row['book_id']),
                'book_name': row['book_name'] or '未知书本',
                'subject_id': row['subject_id'],
                'page_count': row['page_count'] or 0
            })
        
        return jsonify({'success': True, 'data': result})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@batch_evaluation_bp.route('/books/<book_id>/pages', methods=['GET'])
def get_book_pages(book_id):
    """获取书本页码列表"""
    try:
        sql = """
            SELECT DISTINCT c.page_num
            FROM zp_book_chapter c
            WHERE c.book_id = %s AND c.page_num IS NOT NULL
            ORDER BY c.page_num
        """
        rows = DatabaseService.execute_query(sql, (book_id,))
        
        all_pages = sorted(set(row['page_num'] for row in rows if row['page_num']))
        
        return jsonify({
            'success': True,
            'data': {
                'book_id': book_id,
                'all_pages': all_pages,
                'chapters': []
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ========== 数据集管理 API ==========

@batch_evaluation_bp.route('/datasets/all-books', methods=['GET'])
def get_all_books_with_datasets():
    """获取所有有数据集的书本概览 - 优化版本"""
    try:
        # 使用摘要方法，避免加载完整数据
        all_datasets = StorageService.get_all_datasets_summary()
        
        # 按书本分组统计
        books_map = {}
        book_ids_need_info = []
        
        for data in all_datasets:
            book_id = data.get('book_id')
            if not book_id:
                continue
            
            if book_id not in books_map:
                books_map[book_id] = {
                    'book_id': book_id,
                    'book_name': data.get('book_name', ''),
                    'subject_id': data.get('subject_id'),
                    'dataset_count': 0,
                    'question_count': 0,
                    'pages': set()
                }
                # 记录需要查询的book_id
                if not data.get('book_name'):
                    book_ids_need_info.append(book_id)
            
            books_map[book_id]['dataset_count'] += 1
            books_map[book_id]['question_count'] += data.get('question_count', 0)
            
            # 收集页码
            for page in data.get('pages', []):
                books_map[book_id]['pages'].add(page)
        
        # 批量查询数据库获取书本名称和学科信息
        if book_ids_need_info:
            try:
                placeholders = ','.join(['%s'] * len(book_ids_need_info))
                sql = f"SELECT id, book_name, subject_id FROM zp_make_book WHERE id IN ({placeholders})"
                rows = DatabaseService.execute_query(sql, tuple(book_ids_need_info))
                
                # 构建查询结果映射
                book_info_map = {row['id']: row for row in rows}
                
                # 更新书本信息
                for book_id in book_ids_need_info:
                    book_info = books_map.get(book_id)
                    if book_info:
                        db_info = book_info_map.get(book_id)
                        if db_info:
                            book_info['book_name'] = db_info.get('book_name', '') or f'书本 {book_id[-6:]}'
                            if book_info['subject_id'] is None:
                                book_info['subject_id'] = db_info.get('subject_id', 0)
                        else:
                            book_info['book_name'] = f'书本 {book_id[-6:]}'
            except Exception as e:
                print(f"[AllBooks] Batch query error: {e}")
                for book_id in book_ids_need_info:
                    if books_map.get(book_id) and not books_map[book_id]['book_name']:
                        books_map[book_id]['book_name'] = f'书本 {book_id[-6:]}'
        
        # 转换为列表
        result = []
        for book in books_map.values():
            book['pages'] = sorted(list(book['pages']))
            if book['subject_id'] is None:
                book['subject_id'] = 0
            if not book['book_name']:
                book['book_name'] = f"书本 {book['book_id'][-6:]}"
            result.append(book)
        
        # 按数据集数量排序
        result.sort(key=lambda x: x['dataset_count'], reverse=True)
        
        return jsonify({'success': True, 'data': result})
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@batch_evaluation_bp.route('/datasets', methods=['GET', 'POST'])
def batch_datasets():
    """数据集管理"""
    StorageService.ensure_dir(DATASETS_DIR)
    
    if request.method == 'GET':
        book_id = request.args.get('book_id')
        
        try:
            datasets = []
            for filename in StorageService.list_datasets():
                dataset_id = filename[:-5]
                data = StorageService.load_dataset(dataset_id)
                if data:
                    if book_id and data.get('book_id') != book_id:
                        continue
                    
                    question_count = 0
                    for effects in data.get('base_effects', {}).values():
                        question_count += len(effects) if isinstance(effects, list) else 0
                    
                    datasets.append({
                        'dataset_id': dataset_id,
                        'book_id': data.get('book_id'),
                        'book_name': data.get('book_name', ''),
                        'pages': data.get('pages', []),
                        'question_count': question_count,
                        'created_at': data.get('created_at', '')
                    })
            
            datasets.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return jsonify({'success': True, 'data': datasets})
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    else:  # POST
        data = request.json
        print(f"[CreateDataset] Received request: book_id={data.get('book_id') if data else None}")
        
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'})
        
        book_id = data.get('book_id')
        pages = data.get('pages', [])
        base_effects = data.get('base_effects', {})
        
        if not book_id or not pages:
            return jsonify({'success': False, 'error': '缺少必要参数'})
        
        try:
            dataset_id = str(uuid.uuid4())[:8]
            print(f"[CreateDataset] Creating dataset: {dataset_id}, pages={pages}")
            
            # 为每个页码的题目添加类型信息
            enriched_base_effects = enrich_base_effects_with_question_types(book_id, base_effects)
            
            StorageService.save_dataset(dataset_id, {
                'dataset_id': dataset_id,
                'book_id': book_id,
                'pages': pages,
                'base_effects': enriched_base_effects,
                'created_at': datetime.now().isoformat()
            })
            
            print(f"[CreateDataset] Dataset saved successfully: {dataset_id}")
            return jsonify({'success': True, 'dataset_id': dataset_id})
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[CreateDataset] Error: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})


@batch_evaluation_bp.route('/datasets/<dataset_id>', methods=['GET', 'DELETE', 'PUT'])
def dataset_detail(dataset_id):
    """获取、删除或更新数据集"""
    if request.method == 'DELETE':
        try:
            StorageService.delete_dataset(dataset_id)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    elif request.method == 'PUT':
        try:
            data = StorageService.load_dataset(dataset_id)
            if not data:
                return jsonify({'success': False, 'error': '数据集不存在'})
            
            update_data = request.get_json()
            
            # 更新页码列表
            if 'pages' in update_data:
                # 合并新旧页码，去重并排序
                existing_pages = set(int(p) for p in data.get('pages', []))
                new_pages = set(int(p) for p in update_data['pages'])
                merged_pages = sorted(existing_pages | new_pages)
                data['pages'] = merged_pages
            
            if 'base_effects' in update_data:
                # 合并基准效果，而不是完全覆盖
                existing_effects = data.get('base_effects', {})
                new_effects = update_data['base_effects']
                
                # 只对实际变化的页码执行 enrich 操作（优化性能）
                book_id = data.get('book_id')
                changed_pages = {}
                for page_key, effects in new_effects.items():
                    page_str = str(page_key)
                    # 检查是否有实际变化
                    existing = existing_effects.get(page_str, [])
                    if effects != existing:
                        changed_pages[page_str] = effects
                
                # 只对变化的页码执行 enrich（避免大量数据库查询）
                if changed_pages:
                    enriched_changed = enrich_base_effects_with_question_types(book_id, changed_pages)
                    for page_key, effects in enriched_changed.items():
                        existing_effects[str(page_key)] = effects
                
                data['base_effects'] = existing_effects
                
                # 更新页码列表（确保包含所有有基准效果的页码）
                all_pages = set(int(p) for p in existing_effects.keys())
                if 'pages' in data:
                    all_pages |= set(int(p) for p in data['pages'])
                data['pages'] = sorted(all_pages)
                
                # 更新题目数量
                question_count = 0
                for page_data in data['base_effects'].values():
                    if isinstance(page_data, list):
                        question_count += len(page_data)
                data['question_count'] = question_count
            
            data['updated_at'] = datetime.now().isoformat()
            StorageService.save_dataset(dataset_id, data)
            
            print(f"[UpdateDataset] Updated dataset {dataset_id}, pages={data.get('pages')}")
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)})
    
    else:  # GET
        try:
            data = StorageService.load_dataset(dataset_id)
            if not data:
                return jsonify({'success': False, 'error': '数据集不存在'})
            
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})


@batch_evaluation_bp.route('/datasets/question-types/<homework_id>', methods=['GET'])
def get_homework_question_types(homework_id):
    """
    获取指定作业的题目类型信息
    从 zp_homework.data_value 中解析 questionType 和 bvalue 字段
    """
    try:
        sql = """
            SELECT h.id, h.data_value, h.book_id, h.page_num
            FROM zp_homework h
            WHERE h.id = %s
        """
        rows = DatabaseService.execute_query(sql, (homework_id,))
        
        if not rows:
            return jsonify({'success': False, 'error': '作业不存在'})
        
        row = rows[0]
        data_value = row.get('data_value', '[]')
        
        question_types = []
        try:
            data_items = json.loads(data_value) if data_value else []
            for item in data_items:
                question_types.append({
                    'index': str(item.get('index', '')),
                    'tempIndex': item.get('tempIndex', 0),
                    'questionType': item.get('questionType', ''),
                    'bvalue': str(item.get('bvalue', ''))
                })
        except json.JSONDecodeError:
            pass
        
        return jsonify({
            'success': True,
            'data': {
                'homework_id': homework_id,
                'book_id': row.get('book_id'),
                'page_num': row.get('page_num'),
                'question_types': question_types
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@batch_evaluation_bp.route('/datasets/enrich-base-effects', methods=['POST'])
def enrich_base_effects_with_types():
    """
    为基准效果数据添加题目类型信息
    从 zp_homework.data_value 中读取 questionType 和 bvalue 字段
    """
    try:
        data = request.get_json()
        book_id = data.get('book_id')
        page_num = data.get('page_num')
        base_effects = data.get('base_effects', [])
        
        if not book_id or not page_num:
            return jsonify({'success': False, 'error': '缺少必要参数'})
        
        # 查询该书本页码最近的作业数据
        sql = """
            SELECT h.data_value
            FROM zp_homework h
            LEFT JOIN zp_homework_publish p ON h.hw_publish_id = p.id
            WHERE p.book_id = %s AND h.page_num = %s AND h.status = 3
            ORDER BY h.create_time DESC
            LIMIT 1
        """
        rows = DatabaseService.execute_query(sql, (book_id, page_num))
        
        if not rows:
            # 没有找到对应的作业数据，返回原始基准效果
            return jsonify({'success': True, 'data': base_effects})
        
        data_value = rows[0].get('data_value', '[]')
        
        # 解析题目类型信息
        type_map = {}
        try:
            data_items = json.loads(data_value) if data_value else []
            for item in data_items:
                idx = str(item.get('index', ''))
                temp_idx = item.get('tempIndex', 0)
                type_map[idx] = {
                    'questionType': item.get('questionType', ''),
                    'bvalue': str(item.get('bvalue', ''))
                }
                # 也按tempIndex建立索引
                type_map[f'temp_{temp_idx}'] = type_map[idx]
        except json.JSONDecodeError:
            pass
        
        # 为基准效果添加题目类型信息
        enriched_effects = []
        for i, effect in enumerate(base_effects):
            enriched = dict(effect)
            idx = str(effect.get('index', ''))
            temp_idx = effect.get('tempIndex', i)
            
            # 优先按index匹配，其次按tempIndex匹配
            type_info = type_map.get(idx) or type_map.get(f'temp_{temp_idx}') or {}
            enriched['questionType'] = type_info.get('questionType', '')
            enriched['bvalue'] = type_info.get('bvalue', '')
            enriched_effects.append(enriched)
        
        return jsonify({'success': True, 'data': enriched_effects})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ========== 批量任务管理 API ==========

@batch_evaluation_bp.route('/homework-tasks', methods=['GET'])
def get_homework_tasks():
    """获取作业任务列表（按hw_publish_id分组）"""
    subject_id = request.args.get('subject_id', type=int)
    hours = request.args.get('hours', 6, type=int)  # 默认6小时
    
    try:
        # 添加超时保护，限制查询时间范围
        if hours > 720:  # 最多30天
            hours = 720
        
        sql = """
            SELECT p.id AS hw_publish_id, p.content AS task_name, 
                   COUNT(h.id) AS homework_count,
                   MAX(h.create_time) AS latest_time
            FROM zp_homework_publish p
            INNER JOIN zp_homework h ON h.hw_publish_id = p.id
            WHERE h.status = 3 
              AND h.create_time >= DATE_SUB(NOW(), INTERVAL %s HOUR)
        """
        params = [hours]
        
        if subject_id is not None:
            sql += " AND h.subject_id = %s"
            params.append(subject_id)
        
        sql += """
            GROUP BY p.id, p.content
            ORDER BY latest_time DESC
            LIMIT 50
        """
        
        rows = DatabaseService.execute_query(sql, tuple(params))
        
        tasks = []
        for row in rows:
            tasks.append({
                'hw_publish_id': row['hw_publish_id'],
                'task_name': row.get('task_name', ''),
                'homework_count': row.get('homework_count', 0),
                'latest_time': row['latest_time'].isoformat() if row.get('latest_time') else None
            })
        
        return jsonify({'success': True, 'data': tasks})
    
    except Exception as e:
        print(f"[HomeworkTasks] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'查询失败: {str(e)}'}), 500


@batch_evaluation_bp.route('/homework', methods=['GET'])
def get_batch_homework():
    """获取可用于批量评估的作业列表"""
    subject_id = request.args.get('subject_id', type=int)
    hours = request.args.get('hours', 6, type=int)  # 默认6小时
    hw_publish_id = request.args.get('hw_publish_id', type=int)
    
    try:
        # 根据是否有hw_publish_id决定查询条件
        if hw_publish_id:
            sql = """
                SELECT h.id, h.student_id, h.hw_publish_id, h.subject_id, h.page_num, 
                       h.pic_path, h.homework_result, h.create_time,
                       p.content AS homework_name,
                       s.name AS student_name,
                       b.id AS book_id,
                       b.book_name AS book_name
                FROM zp_homework h
                LEFT JOIN zp_homework_publish p ON h.hw_publish_id = p.id
                LEFT JOIN zp_student s ON h.student_id = s.id
                LEFT JOIN zp_make_book b ON p.book_id = b.id
                WHERE h.status = 3 
                  AND h.hw_publish_id = %s
            """
            params = [hw_publish_id]
            
            if subject_id is not None:
                sql += " AND h.subject_id = %s"
                params.append(subject_id)
            
            sql += " ORDER BY h.create_time DESC LIMIT 500"
        else:
            sql = """
                SELECT h.id, h.student_id, h.hw_publish_id, h.subject_id, h.page_num, 
                       h.pic_path, h.homework_result, h.create_time,
                       p.content AS homework_name,
                       s.name AS student_name,
                       b.id AS book_id,
                       b.book_name AS book_name
                FROM zp_homework h
                LEFT JOIN zp_homework_publish p ON h.hw_publish_id = p.id
                LEFT JOIN zp_student s ON h.student_id = s.id
                LEFT JOIN zp_make_book b ON p.book_id = b.id
                WHERE h.status = 3 
                  AND h.create_time >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            """
            params = [hours]
            
            if subject_id is not None:
                sql += " AND h.subject_id = %s"
                params.append(subject_id)
            
            sql += " ORDER BY h.create_time DESC LIMIT 500"
        
        rows = DatabaseService.execute_query(sql, tuple(params))
        
        data = []
        for row in rows:
            homework_result = row.get('homework_result', '[]')
            question_count = 0
            try:
                result_json = json.loads(homework_result) if homework_result else []
                question_count = len(result_json) if isinstance(result_json, list) else 0
            except:
                pass
            
            data.append({
                'id': row['id'],
                'student_id': row.get('student_id', ''),
                'student_name': row.get('student_name', ''),
                'homework_name': row.get('homework_name', ''),
                'subject_id': row.get('subject_id'),
                'page_num': row.get('page_num'),
                'pic_path': row.get('pic_path', ''),
                'book_id': str(row.get('book_id', '')) if row.get('book_id') else '',
                'book_name': row.get('book_name', ''),
                'create_time': row['create_time'].isoformat() if row.get('create_time') else None,
                'question_count': question_count
            })
        
        return jsonify({'success': True, 'data': data})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@batch_evaluation_bp.route('/tasks', methods=['GET', 'POST'])
def batch_tasks():
    """批量评估任务管理"""
    StorageService.ensure_dir(BATCH_TASKS_DIR)
    
    if request.method == 'GET':
        # 获取筛选参数
        subject_id = request.args.get('subject_id', type=int)
        test_condition_id = request.args.get('test_condition_id', type=int)
        
        try:
            tasks = []
            for filename in StorageService.list_batch_tasks():
                task_id = filename[:-5]
                data = StorageService.load_batch_task(task_id)
                if data:
                    # 学科筛选
                    task_subject_id = data.get('subject_id')
                    if subject_id is not None and task_subject_id != subject_id:
                        continue
                    
                    # 测试条件筛选
                    task_test_condition_id = data.get('test_condition_id')
                    if test_condition_id is not None and task_test_condition_id != test_condition_id:
                        continue
                    
                    overall_report = data.get('overall_report') or {}
                    tasks.append({
                        'task_id': data.get('task_id'),
                        'name': data.get('name', ''),
                        'subject_id': task_subject_id,
                        'subject_name': data.get('subject_name', ''),
                        'test_condition_id': task_test_condition_id,
                        'test_condition_name': data.get('test_condition_name', ''),
                        'status': data.get('status', 'pending'),
                        'homework_count': len(data.get('homework_items', [])),
                        'overall_accuracy': overall_report.get('overall_accuracy', 0),
                        'created_at': data.get('created_at', '')
                    })
            
            tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return jsonify({'success': True, 'data': tasks})
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)})
    
    else:  # POST
        data = request.json
        name = data.get('name', '')
        subject_id = data.get('subject_id')
        test_condition_id = data.get('test_condition_id')
        test_condition_name = data.get('test_condition_name', '')
        homework_ids = data.get('homework_ids', [])
        
        if not homework_ids:
            return jsonify({'success': False, 'error': '请选择作业'})
        
        try:
            placeholders = ','.join(['%s'] * len(homework_ids))
            sql = f"""
                SELECT h.id, h.student_id, h.subject_id, h.page_num, h.pic_path, h.homework_result,
                       p.content AS homework_name, s.name AS student_name,
                       b.id AS book_id, b.book_name AS book_name
                FROM zp_homework h
                LEFT JOIN zp_homework_publish p ON h.hw_publish_id = p.id
                LEFT JOIN zp_student s ON h.student_id = s.id
                LEFT JOIN zp_make_book b ON p.book_id = b.id
                WHERE h.id IN ({placeholders})
            """
            rows = DatabaseService.execute_query(sql, tuple(homework_ids))
            
            # 获取学科名称
            subject_name = ''
            if subject_id is not None:
                subject_map = {
                    0: '英语',
                    1: '语文',
                    2: '数学',
                    3: '物理',
                    4: '化学',
                    5: '生物',
                    6: '政治',
                    7: '历史',
                    8: '地理'
                }
                subject_name = subject_map.get(subject_id, f'学科{subject_id}')
            
            # 如果没有提供任务名称，自动生成：学科-月/日
            if not name:
                now = datetime.now()
                if subject_name:
                    name = f'{subject_name}-{now.month}/{now.day}'
                else:
                    name = f'批量评估-{now.month}/{now.day}'
            
            # 加载数据集
            datasets = []
            for fn in StorageService.list_datasets():
                ds = StorageService.load_dataset(fn[:-5])
                if ds:
                    datasets.append(ds)
            
            # 按数据集包含的页码数量降序排序，优先匹配包含更多页码的数据集
            datasets.sort(key=lambda ds: len(ds.get('pages', [])), reverse=True)
            
            homework_items = []
            for row in rows:
                book_id = str(row.get('book_id', '')) if row.get('book_id') else ''
                page_num = row.get('page_num')
                # 确保 page_num 是整数类型用于匹配
                page_num_int = int(page_num) if page_num is not None else None
                
                matched_dataset = None
                for ds in datasets:
                    ds_book_id = str(ds.get('book_id', '')) if ds.get('book_id') else ''
                    ds_pages = ds.get('pages', [])
                    base_effects = ds.get('base_effects', {})
                    
                    # 同时检查整数和字符串形式的页码
                    if ds_book_id == book_id and page_num_int is not None:
                        # 检查数据集的 pages 数组
                        page_in_pages = page_num_int in ds_pages or str(page_num_int) in [str(p) for p in ds_pages]
                        # 检查数据集的 base_effects 是否包含该页码的数据
                        page_in_effects = str(page_num_int) in base_effects
                        
                        if page_in_pages and page_in_effects:
                            matched_dataset = ds.get('dataset_id')
                            break
                
                homework_items.append({
                    'homework_id': row['id'],
                    'student_id': row.get('student_id', ''),
                    'student_name': row.get('student_name', ''),
                    'homework_name': row.get('homework_name', ''),
                    'book_id': book_id,
                    'book_name': row.get('book_name', ''),
                    'page_num': page_num,
                    'pic_path': row.get('pic_path', ''),
                    'homework_result': row.get('homework_result', '[]'),
                    'matched_dataset': matched_dataset,
                    'status': 'matched' if matched_dataset else 'pending',
                    'accuracy': None,
                    'evaluation': None
                })
            
            task_id = str(uuid.uuid4())[:8]
            task_data = {
                'task_id': task_id,
                'name': name,
                'subject_id': subject_id,
                'subject_name': subject_name,
                'test_condition_id': test_condition_id,
                'test_condition_name': test_condition_name,
                'status': 'pending',
                'homework_items': homework_items,
                'overall_report': None,
                'created_at': datetime.now().isoformat()
            }
            
            StorageService.save_batch_task(task_id, task_data)
            
            return jsonify({'success': True, 'task_id': task_id, 'homework_items': homework_items})
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})


@batch_evaluation_bp.route('/tasks/<task_id>', methods=['GET', 'DELETE'])
def batch_task_detail(task_id):
    """获取或删除任务"""
    if request.method == 'GET':
        try:
            data = StorageService.load_batch_task(task_id)
            if not data:
                return jsonify({'success': False, 'error': '任务不存在'})
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    else:  # DELETE
        try:
            StorageService.delete_batch_task(task_id)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})


@batch_evaluation_bp.route('/tasks/<task_id>/homework/<homework_id>', methods=['GET'])
def get_homework_detail(task_id, homework_id):
    """获取任务中某个作业的评估详情"""
    try:
        task_data = StorageService.load_batch_task(task_id)
        if not task_data:
            return jsonify({'success': False, 'error': '任务不存在'})
        
        # 获取任务的学科ID
        task_subject_id = task_data.get('subject_id')
        is_chinese = task_subject_id == 1  # 语文学科
        # 查找对应的作业
        homework_item = None
        for item in task_data.get('homework_items', []):
            if str(item.get('homework_id')) == str(homework_id):
                homework_item = item
                break
        
        if not homework_item:
            return jsonify({'success': False, 'error': '作业不存在'})
        
        # 构建返回数据
        evaluation = homework_item.get('evaluation', {})
        errors = evaluation.get('errors', [])
        
        # 获取基准效果和AI结果的详细对比
        base_effect = []
        if homework_item.get('matched_dataset'):
            ds_data = StorageService.load_dataset(homework_item['matched_dataset'])
            if ds_data:
                page_key = str(homework_item.get('page_num'))
                base_effect = ds_data.get('base_effects', {}).get(page_key, [])
        
        # 如果没有匹配数据集，尝试按book_id和page_num从所有数据集中查找
        if not base_effect:
            book_id = homework_item.get('book_id', '')
            page_num = homework_item.get('page_num')
            if book_id and page_num:
                for filename in StorageService.list_datasets():
                    dataset_id = filename.replace('.json', '')
                    ds_data = StorageService.load_dataset(dataset_id)
                    if ds_data and str(ds_data.get('book_id', '')) == str(book_id):
                        page_key = str(page_num)
                        if page_key in ds_data.get('base_effects', {}):
                            base_effect = ds_data['base_effects'][page_key]
                            break
        
        # 如果还没有，尝试只按page_num从所有数据集中查找
        if not base_effect:
            page_num = homework_item.get('page_num')
            if page_num:
                for filename in StorageService.list_datasets():
                    dataset_id = filename.replace('.json', '')
                    ds_data = StorageService.load_dataset(dataset_id)
                    if ds_data:
                        page_key = str(page_num)
                        if page_key in ds_data.get('base_effects', {}):
                            base_effect = ds_data['base_effects'][page_key]
                            break
        
        # 最后尝试从 baseline_effects 获取
        if not base_effect:
            import re
            book_name = homework_item.get('book_name', '') or homework_item.get('homework_name', '')
            page_num = homework_item.get('page_num')
            if book_name and page_num:
                safe_name = re.sub(r'[<>:"/\\|?*]', '_', book_name)
                baseline_filename = f"{safe_name}_{page_num}.json"
                baseline_data = StorageService.load_baseline_effect(baseline_filename)
                if baseline_data:
                    base_effect = baseline_data.get('base_effect', [])
        
        homework_result = []
        try:
            homework_result = json.loads(homework_item.get('homework_result', '[]'))
        except:
            pass
        
        # 构建详细的错误信息
        detailed_errors = []
        
        # 先展开 homework_result 的 children 结构
        flat_homework = flatten_homework_result(homework_result)
        
        # 构建多种索引方式的字典（使用展开后的数据，标准化题号）
        hw_dict_by_index = {normalize_index(item.get('index', '')): item for item in flat_homework}
        hw_dict_by_tempindex = {}
        for i, item in enumerate(flat_homework):
            temp_idx = item.get('tempIndex')
            if temp_idx is not None:
                hw_dict_by_tempindex[int(temp_idx)] = item
            else:
                hw_dict_by_tempindex[i] = item
        
        for i, base_item in enumerate(base_effect):
            idx = str(base_item.get('index', ''))
            # 标准化基准效果的题号
            normalized_idx = normalize_index(idx)
            # 基准效果的tempIndex，如果没有则使用循环索引
            base_temp_idx = base_item.get('tempIndex')
            if base_temp_idx is not None:
                base_temp_idx = int(base_temp_idx)
            else:
                base_temp_idx = i
            
            # 根据学科选择匹配方式
            if is_chinese:
                # 语文: 仅按题号(index)匹配，使用标准化后的题号
                hw_item = hw_dict_by_index.get(normalized_idx)
            else:
                # 其他学科: 优先按index匹配，其次按tempIndex匹配
                hw_item = hw_dict_by_index.get(normalized_idx)
                if not hw_item:
                    hw_item = hw_dict_by_tempindex.get(base_temp_idx)
            
            is_match, error_type, explanation, severity = classify_error(base_item, hw_item)
            
            if not is_match:
                base_answer = str(base_item.get('answer', '') or base_item.get('mainAnswer', '')).strip()
                base_user = str(base_item.get('userAnswer', '')).strip()
                base_correct = get_correct_value(base_item)
                
                hw_answer = str(hw_item.get('answer', '') or hw_item.get('mainAnswer', '')).strip() if hw_item else ''
                hw_user = str(hw_item.get('userAnswer', '')).strip() if hw_item else ''
                hw_correct = get_correct_value(hw_item) if hw_item else ''
                
                detailed_errors.append({
                    'index': idx,
                    'error_type': error_type,
                    'explanation': explanation,
                    'severity': severity,
                    'base_effect': {
                        'answer': base_answer,
                        'userAnswer': base_user,
                        'correct': base_correct if base_correct else '-'
                    },
                    'ai_result': {
                        'answer': hw_answer,
                        'userAnswer': hw_user,
                        'correct': hw_correct if hw_correct else '-'
                    }
                })
        
        return jsonify({
            'success': True,
            'data': {
                'homework_id': homework_id,
                'book_id': homework_item.get('book_id', ''),
                'book_name': homework_item.get('book_name', ''),
                'page_num': homework_item.get('page_num'),
                'student_id': homework_item.get('student_id', ''),
                'student_name': homework_item.get('student_name', ''),
                'status': homework_item.get('status', ''),
                'accuracy': homework_item.get('accuracy', 0),
                'base_effect': base_effect,
                'ai_result': homework_result,
                'evaluation': {
                    'accuracy': evaluation.get('accuracy', 0),
                    'total_questions': evaluation.get('total_questions', 0),
                    'correct_count': evaluation.get('correct_count', 0),
                    'error_count': evaluation.get('error_count', 0),
                    'errors': detailed_errors
                }
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@batch_evaluation_bp.route('/tasks/<task_id>/evaluate', methods=['POST'])
def batch_evaluate(task_id):
    """执行批量评估（SSE流式返回）"""
    task_data = StorageService.load_batch_task(task_id)
    if not task_data:
        return jsonify({'success': False, 'error': '任务不存在'})
    
    # 获取任务的学科ID
    task_subject_id = task_data.get('subject_id')
    
    def generate():
        task_data['status'] = 'running'
        homework_items = task_data.get('homework_items', [])
        
        total_correct = 0
        total_questions = 0
        
        for item in homework_items:
            homework_id = item['homework_id']
            
            yield f"data: {json.dumps({'type': 'progress', 'homework_id': homework_id, 'status': 'evaluating'})}\n\n"
            
            try:
                base_effect = None
                
                # 优先从数据集获取基准效果
                if item.get('matched_dataset'):
                    ds_data = StorageService.load_dataset(item['matched_dataset'])
                    if ds_data:
                        page_key = str(item.get('page_num'))
                        base_effect = ds_data.get('base_effects', {}).get(page_key, [])
                
                # 如果数据集没有，尝试从 baseline_effects 获取
                if not base_effect:
                    book_name = item.get('book_name', '') or item.get('homework_name', '')
                    page_num = item.get('page_num')
                    if book_name and page_num:
                        import re
                        safe_name = re.sub(r'[<>:"/\\|?*]', '_', book_name)
                        baseline_filename = f"{safe_name}_{page_num}.json"
                        baseline_data = StorageService.load_baseline_effect(baseline_filename)
                        if baseline_data:
                            base_effect = baseline_data.get('base_effect', [])
                
                homework_result = []
                try:
                    homework_result = json.loads(item.get('homework_result', '[]'))
                except:
                    pass
                
                if base_effect and homework_result:
                    # 传递学科ID，语文(2)使用题号匹配
                    evaluation = do_evaluation(base_effect, homework_result, subject_id=task_subject_id)
                    item['accuracy'] = evaluation['accuracy']
                    item['evaluation'] = evaluation
                    item['status'] = 'completed'
                    
                    total_correct += evaluation['correct_count']
                    total_questions += evaluation['total_questions']
                else:
                    item['status'] = 'completed'
                    item['accuracy'] = 0
                    item['evaluation'] = {'accuracy': 0, 'total_questions': 0, 'correct_count': 0, 'error_count': 0, 'errors': []}
                
                yield f"data: {json.dumps({'type': 'result', 'homework_id': homework_id, 'accuracy': item['accuracy']})}\n\n"
                
            except Exception as e:
                item['status'] = 'failed'
                item['error'] = str(e)
                yield f"data: {json.dumps({'type': 'error', 'homework_id': homework_id, 'error': str(e)})}\n\n"
        
        overall_accuracy = total_correct / total_questions if total_questions > 0 else 0
        
        # 汇总所有作业的题目类型统计: 选择题、客观填空题、非选择题
        aggregated_type_stats = {
            'choice': {'total': 0, 'correct': 0, 'accuracy': 0},
            'objective_fill': {'total': 0, 'correct': 0, 'accuracy': 0},
            'other': {'total': 0, 'correct': 0, 'accuracy': 0}
        }
        
        # 汇总bvalue细分统计
        aggregated_bvalue_stats = {
            '1': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '单选'},
            '2': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '多选'},
            '3': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '判断'},
            '4': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '填空'},
            '5': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '解答'}
        }
        
        # 汇总组合统计
        aggregated_combined_stats = {
            'objective_1': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观单选'},
            'objective_2': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观多选'},
            'objective_3': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观判断'},
            'objective_4': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观填空'},
            'objective_5': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观解答'},
            'subjective_1': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观单选'},
            'subjective_2': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观多选'},
            'subjective_3': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观判断'},
            'subjective_4': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观填空'},
            'subjective_5': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观解答'}
        }
        
        for item in homework_items:
            evaluation = item.get('evaluation', {})
            by_type = evaluation.get('by_question_type', {})
            by_bvalue = evaluation.get('by_bvalue', {})
            by_combined = evaluation.get('by_combined', {})
            
            for key in aggregated_type_stats:
                if key in by_type:
                    aggregated_type_stats[key]['total'] += by_type[key].get('total', 0)
                    aggregated_type_stats[key]['correct'] += by_type[key].get('correct', 0)
            
            for key in aggregated_bvalue_stats:
                if key in by_bvalue:
                    aggregated_bvalue_stats[key]['total'] += by_bvalue[key].get('total', 0)
                    aggregated_bvalue_stats[key]['correct'] += by_bvalue[key].get('correct', 0)
            
            for key in aggregated_combined_stats:
                if key in by_combined:
                    aggregated_combined_stats[key]['total'] += by_combined[key].get('total', 0)
                    aggregated_combined_stats[key]['correct'] += by_combined[key].get('correct', 0)
        
        # 计算汇总准确率
        for key in aggregated_type_stats:
            total_count = aggregated_type_stats[key]['total']
            correct = aggregated_type_stats[key]['correct']
            aggregated_type_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
        
        for key in aggregated_bvalue_stats:
            total_count = aggregated_bvalue_stats[key]['total']
            correct = aggregated_bvalue_stats[key]['correct']
            aggregated_bvalue_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
        
        for key in aggregated_combined_stats:
            total_count = aggregated_combined_stats[key]['total']
            correct = aggregated_combined_stats[key]['correct']
            aggregated_combined_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
        
        task_data['status'] = 'completed'
        task_data['overall_report'] = {
            'overall_accuracy': overall_accuracy,
            'total_homework': len(homework_items),
            'total_questions': total_questions,
            'correct_questions': total_correct,
            'by_question_type': aggregated_type_stats,
            'by_bvalue': aggregated_bvalue_stats,
            'by_combined': aggregated_combined_stats
        }
        
        StorageService.save_batch_task(task_id, task_data)
        
        yield f"data: {json.dumps({'type': 'complete', 'overall_accuracy': overall_accuracy, 'by_question_type': aggregated_type_stats, 'by_combined': aggregated_combined_stats})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


def do_evaluation(base_effect, homework_result, use_ai_compare=False, user_id=None, subject_id=None):
    """
    执行评估计算
    - 语文(subject_id=1): 按题号(index)匹配
    - 其他学科: 按tempIndex匹配
    支持本地计算和AI模型比对
    包含题目类型分类统计
    
    Args:
        base_effect: 基准效果数据
        homework_result: AI批改结果
        use_ai_compare: 是否使用AI比对
        user_id: 用户ID，用于加载用户API配置
        subject_id: 学科ID，语文(1)使用题号匹配
    """
    total = len(base_effect)
    correct_count = 0
    errors = []
    error_distribution = {
        '识别错误-判断正确': 0,
        '识别错误-判断错误': 0,
        '识别正确-判断错误': 0,
        '格式差异': 0,
        '缺失题目': 0,
        'AI识别幻觉': 0
    }
    
    # 题目类型分类统计: 选择题、客观填空题、非选择题
    type_stats = {
        'choice': {'total': 0, 'correct': 0, 'accuracy': 0},           # 选择题
        'objective_fill': {'total': 0, 'correct': 0, 'accuracy': 0},   # 客观填空题 (客观+非选择)
        'other': {'total': 0, 'correct': 0, 'accuracy': 0}             # 非选择题 (主观+非选择)
    }
    
    # 按bvalue细分统计 (1=单选, 2=多选, 3=判断, 4=填空, 5=解答)
    bvalue_stats = {
        '1': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '单选'},
        '2': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '多选'},
        '3': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '判断'},
        '4': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '填空'},
        '5': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '解答'}
    }
    
    # 按主观/客观 + bvalue 组合统计
    combined_stats = {
        'objective_1': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观单选'},
        'objective_2': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观多选'},
        'objective_3': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观判断'},
        'objective_4': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观填空'},
        'objective_5': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观解答'},
        'subjective_1': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观单选'},
        'subjective_2': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观多选'},
        'subjective_3': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观判断'},
        'subjective_4': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观填空'},
        'subjective_5': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观解答'}
    }
    
    # 如果启用AI比对
    if use_ai_compare:
        ai_result = do_ai_compare_batch(base_effect, homework_result, user_id=user_id)
        if ai_result:
            return ai_result
    
    # 先展开 homework_result 的 children 结构
    flat_homework = flatten_homework_result(homework_result)
    
    # 判断是否是语文学科 (subject_id=1)，语文使用题号匹配
    is_chinese = subject_id == 1
    
    # 构建索引字典（使用展开后的数据）
    hw_dict_by_index = {}  # 按题号索引（标准化后）
    hw_dict_by_tempindex = {}  # 按tempIndex索引
    for i, item in enumerate(flat_homework):
        # 按题号索引（标准化中英文符号）
        item_idx = normalize_index(item.get('index', ''))
        if item_idx:
            hw_dict_by_index[item_idx] = item
        # 按tempIndex索引
        temp_idx = item.get('tempIndex')
        if temp_idx is not None:
            hw_dict_by_tempindex[int(temp_idx)] = item
        else:
            hw_dict_by_tempindex[i] = item
    
    for i, base_item in enumerate(base_effect):
        idx = str(base_item.get('index', ''))
        # 标准化基准效果的题号
        normalized_idx = normalize_index(idx)
        # 基准效果的tempIndex，如果没有则使用循环索引
        base_temp_idx = base_item.get('tempIndex')
        if base_temp_idx is not None:
            base_temp_idx = int(base_temp_idx)
        else:
            base_temp_idx = i
        
        # 根据学科选择匹配方式
        if is_chinese:
            # 语文: 按题号(index)匹配，使用标准化后的题号
            hw_item = hw_dict_by_index.get(normalized_idx)
        else:
            # 其他学科: 按tempIndex匹配
            hw_item = hw_dict_by_tempindex.get(base_temp_idx)
        
        # 获取题目类型分类
        question_category = classify_question_type(base_item)
        bvalue = str(base_item.get('bvalue', ''))
        is_objective = question_category['is_objective']
        
        # 更新题目类型统计 - 总数 (选择题、客观填空题、非选择题)
        # 选择题: is_choice=true
        # 客观填空题: is_objective=true 且 is_fill=true (bvalue=4)
        # 非选择题: 其他所有题目
        if question_category['is_choice']:
            type_stats['choice']['total'] += 1
        elif question_category['is_objective'] and question_category['is_fill']:
            type_stats['objective_fill']['total'] += 1
        else:
            type_stats['other']['total'] += 1
        
        # 更新bvalue细分统计 - 总数
        if bvalue in bvalue_stats:
            bvalue_stats[bvalue]['total'] += 1
        
        # 更新组合统计 - 总数
        obj_key = 'objective' if is_objective else 'subjective'
        combined_key = f'{obj_key}_{bvalue}'
        if combined_key in combined_stats:
            combined_stats[combined_key]['total'] += 1
        
        # 基准效果的标准答案：优先取 answer，没有则取 mainAnswer
        base_answer = str(base_item.get('answer', '') or base_item.get('mainAnswer', '')).strip()
        base_user = str(base_item.get('userAnswer', '')).strip()
        # 兼容 correct 和 isRight 两种字段格式
        base_correct = get_correct_value(base_item)
        
        # AI批改结果的答案
        hw_answer = str(hw_item.get('answer', '') or hw_item.get('mainAnswer', '')).strip() if hw_item else ''
        hw_user = str(hw_item.get('userAnswer', '')).strip() if hw_item else ''
        hw_correct = get_correct_value(hw_item) if hw_item else ''
        
        is_match = True
        error_type = None
        explanation = ''
        severity = 'medium'
        
        if not hw_item:
            is_match = False
            error_type = '缺失题目'
            explanation = f'AI批改结果中缺少第{idx}题'
            severity = 'high'
        elif not base_correct:
            # 基准效果缺少correct字段，只能比较userAnswer
            norm_base_user = normalize_answer(base_user)
            norm_hw_user = normalize_answer(hw_user)
            
            if norm_base_user == norm_hw_user:
                is_match = True
            else:
                is_match = False
                error_type = '识别错误-判断错误'
                explanation = f'用户答案不一致：基准="{base_user}"，AI="{hw_user}"'
                severity = 'high'
        else:
            # 标准化答案进行比较
            norm_base_user = normalize_answer(base_user)
            norm_hw_user = normalize_answer(hw_user)
            norm_base_answer = normalize_answer(base_answer)
            
            user_match = norm_base_user == norm_hw_user
            correct_match = base_correct == hw_correct
            
            # 检测AI识别幻觉：学生答错了 + AI识别的用户答案≠基准用户答案 + AI识别的用户答案=标准答案
            # 即AI把学生的错误手写答案"脑补"成了标准答案
            if base_correct == 'no' and not user_match and norm_hw_user == norm_base_answer:
                is_match = False
                error_type = 'AI识别幻觉'
                explanation = f'AI将学生答案"{base_user}"识别为"{hw_user}"（标准答案），属于识别幻觉'
                severity = 'high'
            elif user_match and correct_match:
                is_match = True
            elif user_match and not correct_match:
                # 用户答案识别正确，但判断结果不同
                # 这是"识别正确-判断错误"，格式差异只是次要问题
                is_match = False
                error_type = '识别正确-判断错误'
                if has_format_diff(base_user, hw_user):
                    explanation = f'识别正确（有格式差异）但判断错误：基准={base_correct}，AI={hw_correct}'
                else:
                    explanation = f'识别正确但判断错误：基准={base_correct}，AI={hw_correct}'
                severity = 'high'
            elif not user_match and correct_match:
                is_match = False
                error_type = '识别错误-判断正确'
                explanation = f'识别不准确但判断结果正确：基准="{base_user}"，AI="{hw_user}"'
                severity = 'medium'
            else:
                is_match = False
                error_type = '识别错误-判断错误'
                explanation = f'识别和判断都有误：基准="{base_user}/{base_correct}"，AI="{hw_user}/{hw_correct}"'
                severity = 'high'
        
        if is_match:
            correct_count += 1
            # 更新题目类型统计 - 正确数 (选择题、客观填空题、非选择题)
            if question_category['is_choice']:
                type_stats['choice']['correct'] += 1
            elif question_category['is_objective'] and question_category['is_fill']:
                type_stats['objective_fill']['correct'] += 1
            else:
                type_stats['other']['correct'] += 1
            
            # 更新bvalue细分统计 - 正确数
            if bvalue in bvalue_stats:
                bvalue_stats[bvalue]['correct'] += 1
            
            # 更新组合统计 - 正确数
            if combined_key in combined_stats:
                combined_stats[combined_key]['correct'] += 1
            
            # 格式差异虽然计入正确，但仍记录到分布中
            if error_type == '格式差异':
                error_distribution[error_type] = error_distribution.get(error_type, 0) + 1
        else:
            if error_type:
                error_distribution[error_type] = error_distribution.get(error_type, 0) + 1
            
            # 计算分析数据
            recognition_match = normalize_answer(base_user) == normalize_answer(hw_user) if base_user or hw_user else None
            judgment_match = base_correct == hw_correct if base_correct and hw_correct else None
            
            errors.append({
                'index': idx,
                'base_effect': {
                    'answer': base_answer,
                    'userAnswer': base_user,
                    'correct': base_correct if base_correct else '-'
                },
                'ai_result': {
                    'answer': hw_answer,
                    'userAnswer': hw_user,
                    'correct': hw_correct if hw_correct else '-'
                },
                'error_type': error_type or '未知错误',
                'explanation': explanation,
                'severity': severity,
                'severity_code': severity,
                'analysis': {
                    'recognition_match': recognition_match,
                    'judgment_match': judgment_match,
                    'is_hallucination': error_type == 'AI识别幻觉'
                },
                # 添加题目类型标注
                'question_category': question_category
            })
    
    # 计算题目类型准确率
    for key in type_stats:
        total_count = type_stats[key]['total']
        correct = type_stats[key]['correct']
        type_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
    
    # 计算bvalue细分准确率
    for key in bvalue_stats:
        total_count = bvalue_stats[key]['total']
        correct = bvalue_stats[key]['correct']
        bvalue_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
    
    # 计算组合统计准确率
    for key in combined_stats:
        total_count = combined_stats[key]['total']
        correct = combined_stats[key]['correct']
        combined_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
    
    accuracy = correct_count / total if total > 0 else 0
    
    # 计算真正的精确率、召回率、F1
    tp = correct_count
    fp = error_distribution.get('识别正确-判断错误', 0) + error_distribution.get('AI识别幻觉', 0)
    fn = error_distribution.get('识别错误-判断错误', 0)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    # 计算幻觉率
    hallucination_count = error_distribution.get('AI识别幻觉', 0)
    wrong_answers_count = sum(1 for b in base_effect if str(b.get('correct', '')).lower() == 'no')
    hallucination_rate = hallucination_count / wrong_answers_count if wrong_answers_count > 0 else 0
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'hallucination_rate': hallucination_rate,
        'total_questions': total,
        'correct_count': correct_count,
        'error_count': total - correct_count,
        'errors': errors,
        'error_distribution': error_distribution,
        'by_question_type': type_stats,
        'by_bvalue': bvalue_stats,
        'by_combined': combined_stats
    }


def do_ai_compare_batch(base_effect, homework_result, user_id=None):
    """
    批量评估中使用语义级评估系统
    使用 SemanticEvalService 进行更精准的 AI 批改效果分析
    """
    config = ConfigService.load_config(user_id=user_id)
    
    # 检查是否配置了 DeepSeek API Key
    if not config.get('deepseek_api_key'):
        print('[AI Compare Batch] 未配置 DeepSeek API Key，回退到本地评估')
        return None
    
    try:
        # 先展开 homework_result 的 children 结构
        flat_homework = flatten_homework_result(homework_result)
        
        # 构建评估项目列表
        items = []
        hw_dict = {}
        for i, hw_item in enumerate(flat_homework):
            temp_idx = hw_item.get('tempIndex', i)
            hw_dict[int(temp_idx)] = hw_item
        
        for i, base_item in enumerate(base_effect):
            base_temp_idx = base_item.get('tempIndex', i)
            if base_temp_idx is not None:
                base_temp_idx = int(base_temp_idx)
            else:
                base_temp_idx = i
            
            hw_item = hw_dict.get(base_temp_idx, {})
            
            items.append({
                'index': str(base_item.get('index', i + 1)),
                'standard_answer': str(base_item.get('answer', '') or base_item.get('mainAnswer', '')),
                'base_user_answer': str(base_item.get('userAnswer', '')),
                'base_correct': get_correct_value(base_item),
                'ai_user_answer': str(hw_item.get('userAnswer', '')),
                'ai_correct': get_correct_value(hw_item)
            })
        
        # 执行语义评估
        semantic_result = SemanticEvalService.evaluate_batch(
            subject='通用',
            question_type='客观题',
            items=items,
            eval_model='deepseek-chat'
        )
        
        # 转换为批量评估结果格式
        return convert_semantic_to_batch_result(
            semantic_result, 
            base_effect, 
            homework_result
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f'[AI Compare Batch] 语义评估失败: {str(e)}')
        return None


def convert_semantic_to_batch_result(semantic_result, base_effect, homework_result):
    """
    将语义评估结果转换为批量评估结果格式
    """
    total = len(base_effect)
    correct_count = 0
    errors = []
    error_distribution = {
        '识别错误-判断正确': 0,
        '识别错误-判断错误': 0,
        '识别正确-判断错误': 0,
        '格式差异': 0,
        '缺失题目': 0,
        'AI识别幻觉': 0
    }
    
    # 题目类型分类统计: 选择题、客观填空题、非选择题
    type_stats = {
        'choice': {'total': 0, 'correct': 0, 'accuracy': 0},           # 选择题
        'objective_fill': {'total': 0, 'correct': 0, 'accuracy': 0},   # 客观填空题 (客观+非选择)
        'other': {'total': 0, 'correct': 0, 'accuracy': 0}             # 非选择题 (主观+非选择)
    }
    
    # 按bvalue细分统计 (1=单选, 2=多选, 3=判断, 4=填空, 5=解答)
    bvalue_stats = {
        '1': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '单选'},
        '2': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '多选'},
        '3': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '判断'},
        '4': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '填空'},
        '5': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '解答'}
    }
    
    # 按主观/客观 + bvalue 组合统计
    combined_stats = {
        'objective_1': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观单选'},
        'objective_2': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观多选'},
        'objective_3': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观判断'},
        'objective_4': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观填空'},
        'objective_5': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观解答'},
        'subjective_1': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观单选'},
        'subjective_2': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观多选'},
        'subjective_3': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观判断'},
        'subjective_4': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观填空'},
        'subjective_5': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观解答'}
    }
    
    # 错误类型映射
    error_type_map = {
        '完全正确': None,
        '语义等价': None,  # 语义等价视为正确
        '识别错误-判断正确': '识别错误-判断正确',
        '识别错误-判断错误': '识别错误-判断错误',
        '识别正确-判断错误': '识别正确-判断错误',
        '格式差异': '格式差异',
        'AI幻觉': 'AI识别幻觉'
    }
    
    # 先展开 homework_result 的 children 结构
    flat_homework = flatten_homework_result(homework_result)
    
    # 构建索引字典（使用展开后的数据）
    hw_dict = {}
    for i, hw_item in enumerate(flat_homework):
        temp_idx = hw_item.get('tempIndex', i)
        hw_dict[int(temp_idx)] = hw_item
        idx = str(hw_item.get('index', ''))
        if idx:
            hw_dict[f'idx_{idx}'] = hw_item
    
    base_dict = {str(b.get('index', '')): b for b in base_effect}
    
    # 处理语义评估结果
    semantic_results = semantic_result.get('results', [])
    result_dict = {str(r.get('index', '')): r for r in semantic_results}
    
    for i, base_item in enumerate(base_effect):
        idx = str(base_item.get('index', ''))
        base_temp_idx = base_item.get('tempIndex', i)
        if base_temp_idx is not None:
            base_temp_idx = int(base_temp_idx)
        else:
            base_temp_idx = i
        
        # 获取题目类型分类
        question_category = classify_question_type(base_item)
        bvalue = str(base_item.get('bvalue', ''))
        is_objective = question_category['is_objective']
        
        # 更新题目类型统计 - 总数 (选择题、客观填空题、非选择题)
        if question_category['is_choice']:
            type_stats['choice']['total'] += 1
        elif question_category['is_objective'] and question_category['is_fill']:
            type_stats['objective_fill']['total'] += 1
        else:
            type_stats['other']['total'] += 1
        
        # 更新bvalue细分统计 - 总数
        if bvalue in bvalue_stats:
            bvalue_stats[bvalue]['total'] += 1
        
        # 更新组合统计 - 总数
        obj_key = 'objective' if is_objective else 'subjective'
        combined_key = f'{obj_key}_{bvalue}'
        if combined_key in combined_stats:
            combined_stats[combined_key]['total'] += 1
        
        # 获取语义评估结果
        sem_result = result_dict.get(idx, {})
        verdict = sem_result.get('verdict', 'UNKNOWN')
        error_type_raw = sem_result.get('error_type', '')
        
        # 获取 AI 批改结果
        hw_item = hw_dict.get(base_temp_idx) or hw_dict.get(f'idx_{idx}', {})
        
        # 判断是否正确
        is_correct = verdict == 'PASS' or error_type_raw in ('完全正确', '语义等价')
        
        if is_correct:
            correct_count += 1
            # 更新题目类型统计 - 正确数 (选择题、客观填空题、非选择题)
            if question_category['is_choice']:
                type_stats['choice']['correct'] += 1
            elif question_category['is_objective'] and question_category['is_fill']:
                type_stats['objective_fill']['correct'] += 1
            else:
                type_stats['other']['correct'] += 1
            
            # 更新bvalue细分统计 - 正确数
            if bvalue in bvalue_stats:
                bvalue_stats[bvalue]['correct'] += 1
            
            # 更新组合统计 - 正确数
            if combined_key in combined_stats:
                combined_stats[combined_key]['correct'] += 1
        else:
            # 映射错误类型
            error_type = error_type_map.get(error_type_raw, '识别错误-判断错误')
            if error_type and error_type in error_distribution:
                error_distribution[error_type] += 1
            
            # 获取详细说明
            explanation = sem_result.get('summary', '')
            if not explanation:
                recognition = sem_result.get('recognition', {})
                if isinstance(recognition, dict):
                    explanation = recognition.get('detail', '')
            
            errors.append({
                'index': idx,
                'base_effect': {
                    'answer': base_item.get('answer', '') or base_item.get('mainAnswer', ''),
                    'userAnswer': base_item.get('userAnswer', ''),
                    'correct': base_item.get('correct', '')
                },
                'ai_result': {
                    'answer': hw_item.get('answer', '') or hw_item.get('mainAnswer', ''),
                    'userAnswer': hw_item.get('userAnswer', ''),
                    'correct': hw_item.get('correct', '')
                },
                'error_type': error_type or error_type_raw,
                'explanation': explanation,
                'severity': sem_result.get('severity', 'medium'),
                'severity_cn': sem_result.get('severity_cn', '中等'),
                'question_category': question_category,
                'semantic_detail': {
                    'recognition': sem_result.get('recognition', {}),
                    'judgment': sem_result.get('judgment', {}),
                    'hallucination': sem_result.get('hallucination', {}),
                    'suggestion': sem_result.get('suggestion', '')
                }
            })
    
    # 计算题目类型准确率
    for key in type_stats:
        total_count = type_stats[key]['total']
        correct = type_stats[key]['correct']
        type_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
    
    # 计算bvalue细分准确率
    for key in bvalue_stats:
        total_count = bvalue_stats[key]['total']
        correct = bvalue_stats[key]['correct']
        bvalue_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
    
    # 计算组合统计准确率
    for key in combined_stats:
        total_count = combined_stats[key]['total']
        correct = combined_stats[key]['correct']
        combined_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
    
    accuracy = correct_count / total if total > 0 else 0
    
    # 计算精确率、召回率、F1
    tp = correct_count
    fp = error_distribution.get('识别正确-判断错误', 0) + error_distribution.get('AI识别幻觉', 0)
    fn = error_distribution.get('识别错误-判断错误', 0)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    # 计算幻觉率
    hallucination_count = error_distribution.get('AI识别幻觉', 0)
    wrong_answers_count = sum(1 for b in base_effect if str(b.get('correct', '')).lower() == 'no')
    hallucination_rate = hallucination_count / wrong_answers_count if wrong_answers_count > 0 else 0
    
    # 获取语义评估的能力评分
    semantic_summary = semantic_result.get('summary', {})
    capability_scores = semantic_summary.get('capability_scores', {})
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'hallucination_rate': hallucination_rate,
        'total_questions': total,
        'correct_count': correct_count,
        'error_count': total - correct_count,
        'errors': errors,
        'error_distribution': error_distribution,
        'by_question_type': type_stats,
        'by_bvalue': bvalue_stats,
        'by_combined': combined_stats,
        'ai_compared': True,
        'semantic_evaluated': True,
        'capability_scores': capability_scores,
        'semantic_conclusion': semantic_summary.get('conclusion', ''),
        'semantic_recommendations': semantic_summary.get('recommendations', [])
    }


@batch_evaluation_bp.route('/tasks/<task_id>/export', methods=['GET'])
def export_batch_excel(task_id):
    """导出Excel报告"""
    task_data = StorageService.load_batch_task(task_id)
    if not task_data:
        return jsonify({'success': False, 'error': '任务不存在'})
    
    wb = Workbook()
    
    header_font = Font(bold=True, size=12, color="FFFFFF")
    header_fill = PatternFill(start_color="1D1D1F", end_color="1D1D1F", fill_type="solid")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    
    ws1 = wb.active
    ws1.title = "总体概览"
    
    overall = task_data.get('overall_report', {})
    by_question_type = overall.get('by_question_type', {})
    
    # 获取题目类型统计数据 (选择题、客观填空题、非选择题)
    choice_stats = by_question_type.get('choice', {})
    objective_fill_stats = by_question_type.get('objective_fill', {})
    other_stats = by_question_type.get('other', {})
    
    overview_data = [
        ['任务名称', task_data.get('name', '')],
        ['创建时间', task_data.get('created_at', '')],
        ['状态', task_data.get('status', '')],
        ['总作业数', overall.get('total_homework', 0)],
        ['总题目数', overall.get('total_questions', 0)],
        ['正确题目数', overall.get('correct_questions', 0)],
        ['总体准确率', f"{(overall.get('overall_accuracy', 0) * 100):.1f}%"],
        ['', ''],  # 空行
        ['题目类型分类统计', ''],
        ['选择题总数', choice_stats.get('total', 0)],
        ['选择题正确数', choice_stats.get('correct', 0)],
        ['选择题准确率', f"{(choice_stats.get('accuracy', 0) * 100):.1f}%"],
        ['', ''],  # 空行
        ['客观填空题总数', objective_fill_stats.get('total', 0)],
        ['客观填空题正确数', objective_fill_stats.get('correct', 0)],
        ['客观填空题准确率', f"{(objective_fill_stats.get('accuracy', 0) * 100):.1f}%"],
        ['', ''],  # 空行
        ['非选择题总数', other_stats.get('total', 0)],
        ['非选择题正确数', other_stats.get('correct', 0)],
        ['非选择题准确率', f"{(other_stats.get('accuracy', 0) * 100):.1f}%"]
    ]
    
    for row_idx, (label, value) in enumerate(overview_data, 1):
        ws1.cell(row=row_idx, column=1, value=label).font = Font(bold=True)
        ws1.cell(row=row_idx, column=2, value=value)
    
    # 作业明细工作表 - 添加题目类型统计列
    ws2 = wb.create_sheet("作业明细")
    headers = ['序号', '书本', '页码', '学生', '准确率', '正确数', '错误数', 
               '选择题准确率', '客观填空题准确率', '非选择题准确率', '状态']
    for col, header in enumerate(headers, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    
    for row_idx, item in enumerate(task_data.get('homework_items', []), 2):
        eval_data = item.get('evaluation', {})
        item_by_type = eval_data.get('by_question_type', {})
        
        ws2.cell(row=row_idx, column=1, value=row_idx - 1)
        ws2.cell(row=row_idx, column=2, value=item.get('book_name', ''))
        ws2.cell(row=row_idx, column=3, value=item.get('page_num', ''))
        ws2.cell(row=row_idx, column=4, value=item.get('student_name', ''))
        ws2.cell(row=row_idx, column=5, value=f"{(item.get('accuracy', 0) * 100):.1f}%")
        ws2.cell(row=row_idx, column=6, value=eval_data.get('correct_count', 0))
        ws2.cell(row=row_idx, column=7, value=eval_data.get('error_count', 0))
        
        # 题目类型准确率 (选择题、客观填空题、非选择题)
        choice_acc = item_by_type.get('choice', {}).get('accuracy', 0)
        obj_fill_acc = item_by_type.get('objective_fill', {}).get('accuracy', 0)
        other_acc = item_by_type.get('other', {}).get('accuracy', 0)
        
        ws2.cell(row=row_idx, column=8, value=f"{(choice_acc * 100):.1f}%" if item_by_type.get('choice', {}).get('total', 0) > 0 else '-')
        ws2.cell(row=row_idx, column=9, value=f"{(obj_fill_acc * 100):.1f}%" if item_by_type.get('objective_fill', {}).get('total', 0) > 0 else '-')
        ws2.cell(row=row_idx, column=10, value=f"{(other_acc * 100):.1f}%" if item_by_type.get('other', {}).get('total', 0) > 0 else '-')
        ws2.cell(row=row_idx, column=11, value=item.get('status', ''))
    
    # 题目明细工作表 - 添加题目类型标注
    ws3 = wb.create_sheet("题目明细")
    detail_headers = ['作业ID', '书本', '页码', '学生', '题号', '基准答案', 'AI答案', 
                      '是否正确', '错误类型', '题型分类']
    for col, header in enumerate(detail_headers, 1):
        cell = ws3.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    
    detail_row = 2
    for item in task_data.get('homework_items', []):
        eval_data = item.get('evaluation', {})
        errors = eval_data.get('errors', [])
        
        # 获取基准效果数据用于显示所有题目
        base_effect = []
        if item.get('matched_dataset'):
            ds_data = StorageService.load_dataset(item['matched_dataset'])
            if ds_data:
                page_key = str(item.get('page_num'))
                base_effect = ds_data.get('base_effects', {}).get(page_key, [])
        
        # 构建错误题目索引
        error_indices = {str(e.get('index', '')): e for e in errors}
        
        for q in base_effect:
            idx = str(q.get('index', ''))
            error_info = error_indices.get(idx, {})
            is_correct = idx not in error_indices
            
            # 获取题目类型分类
            question_category = classify_question_type(q)
            
            # 确定题型分类 (选择题、客观填空题、非选择题)
            if question_category['is_choice']:
                type_text = '选择题'
            elif question_category['is_objective'] and question_category['is_fill']:
                type_text = '客观填空题'
            else:
                type_text = '非选择题'
            
            ws3.cell(row=detail_row, column=1, value=item.get('homework_id', ''))
            ws3.cell(row=detail_row, column=2, value=item.get('book_name', ''))
            ws3.cell(row=detail_row, column=3, value=item.get('page_num', ''))
            ws3.cell(row=detail_row, column=4, value=item.get('student_name', ''))
            ws3.cell(row=detail_row, column=5, value=idx)
            ws3.cell(row=detail_row, column=6, value=q.get('userAnswer', ''))
            
            if error_info:
                ai_result = error_info.get('ai_result', {})
                ws3.cell(row=detail_row, column=7, value=ai_result.get('userAnswer', ''))
            else:
                ws3.cell(row=detail_row, column=7, value=q.get('userAnswer', ''))
            
            ws3.cell(row=detail_row, column=8, value='正确' if is_correct else '错误')
            ws3.cell(row=detail_row, column=9, value=error_info.get('error_type', '') if error_info else '')
            ws3.cell(row=detail_row, column=10, value=type_text)
            
            detail_row += 1
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'batch_evaluation_{task_id}.xlsx'
    )


# ========== AI分析报告 API ==========

@batch_evaluation_bp.route('/tasks/<task_id>/ai-report', methods=['POST'])
def generate_ai_report(task_id):
    """生成AI分析报告"""
    from services.llm_service import LLMService
    from routes.auth import get_current_user_id
    
    task_data = StorageService.load_batch_task(task_id)
    if not task_data:
        return jsonify({'success': False, 'error': '任务不存在'})
    
    try:
        # 收集所有评估结果 - 使用 homework_items 和 evaluation 字段
        eval_results = []
        total_questions = 0
        total_correct = 0
        error_distribution = {}
        all_errors = []
        
        for hw in task_data.get('homework_items', []):
            if hw.get('status') == 'completed' and hw.get('evaluation'):
                result = hw['evaluation']
                # 注意：do_evaluation 返回的是 total_questions 和 correct_count
                hw_total = result.get('total_questions', 0) or result.get('total', 0)
                hw_correct = result.get('correct_count', 0) or result.get('correct', 0)
                total_questions += hw_total
                total_correct += hw_correct
                
                # 汇总错误分布 - 优先从 error_distribution 获取，否则从 errors 列表统计
                hw_error_dist = result.get('error_distribution') or {}
                if hw_error_dist:
                    for err_type, count in hw_error_dist.items():
                        error_distribution[err_type] = error_distribution.get(err_type, 0) + count
                else:
                    # 从 errors 列表统计
                    for err in result.get('errors', []):
                        err_type = err.get('error_type', '未知错误')
                        error_distribution[err_type] = error_distribution.get(err_type, 0) + 1
                
                # 收集错误示例
                all_errors.extend(result.get('errors', [])[:2])
                
                eval_results.append({
                    'homework_id': hw.get('homework_id'),
                    'book_name': hw.get('book_name', ''),
                    'page_num': hw.get('page_num'),
                    'total': hw_total,
                    'correct': hw_correct,
                    'accuracy': result.get('accuracy', 0),
                    'error_count': result.get('error_count', hw_total - hw_correct)
                })
        
        if not eval_results:
            return jsonify({'success': False, 'error': '没有可用的评估结果，请先执行批量评估'})
        
        # 获取用户配置的模型
        user_id = get_current_user_id()
        config = ConfigService.load_config(user_id=user_id)
        eval_model = config.get('eval_model', 'deepseek-v3.2')
        
        # 构建 LLM 提示词
        overall_accuracy = total_correct / total_questions if total_questions > 0 else 0
        
        # 简化错误示例
        error_examples = []
        for err in all_errors[:5]:
            error_examples.append({
                'type': err.get('error_type', ''),
                'base': err.get('base_effect', {}),
                'ai': err.get('ai_result', {})
            })
        
        prompt = f"""请分析以下 AI 批改效果评估数据，生成分析报告：

【总体数据】
- 总题目数: {total_questions}
- 正确题目数: {total_correct}
- 错误题目数: {total_questions - total_correct}
- 总体准确率: {overall_accuracy * 100:.1f}%

【错误分布】
{json.dumps(error_distribution, ensure_ascii=False, indent=2)}

【错误示例】
{json.dumps(error_examples, ensure_ascii=False, indent=2)[:3000]}

【各作业概览】
{json.dumps(eval_results, ensure_ascii=False, indent=2)[:2000]}

请按以下 JSON 格式输出分析报告：
{{
  "overview": {{
    "total": {total_questions},
    "passed": {total_correct},
    "failed": {total_questions - total_correct},
    "pass_rate": {round(overall_accuracy * 100, 1)}
  }},
  "capability_scores": {{
    "recognition": 识别能力评分0到100,
    "judgment": 判断能力评分0到100,
    "overall": 综合评分0到100
  }},
  "top_issues": [
    {{"issue": "问题描述", "count": 出现次数}}
  ],
  "recommendations": ["改进建议1", "改进建议2"],
  "conclusion": "整体结论2到3句话"
}}"""

        system_prompt = "你是 AI 批改效果分析师，请根据评估数据生成分析报告。严格按照要求的 JSON 格式输出，不要输出其他内容。"
        
        llm_result = LLMService.call_deepseek(
            prompt,
            system_prompt=system_prompt,
            model=eval_model,
            timeout=90
        )
        
        if llm_result.get('error'):
            # LLM 调用失败，使用本地汇总
            report = _generate_local_summary(total_questions, total_correct, error_distribution)
        else:
            parsed = LLMService.parse_json_response(llm_result.get('content', ''))
            if parsed:
                report = parsed
                report['generated_by'] = 'llm'
            else:
                report = _generate_local_summary(total_questions, total_correct, error_distribution)
        
        # 保存到任务数据
        if 'overall_report' not in task_data or task_data['overall_report'] is None:
            task_data['overall_report'] = {}
        task_data['overall_report']['ai_analysis'] = report
        StorageService.save_batch_task(task_id, task_data)
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


def _generate_local_summary(total_questions, total_correct, error_distribution):
    """生成本地汇总报告（不调用 LLM）"""
    accuracy = total_correct / total_questions if total_questions > 0 else 0
    
    # 识别主要问题
    top_issues = []
    for err_type, count in sorted(error_distribution.items(), key=lambda x: -x[1]):
        if count > 0:
            top_issues.append({'issue': err_type, 'count': count})
    
    # 生成建议
    recommendations = []
    if error_distribution.get('识别错误-判断正确', 0) > 0:
        recommendations.append('优化 OCR 识别模型，提高文字识别准确率')
    if error_distribution.get('识别正确-判断错误', 0) > 0:
        recommendations.append('优化判断逻辑，改进答案比对算法')
    if error_distribution.get('AI识别幻觉', 0) > 0:
        recommendations.append('加强幻觉检测，避免 AI 脑补答案')
    if not recommendations:
        recommendations.append('整体表现良好，继续保持')
    
    return {
        'overview': {
            'total': total_questions,
            'passed': total_correct,
            'failed': total_questions - total_correct,
            'pass_rate': round(accuracy * 100, 1)
        },
        'capability_scores': {
            'recognition': round(accuracy * 100, 1),
            'judgment': round(accuracy * 100, 1),
            'overall': round(accuracy * 100, 1)
        },
        'top_issues': top_issues[:5],
        'recommendations': recommendations,
        'conclusion': f'AI 批改表现{"较差" if accuracy < 0.6 else "一般" if accuracy < 0.8 else "良好" if accuracy < 0.95 else "优秀"}，通过率 {accuracy * 100:.1f}%。{"需要重点优化。" if accuracy < 0.8 else ""}',
        'generated_by': 'local'
    }


# ========== 并行AI评估 API ==========

@batch_evaluation_bp.route('/tasks/<task_id>/ai-evaluate', methods=['POST'])
def batch_ai_evaluate(task_id):
    """执行并行AI评估（SSE流式返回）"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from routes.auth import get_current_user_id
    
    task_data = StorageService.load_batch_task(task_id)
    if not task_data:
        return jsonify({'success': False, 'error': '任务不存在'})
    
    # 获取当前用户ID
    user_id = get_current_user_id()
    print(f"[AI Evaluate] 用户ID: {user_id}")
    
    # 获取任务的学科ID
    task_subject_id = task_data.get('subject_id')
    
    # 获取并行数
    data = request.get_json() or {}
    max_workers = min(data.get('parallel', 8), 16)  # 默认8个并行，最多16个
    
    def generate():
        task_data['status'] = 'running'
        homework_items = task_data.get('homework_items', [])
        
        total_correct = 0
        total_questions = 0
        completed_count = 0
        
        yield f"data: {json.dumps({'type': 'start', 'total': len(homework_items), 'parallel': max_workers})}\n\n"
        
        def evaluate_single(item):
            """评估单个作业"""
            homework_id = item['homework_id']
            
            try:
                base_effect = None
                
                # 优先从数据集获取基准效果
                if item.get('matched_dataset'):
                    ds_data = StorageService.load_dataset(item['matched_dataset'])
                    if ds_data:
                        page_key = str(item.get('page_num'))
                        base_effect = ds_data.get('base_effects', {}).get(page_key, [])
                
                # 如果数据集没有，尝试从 baseline_effects 获取
                if not base_effect:
                    book_name = item.get('book_name', '') or item.get('homework_name', '')
                    page_num = item.get('page_num')
                    if book_name and page_num:
                        import re
                        safe_name = re.sub(r'[<>:"/\\|?*]', '_', book_name)
                        baseline_filename = f"{safe_name}_{page_num}.json"
                        baseline_data = StorageService.load_baseline_effect(baseline_filename)
                        if baseline_data:
                            base_effect = baseline_data.get('base_effect', [])
                
                homework_result = []
                try:
                    homework_result = json.loads(item.get('homework_result', '[]'))
                except:
                    pass
                
                if base_effect and homework_result:
                    # 使用AI比对，传递user_id和subject_id
                    evaluation = do_evaluation(base_effect, homework_result, use_ai_compare=True, user_id=user_id, subject_id=task_subject_id)
                    if not evaluation:
                        # AI比对失败，回退到本地计算
                        evaluation = do_evaluation(base_effect, homework_result, use_ai_compare=False, user_id=user_id, subject_id=task_subject_id)
                    
                    return {
                        'homework_id': homework_id,
                        'success': True,
                        'accuracy': evaluation['accuracy'],
                        'evaluation': evaluation,
                        'correct_count': evaluation['correct_count'],
                        'total_questions': evaluation['total_questions']
                    }
                else:
                    return {
                        'homework_id': homework_id,
                        'success': True,
                        'accuracy': 0,
                        'evaluation': {'accuracy': 0, 'total_questions': 0, 'correct_count': 0, 'error_count': 0, 'errors': []},
                        'correct_count': 0,
                        'total_questions': 0
                    }
                    
            except Exception as e:
                return {
                    'homework_id': homework_id,
                    'success': False,
                    'error': str(e)
                }
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(evaluate_single, item): item for item in homework_items}
            
            for future in as_completed(futures):
                item = futures[future]
                result = future.result()
                completed_count += 1
                
                if result['success']:
                    item['accuracy'] = result['accuracy']
                    item['evaluation'] = result['evaluation']
                    item['status'] = 'completed'
                    
                    total_correct += result['correct_count']
                    total_questions += result['total_questions']
                    
                    yield f"data: {json.dumps({'type': 'result', 'homework_id': result['homework_id'], 'accuracy': result['accuracy'], 'completed': completed_count, 'total': len(homework_items)})}\n\n"
                else:
                    item['status'] = 'failed'
                    item['error'] = result.get('error', '未知错误')
                    yield f"data: {json.dumps({'type': 'error', 'homework_id': result['homework_id'], 'error': result.get('error', ''), 'completed': completed_count, 'total': len(homework_items)})}\n\n"
        
        overall_accuracy = total_correct / total_questions if total_questions > 0 else 0
        
        # 汇总所有作业的题目类型统计: 选择题、客观填空题、非选择题
        aggregated_type_stats = {
            'choice': {'total': 0, 'correct': 0, 'accuracy': 0},
            'objective_fill': {'total': 0, 'correct': 0, 'accuracy': 0},
            'other': {'total': 0, 'correct': 0, 'accuracy': 0}
        }
        
        # 汇总bvalue细分统计
        aggregated_bvalue_stats = {
            '1': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '单选'},
            '2': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '多选'},
            '3': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '判断'},
            '4': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '填空'},
            '5': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '解答'}
        }
        
        # 汇总组合统计
        aggregated_combined_stats = {
            'objective_1': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观单选'},
            'objective_2': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观多选'},
            'objective_3': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观判断'},
            'objective_4': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观填空'},
            'objective_5': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '客观解答'},
            'subjective_1': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观单选'},
            'subjective_2': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观多选'},
            'subjective_3': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观判断'},
            'subjective_4': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观填空'},
            'subjective_5': {'total': 0, 'correct': 0, 'accuracy': 0, 'name': '主观解答'}
        }
        
        for item in homework_items:
            evaluation = item.get('evaluation', {})
            by_type = evaluation.get('by_question_type', {})
            by_bvalue = evaluation.get('by_bvalue', {})
            by_combined = evaluation.get('by_combined', {})
            
            for key in aggregated_type_stats:
                if key in by_type:
                    aggregated_type_stats[key]['total'] += by_type[key].get('total', 0)
                    aggregated_type_stats[key]['correct'] += by_type[key].get('correct', 0)
            
            for key in aggregated_bvalue_stats:
                if key in by_bvalue:
                    aggregated_bvalue_stats[key]['total'] += by_bvalue[key].get('total', 0)
                    aggregated_bvalue_stats[key]['correct'] += by_bvalue[key].get('correct', 0)
            
            for key in aggregated_combined_stats:
                if key in by_combined:
                    aggregated_combined_stats[key]['total'] += by_combined[key].get('total', 0)
                    aggregated_combined_stats[key]['correct'] += by_combined[key].get('correct', 0)
        
        # 计算汇总准确率
        for key in aggregated_type_stats:
            total_count = aggregated_type_stats[key]['total']
            correct = aggregated_type_stats[key]['correct']
            aggregated_type_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
        
        for key in aggregated_bvalue_stats:
            total_count = aggregated_bvalue_stats[key]['total']
            correct = aggregated_bvalue_stats[key]['correct']
            aggregated_bvalue_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
        
        for key in aggregated_combined_stats:
            total_count = aggregated_combined_stats[key]['total']
            correct = aggregated_combined_stats[key]['correct']
            aggregated_combined_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
        
        task_data['status'] = 'completed'
        task_data['overall_report'] = {
            'overall_accuracy': overall_accuracy,
            'total_homework': len(homework_items),
            'total_questions': total_questions,
            'correct_questions': total_correct,
            'ai_evaluated': True,
            'by_question_type': aggregated_type_stats,
            'by_bvalue': aggregated_bvalue_stats,
            'by_combined': aggregated_combined_stats
        }
        
        StorageService.save_batch_task(task_id, task_data)
        
        yield f"data: {json.dumps({'type': 'complete', 'overall_accuracy': overall_accuracy, 'total_questions': total_questions, 'correct_questions': total_correct, 'by_question_type': aggregated_type_stats, 'by_combined': aggregated_combined_stats})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@batch_evaluation_bp.route('/tasks/<task_id>/reset', methods=['POST'])
def reset_batch_task(task_id):
    """重置批量评估任务状态，允许重新评估"""
    try:
        task_data = StorageService.load_batch_task(task_id)
        if not task_data:
            return jsonify({'success': False, 'error': '任务不存在'})
        
        # 重置任务状态
        task_data['status'] = 'pending'
        task_data['overall_report'] = None
        
        # 重置所有作业项的评估状态
        for item in task_data.get('homework_items', []):
            if item.get('status') in ['completed', 'failed']:
                item['status'] = 'matched' if item.get('matched_dataset') else 'pending'
                item['accuracy'] = None
                item['evaluation'] = None
                # 保留错误信息以便调试
                if 'error' in item:
                    del item['error']
        
        # 保存更新后的任务数据
        StorageService.save_batch_task(task_id, task_data)
        
        return jsonify({
            'success': True, 
            'message': '任务已重置，可以重新进行批量评估',
            'data': task_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@batch_evaluation_bp.route('/tasks/<task_id>/refresh-datasets', methods=['POST'])
def refresh_task_datasets(task_id):
    """刷新任务中作业的数据集匹配状态"""
    try:
        task_data = StorageService.load_batch_task(task_id)
        if not task_data:
            return jsonify({'success': False, 'error': '任务不存在'})
        
        # 加载所有数据集
        datasets = []
        for filename in StorageService.list_datasets():
            ds = StorageService.load_dataset(filename[:-5])
            if ds:
                datasets.append(ds)
        
        # 按数据集包含的页码数量降序排序，优先匹配包含更多页码的数据集
        datasets.sort(key=lambda ds: len(ds.get('pages', [])), reverse=True)
        
        updated_count = 0
        
        # 重新匹配每个作业的数据集
        for item in task_data.get('homework_items', []):
            book_id = str(item.get('book_id', '')) if item.get('book_id') else ''
            page_num = item.get('page_num')
            # 确保 page_num 是整数类型用于匹配
            page_num_int = int(page_num) if page_num is not None else None
            
            old_dataset = item.get('matched_dataset')
            new_dataset = None
            
            # 查找匹配的数据集
            for ds in datasets:
                ds_book_id = str(ds.get('book_id', '')) if ds.get('book_id') else ''
                ds_pages = ds.get('pages', [])
                base_effects = ds.get('base_effects', {})
                
                # 同时检查整数和字符串形式的页码
                if ds_book_id == book_id and page_num_int is not None:
                    # 检查数据集的 pages 数组
                    page_in_pages = page_num_int in ds_pages or str(page_num_int) in [str(p) for p in ds_pages]
                    # 检查数据集的 base_effects 是否包含该页码的数据
                    page_in_effects = str(page_num_int) in base_effects
                    
                    if page_in_pages and page_in_effects:
                        new_dataset = ds.get('dataset_id')
                        break
            
            # 更新匹配状态
            if new_dataset != old_dataset:
                item['matched_dataset'] = new_dataset
                if new_dataset:
                    item['status'] = 'matched'
                else:
                    item['status'] = 'pending'
                updated_count += 1
        
        # 如果有更新，保存任务数据
        if updated_count > 0:
            StorageService.save_batch_task(task_id, task_data)
        
        return jsonify({
            'success': True,
            'message': f'已刷新数据集匹配状态，更新了 {updated_count} 个作业',
            'updated_count': updated_count,
            'data': task_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ========== 语义级评估 API ==========

@batch_evaluation_bp.route('/tasks/<task_id>/semantic-evaluate', methods=['POST'])
def semantic_evaluate_task(task_id):
    """
    对批量任务执行语义级评估
    使用 LLM 进行更精准的语义分析
    """
    config = ConfigService.load_config()
    if not config.get('deepseek_api_key'):
        return jsonify({'success': False, 'error': '请先配置 DeepSeek API Key 以使用语义评估功能'})
    
    task_data = StorageService.load_batch_task(task_id)
    if not task_data:
        return jsonify({'success': False, 'error': '任务不存在'})
    
    data = request.get_json() or {}
    subject = data.get('subject', '数学')
    question_type = data.get('question_type', '客观题')
    eval_model = data.get('eval_model', 'deepseek-v3.2')
    
    def generate():
        homework_items = task_data.get('homework_items', [])
        total_items = len(homework_items)
        completed = 0
        
        all_semantic_results = []
        
        yield f"data: {json.dumps({'type': 'start', 'total': total_items})}\n\n"
        
        for item in homework_items:
            homework_id = item.get('homework_id')
            completed += 1
            
            try:
                base_effect = None
                
                # 获取基准效果
                if item.get('matched_dataset'):
                    ds_data = StorageService.load_dataset(item['matched_dataset'])
                    if ds_data:
                        page_key = str(item.get('page_num'))
                        base_effect = ds_data.get('base_effects', {}).get(page_key, [])
                
                if not base_effect:
                    book_name = item.get('book_name', '') or item.get('homework_name', '')
                    page_num = item.get('page_num')
                    if book_name and page_num:
                        import re
                        safe_name = re.sub(r'[<>:"/\\|?*]', '_', book_name)
                        baseline_filename = f"{safe_name}_{page_num}.json"
                        baseline_data = StorageService.load_baseline_effect(baseline_filename)
                        if baseline_data:
                            base_effect = baseline_data.get('base_effect', [])
                
                homework_result = []
                try:
                    homework_result = json.loads(item.get('homework_result', '[]'))
                except:
                    pass
                
                if base_effect and homework_result:
                    # 先展开 homework_result 的 children 结构
                    flat_homework = flatten_homework_result(homework_result)
                    
                    # 构建评估项目列表
                    eval_items = []
                    hw_dict = {}
                    for i, hw_item in enumerate(flat_homework):
                        temp_idx = hw_item.get('tempIndex', i)
                        hw_dict[int(temp_idx)] = hw_item
                    
                    for i, base_item in enumerate(base_effect):
                        base_temp_idx = base_item.get('tempIndex', i)
                        if base_temp_idx is not None:
                            base_temp_idx = int(base_temp_idx)
                        else:
                            base_temp_idx = i
                        
                        hw_item = hw_dict.get(base_temp_idx, {})
                        
                        eval_items.append({
                            'index': str(base_item.get('index', i + 1)),
                            'standard_answer': str(base_item.get('answer', '') or base_item.get('mainAnswer', '')),
                            'base_user_answer': str(base_item.get('userAnswer', '')),
                            'base_correct': get_correct_value(base_item),
                            'ai_user_answer': str(hw_item.get('userAnswer', '')),
                            'ai_correct': get_correct_value(hw_item)
                        })
                    
                    # 执行语义评估
                    semantic_result = SemanticEvalService.evaluate_batch(
                        subject=subject,
                        question_type=question_type,
                        items=eval_items,
                        eval_model=eval_model
                    )
                    
                    item['semantic_evaluation'] = semantic_result
                    all_semantic_results.extend(semantic_result.get('results', []))
                    
                    yield f"data: {json.dumps({'type': 'progress', 'homework_id': homework_id, 'completed': completed, 'total': total_items, 'summary': semantic_result.get('summary', {})})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'skip', 'homework_id': homework_id, 'completed': completed, 'total': total_items, 'reason': '缺少基准效果或批改结果'})}\n\n"
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'homework_id': homework_id, 'completed': completed, 'total': total_items, 'error': str(e)})}\n\n"
        
        # 生成整体汇总报告
        if all_semantic_results:
            overall_summary = SemanticEvalService._generate_summary(all_semantic_results)
            task_data['semantic_report'] = {
                'summary': overall_summary,
                'total_questions': len(all_semantic_results),
                'eval_model': eval_model,
                'subject': subject,
                'question_type': question_type
            }
        
        task_data['semantic_evaluated'] = True
        StorageService.save_batch_task(task_id, task_data)
        
        yield f"data: {json.dumps({'type': 'complete', 'summary': task_data.get('semantic_report', {}).get('summary', {})})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


@batch_evaluation_bp.route('/tasks/<task_id>/semantic-report', methods=['GET'])
def get_semantic_report(task_id):
    """获取语义评估报告"""
    task_data = StorageService.load_batch_task(task_id)
    if not task_data:
        return jsonify({'success': False, 'error': '任务不存在'})
    
    if not task_data.get('semantic_evaluated'):
        return jsonify({'success': False, 'error': '该任务尚未进行语义评估'})
    
    semantic_report = task_data.get('semantic_report', {})
    
    # 收集所有作业的语义评估详情
    homework_details = []
    for item in task_data.get('homework_items', []):
        if item.get('semantic_evaluation'):
            homework_details.append({
                'homework_id': item.get('homework_id'),
                'book_name': item.get('book_name', ''),
                'page_num': item.get('page_num'),
                'results': item['semantic_evaluation'].get('results', []),
                'summary': item['semantic_evaluation'].get('summary', {})
            })
    
    return jsonify({
        'success': True,
        'data': {
            'overall_summary': semantic_report.get('summary', {}),
            'eval_model': semantic_report.get('eval_model', ''),
            'subject': semantic_report.get('subject', ''),
            'question_type': semantic_report.get('question_type', ''),
            'total_questions': semantic_report.get('total_questions', 0),
            'homework_details': homework_details
        }
    })


@batch_evaluation_bp.route('/evaluate-single-semantic', methods=['POST'])
def evaluate_single_semantic():
    """
    单题语义评估 API
    用于前端实时评估单道题目
    """
    config = ConfigService.load_config()
    if not config.get('deepseek_api_key'):
        return jsonify({'success': False, 'error': '请先配置 DeepSeek API Key'})
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求数据为空'})
    
    try:
        result = SemanticEvalService.evaluate_single(
            subject=data.get('subject', '数学'),
            question_type=data.get('question_type', '客观题'),
            index=data.get('index', '1'),
            standard_answer=data.get('standard_answer', ''),
            base_user_answer=data.get('base_user_answer', ''),
            base_correct=data.get('base_correct', ''),
            ai_user_answer=data.get('ai_user_answer', ''),
            ai_correct=data.get('ai_correct', ''),
            eval_model=data.get('eval_model', 'deepseek-v3.2')
        )
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
