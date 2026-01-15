# 批量评估学科功能实现文档

## 功能概述

为批量评估模块添加学科管理功能，包括：
1. 任务创建时选择学科
2. 任务名称自动生成（学科-月/日）
3. 任务列表按学科筛选
4. 任务列表显示学科标签

## 实现细节

### 1. 后端改动

#### routes/batch_evaluation.py

**任务列表接口 (GET /api/batch/tasks)**
- 新增 `subject_id` 查询参数支持学科筛选
- 返回数据包含 `subject_id` 和 `subject_name` 字段

```python
@batch_evaluation_bp.route('/tasks', methods=['GET', 'POST'])
def batch_tasks():
    if request.method == 'GET':
        subject_id = request.args.get('subject_id', type=int)
        # 筛选逻辑
        if subject_id is not None and task_subject_id != subject_id:
            continue
```

**任务创建接口 (POST /api/batch/tasks)**
- 接收 `subject_id` 参数
- 自动生成学科名称
- 自动生成任务名称（格式：学科-月/日）

```python
# 学科映射
subject_map = {
    1: '语文',
    2: '数学',
    3: '英语',
    4: '物理',
    # ...
}

# 自动命名逻辑
if not name:
    now = datetime.now()
    if subject_name:
        name = f'{subject_name}-{now.month}/{now.day}'
    else:
        name = f'批量评估-{now.month}/{now.day}'
```

**任务数据结构**
```json
{
    "task_id": "abc123",
    "name": "数学-1/15",
    "subject_id": 2,
    "subject_name": "数学",
    "status": "pending",
    "homework_items": [...],
    "created_at": "2026-01-15T10:00:00"
}
```

### 2. 前端改动

#### templates/batch-evaluation.html

**任务列表区域添加学科筛选器**
```html
<div class="filter-row" style="margin-bottom: 12px;">
    <select id="taskSubjectFilter" onchange="onTaskSubjectFilterChange()">
        <option value="">全部学科</option>
        <option value="0">英语</option>
        <option value="1">语文</option>
        <option value="2">数学</option>
        <option value="3">物理</option>
    </select>
</div>
```

**新建任务弹窗**
- 任务名称输入框改为可选，placeholder提示自动生成规则
- 学科选择器已存在，保持不变

#### static/js/batch-evaluation.js

**新增函数**

1. `onTaskSubjectFilterChange()` - 任务列表学科筛选
```javascript
function onTaskSubjectFilterChange() {
    const subjectId = document.getElementById('taskSubjectFilter').value;
    loadTaskList(subjectId || null);
}
```

2. `updateAutoTaskName()` - 自动更新任务名称
```javascript
function updateAutoTaskName() {
    const subjectId = document.getElementById('hwSubjectFilter').value;
    const now = new Date();
    const monthDay = `${now.getMonth() + 1}/${now.getDate()}`;
    
    if (subjectId && SUBJECT_NAMES[subjectId]) {
        nameInput.placeholder = `${SUBJECT_NAMES[subjectId]}-${monthDay}`;
    } else {
        nameInput.placeholder = `批量评估-${monthDay}`;
    }
}
```

3. `onSubjectFilterChange()` - 学科筛选变化时触发
```javascript
function onSubjectFilterChange() {
    updateAutoTaskName();
    loadHomeworkTasksForFilter();
    loadHomeworkForTask();
}
```

**修改函数**

1. `loadTaskList(subjectId)` - 支持学科筛选参数
```javascript
async function loadTaskList(subjectId = null) {
    let url = '/api/batch/tasks';
    if (subjectId !== null && subjectId !== '') {
        url += `?subject_id=${subjectId}`;
    }
    // ...
}
```

2. `renderTaskList()` - 显示学科标签
```javascript
container.innerHTML = taskList.map(task => `
    <div class="task-item">
        <div class="task-item-title">
            ${task.subject_name ? `<span class="subject-tag">${task.subject_name}</span>` : ''}
            ${task.name}
            <span class="task-item-status">${getStatusText(task.status)}</span>
        </div>
    </div>
`).join('');
```

3. `createTask()` - 传递学科ID
```javascript
async function createTask() {
    const subjectId = document.getElementById('hwSubjectFilter').value;
    
    const res = await fetch('/api/batch/tasks', {
        method: 'POST',
        body: JSON.stringify({
            name: name,
            subject_id: subjectId ? parseInt(subjectId) : null,
            homework_ids: Array.from(selectedHomeworkIds)
        })
    });
}
```

4. `showCreateTaskModal()` - 初始化任务名称
```javascript
function showCreateTaskModal() {
    document.getElementById('taskNameInput').value = '';
    document.getElementById('taskNameInput').placeholder = '留空则自动生成：学科-月/日';
    // ...
}
```

#### static/css/batch-evaluation.css

**新增样式**

```css
/* 学科标签 */
.subject-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
    background: #f5f5f7;
    color: #1d1d1f;
    border: 1px solid #d2d2d7;
}

/* 任务标题支持flex布局 */
.task-item-title {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}
```

## 使用流程

### 创建任务

1. 点击"新建任务"按钮
2. 选择学科（可选）
3. 任务名称留空（自动生成）或手动输入
4. 选择作业
5. 点击"创建任务"

**自动命名规则：**
- 选择学科：`学科名-月/日`（如：数学-1/15）
- 未选学科：`批量评估-月/日`（如：批量评估-1/15）

### 筛选任务

1. 在任务列表上方的学科下拉框中选择学科
2. 任务列表自动刷新，只显示该学科的任务
3. 选择"全部学科"显示所有任务

### 任务显示

- 任务列表中每个任务显示学科标签（如果有）
- 标签样式：浅灰色背景，黑色文字，圆角边框

## 学科映射

```javascript
const SUBJECT_NAMES = {
    0: '英语',
    1: '语文',
    2: '数学',
    3: '物理'
};
```

后端Python映射：
```python
subject_map = {
    1: '语文',
    2: '数学',
    3: '英语',
    4: '物理',
    5: '化学',
    6: '生物',
    7: '政治',
    8: '历史',
    9: '地理'
}
```

## 数据兼容性

- 旧任务数据没有 `subject_id` 和 `subject_name` 字段，显示时不会报错
- 筛选时，旧任务在"全部学科"中显示
- 不影响现有功能

## 测试要点

1. ✅ 创建任务时不填名称，自动生成正确格式
2. ✅ 创建任务时手动填写名称，使用手动名称
3. ✅ 选择不同学科，自动生成对应学科名称
4. ✅ 任务列表按学科筛选正常工作
5. ✅ 任务列表显示学科标签
6. ✅ 旧任务数据兼容性

## 部署说明

修改的文件：
- `routes/batch_evaluation.py`
- `templates/batch-evaluation.html`
- `static/js/batch-evaluation.js`
- `static/css/batch-evaluation.css`

部署命令：
```bash
.\deploy-quick.ps1
```

或手动重启容器：
```bash
docker restart ai-grading-platform
```
