"""
测试计划看板路由模块

提供测试计划看板的所有 API 端点，包括：
- 概览统计 (US-2)
- 批量任务列表 (US-3)
- 数据集概览 (US-4)
- 学科评估概览 (US-5)
- 测试计划 CRUD (US-6)
- 数据同步 (US-9)
- 趋势分析 (US-15)

遵循 NFR-34 代码质量标准：
- 所有路由函数包含文档字符串
- 参数校验（空值、类型）
- 异常捕获和友好错误信息
"""
import os
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from services.dashboard_service import DashboardService
from services.database_service import AppDatabaseService

# 创建蓝图
dashboard_bp = Blueprint('dashboard', __name__)


# ========== 基础功能 API (US-1~9) ==========

@dashboard_bp.route('/api/dashboard/overview', methods=['GET'])
def get_overview():
    """
    获取看板概览统计数据 (US-2)
    
    Query Parameters:
        range: 时间范围，可选值 today|week|month，默认 today
        
    Returns:
        JSON: {
            success: bool,
            data: {
                datasets: {total, by_subject},
                tasks: {today, week, month},
                questions: {tested, total},
                accuracy: {current, previous, trend},
                last_sync: string
            }
        }
        
    Example:
        GET /api/dashboard/overview?range=week
    """
    try:
        # 获取时间范围参数
        time_range = request.args.get('range', 'today')
        
        # 参数校验 (NFR-34.6)
        valid_ranges = ['today', 'week', 'month']
        if time_range not in valid_ranges:
            return jsonify({
                'success': False,
                'error': f'无效的时间范围，可选值: {", ".join(valid_ranges)}'
            }), 400
        
        # 调用服务层获取数据
        data = DashboardService.get_overview(time_range)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        # 异常处理 (NFR-34.7)
        print(f"[Dashboard] 获取概览统计失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取概览统计失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/tasks', methods=['GET'])
def get_tasks():
    """
    获取批量任务列表 (US-3)
    
    Query Parameters:
        page: 页码，从1开始，默认1
        page_size: 每页数量，默认20，最大100
        status: 状态筛选，可选值 all|pending|processing|completed|failed，默认 all
        
    Returns:
        JSON: {
            success: bool,
            data: {
                tasks: [{task_id, name, status, accuracy, total_questions, created_at, formatted_time}],
                pagination: {page, page_size, total, total_pages}
            }
        }
        
    Example:
        GET /api/dashboard/tasks?page=1&page_size=20&status=completed
    """
    try:
        # 获取分页参数
        page = request.args.get('page', 1)
        page_size = request.args.get('page_size', 20)
        status = request.args.get('status', 'all')
        
        # 参数类型校验 (NFR-34.6)
        try:
            page = int(page)
            page_size = int(page_size)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'page 和 page_size 必须是整数'
            }), 400
        
        # 参数范围校验
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100
        
        # 状态参数校验
        valid_statuses = ['all', 'pending', 'processing', 'completed', 'failed']
        if status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'无效的状态值，可选值: {", ".join(valid_statuses)}'
            }), 400
        
        # 调用服务层获取数据
        data = DashboardService.get_tasks(page, page_size, status)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取任务列表失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取任务列表失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/datasets', methods=['GET'])
def get_datasets():
    """
    获取数据集概览 (US-4)
    
    包含历史准确率、使用次数、难度标签等信息。
    
    Query Parameters:
        subject_id: 学科ID筛选，可选
        sort_by: 排序字段，可选值 usage|accuracy|created_at，默认 created_at
        order: 排序方向，可选值 asc|desc，默认 desc
        
    Returns:
        JSON: {
            success: bool,
            data: {
                total: int,
                by_subject: {subject_id: count},
                datasets: [{dataset_id, name, subject_id, subject_name, question_count, 
                           pages, page_range, usage_count, last_used, history_accuracy,
                           last_accuracy, difficulty}],
                top_usage: [top 5 datasets by usage]
            }
        }
        
    Example:
        GET /api/dashboard/datasets?subject_id=3&sort_by=accuracy&order=desc
    """
    try:
        # 获取筛选和排序参数
        subject_id = request.args.get('subject_id')
        sort_by = request.args.get('sort_by', 'created_at')
        order = request.args.get('order', 'desc')
        
        # 学科ID类型校验 (NFR-34.6)
        if subject_id is not None and subject_id != '':
            try:
                subject_id = int(subject_id)
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'subject_id 必须是整数'
                }), 400
        else:
            subject_id = None
        
        # 排序字段校验
        valid_sort_fields = ['usage', 'accuracy', 'created_at']
        if sort_by not in valid_sort_fields:
            return jsonify({
                'success': False,
                'error': f'无效的排序字段，可选值: {", ".join(valid_sort_fields)}'
            }), 400
        
        # 排序方向校验
        if order not in ['asc', 'desc']:
            return jsonify({
                'success': False,
                'error': '无效的排序方向，可选值: asc, desc'
            }), 400
        
        # 调用服务层获取数据
        data = DashboardService.get_datasets_overview(subject_id, sort_by, order)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取数据集概览失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取数据集概览失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/subjects', methods=['GET'])
def get_subjects():
    """
    获取学科评估概览 (US-5)
    
    聚合所有批量任务中的作业数据，按学科分组统计准确率和错误类型分布。
    
    Returns:
        JSON: {
            success: bool,
            data: [{
                subject_id: int,
                subject_name: string,
                task_count: int,
                homework_count: int,
                question_count: int,
                correct_count: int,
                accuracy: float,
                warning: bool,  # 准确率低于80%时为true
                error_types: {error_type: count}
            }]
        }
        
    Example:
        GET /api/dashboard/subjects
    """
    try:
        # 调用服务层获取数据
        data = DashboardService.get_subjects_overview()
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取学科评估概览失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取学科评估概览失败，请稍后重试'
        }), 500


# ========== 测试计划 CRUD API (US-6) ==========

@dashboard_bp.route('/api/dashboard/plans', methods=['GET'])
def get_plans():
    """
    获取测试计划列表 (US-6)
    
    Query Parameters:
        status: 状态筛选，可选值 all|draft|active|completed|archived，默认 all
        
    Returns:
        JSON: {
            success: bool,
            data: [{
                plan_id, name, description, subject_ids, target_count,
                completed_count, progress, status, start_date, end_date,
                ai_generated, created_at
            }]
        }
        
    Example:
        GET /api/dashboard/plans?status=active
    """
    try:
        status = request.args.get('status', 'all')
        
        # 状态参数校验
        valid_statuses = ['all', 'draft', 'active', 'completed', 'archived']
        if status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'无效的状态值，可选值: {", ".join(valid_statuses)}'
            }), 400
        
        # 调用服务层获取数据
        data = DashboardService.get_plans(status)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取测试计划列表失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取测试计划列表失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/plans', methods=['POST'])
