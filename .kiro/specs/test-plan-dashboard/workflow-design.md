# 测试计划自动化工作流 - 方案设计文档

## 一、概述

### 1.1 背景
当前测试计划功能需要手动执行多个步骤：配置数据集 → 创建批量任务 → 执行评估 → 生成报告。
本方案将这些步骤整合为自动化工作流，通过任务名称关键字自动匹配 zpsmart 数据库中的作业数据。

### 1.2 核心改进
- 测试计划名称与任务关键字分离
- 自动匹配 `zp_homework_publish` 中的作业发布
- 自动检测 AI 批改完成状态
- 工作流步骤可视化展示
- 一键执行完整测试流程

---

## 二、数据库关系分析

### 2.1 zpsmart 数据库表结构

```
zp_homework_publish (作业发布)
├── id (发布ID, VARCHAR(36))
├── content (任务名称，如 "不同手写p97-98")
├── teacher_id (教师ID)
├── class_id (班级ID)
├── subject_id (学科ID)
├── book_id (书本ID)
├── page_region (页码范围，如 "97,98")
├── status (状态: 0=草稿, 1=已发布, 2=已结束)
└── create_time (创建时间)
        │
        ▼ (通过 hw_publish_id 关联)
zp_homework (学生作业)
├── id (作业ID)
├── hw_publish_id (关联发布ID)
├── student_id (学生ID)
├── page_num (具体页码)
├── homework_result (AI批改结果 JSON)
├── data_value (题目数据 JSON)
└── status (状态)
```

### 2.2 关键字段说明

| 字段 | 说明 | 用途 |
|------|------|------|
| `content` | 作业发布名称 | 用于关键字匹配 |
| `page_region` | 页码范围 | 与数据集 pages 匹配 |
| `homework_result` | AI批改结果 | 判断是否批改完成 |
| `hw_publish_id` | 发布ID | 关联学生作业 |


---

## 三、工作流设计

### 3.1 工作流四步骤

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        测试计划自动化工作流                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐       │
│  │ 1.数据集  │────▶│ 2.作业   │────▶│ 3.批量   │────▶│ 4.报告   │       │
│  │  配置    │     │  匹配    │     │  评估    │     │  生成    │       │
│  └──────────┘     └──────────┘     └──────────┘     └──────────┘       │
│       │                │                │                │              │
│       ▼                ▼                ▼                ▼              │
│  选择基准效果      按关键字匹配      自动创建任务      汇总统计数据      │
│  数据集           zp_homework_      逐个评估作业      生成测试报告      │
│                   publish                                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 步骤详细说明

#### 步骤1: 数据集配置
- **输入**: 用户选择已有数据集
- **数据源**: `datasets` 表 + `baseline_effects` 表
- **输出**: 关联的 book_id、pages、基准效果数据
- **状态**: 已完成 / 未完成

#### 步骤2: 作业匹配
- **输入**: 任务关键字 + 数据集的 book_id
- **匹配逻辑**:
  ```sql
  SELECT hp.id, hp.content, hp.book_id, hp.page_region,
         COUNT(h.id) as total_homework,
         SUM(CASE WHEN h.homework_result IS NOT NULL 
             AND h.homework_result != '[]' THEN 1 ELSE 0 END) as graded_count
  FROM zp_homework_publish hp
  LEFT JOIN zp_homework h ON h.hw_publish_id = hp.id
  WHERE hp.content LIKE '%{关键字}%'
    AND hp.book_id = '{数据集book_id}'
  GROUP BY hp.id
  ```
- **输出**: 匹配到的 publish 列表、作业数量、批改进度
- **状态**: 未匹配 / 部分批改 / 全部批改完成

#### 步骤3: 批量评估
- **触发条件**: 作业批改完成度达到阈值（默认100%）
- **执行逻辑**:
  1. 获取所有已批改的 homework_id
  2. 自动创建批量评估任务
  3. 使用数据集基准效果进行对比评估
  4. 计算准确率、错误分布
