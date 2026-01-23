"""
测试计划服务模块
提供测试计划工作流相关的业务逻辑：
- 作业匹配服务
- 批改状态检测
- 工作流状态管理
"""
import json
from datetime import datetime
from typing import List, Dict, Optional, Any

from services.database_service import DatabaseService, AppDatabaseService


# ========== 页码解析辅助函数 ==========

def parse_page_region(page_region: str) -> List[int]:
    """
    解析 page_region 字符串为页码列表
    
    支持格式:
    - "97,98" -> [97, 98]
    - "97-100" -> [97, 98, 99, 100]
    - "97～99,101" -> [97, 98, 99, 101]
    - "97~99" -> [97, 98, 99]
    - "97-99,101" -> [97, 98, 99, 101]
    
    Args:
        page_region: 页码范围字符串
        
    Returns:
        list: 排序去重的页码列表
    """
    pages = []
    if not page_region:
        return pages
    
    # 统一替换各种分隔符
    normalized = page_region.replace('～', '-').replace('~', '-')
    
    # 按逗号分割
    parts = normalized.split(',')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        if '-' in part:
            # 范围格式: "97-100"
            try:
                range_parts = part.split('-')
                if len(range_parts) == 2:
                    start = int(range_parts[0].strip())
                    end = int(range_parts[1].strip())
                    # 确保 start <= end
                    if start > end:
                        start, end = end, start
                    pages.extend(range(start, end + 1))
            except ValueError:
                continue
        else:
            # 单个页码
            try:
                pages.append(int(part))
            except ValueError:
                continue
    
    return sorted(set(pages))


def check_page_match(dataset_pages: List[int], page_region: str) -> Dict[str, Any]:
    """
    检查数据集页码与 publish 页码是否匹配
    
    匹配规则:
    1. 完全匹配: dataset_pages == publish_pages
    2. 包含匹配: publish_pages 是 dataset_pages 的子集
    3. 交集匹配: 有任意页码重叠
    
    Args:
        dataset_pages: 数据集的页码列表
        page_region: publish 的页码范围字符串
        
    Returns:
        dict: {
            'is_match': bool,           # 是否匹配
            'match_type': str,          # 匹配类型: exact/subset/intersection/none
            'intersection': list,       # 交集页码
            'dataset_pages': list,      # 数据集页码
            'publish_pages': list       # publish 页码
        }
    """
    publish_pages = parse_page_region(page_region)
    dataset_set = set(dataset_pages)
    publish_set = set(publish_pages)
    
    # 计算交集
    intersection = sorted(dataset_set & publish_set)
    
    # 判断匹配类型
    if dataset_set == publish_set:
        match_type = 'exact'
        is_match = True
    elif publish_set.issubset(dataset_set):
        match_type = 'subset'
        is_match = True
    elif len(intersection) > 0:
        match_type = 'intersection'
        is_match = True
    else:
        match_type = 'none'
        is_match = False
    
    return {
        'is_match': is_match,
        'match_type': match_type,
        'intersection': intersection,
        'dataset_pages': sorted(dataset_pages),
        'publish_pages': publish_pages
    }


# ========== 作业匹配服务 ==========