def create_plan():
    """
    创建测试计划 (US-6.1, US-6.2)
    
    Request Body:
        {
            name: string (必填，最大200字符),
            description: string (可选),
            subject_ids: [int] (可选，目标学科ID列表),
            target_count: int (可选，目标测试数量),
            start_date: string (可选，格式 YYYY-MM-DD),
            end_date: string (可选，格式 YYYY-MM-DD),
            dataset_ids: [string] (可选，关联数据集ID列表)
        }
        
    Returns:
        JSON: {
            success: bool,
            data: {plan_id, name, ...} 或 error: string
        }
        
    Example:
        POST /api/dashboard/plans
        Body: {"name": "物理八上测试计划", "subject_ids": [3], "target_count": 30}
    """
    try:
        # 获取请求数据
        data = request.get_json()
        
        # 参数空值校验 (NFR-34.5)
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据不能为空'
            }), 400
        
        # 名称校验
        name = data.get('name', '').strip() if data.get('name') else ''
        if not name:
            return jsonify({
                'success': False,
                'error': '计划名称不能为空'
            }), 400
        
        if len(name) > 200:
            return jsonify({
                'success': False,
                'error': '计划名称不能超过200字符'
            }), 400
        
        # target_count 类型校验
        if 'target_count' in data and data['target_count'] is not None:
            try:
                data['target_count'] = int(data['target_count'])
                if data['target_count'] < 0:
                    return jsonify({
                        'success': False,
                        'error': '目标测试数量不能为负数'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'target_count 必须是整数'
                }), 400
        
        # 调用服务层创建计划
        result = DashboardService.create_plan(data)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except ValueError as e:
        # 业务校验错误
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        print(f"[Dashboard] 创建测试计划失败: {e}")
        return jsonify({
            'success': False,
            'error': '创建测试计划失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/plans/<plan_id>', methods=['GET'])
def get_plan(plan_id):
    """
    获取测试计划详情 (US-6, US-6.8)
    
    包含关联的数据集列表和任务列表。
    
    Path Parameters:
        plan_id: 计划ID
        
    Returns:
        JSON: {
            success: bool,
            data: {
                plan_id, name, description, subject_ids, target_count,
                completed_count, progress, status, start_date, end_date,
                schedule_config, ai_generated, assignee_id, created_at, updated_at,
                datasets: [{dataset_id, name, book_name, subject_id, subject_name, question_count}],
                tasks: [{task_id, name, status, accuracy, created_at}]
            }
        }
        
    Example:
        GET /api/dashboard/plans/abc12345
    """
    try:
        # 参数空值校验 (NFR-34.5)
        if not plan_id:
            return jsonify({
                'success': False,
                'error': '计划ID不能为空'
            }), 400
        
        # 调用服务层获取数据
        data = DashboardService.get_plan(plan_id)
        
        if not data:
            return jsonify({
                'success': False,
                'error': '计划不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取测试计划详情失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取测试计划详情失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/plans/<plan_id>', methods=['PUT'])
def update_plan(plan_id):
    """
    更新测试计划 (US-6.4)
    
    Path Parameters:
        plan_id: 计划ID
        
    Request Body:
        {
            name: string (可选),
            description: string (可选),
            subject_ids: [int] (可选),
            target_count: int (可选),
            status: string (可选，draft|active|completed|archived),
            start_date: string (可选),
            end_date: string (可选),
            dataset_ids: [string] (可选)
        }
        
    Returns:
        JSON: {
            success: bool,
            data: {更新后的计划数据} 或 error: string
        }
        
    Example:
        PUT /api/dashboard/plans/abc12345
        Body: {"name": "更新后的名称", "status": "active"}
    """
    try:
        # 参数空值校验 (NFR-34.5)
        if not plan_id:
            return jsonify({
                'success': False,
                'error': '计划ID不能为空'
            }), 400
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据不能为空'
            }), 400
        
        # 名称校验（如果提供）
        if 'name' in data:
            name = data.get('name', '').strip() if data.get('name') else ''
            if not name:
                return jsonify({
                    'success': False,
                    'error': '计划名称不能为空'
                }), 400
            if len(name) > 200:
                return jsonify({
                    'success': False,
                    'error': '计划名称不能超过200字符'
                }), 400
            data['name'] = name
        
        # 状态校验（如果提供）
        if 'status' in data:
            valid_statuses = ['draft', 'active', 'completed', 'archived']
            if data['status'] not in valid_statuses:
                return jsonify({
                    'success': False,
                    'error': f'无效的状态值，可选值: {", ".join(valid_statuses)}'
                }), 400
        
        # target_count 类型校验（如果提供）
        if 'target_count' in data and data['target_count'] is not None:
            try:
                data['target_count'] = int(data['target_count'])
                if data['target_count'] < 0:
                    return jsonify({
                        'success': False,
                        'error': '目标测试数量不能为负数'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'target_count 必须是整数'
                }), 400
        
        # 调用服务层更新计划
        result = DashboardService.update_plan(plan_id, data)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        print(f"[Dashboard] 更新测试计划失败: {e}")
        return jsonify({
            'success': False,
            'error': '更新测试计划失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/plans/<plan_id>', methods=['DELETE'])
def delete_plan(plan_id):
    """
    删除测试计划 (US-6.5)
    
    同时删除关联的数据集关系和任务关系。
    
    Path Parameters:
        plan_id: 计划ID
        
    Returns:
        JSON: {
            success: bool,
            message: string 或 error: string
        }
        
    Example:
        DELETE /api/dashboard/plans/abc12345
    """
    try:
        # 参数空值校验 (NFR-34.5)
        if not plan_id:
            return jsonify({
                'success': False,
                'error': '计划ID不能为空'
            }), 400
        
        # 调用服务层删除计划
        success = DashboardService.delete_plan(plan_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '计划删除成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '计划不存在或删除失败'
            }), 404
        
    except Exception as e:
        print(f"[Dashboard] 删除测试计划失败: {e}")
        return jsonify({
            'success': False,
            'error': '删除测试计划失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/plans/<plan_id>/start', methods=['POST'])
def start_plan(plan_id):
    """
    启动测试计划
    
    将计划状态从 draft 改为 active，开始执行评估流程。
    
    Path Parameters:
        plan_id: 计划ID
        
    Returns:
        JSON: {
            success: bool,
            data: { plan_id, status, message } 或 error: string
        }
        
    Example:
        POST /api/dashboard/plans/abc12345/start
    """
    try:
        # 参数空值校验
        if not plan_id:
            return jsonify({
                'success': False,
                'error': '计划ID不能为空'
            }), 400
        
        # 调用服务层启动计划
        result = DashboardService.start_plan(plan_id)
        
        if result:
            return jsonify({
                'success': True,
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'error': '计划不存在或无法启动'
            }), 404
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        print(f"[Dashboard] 启动测试计划失败: {e}")
        return jsonify({
            'success': False,
            'error': '启动测试计划失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/plans/<plan_id>/clone', methods=['POST'])
def clone_plan(plan_id):
    """
    克隆测试计划 (US-6.6)
    
    复制所有字段，名称加"(副本)"后缀。
    
    Path Parameters:
        plan_id: 要克隆的计划ID
        
    Returns:
        JSON: {
            success: bool,
            data: {新创建的计划数据} 或 error: string
        }
        
    Example:
        POST /api/dashboard/plans/abc12345/clone
    """
    try:
        # 参数空值校验 (NFR-34.5)
        if not plan_id:
            return jsonify({
                'success': False,
                'error': '计划ID不能为空'
            }), 400
        
        # 调用服务层克隆计划
        result = DashboardService.clone_plan(plan_id)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        print(f"[Dashboard] 克隆测试计划失败: {e}")
        return jsonify({
            'success': False,
            'error': '克隆测试计划失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/plans/<plan_id>/tasks', methods=['POST'])
def link_task_to_plan(plan_id):
    """
    关联批量任务到测试计划 (US-6.10)
    
    Path Parameters:
        plan_id: 计划ID
        
    Request Body:
        {
            task_id: string (必填，批量任务ID)
        }
        
    Returns:
        JSON: {
            success: bool,
            message: string 或 error: string
        }
        
    Example:
        POST /api/dashboard/plans/abc12345/tasks
        Body: {"task_id": "xyz67890"}
    """
    try:
        # 参数空值校验 (NFR-34.5)
        if not plan_id:
            return jsonify({
                'success': False,
                'error': '计划ID不能为空'
            }), 400
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据不能为空'
            }), 400
        
        task_id = data.get('task_id', '').strip() if data.get('task_id') else ''
        if not task_id:
            return jsonify({
                'success': False,
                'error': '任务ID不能为空'
            }), 400
        
        # 调用服务层关联任务
        success = DashboardService.link_task_to_plan(plan_id, task_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '任务关联成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '任务关联失败'
            }), 400
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        print(f"[Dashboard] 关联任务到计划失败: {e}")
        return jsonify({
            'success': False,
            'error': '关联任务失败，请稍后重试'
        }), 500


