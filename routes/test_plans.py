"""
测试计划路由模块
提供测试计划 CRUD API 和工作流操作
"""
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify

from services.database_service import AppDatabaseService

test_plans_bp = Blueprint('test_plans', __name__)


# ========== 辅助函数 ==========

def get_default_workflow_status():
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


def format_test_plan(row):
    """
    格式化测试计划数据，将数据库行转换为 API 响应格式
    
    Args:
        row: 数据库查询结果行
        
    Returns:
        dict: 格式化后的测试计划数据
    """
    if not row:
        return None
    
    # 解析 JSON 字段
    subject_ids = row.get('subject_ids')
    if subject_ids and isinstance(subject_ids, str):
        try:
            subject_ids = json.loads(subject_ids)
        except:
            subject_ids = []
    
    matched_publish_ids = row.get('matched_publish_ids')
    if matched_publish_ids and isinstance(matched_publish_ids, str):
        try:
            matched_publish_ids = json.loads(matched_publish_ids)
        except:
            matched_publish_ids = []
    
    workflow_status = row.get('workflow_status')
    if workflow_status and isinstance(workflow_status, str):
        try:
            workflow_status = json.loads(workflow_status)
        except:
            workflow_status = get_default_workflow_status()
    elif not workflow_status:
        workflow_status = get_default_workflow_status()
    
    return {
        'id': row.get('id'),
        'plan_id': row.get('plan_id'),
        'name': row.get('name'),
        'description': row.get('description'),
        'subject_ids': subject_ids or [],
        'target_count': row.get('target_count', 0),
        'completed_count': row.get('completed_count', 0),
        'status': row.get('status', 'draft'),
        'start_date': row.get('start_date').isoformat() if row.get('start_date') else None,
        'end_date': row.get('end_date').isoformat() if row.get('end_date') else None,
        'task_keyword': row.get('task_keyword'),
        'keyword_match_type': row.get('keyword_match_type', 'fuzzy'),
        'matched_publish_ids': matched_publish_ids or [],
        'workflow_status': workflow_status,
        'auto_execute': bool(row.get('auto_execute', 0)),
        'grading_threshold': row.get('grading_threshold', 100),
        'assignee_id': row.get('assignee_id'),
        'created_at': row.get('created_at').isoformat() if row.get('created_at') else None,
        'updated_at': row.get('updated_at').isoformat() if row.get('updated_at') else None
    }


# ========== 测试计划 CRUD API ==========