- **输出**: 批量任务ID、评估结果
- **状态**: 待开始 / 进行中 / 已完成

#### 步骤4: 报告生成
- **触发条件**: 批量评估完成
- **执行逻辑**:
  1. 汇总评估结果
  2. 生成统计报告
  3. 可选：AI 生成分析建议
- **输出**: 测试报告（准确率、错误分布、优化建议）
- **状态**: 待开始 / 已生成


---

## 四、数据模型设计

### 4.1 测试计划表修改 (test_plans)

```sql
ALTER TABLE test_plans ADD COLUMN task_keyword VARCHAR(200) 
    COMMENT '任务名称关键字，用于匹配 zp_homework_publish.content';

ALTER TABLE test_plans ADD COLUMN keyword_match_type ENUM('exact', 'fuzzy', 'regex') 
    DEFAULT 'fuzzy' COMMENT '匹配类型: exact=精确, fuzzy=模糊, regex=正则';

ALTER TABLE test_plans ADD COLUMN matched_publish_ids JSON 
    COMMENT '匹配到的发布ID列表';

ALTER TABLE test_plans ADD COLUMN workflow_status JSON 
    COMMENT '工作流各步骤状态';

ALTER TABLE test_plans ADD COLUMN auto_execute TINYINT(1) DEFAULT 0 
    COMMENT '是否自动执行（批改完成后自动评估）';

ALTER TABLE test_plans ADD COLUMN grading_threshold INT DEFAULT 100 
    COMMENT '批改完成度阈值（百分比），达到后触发评估';
```

### 4.2 工作流状态结构 (workflow_status JSON)

```json
{
  "dataset": {
    "status": "completed",  // not_started | in_progress | completed
    "dataset_id": "b3b0395e",
    "dataset_name": "袁崇焕中学_P97-98_20260123",
    "question_count": 45,
    "completed_at": "2026-01-23T10:30:00"
  },
  "homework_match": {
    "status": "in_progress",
    "matched_publish": [
      {
        "publish_id": "2014529620268871681",
        "content": "不同手写p97-98",
        "total_homework": 42,
        "graded_count": 17,
        "grading_progress": 40.5
      }
    ],
    "total_homework": 42,
    "total_graded": 17,
    "grading_progress": 40.5,
    "last_checked": "2026-01-23T10:35:00"
  },
  "evaluation": {
    "status": "not_started",
    "task_id": null,
    "accuracy": null,
    "started_at": null,
    "completed_at": null
  },
  "report": {
    "status": "not_started",
    "report_id": null,
    "generated_at": null
  }
}
```

### 4.3 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_keyword` | VARCHAR(200) | 任务关键字，与测试计划名称分离 |
| `keyword_match_type` | ENUM | 匹配类型：精确/模糊/正则 |
| `matched_publish_ids` | JSON | 匹配到的 publish ID 数组 |
| `workflow_status` | JSON | 四个步骤的详细状态 |
| `auto_execute` | TINYINT | 是否自动执行评估 |
| `grading_threshold` | INT | 批改完成度阈值 |


---

## 五、API 设计

### 5.1 测试计划 CRUD

```
POST   /api/test-plans                    创建测试计划
GET    /api/test-plans                    获取测试计划列表
GET    /api/test-plans/{plan_id}          获取测试计划详情
PUT    /api/test-plans/{plan_id}          更新测试计划
DELETE /api/test-plans/{plan_id}          删除测试计划
```

### 5.2 工作流操作

```
POST   /api/test-plans/{plan_id}/match-homework    执行作业匹配
GET    /api/test-plans/{plan_id}/match-status      获取匹配状态
POST   /api/test-plans/{plan_id}/refresh-grading   刷新批改状态
POST   /api/test-plans/{plan_id}/start-evaluation  开始批量评估
POST   /api/test-plans/{plan_id}/generate-report   生成测试报告
POST   /api/test-plans/{plan_id}/execute           一键执行完整工作流
```

### 5.3 关键字匹配预览