# ========== 数据同步 API (US-9) ==========

@dashboard_bp.route('/api/dashboard/sync', methods=['POST'])
def sync_data():
    """
    手动刷新数据 (US-9)
    
    清除所有缓存，重新加载数据。
    
    Returns:
        JSON: {
            success: bool,
            data: {
                synced_tasks: int,  # 同步的任务数
                synced_at: string   # 同步时间
            }
        }
        
    Example:
        POST /api/dashboard/sync
    """
    try:
        # 调用服务层同步数据
        result = DashboardService.sync_data()
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        print(f"[Dashboard] 数据同步失败: {e}")
        return jsonify({
            'success': False,
            'error': '数据同步失败，请稍后重试'
        }), 500


# ========== 辅助 API ==========

@dashboard_bp.route('/api/dashboard/datasets/<dataset_id>/history', methods=['GET'])
def get_dataset_history(dataset_id):
    """
    获取数据集的历史测试记录 (US-4.8)
    
    用于鼠标悬停时显示历史测试摘要。
    
    Path Parameters:
        dataset_id: 数据集ID
        
    Query Parameters:
        limit: 返回记录数，默认5，最大20
        
    Returns:
        JSON: {
            success: bool,
            data: [{
                task_id: string,
                task_name: string,
                accuracy: float,
                created_at: string
            }]
        }
        
    Example:
        GET /api/dashboard/datasets/abc12345/history?limit=5
    """
    try:
        # 参数空值校验 (NFR-34.5)
        if not dataset_id:
            return jsonify({
                'success': False,
                'error': '数据集ID不能为空'
            }), 400
        
        # 获取 limit 参数
        limit = request.args.get('limit', 5)
        try:
            limit = int(limit)
            if limit < 1:
                limit = 5
            if limit > 20:
                limit = 20
        except (ValueError, TypeError):
            limit = 5
        
        # 调用服务层获取数据
        data = DashboardService.get_dataset_history_tests(dataset_id, limit)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取数据集历史测试记录失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取历史测试记录失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/cache/status', methods=['GET'])
def get_cache_status():
    """
    获取缓存状态 (US-29.5)
    
    返回当前缓存的状态信息。
    
    Returns:
        JSON: {
            success: bool,
            data: {
                total_keys: int,
                keys: [{key, cached_at, expires_at, is_expired}]
            }
        }
        
    Example:
        GET /api/dashboard/cache/status
    """
    try:
        data = DashboardService.get_cache_status()
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取缓存状态失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取缓存状态失败'
        }), 500


@dashboard_bp.route('/api/dashboard/cache/clear', methods=['POST'])
def clear_cache():
    """
    清除缓存 (US-29.3)
    
    清除指定键的缓存，或清除所有缓存。
    
    Request Body (可选):
        {
            key: string (可选，要清除的缓存键名，不提供则清除所有)
        }
        
    Returns:
        JSON: {
            success: bool,
            message: string
        }
        
    Example:
        POST /api/dashboard/cache/clear
        Body: {"key": "overview_today"}  # 或不提供 body 清除所有
    """
    try:
        data = request.get_json() or {}
        key = data.get('key')
        
        DashboardService.clear_cache(key)
        
        if key:
            message = f'缓存 "{key}" 已清除'
        else:
            message = '所有缓存已清除'
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        print(f"[Dashboard] 清除缓存失败: {e}")
        return jsonify({
            'success': False,
            'error': '清除缓存失败'
        }), 500


# ========== AI生成测试计划 API (US-7) ==========

