"""
学科批改评估路由模块
提供学科批改、基准效果识别和评估功能
"""
import os
import re
import json
from datetime import datetime
from flask import Blueprint, request, jsonify

from services.config_service import ConfigService
from services.database_service import DatabaseService
from services.llm_service import LLMService
from services.storage_service import StorageService
from utils.text_utils import normalize_answer, normalize_answer_strict, has_format_diff

subject_grading_bp = Blueprint('subject_grading', __name__)


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


# ========== 提示词配置 API ==========

@subject_grading_bp.route('/prompts', methods=['GET', 'POST'])
def grading_prompts_api():
    """学科批改提示词配置API"""
    if request.method == 'GET':
        prompts = ConfigService.load_grading_prompts()
        return jsonify({'prompts': prompts})
    else:
        data = request.json
        prompts = data.get('prompts', {})
        ConfigService.save_grading_prompts(prompts)
        return jsonify({'success': True})


# ========== 作业数据 API ==========

@subject_grading_bp.route('/homework', methods=['GET'])
def get_grading_homework():
    """获取批改数据列表"""
    subject_id = request.args.get('subject_id', type=int)
    hours = request.args.get('hours', 1, type=int)
    hw_publish_id = request.args.get('hw_publish_id', type=int)
    
    if subject_id is None:
        return jsonify({'success': False, 'error': '缺少subject_id参数'})
    
    try:
        # 根据是否有hw_publish_id决定查询条件
        if hw_publish_id:
            sql = """
                SELECT h.id, h.student_id, h.hw_publish_id, h.subject_id, h.page_num, h.pic_path, 
                       h.homework_result, h.create_time, h.update_time,
                       p.content AS homework_name,
                       s.name AS student_name
                FROM zp_homework h
                LEFT JOIN zp_homework_publish p ON h.hw_publish_id = p.id
                LEFT JOIN zp_student s ON h.student_id = s.id
                WHERE h.subject_id = %s 
                  AND h.status = 3 
                  AND h.hw_publish_id = %s
                ORDER BY h.create_time DESC
                LIMIT 200
            """
            rows = DatabaseService.execute_query(sql, (subject_id, hw_publish_id))
        else:
            sql = """
                SELECT h.id, h.student_id, h.hw_publish_id, h.subject_id, h.page_num, h.pic_path, 
                       h.homework_result, h.create_time, h.update_time,
                       p.content AS homework_name,
                       s.name AS student_name
                FROM zp_homework h
                LEFT JOIN zp_homework_publish p ON h.hw_publish_id = p.id
                LEFT JOIN zp_student s ON h.student_id = s.id
                WHERE h.subject_id = %s 
                  AND h.status = 3 
                  AND h.create_time >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                ORDER BY h.create_time DESC
                LIMIT 100
            """
            rows = DatabaseService.execute_query(sql, (subject_id, hours))
        
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
                'hw_publish_id': row.get('hw_publish_id', ''),
                'homework_name': row.get('homework_name', ''),
                'subject_id': row.get('subject_id'),
                'page_num': row.get('page_num'),
                'pic_path': row.get('pic_path', ''),
                'homework_result': homework_result,
                'create_time': row['create_time'].isoformat() if row.get('create_time') else None,
                'question_count': question_count
            })
        
        return jsonify({'success': True, 'data': data})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@subject_grading_bp.route('/homework-tasks', methods=['GET'])
def get_homework_tasks():
    """获取作业任务列表（按hw_publish_id分组）"""
    subject_id = request.args.get('subject_id', type=int)
    hours = request.args.get('hours', 168, type=int)  # 默认7天
    
    if subject_id is None:
        return jsonify({'success': False, 'error': '缺少subject_id参数'})
    
    try:
        sql = """
            SELECT p.id AS hw_publish_id, p.content AS task_name, 
                   COUNT(h.id) AS homework_count,
                   MAX(h.create_time) AS latest_time
            FROM zp_homework_publish p
            INNER JOIN zp_homework h ON h.hw_publish_id = p.id
            WHERE h.subject_id = %s 
              AND h.status = 3 
              AND h.create_time >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            GROUP BY p.id, p.content
            ORDER BY latest_time DESC
            LIMIT 50
        """
        rows = DatabaseService.execute_query(sql, (subject_id, hours))
        
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
        return jsonify({'success': False, 'error': str(e)})


