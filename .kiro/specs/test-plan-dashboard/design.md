# 测试计划看板 - 设计文档

## 1. 系统架构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           前端层 (templates + static)                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ index.html  │ │ index.js    │ │ index.css   │ │ 原生Canvas  │           │
│  │ (看板页面)   │ │ (交互逻辑)  │ │ (样式)      │ │ (图表渲染)  │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           路由层 (routes/dashboard.py)                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 基础功能 API (US-1~9)                                                │   │
│  │ /api/dashboard/overview      - 概览统计                              │   │
│  │ /api/dashboard/tasks         - 批量任务列表                          │   │
│  │ /api/dashboard/datasets      - 数据集概览                            │   │
│  │ /api/dashboard/subjects      - 学科评估概览                          │   │
│  │ /api/dashboard/plans         - 测试计划CRUD                          │   │
│  │ /api/dashboard/ai-plan       - AI生成测试计划                        │   │
│  │ /api/dashboard/sync          - 手动刷新数据                          │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ 高级功能 API (US-10~16)                                              │   │
│  │ /api/dashboard/schedule      - 自动化调度                            │   │
│  │ /api/dashboard/heatmap       - 问题热点图                            │   │
│  │ /api/dashboard/coverage      - AI覆盖率分析                          │   │
│  │ /api/dashboard/assignments   - 任务分配                              │   │
│  │ /api/dashboard/daily-report  - 日报生成                              │   │
│  │ /api/dashboard/trends        - 趋势分析                              │   │
│  │ /api/dashboard/best-practices- 最佳实践库                            │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ 分析功能 API (US-17~28)                                              │   │
│  │ /api/dashboard/compare       - A/B测试对比                           │   │
│  │ /api/dashboard/batch-compare - 批次对比                              │   │
│  │ /api/dashboard/error-samples - 错误样本库                            │   │
│  │ /api/dashboard/error-analysis- 错误关联分析                          │   │
│  │ /api/dashboard/drilldown     - 多维度下钻                            │   │
│  │ /api/dashboard/search        - 智能搜索                              │   │
│  │ /api/dashboard/anomaly       - 异常检测                              │   │
│  │ /api/dashboard/clustering    - 错误聚类                              │   │
│  │ /api/dashboard/suggestions   - AI优化建议                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           服务层 (services/)                                 │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐   │
│  │ dashboard_service.py│ │ schedule_service.py │ │ report_service.py   │   │
│  │ - 统计数据聚合       │ │ - APScheduler调度   │ │ - 日报生成          │   │
│  │ - 测试计划管理       │ │ - 定时任务管理      │ │ - 报告导出          │   │
│  │ - 数据缓存管理       │ │ - 执行日志记录      │ │ - AI总结            │   │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘   │
│  ┌─────────────────────┐ ┌─────────────────────┐                           │
│  │ analysis_service.py │ │ llm_service.py      │                           │
│  │ - 错误分析          │ │ - DeepSeek调用      │                           │
│  │ - 覆盖率计算        │ │ - AI计划生成        │                           │
│  │ - 异常检测          │ │ - 错误聚类          │                           │
│  └─────────────────────┘ └─────────────────────┘                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据层                                             │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐               │
│  │ batch_tasks/    │ │ datasets表      │ │ test_plans表    │               │
│  │ (JSON文件)      │ │ baseline_effects│ │ (新增MySQL表)   │               │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘               │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐               │
│  │daily_statistics │ │ error_samples   │ │ daily_reports   │               │
│  │ (新增MySQL表)   │ │ (新增MySQL表)   │ │ (新增MySQL表)   │               │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘
```


### 1.2 文件结构

```
routes/
  └── dashboard.py              # 看板路由 (所有API端点)

services/
  ├── dashboard_service.py      # 看板核心服务 (统计、计划管理、缓存)
  ├── schedule_service.py       # 调度服务 (APScheduler定时任务)
  ├── report_service.py         # 报告服务 (日报生成、导出)
  └── analysis_service.py       # 分析服务 (错误分析、覆盖率、异常检测)

templates/
  └── index.html                # 看板页面 (替换原聊天界面)

static/
  ├── css/
  │   └── index.css             # 看板样式 (修改现有文件)
  └── js/
      └── index.js              # 看板脚本 (修改现有文件)
```

---

## 2. 数据库设计

### 2.1 新增数据库表

#### test_plans 表 (测试计划)
```sql
CREATE TABLE test_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL UNIQUE COMMENT '计划唯一标识',
    name VARCHAR(200) NOT NULL COMMENT '计划名称',
    description TEXT COMMENT '计划描述',
    subject_ids JSON COMMENT '目标学科ID列表 [0,2,3]',
    target_count INT DEFAULT 0 COMMENT '目标测试数量',
    completed_count INT DEFAULT 0 COMMENT '已完成数量',
    status ENUM('draft', 'active', 'completed', 'archived') DEFAULT 'draft' COMMENT '状态',
    start_date DATE COMMENT '开始日期',
    end_date DATE COMMENT '结束日期',
    schedule_config JSON COMMENT '调度配置 {type:"daily"|"weekly"|"cron", time:"09:00", cron:"", enabled:true}',
    ai_generated TINYINT(1) DEFAULT 0 COMMENT '是否AI生成',
    assignee_id INT COMMENT '负责人ID (关联users表)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_assignee (assignee_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试计划表';