@dashboard_bp.route('/api/dashboard/ai-plan', methods=['POST'])
def generate_ai_plan():
    """
    AI生成测试计划 (US-7)
    
    根据选定的数据集，使用 DeepSeek V3.2 模型分析数据集内容，
    自动生成测试计划建议。
    
    Request Body:
        {
            dataset_ids: [string] (必填，数据集ID列表，支持多选),
            sample_count: int (可选，测试样本数量，默认30，范围1-100),
            subject_id: int (可选，学科ID，用于生成更精准的计划)
        }
        
    Returns:
        JSON: {
            success: bool,
            data: {
                name: string,           # 计划名称
                description: string,    # 计划描述
                objectives: [string],   # 测试目标列表（3-5条）
                steps: [string],        # 测试步骤列表
                expected_duration: string,  # 预期时长
                acceptance_criteria: [string]  # 验收标准列表
            }
        }
        
    Example:
        POST /api/dashboard/ai-plan
        Body: {
            "dataset_ids": ["b3b0395e", "xxx"],
            "sample_count": 30,
            "subject_id": 3
        }
        
    Error Codes:
        400: 参数校验失败（缺少必填参数、参数类型错误）
        500: AI调用失败或服务器内部错误
    """
    try:
        # 获取请求数据
        data = request.get_json()
        
        # 参数空值校验 (NFR-34.5)
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据不能为空'
            }), 400
        
        # dataset_ids 校验
        dataset_ids = data.get('dataset_ids', [])
        if not dataset_ids:
            return jsonify({
                'success': False,
                'error': '请至少选择一个数据集'
            }), 400
        
        if not isinstance(dataset_ids, list):
            return jsonify({
                'success': False,
                'error': 'dataset_ids 必须是数组'
            }), 400
        
        # 过滤空值
        dataset_ids = [d for d in dataset_ids if d and str(d).strip()]
        if not dataset_ids:
            return jsonify({
                'success': False,
                'error': '请至少选择一个有效的数据集'
            }), 400
        
        # sample_count 校验 (NFR-34.6)
        sample_count = data.get('sample_count', 30)
        try:
            sample_count = int(sample_count)
            if sample_count < 1:
                sample_count = 30
            if sample_count > 100:
                sample_count = 100
        except (ValueError, TypeError):
            sample_count = 30
        
        # subject_id 校验
        subject_id = data.get('subject_id')
        if subject_id is not None and subject_id != '':
            try:
                subject_id = int(subject_id)
                # 验证学科ID有效性
                if subject_id < 0 or subject_id > 6:
                    subject_id = None
            except (ValueError, TypeError):
                subject_id = None
        else:
            subject_id = None
        
        # 调用服务层生成计划
        result = DashboardService.generate_ai_plan(
            dataset_ids=dataset_ids,
            sample_count=sample_count,
            subject_id=subject_id
        )
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except ValueError as e:
        # 业务校验错误
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        # 异常处理 (NFR-34.7)
        print(f"[Dashboard] AI生成测试计划失败: {e}")
        return jsonify({
            'success': False,
            'error': f'生成测试计划失败: {str(e)}'
        }), 500


# ========== 自动化调度 API (US-10) ==========

@dashboard_bp.route('/api/dashboard/plans/<plan_id>/schedule', methods=['PUT'])
def set_plan_schedule(plan_id):
    """
    设置计划调度配置 (US-10, 7.2.1)
    
    为指定的测试计划配置自动执行调度。支持三种调度类型：
    - daily: 每天固定时间执行
    - weekly: 每周固定日期时间执行
    - cron: 自定义 cron 表达式
    
    Path Parameters:
        plan_id: 计划ID
        
    Request Body:
        {
            type: string (必填，调度类型: daily|weekly|cron),
            time: string (必填，执行时间，格式 HH:MM，如 "09:00"),
            day_of_week: int (可选，星期几 0-6，0=周一，仅 weekly 类型需要),
            cron: string (可选，cron 表达式，仅 cron 类型需要),
            enabled: bool (可选，是否启用调度，默认 true)
        }
        
    Returns:
        JSON: {
            success: bool,
            data: {
                next_run: string,  # 下次执行时间 ISO 格式
                enabled: bool      # 是否已启用
            }
        }
        
    Example:
        PUT /api/dashboard/plans/abc12345/schedule
        Body: {
            "type": "daily",
            "time": "09:00",
            "enabled": true
        }
        
    Error Codes:
        400: 参数校验失败
        404: 计划不存在
        500: 服务器内部错误
    """
    # 延迟导入避免循环依赖
    from services.unified_schedule_service import UnifiedScheduleService
    
    try:
        # 参数空值校验 (NFR-34.5)
        if not plan_id:
            return jsonify({
                'success': False,
                'error': '计划ID不能为空'
            }), 400
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据不能为空'
            }), 400
        
        # 调度类型校验 (NFR-34.6)
        schedule_type = data.get('type', 'daily')
        if schedule_type not in ['daily', 'weekly', 'cron']:
            return jsonify({
                'success': False,
                'error': f'无效的调度类型: {schedule_type}，可选值: daily, weekly, cron'
            }), 400
        
        # 时间格式校验
        time_str = data.get('time', '09:00')
        try:
            hour, minute = map(int, time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError()
        except:
            return jsonify({
                'success': False,
                'error': f'无效的时间格式: {time_str}，应为 HH:MM 格式'
            }), 400
        
        # weekly 类型需要 day_of_week
        if schedule_type == 'weekly':
            day_of_week = data.get('day_of_week')
            if day_of_week is None:
                return jsonify({
                    'success': False,
                    'error': 'weekly 类型需要提供 day_of_week 参数'
                }), 400
            try:
                day_of_week = int(day_of_week)
                if not (0 <= day_of_week <= 6):
                    raise ValueError()
            except:
                return jsonify({
                    'success': False,
                    'error': 'day_of_week 必须是 0-6 之间的整数（0=周一）'
                }), 400
        
        # cron 类型需要 cron 表达式
        if schedule_type == 'cron':
            cron_expr = data.get('cron', '')
            if not cron_expr:
                return jsonify({
                    'success': False,
                    'error': 'cron 类型需要提供 cron 表达式'
                }), 400
        
        # 调用服务层设置调度
        result = UnifiedScheduleService.set_plan_schedule(plan_id, data)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        print(f"[Dashboard] 设置计划调度失败: {e}")
        return jsonify({
            'success': False,
            'error': '设置调度失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/plans/<plan_id>/schedule', methods=['GET'])
def get_plan_schedule(plan_id):
    """
    获取计划调度配置
    
    Path Parameters:
        plan_id: 计划ID
        
    Returns:
        JSON: {
            success: bool,
            data: {
                plan_id: string,
                has_schedule: bool,
                enabled: bool,
                config: {type, time, day_of_week, cron},
                next_run: string,
                job_active: bool
            }
        }
        
    Example:
        GET /api/dashboard/plans/abc12345/schedule
    """
    from services.unified_schedule_service import UnifiedScheduleService
    
    try:
        # 参数空值校验 (NFR-34.5)
        if not plan_id:
            return jsonify({
                'success': False,
                'error': '计划ID不能为空'
            }), 400
        
        # 获取调度状态
        data = UnifiedScheduleService.get_schedule_status(plan_id)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取计划调度配置失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取调度配置失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/plans/<plan_id>/schedule', methods=['DELETE'])
def disable_plan_schedule(plan_id):
    """
    禁用计划调度
    
    Path Parameters:
        plan_id: 计划ID
        
    Returns:
        JSON: {
            success: bool,
            message: string
        }
        
    Example:
        DELETE /api/dashboard/plans/abc12345/schedule
    """
    from services.unified_schedule_service import UnifiedScheduleService
    
    try:
        # 参数空值校验 (NFR-34.5)
        if not plan_id:
            return jsonify({
                'success': False,
                'error': '计划ID不能为空'
            }), 400
        
        # 禁用调度
        success = UnifiedScheduleService.disable_schedule(plan_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': '调度已禁用'
            })
        else:
            return jsonify({
                'success': False,
                'error': '禁用调度失败'
            }), 500
        
    except Exception as e:
        print(f"[Dashboard] 禁用计划调度失败: {e}")
        return jsonify({
            'success': False,
            'error': '禁用调度失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/plans/<plan_id>/logs', methods=['GET'])
def get_plan_logs(plan_id):
    """
    获取计划执行日志 (US-10, 7.2.2)
    
    获取测试计划的调度执行历史记录。
    
    Path Parameters:
        plan_id: 计划ID
        
    Query Parameters:
        page: 页码，从1开始，默认1
        page_size: 每页数量，默认20，最大100
        
    Returns:
        JSON: {
            success: bool,
            data: {
                logs: [{
                    log_id: string,
                    plan_id: string,
                    task_id: string,
                    action: string,
                    details: object,
                    created_at: string
                }],
                pagination: {
                    page: int,
                    page_size: int,
                    total: int,
                    total_pages: int
                }
            }
        }
        
    Example:
        GET /api/dashboard/plans/abc12345/logs?page=1&page_size=20
    """
    from services.unified_schedule_service import UnifiedScheduleService
    
    try:
        # 参数空值校验 (NFR-34.5)
        if not plan_id:
            return jsonify({
                'success': False,
                'error': '计划ID不能为空'
            }), 400
        
        # 获取分页参数
        page = request.args.get('page', 1)
        page_size = request.args.get('page_size', 20)
        
        # 参数类型校验 (NFR-34.6)
        try:
            page = int(page)
            page_size = int(page_size)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'page 和 page_size 必须是整数'
            }), 400
        
        # 参数范围校验
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100
        
        # 获取执行日志
        data = UnifiedScheduleService.get_plan_logs(plan_id, page, page_size)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取计划执行日志失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取执行日志失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/plans/<plan_id>/execute', methods=['POST'])