```
POST /api/test-plans/preview-match
Body: {
  "keyword": "p97-98",
  "match_type": "fuzzy",
  "book_id": "1997848714229166082"  // 可选，从数据集获取
}

Response: {
  "success": true,
  "data": {
    "matched_count": 2,
    "matches": [
      {
        "publish_id": "2014529620268871681",
        "content": "不同手写p97-98",
        "subject_id": 3,
        "book_id": "1997848714229166082",
        "page_region": "97,98",
        "total_homework": 42,
        "graded_count": 17,
        "grading_progress": 40.5,
        "create_time": "2026-01-23T02:44:24"
      }
    ]
  }
}
```

### 5.4 批改状态轮询

```
GET /api/test-plans/{plan_id}/grading-status

Response: {
  "success": true,
  "data": {
    "total_homework": 42,
    "graded_count": 25,
    "grading_progress": 59.5,
    "is_complete": false,
    "threshold": 100,
    "can_start_evaluation": false,
    "last_updated": "2026-01-23T10:40:00"
  }
}
```


---

## 六、UI 设计

### 6.1 测试计划卡片布局

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 测试计划: 物理温度章节测试                                    [编辑] [删除] │
│ 任务关键字: p97-98  |  学科: 物理  |  创建时间: 2026-01-23              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ 工作流进度                                                       │    │
│  │                                                                  │    │
│  │   ┌────────┐      ┌────────┐      ┌────────┐      ┌────────┐   │    │
│  │   │ 数据集  │─────▶│ 作业   │─────▶│  评估  │─────▶│  报告  │   │    │
│  │   │  配置  │      │  匹配  │      │       │      │       │   │    │
│  │   │   ✓   │      │   ○   │      │   ○   │      │   ○   │   │    │
│  │   └────────┘      └────────┘      └────────┘      └────────┘   │    │
│  │                                                                  │    │
│  │   数据集: 袁崇焕中学_P97-98 (45题)                               │    │
│  │   匹配: "不同手写p97-98" | 批改进度: 17/42 (40%)                 │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ 统计概览                                                         │    │
│  │   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐               │    │
│  │   │ 作业数  │  │ 批改率  │  │ 准确率  │  │  耗时  │               │    │
│  │   │  42    │  │  40%   │  │   --   │  │   --   │               │    │
│  │   └────────┘  └────────┘  └────────┘  └────────┘               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─ 步骤详情 ──────────────────────────────────────────────── [展开] ┐  │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│                                    [刷新状态] [开始执行] [查看详情]        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 步骤详情展开视图

