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
from services.physics_eval import normalize_physics_markdown
from services.chemistry_eval import normalize_chemistry_markdown
from utils.text_utils import normalize_answer, has_format_diff, calculate_similarity, is_fuzzy_match

batch_evaluation_bp = Blueprint('batch_evaluation', __name__)

DATASETS_DIR = 'datasets'
BATCH_TASKS_DIR = 'batch_tasks'


# ========== 辅助函数 ==========

def parse_essay_feedback(main_answer):
    """
    解析英语作文的AI批改反馈
    从 mainAnswer 字段提取结构化数据：参考得分、综合评价、针对性改进建议
    
    Args:
        main_answer: AI批改返回的 mainAnswer 字符串
        
    Returns:
        {
            'score': float,           # 参考得分
            'evaluation': str,        # 综合评价
            'suggestions': str,       # 针对性改进建议
            'raw': str               # 原始内容
        }
    """
    import re
    
    if not main_answer:
        return None
    
    result = {
        'score': None,
        'evaluation': '',
        'suggestions': '',
        'raw': main_answer
    }
    
    # 提取参考得分 - 支持多种格式
    score_patterns = [
        r'参考得分[：:]\s*([\d.]+)',
        r'得分[：:]\s*([\d.]+)',
        r'分数[：:]\s*([\d.]+)',
        r'Score[：:]\s*([\d.]+)',
    ]
    for pattern in score_patterns:
        match = re.search(pattern, main_answer)
        if match:
            try:
                result['score'] = float(match.group(1))
                break
            except:
                pass
    
    # 提取综合评价
    eval_patterns = [
        r'综合评价[：:]\s*(.+?)(?=针对性改进建议|改进建议|建议|$)',
        r'评价[：:]\s*(.+?)(?=针对性改进建议|改进建议|建议|$)',
    ]
    for pattern in eval_patterns:
        match = re.search(pattern, main_answer, re.DOTALL)
        if match:
            result['evaluation'] = match.group(1).strip()
            break
    
    # 提取改进建议
    suggestion_patterns = [
        r'针对性改进建议[：:]\s*(.+?)$',
        r'改进建议[：:]\s*(.+?)$',
        r'建议[：:]\s*(.+?)$',
    ]
    for pattern in suggestion_patterns:
        match = re.search(pattern, main_answer, re.DOTALL)
        if match:
            result['suggestions'] = match.group(1).strip()
            break
    
    return result


def check_has_essay(data_value_str, subject_id):
    """
    检查是否包含英语作文题目
    条件：subject_id=0（英语）且 data_value 中有 bvalue=8 的题目
    
    Args:
        data_value_str: zp_homework.data_value JSON字符串
        subject_id: 学科ID
        
    Returns:
        bool: 是否包含英语作文
    """
    if subject_id != 0:
        return False
    
    if not data_value_str:
        return False
    
    try:
        data_value = json.loads(data_value_str) if isinstance(data_value_str, str) else data_value_str
        if not isinstance(data_value, list):
            return False
        
        for item in data_value:
            if str(item.get('bvalue', '')) == '8':
                return True
            # 检查 children
            children = item.get('children', [])
            for child in children:
                if str(child.get('bvalue', '')) == '8':
                    return True
        return False
    except:
        return False


def extract_essay_scores(homework_items, subject_id):
    """
    从作业列表中提取英语作文评分数据
    
    判断逻辑：
    1. subject_id=0（英语）
    2. homework_result 中的 mainAnswer 包含"参考得分"关键词
    
    Args:
        homework_items: 作业项列表
        subject_id: 学科ID
        
    Returns:
        {
            'has_essay': bool,
            'essays': [...],
            'stats': {...}
        }
    """
    if subject_id != 0:
        return {'has_essay': False, 'essays': [], 'stats': None}
    
    essays = []
    scores = []
    
    for item in homework_items:
        homework_result_str = item.get('homework_result', '[]')
        try:
            homework_result = json.loads(homework_result_str) if isinstance(homework_result_str, str) else homework_result_str
        except:
            continue
        
        if not isinstance(homework_result, list):
            continue
        
        # 遍历所有题目，查找包含"参考得分"的 mainAnswer（作文评分）
        for q in homework_result:
            main_answer = q.get('mainAnswer', '')
            # 检查 mainAnswer 是否包含评分信息
            if main_answer and '参考得分' in main_answer:
                parsed = parse_essay_feedback(main_answer)
                if parsed and parsed.get('score') is not None:
                    essays.append({
                        'homework_id': item.get('homework_id'),
                        'student_id': item.get('student_id', ''),
                        'student_name': item.get('student_name', ''),
                        'index': q.get('index', ''),
                        'score': parsed['score'],
                        'evaluation': parsed['evaluation'],
                        'suggestions': parsed['suggestions'],
                        'raw': parsed['raw']
                    })
                    scores.append(parsed['score'])
            
            # 检查 children
            children = q.get('children', [])
            for child in children:
                child_main_answer = child.get('mainAnswer', '')
                if child_main_answer and '参考得分' in child_main_answer:
                    parsed = parse_essay_feedback(child_main_answer)
                    if parsed and parsed.get('score') is not None:
                        essays.append({
                            'homework_id': item.get('homework_id'),
                            'student_id': item.get('student_id', ''),
                            'student_name': item.get('student_name', ''),
                            'index': child.get('index', ''),
                            'score': parsed['score'],
                            'evaluation': parsed['evaluation'],
                            'suggestions': parsed['suggestions'],
                            'raw': parsed['raw']
                        })
                        scores.append(parsed['score'])
    
    if not essays:
        return {'has_essay': False, 'essays': [], 'stats': None}
    
    # 计算统计数据
    avg_score = sum(scores) / len(scores) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    
    # 得分分布（按1分区间）
    score_distribution = {}
    for s in scores:
        bucket = int(s)  # 向下取整到整数区间
        key = f'{bucket}-{bucket+1}'
        score_distribution[key] = score_distribution.get(key, 0) + 1
    
    return {
        'has_essay': True,
        'essays': essays,
        'stats': {
            'count': len(essays),
            'avg_score': round(avg_score, 2),
            'max_score': max_score,
            'min_score': min_score,
            'score_distribution': score_distribution
        }
    }


def is_stem_recognition(base_user, hw_user):
    """
    检测是否是"识别题干"的情况
    即AI识别的内容包含了基准答案的所有词，只是多了一些题干内容（连接词）
    
    判断逻辑（按词匹配）：
    1. 将答案拆分成词
    2. AI答案的词数必须比基准答案多
    3. 基准答案的所有词都必须按顺序出现在AI答案中
    
    例如：
    - 基准: "气态 液态 蒸气 沸腾" → ["气态", "液态", "蒸气", "沸腾"]
    - AI: "气态 变为 液态 蒸气 和 沸腾" → ["气态", "变为", "液态", "蒸气", "和", "沸腾"]
    - 结果: 识别题干（4个基准词都按顺序出现）
    
    - 基准: "36 > 能" → ["36", ">", "能"]
    - AI: "36 > 不能" → ["36", ">", "不能"]
    - 结果: 识别错误（"能" ≠ "不能"）
    """
    if not base_user or not hw_user:
        return False
    
    import re
    
    def extract_words(text):
        """提取文本中的词（按空格、标点分割）"""
        # 移除常见标点，但保留有意义的符号如 > < = 
        text = str(text).strip()
        # 用空格和中英文标点分割
        words = re.split(r'[\s，。、；：！？""''（）【】《》\-\.,;:!?\'"()\[\]{}]+', text)
        # 过滤空字符串
        return [w for w in words if w]
    
    base_words = extract_words(base_user)
    hw_words = extract_words(hw_user)
    
    if not base_words or not hw_words:
        return False
    
    # AI答案的词数必须比基准答案多
    if len(hw_words) <= len(base_words):
        return False
    
    # 检查基准答案的所有词是否按顺序出现在AI答案中
    base_idx = 0
    for hw_word in hw_words:
        if base_idx < len(base_words) and hw_word == base_words[base_idx]:
            base_idx += 1
    
    # 如果基准答案的所有词都按顺序出现了，说明是识别题干
    return base_idx == len(base_words)


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


# 学科ID映射
SUBJECT_MAP = {
    0: '英语',
    1: '语文',
    2: '数学',
    3: '物理',
    4: '化学',
    5: '生物',
    6: '地理'
}


