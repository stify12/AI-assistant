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
from services.database_service import DatabaseService
from services.storage_service import StorageService
from services.llm_service import LLMService
from utils.text_utils import normalize_answer, has_format_diff

batch_evaluation_bp = Blueprint('batch_evaluation', __name__)

DATASETS_DIR = 'datasets'
BATCH_TASKS_DIR = 'batch_tasks'


# ========== 辅助函数 ==========

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
            "choice_type": str     # "single" | "multiple" | None
        }
    """
    if not question_data:
        return {
            'is_objective': False,
            'is_choice': False,
            'choice_type': None
        }
    
    # 方式1：检查 questionType 和 bvalue 字段（数据库原始格式）
    question_type = question_data.get('questionType', '')
    bvalue = str(question_data.get('bvalue', ''))
    
    # 方式2：检查 type 字段（数据集格式）
    # type: "choice" 在数据集中表示客观题（需要批改的题目），不是选择题
    type_field = question_data.get('type', '')
    
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
            # 检查是否只是格式差异
            if has_format_diff(base_user, hw_user):
                is_match = False
                error_type = '格式差异'
                explanation = f'识别内容相同但格式不同'
                severity = 'low'
            else:
                is_match = False
                error_type = '识别正确-判断错误'
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
                
                # 为更新的基准效果添加题目类型信息
                book_id = data.get('book_id')
                enriched_new_effects = enrich_base_effects_with_question_types(book_id, new_effects)
                
                # 合并：新的覆盖旧的，保留未更新的页码
                for page_key, effects in enriched_new_effects.items():
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

@batch_evaluation_bp.route('/homework', methods=['GET'])
def get_batch_homework():
    """获取可用于批量评估的作业列表"""
    subject_id = request.args.get('subject_id', type=int)
    hours = request.args.get('hours', 24, type=int)
    
    try:
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
        try:
            tasks = []
            for filename in StorageService.list_batch_tasks():
                task_id = filename[:-5]
                data = StorageService.load_batch_task(task_id)
                if data:
                    overall_report = data.get('overall_report') or {}
                    tasks.append({
                        'task_id': data.get('task_id'),
                        'name': data.get('name', ''),
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
                'name': name or f'批量评估-{datetime.now().strftime("%Y%m%d%H%M")}',
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
        
        # 构建多种索引方式的字典
        hw_dict_by_index = {str(item.get('index', '')): item for item in homework_result}
        hw_dict_by_tempindex = {}
        for i, item in enumerate(homework_result):
            temp_idx = item.get('tempIndex')
            if temp_idx is not None:
                hw_dict_by_tempindex[int(temp_idx)] = item
            else:
                hw_dict_by_tempindex[i] = item
        
        for i, base_item in enumerate(base_effect):
            idx = str(base_item.get('index', ''))
            # 基准效果的tempIndex，如果没有则使用循环索引
            base_temp_idx = base_item.get('tempIndex')
            if base_temp_idx is not None:
                base_temp_idx = int(base_temp_idx)
            else:
                base_temp_idx = i
            
            # 优先按index匹配，其次按tempIndex匹配
            hw_item = hw_dict_by_index.get(idx)
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
                    evaluation = do_evaluation(base_effect, homework_result)
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
        
        # 汇总所有作业的题目类型统计
        aggregated_type_stats = {
            'objective': {'total': 0, 'correct': 0, 'accuracy': 0},
            'subjective': {'total': 0, 'correct': 0, 'accuracy': 0},
            'choice': {'total': 0, 'correct': 0, 'accuracy': 0},
            'non_choice': {'total': 0, 'correct': 0, 'accuracy': 0}
        }
        
        for item in homework_items:
            evaluation = item.get('evaluation', {})
            by_type = evaluation.get('by_question_type', {})
            for key in aggregated_type_stats:
                if key in by_type:
                    aggregated_type_stats[key]['total'] += by_type[key].get('total', 0)
                    aggregated_type_stats[key]['correct'] += by_type[key].get('correct', 0)
        
        # 计算汇总准确率
        for key in aggregated_type_stats:
            total_count = aggregated_type_stats[key]['total']
            correct = aggregated_type_stats[key]['correct']
            aggregated_type_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
        
        task_data['status'] = 'completed'
        task_data['overall_report'] = {
            'overall_accuracy': overall_accuracy,
            'total_homework': len(homework_items),
            'total_questions': total_questions,
            'correct_questions': total_correct,
            'by_question_type': aggregated_type_stats
        }
        
        StorageService.save_batch_task(task_id, task_data)
        
        yield f"data: {json.dumps({'type': 'complete', 'overall_accuracy': overall_accuracy, 'by_question_type': aggregated_type_stats})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


def do_evaluation(base_effect, homework_result, use_ai_compare=False, user_id=None):
    """
    执行评估计算 - 全部按tempIndex匹配
    支持本地计算和AI模型比对
    包含题目类型分类统计
    
    Args:
        base_effect: 基准效果数据
        homework_result: AI批改结果
        use_ai_compare: 是否使用AI比对
        user_id: 用户ID，用于加载用户API配置
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
    
    # 题目类型分类统计
    type_stats = {
        'objective': {'total': 0, 'correct': 0, 'accuracy': 0},
        'subjective': {'total': 0, 'correct': 0, 'accuracy': 0},
        'choice': {'total': 0, 'correct': 0, 'accuracy': 0},
        'non_choice': {'total': 0, 'correct': 0, 'accuracy': 0}
    }
    
    # 如果启用AI比对
    if use_ai_compare:
        ai_result = do_ai_compare_batch(base_effect, homework_result, user_id=user_id)
        if ai_result:
            return ai_result
    
    # 构建tempIndex索引字典
    hw_dict_by_tempindex = {}
    for i, item in enumerate(homework_result):
        temp_idx = item.get('tempIndex')
        if temp_idx is not None:
            hw_dict_by_tempindex[int(temp_idx)] = item
        else:
            hw_dict_by_tempindex[i] = item
    
    for i, base_item in enumerate(base_effect):
        idx = str(base_item.get('index', ''))
        # 基准效果的tempIndex，如果没有则使用循环索引
        base_temp_idx = base_item.get('tempIndex')
        if base_temp_idx is not None:
            base_temp_idx = int(base_temp_idx)
        else:
            base_temp_idx = i
        
        # 全部按tempIndex匹配
        hw_item = hw_dict_by_tempindex.get(base_temp_idx)
        
        # 获取题目类型分类
        question_category = classify_question_type(base_item)
        
        # 更新题目类型统计 - 总数
        if question_category['is_objective']:
            type_stats['objective']['total'] += 1
        else:
            type_stats['subjective']['total'] += 1
        
        if question_category['is_choice']:
            type_stats['choice']['total'] += 1
        else:
            type_stats['non_choice']['total'] += 1
        
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
                # 检查是否只是格式差异 - 格式差异不算错误，计入正确
                if has_format_diff(base_user, hw_user):
                    is_match = True  # 格式差异不算错误
                    error_type = '格式差异'
                    explanation = f'识别内容相同但格式不同'
                    severity = 'low'
                else:
                    is_match = False
                    error_type = '识别正确-判断错误'
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
            # 更新题目类型统计 - 正确数
            if question_category['is_objective']:
                type_stats['objective']['correct'] += 1
            else:
                type_stats['subjective']['correct'] += 1
            
            if question_category['is_choice']:
                type_stats['choice']['correct'] += 1
            else:
                type_stats['non_choice']['correct'] += 1
            
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
        'by_question_type': type_stats
    }


