# AI 分析系统架构梳理与优化指南

## 一、系统现状概览

### 1.1 当前架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              数据源层                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  批量评估任务 (batch_tasks/*.json)                                       │   │
│  │  - homework_items: 作业列表                                              │   │
│  │  - evaluation: 评估结果 (errors, questions, total_questions)            │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              分析服务层                                          │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                      │
│  │  AIAnalysisService      │  │  LLMAnalysisService     │                      │
│  │  (ai_analysis_service)  │  │  (llm_analysis_service) │                      │
│  │                         │  │                         │                      │
│  │  - 快速本地统计         │  │  - 聚类分析 Prompt      │                      │
│  │  - 错误样本收集         │  │  - 任务分析 Prompt      │                      │
│  │  - 初步聚类             │  │  - 维度分析 Prompt      │                      │
│  │  - 异常检测             │  │  - 趋势分析 Prompt      │                      │
│  │  - 队列管理             │  │  - 对比分析 Prompt      │                      │
│  │  - 缓存机制             │  │  - 建议生成 Prompt      │                      │
│  └─────────────────────────┘  └─────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              API 路由层 (routes/analysis.py)                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  分析触发: /api/analysis/trigger/<task_id>                               │   │
│  │  快速统计: /api/analysis/quick-stats/<task_id>                           │   │
│  │  聚类分析: /api/analysis/clusters                                        │   │
│  │  样本管理: /api/analysis/samples                                         │   │
│  │  维度分析: /api/analysis/subject, /book, /question-type                  │   │
│  │  趋势分析: /api/analysis/trend                                           │   │
│  │  对比分析: /api/analysis/compare                                         │   │
│  │  异常检测: /api/analysis/anomalies                                       │   │
│  │  优化建议: /api/analysis/suggestions                                     │   │
│  │  可视化:   /api/analysis/chart/sankey, /heatmap, /radar                  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 多维度分析体系现状