def execute_plan_manually(plan_id):
    """
    手动执行测试计划
    
    立即触发测试计划的执行，不等待调度时间。
    
    Path Parameters:
        plan_id: 计划ID
        
    Returns:
        JSON: {
            success: bool,
            data: {
                plan_id: string,
                task_id: string,
                status: string,
                message: string,
                executed_at: string
            }
        }
        
    Example:
        POST /api/dashboard/plans/abc12345/execute
    """
    from services.unified_schedule_service import UnifiedScheduleService as ScheduleService
    
    try:
        # 参数空值校验 (NFR-34.5)
        if not plan_id:
            return jsonify({
                'success': False,
                'error': '计划ID不能为空'
            }), 400
        
        # 执行任务
        result = ScheduleService.execute_test_plan(plan_id)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        print(f"[Dashboard] 手动执行计划失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'执行失败: {str(e)}'
        }), 500


# ========== 问题热点图 API (US-11) ==========

@dashboard_bp.route('/api/dashboard/heatmap', methods=['GET'])
def get_heatmap():
    """
    获取问题热点图数据 (US-11)
    
    按 book -> page -> question 三级聚合错误数据，
    用于可视化展示错误分布热点。
    
    Query Parameters:
        subject_id: 学科ID筛选，可选，不传表示全部学科
        days: 时间范围，可选值 7|30|0(全部)，默认 7
        
    Returns:
        JSON: {
            success: bool,
            data: {
                heatmap: [
                    {
                        book_id: string,
                        book_name: string,
                        subject_id: int,
                        subject_name: string,
                        error_count: int,
                        pages: [
                            {
                                page_num: int,
                                error_count: int,
                                questions: [
                                    {
                                        index: string,
                                        error_count: int,
                                        heat_level: string (critical|high|medium|low),
                                        error_types: {error_type: count}
                                    }
                                ]
                            }
                        ]
                    }
                ],
                total_errors: int,
                time_range: string
            }
        }
        
    Heat Level Colors (US-11.2):
        - critical (>=10 errors): #d73a49 (red)
        - high (5-9 errors): #e65100 (orange)
        - medium (2-4 errors): #f9a825 (yellow)
        - low (1 error): #4caf50 (green)
        
    Example:
        GET /api/dashboard/heatmap?subject_id=3&days=7
    """
    # 延迟导入避免循环依赖
    from services.analysis_service import AnalysisService
    
    try:
        # 获取筛选参数
        subject_id = request.args.get('subject_id')
        days = request.args.get('days', '7')
        
        # 学科ID类型校验 (NFR-34.6)
        if subject_id is not None and subject_id != '':
            try:
                subject_id = int(subject_id)
                # 验证学科ID有效性 (0-6)
                if subject_id < 0 or subject_id > 6:
                    return jsonify({
                        'success': False,
                        'error': f'无效的学科ID: {subject_id}，有效范围: 0-6'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'subject_id 必须是整数'
                }), 400
        else:
            subject_id = None
        
        # 天数参数校验 (NFR-34.6)
        try:
            days = int(days)
            # 支持 7, 30, 0(全部)
            if days not in [7, 30, 0]:
                # 允许其他正整数，但给出提示
                if days < 0:
                    days = 7
        except (ValueError, TypeError):
            days = 7
        
        # 调用服务层获取热点图数据
        data = AnalysisService.get_heatmap(subject_id, days)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        # 异常处理 (NFR-34.7)
        print(f"[Dashboard] 获取热点图数据失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取热点图数据失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/heatmap/details', methods=['GET'])
def get_heatmap_details():
    """
    获取热点图题目错误详情 (US-11.3)
    
    点击热点时显示具体错误列表。
    
    Query Parameters:
        book_id: 书本ID (必填)
        page_num: 页码 (必填)
        question_index: 题号 (必填)
        days: 时间范围，默认 7
        
    Returns:
        JSON: {
            success: bool,
            data: {
                errors: [
                    {
                        task_id: string,
                        task_name: string,
                        homework_id: string,
                        student_name: string,
                        error_type: string,
                        base_answer: string,
                        base_user: string,
                        hw_user: string,
                        created_at: string
                    }
                ],
                total: int
            }
        }
        
    Example:
        GET /api/dashboard/heatmap/details?book_id=xxx&page_num=76&question_index=1&days=7
    """
    from services.analysis_service import AnalysisService
    
    try:
        # 获取参数
        book_id = request.args.get('book_id', '')
        page_num = request.args.get('page_num', '')
        question_index = request.args.get('question_index', '')
        days = request.args.get('days', '7')
        
        # 参数空值校验 (NFR-34.5)
        if not book_id:
            return jsonify({
                'success': False,
                'error': 'book_id 不能为空'
            }), 400
        
        if not page_num:
            return jsonify({
                'success': False,
                'error': 'page_num 不能为空'
            }), 400
        
        if not question_index:
            return jsonify({
                'success': False,
                'error': 'question_index 不能为空'
            }), 400
        
        # 页码类型校验 (NFR-34.6)
        try:
            page_num = int(page_num)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'page_num 必须是整数'
            }), 400
        
        # 天数参数校验
        try:
            days = int(days)
            if days < 0:
                days = 7
        except (ValueError, TypeError):
            days = 7
        
        # 调用服务层获取错误详情
        data = AnalysisService.get_question_error_details(
            book_id=book_id,
            page_num=page_num,
            question_index=question_index,
            days=days
        )
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取热点图错误详情失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取错误详情失败，请稍后重试'
        }), 500