def do_ai_compare_batch(base_effect, homework_result, user_id=None):
    """批量评估中使用AI模型比对"""
    config = ConfigService.load_config(user_id=user_id)
    
    # 获取比对提示词
    prompts_config = config.get('prompts', {})
    compare_prompt = prompts_config.get('compare_answer', '')
    
    if not compare_prompt:
        print('[AI Compare Batch] 未配置比对提示词')
        return None
    
    prompt = f"""{compare_prompt}

【基准效果数据】
{json.dumps(base_effect, ensure_ascii=False, indent=2)}

【AI批改结果数据】
{json.dumps(homework_result, ensure_ascii=False, indent=2)}

请逐题分析并输出JSON数组。"""
    
    try:
        result = LLMService.call_deepseek(
            prompt, 
            '你是专业的答案比对专家，请严格按照要求输出JSON数组。',
            timeout=120,
            user_id=user_id
        )
        
        if result.get('error'):
            print(f'[AI Compare Batch] DeepSeek调用失败: {result.get("error")}')
            return None
        
        compare_results = LLMService.extract_json_array(result.get('content', ''))
        
        if not compare_results:
            print('[AI Compare Batch] 无法解析AI返回结果')
            return None
        
        # 转换为评估结果格式
        return convert_batch_ai_compare(compare_results, base_effect, homework_result)
    except Exception as e:
        print(f'[AI Compare Batch] AI比对失败: {str(e)}')
        return None