@test_plans_bp.route('/api/test-plans', methods=['POST'])
def create_test_plan():
    """
    创建测试计划
    
    Request Body:
        {
            "name": "计划名称",
            "description": "计划描述",
            "subject_ids": [3],
            "target_count": 50,
            "start_date": "2026-01-23",
            "end_date": "2026-01-30",
            "task_keyword": "p97-98",
            "keyword_match_type": "fuzzy",
            "auto_execute": false,
            "grading_threshold": 100,
            "assignee_id": 1
        }
    
    Returns:
        JSON: {
            success: bool,
            data: { plan_id, ... },
            error: str (if failed)
        }
    """
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        # 验证必填字段
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': '计划名称不能为空'}), 400
        
        if len(name) > 200:
            return jsonify({'success': False, 'error': '计划名称不能超过200个字符'}), 400
        
        # 生成唯一ID
        plan_id = str(uuid.uuid4())[:8]
        
        # 处理可选字段
        description = data.get('description', '')
        subject_ids = data.get('subject_ids', [])
        target_count = data.get('target_count', 0)
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        task_keyword = data.get('task_keyword', '')
        keyword_match_type = data.get('keyword_match_type', 'fuzzy')
        auto_execute = 1 if data.get('auto_execute') else 0
        grading_threshold = data.get('grading_threshold', 100)
        assignee_id = data.get('assignee_id')
        
        # 验证 keyword_match_type
        if keyword_match_type not in ('exact', 'fuzzy', 'regex'):
            keyword_match_type = 'fuzzy'
        
        # 验证 grading_threshold
        if not isinstance(grading_threshold, int) or grading_threshold < 0 or grading_threshold > 100:
            grading_threshold = 100
        
        # 初始化工作流状态
        workflow_status = get_default_workflow_status()
        
        # 插入数据库
        sql = """
            INSERT INTO test_plans 
            (plan_id, name, description, subject_ids, target_count, completed_count, 
             status, start_date, end_date, task_keyword, keyword_match_type, 
             matched_publish_ids, workflow_status, auto_execute, grading_threshold, 
             assignee_id, created_at, updated_at)
            VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        now = datetime.now()
        params = (
            plan_id,
            name,
            description,
            json.dumps(subject_ids) if subject_ids else '[]',
            target_count,
            0,  # completed_count 初始为 0
            'draft',  # 初始状态为草稿
            start_date,
            end_date,
            task_keyword,
            keyword_match_type,
            '[]',  # matched_publish_ids 初始为空数组
            json.dumps(workflow_status),
            auto_execute,
            grading_threshold,
            assignee_id,
            now,
            now
        )
        
        AppDatabaseService.execute_insert(sql, params)
        
        # 返回创建的测试计划
        created_plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        
        return jsonify({
            'success': True,
            'data': format_test_plan(created_plan)
        })
        
    except Exception as e:
        print(f"[TestPlans] 创建测试计划失败: {e}")
        return jsonify({'success': False, 'error': f'创建失败: {str(e)}'}), 500


@test_plans_bp.route('/api/test-plans', methods=['GET'])
def get_test_plans():
    """
    获取测试计划列表
    
    Query Parameters:
        status: 筛选状态 (draft/active/completed/archived)
        subject_id: 筛选学科ID
        page: 页码 (默认1)
        page_size: 每页数量 (默认20)
    
    Returns:
        JSON: {
            success: bool,
            data: {
                items: [...],
                total: int,
                page: int,
                page_size: int
            }
        }
    """
    try:
        # 获取查询参数
        status = request.args.get('status')
        subject_id = request.args.get('subject_id', type=int)
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        # 限制分页参数
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        
        # 构建查询条件
        where_clauses = []
        params = []
        
        # status 为 'all' 或空时不筛选
        if status and status != 'all':
            where_clauses.append("status = %s")
            params.append(status)
        
        if subject_id is not None:
            # 使用 JSON_CONTAINS 查询包含指定学科的计划
            where_clauses.append("JSON_CONTAINS(subject_ids, %s)")
            params.append(json.dumps(subject_id))
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM test_plans WHERE {where_sql}"
        count_result = AppDatabaseService.execute_one(count_sql, tuple(params) if params else None)
        total = count_result['total'] if count_result else 0
        
        # 查询列表
        offset = (page - 1) * page_size
        list_sql = f"""
            SELECT * FROM test_plans 
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        list_params = params + [page_size, offset]
        rows = AppDatabaseService.execute_query(list_sql, tuple(list_params))
        
        # 格式化结果
        items = [format_test_plan(row) for row in rows]
        
        return jsonify({
            'success': True,
            'data': {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 获取测试计划列表失败: {e}")
        return jsonify({'success': False, 'error': f'查询失败: {str(e)}'}), 500


@test_plans_bp.route('/api/test-plans/<plan_id>', methods=['GET'])
def get_test_plan(plan_id):
    """
    获取测试计划详情
    
    Args:
        plan_id: 测试计划ID
    
    Returns:
        JSON: {
            success: bool,
            data: { plan_id, name, ... }
        }
    """
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        sql = "SELECT * FROM test_plans WHERE plan_id = %s"
        row = AppDatabaseService.execute_one(sql, (plan_id,))
        
        if not row:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        return jsonify({
            'success': True,
            'data': format_test_plan(row)
        })
        
    except Exception as e:
        print(f"[TestPlans] 获取测试计划详情失败: {e}")
        return jsonify({'success': False, 'error': f'查询失败: {str(e)}'}), 500


@test_plans_bp.route('/api/test-plans/<plan_id>', methods=['PUT'])
def update_test_plan(plan_id):
    """
    更新测试计划
    
    Args:
        plan_id: 测试计划ID
    
    Request Body:
        {
            "name": "新名称",
            "description": "新描述",
            ...
        }
    
    Returns:
        JSON: {
            success: bool,
            data: { plan_id, ... }
        }
    """
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        # 检查计划是否存在
        existing = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not existing:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        # 构建更新字段
        update_fields = []
        params = []
        
        # 可更新的字段列表
        allowed_fields = [
            'name', 'description', 'subject_ids', 'target_count', 'completed_count',
            'status', 'start_date', 'end_date', 'task_keyword', 'keyword_match_type',
            'matched_publish_ids', 'workflow_status', 'auto_execute', 'grading_threshold',
            'assignee_id'
        ]
        
        for field in allowed_fields:
            if field in data:
                value = data[field]
                
                # 特殊处理
                if field == 'name':
                    if not value or not value.strip():
                        return jsonify({'success': False, 'error': '计划名称不能为空'}), 400
                    if len(value) > 200:
                        return jsonify({'success': False, 'error': '计划名称不能超过200个字符'}), 400
                    value = value.strip()
                
                elif field in ('subject_ids', 'matched_publish_ids', 'workflow_status'):
                    # JSON 字段
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value)
                
                elif field == 'keyword_match_type':
                    if value not in ('exact', 'fuzzy', 'regex'):
                        value = 'fuzzy'
                
                elif field == 'auto_execute':
                    value = 1 if value else 0
                
                elif field == 'grading_threshold':
                    if not isinstance(value, int) or value < 0 or value > 100:
                        value = 100
                
                elif field == 'status':
                    if value not in ('draft', 'active', 'completed', 'archived'):
                        continue  # 跳过无效状态
                
                update_fields.append(f"{field} = %s")
                params.append(value)
        
        if not update_fields:
            return jsonify({'success': False, 'error': '没有可更新的字段'}), 400
        
        # 添加更新时间
        update_fields.append("updated_at = %s")
        params.append(datetime.now())
        
        # 添加 plan_id 条件
        params.append(plan_id)
        
        # 执行更新
        sql = f"UPDATE test_plans SET {', '.join(update_fields)} WHERE plan_id = %s"
        AppDatabaseService.execute_update(sql, tuple(params))
        
        # 返回更新后的数据
        updated_plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        
        return jsonify({
            'success': True,
            'data': format_test_plan(updated_plan)
        })
        
    except Exception as e:
        print(f"[TestPlans] 更新测试计划失败: {e}")
        return jsonify({'success': False, 'error': f'更新失败: {str(e)}'}), 500


@test_plans_bp.route('/api/test-plans/<plan_id>', methods=['DELETE'])
def delete_test_plan(plan_id):
    """
    删除测试计划
    
    Args:
        plan_id: 测试计划ID
    
    Returns:
        JSON: {
            success: bool,
            message: str
        }
    """
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        # 检查计划是否存在
        existing = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not existing:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        # 删除关联的数据集关系
        AppDatabaseService.execute_update(
            "DELETE FROM test_plan_datasets WHERE plan_id = %s", (plan_id,)
        )
        
        # 删除关联的任务关系
        AppDatabaseService.execute_update(
            "DELETE FROM test_plan_tasks WHERE plan_id = %s", (plan_id,)
        )
        
        # 删除测试计划
        AppDatabaseService.execute_update(
            "DELETE FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        
        return jsonify({
            'success': True,
            'message': '测试计划已删除'
        })
        
    except Exception as e:
        print(f"[TestPlans] 删除测试计划失败: {e}")
        return jsonify({'success': False, 'error': f'删除失败: {str(e)}'}), 500


# ========== 测试计划克隆 API ==========

@test_plans_bp.route('/api/test-plans/<plan_id>/clone', methods=['POST'])
def clone_test_plan(plan_id):
    """
    克隆测试计划
    
    Args:
        plan_id: 要克隆的测试计划ID
    
    Returns:
        JSON: {
            success: bool,
            data: { plan_id, ... }  # 新创建的计划
        }
    """
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        # 获取原计划
        original = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not original:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        # 生成新ID
        new_plan_id = str(uuid.uuid4())[:8]
        
        # 复制字段，修改名称
        new_name = f"{original['name']}(副本)"
        if len(new_name) > 200:
            new_name = new_name[:197] + "..."
        
        # 重置工作流状态
        workflow_status = get_default_workflow_status()
        
        # 插入新计划
        sql = """
            INSERT INTO test_plans 
            (plan_id, name, description, subject_ids, target_count, completed_count, 
             status, start_date, end_date, task_keyword, keyword_match_type, 
             matched_publish_ids, workflow_status, auto_execute, grading_threshold, 
             assignee_id, created_at, updated_at)
            VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        now = datetime.now()
        params = (
            new_plan_id,
            new_name,
            original.get('description'),
            original.get('subject_ids'),
            original.get('target_count', 0),
            0,  # completed_count 重置为 0
            'draft',  # 状态重置为草稿
            original.get('start_date'),
            original.get('end_date'),
            original.get('task_keyword'),
            original.get('keyword_match_type', 'fuzzy'),
            '[]',  # matched_publish_ids 重置为空
            json.dumps(workflow_status),
            original.get('auto_execute', 0),
            original.get('grading_threshold', 100),
            original.get('assignee_id'),
            now,
            now
        )
        
        AppDatabaseService.execute_insert(sql, params)
        
        # 返回新创建的计划
        new_plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (new_plan_id,)
        )
        
        return jsonify({
            'success': True,
            'data': format_test_plan(new_plan)
        })
        
    except Exception as e:
        print(f"[TestPlans] 克隆测试计划失败: {e}")
        return jsonify({'success': False, 'error': f'克隆失败: {str(e)}'}), 500


# ========== 测试计划状态更新 API ==========

# ========== 辅助函数：页码解析 ==========

def parse_page_region(page_region: str) -> list:
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
    # 替换全角波浪号和半角波浪号为连字符
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
                # 解析失败，跳过该部分
                continue
        else:
            # 单个页码
            try:
                pages.append(int(part))
            except ValueError:
                # 解析失败，跳过该部分
                continue
    
    # 返回排序去重的列表
    return sorted(set(pages))


# ========== 关键字匹配预览 API ==========

@test_plans_bp.route('/api/test-plans/preview-match', methods=['POST'])
def preview_match():
    """
    预览关键字匹配结果
    
    查询 zpsmart 数据库的 zp_homework_publish 表，
    根据关键字匹配作业发布记录，返回匹配结果及统计信息。
    
    新增功能：
    - 支持 subject_id 过滤
    - 返回 publish.status 字段判断批改是否完成（status=2 表示全部完成）
    
    Request Body:
        {
            "keyword": "p97-98",           # 必填，搜索关键字
            "match_type": "fuzzy",         # 可选，匹配类型: exact/fuzzy/regex，默认 fuzzy
            "subject_id": 4,               # 可选，学科ID过滤
            "book_id": "1997848714229166082",  # 可选，限定书本ID
            "dataset_id": "b3b0395e"       # 可选，从数据集获取 book_id
        }
    
    Returns:
        JSON: {
            success: bool,
            data: {
                matched_count: int,        # 匹配到的发布数量
                total_homework: int,       # 总作业数
                total_graded: int,         # 已批改数
                all_completed: bool,       # 是否全部完成（所有 publish.status=2）
                completed_count: int,      # 已完成的 publish 数量
                matches: [                 # 匹配到的发布列表
                    {
                        publish_id: str,
                        content: str,
                        subject_id: int,
                        book_id: str,
                        page_region: str,
                        pages: list,       # 解析后的页码列表
                        total_homework: int,
                        graded_count: int,
                        grading_progress: float,
                        status: int,       # publish 状态（2=全部批改完成）
                        is_completed: bool,# 是否完成
                        create_time: str
                    }
                ]
            },
            error: str (if failed)
        }
    """
    from services.database_service import DatabaseService
    
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        # 获取并验证关键字
        keyword = data.get('keyword', '').strip()
        if not keyword:
            return jsonify({'success': False, 'error': '关键字不能为空'}), 400
        
        # 获取匹配类型，默认模糊匹配
        match_type = data.get('match_type', 'fuzzy')
        if match_type not in ('exact', 'fuzzy', 'regex'):
            match_type = 'fuzzy'
        
        # 获取学科ID过滤
        subject_id = data.get('subject_id')
        if subject_id is not None:
            try:
                subject_id = int(subject_id)
            except (ValueError, TypeError):
                subject_id = None
        
        # 获取 book_id（可以直接传入或从数据集获取）
        book_id = data.get('book_id')
        dataset_id = data.get('dataset_id')
        
        # 如果提供了 dataset_id，从数据集获取 book_id
        if dataset_id and not book_id:
            dataset = AppDatabaseService.get_dataset(dataset_id)
            if dataset:
                book_id = dataset.get('book_id')
        
        # 构建 SQL 查询
        # 根据匹配类型构建 WHERE 条件
        if match_type == 'exact':
            # 精确匹配
            content_condition = "hp.content = %s"
            content_param = keyword
        elif match_type == 'regex':
            # 正则表达式匹配
            content_condition = "hp.content REGEXP %s"
            content_param = keyword
        else:
            # 模糊匹配（默认）
            content_condition = "hp.content LIKE %s"
            content_param = f'%{keyword}%'
        
        # 构建完整 SQL
        # 查询 zp_homework_publish 并统计关联的作业数量和批改状态
        # 新增：查询 hp.status 字段（status=2 表示全部批改完成）
        sql = f"""
            SELECT 
                hp.id as publish_id,
                hp.content,
                hp.subject_id,
                hp.book_id,
                hp.page_region,
                hp.status,
                hp.create_time,
                b.book_name,
                COUNT(h.id) as total_homework,
                SUM(CASE 
                    WHEN h.homework_result IS NOT NULL 
                    AND h.homework_result != '' 
                    AND h.homework_result != '[]' 
                    THEN 1 ELSE 0 
                END) as graded_count
            FROM zp_homework_publish hp
            LEFT JOIN zp_homework h ON h.hw_publish_id = hp.id
            LEFT JOIN zp_make_book b ON hp.book_id = b.id
            WHERE {content_condition}
        """
        
        params = [content_param]
        
        # 如果指定了 subject_id，添加过滤条件
        if subject_id is not None:
            sql += " AND hp.subject_id = %s"
            params.append(subject_id)
        
        # 如果指定了 book_id，添加过滤条件
        if book_id:
            sql += " AND hp.book_id = %s"
            params.append(book_id)
        
        # 分组和排序
        sql += """
            GROUP BY hp.id, hp.content, hp.subject_id, hp.book_id, hp.page_region, hp.status, hp.create_time, b.book_name
            ORDER BY hp.create_time DESC
            LIMIT 50
        """
        
        # 执行查询（使用 zpsmart 数据库）
        rows = DatabaseService.execute_query(sql, tuple(params))
        
        # 处理结果
        matches = []
        total_homework_sum = 0
        total_graded_sum = 0
        completed_count = 0
        
        for row in rows:
            total_hw = row.get('total_homework', 0) or 0
            graded = row.get('graded_count', 0) or 0
            publish_status = row.get('status', 0) or 0
            
            # status=2 表示该 publish 的所有作业都已批改完成
            is_completed = (publish_status == 2)
            if is_completed:
                completed_count += 1
            
            # 计算批改进度百分比
            grading_progress = round(graded / total_hw * 100, 1) if total_hw > 0 else 0
            
            # 解析页码范围
            page_region = row.get('page_region', '')
            pages = parse_page_region(page_region)
            
            # 格式化创建时间
            create_time = row.get('create_time')
            if create_time:
                if hasattr(create_time, 'isoformat'):
                    create_time = create_time.isoformat()
                else:
                    create_time = str(create_time)
            
            matches.append({
                'publish_id': str(row.get('publish_id', '')),
                'content': row.get('content', ''),
                'subject_id': row.get('subject_id'),
                'book_id': str(row.get('book_id', '')),
                'book_name': row.get('book_name', ''),
                'page_region': page_region,
                'pages': pages,
                'total_homework': total_hw,
                'graded_count': graded,
                'grading_progress': grading_progress,
                'status': publish_status,
                'is_completed': is_completed,
                'create_time': create_time
            })
            
            total_homework_sum += total_hw
            total_graded_sum += graded
        
        # 判断是否全部完成
        all_completed = len(matches) > 0 and completed_count == len(matches)
        
        return jsonify({
            'success': True,
            'data': {
                'matched_count': len(matches),
                'total_homework': total_homework_sum,
                'total_graded': total_graded_sum,
                'all_completed': all_completed,
                'completed_count': completed_count,
                'matches': matches
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 预览匹配失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'匹配查询失败: {str(e)}'}), 500


@test_plans_bp.route('/api/test-plans/<plan_id>/status', methods=['PUT'])
def update_test_plan_status(plan_id):
    """
    更新测试计划状态
    
    Args:
        plan_id: 测试计划ID
    
    Request Body:
        {
            "status": "active"  # draft/active/completed/archived
        }
    
    Returns:
        JSON: {
            success: bool,
            data: { plan_id, status, ... }
        }
    """
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        new_status = data.get('status')
        if new_status not in ('draft', 'active', 'completed', 'archived'):
            return jsonify({'success': False, 'error': '无效的状态值'}), 400
        
        # 检查计划是否存在
        existing = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not existing:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        # 更新状态
        sql = "UPDATE test_plans SET status = %s, updated_at = %s WHERE plan_id = %s"
        AppDatabaseService.execute_update(sql, (new_status, datetime.now(), plan_id))
        
        # 返回更新后的数据
        updated_plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        
        return jsonify({
            'success': True,
            'data': format_test_plan(updated_plan)
        })
        
    except Exception as e:
        print(f"[TestPlans] 更新测试计划状态失败: {e}")
        return jsonify({'success': False, 'error': f'更新失败: {str(e)}'}), 500


# ========== 工作流操作 API ==========

@test_plans_bp.route('/api/test-plans/<plan_id>/match-homework', methods=['POST'])
def match_homework(plan_id):
    """
    执行作业匹配
    
    根据测试计划的关键字配置，匹配 zpsmart 数据库中的作业发布，
    并保存匹配结果到 matched_publish_ids 字段。
    
    Args:
        plan_id: 测试计划ID
    
    Request Body (可选):
        {
            "keyword": "p97-98",           # 可选，覆盖计划中的关键字
            "match_type": "fuzzy",         # 可选，覆盖计划中的匹配类型
            "publish_ids": ["id1", "id2"]  # 可选，直接指定要匹配的 publish ID
        }
    
    Returns:
        JSON: {
            success: bool,
            data: {
                matched_count: int,
                total_homework: int,
                total_graded: int,
                matches: [...],
                workflow_status: {...}
            },
            error: str (if failed)
        }
    """
    from services.test_plan_service import (
        match_homework_publish, 
        save_matched_publish_ids,
        update_workflow_status,
        check_grading_status
    )
    
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        # 获取测试计划
        plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not plan:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        # 获取请求参数
        data = request.json or {}
        
        # 如果直接指定了 publish_ids，直接保存
        if 'publish_ids' in data and data['publish_ids']:
            publish_ids = data['publish_ids']
            
            # 检查批改状态
            grading_status = check_grading_status(publish_ids)
            
            # 保存匹配结果
            save_matched_publish_ids(plan_id, publish_ids)
            
            # 更新工作流状态
            update_workflow_status(plan_id, 'homework_match', {
                'status': 'in_progress',
                'matched_publish': [{'publish_id': pid} for pid in publish_ids],
                'total_homework': grading_status['total_homework'],
                'total_graded': grading_status['graded_count'],
                'grading_progress': grading_status['grading_progress'],
                'last_checked': datetime.now().isoformat()
            })
            
            # 获取更新后的计划
            updated_plan = AppDatabaseService.execute_one(
                "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
            )
            
            return jsonify({
                'success': True,
                'data': {
                    'matched_count': len(publish_ids),
                    'total_homework': grading_status['total_homework'],
                    'total_graded': grading_status['graded_count'],
                    'grading_progress': grading_status['grading_progress'],
                    'matches': [{'publish_id': pid} for pid in publish_ids],
                    'workflow_status': format_test_plan(updated_plan).get('workflow_status', {})
                }
            })
        
        # 获取关键字和匹配类型
        keyword = data.get('keyword') or plan.get('task_keyword', '')
        match_type = data.get('match_type') or plan.get('keyword_match_type', 'fuzzy')
        
        if not keyword:
            return jsonify({'success': False, 'error': '任务关键字不能为空'}), 400
        
        # 获取数据集信息（用于 book_id 和页码匹配）
        book_id = None
        dataset_pages = None
        
        workflow_status = plan.get('workflow_status')
        if workflow_status and isinstance(workflow_status, str):
            try:
                workflow_status = json.loads(workflow_status)
            except:
                workflow_status = {}
        
        dataset_id = workflow_status.get('dataset', {}).get('dataset_id') if workflow_status else None
        
        if dataset_id:
            dataset = AppDatabaseService.get_dataset(dataset_id)
            if dataset:
                book_id = dataset.get('book_id')
                pages = dataset.get('pages')
                if pages:
                    if isinstance(pages, str):
                        try:
                            dataset_pages = json.loads(pages)
                        except:
                            dataset_pages = None
                    else:
                        dataset_pages = pages
        
        # 执行匹配
        result = match_homework_publish(
            keyword=keyword,
            match_type=match_type,
            book_id=book_id,
            dataset_pages=dataset_pages
        )
        
        if not result['success']:
            return jsonify({
                'success': False, 
                'error': result.get('error', '匹配失败')
            }), 500
        
        # 提取匹配到的 publish_ids
        publish_ids = [m['publish_id'] for m in result['matches']]
        
        # 保存匹配结果
        save_matched_publish_ids(plan_id, publish_ids)
        
        # 更新工作流状态
        matched_publish_info = []
        for match in result['matches']:
            matched_publish_info.append({
                'publish_id': match['publish_id'],
                'content': match['content'],
                'total_homework': match['total_homework'],
                'graded_count': match['graded_count'],
                'grading_progress': match['grading_progress']
            })
        
        update_workflow_status(plan_id, 'homework_match', {
            'status': 'in_progress' if result['total_graded'] < result['total_homework'] else 'completed',
            'matched_publish': matched_publish_info,
            'total_homework': result['total_homework'],
            'total_graded': result['total_graded'],
            'grading_progress': round(result['total_graded'] / result['total_homework'] * 100, 1) if result['total_homework'] > 0 else 0,
            'last_checked': datetime.now().isoformat()
        })
        
        # 获取更新后的计划
        updated_plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        
        return jsonify({
            'success': True,
            'data': {
                'matched_count': result['matched_count'],
                'total_homework': result['total_homework'],
                'total_graded': result['total_graded'],
                'grading_progress': round(result['total_graded'] / result['total_homework'] * 100, 1) if result['total_homework'] > 0 else 0,
                'matches': result['matches'],
                'workflow_status': format_test_plan(updated_plan).get('workflow_status', {})
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 执行作业匹配失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'匹配失败: {str(e)}'}), 500


@test_plans_bp.route('/api/test-plans/<plan_id>/grading-status', methods=['GET'])
def get_grading_status(plan_id):
    """
    获取批改状态
    
    查询测试计划关联的作业发布的批改进度。
    
    Args:
        plan_id: 测试计划ID
    
    Returns:
        JSON: {
            success: bool,
            data: {
                total_homework: int,
                graded_count: int,
                grading_progress: float,
                is_complete: bool,
                threshold: int,
                can_start_evaluation: bool,
                last_updated: str,
                publish_details: [...]
            }
        }
    """
    from services.test_plan_service import check_grading_status
    
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        # 获取测试计划
        plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not plan:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        # 获取匹配的 publish_ids
        matched_publish_ids = plan.get('matched_publish_ids')
        if matched_publish_ids and isinstance(matched_publish_ids, str):
            try:
                matched_publish_ids = json.loads(matched_publish_ids)
            except:
                matched_publish_ids = []
        
        if not matched_publish_ids:
            return jsonify({
                'success': True,
                'data': {
                    'total_homework': 0,
                    'graded_count': 0,
                    'grading_progress': 0,
                    'is_complete': False,
                    'threshold': plan.get('grading_threshold', 100),
                    'can_start_evaluation': False,
                    'last_updated': datetime.now().isoformat(),
                    'publish_details': []
                }
            })
        
        # 检查批改状态
        status = check_grading_status(matched_publish_ids)
        
        # 判断是否可以开始评估
        threshold = plan.get('grading_threshold', 100)
        can_start_evaluation = status['grading_progress'] >= threshold
        
        return jsonify({
            'success': True,
            'data': {
                'total_homework': status['total_homework'],
                'graded_count': status['graded_count'],
                'grading_progress': status['grading_progress'],
                'is_complete': status['is_complete'],
                'threshold': threshold,
                'can_start_evaluation': can_start_evaluation,
                'last_updated': datetime.now().isoformat(),
                'publish_details': status.get('publish_details', [])
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 获取批改状态失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'查询失败: {str(e)}'}), 500


@test_plans_bp.route('/api/test-plans/<plan_id>/refresh-grading', methods=['POST'])
def refresh_grading_status(plan_id):
    """
    刷新批改状态
    
    重新查询批改状态并更新 workflow_status.homework_match。
    
    Args:
        plan_id: 测试计划ID
    
    Returns:
        JSON: {
            success: bool,
            data: {
                total_homework: int,
                graded_count: int,
                grading_progress: float,
                is_complete: bool,
                threshold: int,
                can_start_evaluation: bool,
                workflow_status: {...}
            }
        }
    """
    from services.test_plan_service import check_grading_status, update_workflow_status
    
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        # 获取测试计划
        plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not plan:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        # 获取匹配的 publish_ids
        matched_publish_ids = plan.get('matched_publish_ids')
        if matched_publish_ids and isinstance(matched_publish_ids, str):
            try:
                matched_publish_ids = json.loads(matched_publish_ids)
            except:
                matched_publish_ids = []
        
        if not matched_publish_ids:
            return jsonify({
                'success': False,
                'error': '尚未匹配作业发布，请先执行作业匹配'
            }), 400
        
        # 检查批改状态
        status = check_grading_status(matched_publish_ids)
        
        # 判断是否可以开始评估
        threshold = plan.get('grading_threshold', 100)
        can_start_evaluation = status['grading_progress'] >= threshold
        
        # 确定工作流状态
        if status['is_complete']:
            workflow_step_status = 'completed'
        elif status['graded_count'] > 0:
            workflow_step_status = 'in_progress'
        else:
            workflow_step_status = 'not_started'
        
        # 获取当前 workflow_status 中的 matched_publish 信息
        current_workflow = plan.get('workflow_status')
        if current_workflow and isinstance(current_workflow, str):
            try:
                current_workflow = json.loads(current_workflow)
            except:
                current_workflow = {}
        
        matched_publish_info = current_workflow.get('homework_match', {}).get('matched_publish', [])
        
        # 更新 matched_publish 中的批改进度
        publish_details_map = {d['publish_id']: d for d in status.get('publish_details', [])}
        for mp in matched_publish_info:
            pid = mp.get('publish_id')
            if pid in publish_details_map:
                mp['total_homework'] = publish_details_map[pid]['total']
                mp['graded_count'] = publish_details_map[pid]['graded']
                mp['grading_progress'] = publish_details_map[pid]['progress']
        
        # 更新工作流状态
        update_workflow_status(plan_id, 'homework_match', {
            'status': workflow_step_status,
            'matched_publish': matched_publish_info,
            'total_homework': status['total_homework'],
            'total_graded': status['graded_count'],
            'grading_progress': status['grading_progress'],
            'last_checked': datetime.now().isoformat()
        })
        
        # 获取更新后的计划
        updated_plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        
        return jsonify({
            'success': True,
            'data': {
                'total_homework': status['total_homework'],
                'graded_count': status['graded_count'],
                'grading_progress': status['grading_progress'],
                'is_complete': status['is_complete'],
                'threshold': threshold,
                'can_start_evaluation': can_start_evaluation,
                'workflow_status': format_test_plan(updated_plan).get('workflow_status', {})
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 刷新批改状态失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'刷新失败: {str(e)}'}), 500


@test_plans_bp.route('/api/test-plans/<plan_id>/workflow-progress', methods=['GET'])
def get_workflow_progress_api(plan_id):
    """
    获取工作流进度
    
    返回测试计划的工作流整体进度信息。
    
    Args:
        plan_id: 测试计划ID
    
    Returns:
        JSON: {
            success: bool,
            data: {
                workflow_status: {...},
                current_step: str,
                completed_steps: [...],
                progress_percent: float,
                can_proceed: bool,
                next_action: str
            }
        }
    """
    from services.test_plan_service import get_workflow_progress
    
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        result = get_workflow_progress(plan_id)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'error': result.get('error', '获取进度失败')
            }), 404 if '不存在' in result.get('error', '') else 500
        
        return jsonify({
            'success': True,
            'data': {
                'workflow_status': result['workflow_status'],
                'current_step': result['current_step'],
                'completed_steps': result['completed_steps'],
                'progress_percent': result['progress_percent'],
                'can_proceed': result['can_proceed'],
                'next_action': result['next_action']
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 获取工作流进度失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'查询失败: {str(e)}'}), 500


@test_plans_bp.route('/api/test-plans/<plan_id>/update-dataset', methods=['POST'])
def update_plan_dataset(plan_id):
    """
    更新测试计划的数据集配置
    
    设置测试计划关联的数据集，并更新 workflow_status.dataset 状态。
    
    Args:
        plan_id: 测试计划ID
    
    Request Body:
        {
            "dataset_id": "b3b0395e"
        }
    
    Returns:
        JSON: {
            success: bool,
            data: {
                dataset_id: str,
                dataset_name: str,
                question_count: int,
                workflow_status: {...}
            }
        }
    """
    from services.test_plan_service import update_workflow_status
    
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        dataset_id = data.get('dataset_id')
        if not dataset_id:
            return jsonify({'success': False, 'error': '数据集ID不能为空'}), 400
        
        # 检查测试计划是否存在
        plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not plan:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        # 获取数据集信息
        dataset = AppDatabaseService.get_dataset(dataset_id)
        if not dataset:
            return jsonify({'success': False, 'error': '数据集不存在'}), 404
        
        # 更新工作流状态
        update_workflow_status(plan_id, 'dataset', {
            'status': 'completed',
            'dataset_id': dataset_id,
            'dataset_name': dataset.get('name', ''),
            'question_count': dataset.get('question_count', 0),
            'completed_at': datetime.now().isoformat()
        })
        
        # 同时更新 test_plan_datasets 关联表
        # 先删除旧关联
        AppDatabaseService.execute_update(
            "DELETE FROM test_plan_datasets WHERE plan_id = %s",
            (plan_id,)
        )
        # 插入新关联
        AppDatabaseService.execute_insert(
            "INSERT INTO test_plan_datasets (plan_id, dataset_id, created_at) VALUES (%s, %s, %s)",
            (plan_id, dataset_id, datetime.now())
        )
        
        # 获取更新后的计划
        updated_plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        
        return jsonify({
            'success': True,
            'data': {
                'dataset_id': dataset_id,
                'dataset_name': dataset.get('name', ''),
                'question_count': dataset.get('question_count', 0),
                'workflow_status': format_test_plan(updated_plan).get('workflow_status', {})
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 更新数据集配置失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'更新失败: {str(e)}'}), 500



# ========== 批量评估集成 API ==========

@test_plans_bp.route('/api/test-plans/<plan_id>/start-evaluation', methods=['POST'])
def start_evaluation(plan_id):
    """
    开始批量评估
    
    从测试计划创建批量评估任务，并更新工作流状态。
    
    Args:
        plan_id: 测试计划ID
    
    Returns:
        JSON: {
            success: bool,
            data: {
                task_id: str,           # 创建的批量任务ID
                task_name: str,         # 任务名称
                homework_count: int,    # 作业数量
                matched_count: int,     # 匹配数据集的作业数量
                workflow_status: {...}  # 更新后的工作流状态
            },
            error: str (if failed)
        }
    """
    from services.test_plan_service import (
        create_batch_task_from_plan,
        update_workflow_status,
        check_grading_status
    )
    
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        # 获取测试计划
        plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not plan:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        # 检查是否已有进行中的评估
        workflow_status = plan.get('workflow_status')
        if workflow_status and isinstance(workflow_status, str):
            try:
                workflow_status = json.loads(workflow_status)
            except:
                workflow_status = {}
        
        eval_status = workflow_status.get('evaluation', {}).get('status') if workflow_status else None
        if eval_status == 'in_progress':
            existing_task_id = workflow_status.get('evaluation', {}).get('task_id')
            return jsonify({
                'success': False,
                'error': f'已有进行中的评估任务: {existing_task_id}'
            }), 400
        
        # 检查批改进度是否达到阈值
        matched_publish_ids = plan.get('matched_publish_ids')
        if matched_publish_ids and isinstance(matched_publish_ids, str):
            try:
                matched_publish_ids = json.loads(matched_publish_ids)
            except:
                matched_publish_ids = []
        
        if not matched_publish_ids:
            return jsonify({
                'success': False,
                'error': '尚未匹配作业发布，请先执行作业匹配'
            }), 400
        
        grading_status = check_grading_status(matched_publish_ids)
        threshold = plan.get('grading_threshold', 100)
        
        if grading_status['grading_progress'] < threshold:
            return jsonify({
                'success': False,
                'error': f'批改进度未达到阈值（当前 {grading_status["grading_progress"]}%，需达到 {threshold}%）'
            }), 400
        
        # 创建批量评估任务
        result = create_batch_task_from_plan(plan_id)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'error': result.get('error', '创建评估任务失败')
            }), 500
        
        # 更新工作流状态
        update_workflow_status(plan_id, 'evaluation', {
            'status': 'in_progress',
            'task_id': result['task_id'],
            'task_name': result.get('task_name', ''),
            'homework_count': result['homework_count'],
            'matched_count': result.get('matched_count', 0),
            'accuracy': None,
            'started_at': datetime.now().isoformat(),
            'completed_at': None
        })
        
        # 获取更新后的计划
        updated_plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': result['task_id'],
                'task_name': result.get('task_name', ''),
                'homework_count': result['homework_count'],
                'matched_count': result.get('matched_count', 0),
                'workflow_status': format_test_plan(updated_plan).get('workflow_status', {})
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 开始评估失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'开始评估失败: {str(e)}'}), 500


@test_plans_bp.route('/api/test-plans/<plan_id>/evaluation-status', methods=['GET'])
def get_evaluation_status(plan_id):
    """
    获取评估状态
    
    查询测试计划关联的批量评估任务的执行状态。
    
    Args:
        plan_id: 测试计划ID
    
    Returns:
        JSON: {
            success: bool,
            data: {
                status: str,            # not_started/in_progress/completed/failed
                task_id: str,           # 批量任务ID
                task_name: str,         # 任务名称
                accuracy: float,        # 准确率（完成后）
                homework_count: int,    # 作业数量
                completed_count: int,   # 已评估数量
                progress: float,        # 评估进度百分比
                started_at: str,
                completed_at: str
            }
        }
    """
    from services.storage_service import StorageService
    
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        # 获取测试计划
        plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not plan:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        # 获取工作流状态
        workflow_status = plan.get('workflow_status')
        if workflow_status and isinstance(workflow_status, str):
            try:
                workflow_status = json.loads(workflow_status)
            except:
                workflow_status = {}
        
        eval_info = workflow_status.get('evaluation', {}) if workflow_status else {}
        task_id = eval_info.get('task_id')
        
        # 如果没有任务ID，返回未开始状态
        if not task_id:
            return jsonify({
                'success': True,
                'data': {
                    'status': 'not_started',
                    'task_id': None,
                    'task_name': None,
                    'accuracy': None,
                    'homework_count': 0,
                    'completed_count': 0,
                    'progress': 0,
                    'started_at': None,
                    'completed_at': None
                }
            })
        
        # 加载批量任务数据
        task_data = StorageService.load_batch_task(task_id)
        
        if not task_data:
            return jsonify({
                'success': True,
                'data': {
                    'status': eval_info.get('status', 'not_started'),
                    'task_id': task_id,
                    'task_name': eval_info.get('task_name'),
                    'accuracy': eval_info.get('accuracy'),
                    'homework_count': eval_info.get('homework_count', 0),
                    'completed_count': 0,
                    'progress': 0,
                    'started_at': eval_info.get('started_at'),
                    'completed_at': eval_info.get('completed_at'),
                    'error': '任务数据不存在'
                }
            })
        
        # 计算评估进度
        homework_items = task_data.get('homework_items', [])
        total_count = len(homework_items)
        completed_count = sum(1 for item in homework_items if item.get('status') == 'completed')
        progress = round(completed_count / total_count * 100, 1) if total_count > 0 else 0
        
        # 获取准确率
        overall_report = task_data.get('overall_report', {})
        accuracy = overall_report.get('overall_accuracy') if overall_report else None
        
        # 确定状态
        task_status = task_data.get('status', 'pending')
        if task_status == 'completed':
            status = 'completed'
        elif task_status == 'failed':
            status = 'failed'
        elif completed_count > 0:
            status = 'in_progress'
        else:
            status = 'in_progress' if eval_info.get('status') == 'in_progress' else 'not_started'
        
        return jsonify({
            'success': True,
            'data': {
                'status': status,
                'task_id': task_id,
                'task_name': task_data.get('name', ''),
                'accuracy': accuracy,
                'homework_count': total_count,
                'completed_count': completed_count,
                'progress': progress,
                'started_at': eval_info.get('started_at'),
                'completed_at': eval_info.get('completed_at')
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 获取评估状态失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'查询失败: {str(e)}'}), 500


@test_plans_bp.route('/api/test-plans/<plan_id>/complete-evaluation', methods=['POST'])
def complete_evaluation(plan_id):
    """
    完成评估（更新工作流状态）
    
    当批量评估任务完成后，调用此接口更新工作流状态。
    
    Args:
        plan_id: 测试计划ID
    
    Request Body:
        {
            "accuracy": 0.85,           # 可选，准确率
            "task_id": "xxx"            # 可选，任务ID（用于验证）
        }
    
    Returns:
        JSON: {
            success: bool,
            data: {
                workflow_status: {...}
            }
        }
    """
    from services.test_plan_service import update_workflow_status
    from services.storage_service import StorageService
    
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        # 获取测试计划
        plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not plan:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        # 获取请求数据
        data = request.json or {}
        
        # 获取工作流状态
        workflow_status = plan.get('workflow_status')
        if workflow_status and isinstance(workflow_status, str):
            try:
                workflow_status = json.loads(workflow_status)
            except:
                workflow_status = {}
        
        eval_info = workflow_status.get('evaluation', {}) if workflow_status else {}
        task_id = data.get('task_id') or eval_info.get('task_id')
        
        # 获取准确率
        accuracy = data.get('accuracy')
        
        # 如果没有提供准确率，从任务数据中获取
        if accuracy is None and task_id:
            task_data = StorageService.load_batch_task(task_id)
            if task_data:
                overall_report = task_data.get('overall_report', {})
                accuracy = overall_report.get('overall_accuracy') if overall_report else None
        
        # 更新工作流状态
        update_workflow_status(plan_id, 'evaluation', {
            'status': 'completed',
            'accuracy': accuracy,
            'completed_at': datetime.now().isoformat()
        })
        
        # 更新 test_plan_tasks 表中的任务状态
        if task_id:
            try:
                AppDatabaseService.execute_update(
                    """UPDATE test_plan_tasks 
                       SET task_status = %s, accuracy = %s, updated_at = %s 
                       WHERE plan_id = %s AND task_id = %s""",
                    ('completed', accuracy, datetime.now(), plan_id, task_id)
                )
            except Exception as e:
                print(f"[TestPlans] 更新任务状态失败: {e}")
        
        # 获取更新后的计划
        updated_plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        
        return jsonify({
            'success': True,
            'data': {
                'accuracy': accuracy,
                'workflow_status': format_test_plan(updated_plan).get('workflow_status', {})
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 完成评估失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'更新失败: {str(e)}'}), 500


# ========== 报告生成 API ==========

@test_plans_bp.route('/api/test-plans/<plan_id>/generate-report', methods=['POST'])
def generate_report(plan_id):
    """
    生成测试报告
    
    从评估结果中聚合统计数据，生成测试报告，并更新工作流状态。
    
    Args:
        plan_id: 测试计划ID
    
    Request Body (可选):
        {
            "task_id": "xxx"    # 可选，指定批量任务ID
        }
    
    Returns:
        JSON: {
            success: bool,
            data: {
                report: {
                    report_id: str,
                    plan_id: str,
                    task_id: str,
                    overall_accuracy: float,
                    total_questions: int,
                    correct_count: int,
                    error_count: int,
                    error_distribution: dict,
                    question_type_stats: dict,
                    subject_stats: dict,
                    homework_stats: dict,
                    generated_at: str
                },
                workflow_status: {...}
            },
            error: str (if failed)
        }
    """
    from services.test_plan_service import generate_test_report, update_workflow_status
    
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        # 获取测试计划
        plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not plan:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        # 获取请求参数
        data = request.json or {}
        task_id = data.get('task_id')
        
        # 检查评估是否完成
        workflow_status = plan.get('workflow_status')
        if workflow_status and isinstance(workflow_status, str):
            try:
                workflow_status = json.loads(workflow_status)
            except:
                workflow_status = {}
        
        eval_status = workflow_status.get('evaluation', {}).get('status') if workflow_status else None
        if eval_status != 'completed':
            return jsonify({
                'success': False,
                'error': '批量评估尚未完成，请先完成评估'
            }), 400
        
        # 生成报告
        result = generate_test_report(plan_id, task_id)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'error': result.get('error', '生成报告失败')
            }), 500
        
        report = result['report']
        
        # 更新工作流状态
        update_workflow_status(plan_id, 'report', {
            'status': 'completed',
            'report_id': report['report_id'],
            'overall_accuracy': report['overall_accuracy'],
            'total_questions': report['total_questions'],
            'correct_count': report['correct_count'],
            'error_count': report['error_count'],
            'generated_at': report['generated_at']
        })
        
        # 获取更新后的计划
        updated_plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        
        return jsonify({
            'success': True,
            'data': {
                'report': report,
                'workflow_status': format_test_plan(updated_plan).get('workflow_status', {})
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 生成报告失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'生成报告失败: {str(e)}'}), 500


@test_plans_bp.route('/api/test-plans/<plan_id>/report', methods=['GET'])
def get_report(plan_id):
    """
    获取测试报告
    
    获取测试计划的报告数据。如果报告尚未生成，返回空数据。
    
    Args:
        plan_id: 测试计划ID
    
    Query Parameters:
        regenerate: 是否重新生成报告 (true/false)
    
    Returns:
        JSON: {
            success: bool,
            data: {
                report: {...} or null,
                status: str  # not_started/completed
            }
        }
    """
    from services.test_plan_service import generate_test_report
    
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        # 获取测试计划
        plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not plan:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        # 检查是否需要重新生成
        regenerate = request.args.get('regenerate', 'false').lower() == 'true'
        
        # 获取工作流状态
        workflow_status = plan.get('workflow_status')
        if workflow_status and isinstance(workflow_status, str):
            try:
                workflow_status = json.loads(workflow_status)
            except:
                workflow_status = {}
        
        report_info = workflow_status.get('report', {}) if workflow_status else {}
        report_status = report_info.get('status', 'not_started')
        
        # 如果报告已生成且不需要重新生成，返回缓存的摘要信息
        if report_status == 'completed' and not regenerate:
            return jsonify({
                'success': True,
                'data': {
                    'report': {
                        'report_id': report_info.get('report_id'),
                        'overall_accuracy': report_info.get('overall_accuracy'),
                        'total_questions': report_info.get('total_questions'),
                        'correct_count': report_info.get('correct_count'),
                        'error_count': report_info.get('error_count'),
                        'generated_at': report_info.get('generated_at')
                    },
                    'status': 'completed'
                }
            })
        
        # 如果需要重新生成或报告未生成，尝试生成完整报告
        eval_status = workflow_status.get('evaluation', {}).get('status') if workflow_status else None
        
        if eval_status != 'completed':
            return jsonify({
                'success': True,
                'data': {
                    'report': None,
                    'status': 'not_started',
                    'message': '批量评估尚未完成'
                }
            })
        
        # 生成完整报告
        result = generate_test_report(plan_id)
        
        if not result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'report': None,
                    'status': 'failed',
                    'message': result.get('error', '生成报告失败')
                }
            })
        
        return jsonify({
            'success': True,
            'data': {
                'report': result['report'],
                'status': 'completed'
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 获取报告失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'获取报告失败: {str(e)}'}), 500


# ========== 一键执行工作流 API ==========

@test_plans_bp.route('/api/test-plans/<plan_id>/execute', methods=['POST'])
def execute_workflow(plan_id):
    """
    一键执行工作流
    
    按顺序执行测试计划的工作流步骤：
    1. 检查数据集配置 (dataset)
    2. 执行作业匹配 (homework_match)
    3. 检查批改状态 (等待批改完成)
    4. 开始批量评估 (evaluation)
    5. 生成测试报告 (report)
    
    该接口是幂等的，多次调用会从当前状态继续执行。
    
    当 auto_execute=true 时，工作流会自动继续执行所有可以进行的步骤，
    直到遇到需要等待的步骤（如等待批改完成、等待评估完成）。
    
    当 auto_execute=false 时，每次调用只执行当前步骤，然后返回状态。
    
    Args:
        plan_id: 测试计划ID
    
    Request Body (可选):
        {
            "auto_execute": true,       # 是否自动执行下一步（覆盖计划设置）
            "force_refresh": false      # 是否强制刷新批改状态
        }
    
    Returns:
        JSON: {
            success: bool,
            data: {
                current_step: str,          # 当前执行的步骤
                completed_steps: list,      # 已完成的步骤列表
                progress_percent: float,    # 总体进度百分比
                next_action: str,           # 下一步操作建议
                can_proceed: bool,          # 是否可以继续自动执行
                step_result: dict,          # 当前步骤的执行结果
                executed_steps: list,       # 本次执行的步骤列表（auto_execute模式）
                workflow_status: dict       # 完整工作流状态
            },
            error: str (if failed)
        }
    """
    from services.test_plan_service import (
        get_workflow_progress,
        match_homework_publish,
        save_matched_publish_ids,
        update_workflow_status,
        check_grading_status,
        create_batch_task_from_plan,
        generate_test_report
    )
    from services.storage_service import StorageService
    
    try:
        if not plan_id:
            return jsonify({'success': False, 'error': '计划ID不能为空'}), 400
        
        # 获取测试计划
        plan = AppDatabaseService.execute_one(
            "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
        )
        if not plan:
            return jsonify({'success': False, 'error': '测试计划不存在'}), 404
        
        # 获取请求参数
        data = request.json or {}
        auto_execute = data.get('auto_execute')
        force_refresh = data.get('force_refresh', False)
        
        # 如果没有指定 auto_execute，使用计划的设置
        if auto_execute is None:
            auto_execute = bool(plan.get('auto_execute', 0))
        
        # 记录本次执行的步骤（用于 auto_execute 模式）
        executed_steps = []
        
        # 获取当前工作流进度
        progress = get_workflow_progress(plan_id)
        if not progress['success']:
            return jsonify({
                'success': False,
                'error': progress.get('error', '获取工作流进度失败')
            }), 500
        
        current_step = progress['current_step']
        workflow_status = progress['workflow_status']
        completed_steps = progress['completed_steps']
        
        # 步骤执行结果
        step_result = {}
        all_step_results = []  # 记录所有执行的步骤结果
        
        # 循环执行步骤（auto_execute 模式下会继续执行）
        while True:
            # ========== 步骤1: 检查数据集配置 ==========
            if current_step == 'dataset':
                dataset_status = workflow_status.get('dataset', {}).get('status', 'not_started')
                
                if dataset_status != 'completed':
                    return jsonify({
                        'success': True,
                        'data': {
                            'current_step': 'dataset',
                            'completed_steps': completed_steps,
                            'progress_percent': progress['progress_percent'],
                            'next_action': '请先选择数据集',
                            'can_proceed': False,
                            'step_result': {
                                'status': 'waiting',
                                'message': '数据集未配置，请先选择数据集'
                            },
                            'executed_steps': executed_steps,
                            'workflow_status': workflow_status
                        }
                    })
                
                # 数据集已配置，继续下一步
                current_step = 'homework_match'
                if not auto_execute:
                    # 非自动执行模式，返回当前状态
                    break
        
            # ========== 步骤2: 执行作业匹配 ==========
            if current_step == 'homework_match':
                match_status = workflow_status.get('homework_match', {}).get('status', 'not_started')
                
                # 如果匹配尚未开始或需要重新匹配
                if match_status == 'not_started':
                    # 获取关键字和匹配类型
                    keyword = plan.get('task_keyword', '')
                    match_type = plan.get('keyword_match_type', 'fuzzy')
                    
                    if not keyword:
                        return jsonify({
                            'success': True,
                            'data': {
                                'current_step': 'homework_match',
                                'completed_steps': completed_steps,
                                'progress_percent': progress['progress_percent'],
                                'next_action': '请配置任务关键字',
                                'can_proceed': False,
                                'step_result': {
                                    'status': 'waiting',
                                    'message': '任务关键字未配置'
                                },
                                'executed_steps': executed_steps,
                                'workflow_status': workflow_status
                            }
                        })
                    
                    # 获取数据集信息用于匹配
                    dataset_info = workflow_status.get('dataset', {})
                    dataset_id = dataset_info.get('dataset_id')
                    book_id = None
                    dataset_pages = None
                    
                    if dataset_id:
                        dataset = AppDatabaseService.get_dataset(dataset_id)
                        if dataset:
                            book_id = dataset.get('book_id')
                            pages = dataset.get('pages')
                            if pages:
                                if isinstance(pages, str):
                                    try:
                                        dataset_pages = json.loads(pages)
                                    except:
                                        dataset_pages = None
                                else:
                                    dataset_pages = pages
                    
                    # 执行匹配
                    match_result = match_homework_publish(
                        keyword=keyword,
                        match_type=match_type,
                        book_id=book_id,
                        dataset_pages=dataset_pages
                    )
                    
                    if not match_result['success']:
                        return jsonify({
                            'success': False,
                            'error': match_result.get('error', '作业匹配失败')
                        }), 500
                    
                    # 保存匹配结果
                    publish_ids = [m['publish_id'] for m in match_result['matches']]
                    save_matched_publish_ids(plan_id, publish_ids)
                    
                    # 更新工作流状态
                    matched_publish_info = []
                    for match in match_result['matches']:
                        matched_publish_info.append({
                            'publish_id': match['publish_id'],
                            'content': match['content'],
                            'total_homework': match['total_homework'],
                            'graded_count': match['graded_count'],
                            'grading_progress': match['grading_progress']
                        })
                    
                    grading_progress = round(
                        match_result['total_graded'] / match_result['total_homework'] * 100, 1
                    ) if match_result['total_homework'] > 0 else 0
                    
                    update_workflow_status(plan_id, 'homework_match', {
                        'status': 'in_progress',
                        'matched_publish': matched_publish_info,
                        'total_homework': match_result['total_homework'],
                        'total_graded': match_result['total_graded'],
                        'grading_progress': grading_progress,
                        'last_checked': datetime.now().isoformat()
                    })
                    
                    step_result = {
                        'step': 'homework_match',
                        'status': 'completed',
                        'message': f'匹配到 {match_result["matched_count"]} 个作业发布',
                        'matched_count': match_result['matched_count'],
                        'total_homework': match_result['total_homework'],
                        'total_graded': match_result['total_graded'],
                        'grading_progress': grading_progress
                    }
                    executed_steps.append('homework_match')
                    all_step_results.append(step_result)
                    
                    # 更新 workflow_status
                    workflow_status['homework_match'] = {
                        'status': 'in_progress',
                        'matched_publish': matched_publish_info,
                        'total_homework': match_result['total_homework'],
                        'total_graded': match_result['total_graded'],
                        'grading_progress': grading_progress,
                        'last_checked': datetime.now().isoformat()
                    }
                    
                    # 重新加载 plan 以获取更新后的 matched_publish_ids
                    plan = AppDatabaseService.execute_one(
                        "SELECT * FROM test_plans WHERE plan_id = %s", (plan_id,)
                    )
                
                # 检查批改进度
                matched_publish_ids = plan.get('matched_publish_ids')
                if matched_publish_ids and isinstance(matched_publish_ids, str):
                    try:
                        matched_publish_ids = json.loads(matched_publish_ids)
                    except:
                        matched_publish_ids = []
                
                if matched_publish_ids:
                    # 刷新批改状态
                    grading_status = check_grading_status(matched_publish_ids)
                    
                    # 更新工作流状态
                    update_workflow_status(plan_id, 'homework_match', {
                        'total_homework': grading_status['total_homework'],
                        'total_graded': grading_status['graded_count'],
                        'grading_progress': grading_status['grading_progress'],
                        'last_checked': datetime.now().isoformat()
                    })
                    
                    workflow_status['homework_match']['total_homework'] = grading_status['total_homework']
                    workflow_status['homework_match']['total_graded'] = grading_status['graded_count']
                    workflow_status['homework_match']['grading_progress'] = grading_status['grading_progress']
                    
                    # 检查是否达到阈值
                    threshold = plan.get('grading_threshold', 100)
                    
                    if grading_status['grading_progress'] >= threshold:
                        # 批改完成，更新状态
                        update_workflow_status(plan_id, 'homework_match', {
                            'status': 'completed'
                        })
                        workflow_status['homework_match']['status'] = 'completed'
                        if 'homework_match' not in completed_steps:
                            completed_steps.append('homework_match')
                        current_step = 'evaluation'
                        
                        step_result = {
                            'step': 'homework_match',
                            'status': 'completed',
                            'message': f'批改进度已达到阈值 ({grading_status["grading_progress"]}% >= {threshold}%)',
                            'grading_progress': grading_status['grading_progress'],
                            'threshold': threshold
                        }
                        
                        if not auto_execute:
                            # 非自动执行模式，返回当前状态
                            break
                        # 自动执行模式，继续下一步
                        continue
                    else:
                        # 批改未完成，需要等待
                        return jsonify({
                            'success': True,
                            'data': {
                                'current_step': 'homework_match',
                                'completed_steps': completed_steps,
                                'progress_percent': len(completed_steps) / 4 * 100,
                                'next_action': f'等待批改完成（当前 {grading_status["grading_progress"]}%，需达到 {threshold}%）',
                                'can_proceed': False,
                                'step_result': {
                                    'status': 'waiting',
                                    'message': '等待批改完成',
                                    'grading_progress': grading_status['grading_progress'],
                                    'threshold': threshold,
                                    'total_homework': grading_status['total_homework'],
                                    'graded_count': grading_status['graded_count']
                                },
                                'executed_steps': executed_steps,
                                'workflow_status': workflow_status
                            }
                        })
        
            # ========== 步骤3: 开始批量评估 ==========
            if current_step == 'evaluation':
                eval_status = workflow_status.get('evaluation', {}).get('status', 'not_started')
                
                if eval_status == 'not_started':
                    # 创建批量评估任务
                    eval_result = create_batch_task_from_plan(plan_id)
                    
                    if not eval_result['success']:
                        return jsonify({
                            'success': False,
                            'error': eval_result.get('error', '创建评估任务失败')
                        }), 500
                    
                    # 更新工作流状态
                    update_workflow_status(plan_id, 'evaluation', {
                        'status': 'in_progress',
                        'task_id': eval_result['task_id'],
                        'task_name': eval_result.get('task_name', ''),
                        'homework_count': eval_result['homework_count'],
                        'matched_count': eval_result.get('matched_count', 0),
                        'accuracy': None,
                        'started_at': datetime.now().isoformat(),
                        'completed_at': None
                    })
                    
                    workflow_status['evaluation'] = {
                        'status': 'in_progress',
                        'task_id': eval_result['task_id'],
                        'task_name': eval_result.get('task_name', ''),
                        'homework_count': eval_result['homework_count'],
                        'matched_count': eval_result.get('matched_count', 0),
                        'accuracy': None,
                        'started_at': datetime.now().isoformat(),
                        'completed_at': None
                    }
                    
                    step_result = {
                        'step': 'evaluation',
                        'status': 'created',
                        'message': f'已创建评估任务: {eval_result["task_id"]}',
                        'task_id': eval_result['task_id'],
                        'task_name': eval_result.get('task_name', ''),
                        'homework_count': eval_result['homework_count']
                    }
                    executed_steps.append('evaluation_created')
                    all_step_results.append(step_result)
                    
                    # 评估任务需要用户手动执行，返回状态
                    return jsonify({
                        'success': True,
                        'data': {
                            'current_step': 'evaluation',
                            'completed_steps': completed_steps,
                            'progress_percent': len(completed_steps) / 4 * 100,
                            'next_action': f'请执行批量评估任务 (任务ID: {eval_result["task_id"]})',
                            'can_proceed': False,
                            'step_result': step_result,
                            'executed_steps': executed_steps,
                            'workflow_status': workflow_status
                        }
                    })
                
                elif eval_status == 'in_progress':
                    # 检查评估任务状态
                    task_id = workflow_status.get('evaluation', {}).get('task_id')
                    
                    if task_id:
                        task_data = StorageService.load_batch_task(task_id)
                        
                        if task_data:
                            task_status = task_data.get('status', 'pending')
                            
                            if task_status == 'completed':
                                # 评估完成，更新状态
                                overall_report = task_data.get('overall_report', {})
                                accuracy = overall_report.get('overall_accuracy') if overall_report else None
                                
                                update_workflow_status(plan_id, 'evaluation', {
                                    'status': 'completed',
                                    'accuracy': accuracy,
                                    'completed_at': datetime.now().isoformat()
                                })
                                
                                workflow_status['evaluation']['status'] = 'completed'
                                workflow_status['evaluation']['accuracy'] = accuracy
                                workflow_status['evaluation']['completed_at'] = datetime.now().isoformat()
                                if 'evaluation' not in completed_steps:
                                    completed_steps.append('evaluation')
                                current_step = 'report'
                                
                                step_result = {
                                    'step': 'evaluation',
                                    'status': 'completed',
                                    'message': f'评估完成，准确率: {accuracy:.2%}' if accuracy else '评估完成',
                                    'accuracy': accuracy
                                }
                                all_step_results.append(step_result)
                                
                                if not auto_execute:
                                    # 非自动执行模式，返回当前状态
                                    break
                                # 自动执行模式，继续下一步
                                continue
                            else:
                                # 评估进行中，需要等待
                                homework_items = task_data.get('homework_items', [])
                                total_count = len(homework_items)
                                completed_count = sum(1 for item in homework_items if item.get('status') == 'completed')
                                eval_progress = round(completed_count / total_count * 100, 1) if total_count > 0 else 0
                                
                                return jsonify({
                                    'success': True,
                                    'data': {
                                        'current_step': 'evaluation',
                                        'completed_steps': completed_steps,
                                        'progress_percent': len(completed_steps) / 4 * 100,
                                        'next_action': f'评估进行中 ({completed_count}/{total_count})',
                                        'can_proceed': False,
                                        'step_result': {
                                            'status': 'in_progress',
                                            'message': '评估进行中',
                                            'task_id': task_id,
                                            'total_count': total_count,
                                            'completed_count': completed_count,
                                            'progress': eval_progress
                                        },
                                        'executed_steps': executed_steps,
                                        'workflow_status': workflow_status
                                    }
                                })
                        else:
                            return jsonify({
                                'success': True,
                                'data': {
                                    'current_step': 'evaluation',
                                    'completed_steps': completed_steps,
                                    'progress_percent': len(completed_steps) / 4 * 100,
                                    'next_action': '评估任务数据不存在，请重新创建',
                                    'can_proceed': False,
                                    'step_result': {
                                        'status': 'error',
                                        'message': '评估任务数据不存在'
                                    },
                                    'executed_steps': executed_steps,
                                    'workflow_status': workflow_status
                                }
                            })
                
                elif eval_status == 'completed':
                    # 评估已完成，继续下一步
                    if 'evaluation' not in completed_steps:
                        completed_steps.append('evaluation')
                    current_step = 'report'
                    if not auto_execute:
                        break
                    continue
        
            # ========== 步骤4: 生成测试报告 ==========
            if current_step == 'report':
                report_status = workflow_status.get('report', {}).get('status', 'not_started')
                
                if report_status == 'not_started':
                    # 生成报告
                    report_result = generate_test_report(plan_id)
                    
                    if not report_result['success']:
                        return jsonify({
                            'success': False,
                            'error': report_result.get('error', '生成报告失败')
                        }), 500
                    
                    report = report_result['report']
                    
                    # 更新工作流状态
                    update_workflow_status(plan_id, 'report', {
                        'status': 'completed',
                        'report_id': report['report_id'],
                        'overall_accuracy': report['overall_accuracy'],
                        'total_questions': report['total_questions'],
                        'correct_count': report['correct_count'],
                        'error_count': report['error_count'],
                        'generated_at': report['generated_at']
                    })
                    
                    workflow_status['report'] = {
                        'status': 'completed',
                        'report_id': report['report_id'],
                        'overall_accuracy': report['overall_accuracy'],
                        'total_questions': report['total_questions'],
                        'correct_count': report['correct_count'],
                        'error_count': report['error_count'],
                        'generated_at': report['generated_at']
                    }
                    if 'report' not in completed_steps:
                        completed_steps.append('report')
                    
                    step_result = {
                        'step': 'report',
                        'status': 'completed',
                        'message': '测试报告已生成',
                        'report_id': report['report_id'],
                        'overall_accuracy': report['overall_accuracy'],
                        'total_questions': report['total_questions']
                    }
                    executed_steps.append('report')
                    all_step_results.append(step_result)
                    
                    current_step = 'completed'
                
                elif report_status == 'completed':
                    # 报告已生成
                    if 'report' not in completed_steps:
                        completed_steps.append('report')
                    current_step = 'completed'
            
            # ========== 工作流完成 ==========
            if current_step == 'completed':
                return jsonify({
                    'success': True,
                    'data': {
                        'current_step': 'completed',
                        'completed_steps': completed_steps,
                        'progress_percent': 100,
                        'next_action': '工作流已完成',
                        'can_proceed': False,
                        'step_result': step_result if step_result else {
                            'status': 'completed',
                            'message': '所有步骤已完成'
                        },
                        'executed_steps': executed_steps,
                        'all_step_results': all_step_results if all_step_results else None,
                        'workflow_status': workflow_status
                    }
                })
            
            # 如果不是自动执行模式，跳出循环
            if not auto_execute:
                break
        
        # 返回当前状态（非自动执行模式下的中间状态）
        return jsonify({
            'success': True,
            'data': {
                'current_step': current_step,
                'completed_steps': completed_steps,
                'progress_percent': len(completed_steps) / 4 * 100,
                'next_action': progress.get('next_action', ''),
                'can_proceed': progress.get('can_proceed', False),
                'step_result': step_result if step_result else None,
                'executed_steps': executed_steps,
                'all_step_results': all_step_results if all_step_results else None,
                'workflow_status': workflow_status
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 执行工作流失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'执行失败: {str(e)}'}), 500


# ========== 合并作业发布到批量评估任务 API ==========

@test_plans_bp.route('/api/test-plans/check-and-merge', methods=['POST'])
def check_and_merge_homework():
    """
    检查作业发布完成状态并合并创建批量评估任务
    
    根据关键字和学科匹配 zp_homework_publish，检查所有匹配的 publish 是否都已完成
    （status=2），如果全部完成则合并所有作业创建一个批量评估任务。
    
    Request Body:
        {
            "keyword": "=",                # 必填，搜索关键字
            "subject_id": 4,               # 必填，学科ID
            "match_type": "fuzzy",         # 可选，匹配类型: exact/fuzzy/regex，默认 fuzzy
            "auto_match_dataset": true,    # 可选，是否自动匹配数据集，默认 true
            "force_create": false          # 可选，是否强制创建（即使未全部完成），默认 false
        }
    
    Returns:
        JSON: {
            success: bool,
            data: {
                status: str,               # checking/waiting/completed
                matched_count: int,        # 匹配到的 publish 数量
                completed_count: int,      # 已完成的 publish 数量
                all_completed: bool,       # 是否全部完成
                total_homework: int,       # 总作业数
                matches: [...],            # 匹配到的 publish 列表
                task_id: str,              # 创建的批量任务ID（仅当 all_completed=true 或 force_create=true）
                task_name: str,            # 任务名称
                message: str               # 状态消息
            },
            error: str (if failed)
        }
    """
    from services.database_service import DatabaseService
    from services.storage_service import StorageService
    import uuid
    
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
    
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        # 获取并验证参数
        keyword = data.get('keyword', '').strip()
        if not keyword:
            return jsonify({'success': False, 'error': '关键字不能为空'}), 400
        
        subject_id = data.get('subject_id')
        if subject_id is None:
            return jsonify({'success': False, 'error': '学科ID不能为空'}), 400
        
        try:
            subject_id = int(subject_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': '学科ID格式错误'}), 400
        
        match_type = data.get('match_type', 'fuzzy')
        if match_type not in ('exact', 'fuzzy', 'regex'):
            match_type = 'fuzzy'
        
        auto_match_dataset = data.get('auto_match_dataset', True)
        force_create = data.get('force_create', False)
        
        # 构建 SQL 查询条件
        if match_type == 'exact':
            content_condition = "hp.content = %s"
            content_param = keyword
        elif match_type == 'regex':
            content_condition = "hp.content REGEXP %s"
            content_param = keyword
        else:
            content_condition = "hp.content LIKE %s"
            content_param = f'%{keyword}%'
        
        # 查询匹配的 publish（包含 status 字段）
        sql = f"""
            SELECT 
                hp.id as publish_id,
                hp.content,
                hp.subject_id,
                hp.book_id,
                hp.page_region,
                hp.status,
                hp.create_time,
                b.book_name,
                COUNT(h.id) as total_homework
            FROM zp_homework_publish hp
            LEFT JOIN zp_homework h ON h.hw_publish_id = hp.id
            LEFT JOIN zp_make_book b ON hp.book_id = b.id
            WHERE {content_condition}
              AND hp.subject_id = %s
            GROUP BY hp.id, hp.content, hp.subject_id, hp.book_id, hp.page_region, hp.status, hp.create_time, b.book_name
            ORDER BY hp.create_time DESC
            LIMIT 100
        """
        
        rows = DatabaseService.execute_query(sql, (content_param, subject_id))
        
        if not rows:
            return jsonify({
                'success': True,
                'data': {
                    'status': 'no_match',
                    'matched_count': 0,
                    'completed_count': 0,
                    'all_completed': False,
                    'total_homework': 0,
                    'matches': [],
                    'message': '未找到匹配的作业发布'
                }
            })
        
        # 处理匹配结果
        matches = []
        total_homework_sum = 0
        completed_count = 0
        publish_ids = []
        
        for row in rows:
            publish_id = str(row.get('publish_id', ''))
            publish_status = row.get('status', 0) or 0
            is_completed = (publish_status == 2)
            total_hw = row.get('total_homework', 0) or 0
            
            if is_completed:
                completed_count += 1
            
            publish_ids.append(publish_id)
            total_homework_sum += total_hw
            
            # 解析页码
            page_region = row.get('page_region', '')
            pages = parse_page_region(page_region)
            
            # 格式化时间
            create_time = row.get('create_time')
            if create_time and hasattr(create_time, 'isoformat'):
                create_time = create_time.isoformat()
            
            matches.append({
                'publish_id': publish_id,
                'content': row.get('content', ''),
                'book_id': str(row.get('book_id', '')),
                'book_name': row.get('book_name', ''),
                'page_region': page_region,
                'pages': pages,
                'total_homework': total_hw,
                'status': publish_status,
                'is_completed': is_completed,
                'create_time': create_time
            })
        
        all_completed = len(matches) > 0 and completed_count == len(matches)
        
        # 如果未全部完成且不强制创建，返回等待状态
        if not all_completed and not force_create:
            return jsonify({
                'success': True,
                'data': {
                    'status': 'waiting',
                    'matched_count': len(matches),
                    'completed_count': completed_count,
                    'all_completed': False,
                    'total_homework': total_homework_sum,
                    'matches': matches,
                    'message': f'等待批改完成：{completed_count}/{len(matches)} 个任务已完成'
                }
            })
        
        # 全部完成或强制创建，开始合并创建批量任务
        # 1. 获取所有作业详细信息
        placeholders = ','.join(['%s'] * len(publish_ids))
        homework_sql = f"""
            SELECT h.id, h.hw_publish_id, h.student_id, h.subject_id, h.page_num, 
                   h.pic_path, h.homework_result, h.data_value,
                   p.content AS homework_name, s.name AS student_name,
                   b.id AS book_id, b.book_name AS book_name, p.page_region
            FROM zp_homework h
            LEFT JOIN zp_homework_publish p ON h.hw_publish_id = p.id
            LEFT JOIN zp_student s ON h.student_id = s.id
            LEFT JOIN zp_make_book b ON p.book_id = b.id
            WHERE h.hw_publish_id IN ({placeholders})
              AND h.homework_result IS NOT NULL 
              AND h.homework_result != '' 
              AND h.homework_result != '[]'
        """
        
        homework_rows = DatabaseService.execute_query(homework_sql, tuple(publish_ids))
        
        if not homework_rows:
            return jsonify({
                'success': False,
                'error': '没有已批改的作业数据'
            }), 400
        
        # 2. 加载数据集用于匹配
        datasets = []
        if auto_match_dataset:
            for fn in StorageService.list_datasets():
                ds = StorageService.load_dataset(fn[:-5])
                if ds:
                    datasets.append(ds)
            datasets.sort(key=lambda ds: ds.get('created_at', ''), reverse=True)
        
        # 3. 构建 homework_items
        homework_items = []
        page_nums = set()
        book_names = set()
        
        for row in homework_rows:
            book_id = str(row.get('book_id', '')) if row.get('book_id') else ''
            page_num = row.get('page_num')
            page_num_int = int(page_num) if page_num is not None else None
            
            if page_num_int:
                page_nums.add(page_num_int)
            if row.get('book_name'):
                book_names.add(row.get('book_name'))
            
            # 自动匹配数据集
            matched_dataset = None
            matched_dataset_name = ''
            
            if auto_match_dataset:
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
                'data_value': row.get('data_value', '[]'),
                'matched_dataset': matched_dataset,
                'matched_dataset_name': matched_dataset_name,
                'status': 'matched' if matched_dataset else 'pending',
                'accuracy': None,
                'evaluation': None
            })
        
        # 4. 生成任务ID和名称
        task_id = str(uuid.uuid4())[:8]
        now = datetime.now()
        subject_name = SUBJECT_MAP.get(subject_id, f'学科{subject_id}')
        
        # 自动生成任务名称: {学科名}_P{页码范围}_自动评估_{日期}
        if page_nums:
            sorted_pages = sorted(page_nums)
            if len(sorted_pages) == 1:
                page_range = f'P{sorted_pages[0]}'
            else:
                page_range = f'P{sorted_pages[0]}-{sorted_pages[-1]}'
        else:
            page_range = ''
        
        task_name = f'{subject_name}_{page_range}_自动评估_{now.strftime("%m%d")}'
        
        # 5. 创建任务数据
        task_data = {
            'task_id': task_id,
            'name': task_name,
            'subject_id': subject_id,
            'subject_name': subject_name,
            'source': 'auto_merge',  # 标记来源为自动合并
            'source_keyword': keyword,
            'source_publish_ids': publish_ids,
            'fuzzy_threshold': 0.85,
            'status': 'pending',
            'homework_items': homework_items,
            'overall_report': None,
            'created_at': now.isoformat()
        }
        
        # 6. 保存任务
        StorageService.save_batch_task(task_id, task_data)
        
        # 7. 创建测试计划并关联任务（存入数据库）
        plan_id = str(uuid.uuid4())[:8]
        try:
            from services.database_service import AppDatabaseService
            import json
            
            plan_sql = """
                INSERT INTO test_plans 
                (plan_id, name, description, subject_ids, target_count, completed_count, 
                 status, task_keyword, keyword_match_type, linked_task_ids, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            plan_params = (
                plan_id,
                task_name,
                f'自动合并创建，关键字: {keyword}',
                json.dumps([subject_id]),  # subject_ids 是 JSON 数组
                len(homework_items),  # target_count
                0,  # completed_count
                'active',  # status - 直接设为进行中
                keyword,  # task_keyword
                match_type,  # keyword_match_type
                json.dumps([task_id]),  # linked_task_ids - 关联批量任务
                now,  # created_at
                now   # updated_at
            )
            AppDatabaseService.execute_update(plan_sql, plan_params)
            print(f"[TestPlans] 已创建测试计划: {plan_id} - {task_name}")
        except Exception as plan_error:
            print(f"[TestPlans] 创建测试计划失败: {plan_error}")
            # 测试计划创建失败不影响批量任务
        
        # 8. 统计匹配情况
        matched_count = sum(1 for item in homework_items if item.get('matched_dataset'))
        
        return jsonify({
            'success': True,
            'data': {
                'status': 'completed',
                'matched_count': len(matches),
                'completed_count': completed_count,
                'all_completed': all_completed,
                'total_homework': len(homework_items),
                'matches': matches,
                'task_id': task_id,
                'task_name': task_name,
                'dataset_matched_count': matched_count,
                'message': f'已创建批量评估任务：{task_name}，包含 {len(homework_items)} 份作业'
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 检查并合并作业失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'操作失败: {str(e)}'}), 500


@test_plans_bp.route('/api/test-plans/poll-completion', methods=['POST'])
def poll_completion_status():
    """
    轮询检查作业发布完成状态
    
    用于前端定时轮询，检查匹配的 publish 是否全部完成。
    
    Request Body:
        {
            "keyword": "=",
            "subject_id": 4,
            "match_type": "fuzzy"
        }
    
    Returns:
        JSON: {
            success: bool,
            data: {
                matched_count: int,
                completed_count: int,
                all_completed: bool,
                progress: float,        # 完成进度百分比
                matches: [
                    {
                        publish_id: str,
                        content: str,
                        is_completed: bool,
                        total_homework: int
                    }
                ]
            }
        }
    """
    from services.database_service import DatabaseService
    
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求数据为空'}), 400
        
        keyword = data.get('keyword', '').strip()
        if not keyword:
            return jsonify({'success': False, 'error': '关键字不能为空'}), 400
        
        subject_id = data.get('subject_id')
        if subject_id is None:
            return jsonify({'success': False, 'error': '学科ID不能为空'}), 400
        
        try:
            subject_id = int(subject_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': '学科ID格式错误'}), 400
        
        match_type = data.get('match_type', 'fuzzy')
        
        # 构建查询条件
        if match_type == 'exact':
            content_condition = "hp.content = %s"
            content_param = keyword
        elif match_type == 'regex':
            content_condition = "hp.content REGEXP %s"
            content_param = keyword
        else:
            content_condition = "hp.content LIKE %s"
            content_param = f'%{keyword}%'
        
        # 查询 publish 状态
        sql = f"""
            SELECT 
                hp.id as publish_id,
                hp.content,
                hp.status,
                COUNT(h.id) as total_homework
            FROM zp_homework_publish hp
            LEFT JOIN zp_homework h ON h.hw_publish_id = hp.id
            WHERE {content_condition}
              AND hp.subject_id = %s
            GROUP BY hp.id, hp.content, hp.status
            ORDER BY hp.create_time DESC
            LIMIT 100
        """
        
        rows = DatabaseService.execute_query(sql, (content_param, subject_id))
        
        matches = []
        completed_count = 0
        
        for row in rows:
            is_completed = (row.get('status', 0) == 2)
            if is_completed:
                completed_count += 1
            
            matches.append({
                'publish_id': str(row.get('publish_id', '')),
                'content': row.get('content', ''),
                'is_completed': is_completed,
                'total_homework': row.get('total_homework', 0) or 0
            })
        
        all_completed = len(matches) > 0 and completed_count == len(matches)
        progress = round(completed_count / len(matches) * 100, 1) if matches else 0
        
        return jsonify({
            'success': True,
            'data': {
                'matched_count': len(matches),
                'completed_count': completed_count,
                'all_completed': all_completed,
                'progress': progress,
                'matches': matches
            }
        })
        
    except Exception as e:
        print(f"[TestPlans] 轮询完成状态失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'查询失败: {str(e)}'}), 500