```

#### test_plan_datasets 表 (计划-数据集关联)
```sql
CREATE TABLE test_plan_datasets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL COMMENT '计划ID',
    dataset_id VARCHAR(36) NOT NULL COMMENT '数据集ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_plan_dataset (plan_id, dataset_id),
    INDEX idx_plan_id (plan_id),
    INDEX idx_dataset_id (dataset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试计划-数据集关联表';
```

#### test_plan_tasks 表 (计划-任务关联)
```sql
CREATE TABLE test_plan_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL COMMENT '计划ID',
    task_id VARCHAR(36) NOT NULL COMMENT '批量任务ID',
    task_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending' COMMENT '任务状态',
    accuracy DECIMAL(5,4) COMMENT '任务准确率',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_plan_task (plan_id, task_id),
    INDEX idx_plan_id (plan_id),
    INDEX idx_task_id (task_id),
    INDEX idx_task_status (task_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试计划-批量任务关联表';
```

#### daily_statistics 表 (每日统计缓存)
```sql
CREATE TABLE daily_statistics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stat_date DATE NOT NULL COMMENT '统计日期',
    subject_id INT COMMENT '学科ID，NULL表示全部',
    task_count INT DEFAULT 0 COMMENT '任务数',
    homework_count INT DEFAULT 0 COMMENT '作业数',
    question_count INT DEFAULT 0 COMMENT '题目数',
    correct_count INT DEFAULT 0 COMMENT '正确数',
    accuracy DECIMAL(5,4) DEFAULT 0 COMMENT '准确率',
    error_distribution JSON COMMENT '错误类型分布 {"识别错误-判断错误":10,...}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_date_subject (stat_date, subject_id),
    INDEX idx_stat_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日统计缓存表';
```

#### error_samples 表 (错误样本库)
```sql
CREATE TABLE error_samples (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sample_id VARCHAR(36) NOT NULL UNIQUE COMMENT '样本唯一标识',
    task_id VARCHAR(36) NOT NULL COMMENT '批量任务ID',
    homework_id VARCHAR(50) NOT NULL COMMENT '作业ID',
    book_id VARCHAR(50) COMMENT '书本ID',
    book_name VARCHAR(200) COMMENT '书本名称',
    page_num INT COMMENT '页码',
    question_index VARCHAR(50) NOT NULL COMMENT '题号',
    error_type VARCHAR(50) NOT NULL COMMENT '错误类型',
    base_answer TEXT COMMENT '基准答案',
    base_user TEXT COMMENT '基准用户答案',
    hw_user TEXT COMMENT 'AI识别答案',
    status ENUM('pending', 'analyzed', 'fixed') DEFAULT 'pending' COMMENT '状态',
    notes TEXT COMMENT '分析备注',
    cluster_id VARCHAR(36) COMMENT '聚类ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_error_type (error_type),
    INDEX idx_status (status),
    INDEX idx_cluster_id (cluster_id),
    INDEX idx_book_page (book_id, page_num)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='错误样本库';
```


#### daily_reports 表 (测试日报)
```sql
CREATE TABLE daily_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_id VARCHAR(36) NOT NULL UNIQUE COMMENT '日报唯一标识',
    report_date DATE NOT NULL COMMENT '日报日期',
    task_completed INT DEFAULT 0 COMMENT '完成任务数',
    task_planned INT DEFAULT 0 COMMENT '计划任务数',
    accuracy DECIMAL(5,4) DEFAULT 0 COMMENT '当日准确率',
    accuracy_change DECIMAL(5,4) DEFAULT 0 COMMENT '准确率变化（与昨日对比）',
    accuracy_week_change DECIMAL(5,4) DEFAULT 0 COMMENT '准确率变化（与上周同日对比）',
    top_errors JSON COMMENT '主要错误类型 Top 5 [{type,count},...]',
    new_error_types JSON COMMENT '今日新增错误类型',
    high_freq_errors JSON COMMENT '高频错误题目 [{index,count,book_name},...]',
    tomorrow_plan JSON COMMENT '明日计划任务列表',
    anomalies JSON COMMENT '异常情况列表',
    model_version VARCHAR(100) COMMENT '当日使用的AI模型版本',
    ai_summary TEXT COMMENT 'AI生成的总结',
    raw_content TEXT COMMENT '完整日报内容（Markdown）',
    generated_by ENUM('auto', 'manual') DEFAULT 'auto' COMMENT '生成方式',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_report_date (report_date),
    INDEX idx_report_date (report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试日报表';
```

#### test_plan_assignments 表 (任务分配)
```sql
CREATE TABLE test_plan_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL COMMENT '计划ID',
    user_id INT NOT NULL COMMENT '用户ID',
    role ENUM('owner', 'member') DEFAULT 'member' COMMENT '角色',
    status ENUM('pending', 'in_progress', 'completed') DEFAULT 'pending' COMMENT '状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_plan_user (plan_id, user_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试计划分配表';
```

#### test_plan_comments 表 (计划评论)
```sql
CREATE TABLE test_plan_comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    comment_id VARCHAR(36) NOT NULL UNIQUE COMMENT '评论唯一标识',
    plan_id VARCHAR(36) NOT NULL COMMENT '计划ID',
    user_id INT NOT NULL COMMENT '用户ID',
    content TEXT NOT NULL COMMENT '评论内容',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_plan_id (plan_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试计划评论表';
```

#### test_plan_logs 表 (执行日志)
```sql
CREATE TABLE test_plan_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    log_id VARCHAR(36) NOT NULL UNIQUE COMMENT '日志唯一标识',
    plan_id VARCHAR(36) NOT NULL COMMENT '计划ID',
    task_id VARCHAR(36) COMMENT '关联的批量任务ID',
    action VARCHAR(50) NOT NULL COMMENT '操作类型: scheduled_run, manual_run, status_change',
    details JSON COMMENT '详细信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_plan_id (plan_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试计划执行日志表';
```

#### anomaly_logs 表 (异常记录)
```sql
CREATE TABLE anomaly_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    anomaly_id VARCHAR(36) NOT NULL UNIQUE COMMENT '异常唯一标识',
    task_id VARCHAR(36) NOT NULL COMMENT '批量任务ID',
    anomaly_type VARCHAR(50) NOT NULL COMMENT '异常类型: accuracy_drop, task_failed',
    severity ENUM('low', 'medium', 'high') DEFAULT 'medium' COMMENT '严重程度',
    threshold DECIMAL(5,4) COMMENT '触发阈值',
    actual_value DECIMAL(5,4) COMMENT '实际值',
    expected_value DECIMAL(5,4) COMMENT '期望值',
    details JSON COMMENT '详细信息',
    acknowledged TINYINT(1) DEFAULT 0 COMMENT '是否已确认',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_anomaly_type (anomaly_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='异常记录表';
```

#### milestones 表 (里程碑)
```sql
CREATE TABLE milestones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    milestone_id VARCHAR(36) NOT NULL UNIQUE COMMENT '里程碑唯一标识',
    name VARCHAR(200) NOT NULL COMMENT '名称',
    description TEXT COMMENT '描述',
    milestone_date DATE NOT NULL COMMENT '日期',
    milestone_type VARCHAR(50) COMMENT '类型: model_update, config_change, release',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_milestone_date (milestone_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='里程碑表';
```

#### optimization_suggestions 表 (优化建议)
```sql
CREATE TABLE optimization_suggestions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    suggestion_id VARCHAR(36) NOT NULL UNIQUE COMMENT '建议唯一标识',
    title VARCHAR(200) NOT NULL COMMENT '标题',
    problem_description TEXT COMMENT '问题描述',
    affected_scope JSON COMMENT '影响范围 {subjects:[],question_types:[]}',
    solution TEXT COMMENT '优化方案',
    status ENUM('pending', 'in_progress', 'completed', 'rejected') DEFAULT 'pending' COMMENT '状态',
    priority ENUM('low', 'medium', 'high') DEFAULT 'medium' COMMENT '优先级',
    source_task_ids JSON COMMENT '来源任务ID列表',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_priority (priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优化建议表';
```


---

## 3. API 设计

### 3.1 基础功能 API (US-1~9)

#### 3.1.1 概览统计 API (US-2)
```
GET /api/dashboard/overview?range=today|week|month

Response:
{
    "success": true,
    "data": {
        "datasets": {
            "total": 15,
            "by_subject": {"0": 3, "2": 5, "3": 7}
        },
        "tasks": {
            "today": 5,
            "week": 25,
            "month": 100
        },
        "questions": {
            "tested": 5000,
            "total": 6000
        },
        "accuracy": {
            "current": 0.852,
            "previous": 0.830,
            "trend": "up"
        },
        "last_sync": "2026-01-23T10:30:00"
    }
}
```

#### 3.1.2 批量任务列表 API (US-3)
```
GET /api/dashboard/tasks?page=1&page_size=20&status=all|pending|processing|completed|failed

Response:
{
    "success": true,
    "data": {
        "tasks": [
            {
                "task_id": "074805e2",
                "name": "批量评估-2026/1/9",
                "status": "completed",
                "accuracy": 0.1667,
                "total_questions": 46,
                "created_at": "2026-01-09T15:26:23"
            }
        ],
        "pagination": {
            "page": 1,
            "page_size": 20,
            "total": 100,
            "total_pages": 5
        }
    }
}
```

#### 3.1.3 数据集概览 API (US-4)
```
GET /api/dashboard/datasets?subject_id=&sort_by=usage|accuracy|created_at&order=desc

Response:
{
    "success": true,
    "data": {
        "total": 15,
        "by_subject": {"0": 3, "2": 5, "3": 7},
        "datasets": [
            {
                "dataset_id": "b3b0395e",
                "name": "物理八上_P76-86_01091526",
                "subject_id": 3,
                "subject_name": "物理",
                "question_count": 46,
                "pages": [76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86],
                "page_range": "76-86",
                "usage_count": 12,
                "last_used": "2026-01-20T14:30:00",
                "history_accuracy": 0.72,
                "last_accuracy": 0.68,
                "last_test_time": "2026-01-20T14:30:00",
                "difficulty": "hard"
            }
        ],
        "top_usage": [...]
    }
}
```

#### 3.1.4 学科评估概览 API (US-5)
```
GET /api/dashboard/subjects

Response:
{
    "success": true,
    "data": [
        {
            "subject_id": 3,
            "subject_name": "物理",
            "task_count": 30,
            "homework_count": 350,
            "question_count": 1500,
            "correct_count": 1275,
            "accuracy": 0.85,
            "warning": false,
            "error_types": {
                "识别错误-判断错误": 50,
                "识别正确-判断错误": 30,
                "缺失题目": 20,
                "AI识别幻觉": 15
            }
        }
    ]
}
```

#### 3.1.5 测试计划 CRUD API (US-6)
```
# 获取计划列表
GET /api/dashboard/plans?status=all|draft|active|completed|archived

# 创建计划
POST /api/dashboard/plans
Request:
{
    "name": "物理八上温度章节测试",
    "description": "测试温度相关知识点的AI批改效果",
    "subject_ids": [3],
    "target_count": 30,
    "start_date": "2026-01-23",
    "end_date": "2026-01-30",
    "dataset_ids": ["b3b0395e", "xxx"]
}

# 获取计划详情 (含关联任务列表)
GET /api/dashboard/plans/<plan_id>
Response:
{
    "success": true,
    "data": {
        "plan_id": "xxx",
        "name": "物理八上温度章节测试",
        "status": "active",
        "progress": 0.6,
        "datasets": [...],
        "tasks": [
            {
                "task_id": "xxx",
                "name": "批量评估-2026/1/23",
                "status": "completed",
                "accuracy": 0.85,
                "created_at": "2026-01-23T10:00:00"
            }
        ]
    }
}

# 更新计划
PUT /api/dashboard/plans/<plan_id>

# 删除计划
DELETE /api/dashboard/plans/<plan_id>

# 克隆计划
POST /api/dashboard/plans/<plan_id>/clone

# 关联批量任务到计划
POST /api/dashboard/plans/<plan_id>/tasks
Request: { "task_id": "xxx" }
```

#### 3.1.6 AI生成测试计划 API (US-7)
```
POST /api/dashboard/ai-plan
Request:
{
    "dataset_ids": ["b3b0395e", "xxx"],
    "sample_count": 30,
    "subject_id": 3
}

Response:
{
    "success": true,
    "data": {
        "name": "物理八上温度章节测试计划",
        "description": "针对温度相关知识点的AI批改效果测试",
        "objectives": [
            "验证温度计读数识别准确率",
            "验证填空题答案匹配准确率",
            "验证选择题判断准确率"
        ],
        "steps": [...],
        "expected_duration": "2小时",
        "acceptance_criteria": [
            "选择题准确率 >= 95%",
            "填空题准确率 >= 85%",
            "整体准确率 >= 80%"
        ]
    }
}
```

#### 3.1.7 数据同步 API (US-9)
```
POST /api/dashboard/sync

Response:
{
    "success": true,
    "data": {
        "synced_tasks": 50,
        "synced_at": "2026-01-23T10:30:00"
    }
}
```


### 3.2 高级功能 API (US-10~16)

#### 3.2.1 自动化调度 API (US-10)
```
# 设置调度配置
PUT /api/dashboard/plans/<plan_id>/schedule
Request:
{
    "type": "daily",
    "time": "09:00",
    "day_of_week": 1,
    "cron": "0 9 * * *",
    "enabled": true
}

Response:
{
    "success": true,
    "data": {
        "next_run": "2026-01-24T09:00:00"
    }
}

# 获取执行日志
GET /api/dashboard/plans/<plan_id>/logs?page=1&page_size=20
```

#### 3.2.2 问题热点图 API (US-11)
```
GET /api/dashboard/heatmap?subject_id=&days=7|30|all

Response:
{
    "success": true,
    "data": {
        "heatmap": [
            {
                "book_id": "xxx",
                "book_name": "物理八上",
                "error_count": 50,
                "pages": [
                    {
                        "page_num": 76,
                        "error_count": 20,
                        "questions": [
                            {
                                "index": "1",
                                "error_count": 8,
                                "heat_level": "critical"
                            }
                        ]
                    }
                ]
            }
        ]
    }
}
```

#### 3.2.3 AI覆盖率分析 API (US-12)
```
POST /api/dashboard/coverage
Request:
{
    "subject_ids": [3],
    "date_range": {
        "start": "2026-01-01",
        "end": "2026-01-23"
    }
}

Response:
{
    "success": true,
    "data": {
        "coverage": {
            "choice": 0.95,
            "objective_fill": 0.78,
            "subjective": 0.45
        },
        "uncovered_areas": [
            {
                "subject": "物理",
                "question_type": "主观题",
                "coverage": 0.45,
                "suggestion": "建议增加物理主观题测试数据集"
            }
        ],
        "report_markdown": "# 覆盖率分析报告\n..."
    }
}
```

#### 3.2.4 任务分配 API (US-13)
```
# 分配任务
POST /api/dashboard/plans/<plan_id>/assignments
Request: { "user_id": 1, "role": "member" }

# 获取成员任务列表
GET /api/dashboard/assignments?user_id=1

# 更新任务状态
PUT /api/dashboard/assignments/<assignment_id>
Request: { "status": "in_progress" }

# 添加评论
POST /api/dashboard/plans/<plan_id>/comments
Request: { "content": "已完成第一批测试" }
```

#### 3.2.5 日报 API (US-14)
```
# 生成日报
POST /api/dashboard/daily-report
Request: { "date": "2026-01-23" }

Response:
{
    "success": true,
    "data": {
        "report_id": "xxx",
        "report_date": "2026-01-23",
        "task_completed": 5,
        "task_planned": 8,
        "accuracy": 0.85,
        "accuracy_change": 0.02,
        "accuracy_week_change": 0.05,
        "top_errors": [
            {"type": "识别错误-判断错误", "count": 30}
        ],
        "new_error_types": ["新错误类型A"],
        "high_freq_errors": [
            {"index": "3", "count": 5, "book_name": "物理八上"}
        ],
        "model_version": "doubao-1-5-vision-pro-32k-250115",
        "ai_summary": "今日测试整体表现良好...",
        "raw_content": "# 测试日报 2026-01-23\n..."
    }
}

# 获取历史日报列表
GET /api/dashboard/daily-reports?page=1&page_size=30

# 导出日报
GET /api/dashboard/daily-report/<report_id>/export?format=pdf|docx
```

#### 3.2.6 趋势分析 API (US-15)
```
GET /api/dashboard/trends?days=7|30|90&subject_id=

Response:
{
    "success": true,
    "data": {
        "trends": [
            {
                "date": "2026-01-23",
                "accuracy": 0.85,
                "task_count": 5,
                "question_count": 230
            }
        ],
        "by_subject": {
            "3": [{"date": "2026-01-23", "accuracy": 0.85}]
        },
        "milestones": [
            {
                "date": "2026-01-20",
                "name": "模型更新v2.0",
                "type": "model_update"
            }
        ]
    }
}

# 添加里程碑
POST /api/dashboard/milestones
Request:
{
    "name": "模型更新v2.0",
    "description": "升级到doubao-1-5-vision-pro",
    "milestone_date": "2026-01-20",
    "milestone_type": "model_update"
}

# 导出历史数据
GET /api/dashboard/trends/export?days=30&format=csv
```

#### 3.2.7 最佳实践库 API (US-16)
```
GET /api/dashboard/best-practices

Response:
{
    "success": true,
    "data": {
        "prompts": [
            {
                "prompt_key": "physics_grading",
                "prompt_version": "v1.2",
                "accuracy": 0.92,
                "is_best_practice": true,
                "usage_count": 50,
                "last_used": "2026-01-23"
            }
        ]
    }
}

# 应用最佳实践
POST /api/dashboard/best-practices/apply
Request: { "prompt_key": "physics_grading", "prompt_version": "v1.2" }
```


### 3.3 分析功能 API (US-17~28)

#### 3.3.1 A/B测试对比 API (US-17)
```
POST /api/dashboard/compare
Request: { "task_id_a": "xxx", "task_id_b": "yyy" }

Response:
{
    "success": true,
    "data": {
        "task_a": {
            "task_id": "xxx",
            "name": "批量评估A",
            "accuracy": 0.85,
            "total_questions": 100,
            "correct_count": 85,
            "error_distribution": {...}
        },
        "task_b": {...},
        "diff": {
            "accuracy": 0.03,
            "highlight": true
        },
        "report_markdown": "# A/B测试对比报告\n..."
    }
}
```

#### 3.3.2 批次对比 API (US-18)
```
GET /api/dashboard/batch-compare?start=2026-01-01&end=2026-01-23

Response:
{
    "success": true,
    "data": {
        "batches": [
            {
                "task_id": "xxx",
                "name": "批量评估-2026/1/23",
                "accuracy": 0.85,
                "created_at": "2026-01-23T10:00:00",
                "is_anomaly": false
            }
        ],
        "mean_accuracy": 0.82,
        "std_deviation": 0.05,
        "anomaly_threshold": 0.72
    }
}
```

#### 3.3.3 错误样本库 API (US-19)
```
# 获取错误样本列表
GET /api/dashboard/error-samples?error_type=&status=&page=1&page_size=20

# 更新样本状态
PUT /api/dashboard/error-samples/<sample_id>
Request: { "status": "analyzed", "notes": "识别模型对手写体识别不准确" }

# 批量更新状态
POST /api/dashboard/error-samples/batch-update
Request: { "sample_ids": ["xxx", "yyy"], "status": "analyzed" }
```

#### 3.3.4 错误关联分析 API (US-20)
```
POST /api/dashboard/error-analysis
Request:
{
    "date_range": { "start": "2026-01-01", "end": "2026-01-23" }
}

Response:
{
    "success": true,
    "data": {
        "by_book": [{"book_name": "物理八上", "error_rate": 0.15}],
        "by_question_type": [
            {"type": "选择题", "error_rate": 0.05},
            {"type": "填空题", "error_rate": 0.12},
            {"type": "主观题", "error_rate": 0.25}
        ],
        "by_subject": [{"subject": "物理", "error_rate": 0.15}],
        "ai_suggestions": [
            "建议优化主观题识别模型",
            "物理学科填空题错误率较高，建议增加训练数据"
        ]
    }
}
```

#### 3.3.5 多维度下钻 API (US-21)
```
GET /api/dashboard/drilldown?level=overall|subject|book|page|question&subject_id=&book_id=&page_num=

Response:
{
    "success": true,
    "data": {
        "level": "subject",
        "breadcrumb": [
            {"level": "overall", "name": "总体", "accuracy": 0.82}
        ],
        "current": {
            "name": "物理",
            "accuracy": 0.85,
            "total_questions": 1500,
            "error_count": 225
        },
        "children": [
            {
                "id": "xxx",
                "name": "物理八上",
                "accuracy": 0.83,
                "question_count": 500
            }
        ]
    }
}
```

#### 3.3.6 错误详情快速查看 API (US-22)
```
GET /api/dashboard/errors?task_id=&error_types=&page=1&page_size=20

Response:
{
    "success": true,
    "data": {
        "errors": [
            {
                "sample_id": "xxx",
                "question_index": "3",
                "error_type": "识别错误-判断错误",
                "base_answer": "温度",
                "hw_user": "温庆",
                "book_name": "物理八上",
                "page_num": 76
            }
        ],
        "pagination": {...}
    }
}
```

#### 3.3.7 图片对比查看 API (US-23)
```
GET /api/dashboard/image-compare?homework_id=&question_index=

Response:
{
    "success": true,
    "data": {
        "pic_path": "https://...",
        "homework_result": {...},
        "base_answer": "温度",
        "hw_user": "温庆",
        "error_type": "识别错误-判断错误",
        "prev_question": "2",
        "next_question": "4"
    }
}
```

#### 3.3.8 多条件组合筛选 API (US-24)
```
POST /api/dashboard/filter
Request:
{
    "subject_ids": [3],
    "question_types": ["choice", "objective_fill"],
    "error_types": ["识别错误-判断错误"],
    "date_range": { "start": "2026-01-01", "end": "2026-01-23" },
    "accuracy_range": { "min": 0, "max": 0.8 }
}

Response:
{
    "success": true,
    "data": {
        "results": [...],
        "total": 150
    }
}
```

#### 3.3.9 快速导出 API (US-25)
```
POST /api/dashboard/export
Request:
{
    "type": "errors",
    "format": "xlsx",
    "filters": {...}
}

Response:
{
    "success": true,
    "data": {
        "file_path": "/exports/errors_20260123_103000.xlsx",
        "download_url": "/api/dashboard/export/download/xxx"
    }
}
```

#### 3.3.10 异常检测 API (US-26)
```
GET /api/dashboard/anomaly?days=7

Response:
{
    "success": true,
    "data": {
        "anomalies": [
            {
                "anomaly_id": "xxx",
                "task_id": "yyy",
                "task_name": "批量评估-2026/1/23",
                "anomaly_type": "accuracy_drop",
                "severity": "high",
                "actual_value": 0.65,
                "expected_value": 0.82,
                "threshold": 0.72,
                "created_at": "2026-01-23T10:00:00"
            }
        ],
        "threshold_config": { "std_multiplier": 2 }
    }
}

# 更新阈值配置
PUT /api/dashboard/anomaly/config
Request: { "std_multiplier": 2.5 }
```

#### 3.3.11 错误聚类 API (US-27)
```
POST /api/dashboard/clustering
Request: { "task_ids": ["xxx", "yyy"], "min_samples": 5 }

Response:
{
    "success": true,
    "data": {
        "clusters": [
            {
                "cluster_id": "xxx",
                "label": "手写体识别错误",
                "sample_count": 25,
                "typical_sample": {
                    "question_index": "3",
                    "base_answer": "温度",
                    "hw_user": "温庆"
                },
                "error_types": ["识别错误-判断错误"]
            }
        ]
    }
}

# 合并聚类
POST /api/dashboard/clustering/merge
Request: { "cluster_ids": ["xxx", "yyy"], "new_label": "手写体识别问题" }

# 拆分聚类
POST /api/dashboard/clustering/split
Request: { "cluster_id": "xxx", "sample_ids": ["aaa", "bbb"] }
```

#### 3.3.12 AI优化建议 API (US-28)
```
POST /api/dashboard/suggestions
Request:
{
    "task_ids": ["xxx", "yyy"],
    "date_range": { "start": "2026-01-01", "end": "2026-01-23" }
}

Response:
{
    "success": true,
    "data": {
        "suggestions": [
            {
                "suggestion_id": "xxx",
                "title": "优化手写体识别模型",
                "problem_description": "手写体识别错误占总错误的35%",
                "affected_scope": {
                    "subjects": ["物理", "数学"],
                    "question_types": ["填空题"]
                },
                "solution": "建议增加手写体训练数据，特别是数字和单位的识别",
                "priority": "high",
                "status": "pending"
            }
        ]
    }
}

# 更新建议状态
PUT /api/dashboard/suggestions/<suggestion_id>
Request: { "status": "in_progress" }
```


### 3.4 性能与体验优化 API (US-29~33)

#### 3.4.1 智能搜索 API (US-32)
```
GET /api/dashboard/search?q=物理&type=all|task|dataset|book|question

Response:
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
```

#### 3.4.2 数据对比增强 API (US-33)
```
GET /api/dashboard/compare-period?compare_type=last_week|last_month|custom&custom_start=&custom_end=

Response:
{
    "success": true,
    "data": {
        "current": {
            "accuracy": 0.85,
            "task_count": 25,
            "question_count": 1200
        },
        "compare": {
            "accuracy": 0.82,
            "task_count": 20,
            "question_count": 1000
        },
        "diff": {
            "accuracy": 0.03,
            "accuracy_status": "above"
        },
        "baseline": {
            "value": 0.85,
            "source": "custom"
        }
    }
}

# 设置基线
PUT /api/dashboard/baseline
Request: { "value": 0.85 }
```

---

## 4. 前端设计

### 4.1 页面布局 (US-1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  侧边栏 (200px)        │              主内容区                               │
│  ┌─────────────────┐  │  ┌─────────────────────────────────────────────────┐│
│  │ 品牌标识        │  │  │ 顶部栏: 最后同步时间 + 刷新按钮 + 搜索框        ││
│  │                 │  │  └─────────────────────────────────────────────────┘│
│  │ 导航菜单        │  │  ┌─────────────────────────────────────────────────┐│
│  │ ● 测试看板      │  │  │ 统计概览区 (4个卡片)                            ││
│  │ ○ 学科批改评估  │  │  │ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐               ││
│  │ ○ 批量评估      │  │  │ │数据集│ │任务数│ │题目数│ │准确率│               ││
│  │ ○ 知识点类题    │  │  │ └─────┘ └─────┘ └─────┘ └─────┘               ││
│  │ ○ 数据分析      │  │  └─────────────────────────────────────────────────┘│
│  │ ○ 数据集管理    │  │  ┌────────────────────┐ ┌────────────────────────┐ │
│  │ ○ 提示词优化    │  │  │ 任务列表区 (左下)   │ │ 数据集区 (右上)        │ │
│  │                 │  │  │                    │ │                        │ │
│  │                 │  │  │ - 最近20条任务     │ │ - 数据集列表           │ │
│  │                 │  │  │ - 状态筛选         │ │ - 学科分布饼图         │ │
│  │                 │  │  │ - 分页加载         │ │ - 使用频率排行         │ │
│  │                 │  │  │                    │ ├────────────────────────┤ │
│  │                 │  │  │                    │ │ 学科概览区 (右下)      │ │
│  │                 │  │  │                    │ │                        │ │
│  │                 │  │  │                    │ │ - 各学科准确率柱状图   │ │
│  │                 │  │  │                    │ │ - 错误类型分布         │ │
│  └─────────────────┘  │  └────────────────────┘ └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 响应式断点

| 断点 | 布局 |
|------|------|
| >= 1200px | 三列布局 (侧边栏 + 任务列表 + 数据集/学科) |
| 768px ~ 1199px | 两列布局 (侧边栏折叠 + 主内容区) |
| < 768px | 单列布局 (侧边栏隐藏) |

### 4.3 组件设计

#### 4.3.1 统计卡片组件
```html
<div class="stat-card" onclick="navigateTo('/dataset-manage')">
    <div class="stat-value">15</div>
    <div class="stat-label">数据集总数</div>
    <div class="stat-detail">物理 7 | 数学 5 | 英语 3</div>
</div>
```

#### 4.3.2 任务列表项组件
```html
<div class="task-item" onclick="navigateTo('/batch-evaluation?task_id=xxx')">
    <div class="task-name">批量评估-2026/1/9</div>
    <div class="task-meta">
        <span class="task-time">01-09 15:26</span>
        <span class="task-status status-completed">已完成</span>
        <span class="task-accuracy">16.67%</span>
        <span class="task-questions">46题</span>
    </div>
</div>
```

#### 4.3.3 数据集列表项组件
```html
<div class="dataset-item" onclick="navigateTo('/dataset-manage?dataset_id=xxx')">
    <div class="dataset-name">物理八上_P76-86_01091526</div>
    <div class="dataset-meta">
        <span class="dataset-subject">物理</span>
        <span class="dataset-questions">46题</span>
        <span class="dataset-pages">P76-86</span>
        <span class="dataset-usage">使用12次</span>
        <span class="dataset-accuracy difficulty-hard">72%</span>
    </div>
    <div class="dataset-history-tooltip">
        <!-- 悬停显示历史测试摘要 -->
    </div>
</div>
```

### 4.4 状态标签样式

| 状态 | 背景色 | 文字色 |
|------|--------|--------|
| pending | #f5f5f7 | #86868b |
| processing | #e3f2fd | #1565c0 |
| completed | #e3f9e5 | #1e7e34 |
| failed | #ffeef0 | #d73a49 |

### 4.5 难度标签样式

| 难度 | 准确率范围 | 背景色 |
|------|-----------|--------|
| easy | >= 90% | #e3f9e5 |
| medium | 70% ~ 90% | #fff3e0 |
| hard | < 70% | #ffeef0 |


---

## 5. 服务层设计

### 5.1 DashboardService (dashboard_service.py)

```python
class DashboardService:
    """看板核心服务"""
    
    # 内存缓存 (5分钟TTL)
    _cache = {}
    _cache_ttl = 300
    
    @staticmethod
    def get_overview(time_range: str = 'today') -> dict:
        """
        获取概览统计数据 (US-2)
        
        Args:
            time_range: 时间范围 today|week|month
            
        Returns:
            dict: 包含 datasets, tasks, questions, accuracy 的统计数据
        """
        pass
    
    @staticmethod
    def get_tasks(page: int, page_size: int, status: str) -> dict:
        """
        获取批量任务列表 (US-3)
        
        Args:
            page: 页码
            page_size: 每页数量
            status: 状态筛选 all|pending|processing|completed|failed
            
        Returns:
            dict: 任务列表和分页信息
        """
        pass
    
    @staticmethod
    def get_datasets_overview(subject_id: int = None, sort_by: str = 'created_at', order: str = 'desc') -> dict:
        """
        获取数据集概览 (US-4)
        包含历史准确率、使用次数、难度标签
        
        Args:
            subject_id: 学科ID筛选
            sort_by: 排序字段 usage|accuracy|created_at
            order: 排序方向 asc|desc
            
        Returns:
            dict: 数据集列表和统计信息
        """
        pass
    
    @staticmethod
    def get_subjects_overview() -> list:
        """
        获取学科评估概览 (US-5)
        
        Returns:
            list: 各学科统计数据
        """
        pass
    
    # 测试计划 CRUD (US-6)
    @staticmethod
    def create_plan(data: dict) -> dict:
        """创建测试计划"""
        pass
    
    @staticmethod
    def get_plan(plan_id: str) -> dict:
        """获取计划详情，包含关联任务列表"""
        pass
    
    @staticmethod
    def update_plan(plan_id: str, data: dict) -> dict:
        """更新测试计划"""
        pass
    
    @staticmethod
    def delete_plan(plan_id: str) -> bool:
        """删除测试计划"""
        pass
    
    @staticmethod
    def clone_plan(plan_id: str) -> dict:
        """克隆测试计划"""
        pass
    
    @staticmethod
    def link_task_to_plan(plan_id: str, task_id: str) -> bool:
        """关联批量任务到计划"""
        pass
    
    @staticmethod
    def update_plan_progress(plan_id: str):
        """
        自动更新计划完成度 (US-6.9)
        当关联任务完成时调用
        """
        pass
    
    # 缓存管理 (US-29)
    @staticmethod
    def get_cached(key: str):
        """获取缓存数据"""
        pass
    
    @staticmethod
    def set_cached(key: str, value: any, ttl: int = 300):
        """设置缓存数据"""
        pass
    
    @staticmethod
    def clear_cache():
        """清除所有缓存"""
        pass
```

### 5.2 ScheduleService (schedule_service.py)

```python
from apscheduler.schedulers.background import BackgroundScheduler

class ScheduleService:
    """调度服务 (US-10)"""
    
    scheduler = BackgroundScheduler()
    
    @staticmethod
    def init_scheduler():
        """初始化调度器"""
        pass
    
    @staticmethod
    def set_plan_schedule(plan_id: str, config: dict) -> str:
        """
        设置计划调度
        
        Args:
            plan_id: 计划ID
            config: {type, time, day_of_week, cron, enabled}
            
        Returns:
            str: 下次执行时间
        """
        pass
    
    @staticmethod
    def execute_scheduled_task(plan_id: str):
        """执行定时任务"""
        pass
    
    @staticmethod
    def get_next_run_time(plan_id: str) -> str:
        """获取下次执行时间"""
        pass
    
    @staticmethod
    def log_execution(plan_id: str, task_id: str, action: str, details: dict):
        """记录执行日志"""
        pass
```

### 5.3 ReportService (report_service.py)

```python
class ReportService:
    """报告服务 (US-14)"""
    
    @staticmethod
    def generate_daily_report(date: str = None) -> dict:
        """
        生成测试日报
        
        包含:
        - 今日任务完成数
        - 准确率及变化
        - 主要错误类型 Top 5
        - 新增错误类型
        - 高频错误题目
        - 明日计划
        - 异常情况
        - 模型版本信息
        - AI总结
        
        Args:
            date: 日期，默认今天
            
        Returns:
            dict: 日报数据
        """
        pass
    
    @staticmethod
    def get_new_error_types(date: str) -> list:
        """
        获取今日新增错误类型 (US-14.2)
        与历史错误类型对比
        """
        pass
    
    @staticmethod
    def get_high_freq_errors(date: str) -> list:
        """
        获取高频错误题目 (US-14.2)
        同一题目出错次数>=3
        """
        pass
    
    @staticmethod
    def export_report(report_id: str, format: str) -> str:
        """
        导出日报
        
        Args:
            report_id: 日报ID
            format: pdf|docx
            
        Returns:
            str: 文件路径
        """
        pass
    
    @staticmethod
    def get_report_history(page: int, page_size: int) -> dict:
        """获取历史日报列表"""
        pass
```

### 5.4 AnalysisService (analysis_service.py)

```python
class AnalysisService:
    """分析服务"""
    
    @staticmethod
    def get_heatmap(subject_id: int = None, days: int = 7) -> dict:
        """
        获取问题热点图 (US-11)
        按 book → page → question 三级聚合
        """
        pass
    
    @staticmethod
    def analyze_coverage(subject_ids: list, date_range: dict) -> dict:
        """
        AI覆盖率分析 (US-12)
        分析选择题、客观填空题、主观题覆盖率
        """
        pass
    
    @staticmethod
    def detect_anomaly(days: int = 7) -> list:
        """
        异常检测 (US-26)
        检测准确率异常波动 (偏离均值2σ)
        """
        pass
    
    @staticmethod
    def cluster_errors(task_ids: list = None, min_samples: int = 5) -> dict:
        """
        错误聚类 (US-27)
        使用AI对错误进行相似度聚类
        """
        pass
    
    @staticmethod
    def generate_suggestions(task_ids: list = None, date_range: dict = None) -> list:
        """
        AI优化建议 (US-28)
        分析错误样本，生成优化建议
        """
        pass
    
    @staticmethod
    def compare_tasks(task_id_a: str, task_id_b: str) -> dict:
        """
        A/B测试对比 (US-17)
        """
        pass
    
    @staticmethod
    def analyze_error_correlation(date_range: dict) -> dict:
        """
        错误关联分析 (US-20)
        分析错误与书本/题型/学科的关联
        """
        pass
    
    @staticmethod
    def drilldown(level: str, **kwargs) -> dict:
        """
        多维度下钻 (US-21)
        支持 overall → subject → book → page → question
        """
        pass
```


---

## 6. 前端 JavaScript 设计

### 6.1 API 模块

```javascript
/**
 * 看板 API 封装
 */
const DashboardAPI = {
    // 基础功能
    getOverview: (range = 'today') => 
        fetch(`/api/dashboard/overview?range=${range}`).then(r => r.json()),
    
    getTasks: (page = 1, pageSize = 20, status = 'all') => 
        fetch(`/api/dashboard/tasks?page=${page}&page_size=${pageSize}&status=${status}`).then(r => r.json()),
    
    getDatasets: (subjectId = '', sortBy = 'created_at', order = 'desc') => 
        fetch(`/api/dashboard/datasets?subject_id=${subjectId}&sort_by=${sortBy}&order=${order}`).then(r => r.json()),
    
    getSubjects: () => 
        fetch('/api/dashboard/subjects').then(r => r.json()),
    
    sync: () => 
        fetch('/api/dashboard/sync', { method: 'POST' }).then(r => r.json()),
    
    // 测试计划
    getPlans: (status = 'all') => 
        fetch(`/api/dashboard/plans?status=${status}`).then(r => r.json()),
    
    createPlan: (data) => 
        fetch('/api/dashboard/plans', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        }).then(r => r.json()),
    
    getPlan: (planId) => 
        fetch(`/api/dashboard/plans/${planId}`).then(r => r.json()),
    
    // 搜索
    search: (query, type = 'all') => 
        fetch(`/api/dashboard/search?q=${encodeURIComponent(query)}&type=${type}`).then(r => r.json()),
    
    // 导出
    exportData: (type, format, filters) => 
        fetch('/api/dashboard/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, format, filters })
        }).then(r => r.json())
};
```

### 6.2 UI 组件函数

```javascript
/**
 * 渲染统计卡片
 * @param {Object} data - 统计数据
 */
function renderStatCards(data) {
    // 数据集卡片
    // 任务数卡片
    // 题目数卡片
    // 准确率卡片 (含趋势箭头)
}

/**
 * 渲染任务列表
 * @param {Array} tasks - 任务数组
 */
function renderTaskList(tasks) {
    // 渲染任务项
    // 状态标签样式
}

/**
 * 渲染数据集列表
 * @param {Array} datasets - 数据集数组
 */
function renderDatasetList(datasets) {
    // 渲染数据集项
    // 难度标签
    // 悬停显示历史测试摘要
}

/**
 * 渲染学科柱状图 (原生Canvas)
 * @param {Array} subjects - 学科数据
 */
function renderSubjectChart(subjects) {
    // 水平条形图
    // 准确率<80%标红
}

/**
 * 渲染学科分布饼图 (原生Canvas/SVG)
 * @param {Object} distribution - 学科分布数据
 */
function renderSubjectPieChart(distribution) {
    // 饼图
}

/**
 * 显示骨架屏
 */
function showSkeleton() {
    // 灰色占位块动画
}

/**
 * 显示Toast通知
 * @param {string} message - 消息内容
 * @param {string} type - 类型 success|error|warning
 */
function showToast(message, type = 'info') {
    // 3秒后自动消失
}
```

### 6.3 事件处理

```javascript
// 刷新按钮
document.getElementById('refresh-btn').addEventListener('click', async () => {
    showLoading();
    try {
        await DashboardAPI.sync();
        await loadDashboard();
        showToast('数据刷新成功', 'success');
    } catch (e) {
        showToast('刷新失败，请稍后重试', 'error');
    }
});

// 搜索框 (防抖300ms)
const searchInput = document.getElementById('search-input');
let searchTimer;
searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
        performSearch(e.target.value);
    }, 300);
});

// 快捷键 '/' 聚焦搜索框
document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        searchInput.focus();
    }
});