def match_homework_publish(
    keyword: str,
    match_type: str = 'fuzzy',
    book_id: Optional[str] = None,
    dataset_pages: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    根据关键字匹配 zp_homework_publish 中的作业发布
    
    Args:
        keyword: 搜索关键字
        match_type: 匹配类型 (exact/fuzzy/regex)
        book_id: 可选，限定书本ID
        dataset_pages: 可选，数据集页码列表，用于页码匹配过滤
        
    Returns:
        dict: {
            'success': bool,
            'matched_count': int,
            'total_homework': int,
            'total_graded': int,
            'matches': [
                {
                    'publish_id': str,
                    'content': str,
                    'subject_id': int,
                    'book_id': str,
                    'page_region': str,
                    'pages': list,
                    'total_homework': int,
                    'graded_count': int,
                    'grading_progress': float,
                    'create_time': str,
                    'page_match': dict  # 页码匹配信息
                }
            ],
            'error': str (if failed)
        }
    """
    try:
        # 构建 SQL 查询条件
        if match_type == 'exact':
            content_condition = "hp.content = %s"
            content_param = keyword
        elif match_type == 'regex':
            content_condition = "hp.content REGEXP %s"
            content_param = keyword
        else:
            # 模糊匹配（默认）
            content_condition = "hp.content LIKE %s"
            content_param = f'%{keyword}%'
        
        # 构建完整 SQL
        sql = f"""
            SELECT 
                hp.id as publish_id,
                hp.content,
                hp.subject_id,
                hp.book_id,
                hp.page_region,
                hp.create_time,
                COUNT(h.id) as total_homework,
                SUM(CASE 
                    WHEN h.homework_result IS NOT NULL 
                    AND h.homework_result != '' 
                    AND h.homework_result != '[]' 
                    THEN 1 ELSE 0 
                END) as graded_count
            FROM zp_homework_publish hp
            LEFT JOIN zp_homework h ON h.hw_publish_id = hp.id
            WHERE {content_condition}
        """
        
        params = [content_param]
        
        # 如果指定了 book_id，添加过滤条件
        if book_id:
            sql += " AND hp.book_id = %s"
            params.append(book_id)
        
        # 分组和排序
        sql += """
            GROUP BY hp.id, hp.content, hp.subject_id, hp.book_id, hp.page_region, hp.create_time
            ORDER BY hp.create_time DESC
            LIMIT 100
        """
        
        # 执行查询（使用 zpsmart 数据库）
        rows = DatabaseService.execute_query(sql, tuple(params))
        
        # 处理结果
        matches = []
        total_homework_sum = 0
        total_graded_sum = 0
        
        for row in rows:
            total_hw = row.get('total_homework', 0) or 0
            graded = row.get('graded_count', 0) or 0
            
            # 计算批改进度百分比
            grading_progress = round(graded / total_hw * 100, 1) if total_hw > 0 else 0
            
            # 解析页码范围
            page_region = row.get('page_region', '')
            pages = parse_page_region(page_region)
            
            # 检查页码匹配（如果提供了数据集页码）
            page_match = None
            if dataset_pages:
                page_match = check_page_match(dataset_pages, page_region)
                # 如果页码不匹配，跳过该记录
                if not page_match['is_match']:
                    continue
            
            # 格式化创建时间
            create_time = row.get('create_time')
            if create_time:
                if hasattr(create_time, 'isoformat'):
                    create_time = create_time.isoformat()
                else:
                    create_time = str(create_time)
            
            match_item = {
                'publish_id': str(row.get('publish_id', '')),
                'content': row.get('content', ''),
                'subject_id': row.get('subject_id'),
                'book_id': str(row.get('book_id', '')),
                'page_region': page_region,
                'pages': pages,
                'total_homework': total_hw,
                'graded_count': graded,
                'grading_progress': grading_progress,
                'create_time': create_time
            }
            
            if page_match:
                match_item['page_match'] = page_match
            
            matches.append(match_item)
            total_homework_sum += total_hw
            total_graded_sum += graded
        
        return {
            'success': True,
            'matched_count': len(matches),
            'total_homework': total_homework_sum,
            'total_graded': total_graded_sum,
            'matches': matches
        }
        
    except Exception as e:
        print(f"[TestPlanService] 作业匹配失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'matched_count': 0,
            'total_homework': 0,
            'total_graded': 0,
            'matches': [],
            'error': str(e)
        }


def save_matched_publish_ids(plan_id: str, publish_ids: List[str]) -> bool:
    """
    保存匹配结果到 test_plans 表的 matched_publish_ids 字段
    
    Args:
        plan_id: 测试计划ID
        publish_ids: 匹配到的 publish ID 列表
        
    Returns:
        bool: 是否保存成功
    """
    try:
        sql = """
            UPDATE test_plans 
            SET matched_publish_ids = %s, updated_at = %s 
            WHERE plan_id = %s
        """
        AppDatabaseService.execute_update(sql, (
            json.dumps(publish_ids),
            datetime.now(),
            plan_id
        ))
        return True
    except Exception as e:
        print(f"[TestPlanService] 保存匹配结果失败: {e}")
        return False


# ========== 批改状态检测 ==========

def check_grading_status(publish_ids: List[str]) -> Dict[str, Any]:
    """
    检查作业批改状态
    
    Args:
        publish_ids: publish ID 列表
        
    Returns:
        dict: {
            'total_homework': int,      # 总作业数
            'graded_count': int,        # 已批改数
            'grading_progress': float,  # 批改进度百分比
            'is_complete': bool,        # 是否全部批改完成
            'publish_details': [        # 每个 publish 的详情
                {
                    'publish_id': str,
                    'total': int,
                    'graded': int,
                    'progress': float
                }
            ]
        }
    """
    if not publish_ids:
        return {
            'total_homework': 0,
            'graded_count': 0,
            'grading_progress': 0,
            'is_complete': False,
            'publish_details': []
        }
    
    try:
        # 构建 SQL 查询每个 publish 的批改状态
        placeholders = ','.join(['%s'] * len(publish_ids))
        sql = f"""
            SELECT 
                hw_publish_id,
                COUNT(*) as total,
                SUM(CASE 
                    WHEN homework_result IS NOT NULL 
                    AND homework_result != '' 
                    AND homework_result != '[]' 
                    THEN 1 ELSE 0 
                END) as graded
            FROM zp_homework
            WHERE hw_publish_id IN ({placeholders})
            GROUP BY hw_publish_id
        """
        
        rows = DatabaseService.execute_query(sql, tuple(publish_ids))
        
        # 汇总统计
        total_homework = 0
        graded_count = 0
        publish_details = []
        
        for row in rows:
            total = row.get('total', 0) or 0
            graded = row.get('graded', 0) or 0
            progress = round(graded / total * 100, 1) if total > 0 else 0
            
            publish_details.append({
                'publish_id': str(row.get('hw_publish_id', '')),
                'total': total,
                'graded': graded,
                'progress': progress
            })
            
            total_homework += total
            graded_count += graded
        
        # 计算总体进度
        grading_progress = round(graded_count / total_homework * 100, 1) if total_homework > 0 else 0
        is_complete = graded_count >= total_homework and total_homework > 0
        
        return {
            'total_homework': total_homework,
            'graded_count': graded_count,
            'grading_progress': grading_progress,
            'is_complete': is_complete,
            'publish_details': publish_details
        }
        
    except Exception as e:
        print(f"[TestPlanService] 检查批改状态失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'total_homework': 0,
            'graded_count': 0,
            'grading_progress': 0,
            'is_complete': False,
            'publish_details': [],
            'error': str(e)
        }


def get_graded_homework_ids(publish_ids: List[str]) -> List[str]:
    """
    获取已批改的作业ID列表
    
    Args:
        publish_ids: publish ID 列表
        
    Returns:
        list: 已批改的 homework_id 列表
    """
    if not publish_ids:
        return []
    
    try:
        placeholders = ','.join(['%s'] * len(publish_ids))
        sql = f"""
            SELECT id
            FROM zp_homework
            WHERE hw_publish_id IN ({placeholders})
              AND homework_result IS NOT NULL 
              AND homework_result != '' 
              AND homework_result != '[]'
        """
        
        rows = DatabaseService.execute_query(sql, tuple(publish_ids))
        return [str(row['id']) for row in rows]
        
    except Exception as e:
        print(f"[TestPlanService] 获取已批改作业ID失败: {e}")
        return []


# ========== 工作流状态管理 ==========

def get_default_workflow_status() -> Dict[str, Any]:
    """
    获取默认的工作流状态结构
    
    Returns:
        dict: 工作流状态初始结构
    """
    return {
        "dataset": {
            "status": "not_started",
            "dataset_id": None,
            "dataset_name": None,
            "question_count": 0,
            "completed_at": None
        },
        "homework_match": {
            "status": "not_started",
            "matched_publish": [],
            "total_homework": 0,
            "total_graded": 0,
            "grading_progress": 0,
            "last_checked": None
        },
        "evaluation": {
            "status": "not_started",
            "task_id": None,
            "accuracy": None,
            "started_at": None,
            "completed_at": None
        },
        "report": {
            "status": "not_started",
            "report_id": None,
            "generated_at": None
        }
    }


def update_workflow_status(
    plan_id: str,
    step: str,
    status_data: Dict[str, Any]
) -> bool:
    """
    更新工作流状态
    
    Args:
        plan_id: 测试计划ID
        step: 步骤名称 (dataset/homework_match/evaluation/report)
        status_data: 状态数据，将合并到对应步骤
        
    Returns:
        bool: 是否更新成功
    """
    try:
        # 获取当前工作流状态
        plan = AppDatabaseService.execute_one(
            "SELECT workflow_status FROM test_plans WHERE plan_id = %s",
            (plan_id,)
        )
        
        if not plan:
            print(f"[TestPlanService] 测试计划不存在: {plan_id}")
            return False
        
        # 解析当前状态
        workflow_status = plan.get('workflow_status')
        if workflow_status and isinstance(workflow_status, str):
            try:
                workflow_status = json.loads(workflow_status)
            except:
                workflow_status = get_default_workflow_status()
        elif not workflow_status:
            workflow_status = get_default_workflow_status()
        
        # 确保步骤存在
        if step not in workflow_status:
            workflow_status[step] = {}
        
        # 合并状态数据
        workflow_status[step].update(status_data)
        
        # 保存更新
        sql = """
            UPDATE test_plans 
            SET workflow_status = %s, updated_at = %s 
            WHERE plan_id = %s
        """
        AppDatabaseService.execute_update(sql, (
            json.dumps(workflow_status, ensure_ascii=False),
            datetime.now(),
            plan_id
        ))
        
        return True
        
    except Exception as e:
        print(f"[TestPlanService] 更新工作流状态失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_workflow_progress(plan_id: str) -> Dict[str, Any]:
    """
    获取工作流进度
    
    Args:
        plan_id: 测试计划ID
        
    Returns:
        dict: {
            'success': bool,
            'workflow_status': dict,    # 完整工作流状态
            'current_step': str,        # 当前步骤
            'completed_steps': list,    # 已完成步骤列表
            'progress_percent': float,  # 总体进度百分比
            'can_proceed': bool,        # 是否可以继续下一步
            'next_action': str          # 下一步操作建议
        }
    """
    try:
        # 获取测试计划
        plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s",
            (plan_id,)
        )
        
        if not plan:
            return {
                'success': False,
                'error': '测试计划不存在'
            }
        
        # 解析工作流状态
        workflow_status = plan.get('workflow_status')
        if workflow_status and isinstance(workflow_status, str):
            try:
                workflow_status = json.loads(workflow_status)
            except:
                workflow_status = get_default_workflow_status()
        elif not workflow_status:
            workflow_status = get_default_workflow_status()
        
        # 分析各步骤状态
        steps = ['dataset', 'homework_match', 'evaluation', 'report']
        completed_steps = []
        current_step = None
        
        for step in steps:
            step_status = workflow_status.get(step, {}).get('status', 'not_started')
            if step_status == 'completed':
                completed_steps.append(step)
            elif step_status == 'in_progress':
                current_step = step
                break
            elif step_status == 'not_started':
                if current_step is None:
                    current_step = step
                break
        
        # 如果所有步骤都完成了
        if len(completed_steps) == len(steps):
            current_step = 'completed'
        
        # 计算进度百分比
        progress_percent = round(len(completed_steps) / len(steps) * 100, 1)
        
        # 判断是否可以继续
        can_proceed = True
        next_action = ''
        
        if current_step == 'dataset':
            next_action = '请选择数据集'
        elif current_step == 'homework_match':
            dataset_status = workflow_status.get('dataset', {}).get('status')
            if dataset_status != 'completed':
                can_proceed = False
                next_action = '请先完成数据集配置'
            else:
                next_action = '执行作业匹配'
        elif current_step == 'evaluation':
            match_status = workflow_status.get('homework_match', {})
            grading_progress = match_status.get('grading_progress', 0)
            threshold = plan.get('grading_threshold', 100)
            if grading_progress < threshold:
                can_proceed = False
                next_action = f'等待批改完成（当前 {grading_progress}%，需达到 {threshold}%）'
            else:
                next_action = '开始批量评估'
        elif current_step == 'report':
            eval_status = workflow_status.get('evaluation', {}).get('status')
            if eval_status != 'completed':
                can_proceed = False
                next_action = '请先完成批量评估'
            else:
                next_action = '生成测试报告'
        elif current_step == 'completed':
            next_action = '工作流已完成'
        
        return {
            'success': True,
            'workflow_status': workflow_status,
            'current_step': current_step,
            'completed_steps': completed_steps,
            'progress_percent': progress_percent,
            'can_proceed': can_proceed,
            'next_action': next_action
        }
        
    except Exception as e:
        print(f"[TestPlanService] 获取工作流进度失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


def transition_workflow_status(
    plan_id: str,
    step: str,
    new_status: str
) -> bool:
    """
    工作流状态流转
    
    状态流转规则:
    - not_started → in_progress: 开始执行
    - in_progress → completed: 执行完成
    - in_progress → failed: 执行失败
    - failed → in_progress: 重试
    
    Args:
        plan_id: 测试计划ID
        step: 步骤名称
        new_status: 新状态 (not_started/in_progress/completed/failed)
        
    Returns:
        bool: 是否流转成功
    """
    valid_statuses = ['not_started', 'in_progress', 'completed', 'failed']
    if new_status not in valid_statuses:
        print(f"[TestPlanService] 无效的状态值: {new_status}")
        return False
    
    # 更新状态
    status_data = {'status': new_status}
    
    # 根据状态添加时间戳
    if new_status == 'in_progress':
        status_data['started_at'] = datetime.now().isoformat()
    elif new_status == 'completed':
        status_data['completed_at'] = datetime.now().isoformat()
    
    return update_workflow_status(plan_id, step, status_data)


# ========== 批量评估集成 ==========

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


# ========== 报告生成 ==========

def generate_test_report(plan_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
    """
    生成测试报告
    
    从评估结果中聚合统计数据，生成测试报告。
    
    Args:
        plan_id: 测试计划ID
        task_id: 可选，指定批量任务ID。如果不提供，从工作流状态中获取
        
    Returns:
        dict: {
            'success': bool,
            'report': {
                'report_id': str,           # 报告唯一标识
                'plan_id': str,             # 测试计划ID
                'task_id': str,             # 批量任务ID
                'overall_accuracy': float,  # 整体准确率
                'total_questions': int,     # 总题目数
                'correct_count': int,       # 正确数
                'error_count': int,         # 错误数
                'error_distribution': dict, # 错误类型分布
                'question_type_stats': dict,# 题型统计
                'subject_stats': dict,      # 学科统计
                'homework_stats': {         # 作业统计
                    'total': int,
                    'evaluated': int,
                    'matched': int
                },
                'generated_at': str         # 生成时间
            },
            'error': str (if failed)
        }
    """
    import uuid
    from services.storage_service import StorageService
    
    try:
        # 1. 获取测试计划
        plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s",
            (plan_id,)
        )
        
        if not plan:
            return {
                'success': False,
                'error': '测试计划不存在'
            }
        
        # 2. 获取任务ID（从参数或工作流状态）
        if not task_id:
            workflow_status = plan.get('workflow_status')
            if workflow_status and isinstance(workflow_status, str):
                try:
                    workflow_status = json.loads(workflow_status)
                except:
                    workflow_status = {}
            
            task_id = workflow_status.get('evaluation', {}).get('task_id') if workflow_status else None
        
        if not task_id:
            return {
                'success': False,
                'error': '未找到关联的评估任务，请先完成批量评估'
            }
        
        # 3. 加载批量任务数据
        task_data = StorageService.load_batch_task(task_id)
        
        if not task_data:
            return {
                'success': False,
                'error': f'批量任务数据不存在: {task_id}'
            }
        
        # 4. 检查任务状态
        task_status = task_data.get('status', 'pending')
        if task_status != 'completed':
            return {
                'success': False,
                'error': f'批量评估尚未完成，当前状态: {task_status}'
            }
        
        # 5. 聚合评估结果
        homework_items = task_data.get('homework_items', [])
        overall_report = task_data.get('overall_report', {})
        
        # 基础统计
        total_questions = overall_report.get('total_questions', 0)
        correct_count = overall_report.get('correct_questions', 0)
        error_count = total_questions - correct_count
        overall_accuracy = overall_report.get('overall_accuracy', 0)
        
        # 作业统计
        total_homework = len(homework_items)
        evaluated_homework = sum(1 for item in homework_items if item.get('status') == 'completed')
        matched_homework = sum(1 for item in homework_items if item.get('matched_dataset'))
        
        # 6. 错误类型分布统计
        error_distribution = {}
        for item in homework_items:
            evaluation = item.get('evaluation', {})
            if not evaluation:
                continue
            
            errors = evaluation.get('errors', [])
            for error in errors:
                error_type = error.get('error_type', '未知错误')
                if error_type not in error_distribution:
                    error_distribution[error_type] = 0
                error_distribution[error_type] += 1
        
        # 7. 题型统计（选择题/客观填空题/主观题）
        # 评估结果中使用 by_question_type 字段存储题型统计
        question_type_stats = {
            'choice': {
                'name': '选择题',
                'total': 0,
                'correct': 0,
                'accuracy': 0
            },
            'objective_fill': {
                'name': '客观填空题',
                'total': 0,
                'correct': 0,
                'accuracy': 0
            },
            'subjective': {
                'name': '主观题',
                'total': 0,
                'correct': 0,
                'accuracy': 0
            }
        }
        
        # bvalue 细分统计 (1=单选, 2=多选, 3=判断, 4=填空, 5=解答)
        bvalue_stats = {
            '1': {'name': '单选', 'total': 0, 'correct': 0, 'accuracy': 0},
            '2': {'name': '多选', 'total': 0, 'correct': 0, 'accuracy': 0},
            '3': {'name': '判断', 'total': 0, 'correct': 0, 'accuracy': 0},
            '4': {'name': '填空', 'total': 0, 'correct': 0, 'accuracy': 0},
            '5': {'name': '解答', 'total': 0, 'correct': 0, 'accuracy': 0}
        }
        
        for item in homework_items:
            evaluation = item.get('evaluation', {})
            if not evaluation:
                continue
            
            # 从 evaluation 中获取题型统计
            # 评估结果使用 by_question_type 字段（选择题/客观填空题/主观题）
            type_stats = evaluation.get('by_question_type', {})
            
            for qtype in ['choice', 'objective_fill', 'subjective']:
                if qtype in type_stats:
                    question_type_stats[qtype]['total'] += type_stats[qtype].get('total', 0)
                    question_type_stats[qtype]['correct'] += type_stats[qtype].get('correct', 0)
            
            # 从 evaluation 中获取 bvalue 细分统计
            by_bvalue = evaluation.get('by_bvalue', {})
            for bv in ['1', '2', '3', '4', '5']:
                if bv in by_bvalue:
                    bvalue_stats[bv]['total'] += by_bvalue[bv].get('total', 0)
                    bvalue_stats[bv]['correct'] += by_bvalue[bv].get('correct', 0)
        
        # 计算各题型准确率
        for qtype in question_type_stats:
            total = question_type_stats[qtype]['total']
            correct = question_type_stats[qtype]['correct']
            question_type_stats[qtype]['accuracy'] = round(correct / total, 4) if total > 0 else 0
        
        # 计算 bvalue 细分准确率
        for bv in bvalue_stats:
            total = bvalue_stats[bv]['total']
            correct = bvalue_stats[bv]['correct']
            bvalue_stats[bv]['accuracy'] = round(correct / total, 4) if total > 0 else 0
        
        # 8. 学科统计
        subject_stats = {}
        for item in homework_items:
            evaluation = item.get('evaluation', {})
            if not evaluation:
                continue
            
            # 从 homework_items 获取学科信息
            # 注意：学科信息可能在 task_data 级别
            subject_id = task_data.get('subject_id')
            subject_name = task_data.get('subject_name', SUBJECT_MAP.get(subject_id, f'学科{subject_id}'))
            
            if subject_name not in subject_stats:
                subject_stats[subject_name] = {
                    'subject_id': subject_id,
                    'total_questions': 0,
                    'correct_count': 0,
                    'error_count': 0,
                    'accuracy': 0,
                    'homework_count': 0
                }
            
            subject_stats[subject_name]['homework_count'] += 1
            subject_stats[subject_name]['total_questions'] += evaluation.get('total_questions', 0)
            subject_stats[subject_name]['correct_count'] += evaluation.get('correct_count', 0)
            subject_stats[subject_name]['error_count'] += evaluation.get('error_count', 0)
        
        # 计算各学科准确率
        for subject in subject_stats:
            total = subject_stats[subject]['total_questions']
            correct = subject_stats[subject]['correct_count']
            subject_stats[subject]['accuracy'] = round(correct / total, 4) if total > 0 else 0
        
        # 9. 生成报告ID
        report_id = str(uuid.uuid4())[:8]
        generated_at = datetime.now().isoformat()
        
        # 10. 构建报告数据
        report = {
            'report_id': report_id,
            'plan_id': plan_id,
            'plan_name': plan.get('name', ''),
            'task_id': task_id,
            'task_name': task_data.get('name', ''),
            'overall_accuracy': overall_accuracy,
            'total_questions': total_questions,
            'correct_count': correct_count,
            'error_count': error_count,
            'error_distribution': error_distribution,
            'question_type_stats': question_type_stats,
            'bvalue_stats': bvalue_stats,  # bvalue 细分统计
            'subject_stats': subject_stats,
            'homework_stats': {
                'total': total_homework,
                'evaluated': evaluated_homework,
                'matched': matched_homework
            },
            'generated_at': generated_at
        }
        
        return {
            'success': True,
            'report': report
        }
        
    except Exception as e:
        print(f"[TestPlanService] 生成测试报告失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


def create_batch_task_from_plan(plan_id: str) -> Dict[str, Any]:
    """
    从测试计划创建批量评估任务
    
    根据测试计划的 matched_publish_ids 获取已批改的作业，
    创建批量评估任务，复用现有批量评估逻辑。
    
    Args:
        plan_id: 测试计划ID
        
    Returns:
        dict: {
            'success': bool,
            'task_id': str,           # 创建的批量任务ID
            'homework_count': int,    # 作业数量
            'error': str (if failed)
        }
    """
    import uuid
    from services.storage_service import StorageService
    
    try:
        # 1. 获取测试计划
        plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s",
            (plan_id,)
        )
        
        if not plan:
            return {
                'success': False,
                'error': '测试计划不存在'
            }
        
        # 2. 获取匹配的 publish_ids
        matched_publish_ids = plan.get('matched_publish_ids')
        if matched_publish_ids and isinstance(matched_publish_ids, str):
            try:
                matched_publish_ids = json.loads(matched_publish_ids)
            except:
                matched_publish_ids = []
        
        if not matched_publish_ids:
            return {
                'success': False,
                'error': '尚未匹配作业发布，请先执行作业匹配'
            }
        
        # 3. 获取已批改的作业ID
        homework_ids = get_graded_homework_ids(matched_publish_ids)
        
        if not homework_ids:
            return {
                'success': False,
                'error': '没有已批改的作业，请等待批改完成'
            }
        
        # 4. 获取工作流状态中的数据集信息
        workflow_status = plan.get('workflow_status')
        if workflow_status and isinstance(workflow_status, str):
            try:
                workflow_status = json.loads(workflow_status)
            except:
                workflow_status = {}
        
        dataset_info = workflow_status.get('dataset', {}) if workflow_status else {}
        dataset_id = dataset_info.get('dataset_id')
        dataset_name = dataset_info.get('dataset_name', '')
        
        # 5. 查询作业详细信息
        placeholders = ','.join(['%s'] * len(homework_ids))
        sql = f"""
            SELECT h.id, h.hw_publish_id, h.student_id, h.subject_id, h.page_num, 
                   h.pic_path, h.homework_result, h.data_value,
                   p.content AS homework_name, s.name AS student_name,
                   b.id AS book_id, b.book_name AS book_name
            FROM zp_homework h
            LEFT JOIN zp_homework_publish p ON h.hw_publish_id = p.id
            LEFT JOIN zp_student s ON h.student_id = s.id
            LEFT JOIN zp_make_book b ON p.book_id = b.id
            WHERE h.id IN ({placeholders})
        """
        rows = DatabaseService.execute_query(sql, tuple(homework_ids))
        
        if not rows:
            return {
                'success': False,
                'error': '无法获取作业详细信息'
            }
        
        # 6. 获取学科信息
        subject_id = rows[0].get('subject_id') if rows else None
        subject_name = SUBJECT_MAP.get(subject_id, f'学科{subject_id}') if subject_id is not None else ''
        
        # 7. 加载数据集用于匹配（如果没有指定数据集）
        datasets = []
        if not dataset_id:
            for fn in StorageService.list_datasets():
                ds = StorageService.load_dataset(fn[:-5])
                if ds:
                    datasets.append(ds)
            # 按创建时间倒序排序，优先匹配最新创建的数据集
            datasets.sort(key=lambda ds: ds.get('created_at', ''), reverse=True)
        
        # 8. 构建 homework_items
        homework_items = []
        for row in rows:
            book_id = str(row.get('book_id', '')) if row.get('book_id') else ''
            page_num = row.get('page_num')
            page_num_int = int(page_num) if page_num is not None else None
            
            # 确定匹配的数据集
            matched_dataset = dataset_id  # 优先使用计划指定的数据集
            matched_dataset_name = dataset_name
            
            if not matched_dataset:
                # 自动匹配数据集
                for ds in datasets:
                    ds_book_id = str(ds.get('book_id', '')) if ds.get('book_id') else ''
                    ds_pages = ds.get('pages', [])
                    base_effects = ds.get('base_effects', {})
                    
                    if ds_book_id == book_id and page_num_int is not None:
                        page_in_pages = page_num_int in ds_pages or str(page_num_int) in [str(p) for p in ds_pages]
                        page_in_effects = str(page_num_int) in base_effects
                        
                        if page_in_pages and page_in_effects:
                            matched_dataset = ds.get('dataset_id')
                            matched_dataset_name = ds.get('name', '')
                            break
            
            homework_items.append({
                'homework_id': str(row['id']),
                'student_id': str(row.get('student_id', '')),
                'student_name': row.get('student_name', ''),
                'homework_name': row.get('homework_name', ''),
                'book_id': book_id,
                'book_name': row.get('book_name', ''),
                'page_num': page_num,
                'pic_path': row.get('pic_path', ''),
                'homework_result': row.get('homework_result', '[]'),
                'data_value': row.get('data_value', '[]'),  # 题目类型信息来源
                'matched_dataset': matched_dataset,
                'matched_dataset_name': matched_dataset_name,
                'status': 'matched' if matched_dataset else 'pending',
                'accuracy': None,
                'evaluation': None
            })
        
        # 9. 生成任务ID和名称
        task_id = str(uuid.uuid4())[:8]
        now = datetime.now()
        plan_name = plan.get('name', '')
        
        # 任务名称格式: 计划名称-月/日 或 学科-月/日
        if plan_name:
            task_name = f'{plan_name}-{now.month}/{now.day}'
        elif subject_name:
            task_name = f'{subject_name}-{now.month}/{now.day}'
        else:
            task_name = f'批量评估-{now.month}/{now.day}'
        
        # 10. 创建任务数据
        task_data = {
            'task_id': task_id,
            'name': task_name,
            'subject_id': subject_id,
            'subject_name': subject_name,
            'test_plan_id': plan_id,  # 关联测试计划
            'test_plan_name': plan_name,
            'fuzzy_threshold': 0.85,  # 语文主观题模糊匹配阈值
            'status': 'pending',
            'homework_items': homework_items,
            'overall_report': None,
            'created_at': now.isoformat()
        }
        
        # 11. 保存任务
        StorageService.save_batch_task(task_id, task_data)
        
        # 12. 关联任务到测试计划（插入 test_plan_tasks 表）
        try:
            AppDatabaseService.execute_insert(
                """INSERT INTO test_plan_tasks (plan_id, task_id, task_status, created_at) 
                   VALUES (%s, %s, %s, %s)""",
                (plan_id, task_id, 'pending', now)
            )
        except Exception as e:
            print(f"[TestPlanService] 关联任务到计划失败: {e}")
            # 不影响主流程
        
        return {
            'success': True,
            'task_id': task_id,
            'task_name': task_name,
            'homework_count': len(homework_items),
            'matched_count': sum(1 for item in homework_items if item.get('matched_dataset'))
        }
        
    except Exception as e:
        print(f"[TestPlanService] 从计划创建批量任务失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