```
┌─ 步骤详情 ──────────────────────────────────────────────────── [收起] ┐
│                                                                        │
│  1. 数据集配置                                          [已完成] ✓     │
│     ├─ 数据集: 袁崇焕中学_P97-98_20260123                             │
│     ├─ 题目数: 45 道                                                  │
│     ├─ 页码范围: P97-98                                               │
│     └─ 学科: 物理                                                     │
│                                                                        │
│  2. 作业匹配                                            [进行中] ○     │
│     ├─ 关键字: p97-98 (模糊匹配)                                      │
│     ├─ 匹配结果:                                                      │
│     │   └─ "不同手写p97-98" (publish_id: 2014529620268871681)        │
│     ├─ 作业数量: 42 份                                                │
│     ├─ AI批改进度: 17/42 (40%)                                        │
│     │   ████████░░░░░░░░░░░░ 40%                                      │
│     └─ 最后检查: 2026-01-23 10:35                    [刷新状态]        │
│                                                                        │
│  3. 批量评估                                            [待开始] ○     │
│     └─ 等待作业批改完成后自动开始                                      │
│        (当前进度 40%，需达到 100%)                                     │
│                                                                        │
│  4. 报告生成                                            [待开始] ○     │
│     └─ 评估完成后自动生成                                              │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### 6.3 状态标识说明

| 状态 | 图标 | 颜色 | 说明 |
|------|------|------|------|
| 已完成 | ✓ | 绿色 #1e7e34 | 步骤已成功完成 |
| 进行中 | ○ (动画) | 蓝色 #1565c0 | 步骤正在执行 |
| 待开始 | ○ | 灰色 #86868b | 等待前置步骤完成 |
| 失败 | ✗ | 红色 #d73a49 | 步骤执行失败 |


---

## 七、创建测试计划流程

### 7.1 创建表单设计

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 创建测试计划                                                      [×]   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  测试计划名称 *                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ 物理温度章节测试                                                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  任务关键字 *                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ p97-98                                                          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│  提示: 用于匹配 zp_homework_publish 中的作业名称                         │
│                                                                          │
│  匹配方式                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ ○ 精确匹配  ● 模糊匹配  ○ 正则表达式                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  选择数据集 *                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ 袁崇焕中学_P97-98_20260123 (物理, 45题)                    [▼]  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ [预览匹配结果]                                                   │    │
│  │                                                                  │    │
│  │ 匹配到 1 条作业发布:                                             │    │
│  │ ┌────────────────────────────────────────────────────────────┐  │    │
│  │ │ ☑ 不同手写p97-98                                           │  │    │
│  │ │   发布时间: 2026-01-23 02:44 | 作业数: 42 | 批改: 17/42    │  │    │
│  │ └────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  高级设置                                                    [展开 ▼]   │
│                                                                          │
│                                              [取消]  [创建测试计划]      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 高级设置展开

```
│  高级设置                                                    [收起 ▲]   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                                                                  │    │
│  │  批改完成度阈值                                                  │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │ 100 %                                               [▼]  │   │    │
│  │  └──────────────────────────────────────────────────────────┘   │    │
│  │  提示: 达到此阈值后可开始评估                                    │    │
│  │                                                                  │    │
│  │  ☐ 批改完成后自动执行评估                                        │    │
│  │                                                                  │    │
│  │  计划描述                                                        │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │                                                          │   │    │
│  │  │                                                          │   │    │
│  │  └──────────────────────────────────────────────────────────┘   │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
```


---

## 八、关键字匹配策略

### 8.1 三种匹配模式

| 模式 | SQL 实现 | 示例 |
|------|----------|------|
| 精确匹配 | `content = '{keyword}'` | "p97-98" 只匹配 "p97-98" |
| 模糊匹配 | `content LIKE '%{keyword}%'` | "p97" 匹配 "不同手写p97-98" |
| 正则表达式 | `content REGEXP '{keyword}'` | "p9[7-8]" 匹配 "p97"、"p98" |

### 8.2 匹配优先级

1. 优先匹配 `book_id` 相同的发布（从数据集获取）
2. 其次匹配 `subject_id` 相同的发布
3. 最后按 `create_time` 倒序排列

### 8.3 匹配结果确认

- 匹配结果需要用户确认后才会保存
- 支持多选/取消选择匹配到的发布
- 显示每个发布的详细信息供用户判断

### 8.4 数据集与作业的页码匹配

数据集的 `book_id` + `pages` 需要与 publish 的 `book_id` + `page_region` 匹配。

**page_region 格式解析:**
```python
def parse_page_region(page_region: str) -> list:
    """
    解析 page_region 字符串为页码列表
    
    示例:
    - "97,98" -> [97, 98]
    - "97-100" -> [97, 98, 99, 100]
    - "97,99,101" -> [97, 99, 101]
    - "97-99,101" -> [97, 98, 99, 101]
    """
    pages = []
    if not page_region:
        return pages
    
    parts = page_region.replace('～', '-').replace('~', '-').split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            # 范围格式: "97-100"
            start, end = part.split('-')
            pages.extend(range(int(start), int(end) + 1))
        else:
            # 单个页码
            pages.append(int(part))
    
    return sorted(set(pages))