# ========== 识别 API ==========

@subject_grading_bp.route('/recognize', methods=['POST'])
def recognize_base_effect():
    """图片识别基准效果"""
    data = request.json
    image = data.get('image', '')
    
    if not image:
        return jsonify({'success': False, 'error': '缺少图片数据'})
    
    config = ConfigService.load_config()
    
    # 使用通用识别提示词
    prompts_config = config.get('prompts', {})
    prompt = prompts_config.get('recognize', '请识别图片中作业的每道题答案。')
    
    result = LLMService.call_vision_model(image, prompt, 'doubao-1-5-vision-pro-32k-250115')
    
    if result.get('error'):
        return jsonify({'success': False, 'error': result['error']})
    
    base_effect = LLMService.extract_json_array(result.get('content', ''))
    if base_effect:
        return jsonify({'success': True, 'base_effect': base_effect})
    
    return jsonify({'success': False, 'error': '无法解析识别结果', 'raw': result.get('content', '')})


@subject_grading_bp.route('/auto-recognize', methods=['POST'])
def auto_recognize_from_db():
    """从数据库图片自动识别基准效果"""
    data = request.json
    homework_id = data.get('homework_id')
    pic_path = data.get('pic_path', '')
    subject_id = data.get('subject_id', 0)
    homework_name = data.get('homework_name', '')
    page_num = data.get('page_num', '')
    
    if not pic_path:
        return jsonify({'success': False, 'error': '图片路径为空'})
    
    config = ConfigService.load_config()
    
    # 使用通用识别提示词
    prompts_config = config.get('prompts', {})
    prompt = prompts_config.get('recognize', '请识别图片中作业的每道题答案。')
    
    result = LLMService.call_vision_model(pic_path, prompt, 'doubao-seed-1-8-251228')
    
    if result.get('error'):
        return jsonify({'success': False, 'error': result['error']})
    
    base_effect = LLMService.extract_json_array(result.get('content', ''))
    if base_effect:
        # 自动保存基准效果
        if homework_name and page_num:
            try:
                safe_name = re.sub(r'[<>:"/\\|?*]', '_', homework_name)
                filename = f"{safe_name}_{page_num}.json"
                StorageService.save_baseline_effect(filename, {
                    'homework_name': homework_name,
                    'page_num': page_num,
                    'subject_id': subject_id,
                    'base_effect': base_effect,
                    'created_at': datetime.now().isoformat(),
                    'homework_id': homework_id
                })
            except Exception as e:
                print(f'自动保存基准效果失败: {str(e)}')
        
        return jsonify({'success': True, 'base_effect': base_effect})
    
    return jsonify({'success': False, 'error': '无法解析识别结果', 'raw': result.get('content', '')})


# ========== 评估 API ==========

@subject_grading_bp.route('/evaluate', methods=['POST'])
def evaluate_grading():
    """评估对比 - 支持本地计算和AI模型比对"""
    data = request.json
    base_effect = data.get('base_effect', [])
    homework_result = data.get('homework_result', [])
    use_ai_compare = data.get('use_ai_compare', False)  # 是否使用AI模型比对
    
    if not base_effect:
        return jsonify({'success': False, 'error': '缺少基准效果数据'})
    
    # 如果启用AI比对，调用大模型逐题解析
    if use_ai_compare:
        ai_compare_result = do_ai_compare(base_effect, homework_result)
        if ai_compare_result.get('success'):
            return jsonify({'success': True, 'evaluation': ai_compare_result['evaluation']})
        # AI比对失败，回退到本地计算
    
    # 本地对比计算
    evaluation = do_local_evaluation(base_effect, homework_result)
    
    return jsonify({'success': True, 'evaluation': evaluation})