# ========== 日报 API (US-14) ==========

@dashboard_bp.route('/api/dashboard/daily-report', methods=['POST'])
def generate_daily_report():
    """
    生成测试日报 (US-14, 9.2.1)
    
    生成指定日期的测试日报，包含任务完成情况、准确率变化、
    错误分析、AI总结等内容。
    
    Request Body:
        {
            date: string (可选，日期格式 YYYY-MM-DD，默认今天)
        }
        
    Returns:
        JSON: {
            success: bool,
            data: {
                report_id: string,
                report_date: string,
                task_completed: int,
                task_planned: int,
                accuracy: float,
                accuracy_change: float,
                accuracy_week_change: float,
                top_errors: [{type, count}],
                new_error_types: [string],
                high_freq_errors: [{index, count, book_name}],
                tomorrow_plan: [{plan_id, name, remaining}],
                anomalies: [{type, severity, message}],
                model_version: string,
                ai_summary: string,
                raw_content: string
            }
        }
        
    Example:
        POST /api/dashboard/daily-report
        Body: {"date": "2026-01-23"}
        
    Error Codes:
        400: 日期格式错误
        500: 生成失败
    """
    # 延迟导入避免循环依赖
    from services.report_service import ReportService
    
    try:
        # 获取请求数据
        data = request.get_json() or {}
        date = data.get('date')
        
        # 日期格式校验 (NFR-34.6)
        if date:
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'无效的日期格式: {date}，应为 YYYY-MM-DD'
                }), 400
        
        # 调用服务层生成日报
        result = ReportService.generate_daily_report(
            date=date,
            generated_by='manual'
        )
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        print(f"[Dashboard] 生成日报失败: {e}")
        return jsonify({
            'success': False,
            'error': '生成日报失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/daily-reports', methods=['GET'])
def get_daily_reports():
    """
    获取历史日报列表 (US-14, 9.2.2)
    
    分页查询历史日报，按日期倒序排列。
    
    Query Parameters:
        page: 页码，从1开始，默认1
        page_size: 每页数量，默认30，最大100
        
    Returns:
        JSON: {
            success: bool,
            data: {
                reports: [{
                    report_id: string,
                    report_date: string,
                    task_completed: int,
                    task_planned: int,
                    accuracy: float,
                    accuracy_change: float,
                    generated_by: string,
                    created_at: string
                }],
                pagination: {
                    page: int,
                    page_size: int,
                    total: int,
                    total_pages: int
                }
            }
        }
        
    Example:
        GET /api/dashboard/daily-reports?page=1&page_size=30
    """
    from services.report_service import ReportService
    
    try:
        # 获取分页参数
        page = request.args.get('page', 1)
        page_size = request.args.get('page_size', 30)
        
        # 参数类型校验 (NFR-34.6)
        try:
            page = int(page)
            page_size = int(page_size)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'page 和 page_size 必须是整数'
            }), 400
        
        # 参数范围校验
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 30
        if page_size > 100:
            page_size = 100
        
        # 调用服务层获取历史日报
        data = ReportService.get_report_history(page, page_size)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取历史日报列表失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取历史日报列表失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/daily-report/<report_id>', methods=['GET'])