```

**匹配逻辑:**
```python
def check_page_match(dataset_pages: list, page_region: str) -> bool:
    """
    检查数据集页码与 publish 页码是否匹配
    
    匹配规则:
    1. 完全匹配: dataset_pages == publish_pages
    2. 包含匹配: publish_pages 是 dataset_pages 的子集
    3. 交集匹配: 有任意页码重叠
    """
    publish_pages = parse_page_region(page_region)
    
    # 检查是否有交集
    intersection = set(dataset_pages) & set(publish_pages)
    return len(intersection) > 0
```

**匹配优先级:**
1. book_id 必须完全匹配
2. 页码有交集即可匹配
3. 页码完全匹配的优先级更高

---

## 九、批改状态检测

### 9.1 检测逻辑

```python
def check_grading_status(publish_ids: list) -> dict:
    """
    检查作业批改状态
    
    Returns:
        {
            "total_homework": 42,
            "graded_count": 17,
            "grading_progress": 40.5,
            "is_complete": False
        }
    """
    sql = """
    SELECT 
        COUNT(*) as total,
        SUM(CASE 
            WHEN homework_result IS NOT NULL 
            AND homework_result != '' 
            AND homework_result != '[]' 
            THEN 1 ELSE 0 
        END) as graded
    FROM zp_homework
    WHERE hw_publish_id IN ({})
    """.format(','.join(['%s'] * len(publish_ids)))
    
    result = execute_query(sql, publish_ids)
    total = result['total']
    graded = result['graded']
    
    return {
        "total_homework": total,
        "graded_count": graded,
        "grading_progress": round(graded / total * 100, 1) if total > 0 else 0,
        "is_complete": graded >= total
    }
```

### 9.2 轮询策略

- 前端定时轮询（默认 30 秒）
- 用户可手动点击"刷新状态"
- 批改完成后停止轮询
- 支持配置轮询间隔

### 9.3 完成度阈值

- 默认 100%（全部批改完成）
- 可配置为 80%、90% 等
- 达到阈值后显示"可开始评估"按钮


---

## 十、自动评估流程

### 10.1 触发条件

1. 批改完成度达到阈值
2. 用户点击"开始执行"或开启了"自动执行"

### 10.2 执行步骤

```python
def execute_evaluation(plan_id: str) -> dict:
    """
    执行批量评估
    
    1. 获取测试计划信息
    2. 获取匹配的 homework_id 列表
    3. 创建批量评估任务
    4. 执行评估
    5. 更新工作流状态
    """
    # 1. 获取计划信息
    plan = get_test_plan(plan_id)
    dataset_id = plan['workflow_status']['dataset']['dataset_id']
    publish_ids = plan['matched_publish_ids']
    
    # 2. 获取已批改的作业
    homework_ids = get_graded_homework_ids(publish_ids)
    
    # 3. 创建批量任务
    task_id = create_batch_task({
        'name': f"自动评估-{plan['name']}",
        'homework_ids': homework_ids,
        'dataset_id': dataset_id,
        'plan_id': plan_id
    })
    
    # 4. 执行评估（复用现有逻辑）
    evaluate_batch_task(task_id)
    
    # 5. 更新状态
    update_workflow_status(plan_id, 'evaluation', {
        'status': 'completed',
        'task_id': task_id,
        'accuracy': get_task_accuracy(task_id),
        'completed_at': datetime.now().isoformat()
    })
    
    return {'success': True, 'task_id': task_id}