def infer_subject_id_from_homework(task_data):
    """
    从作业数据中推断学科ID
    
    逻辑：
    1. 如果任务已有 subject_id，直接返回
    2. 否则从数据库查询所有作业的 subject_id
    3. 如果所有作业的 subject_id 相同，使用该学科并更新任务数据
    4. 如果不一致，返回 None
    
    Args:
        task_data: 任务数据字典
        
    Returns:
        subject_id: 推断出的学科ID，如果无法推断则返回 None
    """
    # 如果任务已有 subject_id，直接返回
    task_subject_id = task_data.get('subject_id')
    if task_subject_id is not None:
        return task_subject_id
    
    homework_items = task_data.get('homework_items', [])
    if not homework_items:
        return None
    
    # 批量查询所有作业的 subject_id
    homework_ids = [item.get('homework_id') for item in homework_items if item.get('homework_id')]
    if not homework_ids:
        return None
    
    try:
        placeholders = ','.join(['%s'] * len(homework_ids))
        sql = f"SELECT DISTINCT subject_id FROM zp_homework WHERE id IN ({placeholders})"
        results = DatabaseService.execute_query(sql, tuple(homework_ids))
        
        if not results:
            return None
        
        # 提取所有不同的 subject_id
        subject_ids = set(row.get('subject_id') for row in results if row.get('subject_id') is not None)
        
        # 如果所有作业的 subject_id 相同
        if len(subject_ids) == 1:
            inferred_subject_id = subject_ids.pop()
            # 更新任务数据
            task_data['subject_id'] = inferred_subject_id
            task_data['subject_name'] = SUBJECT_MAP.get(inferred_subject_id, f'学科{inferred_subject_id}')
            return inferred_subject_id
        
        # 如果 subject_id 不一致，返回 None
        return None
        
    except Exception as e:
        print(f"推断学科ID失败: {e}")
        return None


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
    根据题目数据判断题目类型（三类互不包含）
    
    分类规则：
    1. 选择题: bvalue=1(单选)、2(多选)、3(判断)
    2. 客观填空题: questionType='objective' 且 bvalue='4'
       - 如果有children，大题本身不计入，只统计children
    3. 主观题: 其他所有（bvalue=5解答题，或无bvalue等）
    
    Args:
        question_data: 题目数据
        
    Returns:
        {
            "is_choice": bool,       # 是否选择题（含判断题）
            "is_fill": bool,         # 是否客观填空题
            "is_subjective": bool,   # 是否主观题
            "is_parent": bool,       # 是否大题（有children，不参与统计）
            "choice_type": str       # "single" | "multiple" | "judge" | None
        }
    """
    if not question_data:
        return {
            'is_choice': False,
            'is_fill': False,
            'is_subjective': True,
            'is_parent': False,
            'choice_type': None
        }
    
    bvalue = str(question_data.get('bvalue', ''))
    question_type = question_data.get('questionType', '')
    children = question_data.get('children', [])
    
    # 判断是否为大题（有children）- 大题本身不参与统计
    is_parent = bool(children and len(children) > 0)
    if is_parent:
        return {
            'is_choice': False,
            'is_fill': False,
            'is_subjective': False,
            'is_parent': True,
            'choice_type': None
        }
    
    # 选择题: bvalue=1(单选)、2(多选)、3(判断)
    is_choice = bvalue in ('1', '2', '3')
    choice_type = None
    if bvalue == '1':
        choice_type = 'single'
    elif bvalue == '2':
        choice_type = 'multiple'
    elif bvalue == '3':
        choice_type = 'judge'
    
    # 客观填空题: questionType='objective' 且 bvalue='4'
    is_fill = (question_type == 'objective' and bvalue == '4')
    
    # 主观题: 非选择题且非客观填空题
    is_subjective = not is_choice and not is_fill
    
    return {
        'is_choice': is_choice,
        'is_fill': is_fill,
        'is_subjective': is_subjective,
        'is_parent': is_parent,
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
            
            # 解析题目类型信息（包括子题）
            type_map = {}
            if rows:
                data_value = rows[0].get('data_value', '[]')
                try:
                    data_items = json.loads(data_value) if data_value else []
                    
                    def add_to_type_map(item):
                        """递归添加题目及其子题到 type_map"""
                        temp_idx = item.get('tempIndex', 0)
                        idx = str(item.get('index', ''))
                        type_info = {
                            'questionType': item.get('questionType', ''),
                            'bvalue': str(item.get('bvalue', ''))
                        }
                        type_map[temp_idx] = type_info
                        type_map[f'idx_{idx}'] = type_info
                        # 递归处理子题
                        for child in item.get('children', []):
                            add_to_type_map(child)
                    
                    for item in data_items:
                        add_to_type_map(item)
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


def remove_index_prefix(text):
    """
    移除答案前面的题号前缀
    如: "(1)答案内容" -> "答案内容"
        "（2）答案内容" -> "答案内容"
        "1.答案内容" -> "答案内容"
        "1、答案内容" -> "答案内容"
    """
    import re
    if not text:
        return text
    text = str(text).strip()
    # 匹配常见的题号前缀格式：(1) （1） 1. 1、 1) 等
    pattern = r'^[\(（]?\d+[\)）]?[\.、\s]*'
    return re.sub(pattern, '', text).strip()


def classify_error(base_item, hw_item, is_chinese=False, fuzzy_threshold=0.85, ignore_index_prefix=True):
    """
    详细的错误分类逻辑
    返回: (is_match, error_type, explanation, severity, similarity)
    
    Args:
        base_item: 基准效果数据
        hw_item: AI批改结果
        is_chinese: 是否是语文学科
        fuzzy_threshold: 模糊匹配阈值
        ignore_index_prefix: 是否忽略题号前缀差异
    """
    from utils.text_utils import is_fuzzy_match
    
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
    similarity_value = None
    
    # 获取题目类型
    question_category = classify_question_type(base_item)
    bvalue = str(base_item.get('bvalue', ''))
    
    # 语文非选择题使用模糊匹配（包括客观填空题和主观题）
    is_chinese_fuzzy = is_chinese and not question_category['is_choice']
    
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
            # 语文非选择题：尝试模糊匹配
            if is_chinese_fuzzy:
                fuzzy_match, similarity_value = is_fuzzy_match(base_user, hw_user, fuzzy_threshold)
                if fuzzy_match:
                    is_match = True
                    # 相似度100%算作完全识别成功，不设置error_type
                    if similarity_value >= 0.9999:
                        error_type = None
                        explanation = ''
                    else:
                        error_type = '识别差异-判断正确'
                        explanation = f'模糊匹配通过（相似度{similarity_value*100:.1f}%）：基准="{base_user}"，AI="{hw_user}"'
                        severity = 'low'
                else:
                    is_match = False
                    error_type = '识别错误-判断错误'
                    explanation = f'用户答案不一致（相似度{similarity_value*100:.1f}%）：基准="{base_user}"，AI="{hw_user}"'
                    severity = 'high'
            else:
                is_match = False
                error_type = '识别错误-判断错误'
                explanation = f'用户答案不一致：基准="{base_user}"，AI="{hw_user}"'
                severity = 'high'
    else:
        # 标准化答案进行比较
        if ignore_index_prefix:
            # 先移除题号前缀，再标准化
            norm_base_user = normalize_answer(remove_index_prefix(base_user))
            norm_hw_user = normalize_answer(remove_index_prefix(hw_user))
            norm_base_answer = normalize_answer(remove_index_prefix(base_answer))
        else:
            # 直接标准化，不移除题号前缀
            norm_base_user = normalize_answer(base_user)
            norm_hw_user = normalize_answer(hw_user)
            norm_base_answer = normalize_answer(base_answer)
        
        user_match = norm_base_user == norm_hw_user
        correct_match = base_correct == hw_correct
        
        # 检测是否只是题号前缀差异（移除前缀后完全一致）
        has_index_prefix_diff = ignore_index_prefix and (normalize_answer(base_user) != normalize_answer(hw_user)) and user_match
        
        # 检测AI识别幻觉：学生答错了 + AI识别的用户答案≠基准用户答案 + AI识别的用户答案=标准答案
        # 即AI把学生的错误手写答案"脑补"成了标准答案
        if base_correct == 'no' and not user_match and norm_hw_user == norm_base_answer:
            is_match = False
            error_type = 'AI识别幻觉'
            explanation = f'AI将学生答案"{base_user}"识别为"{hw_user}"（标准答案），属于识别幻觉'
            severity = 'high'
        elif user_match and correct_match:
            # 检查是否有题号前缀差异
            if has_index_prefix_diff:
                is_match = True  # 不计入错误
                error_type = '识别差异-判断正确'
                explanation = f'AI多识别了题号前缀，判断正确：基准="{base_user}"，AI="{hw_user}"'
                severity = 'low'
                similarity_value = 1.0  # 移除前缀后完全一致
            else:
                is_match = True
        elif user_match and not correct_match:
            # 用户答案识别正确，但判断结果不同
            is_match = False
            error_type = '识别正确-判断错误'
            if has_format_diff(base_user, hw_user):
                explanation = f'识别正确（有格式差异）但判断错误：基准={base_correct}，AI={hw_correct}'
            else:
                explanation = f'识别正确但判断错误：基准={base_correct}，AI={hw_correct}'
            severity = 'high'
        elif not user_match and correct_match:
            # 语文非选择题：优先尝试模糊匹配
            if is_chinese_fuzzy:
                fuzzy_match, similarity_value = is_fuzzy_match(base_user, hw_user, fuzzy_threshold)
                if fuzzy_match:
                    is_match = True  # 不计入错误
                    # 相似度100%算作完全识别成功，不设置error_type
                    if similarity_value >= 0.9999:
                        error_type = None
                        explanation = ''
                    else:
                        error_type = '识别差异-判断正确'
                        explanation = f'模糊匹配通过（相似度{similarity_value*100:.1f}%），判断正确：基准="{base_user}"，AI="{hw_user}"'
                        severity = 'low'
                else:
                    is_match = False
                    error_type = '识别错误-判断正确'
                    explanation = f'识别不准确（相似度{similarity_value*100:.1f}%）但判断结果正确：基准="{base_user}"，AI="{hw_user}"'
                    severity = 'medium'
            # 非语文的填空题：检测是否是"识别题干"的情况
            elif not is_chinese and bvalue == '4' and is_stem_recognition(base_user, hw_user):
                is_match = True  # 不计入错误
                error_type = '识别题干-判断正确'
                explanation = f'AI多识别了题干内容，但判断正确：基准="{base_user}"，AI="{hw_user}"'
                severity = 'low'
            else:
                is_match = False
                error_type = '识别错误-判断正确'
                explanation = f'识别不准确但判断结果正确：基准="{base_user}"，AI="{hw_user}"'
                severity = 'medium'
        else:
            # 语文非选择题：即使判断不一致，也检查模糊匹配
            if is_chinese_fuzzy:
                fuzzy_match, similarity_value = is_fuzzy_match(base_user, hw_user, fuzzy_threshold)
                if fuzzy_match:
                    is_match = False
                    error_type = '识别正确-判断错误'
                    explanation = f'识别相似（相似度{similarity_value*100:.1f}%）但判断错误：基准={base_correct}，AI={hw_correct}'
                    severity = 'high'
                else:
                    is_match = False
                    error_type = '识别错误-判断错误'
                    explanation = f'识别和判断都有误（相似度{similarity_value*100:.1f}%）：基准="{base_user}/{base_correct}"，AI="{hw_user}/{hw_correct}"'
                    severity = 'high'
            else:
                is_match = False
                error_type = '识别错误-判断错误'
                explanation = f'识别和判断都有误：基准="{base_user}/{base_correct}"，AI="{hw_user}/{hw_correct}"'
                severity = 'high'
    
    return is_match, error_type, explanation, severity, similarity_value


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


@batch_evaluation_bp.route('/datasets/check-duplicate', methods=['GET'])
def check_duplicate_datasets():
    """
    检查是否存在重复数据集
    
    Query params:
        book_id: 书本ID
        pages: 页码列表（逗号分隔，如 "1,2,3"）
    
    Returns:
        {
            "success": true,
            "has_duplicate": true/false,
            "duplicates": [
                {
                    "dataset_id": "abc12345",
                    "name": "学生A基准",
                    "book_name": "七年级英语上册",
                    "pages": [1, 2, 3],
                    "question_count": 50,
                    "created_at": "2024-01-01T10:00:00"
                }
            ]
        }
    """
    book_id = request.args.get('book_id')
    pages_str = request.args.get('pages', '')
    
    if not book_id:
        return jsonify({'success': False, 'error': '缺少 book_id 参数'})
    
    if not pages_str:
        return jsonify({'success': False, 'error': '缺少 pages 参数'})
    
    try:
        # 解析页码列表
        pages = [int(p.strip()) for p in pages_str.split(',') if p.strip()]
        if not pages:
            return jsonify({'success': False, 'error': '页码列表为空'})
        
        # 查找所有匹配的数据集
        duplicates = []
        all_datasets = StorageService.get_all_datasets_summary()
        
        for ds in all_datasets:
            if ds.get('book_id') != book_id:
                continue
            
            ds_pages = ds.get('pages', [])
            # 检查是否有任何页码重叠
            if any(p in ds_pages for p in pages):
                duplicates.append({
                    'dataset_id': ds['dataset_id'],
                    'name': ds.get('name', ''),
                    'book_name': ds.get('book_name', ''),
                    'pages': ds_pages,
                    'question_count': ds.get('question_count', 0),
                    'created_at': ds.get('created_at', '')
                })
        
        return jsonify({
            'success': True,
            'has_duplicate': len(duplicates) > 0,
            'duplicates': duplicates
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': f'页码格式错误: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@batch_evaluation_bp.route('/matching-datasets', methods=['GET'])
def get_matching_datasets():
    """
    查询匹配的数据集列表
    
    根据 book_id 和 page_num 查询所有匹配的数据集，
    按创建时间倒序排列（最新的排在前面）
    
    Query params:
        book_id: 书本ID（必填）
        page_num: 页码（必填，正整数）
    
    Returns:
        {
            "success": true,
            "data": [
                {
                    "dataset_id": "abc12345",
                    "name": "学生A基准",
                    "book_name": "七年级英语上册",
                    "pages": [30, 31],
                    "question_count": 50,
                    "created_at": "2024-01-01T10:00:00"
                }
            ]
        }
    
    Error responses:
        - 400: 缺少书本ID
        - 400: 缺少页码
        - 400: 页码必须是正整数
    """
    book_id = request.args.get('book_id')
    page_num_str = request.args.get('page_num')
    
    # 参数验证：book_id 必填
    if not book_id:
        return jsonify({'success': False, 'error': '缺少书本ID'}), 400
    
    # 参数验证：page_num 必填
    if not page_num_str:
        return jsonify({'success': False, 'error': '缺少页码'}), 400
    
    # 参数验证：page_num 必须是正整数
    try:
        page_num = int(page_num_str)
        if page_num <= 0:
            return jsonify({'success': False, 'error': '页码必须是正整数'}), 400
    except ValueError:
        return jsonify({'success': False, 'error': '页码必须是正整数'}), 400
    
    try:
        # 调用 StorageService 获取匹配的数据集
        matching_datasets = StorageService.get_matching_datasets(book_id, page_num)
        
        # 返回结果（已按 created_at 倒序排列）
        return jsonify({
            'success': True,
            'data': matching_datasets
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@batch_evaluation_bp.route('/datasets', methods=['GET', 'POST'])
def batch_datasets():
    """数据集管理"""
    StorageService.ensure_dir(DATASETS_DIR)
    
    if request.method == 'GET':
        book_id = request.args.get('book_id')
        search = request.args.get('search', '').strip()
        
        try:
            # 使用 get_all_datasets_summary 获取更好的性能
            all_datasets = StorageService.get_all_datasets_summary()
            
            datasets = []
            for ds in all_datasets:
                # 按 book_id 过滤
                if book_id and ds.get('book_id') != book_id:
                    continue
                
                # 按 name 模糊搜索（不区分大小写）
                if search:
                    ds_name = ds.get('name', '') or ''
                    if search.lower() not in ds_name.lower():
                        continue
                
                datasets.append({
                    'dataset_id': ds['dataset_id'],
                    'name': ds.get('name', ''),
                    'book_id': ds.get('book_id'),
                    'book_name': ds.get('book_name', ''),
                    'pages': ds.get('pages', []),
                    'question_count': ds.get('question_count', 0),
                    'description': ds.get('description', ''),
                    'created_at': ds.get('created_at', '')
                })
            
            # 按 created_at 倒序排列（get_all_datasets_summary 已排序，但确保一致性）
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
        book_name = data.get('book_name', '')
        subject_id = data.get('subject_id')
        pages = data.get('pages', [])
        base_effects = data.get('base_effects', {})
        name = data.get('name', '').strip() if data.get('name') else ''
        description = data.get('description', '').strip() if data.get('description') else ''
        
        if not book_id or not pages:
            return jsonify({'success': False, 'error': '缺少必要参数'})
        
        # 如果前端没有传递 book_name 或 subject_id，从数据库查询
        if not book_name or subject_id is None:
            try:
                sql = "SELECT book_name, subject_id FROM zp_make_book WHERE id = %s"
                rows = DatabaseService.execute_query(sql, (book_id,))
                if rows:
                    if not book_name:
                        book_name = rows[0].get('book_name', '')
                    if subject_id is None:
                        subject_id = rows[0].get('subject_id')
                    print(f"[CreateDataset] Fetched from DB: book_name={book_name}, subject_id={subject_id}")
            except Exception as e:
                print(f"[CreateDataset] Warning: Failed to fetch book info: {e}")
        
        # 验证 name 不能为空或纯空白（如果提供了 name 参数）
        if 'name' in data and data.get('name') is not None:
            if not name:
                return jsonify({'success': False, 'error': '数据集名称不能为空'})
        
        try:
            dataset_id = str(uuid.uuid4())[:8]
            print(f"[CreateDataset] Creating dataset: {dataset_id}, name={name}, book_name={book_name}, subject_id={subject_id}, pages={pages}")
            
            # 为每个页码的题目添加类型信息
            enriched_base_effects = enrich_base_effects_with_question_types(book_id, base_effects)
            
            StorageService.save_dataset(dataset_id, {
                'dataset_id': dataset_id,
                'book_id': book_id,
                'book_name': book_name,
                'subject_id': subject_id,
                'name': name,  # 传递 name，StorageService 会处理空值情况
                'description': description,
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
            
            # 更新 name 字段（如果提供）
            if 'name' in update_data:
                new_name = update_data.get('name', '').strip() if update_data.get('name') else ''
                # 验证 name 不能为空或纯空白
                if update_data.get('name') is not None and not new_name:
                    return jsonify({'success': False, 'error': '数据集名称不能为空'})
                if new_name:
                    data['name'] = new_name
            
            # 更新 description 字段（如果提供）
            if 'description' in update_data:
                data['description'] = update_data.get('description', '').strip() if update_data.get('description') else ''
            
            # 检查是否需要删除页码
            delete_pages = update_data.get('delete_pages', [])
            if delete_pages:
                existing_effects = data.get('base_effects', {})
                for page in delete_pages:
                    page_str = str(page)
                    if page_str in existing_effects:
                        del existing_effects[page_str]
                        print(f"[UpdateDataset] Deleted page {page_str} from dataset {dataset_id}")
                data['base_effects'] = existing_effects
            
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
                
                # 处理删除页码的情况：如果某页的 effects 为 null 或空数组，则删除该页
                pages_to_delete = []
                for page_key, effects in new_effects.items():
                    if effects is None or (isinstance(effects, list) and len(effects) == 0):
                        pages_to_delete.append(str(page_key))
                    
                # 删除标记为删除的页码
                for page_str in pages_to_delete:
                    if page_str in existing_effects:
                        del existing_effects[page_str]
                        print(f"[UpdateDataset] Deleted page {page_str} (empty effects) from dataset {dataset_id}")
                    del new_effects[page_str]
                
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
            
            # 更新页码列表（基于实际有数据的页码）
            existing_effects = data.get('base_effects', {})
            all_pages = set(int(p) for p in existing_effects.keys() if existing_effects.get(p))
            data['pages'] = sorted(all_pages)
            
            # 更新题目数量
            question_count = 0
            for page_data in data['base_effects'].values():
                if isinstance(page_data, list):
                    question_count += len(page_data)
            data['question_count'] = question_count
            
            # 如果所有页面都被删除，删除整个数据集
            if len(data['pages']) == 0:
                StorageService.delete_dataset(dataset_id)
                print(f"[UpdateDataset] Deleted entire dataset {dataset_id} (no pages left)")
                return jsonify({'success': True, 'deleted': True, 'message': '数据集已删除（所有页面已移除）'})
            
            data['updated_at'] = datetime.now().isoformat()
            StorageService.save_dataset(dataset_id, data)
            
            print(f"[UpdateDataset] Updated dataset {dataset_id}, pages={data.get('pages')}, question_count={question_count}")
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
                   COUNT(DISTINCT h.student_id) AS student_count,
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
            homework_count = row.get('homework_count', 0)
            student_count = row.get('student_count', 0)
            # 计算每个学生平均作业数
            avg_homework_per_student = round(homework_count / student_count, 1) if student_count > 0 else 0
            
            tasks.append({
                'hw_publish_id': str(row['hw_publish_id']),  # 转为字符串避免JS精度丢失
                'task_name': row.get('task_name', ''),
                'homework_count': homework_count,
                'student_count': student_count,
                'avg_homework_per_student': avg_homework_per_student,
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
    hw_publish_id = request.args.get('hw_publish_id')  # 改为字符串，避免大整数精度问题
    hw_publish_ids = request.args.get('hw_publish_ids', '')  # 支持多个ID，逗号分隔
    
    try:
        # 解析多个作业任务ID（保持字符串形式，避免大整数精度问题）
        publish_id_list = []
        if hw_publish_ids:
            for x in hw_publish_ids.split(','):
                x = x.strip()
                if x and x.isdigit():
                    publish_id_list.append(x)
            print(f"[get_batch_homework] 解析hw_publish_ids: {hw_publish_ids} -> {publish_id_list}")
        elif hw_publish_id:
            publish_id_list = [str(hw_publish_id)]
        
        # 根据是否有hw_publish_id决定查询条件
        if publish_id_list:
            placeholders = ','.join(['%s'] * len(publish_id_list))
            sql = f"""
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
                  AND h.hw_publish_id IN ({placeholders})
            """
            params = list(publish_id_list)
            
            if subject_id is not None:
                sql += " AND h.subject_id = %s"
                params.append(subject_id)
            
            sql += " ORDER BY h.create_time DESC LIMIT 500"
            print(f"[get_batch_homework] 查询参数: {params}")
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
        fuzzy_threshold = data.get('fuzzy_threshold', 0.85)  # 语文主观题模糊匹配阈值，默认85%
        
        if not homework_ids:
            return jsonify({'success': False, 'error': '请选择作业'})
        
        try:
            placeholders = ','.join(['%s'] * len(homework_ids))
            sql = f"""
                SELECT h.id, h.hw_publish_id, h.student_id, h.subject_id, h.page_num, h.pic_path, h.homework_result, h.data_value,
                       p.content AS homework_name, s.name AS student_name,
                       b.id AS book_id, b.book_name AS book_name
                FROM zp_homework h
                LEFT JOIN zp_homework_publish p ON h.hw_publish_id = p.id
                LEFT JOIN zp_student s ON h.student_id = s.id
                LEFT JOIN zp_make_book b ON p.book_id = b.id
                WHERE h.id IN ({placeholders})
            """
            rows = DatabaseService.execute_query(sql, tuple(homework_ids))
            
            # 如果前端没有传 subject_id，从作业数据中自动获取
            if subject_id is None and rows:
                subject_id = rows[0].get('subject_id')
            
            # 获取学科名称
            subject_map = {
                0: '英语',
                1: '语文',
                2: '数学',
                3: '物理',
                4: '化学',
                5: '生物',
                6: '地理'
            }
            subject_name = subject_map.get(subject_id, f'学科{subject_id}') if subject_id is not None else ''
            
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
            
            # 按创建时间倒序排序，优先匹配最新创建的数据集 (Requirements 4.3, 5.3)
            datasets.sort(key=lambda ds: ds.get('created_at', ''), reverse=True)
            
            homework_items = []
            for row in rows:
                book_id = str(row.get('book_id', '')) if row.get('book_id') else ''
                page_num = row.get('page_num')
                # 确保 page_num 是整数类型用于匹配
                page_num_int = int(page_num) if page_num is not None else None
                
                matched_dataset = None
                matched_dataset_name = ''  # 记录匹配的数据集名称
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
                            matched_dataset_name = ds.get('name', '')  # 获取数据集名称
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
                    'data_value': row.get('data_value', '[]'),  # 题目类型信息来源
                    'matched_dataset': matched_dataset,
                    'matched_dataset_name': matched_dataset_name,  # 记录数据集名称
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
                'fuzzy_threshold': fuzzy_threshold,  # 语文主观题模糊匹配阈值
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
            
            # 检查是否有英语作文，提取作文评分数据
            subject_id = data.get('subject_id')
            homework_items = data.get('homework_items', [])
            essay_data = extract_essay_scores(homework_items, subject_id)
            
            # 将作文数据添加到返回结果中
            data['essay_data'] = essay_data
            
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
    """获取任务中某个作业的评估详情（实时重新计算）"""
    try:
        task_data = StorageService.load_batch_task(task_id)
        if not task_data:
            return jsonify({'success': False, 'error': '任务不存在'})
        
        # 获取任务的学科ID，如果没有则从作业中推断
        task_subject_id = infer_subject_id_from_homework(task_data)
        
        # 查找对应的作业
        homework_item = None
        for item in task_data.get('homework_items', []):
            if str(item.get('homework_id')) == str(homework_id):
                homework_item = item
                break
        
        if not homework_item:
            return jsonify({'success': False, 'error': '作业不存在'})
        
        # 获取基准效果
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
        
        # 获取 data_value（题目类型信息来源）
        data_value = []
        try:
            data_value = json.loads(homework_item.get('data_value', '[]'))
        except:
            pass
        
        # 获取模糊匹配阈值和忽略题号前缀设置
        fuzzy_threshold = task_data.get('fuzzy_threshold', 0.85)
        ignore_index_prefix = task_data.get('ignore_index_prefix', True)
        
        # 实时重新计算评估结果（使用正确的学科ID，传递 data_value 获取题目类型）
        if base_effect and homework_result:
            print(f"[DEBUG] get_homework_detail: 调用 do_evaluation, base_effect={len(base_effect)}, homework_result={len(homework_result)}")
            evaluation = do_evaluation(
                base_effect, 
                homework_result, 
                subject_id=task_subject_id, 
                fuzzy_threshold=fuzzy_threshold, 
                ignore_index_prefix=ignore_index_prefix,
                data_value=data_value
            )
            print(f"[DEBUG] get_homework_detail: 评估完成, errors={len(evaluation.get('errors', []))}")
            if evaluation.get('errors'):
                for err in evaluation['errors'][:2]:
                    print(f"[DEBUG]   题{err.get('index')}: similarity={err.get('similarity')}")
        else:
            evaluation = {
                'accuracy': 0,
                'total_questions': 0,
                'correct_count': 0,
                'error_count': 0,
                'errors': []
            }
        
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
                'accuracy': evaluation.get('accuracy', 0),
                'matched_dataset': homework_item.get('matched_dataset', ''),
                'matched_dataset_name': homework_item.get('matched_dataset_name', ''),
                'base_effect': base_effect,
                'ai_result': homework_result,
                'evaluation': {
                    'accuracy': evaluation.get('accuracy', 0),
                    'total_questions': evaluation.get('total_questions', 0),
                    'correct_count': evaluation.get('correct_count', 0),
                    'error_count': evaluation.get('error_count', 0),
                    'errors': evaluation.get('errors', [])
                }
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@batch_evaluation_bp.route('/tasks/<task_id>/select-dataset', methods=['POST'])
def select_dataset_for_homework(task_id):
    """
    为作业选择数据集
    
    支持批量为多个作业选择同一数据集。
    更换数据集时会清除已有评估结果，重置状态为 pending。
    
    Request body:
        {
            "homework_ids": ["hw1", "hw2"],  # 作业ID列表（必填）
            "dataset_id": "abc12345"         # 数据集ID（必填）
        }
    
    Returns:
        {
            "success": true,
            "updated_count": 2
        }
    
    Error responses:
        - 400: 缺少作业ID列表
        - 400: 缺少数据集ID
        - 404: 任务不存在
        - 404: 数据集不存在
    
    _Requirements: 4.5, 4.6, 5.4_
    """
    # 加载任务数据
    task_data = StorageService.load_batch_task(task_id)
    if not task_data:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    # 解析请求参数
    req_data = request.get_json() or {}
    homework_ids = req_data.get('homework_ids')
    dataset_id = req_data.get('dataset_id')
    
    # 参数验证：homework_ids 必填
    if not homework_ids:
        return jsonify({'success': False, 'error': '缺少作业ID列表'}), 400
    
    # 参数验证：homework_ids 必须是列表
    if not isinstance(homework_ids, list):
        return jsonify({'success': False, 'error': '作业ID列表格式错误'}), 400
    
    # 参数验证：dataset_id 必填
    if not dataset_id:
        return jsonify({'success': False, 'error': '缺少数据集ID'}), 400
    
    # 加载数据集，验证数据集存在
    dataset = StorageService.load_dataset(dataset_id)
    if not dataset:
        return jsonify({'success': False, 'error': '数据集不存在'}), 404
    
    # 获取数据集名称
    dataset_name = dataset.get('name', '')
    
    # 遍历作业列表，更新匹配的作业
    updated_count = 0
    homework_items = task_data.get('homework_items', [])
    
    # 将 homework_ids 转换为字符串集合，便于匹配
    homework_ids_set = set(str(hw_id) for hw_id in homework_ids)
    
    for item in homework_items:
        item_id = str(item.get('homework_id', ''))
        
        # 检查是否在待更新列表中
        if item_id in homework_ids_set:
            # 更新数据集信息
            item['matched_dataset'] = dataset_id
            item['matched_dataset_name'] = dataset_name
            
            # 清除已有评估结果
            item['accuracy'] = None
            item['precision'] = None
            item['recall'] = None
            item['f1'] = None
            item['correct_count'] = None
            item['wrong_count'] = None
            item['total_count'] = None
            item['error_details'] = None
            
            # 重置状态为 pending
            item['status'] = 'pending'
            
            updated_count += 1
    
    # 保存更新后的任务数据
    StorageService.save_batch_task(task_id, task_data)
    
    return jsonify({
        'success': True,
        'updated_count': updated_count
    })


@batch_evaluation_bp.route('/tasks/<task_id>/evaluate', methods=['POST'])
def batch_evaluate(task_id):
    """执行批量评估（SSE流式返回）"""
    task_data = StorageService.load_batch_task(task_id)
    if not task_data:
        return jsonify({'success': False, 'error': '任务不存在'})
    
    # 获取任务的学科ID，如果没有则从作业中推断，并保存到任务数据
    task_subject_id = infer_subject_id_from_homework(task_data)
    
    # 保存推断的学科信息到任务数据（确保重新评估时使用正确的学科逻辑）
    if task_subject_id is not None and task_data.get('subject_id') != task_subject_id:
        task_data['subject_id'] = task_subject_id
        task_data['subject_name'] = SUBJECT_MAP.get(task_subject_id, '未知')
    
    # 获取前端传递的设置参数
    req_data = request.get_json() or {}
    fuzzy_threshold = req_data.get('fuzzy_threshold', 0.85)
    ignore_index_prefix = req_data.get('ignore_index_prefix', True)
    
    # 保存设置到任务数据
    task_data['fuzzy_threshold'] = fuzzy_threshold
    task_data['ignore_index_prefix'] = ignore_index_prefix
    
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
                
                # 解析 data_value 获取题目类型信息
                data_value = []
                try:
                    data_value = json.loads(item.get('data_value', '[]'))
                except:
                    pass
                
                if base_effect and homework_result:
                    # 传递学科ID、模糊匹配阈值和 data_value（题目类型信息来源）
                    evaluation = do_evaluation(base_effect, homework_result, subject_id=task_subject_id, fuzzy_threshold=fuzzy_threshold, ignore_index_prefix=ignore_index_prefix, data_value=data_value)
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
                item['evaluation'] = {'accuracy': 0, 'total_questions': 0, 'correct_count': 0, 'error_count': 0, 'errors': [], 'by_question_type': {}, 'by_bvalue': {}, 'by_combined': {}}
                yield f"data: {json.dumps({'type': 'error', 'homework_id': homework_id, 'error': str(e)})}\n\n"
        
        overall_accuracy = total_correct / total_questions if total_questions > 0 else 0
        
        # 汇总所有作业的题目类型统计: 选择题、客观填空题、主观题
        aggregated_type_stats = {
            'choice': {'total': 0, 'correct': 0, 'accuracy': 0},
            'objective_fill': {'total': 0, 'correct': 0, 'accuracy': 0},
            'subjective': {'total': 0, 'correct': 0, 'accuracy': 0}
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
            evaluation = item.get('evaluation') or {}
            by_type = evaluation.get('by_question_type') or {}
            by_bvalue = evaluation.get('by_bvalue') or {}
            by_combined = evaluation.get('by_combined') or {}
            
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


def do_evaluation(base_effect, homework_result, use_ai_compare=False, user_id=None, subject_id=None, fuzzy_threshold=0.85, ignore_index_prefix=True, data_value=None):
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
        fuzzy_threshold: 语文主观题模糊匹配阈值，默认0.85 (85%)
        ignore_index_prefix: 是否忽略题号前缀差异，默认True
        data_value: 题目原始数据（包含 bvalue, questionType 等类型信息）
    """
    total = len(base_effect)
    correct_count = 0
    errors = []
    error_distribution = {
        '识别错误-判断正确': 0,
        '识别错误-判断错误': 0,
        '识别正确-判断错误': 0,
        '识别题干-判断正确': 0,
        '识别差异-判断正确': 0,  # 新增：语文主观题模糊匹配
        '格式差异': 0,
        '缺失题目': 0,
        'AI识别幻觉': 0
    }
    
    # 从 data_value 构建题目类型映射（按 index 和 tempIndex）
    type_map = {}
    if data_value:
        def add_to_type_map(item):
            """递归添加题目及其子题到 type_map"""
            temp_idx = item.get('tempIndex')
            idx = str(item.get('index', ''))
            normalized_idx = normalize_index(idx)
            type_info = {
                'questionType': item.get('questionType', ''),
                'bvalue': str(item.get('bvalue', ''))
            }
            if temp_idx is not None:
                type_map[f'temp_{temp_idx}'] = type_info
            if normalized_idx:
                type_map[f'idx_{normalized_idx}'] = type_info
            # 递归处理子题
            for child in item.get('children', []):
                add_to_type_map(child)
        
        for item in data_value:
            add_to_type_map(item)
    
    # 题目类型分类统计: 选择题、客观填空题、主观题（三类互不包含）
    type_stats = {
        'choice': {'total': 0, 'correct': 0, 'accuracy': 0},           # 选择题 (bvalue=1,2,3)
        'objective_fill': {'total': 0, 'correct': 0, 'accuracy': 0},   # 客观填空题 (questionType=objective且bvalue=4)
        'subjective': {'total': 0, 'correct': 0, 'accuracy': 0}        # 主观题 (其他)
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
    
    # 展开 homework_result 的 children 结构为扁平数组
    # AI批改结果可能有嵌套的children（如大题包含小题），需要展开后按题号匹配
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
        
        # 匹配方式：优先按题号(index)匹配，其次按tempIndex匹配
        # 因为基准效果可能是小题格式（如例3(1)），需要按题号匹配
        hw_item = hw_dict_by_index.get(normalized_idx)
        if not hw_item:
            hw_item = hw_dict_by_tempindex.get(base_temp_idx)
        
        # 获取题目类型分类
        # 优先从 type_map（data_value）获取类型信息
        # 其次从 base_item 获取，最后从 hw_item 获取
        type_info = None
        if type_map:
            # 优先按题号匹配
            type_info = type_map.get(f'idx_{normalized_idx}')
            # 其次按 tempIndex 匹配
            if not type_info:
                type_info = type_map.get(f'temp_{base_temp_idx}')
        
        if type_info:
            # 从 type_map 获取到类型信息，构造一个临时对象用于分类
            type_source = {
                'bvalue': type_info.get('bvalue', ''),
                'questionType': type_info.get('questionType', '')
            }
        elif base_item.get('bvalue'):
            type_source = base_item
        elif hw_item and hw_item.get('bvalue'):
            type_source = hw_item
        else:
            type_source = base_item
        
        question_category = classify_question_type(type_source)
        bvalue = str(type_source.get('bvalue', ''))
        
        # 跳过大题（有children的题目不参与统计）
        if question_category['is_parent']:
            continue
        
        # 更新题目类型统计 - 总数 (选择题、客观填空题、主观题，三类互不包含)
        if question_category['is_choice']:
            type_stats['choice']['total'] += 1
        elif question_category['is_fill']:
            type_stats['objective_fill']['total'] += 1
        elif question_category['is_subjective']:
            type_stats['subjective']['total'] += 1
        
        # 更新bvalue细分统计 - 总数
        if bvalue in bvalue_stats:
            bvalue_stats[bvalue]['total'] += 1
        
        # 更新组合统计 - 总数（基于新分类）
        if question_category['is_choice']:
            obj_key = 'objective'
        elif question_category['is_fill']:
            obj_key = 'objective'
        else:
            obj_key = 'subjective'
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
        
        # 物理学科(subject_id=3)：先将 LaTeX/Markdown 格式转换为纯文本
        # 这样可以正确比较 "$1\text{m}^3$" 和 "1m³" 这类格式差异
        is_physics = subject_id == 3
        if is_physics:
            base_answer = normalize_physics_markdown(base_answer)
            base_user = normalize_physics_markdown(base_user)
            hw_answer = normalize_physics_markdown(hw_answer)
            hw_user = normalize_physics_markdown(hw_user)
        
        # 化学学科(subject_id=4)：先将 LaTeX 化学式/方程式转换为纯文本
        # 这样可以正确比较 "$MgCl_2$" 和 "MgCl₂" 这类格式差异
        is_chemistry = subject_id == 4
        if is_chemistry:
            base_answer = normalize_chemistry_markdown(base_answer)
            base_user = normalize_chemistry_markdown(base_user)
            hw_answer = normalize_chemistry_markdown(hw_answer)
            hw_user = normalize_chemistry_markdown(hw_user)
        
        is_match = True
        error_type = None
        explanation = ''
        severity = 'medium'
        similarity_value = None  # 记录相似度值（用于模糊匹配）
        
        # 判断是否为语文非选择题（用于模糊匹配）
        # 语文学科的所有非选择题（包括客观填空题和主观题）都使用模糊匹配
        is_chinese_fuzzy = is_chinese and not question_category['is_choice']
        print(f"[DEBUG] do_evaluation 题{idx}: is_chinese={is_chinese}, is_choice={question_category['is_choice']}, is_chinese_fuzzy={is_chinese_fuzzy}, is_physics={is_physics}, is_chemistry={is_chemistry}")
        
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
                # 语文非选择题：尝试模糊匹配
                if is_chinese_fuzzy:
                    fuzzy_match, similarity_value = is_fuzzy_match(base_user, hw_user, fuzzy_threshold)
                    if fuzzy_match:
                        is_match = True
                        # 相似度100%算作完全识别成功，不设置error_type
                        if similarity_value >= 0.9999:
                            error_type = None
                            explanation = ''
                        else:
                            error_type = '识别差异-判断正确'
                            explanation = f'模糊匹配通过（相似度{similarity_value*100:.1f}%）：基准="{base_user}"，AI="{hw_user}"'
                            severity = 'low'
                    else:
                        is_match = False
                        error_type = '识别错误-判断错误'
                        explanation = f'用户答案不一致（相似度{similarity_value*100:.1f}%）：基准="{base_user}"，AI="{hw_user}"'
                        severity = 'high'
                else:
                    is_match = False
                    error_type = '识别错误-判断错误'
                    explanation = f'用户答案不一致：基准="{base_user}"，AI="{hw_user}"'
                    severity = 'high'
        else:
            # 标准化答案进行比较
            if ignore_index_prefix:
                # 先移除题号前缀，再标准化
                norm_base_user = normalize_answer(remove_index_prefix(base_user))
                norm_hw_user = normalize_answer(remove_index_prefix(hw_user))
                norm_base_answer = normalize_answer(remove_index_prefix(base_answer))
            else:
                # 直接标准化，不移除题号前缀
                norm_base_user = normalize_answer(base_user)
                norm_hw_user = normalize_answer(hw_user)
                norm_base_answer = normalize_answer(base_answer)
            
            user_match = norm_base_user == norm_hw_user
            correct_match = base_correct == hw_correct
            
            # 检测是否只是题号前缀差异（移除前缀后完全一致）
            has_index_prefix_diff = ignore_index_prefix and (normalize_answer(base_user) != normalize_answer(hw_user)) and user_match
            
            # 检测AI识别幻觉：学生答错了 + AI识别的用户答案≠基准用户答案 + AI识别的用户答案=标准答案
            # 即AI把学生的错误手写答案"脑补"成了标准答案
            if base_correct == 'no' and not user_match and norm_hw_user == norm_base_answer:
                is_match = False
                error_type = 'AI识别幻觉'
                explanation = f'AI将学生答案"{base_user}"识别为"{hw_user}"（标准答案），属于识别幻觉'
                severity = 'high'
            elif user_match and correct_match:
                # 检查是否有题号前缀差异
                if has_index_prefix_diff:
                    is_match = True  # 不计入错误
                    error_type = '识别差异-判断正确'
                    explanation = f'AI多识别了题号前缀，判断正确：基准="{base_user}"，AI="{hw_user}"'
                    severity = 'low'
                    similarity_value = 1.0  # 移除前缀后完全一致
                else:
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
                # 语文非选择题：优先尝试模糊匹配（语文不使用识别题干逻辑）
                if is_chinese_fuzzy:
                    fuzzy_match, similarity_value = is_fuzzy_match(base_user, hw_user, fuzzy_threshold)
                    if fuzzy_match:
                        is_match = True  # 不计入错误
                        # 相似度100%算作完全识别成功，不设置error_type
                        if similarity_value >= 0.9999:
                            error_type = None
                            explanation = ''
                        else:
                            error_type = '识别差异-判断正确'
                            explanation = f'模糊匹配通过（相似度{similarity_value*100:.1f}%），判断正确：基准="{base_user}"，AI="{hw_user}"'
                            severity = 'low'
                    else:
                        is_match = False
                        error_type = '识别错误-判断正确'
                        explanation = f'识别不准确（相似度{similarity_value*100:.1f}%）但判断结果正确：基准="{base_user}"，AI="{hw_user}"'
                        severity = 'medium'
                # 非语文的填空题：检测是否是"识别题干"的情况
                elif not is_chinese and bvalue == '4' and is_stem_recognition(base_user, hw_user):
                    is_match = True  # 不计入错误
                    error_type = '识别题干-判断正确'
                    explanation = f'AI多识别了题干内容，但判断正确：基准="{base_user}"，AI="{hw_user}"'
                    severity = 'low'
                else:
                    is_match = False
                    error_type = '识别错误-判断正确'
                    explanation = f'识别不准确但判断结果正确：基准="{base_user}"，AI="{hw_user}"'
                    severity = 'medium'
            else:
                # 语文非选择题：即使判断不一致，也检查模糊匹配
                if is_chinese_fuzzy:
                    fuzzy_match, similarity_value = is_fuzzy_match(base_user, hw_user, fuzzy_threshold)
                    if fuzzy_match:
                        # 识别相似但判断不同
                        is_match = False
                        error_type = '识别正确-判断错误'
                        explanation = f'识别相似（相似度{similarity_value*100:.1f}%）但判断错误：基准={base_correct}，AI={hw_correct}'
                        severity = 'high'
                    else:
                        is_match = False
                        error_type = '识别错误-判断错误'
                        explanation = f'识别和判断都有误（相似度{similarity_value*100:.1f}%）：基准="{base_user}/{base_correct}"，AI="{hw_user}/{hw_correct}"'
                        severity = 'high'
                else:
                    is_match = False
                    error_type = '识别错误-判断错误'
                    explanation = f'识别和判断都有误：基准="{base_user}/{base_correct}"，AI="{hw_user}/{hw_correct}"'
                    severity = 'high'
        
        if is_match:
            correct_count += 1
            # 更新题目类型统计 - 正确数 (选择题、客观填空题、主观题)
            if question_category['is_choice']:
                type_stats['choice']['correct'] += 1
            elif question_category['is_fill']:
                type_stats['objective_fill']['correct'] += 1
            elif question_category['is_subjective']:
                type_stats['subjective']['correct'] += 1
            
            # 更新bvalue细分统计 - 正确数
            if bvalue in bvalue_stats:
                bvalue_stats[bvalue]['correct'] += 1
            
            # 更新组合统计 - 正确数
            if combined_key in combined_stats:
                combined_stats[combined_key]['correct'] += 1
            
            # 格式差异、识别题干、识别差异虽然计入正确，但仍记录到分布和详情中
            if error_type in ('格式差异', '识别题干-判断正确', '识别差异-判断正确'):
                error_distribution[error_type] = error_distribution.get(error_type, 0) + 1
                # 记录到详情中展示
                recognition_match = normalize_answer(base_user) == normalize_answer(hw_user) if base_user or hw_user else None
                judgment_match = base_correct == hw_correct if base_correct and hw_correct else None
                error_record = {
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
                    'error_type': error_type,
                    'explanation': explanation,
                    'severity': severity,
                    'severity_code': severity,
                    'analysis': {
                        'recognition_match': recognition_match,
                        'judgment_match': judgment_match,
                        'is_hallucination': False,
                        'similarity': similarity_value  # 添加相似度值
                    },
                    'question_category': question_category,
                    'is_stem_recognition': error_type == '识别题干-判断正确',
                    'is_fuzzy_match': error_type == '识别差异-判断正确',
                    'similarity': similarity_value  # 顶层也添加相似度值，方便前端访问
                }
                errors.append(error_record)
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
                    'is_hallucination': error_type == 'AI识别幻觉',
                    'similarity': similarity_value  # 添加相似度值
                },
                'similarity': similarity_value,  # 顶层也添加相似度值
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
    
    # 计算幻觉率（幻觉数 / 总题目数）
    hallucination_count = error_distribution.get('AI识别幻觉', 0)
    hallucination_rate = hallucination_count / total if total > 0 else 0
    
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
        '识别题干-判断正确': 0,
        '格式差异': 0,
        '缺失题目': 0,
        'AI识别幻觉': 0
    }
    
    # 题目类型分类统计: 选择题、客观填空题、主观题（三类互不包含）
    type_stats = {
        'choice': {'total': 0, 'correct': 0, 'accuracy': 0},           # 选择题 (bvalue=1,2,3)
        'objective_fill': {'total': 0, 'correct': 0, 'accuracy': 0},   # 客观填空题 (questionType=objective且bvalue=4)
        'subjective': {'total': 0, 'correct': 0, 'accuracy': 0}        # 主观题 (其他)
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
        
        # 跳过大题（有children的题目不参与统计）
        if question_category['is_parent']:
            continue
        
        # 更新题目类型统计 - 总数 (选择题、客观填空题、主观题)
        if question_category['is_choice']:
            type_stats['choice']['total'] += 1
        elif question_category['is_fill']:
            type_stats['objective_fill']['total'] += 1
        elif question_category['is_subjective']:
            type_stats['subjective']['total'] += 1
        
        # 更新bvalue细分统计 - 总数
        if bvalue in bvalue_stats:
            bvalue_stats[bvalue]['total'] += 1
        
        # 更新组合统计 - 总数（基于新分类）
        if question_category['is_choice'] or question_category['is_fill']:
            obj_key = 'objective'
        else:
            obj_key = 'subjective'
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
            # 更新题目类型统计 - 正确数 (选择题、客观填空题、主观题)
            if question_category['is_choice']:
                type_stats['choice']['correct'] += 1
            elif question_category['is_fill']:
                type_stats['objective_fill']['correct'] += 1
            elif question_category['is_subjective']:
                type_stats['subjective']['correct'] += 1
            
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
    
    # 计算幻觉率（幻觉数 / 总题目数）
    hallucination_count = error_distribution.get('AI识别幻觉', 0)
    hallucination_rate = hallucination_count / total if total > 0 else 0
    
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
    """导出Excel报告 - 增强版，包含可视化图表和详细总结"""
    from openpyxl.chart import PieChart, BarChart, RadarChart, Reference
    from openpyxl.chart.label import DataLabelList
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import Alignment, Font as XlFont, PatternFill as XlFill
    
    task_data = StorageService.load_batch_task(task_id)
    if not task_data:
        return jsonify({'success': False, 'error': '任务不存在'})
    
    wb = Workbook()
    
    header_font = Font(bold=True, size=12, color="FFFFFF")
    header_fill = PatternFill(start_color="1D1D1F", end_color="1D1D1F", fill_type="solid")
    border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    
    # 样式定义
    title_font = Font(bold=True, size=16, color="1D1D1F")
    subtitle_font = Font(bold=True, size=14, color="1D1D1F")
    section_font = Font(bold=True, size=12, color="1D1D1F")
    highlight_fill = PatternFill(start_color="E3F9E5", end_color="E3F9E5", fill_type="solid")
    warning_fill = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
    error_fill = PatternFill(start_color="FFEEF0", end_color="FFEEF0", fill_type="solid")
    center_align = Alignment(horizontal='center', vertical='center')
    
    overall = task_data.get('overall_report', {})
    by_question_type = overall.get('by_question_type', {})
    homework_items = task_data.get('homework_items', [])
    
    # 获取题目类型统计数据
    choice_stats = by_question_type.get('choice', {})
    objective_fill_stats = by_question_type.get('objective_fill', {})
    subjective_stats = by_question_type.get('subjective', {})
    
    # ========== 1. 评估总结表 (Summary) ==========
    ws1 = wb.active
    ws1.title = "评估总结"
    ws1.column_dimensions['A'].width = 25
    ws1.column_dimensions['B'].width = 20
    ws1.column_dimensions['C'].width = 20
    ws1.column_dimensions['D'].width = 20
    ws1.column_dimensions['E'].width = 20
    
    # 标题
    ws1.merge_cells('A1:E1')
    ws1['A1'] = "AI批改效果评估报告"
    ws1['A1'].font = title_font
    ws1['A1'].alignment = center_align
    ws1.row_dimensions[1].height = 30
    
    # 基本信息
    ws1['A3'] = "任务名称"
    ws1['B3'] = task_data.get('name', '')
    ws1['A4'] = "创建时间"
    ws1['B4'] = task_data.get('created_at', '')
    ws1['A5'] = "评估状态"
    ws1['B5'] = '已完成' if task_data.get('status') == 'completed' else task_data.get('status', '')
    ws1['A6'] = "测试条件"
    ws1['B6'] = task_data.get('test_condition_name', '-')
    
    for row in range(3, 7):
        ws1[f'A{row}'].font = section_font
    
    # 核心指标
    ws1['A8'] = "核心评估指标"
    ws1['A8'].font = subtitle_font
    ws1.merge_cells('A8:E8')
    
    metrics_headers = ['指标', '数值', '说明']
    for col, h in enumerate(metrics_headers, 1):
        cell = ws1.cell(row=9, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    
    accuracy = overall.get('overall_accuracy', 0)
    total_q = overall.get('total_questions', 0)
    correct_q = overall.get('correct_questions', 0)
    error_q = total_q - correct_q
    
    metrics_data = [
        ['总体准确率', f"{accuracy * 100:.1f}%", '正确题目数/总题目数'],
        ['总作业数', overall.get('total_homework', 0), '参与评估的作业数量'],
        ['总题目数', total_q, '所有作业的题目总数'],
        ['正确题目数', correct_q, 'AI批改与基准一致的题目'],
        ['错误题目数', error_q, 'AI批改与基准不一致的题目'],
    ]
    
    for row_idx, (label, value, desc) in enumerate(metrics_data, 10):
        ws1.cell(row=row_idx, column=1, value=label).border = border
        cell = ws1.cell(row=row_idx, column=2, value=value)
        cell.border = border
        cell.alignment = center_align
        if row_idx == 10:  # 准确率行高亮
            cell.fill = highlight_fill if accuracy >= 0.9 else warning_fill if accuracy >= 0.7 else error_fill
        ws1.cell(row=row_idx, column=3, value=desc).border = border
    
    # 题型分类统计
    ws1['A16'] = "题型分类统计"
    ws1['A16'].font = subtitle_font
    ws1.merge_cells('A16:E16')
    
    type_headers = ['题型', '总数', '正确数', '错误数', '准确率']
    for col, h in enumerate(type_headers, 1):
        cell = ws1.cell(row=17, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    
    type_data = [
        ['选择题', choice_stats.get('total', 0), choice_stats.get('correct', 0), 
         choice_stats.get('total', 0) - choice_stats.get('correct', 0), choice_stats.get('accuracy', 0)],
        ['客观填空题', objective_fill_stats.get('total', 0), objective_fill_stats.get('correct', 0),
         objective_fill_stats.get('total', 0) - objective_fill_stats.get('correct', 0), objective_fill_stats.get('accuracy', 0)],
        ['主观题', subjective_stats.get('total', 0), subjective_stats.get('correct', 0),
         subjective_stats.get('total', 0) - subjective_stats.get('correct', 0), subjective_stats.get('accuracy', 0)],
    ]
    
    for row_idx, row_data in enumerate(type_data, 18):
        for col_idx, val in enumerate(row_data, 1):
            cell = ws1.cell(row=row_idx, column=col_idx)
            if col_idx == 5:  # 准确率列
                cell.value = f"{val * 100:.1f}%" if row_data[1] > 0 else '-'
            else:
                cell.value = val
            cell.border = border
            if col_idx > 1:
                cell.alignment = center_align
    
    # ========== 2. 错误分析表 (Error Analysis) ==========
    ws_err = wb.create_sheet("错误分析")
    ws_err.column_dimensions['A'].width = 25
    ws_err.column_dimensions['B'].width = 15
    ws_err.column_dimensions['C'].width = 15
    ws_err.column_dimensions['D'].width = 40
    
    # 统计错误类型分布
    error_distribution = {}
    all_errors = []
    page_error_count = {}  # 按页码统计错误
    question_error_count = {}  # 按题号统计错误
    
    for item in homework_items:
        if item.get('status') == 'completed' and item.get('evaluation'):
            errors = item['evaluation'].get('errors', [])
            page_num = str(item.get('page_num', '?'))
            
            for err in errors:
                err_type = err.get('error_type', '未分类')
                error_distribution[err_type] = error_distribution.get(err_type, 0) + 1
                
                # 按页码统计
                page_error_count[page_num] = page_error_count.get(page_num, 0) + 1
                
                # 按题号统计
                q_idx = err.get('index', '?')
                q_key = f"P{page_num}-{q_idx}"
                question_error_count[q_key] = question_error_count.get(q_key, 0) + 1
                
                all_errors.append({
                    'page': page_num,
                    'index': q_idx,
                    'type': err_type,
                    'explanation': err.get('explanation', ''),
                    'book': item.get('book_name', ''),
                    'student': item.get('student_name', '')
                })
    
    # 错误类型分布表
    ws_err['A1'] = "错误类型分布"
    ws_err['A1'].font = subtitle_font
    ws_err.merge_cells('A1:D1')
    
    err_headers = ['错误类型', '数量', '占比', '说明']
    for col, h in enumerate(err_headers, 1):
        cell = ws_err.cell(row=2, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    
    total_errors = sum(error_distribution.values()) or 1
    error_type_desc = {
        '识别错误-判断正确': '用户答案识别不准确，但最终判断结果正确',
        '识别错误-判断错误': '用户答案识别不准确，且判断结果错误',
        '识别正确-判断错误': '用户答案识别正确，但判断结果错误',
        '缺失题目': 'AI批改结果中缺少该题目',
        'AI识别幻觉': 'AI将错误答案识别为标准答案',
        '格式差异': '答案格式不一致但内容相同'
    }
    
    sorted_errors = sorted(error_distribution.items(), key=lambda x: -x[1])
    for row_idx, (err_type, count) in enumerate(sorted_errors, 3):
        ws_err.cell(row=row_idx, column=1, value=err_type).border = border
        ws_err.cell(row=row_idx, column=2, value=count).border = border
        ws_err.cell(row=row_idx, column=3, value=f"{count/total_errors*100:.1f}%").border = border
        ws_err.cell(row=row_idx, column=4, value=error_type_desc.get(err_type, '')).border = border
    
    # 错误类型饼图数据区域 (用于图表)
    chart_start_row = len(sorted_errors) + 5
    ws_err.cell(row=chart_start_row, column=1, value="图表数据区")
    ws_err.cell(row=chart_start_row, column=1).font = section_font
    
    for row_idx, (err_type, count) in enumerate(sorted_errors, chart_start_row + 1):
        ws_err.cell(row=row_idx, column=1, value=err_type)
        ws_err.cell(row=row_idx, column=2, value=count)
    
    # 创建错误类型饼图
    if sorted_errors:
        pie = PieChart()
        pie.title = "错误类型分布"
        labels = Reference(ws_err, min_col=1, min_row=chart_start_row+1, max_row=chart_start_row+len(sorted_errors))
        data = Reference(ws_err, min_col=2, min_row=chart_start_row, max_row=chart_start_row+len(sorted_errors))
        pie.add_data(data, titles_from_data=True)
        pie.set_categories(labels)
        pie.width = 15
        pie.height = 10
        pie.dataLabels = DataLabelList()
        pie.dataLabels.showPercent = True
        pie.dataLabels.showVal = True
        ws_err.add_chart(pie, "F2")
    
    # 高频错误题目 TOP10
    top_error_row = chart_start_row + len(sorted_errors) + 3
    ws_err.cell(row=top_error_row, column=1, value="高频错误题目 TOP10")
    ws_err.cell(row=top_error_row, column=1).font = subtitle_font
    ws_err.merge_cells(f'A{top_error_row}:D{top_error_row}')
    
    top_q_headers = ['题目', '错误次数', '占比']
    for col, h in enumerate(top_q_headers, 1):
        cell = ws_err.cell(row=top_error_row+1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    
    sorted_questions = sorted(question_error_count.items(), key=lambda x: -x[1])[:10]
    for row_idx, (q_key, count) in enumerate(sorted_questions, top_error_row+2):
        ws_err.cell(row=row_idx, column=1, value=q_key).border = border
        ws_err.cell(row=row_idx, column=2, value=count).border = border
        ws_err.cell(row=row_idx, column=3, value=f"{count/total_errors*100:.1f}%").border = border
    
    # 高频错误题目柱状图
    if sorted_questions:
        bar_data_start = top_error_row + 2
        bar = BarChart()
        bar.title = "高频错误题目 TOP10"
        bar.type = "col"
        bar.style = 10
        data = Reference(ws_err, min_col=2, min_row=bar_data_start-1, max_row=bar_data_start+len(sorted_questions)-1)
        cats = Reference(ws_err, min_col=1, min_row=bar_data_start, max_row=bar_data_start+len(sorted_questions)-1)
        bar.add_data(data, titles_from_data=True)
        bar.set_categories(cats)
        bar.width = 15
        bar.height = 10
        bar.shape = 4
        ws_err.add_chart(bar, "F18")
    
    # ========== 3. 可视化图表表 (Charts) ==========
    ws_chart = wb.create_sheet("可视化图表")
    ws_chart.column_dimensions['A'].width = 20
    ws_chart.column_dimensions['B'].width = 15
    ws_chart.column_dimensions['C'].width = 15
    ws_chart.column_dimensions['D'].width = 15
    ws_chart.column_dimensions['E'].width = 15
    
    # 题型准确率对比数据
    ws_chart['A1'] = "题型准确率对比"
    ws_chart['A1'].font = subtitle_font
    
    type_chart_headers = ['题型', '准确率%', '总数', '正确数']
    for col, h in enumerate(type_chart_headers, 1):
        cell = ws_chart.cell(row=2, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    
    type_chart_data = [
        ['选择题', choice_stats.get('accuracy', 0) * 100, choice_stats.get('total', 0), choice_stats.get('correct', 0)],
        ['客观填空题', objective_fill_stats.get('accuracy', 0) * 100, objective_fill_stats.get('total', 0), objective_fill_stats.get('correct', 0)],
        ['主观题', subjective_stats.get('accuracy', 0) * 100, subjective_stats.get('total', 0), subjective_stats.get('correct', 0)],
    ]
    
    for row_idx, row_data in enumerate(type_chart_data, 3):
        for col_idx, val in enumerate(row_data, 1):
            cell = ws_chart.cell(row=row_idx, column=col_idx, value=val)
            cell.border = border
    
    # 题型准确率柱状图
    bar2 = BarChart()
    bar2.title = "题型准确率对比"
    bar2.type = "col"
    bar2.style = 10
    data2 = Reference(ws_chart, min_col=2, min_row=2, max_row=5)
    cats2 = Reference(ws_chart, min_col=1, min_row=3, max_row=5)
    bar2.add_data(data2, titles_from_data=True)
    bar2.set_categories(cats2)
    bar2.width = 12
    bar2.height = 8
    bar2.y_axis.scaling.max = 100
    bar2.y_axis.title = "准确率 %"
    ws_chart.add_chart(bar2, "F1")
    
    # 按页码错误分布
    ws_chart['A8'] = "按页码错误分布"
    ws_chart['A8'].font = subtitle_font
    
    page_headers = ['页码', '错误数']
    for col, h in enumerate(page_headers, 1):
        cell = ws_chart.cell(row=9, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    
    sorted_pages = sorted(page_error_count.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999)
    for row_idx, (page, count) in enumerate(sorted_pages, 10):
        ws_chart.cell(row=row_idx, column=1, value=f"第{page}页").border = border
        ws_chart.cell(row=row_idx, column=2, value=count).border = border
    
    # 页码错误柱状图
    if sorted_pages:
        bar3 = BarChart()
        bar3.title = "按页码错误分布"
        bar3.type = "col"
        bar3.style = 11
        data3 = Reference(ws_chart, min_col=2, min_row=9, max_row=9+len(sorted_pages))
        cats3 = Reference(ws_chart, min_col=1, min_row=10, max_row=9+len(sorted_pages))
        bar3.add_data(data3, titles_from_data=True)
        bar3.set_categories(cats3)
        bar3.width = 12
        bar3.height = 8
        ws_chart.add_chart(bar3, "F15")
    
    # 正确/错误对比饼图数据
    pie_row = 10 + len(sorted_pages) + 2
    ws_chart.cell(row=pie_row, column=1, value="正确/错误分布")
    ws_chart.cell(row=pie_row, column=1).font = subtitle_font
    
    ws_chart.cell(row=pie_row+1, column=1, value="类别")
    ws_chart.cell(row=pie_row+1, column=2, value="数量")
    ws_chart.cell(row=pie_row+2, column=1, value="正确")
    ws_chart.cell(row=pie_row+2, column=2, value=correct_q)
    ws_chart.cell(row=pie_row+3, column=1, value="错误")
    ws_chart.cell(row=pie_row+3, column=2, value=error_q)
    
    pie2 = PieChart()
    pie2.title = "正确/错误分布"
    labels2 = Reference(ws_chart, min_col=1, min_row=pie_row+2, max_row=pie_row+3)
    data_pie2 = Reference(ws_chart, min_col=2, min_row=pie_row+1, max_row=pie_row+3)
    pie2.add_data(data_pie2, titles_from_data=True)
    pie2.set_categories(labels2)
    pie2.width = 10
    pie2.height = 8
    pie2.dataLabels = DataLabelList()
    pie2.dataLabels.showPercent = True
    pie2.dataLabels.showVal = True
    ws_chart.add_chart(pie2, "F30")
    
    # 评估指标雷达图数据
    radar_row = pie_row + 6
    ws_chart.cell(row=radar_row, column=1, value="评估指标雷达图数据")
    ws_chart.cell(row=radar_row, column=1).font = subtitle_font
    
    radar_headers = ['指标', '得分']
    for col, h in enumerate(radar_headers, 1):
        cell = ws_chart.cell(row=radar_row+1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
    
    choice_acc = choice_stats.get('accuracy', 0) * 100 if choice_stats.get('total', 0) > 0 else accuracy * 100
    fill_acc = objective_fill_stats.get('accuracy', 0) * 100 if objective_fill_stats.get('total', 0) > 0 else accuracy * 100
    
    radar_data = [
        ['总体准确率', accuracy * 100],
        ['选择题准确率', choice_acc],
        ['填空题准确率', fill_acc],
        ['完整性', 100 if total_q > 0 else 0],
        ['一致性', accuracy * 100],
    ]
    
    for row_idx, (label, val) in enumerate(radar_data, radar_row+2):
        ws_chart.cell(row=row_idx, column=1, value=label)
        ws_chart.cell(row=row_idx, column=2, value=round(val, 1))
    
    # 创建雷达图
    radar = RadarChart()
    radar.title = "评估指标雷达图"
    radar.type = "filled"
    radar_labels = Reference(ws_chart, min_col=1, min_row=radar_row+2, max_row=radar_row+6)
    radar_values = Reference(ws_chart, min_col=2, min_row=radar_row+1, max_row=radar_row+6)
    radar.add_data(radar_values, titles_from_data=True)
    radar.set_categories(radar_labels)
    radar.width = 12
    radar.height = 10
    ws_chart.add_chart(radar, "F45")
    
    # 按书本统计柱状图
    by_book = overall.get('by_book', {})
    if by_book:
        book_row = radar_row + 10
        ws_chart.cell(row=book_row, column=1, value="按书本准确率统计")
        ws_chart.cell(row=book_row, column=1).font = subtitle_font
        
        book_headers = ['书本', '准确率%', '作业数']
        for col, h in enumerate(book_headers, 1):
            cell = ws_chart.cell(row=book_row+1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
        
        for row_idx, (book_id, book_data) in enumerate(by_book.items(), book_row+2):
            ws_chart.cell(row=row_idx, column=1, value=book_data.get('book_name', book_id)[:15]).border = border
            ws_chart.cell(row=row_idx, column=2, value=round(book_data.get('accuracy', 0) * 100, 1)).border = border
            ws_chart.cell(row=row_idx, column=3, value=book_data.get('homework_count', 0)).border = border
        
        if len(by_book) > 0:
            bar4 = BarChart()
            bar4.title = "按书本准确率统计"
            bar4.type = "col"
            bar4.style = 12
            data4 = Reference(ws_chart, min_col=2, min_row=book_row+1, max_row=book_row+1+len(by_book))
            cats4 = Reference(ws_chart, min_col=1, min_row=book_row+2, max_row=book_row+1+len(by_book))
            bar4.add_data(data4, titles_from_data=True)
            bar4.set_categories(cats4)
            bar4.width = 12
            bar4.height = 8
            bar4.y_axis.scaling.max = 100
            ws_chart.add_chart(bar4, "F60")
    
    # ========== 4. 作业明细表 ==========
    ws2 = wb.create_sheet("作业明细")
    headers = ['序号', '书本', '页码', '学生', '准确率', '正确数', '错误数', 
               '选择题准确率', '客观填空题准确率', '主观题准确率', '状态']
    for col, header in enumerate(headers, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    
    for row_idx, item in enumerate(homework_items, 2):
        eval_data = item.get('evaluation', {})
        item_by_type = eval_data.get('by_question_type', {})
        
        ws2.cell(row=row_idx, column=1, value=row_idx - 1)
        ws2.cell(row=row_idx, column=2, value=item.get('book_name', ''))
        ws2.cell(row=row_idx, column=3, value=item.get('page_num', ''))
        ws2.cell(row=row_idx, column=4, value=item.get('student_name', ''))
        
        item_acc = item.get('accuracy', 0)
        acc_cell = ws2.cell(row=row_idx, column=5, value=f"{item_acc * 100:.1f}%")
        if item_acc >= 0.9:
            acc_cell.fill = highlight_fill
        elif item_acc < 0.7:
            acc_cell.fill = error_fill
        
        ws2.cell(row=row_idx, column=6, value=eval_data.get('correct_count', 0))
        ws2.cell(row=row_idx, column=7, value=eval_data.get('error_count', 0))
        
        # 题目类型准确率
        choice_acc = item_by_type.get('choice', {}).get('accuracy', 0)
        obj_fill_acc = item_by_type.get('objective_fill', {}).get('accuracy', 0)
        other_acc = item_by_type.get('other', {}).get('accuracy', 0)
        
        ws2.cell(row=row_idx, column=8, value=f"{choice_acc * 100:.1f}%" if item_by_type.get('choice', {}).get('total', 0) > 0 else '-')
        ws2.cell(row=row_idx, column=9, value=f"{obj_fill_acc * 100:.1f}%" if item_by_type.get('objective_fill', {}).get('total', 0) > 0 else '-')
        ws2.cell(row=row_idx, column=10, value=f"{other_acc * 100:.1f}%" if item_by_type.get('other', {}).get('total', 0) > 0 else '-')
        ws2.cell(row=row_idx, column=11, value='已完成' if item.get('status') == 'completed' else item.get('status', ''))
    
    # 设置列宽
    for col in range(1, 12):
        ws2.column_dimensions[get_column_letter(col)].width = 15
    
    # ========== 5. 题目明细表 ==========
    ws3 = wb.create_sheet("题目明细")
    detail_headers = ['作业ID', '书本', '页码', '学生', '题号', '基准答案', 'AI答案', 
                      '是否正确', '错误类型', '题型分类', '错误说明']
    for col, header in enumerate(detail_headers, 1):
        cell = ws3.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    
    detail_row = 2
    for item in homework_items:
        eval_data = item.get('evaluation', {})
        errors = eval_data.get('errors', [])
        
        # 获取基准效果数据
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
            
            if question_category['is_choice']:
                type_text = '选择题'
            elif question_category['is_fill']:
                type_text = '客观填空题'
            elif question_category['is_subjective']:
                type_text = '主观题'
            else:
                type_text = '未分类'
            
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
            
            correct_cell = ws3.cell(row=detail_row, column=8, value='正确' if is_correct else '错误')
            if not is_correct:
                correct_cell.fill = error_fill
            
            ws3.cell(row=detail_row, column=9, value=error_info.get('error_type', '') if error_info else '')
            ws3.cell(row=detail_row, column=10, value=type_text)
            ws3.cell(row=detail_row, column=11, value=error_info.get('explanation', '') if error_info else '')
            
            detail_row += 1
    
    # 设置列宽
    col_widths = [15, 20, 8, 12, 8, 20, 20, 10, 18, 12, 40]
    for col, width in enumerate(col_widths, 1):
        ws3.column_dimensions[get_column_letter(col)].width = width
    
    # ========== 6. 错误详情表 ==========
    ws_detail = wb.create_sheet("错误详情")
    err_detail_headers = ['序号', '书本', '页码', '题号', '错误类型', '基准用户答案', 'AI识别答案', 
                          '基准判断', 'AI判断', '详细说明']
    for col, header in enumerate(err_detail_headers, 1):
        cell = ws_detail.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
    
    for row_idx, err in enumerate(all_errors, 2):
        ws_detail.cell(row=row_idx, column=1, value=row_idx - 1)
        ws_detail.cell(row=row_idx, column=2, value=err.get('book', ''))
        ws_detail.cell(row=row_idx, column=3, value=err.get('page', ''))
        ws_detail.cell(row=row_idx, column=4, value=err.get('index', ''))
        
        err_type_cell = ws_detail.cell(row=row_idx, column=5, value=err.get('type', ''))
        # 根据错误类型设置颜色
        if '幻觉' in err.get('type', ''):
            err_type_cell.fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid")
        elif '判断错误' in err.get('type', ''):
            err_type_cell.fill = error_fill
        elif '识别错误' in err.get('type', ''):
            err_type_cell.fill = warning_fill
        
        ws_detail.cell(row=row_idx, column=6, value='')  # 基准用户答案
        ws_detail.cell(row=row_idx, column=7, value='')  # AI识别答案
        ws_detail.cell(row=row_idx, column=8, value='')  # 基准判断
        ws_detail.cell(row=row_idx, column=9, value='')  # AI判断
        ws_detail.cell(row=row_idx, column=10, value=err.get('explanation', ''))
    
    # 设置列宽
    err_col_widths = [8, 20, 8, 8, 18, 15, 15, 10, 10, 50]
    for col, width in enumerate(err_col_widths, 1):
        ws_detail.column_dimensions[get_column_letter(col)].width = width
    
    # ========== 7. AI分析报告表 ==========
    ai_analysis = overall.get('ai_analysis', {})
    if ai_analysis:
        ws_ai = wb.create_sheet("AI分析报告")
        ws_ai.column_dimensions['A'].width = 25
        ws_ai.column_dimensions['B'].width = 50
        
        ws_ai['A1'] = "AI智能分析报告"
        ws_ai['A1'].font = title_font
        ws_ai.merge_cells('A1:B1')
        
        # 能力评分
        ws_ai['A3'] = "能力评分"
        ws_ai['A3'].font = subtitle_font
        
        scores = ai_analysis.get('capability_scores', {})
        ws_ai['A4'] = "识别能力"
        ws_ai['B4'] = f"{scores.get('recognition', 0)}分"
        ws_ai['A5'] = "判断能力"
        ws_ai['B5'] = f"{scores.get('judgment', 0)}分"
        ws_ai['A6'] = "综合评分"
        ws_ai['B6'] = f"{scores.get('overall', 0)}分"
        
        # 主要问题
        ws_ai['A8'] = "主要问题"
        ws_ai['A8'].font = subtitle_font
        
        top_issues = ai_analysis.get('top_issues', [])
        for row_idx, issue in enumerate(top_issues, 9):
            ws_ai.cell(row=row_idx, column=1, value=issue.get('issue', ''))
            ws_ai.cell(row=row_idx, column=2, value=f"出现 {issue.get('count', 0)} 次")
        
        # 改进建议
        rec_row = 9 + len(top_issues) + 1
        ws_ai.cell(row=rec_row, column=1, value="改进建议")
        ws_ai.cell(row=rec_row, column=1).font = subtitle_font
        
        recommendations = ai_analysis.get('recommendations', [])
        for row_idx, rec in enumerate(recommendations, rec_row + 1):
            ws_ai.cell(row=row_idx, column=1, value=f"{row_idx - rec_row}.")
            ws_ai.cell(row=row_idx, column=2, value=rec)
        
        # 结论
        conclusion_row = rec_row + len(recommendations) + 2
        ws_ai.cell(row=conclusion_row, column=1, value="总体结论")
        ws_ai.cell(row=conclusion_row, column=1).font = subtitle_font
        ws_ai.cell(row=conclusion_row + 1, column=1, value=ai_analysis.get('conclusion', ''))
        ws_ai.merge_cells(f'A{conclusion_row + 1}:B{conclusion_row + 1}')
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # 生成文件名
    task_name = task_data.get('name', task_id)[:20].replace(' ', '_')
    filename = f'batch_eval_{task_name}_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
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
    
    # 获取任务的学科ID，如果没有则从作业中推断
    task_subject_id = infer_subject_id_from_homework(task_data)
    
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
        
        # 汇总所有作业的题目类型统计: 选择题、客观填空题、主观题
        aggregated_type_stats = {
            'choice': {'total': 0, 'correct': 0, 'accuracy': 0},
            'objective_fill': {'total': 0, 'correct': 0, 'accuracy': 0},
            'subjective': {'total': 0, 'correct': 0, 'accuracy': 0}
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
            evaluation = item.get('evaluation') or {}
            by_type = evaluation.get('by_question_type') or {}
            by_bvalue = evaluation.get('by_bvalue') or {}
            by_combined = evaluation.get('by_combined') or {}
            
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
        
        # 按创建时间倒序排序，优先匹配最新创建的数据集 (Requirements 4.3, 5.3)
        datasets.sort(key=lambda ds: ds.get('created_at', ''), reverse=True)
        
        updated_count = 0
        
        # 重新匹配每个作业的数据集
        for item in task_data.get('homework_items', []):
            book_id = str(item.get('book_id', '')) if item.get('book_id') else ''
            page_num = item.get('page_num')
            # 确保 page_num 是整数类型用于匹配
            page_num_int = int(page_num) if page_num is not None else None
            
            old_dataset = item.get('matched_dataset')
            new_dataset = None
            new_dataset_name = ''  # 记录匹配的数据集名称
            
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
                        new_dataset_name = ds.get('name', '')  # 获取数据集名称
                        break
            
            # 更新匹配状态
            if new_dataset != old_dataset:
                item['matched_dataset'] = new_dataset
                item['matched_dataset_name'] = new_dataset_name  # 记录数据集名称
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