| 分析维度 | 实现状态 | 数据来源 | 快速统计 | LLM深度分析 |
|---------|---------|---------|---------|------------|
| 错题数据分析 | ✅ 已实现 | batch_tasks/*.json | ✅ | ⚠️ 部分 |
| 聚类分析 | ✅ 已实现 | 错误样本聚合 | ✅ | ✅ |
| 评估任务分析 | ✅ 已实现 | 单任务统计 | ✅ | ✅ |
| 学科分析 | ✅ 已实现 | 从书名推断 | ✅ | ⚠️ 部分 |
| 书本分析 | ✅ 已实现 | book_name 字段 | ✅ | ⚠️ 部分 |
| 题型分析 | ⚠️ 部分 | error_type 字段 | ✅ | ❌ |
| 时间趋势分析 | ✅ 已实现 | 多任务聚合 | ✅ | ❌ |
| 对比分析 | ✅ 已实现 | 两任务对比 | ✅ | ❌ |

### 1.3 高级分析工具与数据联动现状

| 高级分析工具 | 数据来源 | 实现状态 | 问题 |
|-------------|---------|---------|------|
| 错误样本库 | 错题数据 + 聚类 | ✅ 已实现 | 状态管理在内存，重启丢失 |
| 异常检测 | 聚类 + 任务分析 | ✅ 已实现 | 仅本地检测，无LLM分析 |
| 错误聚类 | 聚类分析 | ✅ 已实现 | 聚类命名依赖LLM |
| 优化建议 | 所有维度综合 | ⚠️ 部分 | 快速建议是硬编码规则 |
| 批次对比 | 对比 + 趋势 | ✅ 已实现 | 无LLM深度分析 |
| 数据下钻 | 学科/书本/题型 | ✅ 已实现 | 下钻层级有限 |

---

## 二、核心问题诊断

### 2.1 数据流问题

```
问题1: 数据源单一
┌─────────────────────────────────────────────────────────────────┐
│  当前: batch_tasks/*.json → 所有分析                            │
│  问题: 每次分析都要重新解析JSON，无持久化的分析结果              │
│  影响: 重复计算、性能浪费、无法跨任务聚合                        │
└─────────────────────────────────────────────────────────────────┘

问题2: 缓存机制不完善
┌─────────────────────────────────────────────────────────────────┐
│  当前: analysis_results 表存储LLM分析结果                        │
│  问题: 快速统计每次都重新计算，未缓存                            │
│  影响: 页面加载慢，重复计算                                      │
└─────────────────────────────────────────────────────────────────┘

问题3: 样本状态管理
┌─────────────────────────────────────────────────────────────────┐
│  当前: error_samples 表存在但未充分利用                          │
│  问题: 样本状态更新后无法反映到原始数据                          │
│  影响: 状态管理与数据分析脱节                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 分析深度问题

```
问题4: LLM分析覆盖不全
┌─────────────────────────────────────────────────────────────────┐
│  已有LLM分析:                                                    │
│  - 聚类分析 (cluster) ✅                                         │
│  - 任务分析 (task) ✅                                            │
│  - 异常分析 (anomaly) ✅                                         │
│                                                                  │
│  缺失LLM分析:                                                    │
│  - 学科维度深度分析 ❌                                           │
│  - 书本维度深度分析 ❌                                           │
│  - 题型维度深度分析 ❌                                           │
│  - 时间趋势深度分析 ❌                                           │
│  - 批次对比深度分析 ❌                                           │
└─────────────────────────────────────────────────────────────────┘

问题5: 优化建议生成
┌─────────────────────────────────────────────────────────────────┐
│  当前: _generate_quick_suggestions() 使用硬编码规则              │
│  问题: 建议不够智能，无法根据具体情况定制                        │
│  期望: 全部由LLM生成，基于所有维度分析结果                       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 前端展示问题

```
问题6: 高级分析工具弹窗
┌─────────────────────────────────────────────────────────────────┐
│  当前: 部分弹窗UI未实现或功能不完整                              │
│  - 错误样本库弹窗: ⚠️ 基础功能                                   │
│  - 异常检测弹窗: ⚠️ 基础功能                                     │
│  - 错误聚类弹窗: ⚠️ 基础功能                                     │
│  - 优化建议弹窗: ⚠️ 基础功能                                     │
│  - 批次对比弹窗: ❌ 未实现                                       │
│  - 数据下钻弹窗: ❌ 未实现                                       │
└─────────────────────────────────────────────────────────────────┘

问题7: 可视化图表
┌─────────────────────────────────────────────────────────────────┐
│  已实现API:                                                      │
│  - 桑基图 /api/analysis/chart/sankey ✅                          │
│  - 热力图 /api/analysis/chart/heatmap ✅                         │
│  - 雷达图 /api/analysis/chart/radar ✅                           │
│                                                                  │
│  前端展示: ❌ 未实现图表渲染                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、优化路线图

### 3.1 优先级矩阵

| 优化项 | 影响范围 | 实现难度 | 优先级 | 预计工时 |
|-------|---------|---------|-------|---------|
| 完善数据持久化 | 高 | 中 | P0 | 2天 |
| 补全LLM维度分析 | 高 | 中 | P0 | 3天 |
| 优化建议LLM化 | 中 | 低 | P1 | 1天 |
| 前端弹窗完善 | 高 | 中 | P1 | 3天 |
| 可视化图表实现 | 中 | 中 | P2 | 2天 |
| 性能优化 | 中 | 高 | P2 | 2天 |

### 3.2 推荐优化顺序

```
阶段1: 数据基础 (1周)
├── 1.1 完善 error_samples 表的数据写入
├── 1.2 完善 error_clusters 表的数据写入
├── 1.3 添加快速统计缓存机制
└── 1.4 修复样本状态管理

阶段2: LLM分析补全 (1周)
├── 2.1 学科维度LLM分析
├── 2.2 书本维度LLM分析
├── 2.3 题型维度LLM分析
├── 2.4 时间趋势LLM分析
├── 2.5 批次对比LLM分析
└── 2.6 优化建议全LLM化

阶段3: 前端完善 (1周)
├── 3.1 批次对比弹窗
├── 3.2 数据下钻弹窗
├── 3.3 可视化图表渲染
└── 3.4 交互优化

阶段4: 性能优化 (3天)
├── 4.1 虚拟滚动
├── 4.2 懒加载
└── 4.3 缓存策略优化
```

---

## 四、详细实现方案

### 4.1 数据持久化优化

#### 4.1.1 错误样本自动入库

```python
# 在 AIAnalysisService._collect_error_samples() 后添加
@classmethod
def _persist_error_samples(cls, task_id: str, error_samples: List[dict]):
    """将错误样本持久化到数据库"""
    for sample in error_samples:
        sample_id = f"{sample.get('homework_id', '')}_{sample.get('question_index', 0)}"
        sql = """
            INSERT INTO error_samples 
            (sample_id, task_id, homework_id, book_name, page_num, question_index,
             subject_id, error_type, ai_answer, expected_answer, base_user, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            ON DUPLICATE KEY UPDATE
            error_type = VALUES(error_type),
            ai_answer = VALUES(ai_answer),
            expected_answer = VALUES(expected_answer)
        """
        AppDatabaseService.execute_insert(sql, (
            sample_id, task_id, sample.get('homework_id'),
            sample.get('book_name'), sample.get('page_num'),
            sample.get('question_index'), sample.get('subject_id'),
            sample.get('error_type'), sample.get('ai_answer'),
            sample.get('expected_answer'), sample.get('base_user', '')
        ))
```

#### 4.1.2 快速统计缓存

```python
# 添加快速统计缓存表
CREATE TABLE IF NOT EXISTS quick_stats_cache (
    task_id VARCHAR(36) PRIMARY KEY,
    stats_data JSON NOT NULL,
    data_hash VARCHAR(64) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

# 修改 get_quick_stats 方法
@classmethod
def get_quick_stats(cls, task_id: str, use_cache: bool = True) -> dict:
    """获取快速统计（支持缓存）"""
    if use_cache:
        cached = cls._get_cached_quick_stats(task_id)
        if cached:
            return cached
    
    # 原有计算逻辑...
    stats = cls._compute_quick_stats(task_id)
    
    # 保存缓存
    cls._save_quick_stats_cache(task_id, stats)
    
    return stats
```

### 4.2 LLM维度分析补全

#### 4.2.1 学科维度LLM分析

```python
# 在 LLMAnalysisService 中添加
SUBJECT_ANALYSIS_PROMPT = """
你是一个专业的 AI 批改系统分析专家。请分析以下学科的批改数据。

## 学科信息
- 学科名称: {subject_name}
- 错误数: {error_count}
- 总题目数: {total}
- 错误率: {error_rate:.2%}

## 错误类型分布
{error_type_distribution}

## 代表性错误样本
{sample_examples}

## 请生成以下分析结果（JSON格式）：
{{
    "subject_summary": "该学科批改情况总结（100字以内）",
    "accuracy_analysis": "准确率分析及影响因素",
    "common_error_patterns": ["常见错误模式1", "模式2"],
    "subject_specific_issues": ["该学科特有问题1", "问题2"],
    "recognition_challenges": "该学科的OCR识别难点",
    "grading_challenges": "该学科的评分难点",
    "improvement_suggestions": ["改进建议1", "建议2"]
}}

只返回 JSON，不要其他内容。
"""

@classmethod
async def analyze_subject(cls, subject_data: dict, task_id: str = None) -> dict:
    """分析学科维度"""
    # 实现类似 analyze_cluster 的逻辑
    pass
```

#### 4.2.2 时间趋势LLM分析

```python
TREND_ANALYSIS_PROMPT = """
你是一个专业的 AI 批改系统分析专家。请分析以下时间趋势数据。

## 时间范围
{time_range}

## 数据点
{data_points}

## 准确率趋势
{accuracy_trend_data}

## 请生成以下分析结果（JSON格式）：
{{
    "trend_summary": "整体趋势总结（50字以内）",
    "accuracy_trend": "improved/declined/stable",
    "error_pattern_evolution": "错误模式的演变分析",
    "improvement_areas": ["改进的方面1", "改进的方面2"],
    "regression_areas": ["退步的方面1", "退步的方面2"],
    "prediction": "基于趋势的预测",
    "recommendations": ["建议1", "建议2"]
}}

只返回 JSON，不要其他内容。
"""
```

### 4.3 前端弹窗实现

#### 4.3.1 批次对比弹窗

```html
<!-- 在 index.html 中添加 -->
<div class="modal" id="batchCompareModal" style="display:none;">
    <div class="modal-content modal-lg">
        <div class="modal-header">
            <h3>批次对比分析</h3>
            <button class="modal-close" onclick="closeBatchCompareModal()">×</button>
        </div>
        <div class="modal-body">
            <!-- 批次选择器 -->
            <div class="compare-selector">
                <div class="selector-item">
                    <label>批次1</label>
                    <select id="batch1Select" onchange="onBatchSelect()"></select>
                </div>
                <div class="selector-vs">VS</div>
                <div class="selector-item">
                    <label>批次2</label>
                    <select id="batch2Select" onchange="onBatchSelect()"></select>
                </div>
            </div>
            
            <!-- 对比结果 -->
            <div id="compareResult" class="compare-result"></div>
        </div>
    </div>
</div>
```

```javascript
// 在 index.js 中添加
async function openBatchCompareModal() {
    document.getElementById('batchCompareModal').style.display = 'flex';
    await loadBatchOptions();
}

async function loadBatchOptions() {
    const tasks = await DashboardAPI.getBatchTasks();
    const select1 = document.getElementById('batch1Select');
    const select2 = document.getElementById('batch2Select');
    
    const options = tasks.map(t => 
        `<option value="${t.task_id}">${t.name} (${t.created_at})</option>`
    ).join('');
    
    select1.innerHTML = options;
    select2.innerHTML = options;
}

async function onBatchSelect() {
    const task1 = document.getElementById('batch1Select').value;
    const task2 = document.getElementById('batch2Select').value;
    
    if (task1 && task2 && task1 !== task2) {
        const result = await DashboardAPI.compareBatches(task1, task2);
        renderCompareResult(result);
    }
}
```

---

## 五、从哪里开始

### 5.1 立即可做（今天）

1. **修复样本状态持久化**
   - 文件: `services/ai_analysis_service.py`
   - 在 `_collect_error_samples` 后调用 `_persist_error_samples`

2. **添加快速统计缓存**
   - 文件: `services/ai_analysis_service.py`
   - 修改 `get_quick_stats` 方法支持缓存

### 5.2 本周目标

1. **补全学科/书本/题型的LLM分析**
   - 文件: `services/llm_analysis_service.py`
   - 添加 `analyze_subject`, `analyze_book`, `analyze_question_type` 方法

2. **优化建议全LLM化**
   - 文件: `routes/analysis.py`
   - 修改 `get_suggestions` 调用 LLM 而非硬编码规则

### 5.3 下周目标

1. **前端弹窗完善**
   - 批次对比弹窗
   - 数据下钻弹窗
   - 可视化图表渲染

---

## 六、关键代码位置索引

| 功能 | 文件 | 关键方法/类 |
|-----|------|-----------|
| 快速统计 | `services/ai_analysis_service.py` | `get_quick_stats()` |
| 错误样本收集 | `services/ai_analysis_service.py` | `_collect_error_samples()` |
| 初步聚类 | `services/ai_analysis_service.py` | `_generate_quick_clusters()` |
| 异常检测 | `services/ai_analysis_service.py` | `detect_anomalies()` |
| 缓存机制 | `services/ai_analysis_service.py` | `get_cached_analysis()` |
| LLM聚类分析 | `services/llm_analysis_service.py` | `analyze_cluster()` |
| LLM任务分析 | `services/llm_analysis_service.py` | `analyze_task()` |
| LLM并行调用 | `services/llm_analysis_service.py` | `parallel_analyze_clusters()` |
| 分析触发API | `routes/analysis.py` | `trigger_analysis()` |
| 维度分析API | `routes/analysis.py` | `get_subject_analysis()` 等 |
| 可视化API | `routes/analysis.py` | `get_sankey_chart()` 等 |

---

## 七、数据库表结构参考

```sql
-- 分析结果缓存表
CREATE TABLE analysis_results (
    result_id VARCHAR(36) PRIMARY KEY,
    analysis_type ENUM('sample', 'cluster', 'task', 'subject', 'book', 'question_type', 'trend', 'compare'),
    target_id VARCHAR(100),
    task_id VARCHAR(36),
    analysis_data JSON,
    data_hash VARCHAR(64),
    status ENUM('pending', 'analyzing', 'completed', 'failed'),
    token_usage INT DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME
);

-- 错误样本表
CREATE TABLE error_samples (
    sample_id VARCHAR(100) PRIMARY KEY,
    task_id VARCHAR(36),
    cluster_id VARCHAR(36),
    homework_id VARCHAR(36),
    book_name VARCHAR(100),
    page_num INT,
    question_index INT,
    subject_id INT,
    error_type VARCHAR(50),
    ai_answer TEXT,
    expected_answer TEXT,
    base_user TEXT,
    status ENUM('pending', 'analyzed', 'in_progress', 'fixed', 'ignored'),
    llm_insight JSON,
    note TEXT,
    created_at DATETIME,
    updated_at DATETIME
);

-- 错误聚类表
CREATE TABLE error_clusters (
    cluster_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36),
    cluster_key VARCHAR(200),
    cluster_name VARCHAR(200),
    cluster_description TEXT,
    root_cause TEXT,
    severity ENUM('critical', 'high', 'medium', 'low'),
    sample_count INT,
    common_fix TEXT,
    pattern_insight TEXT,
    created_at DATETIME,
    updated_at DATETIME
);

-- LLM调用日志表
CREATE TABLE llm_call_logs (
    log_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36),
    analysis_type VARCHAR(50),
    target_id VARCHAR(100),
    model VARCHAR(50),
    prompt_tokens INT,
    completion_tokens INT,
    total_tokens INT,
    duration_ms INT,
    retry_count INT,
    status ENUM('success', 'failed', 'timeout'),
    error_type VARCHAR(50),
    error_message TEXT,
    created_at DATETIME
);
```

---

## 八、总结

当前系统已经具备了多维度分析的基础框架，主要问题集中在：

1. **数据持久化不完整** - 分析结果未充分利用数据库
2. **LLM分析覆盖不全** - 部分维度仍使用硬编码规则
3. **前端展示不完善** - 高级分析工具弹窗和可视化图表未实现

建议从**数据持久化**开始优化，这是后续所有功能的基础。然后逐步补全LLM分析，最后完善前端展示。

按照推荐的优化顺序，预计3周可以完成主要优化工作。


---

## 九、前端优化优先级指南

### 9.1 优先级矩阵

| 优先级 | 功能 | 后端就绪度 | 当前状态 | 预计工时 |
|-------|------|-----------|---------|---------|
| P0 | 错误聚类弹窗 | ✅ 完整 | 简陋实现 | 4h |
| P1 | 错误样本库弹窗 | ✅ 完整 | 展示任务而非样本 | 6h |
| P2 | 数据下钻弹窗 | ✅ 完整 | 基础框架 | 4h |
| P3 | 批次对比弹窗 | ✅ 完整 | 基础功能 | 3h |
| P4 | 优化建议弹窗 | ⚠️ 硬编码 | 需改LLM | 4h |
| P5 | 异常检测弹窗 | ✅ 完整 | 只显示数字 | 3h |

### 9.2 详细优化方案

#### P0: 错误聚类弹窗 (openClusteringModal) - 最高优先级

**选择理由：**
1. 后端数据最完善 - `get_quick_stats()` 已实现完整聚类逻辑
2. API 已就绪 - `/api/analysis/clusters` 和 `/api/analysis/clusters/<cluster_id>`
3. 当前实现太简陋 - 只调用 `/api/dashboard/drilldown?dimension=question_type`
4. 价值最高 - 聚类是所有分析的核心，完善后可联动错误样本、优化建议

**当前代码问题：**
```javascript
// 当前实现 - 错误地调用了 drilldown API
async function loadClusters() {
    const res = await fetch('/api/dashboard/drilldown?dimension=question_type').then(r => r.json());
    // ...只展示简单列表
}
```

**需要改进为：**
```javascript
async function loadClusters() {
    // 1. 获取最近的批量评估任务
    const tasksRes = await fetch('/api/dashboard/batch-tasks?page_size=1').then(r => r.json());
    const taskId = tasksRes.data?.[0]?.task_id;
    
    // 2. 调用正确的聚类 API
    const res = await fetch(`/api/analysis/clusters?task_id=${taskId}`).then(r => r.json());
    
    // 3. 渲染聚类卡片（包含 LLM 分析结果）
    renderClusterCards(res.data);
}

function renderClusterCards(data) {
    const clusters = data.llm_analysis?.clusters || data.quick_stats?.clusters || [];
    // 展示：聚类名称、样本数、严重程度、根因分析、代表性样本
}
```

**需要展示的字段：**
- `cluster_name` - LLM 生成的聚类名称
- `cluster_description` - 聚类描述
- `sample_count` - 样本数量
- `severity` - 严重程度 (critical/high/medium/low)
- `root_cause` - 根因分析
- `common_fix` - 通用修复建议
- `representative_samples` - 代表性样本（最多3个）

**交互功能：**
- 点击聚类卡片展开查看样本列表
- 点击"查看详情"跳转到 `/cluster-detail?task_id=xxx&cluster_id=xxx`
- 支持按严重程度筛选

---

#### P1: 错误样本库弹窗 (openErrorSamplesModal)

**选择理由：**
1. 用户最常用 - 查看具体错误是最基本的需求
2. 当前实现有问题 - 只展示任务列表，没有展示真正的错误样本
3. API 已就绪 - `/api/analysis/samples` 支持完整筛选、分页

**当前代码问题：**
```javascript
// 当前实现 - 展示的是任务列表而非样本
async function loadErrorSamples() {
    const tasksRes = await fetch('/api/dashboard/tasks?page_size=50').then(r => r.json());
    renderErrorSampleList(tasksRes.data?.tasks || []);  // 错误：渲染的是任务
}
```

**需要改进为：**
```javascript
async function loadErrorSamples() {
    // 1. 获取筛选条件
    const errorType = document.getElementById('errorTypeFilter').value;
    const status = document.getElementById('statusFilter').value;
    const taskId = document.getElementById('taskFilter').value;
    
    // 2. 调用样本 API
    let url = `/api/analysis/samples?page=1&page_size=20`;
    if (taskId) url += `&task_id=${taskId}`;
    if (errorType) url += `&error_type=${encodeURIComponent(errorType)}`;
    if (status) url += `&status=${status}`;
    
    const res = await fetch(url).then(r => r.json());
    
    // 3. 渲染样本列表
    renderSampleList(res.data);
}
```

**需要展示的字段：**
- `sample_id` - 样本ID
- `homework_id` - 作业ID
- `book_name` - 书本名称
- `page_num` - 页码
- `question_index` - 题目序号
- `error_type` - 错误类型
- `ai_answer` - AI 答案
- `expected_answer` - 期望答案
- `status` - 状态 (pending/confirmed/fixed/ignored)
- `llm_insight` - LLM 分析结果（如果有）

**交互功能：**
- 按错误类型、状态、任务筛选
- 点击样本查看详情弹窗
- 批量选择 + 批量标记状态
- 支持分页

---

#### P2: 数据下钻弹窗 (openDrilldownModal)

**选择理由：**
1. 框架已有 - 当前实现了基本的维度切换和下钻逻辑
2. API 已就绪 - `/api/analysis/drilldown/<task_id>` 支持多级下钻
3. 需要增强 - 添加 LLM 分析结果、可视化图表

**当前代码问题：**
- 调用的是 `/api/dashboard/drilldown`，应该调用 `/api/analysis/drilldown/<task_id>`
- 没有展示 LLM 分析结果
- 没有可视化图表

**需要改进为：**
```javascript
async function loadDrilldownData() {
    const taskId = advancedToolsData.currentTaskId;
    const dimension = advancedToolsData.drilldownDimension;
    const parentId = advancedToolsData.drilldownParentId;
    
    // 1. 获取下钻数据
    let url = `/api/analysis/drilldown/${taskId}?level=${dimension}`;
    if (parentId) url += `&parent_id=${encodeURIComponent(parentId)}`;
    
    const res = await fetch(url).then(r => r.json());
    
    // 2. 渲染列表
    renderDrilldownList(res.data);
    
    // 3. 加载可视化图表（如果是顶层）
    if (!parentId) {
        loadDrilldownChart(taskId, dimension);
    }
}

async function loadDrilldownChart(taskId, dimension) {
    // 加载雷达图
    const radarRes = await fetch(`/api/analysis/chart/radar?task_id=${taskId}&dimension=${dimension}`).then(r => r.json());
    renderRadarChart(radarRes.data);
}
```

**需要展示的字段：**
- 学科/书本/页码名称
- 错误数、总题目数、错误率
- 是否有子级（has_children）
- LLM 分析摘要（如果有）

**交互功能：**
- 维度切换（学科 → 书本 → 页码）
- 面包屑导航
- 点击下钻到子级
- 雷达图/热力图可视化

---

#### P3: 批次对比弹窗 (openBatchCompareModal)

**选择理由：**
1. 基础功能已有 - 当前实现了任务选择和基本对比
2. API 已就绪 - `/api/analysis/compare`
3. 需要增强 - 添加可视化对比图表

**当前实现基本可用，需要增强：**
```javascript
function renderCompareResult(data) {
    // 当前只展示准确率差值
    // 需要增加：
    // 1. 错误类型变化柱状图
    // 2. 趋势分析（如果选择多个批次）
    // 3. LLM 深度分析结果
}
```

**需要增加的展示：**
- 错误类型变化对比图（柱状图）
- 改进项 / 退步项列表
- LLM 生成的对比分析摘要
- 后续建议

---

#### P4: 优化建议弹窗 (openOptimizationModal)

**选择理由：**
1. 依赖其他分析 - 优化建议需要基于聚类、异常检测等结果
2. 当前是硬编码 - 需要改为调用 LLM 生成

**当前代码问题：**
```javascript
// 当前实现 - 基于 drilldown 数据硬编码生成建议
async function loadSuggestions() {
    const res = await fetch('/api/dashboard/drilldown?dimension=question_type').then(r => r.json());
    // 硬编码生成建议...
}
```

**需要改进为：**
```javascript
async function loadSuggestions() {
    const taskId = advancedToolsData.currentTaskId;
    const res = await fetch(`/api/analysis/suggestions?task_id=${taskId}`).then(r => r.json());
    renderSuggestions(res.data.suggestions);
}

function renderSuggestions(suggestions) {
    // 展示 LLM 生成的建议
    // 包含：标题、描述、优先级、预期效果、实施步骤、Prompt 模板
}
```

**需要展示的字段：**
- `title` - 建议标题
- `category` - 类别（Prompt优化/数据集优化/评分逻辑优化/OCR优化）
- `description` - 详细描述
- `priority` - 优先级（P0/P1/P2）
- `expected_impact` - 预期效果
- `implementation_steps` - 实施步骤
- `prompt_template` - Prompt 修改建议（如果有）

---

#### P5: 异常检测弹窗 (openAnomalyModal)

**选择理由：**
1. API 已就绪 - `/api/analysis/anomalies`
2. 当前展示太简单 - 只显示统计数字

**当前代码问题：**
```javascript
// 当前实现 - 只展示统计数字
async function loadAnomalies() {
    const res = await fetch('/api/dashboard/advanced-tools/stats').then(r => r.json());
    // 只展示 total, unconfirmed, today 三个数字
}
```

**需要改进为：**
```javascript
async function loadAnomalies() {
    const taskId = advancedToolsData.currentTaskId;
    const res = await fetch(`/api/analysis/anomalies?task_id=${taskId}`).then(r => r.json());
    renderAnomalyList(res.data.anomalies);
}
```

**需要展示的字段：**
- `anomaly_type` - 异常类型（inconsistent_grading/continuous_error/batch_missing）
- `severity` - 严重程度
- `base_user_answer` - 学生答案
- `correct_cases` - 正确批改案例
- `incorrect_cases` - 错误批改案例
- `inconsistency_rate` - 不一致率
- `description` - LLM 生成的描述
- `suggested_action` - LLM 生成的建议

---

### 9.3 推荐实施顺序

```
Week 1: 核心功能
├── Day 1-2: 错误聚类弹窗 (P0)
│   ├── 修改 loadClusters() 调用正确 API
│   ├── 实现聚类卡片渲染
│   └── 添加展开/跳转交互
│
├── Day 3-4: 错误样本库弹窗 (P1)
│   ├── 修改 loadErrorSamples() 调用样本 API
│   ├── 实现样本列表渲染
│   ├── 添加筛选功能
│   └── 添加批量操作
│
└── Day 5: 数据下钻弹窗 (P2)
    ├── 修改 loadDrilldownData() 调用正确 API
    └── 添加雷达图可视化

Week 2: 增强功能
├── Day 1: 批次对比弹窗 (P3)
│   └── 添加对比图表和 LLM 分析
│
├── Day 2: 优化建议弹窗 (P4)
│   └── 改为调用 LLM 生成建议
│
└── Day 3: 异常检测弹窗 (P5)
    └── 展示异常详情列表
```

### 9.4 关键代码位置

| 功能 | HTML 位置 | JS 位置 | API 位置 |
|-----|----------|--------|---------|
| 错误聚类 | `index.html:994-1013` | `index.js:1462-1498` | `/api/analysis/clusters` |
| 错误样本 | `index.html:926-967` | `index.js:1348-1414` | `/api/analysis/samples` |
| 数据下钻 | `index.html:1088-1130` | `index.js:1645-1737` | `/api/analysis/drilldown/<task_id>` |
| 批次对比 | `index.html:1034-1087` | `index.js:1543-1642` | `/api/analysis/compare` |
| 优化建议 | `index.html:1014-1033` | `index.js:1501-1540` | `/api/analysis/suggestions` |
| 异常检测 | `index.html:969-993` | `index.js:1417-1459` | `/api/analysis/anomalies` |

### 9.5 起步建议

**今天就可以开始：错误聚类弹窗**

因为：
1. 后端数据最完整，改动风险最小
2. 改动量适中（主要是前端渲染逻辑）
3. 完成后立刻能看到效果
4. 为后续的错误样本、优化建议打好基础
5. 已有 `cluster-detail.html` 详情页可以复用