```

### 10.3 与现有批量评估的集成

- 复用 `routes/batch_evaluation.py` 中的评估逻辑
- 复用 `services/storage_service.py` 中的数据集匹配
- 自动关联 `test_plan_tasks` 表

---

## 十一、报告生成

### 11.1 报告内容

```json
{
  "plan_name": "物理温度章节测试",
  "dataset_name": "袁崇焕中学_P97-98_20260123",
  "execution_time": "2026-01-23T11:00:00",
  "summary": {
    "total_homework": 42,
    "total_questions": 189,
    "correct_count": 156,
    "accuracy": 82.5,
    "grading_time_avg": "2.3s"
  },
  "error_distribution": {
    "识别错误-判断错误": 15,
    "识别正确-判断错误": 8,
    "缺失题目": 5,
    "AI识别幻觉": 5
  },
  "by_question_type": {
    "选择题": {"total": 80, "correct": 75, "accuracy": 93.8},
    "填空题": {"total": 60, "correct": 48, "accuracy": 80.0},
    "主观题": {"total": 49, "correct": 33, "accuracy": 67.3}
  },
  "recommendations": [
    "主观题准确率较低，建议优化识别模型",
    "填空题存在较多识别错误，建议检查手写识别"
  ]
}
```

### 11.2 报告展示

- 在测试计划详情页展示
- 支持导出 Excel/PDF
- 支持与历史报告对比


---

## 十二、可行性评估

### 12.1 技术可行性

| 方面 | 可行性 | 说明 |
|------|--------|------|
| 数据关联 | ✅ 高 | publish → homework 关系清晰，通过 hw_publish_id 关联 |
| 任务匹配 | ✅ 高 | content 字段支持模糊搜索，MySQL LIKE/REGEXP 支持 |
| 批改状态 | ✅ 高 | homework_result 字段可判断是否批改完成 |
| 基准效果 | ✅ 高 | 复用现有 datasets + baseline_effects 表 |
| 自动评估 | ✅ 高 | 复用现有批量评估逻辑 |
| 跨库查询 | ⚠️ 中 | 需要同时访问 zpsmart 和本地数据库 |

### 12.2 需要注意的问题

1. **跨数据库访问**
   - zpsmart 数据库（作业数据）和本地数据库（测试计划）需要分别连接
   - 建议使用 `AppDatabaseService` 封装跨库查询

2. **数据一致性**
   - book_id 需要在两个系统中保持一致
   - page_region 格式需要与数据集 pages 匹配

3. **性能考虑**
   - 大量作业时，批改状态查询可能较慢
   - 建议添加索引：`zp_homework(hw_publish_id, homework_result)`

4. **权限控制**
   - zpsmart 数据库只读访问
   - 本地数据库读写访问

### 12.3 优化建议

1. **缓存匹配结果**
   - 匹配到的 publish_ids 保存到 test_plans 表
   - 避免重复查询

2. **增量检测**
   - 只检查未批改的作业状态
   - 减少查询数据量

3. **异步执行**
   - 评估过程放入后台队列
   - 避免阻塞用户操作

4. **错误重试**
   - 评估失败支持重试
   - 记录失败原因


---

## 十三、实现计划

### 13.1 阶段一：基础框架（2天）

- [ ] 修改 test_plans 表结构，添加工作流相关字段
- [ ] 实现测试计划 CRUD API
- [ ] 实现关键字匹配预览 API
- [ ] 创建测试计划表单 UI

### 13.2 阶段二：工作流核心（3天）

- [ ] 实现作业匹配逻辑（精确/模糊/正则）
- [ ] 实现批改状态检测 API
- [ ] 实现工作流状态管理
- [ ] 工作流进度卡片 UI

### 13.3 阶段三：自动评估（2天）

- [ ] 集成现有批量评估逻辑
- [ ] 实现自动触发评估
- [ ] 实现报告生成
- [ ] 步骤详情展开 UI

### 13.4 阶段四：优化完善（1天）

- [ ] 轮询状态刷新
- [ ] 错误处理和重试
- [ ] 性能优化
- [ ] 测试和修复

---

## 十四、总结

本方案将测试计划改造为自动化工作流，核心改进：

1. **测试计划名称与任务关键字分离** - 更灵活的匹配策略
2. **自动匹配作业发布** - 通过关键字匹配 zp_homework_publish
3. **实时批改状态检测** - 轮询检查 homework_result
4. **一键执行完整流程** - 数据集配置 → 作业匹配 → 批量评估 → 报告生成
5. **可视化工作流进度** - 四步骤状态展示，步骤详情可展开

技术上完全可行，复用现有批量评估逻辑，主要工作在于：
- 新增工作流状态管理
- 实现跨库查询（zpsmart）
- 优化 UI 展示

预计开发周期：8 个工作日