// 任务状态筛选
document.querySelectorAll('.status-filter').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const status = e.target.dataset.status;
        loadTasks(1, 20, status);
    });
});

// 数据集排序
document.getElementById('dataset-sort').addEventListener('change', (e) => {
    const [sortBy, order] = e.target.value.split('-');
    loadDatasets(null, sortBy, order);
});
```

### 6.4 虚拟滚动 (US-31)

```javascript
/**
 * 虚拟滚动实现
 * 列表超过100条时启用
 */
class VirtualScroller {
    constructor(container, itemHeight, renderItem) {
        this.container = container;
        this.itemHeight = itemHeight;
        this.renderItem = renderItem;
        this.items = [];
        this.visibleStart = 0;
        this.visibleEnd = 0;
        
        this.container.addEventListener('scroll', () => {
            requestAnimationFrame(() => this.onScroll());
        });
    }
    
    setItems(items) {
        this.items = items;
        this.render();
    }
    
    onScroll() {
        // 计算可见区域
        // 只渲染可见项
    }
    
    render() {
        // 渲染可见项
    }
}
```


---

## 7. 正确性属性

### 7.1 数据一致性属性

| ID | 属性 | 描述 | 验证方式 |
|----|------|------|----------|
| P1 | 统计数据一致性 | 概览统计数据与实际任务数据一致 | 对比聚合结果与原始数据 |
| P2 | 准确率计算正确性 | accuracy = correct_count / total_questions | 属性测试验证计算公式 |
| P3 | 分页数据完整性 | 分页遍历所有数据等于总数据 | 遍历所有页验证 |
| P4 | 缓存数据一致性 | 缓存数据与数据库数据一致 | 清除缓存后对比 |

### 7.2 业务规则属性

| ID | 属性 | 描述 | 验证方式 |
|----|------|------|----------|
| P5 | 计划状态流转 | draft → active → completed/archived | 状态机测试 |
| P6 | 计划完成度自动更新 | 关联任务完成时 completed_count 自动+1 | 集成测试 |
| P7 | 异常检测阈值 | 准确率偏离均值2σ时触发异常 | 统计测试 |
| P8 | 难度标签正确性 | easy(>=90%), medium(70-90%), hard(<70%) | 边界测试 |

### 7.3 性能属性

| ID | 属性 | 描述 | 验证方式 |
|----|------|------|----------|
| P9 | API响应时间 | P95 < 2秒 | 性能测试 |
| P10 | 首屏渲染时间 | LCP < 3秒 | Lighthouse测试 |
| P11 | 缓存命中率 | 热点数据缓存命中率 > 80% | 监控统计 |

---

## 8. 技术约束

### 8.1 前端约束
- 原生 JavaScript + CSS，不引入 React/Vue 等框架
- 图表使用原生 Canvas/SVG 实现，不引入 ECharts/Chart.js
- 遵循 `ui-style.md` 规范，浅色主题

### 8.2 后端约束
- Flask 蓝图，遵循现有项目结构
- 数据库使用 MySQL，通过 `AppDatabaseService` 操作
- AI 调用使用 `LLMService.call_deepseek()`
- 定时任务使用 APScheduler

### 8.3 代码质量约束 (NFR-34)
- 路由函数必须包含文档字符串
- 核心逻辑必须添加行内注释
- 前端函数必须添加 JSDoc 注释
- 所有 API 必须校验参数空值和类型
- 数据库操作必须捕获异常
- 外部 API 调用必须设置超时 (30秒)

---

## 9. 实现优先级

### P0 - 必须 (MVP)
1. US-1: 看板首页布局
2. US-2: 统计概览卡片
3. US-3: 批量任务列表
4. US-4: 数据集概览
5. US-5: 学科评估概览
6. US-6: 测试计划CRUD
7. US-8: 侧边栏导航
8. US-9: 数据手动刷新

### P1 - 重要
1. US-7: AI生成测试计划
2. US-10: 自动化调度
3. US-11: 问题热点图
4. US-14: 日报自动生成
5. US-15: 趋势分析
6. US-29: 数据缓存
7. US-30: 异步加载与骨架屏
8. US-32: 智能搜索

### P2 - 期望
1. US-12: AI覆盖率分析
2. US-13: 任务分配
3. US-16: 最佳实践库
4. US-17~28: 分析功能
5. US-31: 大数据量处理
6. US-33: 数据对比增强

### P3 - 可选
1. NFR-34: 代码质量标准 (贯穿开发全程)