def do_ai_compare(base_effect, homework_result):
    """使用AI模型逐题比对"""
    config = ConfigService.load_config()
    
    # 获取比对提示词
    prompts_config = config.get('prompts', {})
    compare_prompt = prompts_config.get('compare_answer', '')
    
    if not compare_prompt:
        return {'success': False, 'error': '未配置比对提示词'}
    
    # 构建比对数据
    compare_data = {
        'base_effect': base_effect,
        'homework_result': homework_result
    }
    
    prompt = f"""{compare_prompt}

【基准效果数据】
{json.dumps(base_effect, ensure_ascii=False, indent=2)}

【AI批改结果数据】
{json.dumps(homework_result, ensure_ascii=False, indent=2)}

请逐题分析并输出JSON数组。"""
    
    # 调用DeepSeek进行比对
    result = LLMService.call_deepseek(
        prompt, 
        '你是专业的答案比对专家，请严格按照要求输出JSON数组。',
        timeout=120
    )
    
    if result.get('error'):
        return {'success': False, 'error': result['error']}
    
    # 解析AI返回的比对结果
    compare_results = LLMService.extract_json_array(result.get('content', ''))
    
    if not compare_results:
        return {'success': False, 'error': '无法解析AI比对结果'}
    
    # 转换为评估结果格式
    evaluation = convert_ai_compare_to_evaluation(compare_results, base_effect, homework_result)
    
    return {'success': True, 'evaluation': evaluation}


def convert_ai_compare_to_evaluation(compare_results, base_effect, homework_result):
    """将AI比对结果转换为评估结果格式（支持详细数据）"""
    total = len(base_effect)
    correct_count = 0
    errors = []
    error_distribution = {
        '识别错误-判断正确': 0,
        '识别错误-判断错误': 0,
        '识别正确-判断错误': 0,
        '格式差异': 0,
        '缺失题目': 0,
        'AI幻觉': 0,
        '标准答案不一致': 0
    }
    
    # 错误类型映射（英文代码 -> 中文名称）
    error_type_map = {
        'correct': None,
        'recognition_error_judgment_correct': '识别错误-判断正确',
        'recognition_error_judgment_error': '识别错误-判断错误',
        'recognition_correct_judgment_error': '识别正确-判断错误',
        'format_diff': '格式差异',
        'missing': '缺失题目',
        'hallucination': 'AI幻觉',
        'answer_mismatch': '标准答案不一致'
    }
    
    # 严重程度映射
    severity_map = {
        'high': '高',
        'medium': '中',
        'low': '低'
    }
    
    # 构建homework_result字典
    hw_dict = {}
    for item in homework_result:
        idx = str(item.get('index', ''))
        if idx:
            hw_dict[idx] = item
    
    # 详细分析数据
    detailed_analysis = []
    
    for result in compare_results:
        idx = str(result.get('index', ''))
        is_correct = result.get('is_correct', False)
        error_type_key = result.get('error_type', 'correct')
        error_type_cn = result.get('error_type_cn', '') or error_type_map.get(error_type_key)
        severity = result.get('severity', 'medium')
        
        # 获取分析数据（新格式支持）
        analysis = result.get('analysis', {})
        base_effect_data = result.get('base_effect', {})
        ai_result_data = result.get('ai_result', {})
        
        # 如果AI返回了详细的base_effect和ai_result，直接使用
        if not base_effect_data:
            base_item = next((b for b in base_effect if str(b.get('index', '')) == idx), {})
            base_effect_data = {
                'answer': base_item.get('answer', '') or base_item.get('mainAnswer', ''),
                'userAnswer': base_item.get('userAnswer', ''),
                'correct': base_item.get('correct', '')
            }
        
        if not ai_result_data:
            hw_item = hw_dict.get(idx, {})
            ai_result_data = {
                'answer': hw_item.get('answer', '') or hw_item.get('mainAnswer', ''),
                'userAnswer': hw_item.get('userAnswer', ''),
                'correct': hw_item.get('correct', '')
            }
        
        # 构建详细分析记录
        detail_item = {
            'index': idx,
            'is_correct': is_correct,
            'error_type': error_type_cn,
            'error_type_code': error_type_key,
            'severity': severity_map.get(severity, severity),
            'severity_code': severity,
            'base_effect': base_effect_data,
            'ai_result': ai_result_data,
            'analysis': {
                'recognition_match': analysis.get('recognition_match', None),
                'judgment_match': analysis.get('judgment_match', None),
                'answer_match': analysis.get('answer_match', None),
                'is_hallucination': analysis.get('is_hallucination', False)
            },
            'explanation': result.get('explanation', ''),
            'suggestion': result.get('suggestion', '')
        }
        
        detailed_analysis.append(detail_item)
        
        if is_correct or error_type_cn is None:
            correct_count += 1
        else:
            # 统计错误分布
            if error_type_cn in error_distribution:
                error_distribution[error_type_cn] += 1
            
            errors.append(detail_item)
    
    # 计算各项指标
    accuracy = correct_count / total if total > 0 else 0
    
    # 计算真正的精确率、召回率、F1
    tp = correct_count
    fp = error_distribution.get('识别正确-判断错误', 0) + error_distribution.get('AI幻觉', 0)
    fn = error_distribution.get('识别错误-判断错误', 0)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    # 计算幻觉率
    hallucination_count = error_distribution.get('AI幻觉', 0)
    wrong_answers_count = sum(1 for b in base_effect if str(b.get('correct', '')).lower() == 'no')
    hallucination_rate = hallucination_count / wrong_answers_count if wrong_answers_count > 0 else 0
    
    # 按严重程度统计
    severity_distribution = {
        '高': sum(1 for e in errors if e.get('severity_code') == 'high'),
        '中': sum(1 for e in errors if e.get('severity_code') == 'medium'),
        '低': sum(1 for e in errors if e.get('severity_code') == 'low')
    }
    
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
        'severity_distribution': severity_distribution,
        'detailed_analysis': detailed_analysis,
        'ai_compared': True
    }