def get_daily_report(report_id):
    """
    获取日报详情
    
    Path Parameters:
        report_id: 日报ID
        
    Returns:
        JSON: {
            success: bool,
            data: {完整日报数据}
        }
        
    Example:
        GET /api/dashboard/daily-report/abc12345
    """
    from services.report_service import ReportService
    
    try:
        # 参数空值校验 (NFR-34.5)
        if not report_id:
            return jsonify({
                'success': False,
                'error': '日报ID不能为空'
            }), 400
        
        # 获取日报详情
        report = ReportService._get_report_by_id(report_id)
        
        if not report:
            return jsonify({
                'success': False,
                'error': '日报不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'data': report
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取日报详情失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取日报详情失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/daily-report/<report_id>/export', methods=['GET'])
def export_daily_report(report_id):
    """
    导出日报 (US-14, 9.2.3)
    
    将日报导出为 Word 文档。
    
    Path Parameters:
        report_id: 日报ID
        
    Query Parameters:
        format: 导出格式，目前仅支持 docx，默认 docx
        
    Returns:
        文件下载响应
        
    Example:
        GET /api/dashboard/daily-report/abc12345/export?format=docx
        
    Error Codes:
        400: 格式不支持
        404: 日报不存在
        500: 导出失败
    """
    from flask import send_file
    from services.report_service import ReportService
    
    try:
        # 参数空值校验 (NFR-34.5)
        if not report_id:
            return jsonify({
                'success': False,
                'error': '日报ID不能为空'
            }), 400
        
        # 获取导出格式
        export_format = request.args.get('format', 'docx')
        
        # 格式校验 (NFR-34.6)
        if export_format not in ['docx']:
            return jsonify({
                'success': False,
                'error': f'不支持的导出格式: {export_format}，目前仅支持 docx'
            }), 400
        
        # 调用服务层导出
        filepath = ReportService.export_report(report_id, export_format)
        
        # 返回文件下载
        return send_file(
            filepath,
            as_attachment=True,
            download_name=os.path.basename(filepath)
        )
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        print(f"[Dashboard] 导出日报失败: {e}")
        return jsonify({
            'success': False,
            'error': '导出日报失败，请稍后重试'
        }), 500


# ========== 趋势分析 API (US-15) ==========

@dashboard_bp.route('/api/dashboard/trends', methods=['GET'])
def get_trends():
    """
    获取趋势分析数据 (US-15, 10.2.1)
    
    从 daily_statistics 表获取历史统计数据，
    用于绘制趋势折线图。
    
    Query Parameters:
        days: 时间范围，可选值 7|30|90，默认 7
        subject_id: 学科ID筛选，可选，不传表示整体
        
    Returns:
        JSON: {
            success: bool,
            data: {
                trends: [
                    {
                        date: string,
                        accuracy: float,
                        task_count: int,
                        question_count: int
                    }
                ],
                by_subject: {
                    subject_id: [
                        {date: string, accuracy: float}
                    ]
                },
                milestones: [
                    {
                        milestone_id: string,
                        date: string,
                        name: string,
                        description: string,
                        type: string
                    }
                ]
            }
        }
        
    Example:
        GET /api/dashboard/trends?days=30&subject_id=3
    """
    try:
        # 获取参数
        days = request.args.get('days', '7')
        subject_id = request.args.get('subject_id')
        
        # 天数参数校验 (NFR-34.6)
        try:
            days = int(days)
            if days not in [7, 30, 90]:
                # 允许其他正整数，但限制范围
                if days < 1:
                    days = 7
                if days > 365:
                    days = 365
        except (ValueError, TypeError):
            days = 7
        
        # 学科ID类型校验 (NFR-34.6)
        if subject_id is not None and subject_id != '':
            try:
                subject_id = int(subject_id)
                if subject_id < 0 or subject_id > 6:
                    return jsonify({
                        'success': False,
                        'error': f'无效的学科ID: {subject_id}，有效范围: 0-6'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'subject_id 必须是整数'
                }), 400
        else:
            subject_id = None
        
        # 调用服务层获取趋势数据
        data = DashboardService.get_trends(days, subject_id)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取趋势数据失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取趋势数据失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/trends/export', methods=['GET'])
def export_trends():
    """
    导出趋势数据为 CSV (US-15, 10.2.3)
    
    Query Parameters:
        days: 时间范围，默认 30
        subject_id: 学科ID筛选，可选
        format: 导出格式，目前仅支持 csv，默认 csv
        
    Returns:
        文件下载响应
        
    Example:
        GET /api/dashboard/trends/export?days=30&format=csv
        
    Error Codes:
        400: 格式不支持
        500: 导出失败
    """
    from flask import send_file
    
    try:
        # 获取参数
        days = request.args.get('days', '30')
        subject_id = request.args.get('subject_id')
        export_format = request.args.get('format', 'csv')
        
        # 格式校验 (NFR-34.6)
        if export_format not in ['csv']:
            return jsonify({
                'success': False,
                'error': f'不支持的导出格式: {export_format}，目前仅支持 csv'
            }), 400
        
        # 天数参数校验
        try:
            days = int(days)
            if days < 1:
                days = 30
            if days > 365:
                days = 365
        except (ValueError, TypeError):
            days = 30
        
        # 学科ID类型校验
        if subject_id is not None and subject_id != '':
            try:
                subject_id = int(subject_id)
            except (ValueError, TypeError):
                subject_id = None
        else:
            subject_id = None
        
        # 调用服务层导出
        filepath = DashboardService.export_trends_csv(days, subject_id)
        
        # 返回文件下载
        return send_file(
            filepath,
            as_attachment=True,
            download_name=os.path.basename(filepath)
        )
        
    except Exception as e:
        print(f"[Dashboard] 导出趋势数据失败: {e}")
        return jsonify({
            'success': False,
            'error': '导出趋势数据失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/statistics/snapshot', methods=['POST'])
def generate_statistics_snapshot():
    """
    手动生成统计快照
    
    用于手动触发生成指定日期的统计快照。
    
    Request Body:
        {
            date: string (可选，日期格式 YYYY-MM-DD，默认昨天)
        }
        
    Returns:
        JSON: {
            success: bool,
            data: {
                date: string,
                overall: {...},
                by_subject: {...}
            }
        }
        
    Example:
        POST /api/dashboard/statistics/snapshot
        Body: {"date": "2026-01-22"}
    """
    try:
        data = request.get_json() or {}
        date = data.get('date')
        
        # 日期格式校验
        if date:
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'无效的日期格式: {date}，应为 YYYY-MM-DD'
                }), 400
        
        # 调用服务层生成快照
        result = DashboardService.generate_daily_statistics_snapshot(date)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        print(f"[Dashboard] 生成统计快照失败: {e}")
        return jsonify({
            'success': False,
            'error': '生成统计快照失败，请稍后重试'
        }), 500


# ========== 智能搜索 API (US-32) ==========

@dashboard_bp.route('/api/dashboard/search', methods=['GET'])
def search():
    """
    智能搜索 (US-32)
    
    全局搜索框支持搜索任务名、数据集名、书本名、题号等内容。
    返回匹配结果并高亮关键词。
    
    Query Parameters:
        q: 搜索关键词（必填，至少1个字符）
        type: 搜索类型，可选值 all|task|dataset|book|question，默认 all
        
    Returns:
        JSON: {
            success: bool,
            data: {
                results: [
                    {
                        type: string,      # 结果类型: task|dataset|book|question
                        id: string,        # 结果ID
                        name: string,      # 结果名称
                        highlight: string  # 高亮后的名称（使用<mark>标签）
                    }
                ]
            }
        }
        
    Example:
        GET /api/dashboard/search?q=物理&type=all
        
    Response Example:
        {
            "success": true,
            "data": {
                "results": [
                    {
                        "type": "task",
                        "id": "xxx",
                        "name": "批量评估-物理八上",
                        "highlight": "批量评估-<mark>物理</mark>八上"
                    },
                    {
                        "type": "dataset",
                        "id": "yyy",
                        "name": "物理八上_P76-86",
                        "highlight": "<mark>物理</mark>八上_P76-86"
                    }
                ]
            }
        }
        
    Error Codes:
        400: 参数校验失败（缺少搜索关键词、类型无效）
        500: 服务器内部错误
    """
    try:
        # 获取搜索参数
        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'all')
        
        # 参数空值校验 (NFR-34.5)
        if not query:
            return jsonify({
                'success': False,
                'error': '搜索关键词不能为空'
            }), 400
        
        # 搜索类型校验 (NFR-34.6)
        valid_types = ['all', 'task', 'dataset', 'book', 'question']
        if search_type not in valid_types:
            return jsonify({
                'success': False,
                'error': f'无效的搜索类型，可选值: {", ".join(valid_types)}'
            }), 400
        
        # 调用服务层执行搜索
        data = DashboardService.search(query, search_type)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        # 异常处理 (NFR-34.7)
        print(f"[Dashboard] 搜索失败: {e}")
        return jsonify({
            'success': False,
            'error': '搜索失败，请稍后重试'
        }), 500