def convert_batch_ai_compare(compare_results, base_effect, homework_result):
    """将批量AI比对结果转换为评估结果格式"""
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
    
    # 题目类型分类统计
    type_stats = {
        'objective': {'total': 0, 'correct': 0, 'accuracy': 0},
        'subjective': {'total': 0, 'correct': 0, 'accuracy': 0},
        'choice': {'total': 0, 'correct': 0, 'accuracy': 0},
        'non_choice': {'total': 0, 'correct': 0, 'accuracy': 0}
    }
    
    error_type_map = {
        'correct': None,
        'recognition_error_judgment_correct': '识别错误-判断正确',
        'recognition_error_judgment_error': '识别错误-判断错误',
        'recognition_correct_judgment_error': '识别正确-判断错误',
        'format_diff': '格式差异',
        'missing': '缺失题目',
        'hallucination': 'AI识别幻觉'
    }
    
    hw_dict = {str(item.get('index', '')): item for item in homework_result if item.get('index')}
    
    # 构建基准效果的index集合和字典
    base_dict = {str(b.get('index', '')): b for b in base_effect}
    base_indices = set(base_dict.keys())
    processed_indices = set()
    
    for result in compare_results:
        idx = str(result.get('index', ''))
        
        # 跳过不在基准效果中的题目，避免重复计数
        if idx not in base_indices or idx in processed_indices:
            continue
        processed_indices.add(idx)
        
        # 获取基准效果中的题目数据用于类型分类
        base_item = base_dict.get(idx, {})
        question_category = classify_question_type(base_item)
        
        # 更新题目类型统计 - 总数
        if question_category['is_objective']:
            type_stats['objective']['total'] += 1
        else:
            type_stats['subjective']['total'] += 1
        
        if question_category['is_choice']:
            type_stats['choice']['total'] += 1
        else:
            type_stats['non_choice']['total'] += 1
        
        is_correct = result.get('is_correct', False)
        error_type_key = result.get('error_type', 'correct')
        error_type = error_type_map.get(error_type_key)
        
        if is_correct or error_type is None:
            correct_count += 1
            # 更新题目类型统计 - 正确数
            if question_category['is_objective']:
                type_stats['objective']['correct'] += 1
            else:
                type_stats['subjective']['correct'] += 1
            
            if question_category['is_choice']:
                type_stats['choice']['correct'] += 1
            else:
                type_stats['non_choice']['correct'] += 1
        else:
            if error_type in error_distribution:
                error_distribution[error_type] += 1
            
            hw_item = hw_dict.get(idx, {})
            
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
                'error_type': error_type,
                'explanation': result.get('explanation', ''),
                'question_category': question_category
            })
    
    # 处理基准效果中存在但AI未返回结果的题目（视为缺失）
    for base_item in base_effect:
        idx = str(base_item.get('index', ''))
        if idx not in processed_indices:
            # 获取题目类型分类
            question_category = classify_question_type(base_item)
            
            # 更新题目类型统计 - 总数（缺失题目也计入总数，但不计入正确数）
            if question_category['is_objective']:
                type_stats['objective']['total'] += 1
            else:
                type_stats['subjective']['total'] += 1
            
            if question_category['is_choice']:
                type_stats['choice']['total'] += 1
            else:
                type_stats['non_choice']['total'] += 1
            
            error_distribution['缺失题目'] += 1
            errors.append({
                'index': idx,
                'base_effect': {
                    'answer': base_item.get('answer', '') or base_item.get('mainAnswer', ''),
                    'userAnswer': base_item.get('userAnswer', ''),
                    'correct': base_item.get('correct', '')
                },
                'ai_result': {'answer': '', 'userAnswer': '', 'correct': ''},
                'error_type': '缺失题目',
                'explanation': 'AI比对结果中缺少该题',
                'question_category': question_category
            })
    
    # 计算题目类型准确率
    for key in type_stats:
        total_count = type_stats[key]['total']
        correct = type_stats[key]['correct']
        type_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
    
    accuracy = correct_count / total if total > 0 else 0
    
    tp = correct_count
    fp = error_distribution.get('识别正确-判断错误', 0) + error_distribution.get('AI识别幻觉', 0)
    fn = error_distribution.get('识别错误-判断错误', 0)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
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
        'ai_compared': True
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
    
    # 获取题目类型统计数据
    objective_stats = by_question_type.get('objective', {})
    subjective_stats = by_question_type.get('subjective', {})
    choice_stats = by_question_type.get('choice', {})
    non_choice_stats = by_question_type.get('non_choice', {})
    
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
        ['客观题总数', objective_stats.get('total', 0)],
        ['客观题正确数', objective_stats.get('correct', 0)],
        ['客观题准确率', f"{(objective_stats.get('accuracy', 0) * 100):.1f}%"],
        ['主观题总数', subjective_stats.get('total', 0)],
        ['主观题正确数', subjective_stats.get('correct', 0)],
        ['主观题准确率', f"{(subjective_stats.get('accuracy', 0) * 100):.1f}%"],
        ['', ''],  # 空行
        ['选择题总数', choice_stats.get('total', 0)],
        ['选择题正确数', choice_stats.get('correct', 0)],
        ['选择题准确率', f"{(choice_stats.get('accuracy', 0) * 100):.1f}%"],
        ['非选择题总数', non_choice_stats.get('total', 0)],
        ['非选择题正确数', non_choice_stats.get('correct', 0)],
        ['非选择题准确率', f"{(non_choice_stats.get('accuracy', 0) * 100):.1f}%"]
    ]
    
    for row_idx, (label, value) in enumerate(overview_data, 1):
        ws1.cell(row=row_idx, column=1, value=label).font = Font(bold=True)
        ws1.cell(row=row_idx, column=2, value=value)
    
    # 作业明细工作表 - 添加题目类型统计列
    ws2 = wb.create_sheet("作业明细")
    headers = ['序号', '书本', '页码', '学生', '准确率', '正确数', '错误数', 
               '客观题准确率', '主观题准确率', '选择题准确率', '非选择题准确率', '状态']
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
        
        # 题目类型准确率
        obj_acc = item_by_type.get('objective', {}).get('accuracy', 0)
        subj_acc = item_by_type.get('subjective', {}).get('accuracy', 0)
        choice_acc = item_by_type.get('choice', {}).get('accuracy', 0)
        non_choice_acc = item_by_type.get('non_choice', {}).get('accuracy', 0)
        
        ws2.cell(row=row_idx, column=8, value=f"{(obj_acc * 100):.1f}%" if item_by_type.get('objective', {}).get('total', 0) > 0 else '-')
        ws2.cell(row=row_idx, column=9, value=f"{(subj_acc * 100):.1f}%" if item_by_type.get('subjective', {}).get('total', 0) > 0 else '-')
        ws2.cell(row=row_idx, column=10, value=f"{(choice_acc * 100):.1f}%" if item_by_type.get('choice', {}).get('total', 0) > 0 else '-')
        ws2.cell(row=row_idx, column=11, value=f"{(non_choice_acc * 100):.1f}%" if item_by_type.get('non_choice', {}).get('total', 0) > 0 else '-')
        ws2.cell(row=row_idx, column=12, value=item.get('status', ''))
    
    # 题目明细工作表 - 添加题目类型标注
    ws3 = wb.create_sheet("题目明细")
    detail_headers = ['作业ID', '书本', '页码', '学生', '题号', '基准答案', 'AI答案', 
                      '是否正确', '错误类型', '是否客观题', '是否选择题', '选择题类型']
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
            ws3.cell(row=detail_row, column=10, value='是' if question_category['is_objective'] else '否')
            ws3.cell(row=detail_row, column=11, value='是' if question_category['is_choice'] else '否')
            
            choice_type_text = ''
            if question_category['choice_type'] == 'single':
                choice_type_text = '单选'
            elif question_category['choice_type'] == 'multiple':
                choice_type_text = '多选'
            ws3.cell(row=detail_row, column=12, value=choice_type_text)
            
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
                    # 使用AI比对，传递user_id
                    evaluation = do_evaluation(base_effect, homework_result, use_ai_compare=True, user_id=user_id)
                    if not evaluation:
                        # AI比对失败，回退到本地计算
                        evaluation = do_evaluation(base_effect, homework_result, use_ai_compare=False, user_id=user_id)
                    
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
        
        # 汇总所有作业的题目类型统计
        aggregated_type_stats = {
            'objective': {'total': 0, 'correct': 0, 'accuracy': 0},
            'subjective': {'total': 0, 'correct': 0, 'accuracy': 0},
            'choice': {'total': 0, 'correct': 0, 'accuracy': 0},
            'non_choice': {'total': 0, 'correct': 0, 'accuracy': 0}
        }
        
        for item in homework_items:
            evaluation = item.get('evaluation', {})
            by_type = evaluation.get('by_question_type', {})
            for key in aggregated_type_stats:
                if key in by_type:
                    aggregated_type_stats[key]['total'] += by_type[key].get('total', 0)
                    aggregated_type_stats[key]['correct'] += by_type[key].get('correct', 0)
        
        # 计算汇总准确率
        for key in aggregated_type_stats:
            total_count = aggregated_type_stats[key]['total']
            correct = aggregated_type_stats[key]['correct']
            aggregated_type_stats[key]['accuracy'] = correct / total_count if total_count > 0 else 0
        
        task_data['status'] = 'completed'
        task_data['overall_report'] = {
            'overall_accuracy': overall_accuracy,
            'total_homework': len(homework_items),
            'total_questions': total_questions,
            'correct_questions': total_correct,
            'ai_evaluated': True,
            'by_question_type': aggregated_type_stats
        }
        
        StorageService.save_batch_task(task_id, task_data)
        
        yield f"data: {json.dumps({'type': 'complete', 'overall_accuracy': overall_accuracy, 'total_questions': total_questions, 'correct_questions': total_correct, 'by_question_type': aggregated_type_stats})}\n\n"
    
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