def do_local_evaluation(base_effect, homework_result):
    """本地对比计算评估结果 - 全部按tempIndex匹配"""
    total = len(base_effect)
    correct_count = 0
    errors = []
    error_distribution = {
        '识别错误-判断正确': 0,
        '识别错误-判断错误': 0,
        '识别正确-判断错误': 0,
        '格式差异': 0,
        '缺失题目': 0,
        'AI幻觉': 0,
        '基准数据不完整': 0
    }
    
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
        if not hw_item:
            hw_item = {}
        
        # 基准效果的标准答案：优先取 answer，没有则取 mainAnswer
        base_answer = str(base_item.get('answer', '') or base_item.get('mainAnswer', '')).strip()
        base_user = str(base_item.get('userAnswer', '')).strip()
        
        # 兼容 correct 和 isRight 两种字段格式
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
                explanation = f'用户答案不一致：基准="{base_user}"，AI="{hw_user}"（基准效果缺少判断结果，无法判断correct是否正确）'
                severity = 'high'
        else:
            # 标准化答案进行比较
            norm_base_user = normalize_answer(base_user)
            norm_hw_user = normalize_answer(hw_user)
            norm_base_answer = normalize_answer(base_answer)
            
            user_match = norm_base_user == norm_hw_user
            correct_match = base_correct == hw_correct
            
            # 检测AI幻觉：学生答错了，但AI识别成了正确答案
            if base_correct == 'no' and norm_hw_user == norm_base_answer:
                is_match = False
                error_type = 'AI幻觉'
                explanation = f'学生答案"{base_user}"是错误的，但AI识别成了正确答案"{hw_user}"'
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
                    'is_hallucination': error_type == 'AI幻觉'
                }
            })
    
    accuracy = correct_count / total if total > 0 else 0
    
    # 计算真正的精确率、召回率、F1
    tp = correct_count
    fp = error_distribution.get('识别正确-判断错误', 0) + error_distribution.get('AI幻觉', 0)
    fn = error_distribution.get('识别错误-判断错误', 0)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    # 计算幻觉率
    hallucination_count = error_distribution.get('AI幻觉', 0)
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
        'ai_compared': False
    }


# ========== 基准效果管理 API ==========

@subject_grading_bp.route('/save-baseline', methods=['POST'])
def save_baseline_effect():
    """保存基准效果到文件"""
    data = request.json
    homework_name = data.get('homework_name', '')
    page_num = data.get('page_num', '')
    base_effect = data.get('base_effect', [])
    subject_id = data.get('subject_id', 0)
    
    if not homework_name or not page_num:
        return jsonify({'success': False, 'error': '缺少作业名称或页码'})
    
    if not base_effect:
        return jsonify({'success': False, 'error': '基准效果为空'})
    
    try:
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', homework_name)
        filename = f"{safe_name}_{page_num}.json"
        
        StorageService.save_baseline_effect(filename, {
            'homework_name': homework_name,
            'page_num': page_num,
            'subject_id': subject_id,
            'base_effect': base_effect,
            'created_at': datetime.now().isoformat()
        })
        
        return jsonify({'success': True, 'filepath': filename})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@subject_grading_bp.route('/load-baseline', methods=['POST'])