# ========== 高级分析工具 API ==========

@dashboard_bp.route('/api/dashboard/advanced-tools/stats', methods=['GET'])
def get_advanced_tools_stats():
    """
    获取高级分析工具统计数据
    
    从批量评估任务中聚合各工具的统计数据，用于更新看板徽章。
    
    Returns:
        JSON: {
            success: bool,
            data: {
                error_samples: {
                    total: int,      # 总错误样本数
                    pending: int,    # 待分析数
                    analyzed: int,   # 已分析数
                    fixed: int       # 已修复数
                },
                anomalies: {
                    total: int,      # 总异常数
                    unconfirmed: int,# 未确认数
                    today: int       # 今日异常数
                },
                clusters: {
                    total: int       # 聚类总数
                },
                suggestions: {
                    total: int,      # 总建议数
                    pending: int     # 待处理数
                }
            }
        }
        
    Example:
        GET /api/dashboard/advanced-tools/stats
    """
    try:
        # 从批量评估任务中聚合统计数据
        data = DashboardService.get_advanced_tools_stats()
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取高级工具统计失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取统计数据失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/batch-compare', methods=['GET'])
def get_batch_compare():
    """
    获取批次对比数据
    
    对比两个批量评估任务的评估结果。
    
    Query Parameters:
        task_id_1: 第一个批量评估任务ID (必填)
        task_id_2: 第二个批量评估任务ID (必填)
        
    Returns:
        JSON: {
            success: bool,
            data: {
                task1: {
                    task_id: string,
                    name: string,
                    accuracy: float,
                    total_questions: int,
                    correct_count: int,
                    error_distribution: {error_type: count}
                },
                task2: {
                    task_id: string,
                    name: string,
                    accuracy: float,
                    total_questions: int,
                    correct_count: int,
                    error_distribution: {error_type: count}
                },
                comparison: {
                    accuracy_diff: float,
                    improvement: bool,
                    error_changes: {error_type: diff}
                }
            }
        }
        
    Example:
        GET /api/dashboard/batch-compare?task_id_1=xxx&task_id_2=yyy
    """
    try:
        task_id_1 = request.args.get('task_id_1', '').strip()
        task_id_2 = request.args.get('task_id_2', '').strip()
        
        # 参数校验
        if not task_id_1:
            return jsonify({
                'success': False,
                'error': 'task_id_1 不能为空'
            }), 400
        
        if not task_id_2:
            return jsonify({
                'success': False,
                'error': 'task_id_2 不能为空'
            }), 400
        
        # 调用服务层获取对比数据
        data = DashboardService.get_batch_compare(task_id_1, task_id_2)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        print(f"[Dashboard] 获取批次对比数据失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取对比数据失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/batch-tasks', methods=['GET'])
def get_batch_tasks_for_compare():
    """
    获取可用于对比的批量评估任务列表
    
    Returns:
        JSON: {
            success: bool,
            data: [{
                task_id: string,
                name: string,
                subject_id: int,
                subject_name: string,
                accuracy: float,
                total_questions: int,
                created_at: string
            }]
        }
        
    Example:
        GET /api/dashboard/batch-tasks
    """
    try:
        data = DashboardService.get_batch_tasks_for_compare()
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取批量任务列表失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取任务列表失败，请稍后重试'
        }), 500


@dashboard_bp.route('/api/dashboard/drilldown', methods=['GET'])
def get_drilldown():
    """
    获取数据下钻分析结果
    
    基于批量评估任务数据进行多维度聚合分析。
    
    Query Parameters:
        dimension: 维度，可选值 subject|book|page|question_type (必填)
        parent_id: 父级ID，用于下钻 (可选)
        
    Returns:
        JSON: {
            success: bool,
            data: {
                dimension: string,
                parent_id: string,
                items: [{
                    id: string,
                    name: string,
                    total_questions: int,
                    correct_count: int,
                    error_count: int,
                    accuracy: float,
                    has_children: bool
                }]
            }
        }
        
    Example:
        GET /api/dashboard/drilldown?dimension=subject
        GET /api/dashboard/drilldown?dimension=book&parent_id=3
    """
    try:
        dimension = request.args.get('dimension', '').strip()
        parent_id = request.args.get('parent_id', '').strip()
        
        # 维度参数校验
        valid_dimensions = ['subject', 'book', 'page', 'question_type']
        if not dimension:
            return jsonify({
                'success': False,
                'error': 'dimension 不能为空'
            }), 400
        
        if dimension not in valid_dimensions:
            return jsonify({
                'success': False,
                'error': f'无效的维度: {dimension}，可选值: {", ".join(valid_dimensions)}'
            }), 400
        
        # 调用服务层获取下钻数据
        data = DashboardService.get_drilldown(dimension, parent_id if parent_id else None)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[Dashboard] 获取数据下钻失败: {e}")
        return jsonify({
            'success': False,
            'error': '获取下钻数据失败，请稍后重试'
        }), 500