def load_baseline_effect():
    """加载已保存的基准效果（优先从数据集加载，其次从baseline_effects加载）"""
    data = request.json
    homework_name = data.get('homework_name', '')
    page_num = data.get('page_num', '')
    book_id = data.get('book_id', '')
    
    if not page_num:
        return jsonify({'success': False, 'error': '缺少页码'})
    
    try:
        base_effect = []
        source = None
        
        # 1. 优先从数据集中查找（按book_id和page_num匹配）
        if book_id:
            for filename in StorageService.list_datasets():
                dataset_id = filename.replace('.json', '')
                ds_data = StorageService.load_dataset(dataset_id)
                if ds_data and str(ds_data.get('book_id', '')) == str(book_id):
                    base_effects = ds_data.get('base_effects', {})
                    page_key = str(page_num)
                    if page_key in base_effects:
                        base_effect = base_effects[page_key]
                        source = 'dataset'
                        break
        
        # 2. 如果没有book_id或数据集中没找到，尝试遍历所有数据集按页码匹配
        if not base_effect:
            for filename in StorageService.list_datasets():
                dataset_id = filename.replace('.json', '')
                ds_data = StorageService.load_dataset(dataset_id)
                if ds_data:
                    base_effects = ds_data.get('base_effects', {})
                    page_key = str(page_num)
                    if page_key in base_effects:
                        base_effect = base_effects[page_key]
                        source = 'dataset'
                        break
        
        # 3. 最后从baseline_effects目录加载
        if not base_effect and homework_name:
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', homework_name)
            filename = f"{safe_name}_{page_num}.json"
            
            saved_data = StorageService.load_baseline_effect(filename)
            if saved_data:
                base_effect = saved_data.get('base_effect', [])
                source = 'baseline'
        
        if not base_effect:
            return jsonify({'success': False, 'error': '未找到保存的基准效果'})
        
        return jsonify({
            'success': True,
            'base_effect': base_effect,
            'source': source
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@subject_grading_bp.route('/delete-baseline', methods=['POST'])
def delete_baseline_effect():
    """删除基准效果文件"""
    data = request.json
    homework_name = data.get('homework_name', '')
    page_num = data.get('page_num', '')
    
    if not homework_name or not page_num:
        return jsonify({'success': False, 'error': '缺少作业名称或页码'})
    
    try:
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', homework_name)
        filename = f"{safe_name}_{page_num}.json"
        
        if StorageService.delete_baseline_effect(filename):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': '文件不存在'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@subject_grading_bp.route('/list-baselines', methods=['GET'])
def list_baseline_effects():
    """列出所有基准效果文件（包括 baseline_effects 和 datasets 目录）"""
    try:
        baselines = []
        
        # 1. 读取 baseline_effects 目录
        for filename in StorageService.list_baseline_effects():
            data = StorageService.load_baseline_effect(filename)
            if data:
                baselines.append({
                    'filename': filename,
                    'source': 'baseline',
                    'homework_name': data.get('homework_name', ''),
                    'page_num': data.get('page_num', ''),
                    'subject_id': data.get('subject_id', 0),
                    'question_count': len(data.get('base_effect', [])),
                    'created_at': data.get('created_at', '')
                })
        
        # 2. 读取 datasets 目录
        for filename in StorageService.list_datasets():
            dataset_id = filename.replace('.json', '')
            data = StorageService.load_dataset(dataset_id)
            if data and data.get('base_effects'):
                # 数据集按页码存储基准效果
                base_effects = data.get('base_effects', {})
                for page_num, effects in base_effects.items():
                    question_count = len(effects) if isinstance(effects, list) else 0
                    baselines.append({
                        'filename': filename,
                        'source': 'dataset',
                        'dataset_id': dataset_id,
                        'homework_name': f"数据集 {dataset_id[:8]}",
                        'page_num': str(page_num),
                        'subject_id': data.get('subject_id', 0),
                        'question_count': question_count,
                        'created_at': data.get('created_at', ''),
                        'book_id': data.get('book_id', '')
                    })
        
        baselines.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return jsonify({'success': True, 'data': baselines})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
