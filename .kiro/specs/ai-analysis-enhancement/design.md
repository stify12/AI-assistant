# Design Document

## Overview

本设计文档详细说明 AI 智能分析功能增强优化的技术实现方案。系统通过调用 DeepSeek V3.2 大模型对批量评估数据进行多维度深度分析，生成有价值、可读性强的分析数据，作为测试看板高级分析工具的数据底座。

**核心设计原则：**
1. **全程 LLM 分析**：所有分析结果由 DeepSeek V3.2 生成，不使用硬编码规则
2. **聚类优先**：先对错误样本聚类，再按聚类调用 LLM（减少 API 调用）
3. **并行处理**：LLM 请求并行执行，最大并发数 10
4. **两级分析**：快速本地统计 + LLM 深度分析，渐进式展示
5. **结果缓存**：基于数据哈希的缓存策略，避免重复分析

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Flask Application                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐     │
│  │ analysis       │  │ dashboard      │  │ automation     │  │ batch_eval     │     │
│  │ routes         │  │ routes         │  │ routes         │  │ routes         │     │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘     │
│          │                   │                   │                   │              │
│          ▼                   ▼                   ▼                   ▼              │
│  ┌──────────────────────────────────────────────────────────────────────────┐       │
│  │                          Service Layer                                    │       │
│  │                                                                           │       │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────┐   │       │
│  │  │ AIAnalysisService   │  │ LLMAnalysisService  │  │ LLMService      │   │       │
│  │  │ (Enhanced)          │  │ (New)               │  │                 │   │       │
│  │  │                     │  │                     │  │ - DeepSeek V3.2 │   │       │
│  │  │ - trigger_analysis  │  │ - analyze_cluster   │  │ - call_deepseek │   │       │
│  │  │ - quick_stats       │  │ - analyze_task      │  │ - parallel_call │   │       │
│  │  │ - get_cached_result │  │ - analyze_dimension │  │                 │   │       │
│  │  │ - drill_down        │  │ - generate_suggest  │  │                 │   │       │
│  │  └──────────┬──────────┘  └──────────┬──────────┘  └────────┬────────┘   │       │
│  │             │                        │                      │            │       │
│  │             ▼                        ▼                      ▼            │       │
│  │  ┌──────────────────────────────────────────────────────────────────┐   │       │
│  │  │                    Analysis Queue (内存队列)                      │   │       │
│  │  │  - 任务优先级队列 (高/中/低)                                      │   │       │
│  │  │  - 并发控制 (max_concurrent=10)                                   │   │       │
│  │  │  - 进度追踪 (0-100%)                                              │   │       │
│  │  │  - 错误日志记录                                                   │   │       │
│  │  └──────────────────────────────────────────────────────────────────┘   │       │
│  │                                                                           │       │
│  └───────────────────────────────────────────────────────────────────────────┘       │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                  Data Storage                                         │
│                                                                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  MySQL          │  │  JSON Files     │  │  Config         │  │  Cache          │  │
│  │                 │  │                 │  │                 │  │                 │  │
│  │ - analysis_     │  │ - batch_tasks/  │  │ - automation_   │  │ - 分析结果缓存  │  │
│  │   results       │  │   *.json        │  │   config.json   │  │ - 数据哈希映射  │  │
│  │ - error_samples │  │                 │  │                 │  │                 │  │
│  │ - error_clusters│  │                 │  │                 │  │                 │  │
│  │ - llm_call_logs │  │                 │  │                 │  │                 │  │
│  │ - anomalies     │  │                 │  │                 │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. AI 分析服务增强 (ai_analysis_service.py)

```python
class AIAnalysisService:
    """AI 数据分析服务（增强版）"""
    
    # 分析队列配置
    _queue: List[dict] = []  # [{task_id, priority, created_at}]
    _running: Dict[str, dict] = {}  # {task_id: {progress, started_at, step}}
    _max_concurrent: int = 10  # 最大并发数
    _lock = threading.Lock()
    
    @classmethod
    def trigger_analysis(cls, task_id: str, priority: str = 'medium') -> dict:
        """
        触发任务分析
        
        Args:
            task_id: 批量评估任务ID
            priority: 优先级 high|medium|low
            
        Returns:
            dict: {queued: bool, position: int, job_id: str, message: str}
        """
        pass
    
    @classmethod
    def get_quick_stats(cls, task_id: str) -> dict:
        """
        获取快速本地统计（毫秒级响应）
        
        Returns:
            dict: {
                total_errors: int,
                error_rate: float,
                error_type_distribution: {...},
                subject_distribution: {...},
                book_distribution: {...},
                clusters: [{cluster_key, count, samples}]
            }
        """
        pass
    
    @classmethod
    def get_cached_analysis(cls, task_id: str, analysis_type: str, target_id: str = None) -> dict:
        """
        获取缓存的分析结果
        
        Args:
            task_id: 任务ID
            analysis_type: sample|cluster|task|subject|book|question_type|trend|compare
            target_id: 目标ID（如聚类ID、学科名等）
            
        Returns:
            dict: {
                quick_stats: {...},
                llm_analysis: {...} or None,
                analysis_status: pending|analyzing|completed,
                data_hash: str,
                updated_at: str
            }
        """
        pass
    
    @classmethod
    def detect_anomalies(cls, task_id: str) -> List[dict]:
        """
        检测异常模式（重点：批改不一致）
        
        Returns:
            list: [{
                anomaly_id: str,
                anomaly_type: str,  # inconsistent_grading|recognition_unstable|...
                severity: str,  # critical|high|medium|low
                base_user_answer: str,
                correct_cases: [...],
                incorrect_cases: [...],
                inconsistency_rate: float,
                description: str,  # LLM 生成
                suggested_action: str  # LLM 生成
            }]
        """
        pass
    
    @classmethod
    def get_analysis_queue_status(cls) -> dict:
        """
        获取分析队列状态
        
        Returns:
            dict: {
                waiting: int,
                running: [{task_id, progress, step, started_at}],
                recent_completed: [{task_id, completed_at, duration}],
                recent_failed: [{task_id, error, failed_at}]
            }
        """
        pass
    
    @classmethod
    def cancel_analysis(cls, job_id: str) -> bool:
        """取消排队中的分析任务"""
        pass
```

### 2. LLM 分析服务（新增）(llm_analysis_service.py)

```python
class LLMAnalysisService:
    """LLM 深度分析服务"""
    
    MODEL = 'deepseek-v3.2'
    MAX_CONCURRENT = 10
    DEFAULT_TIMEOUT = 60
    MAX_RETRIES = 3
    
    @classmethod
    async def analyze_cluster(cls, cluster_data: dict) -> dict:
        """
        分析单个聚类
        
        Args:
            cluster_data: {
                cluster_key: str,
                samples: [{homework_id, error_type, ai_answer, expected_answer, ...}],
                sample_count: int
            }
            
        Returns:
            dict: {
                cluster_id: str,
                cluster_name: str,  # LLM 生成的可读名称
                cluster_description: str,
                root_cause: str,
                severity: str,
                common_fix: str,
                pattern_insight: str,
                representative_samples: [...]
            }
        """
        pass
    
    @classmethod
    async def analyze_task(cls, task_id: str, clusters: List[dict], quick_stats: dict) -> dict:
        """
        分析任务整体
        
        Returns:
            dict: {
                task_summary: str,
                accuracy_analysis: str,
                main_issues: [...],
                error_distribution: str,
                risk_assessment: str,
                improvement_priority: [...],
                actionable_suggestions: [...]
            }
        """
        pass
    
    @classmethod
    async def analyze_dimension(cls, dimension: str, data: dict) -> dict:
        """
        分析特定维度（学科/书本/题型）
        
        Args:
            dimension: subject|book|question_type
            data: 该维度的统计数据
            
        Returns:
            dict: 维度分析结果
        """
        pass
    
    @classmethod
    async def analyze_trend(cls, trend_data: List[dict], time_range: str) -> dict:
        """分析时间趋势"""
        pass
    
    @classmethod
    async def compare_batches(cls, batch1_data: dict, batch2_data: dict) -> dict:
        """对比两个批次"""
        pass
    
    @classmethod
    async def generate_suggestions(cls, all_analysis: dict) -> List[dict]:
        """
        生成优化建议
        
        Returns:
            list: [{
                suggestion_id: str,
                title: str,
                category: str,
                description: str,
                priority: str,
                expected_impact: str,
                implementation_steps: [...],
                related_clusters: [...],
                prompt_template: str or None
            }]
        """
        pass
    
    @classmethod
    async def parallel_analyze(cls, tasks: List[Callable]) -> List[dict]:
        """
        并行执行多个分析任务
        
        Args:
            tasks: 分析任务列表
            
        Returns:
            list: 分析结果列表
        """
        pass
```

### 3. LLM 服务扩展 (llm_service.py)

```python
class LLMService:
    """LLM 服务类（扩展并行调用）"""
    
    @staticmethod
    async def call_deepseek_async(
        prompt: str, 
        system_prompt: str = None,
        model: str = 'deepseek-v3.2',
        temperature: float = 0.2,
        timeout: int = 60
    ) -> dict:
        """异步调用 DeepSeek"""
        pass
    
    @staticmethod
    async def parallel_call(
        prompts: List[dict],  # [{prompt, system_prompt, ...}]
        max_concurrent: int = 10
    ) -> List[dict]:
        """
        并行调用 LLM
        
        Args:
            prompts: 提示词列表
            max_concurrent: 最大并发数
            
        Returns:
            list: [{success: bool, content: str, error: str, duration: float}]
        """
        pass
```



### 4. API 接口设计

#### 4.1 分析触发与状态 API

**POST /api/analysis/trigger/{task_id}**
```json
// Request
{
    "priority": "high"  // high|medium|low, 默认 medium
}
// Response
{
    "success": true,
    "data": {
        "queued": true,
        "job_id": "job_abc123",
        "position": 1,
        "message": "分析任务已加入队列"
    }
}
```

**GET /api/analysis/queue**
```json
// Response
{
    "success": true,
    "data": {
        "waiting": 3,
        "running": [
            {
                "task_id": "xxx",
                "job_id": "job_abc",
                "progress": 45,
                "step": "正在分析聚类 3/5...",
                "started_at": "2026-01-25 10:00:00"
            }
        ],
        "recent_completed": [...],
        "recent_failed": [...]
    }
}
```

**DELETE /api/analysis/queue/{job_id}**
```json
// Response
{
    "success": true,
    "message": "任务已取消"
}
```

#### 4.2 分析结果 API

**GET /api/analysis/task/{task_id}**
```json
// Response
{
    "success": true,
    "data": {
        "quick_stats": {
            "total_errors": 156,
            "total_questions": 1200,
            "error_rate": 0.13,
            "error_type_distribution": {
                "识别错误-判断错误": 45,
                "识别正确-判断错误": 38,
                "缺失题目": 23
            },
            "subject_distribution": {...},
            "book_distribution": {...}
        },
        "llm_analysis": {
            "task_summary": "本次批量评估共处理 1200 道题目...",
            "accuracy_analysis": "整体准确率 87%，其中物理学科...",
            "main_issues": [
                {"issue": "物理力学题漏批率高", "count": 45, "severity": "high"},
                {"issue": "化学方程式配平误判", "count": 23, "severity": "medium"}
            ],
            "risk_assessment": "当前存在中等风险...",
            "improvement_priority": ["优化手写体识别", "完善评分逻辑"],
            "actionable_suggestions": [...]
        },
        "analysis_status": "completed",
        "updated_at": "2026-01-25 10:30:00"
    }
}
```

**GET /api/analysis/clusters?task_id={task_id}**
```json
// Response
{
    "success": true,
    "data": {
        "quick_stats": {
            "total_clusters": 12,
            "clusters": [
                {
                    "cluster_key": "识别错误_数学_10-20",
                    "sample_count": 23,
                    "error_type": "识别错误-判断错误",
                    "book_name": "数学八上",
                    "page_range": "10-20"
                }
            ]
        },
        "llm_analysis": {
            "clusters": [
                {
                    "cluster_id": "c1",
                    "cluster_name": "数学手写体识别问题",
                    "cluster_description": "学生手写数字和符号识别不准确...",
                    "root_cause": "手写体变体多，OCR 模型覆盖不足",
                    "severity": "high",
                    "sample_count": 23,
                    "common_fix": "在 Prompt 中增加手写体容错说明",
                    "pattern_insight": "主要集中在分数、根号等复杂符号",
                    "representative_samples": [...]
                }
            ],
            "top_5_clusters": ["c1", "c3", "c5", "c2", "c8"]
        },
        "analysis_status": "completed"
    }
}
```

**GET /api/analysis/clusters/{cluster_id}**
```json
// Response
{
    "success": true,
    "data": {
        "cluster_id": "c1",
        "cluster_name": "数学手写体识别问题",
        "cluster_description": "...",
        "root_cause": "...",
        "severity": "high",
        "sample_count": 23,
        "common_fix": "...",
        "pattern_insight": "...",
        "samples": [
            {
                "sample_id": "s1",
                "homework_id": "hw123",
                "book_name": "数学八上",
                "page_num": 15,
                "question_index": 3,
                "error_type": "识别错误-判断错误",
                "ai_answer": "...",
                "expected_answer": "...",
                "status": "pending",
                "llm_insight": {...}
            }
        ]
    }
}
```

#### 4.3 维度分析 API

**GET /api/analysis/subject?task_id={task_id}**
```json
// Response
{
    "success": true,
    "data": {
        "quick_stats": {
            "subjects": [
                {"subject_id": 2, "name": "数学", "error_count": 56, "total": 400, "error_rate": 0.14},
                {"subject_id": 3, "name": "物理", "error_count": 45, "total": 300, "error_rate": 0.15}
            ]
        },
        "llm_analysis": {
            "subjects": [
                {
                    "subject_name": "数学",
                    "subject_summary": "数学学科整体准确率 86%...",
                    "common_error_patterns": ["手写数字识别", "公式符号识别"],
                    "subject_specific_issues": ["分数线识别困难", "根号内容提取不准"],
                    "cross_book_comparison": "八上比八下错误率高 5%...",
                    "improvement_suggestions": ["增加数学符号训练数据"]
                }
            ]
        },
        "analysis_status": "completed"
    }
}
```

**GET /api/analysis/book?task_id={task_id}&subject={subject_id}**
**GET /api/analysis/question-type?task_id={task_id}**
**GET /api/analysis/trend?task_ids={id1,id2,...}&time_range=7d**
**GET /api/analysis/compare?task_id_1={id1}&task_id_2={id2}**

#### 4.4 异常检测 API

**GET /api/analysis/anomalies?task_id={task_id}**
```json
// Response
{
    "success": true,
    "data": {
        "anomalies": [
            {
                "anomaly_id": "a1",
                "anomaly_type": "inconsistent_grading",
                "severity": "critical",
                "base_user_answer": "3.14",
                "correct_cases": [
                    {"homework_id": "hw1", "ai_result": "correct"},
                    {"homework_id": "hw3", "ai_result": "correct"}
                ],
                "incorrect_cases": [
                    {"homework_id": "hw2", "ai_result": "incorrect"}
                ],
                "inconsistency_rate": 0.33,
                "description": "同一学生答案 '3.14' 在 3 份作业中出现，其中 1 份被错误判定...",
                "suggested_action": "检查评分 Prompt 对数值答案的处理逻辑..."
            }
        ],
        "summary": {
            "critical_count": 2,
            "high_count": 5,
            "medium_count": 8
        }
    }
}
```

#### 4.5 优化建议 API

**GET /api/analysis/suggestions?task_id={task_id}**
```json
// Response
{
    "success": true,
    "data": {
        "suggestions": [
            {
                "suggestion_id": "s1",
                "title": "优化手写体识别容错",
                "category": "Prompt优化",
                "description": "在评分 Prompt 中增加对手写体的容错处理...",
                "priority": "P0",
                "expected_impact": "预计可减少 30% 的识别错误",
                "implementation_steps": [
                    "在 Prompt 中添加手写体容错说明",
                    "增加常见书写变体的示例",
                    "测试验证效果"
                ],
                "related_clusters": ["c1", "c3"],
                "prompt_template": "对于手写体答案，请考虑以下常见变体：..."
            }
        ]
    }
}
```

#### 4.6 样本管理 API

**GET /api/analysis/samples?task_id={task_id}&status=pending&page=1&page_size=20**
**GET /api/analysis/samples/{sample_id}**
**PUT /api/analysis/samples/{sample_id}/status**
```json
// Request
{
    "status": "fixed",
    "note": "已通过 Prompt 优化修复"
}
```
**PUT /api/analysis/samples/batch-status**
```json
// Request
{
    "sample_ids": ["s1", "s2", "s3"],
    "status": "ignored"
}
```

#### 4.7 错误日志 API

**GET /api/analysis/logs?days=7&type=timeout**
```json
// Response
{
    "success": true,
    "data": {
        "logs": [
            {
                "log_id": "log1",
                "task_id": "task123",
                "error_type": "timeout",
                "error_message": "LLM 请求超时（60s）",
                "retry_count": 3,
                "final_status": "failed",
                "created_at": "2026-01-25 10:00:00"
            }
        ],
        "summary": {
            "total": 15,
            "by_type": {
                "timeout": 8,
                "api_error": 5,
                "parse_error": 2
            }
        }
    }
}
```


## Data Models

### 1. 数据库表结构

#### 1.1 分析结果表 (analysis_results)

```sql
CREATE TABLE IF NOT EXISTS analysis_results (
    result_id VARCHAR(36) PRIMARY KEY,
    analysis_type ENUM('sample', 'cluster', 'task', 'subject', 'book', 'question_type', 'trend', 'compare') NOT NULL,
    target_id VARCHAR(100) NOT NULL COMMENT '分析目标ID（task_id/cluster_id/subject_name等）',
    task_id VARCHAR(36) COMMENT '关联的批量评估任务ID',
    analysis_data JSON NOT NULL COMMENT 'LLM 分析结果（JSON格式）',
    data_hash VARCHAR(64) NOT NULL COMMENT '源数据哈希值（用于缓存判断）',
    status ENUM('pending', 'analyzing', 'completed', 'failed') DEFAULT 'pending',
    token_usage INT DEFAULT 0 COMMENT 'LLM token 消耗量',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type_target (analysis_type, target_id),
    INDEX idx_task_id (task_id),
    INDEX idx_data_hash (data_hash),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 1.2 错误样本表 (error_samples)

```sql
CREATE TABLE IF NOT EXISTS error_samples (
    sample_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    cluster_id VARCHAR(36) COMMENT '所属聚类ID',
    homework_id VARCHAR(36) NOT NULL,
    book_name VARCHAR(100),
    page_num INT,
    question_index INT,
    subject_id INT,
    error_type VARCHAR(50),
    ai_answer TEXT,
    expected_answer TEXT,
    base_user TEXT COMMENT '学生原始答案（用于不一致检测）',
    status ENUM('pending', 'analyzed', 'in_progress', 'fixed', 'ignored') DEFAULT 'pending',
    llm_insight JSON COMMENT 'LLM 分析结果',
    note TEXT COMMENT '处理备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_cluster_id (cluster_id),
    INDEX idx_status (status),
    INDEX idx_base_user (base_user(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 1.3 错误聚类表 (error_clusters)

```sql
CREATE TABLE IF NOT EXISTS error_clusters (
    cluster_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    cluster_key VARCHAR(200) NOT NULL COMMENT '聚类键（error_type_book_page_range）',
    cluster_name VARCHAR(200) COMMENT 'LLM 生成的聚类名称',
    cluster_description TEXT COMMENT 'LLM 生成的聚类描述',
    root_cause TEXT COMMENT 'LLM 分析的根因',
    severity ENUM('critical', 'high', 'medium', 'low') DEFAULT 'medium',
    sample_count INT DEFAULT 0,
    common_fix TEXT COMMENT 'LLM 生成的通用修复建议',
    pattern_insight TEXT COMMENT 'LLM 生成的模式洞察',
    representative_samples JSON COMMENT '代表性样本ID列表',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_severity (severity),
    UNIQUE KEY uk_task_cluster (task_id, cluster_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 1.4 异常检测表 (analysis_anomalies)

```sql
CREATE TABLE IF NOT EXISTS analysis_anomalies (
    anomaly_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    anomaly_type ENUM('inconsistent_grading', 'recognition_unstable', 'continuous_error', 'batch_missing') NOT NULL,
    severity ENUM('critical', 'high', 'medium', 'low') DEFAULT 'medium',
    base_user_answer TEXT COMMENT '学生原始答案',
    correct_cases JSON COMMENT '正确批改的作业列表',
    incorrect_cases JSON COMMENT '错误批改的作业列表',
    inconsistency_rate DECIMAL(5,4) COMMENT '不一致率',
    description TEXT COMMENT 'LLM 生成的异常描述',
    suggested_action TEXT COMMENT 'LLM 生成的改进建议',
    status ENUM('open', 'investigating', 'resolved', 'ignored') DEFAULT 'open',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_type (anomaly_type),
    INDEX idx_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 1.5 LLM 调用日志表 (llm_call_logs)

```sql
CREATE TABLE IF NOT EXISTS llm_call_logs (
    log_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36),
    analysis_type VARCHAR(50) COMMENT '分析类型',
    target_id VARCHAR(100) COMMENT '分析目标',
    model VARCHAR(50) DEFAULT 'deepseek-v3.2',
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    duration_ms INT COMMENT '耗时（毫秒）',
    retry_count INT DEFAULT 0,
    status ENUM('success', 'failed', 'timeout') NOT NULL,
    error_type VARCHAR(50) COMMENT '错误类型：timeout/api_error/parse_error/other',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_error_type (error_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## LLM Prompt Templates

### 1. 聚类分析 Prompt

```python
CLUSTER_ANALYSIS_PROMPT = """
你是一个专业的 AI 批改系统分析专家。请分析以下错误样本聚类，生成结构化的分析结果。

## 聚类信息
- 聚类键: {cluster_key}
- 样本数量: {sample_count}
- 错误类型: {error_type}
- 书本: {book_name}
- 页码范围: {page_range}

## 错误样本（最多展示10个）
{samples_json}

## 请生成以下分析结果（JSON格式）：
{{
    "cluster_name": "简洁的聚类名称（10字以内）",
    "cluster_description": "描述这类错误的共同特征（50字以内）",
    "root_cause": "分析这类错误的根本原因（100字以内）",
    "severity": "critical/high/medium/low（基于数量和影响判断）",
    "common_fix": "针对这类错误的通用修复建议（100字以内）",
    "pattern_insight": "深度分析这类错误的模式和规律（150字以内）"
}}

只返回 JSON，不要其他内容。
"""
```

### 2. 任务分析 Prompt

```python
TASK_ANALYSIS_PROMPT = """
你是一个专业的 AI 批改系统分析专家。请基于以下批量评估任务的统计数据和聚类分析结果，生成任务级别的综合分析报告。

## 任务统计
- 任务ID: {task_id}
- 总题目数: {total_questions}
- 错误数: {total_errors}
- 错误率: {error_rate:.2%}

## 错误类型分布
{error_type_distribution}

## 学科分布
{subject_distribution}

## 聚类分析结果（Top 5）
{clusters_summary}

## 请生成以下分析结果（JSON格式）：
{{
    "task_summary": "3-5句话总结该任务的整体情况",
    "accuracy_analysis": "分析准确率及其影响因素",
    "main_issues": [
        {{"issue": "问题描述", "count": 数量, "severity": "high/medium/low"}}
    ],
    "error_distribution": "分析错误的分布特征",
    "risk_assessment": "评估该任务暴露的风险",
    "improvement_priority": ["改进项1", "改进项2", "改进项3"],
    "actionable_suggestions": [
        {{"title": "建议标题", "description": "具体描述", "expected_impact": "预期效果"}}
    ]
}}

只返回 JSON，不要其他内容。
"""
```

### 3. 维度分析 Prompt（学科/书本/题型）

```python
DIMENSION_ANALYSIS_PROMPT = """
你是一个专业的 AI 批改系统分析专家。请分析以下{dimension_name}维度的错误数据。

## {dimension_name}信息
- 名称: {name}
- 错误数: {error_count}
- 总题目数: {total}
- 错误率: {error_rate:.2%}

## 错误样本摘要
{samples_summary}

## 请生成以下分析结果（JSON格式）：
{{
    "{dimension}_summary": "总结该{dimension_name}的整体批改情况（50字以内）",
    "common_error_patterns": ["常见错误模式1", "常见错误模式2"],
    "{dimension}_specific_issues": ["该{dimension_name}特有的问题1", "问题2"],
    "improvement_suggestions": ["改进建议1", "改进建议2"]
}}

只返回 JSON，不要其他内容。
"""
```

### 4. 异常检测分析 Prompt

```python
ANOMALY_ANALYSIS_PROMPT = """
你是一个专业的 AI 批改系统分析专家。请分析以下批改不一致的异常情况。

## 异常信息
- 学生答案: {base_user_answer}
- 出现次数: {occurrence_count}
- 正确批改次数: {correct_count}
- 错误批改次数: {incorrect_count}
- 不一致率: {inconsistency_rate:.2%}

## 正确批改案例
{correct_cases}

## 错误批改案例
{incorrect_cases}

## 请生成以下分析结果（JSON格式）：
{{
    "description": "描述这个不一致问题（100字以内）",
    "root_cause": "分析导致不一致的根本原因",
    "suggested_action": "具体的改进建议（包括 Prompt 修改建议）",
    "severity": "critical/high/medium/low"
}}

只返回 JSON，不要其他内容。
"""
```

### 5. 优化建议生成 Prompt

```python
SUGGESTION_GENERATION_PROMPT = """
你是一个专业的 AI 批改系统优化专家。请基于以下分析结果，生成具体可执行的优化建议。

## 任务分析摘要
{task_summary}

## 主要问题聚类
{main_clusters}

## 异常检测结果
{anomalies}

## 请生成最多5条高价值优化建议（JSON数组格式）：
[
    {{
        "title": "建议标题（10字以内）",
        "category": "Prompt优化/数据集优化/评分逻辑优化/OCR优化",
        "description": "详细描述（100字以内）",
        "priority": "P0/P1/P2",
        "expected_impact": "预期效果（50字以内）",
        "implementation_steps": ["步骤1", "步骤2", "步骤3"],
        "prompt_template": "如果是Prompt优化，提供具体的Prompt修改建议，否则为null"
    }}
]

按优先级排序，只返回 JSON 数组，不要其他内容。
"""
```

### 6. 批次对比分析 Prompt

```python
COMPARISON_ANALYSIS_PROMPT = """
你是一个专业的 AI 批改系统分析专家。请对比以下两个批次的评估结果。

## 批次1信息
- 任务ID: {task_id_1}
- 时间: {time_1}
- 总题目数: {total_1}
- 错误数: {errors_1}
- 错误率: {error_rate_1:.2%}
- 主要错误类型: {main_errors_1}

## 批次2信息
- 任务ID: {task_id_2}
- 时间: {time_2}
- 总题目数: {total_2}
- 错误数: {errors_2}
- 错误率: {error_rate_2:.2%}
- 主要错误类型: {main_errors_2}

## 请生成对比分析结果（JSON格式）：
{{
    "comparison_summary": "整体对比分析（100字以内）",
    "accuracy_change": {{
        "direction": "improved/declined/stable",
        "percentage": 变化百分比,
        "analysis": "变化原因分析"
    }},
    "error_pattern_changes": {{
        "new_patterns": ["新增的错误模式"],
        "reduced_patterns": ["减少的错误模式"],
        "analysis": "模式变化分析"
    }},
    "improvement_items": ["具体改进的地方"],
    "regression_items": ["退步的地方"],
    "root_cause_analysis": "导致改进或退步的根本原因分析",
    "recommendations": ["后续建议1", "建议2"]
}}

只返回 JSON，不要其他内容。
"""
```

## Frontend Components Design

### 5. 前端页面组件设计

#### 5.1 分析报告页面 (analysis-report.html)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  AI 智能分析报告                                                    [刷新分析] [导出] │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │
│  │ 总错误数     │ │ 错误率       │ │ 待处理       │ │ 已修复       │ │ 分析状态   │ │
│  │    156       │ │   13.0%      │ │    89        │ │    45        │ │ ● 已完成   │ │
│  │   ↑12        │ │   ↓2.1%      │ │              │ │              │ │            │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │
│                                                                                      │
│  ┌─ 执行摘要 ────────────────────────────────────────────────────────────────────┐  │
│  │ 本次批量评估共处理 1200 道题目，整体准确率 87%。主要问题集中在物理力学题的    │  │
│  │ 手写体识别和化学方程式配平判断。建议优先优化手写体识别的 Prompt 容错处理。    │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌─ 图表区域 ────────────────────────────────────────────────────────────────────┐  │
│  │  [饼图] [桑基图] [热力图] [雷达图]                                             │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                                                                         │  │  │
│  │  │                        (图表渲染区域)                                    │  │  │
│  │  │                                                                         │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌─ 维度分析 ────────────────────────────────────────────────────────────────────┐  │
│  │  [学科] [书本] [题型] [时间趋势] [批次对比]                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │  数学 (56 错误, 14%)  │  物理 (45 错误, 15%)  │  化学 (23 错误, 11%)     │  │  │
│  │  │  [查看详情]           │  [查看详情]           │  [查看详情]              │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌─ Top 5 问题聚类 ──────────────────────────────────────────────────────────────┐  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │ [严重] 数学手写体识别问题 (23 样本)                                      │  │  │
│  │  │ 学生手写数字和符号识别不准确，主要集中在分数、根号等复杂符号             │  │  │
│  │  │ [查看详情] [查看样本]                                                    │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │ [中等] 物理公式判断错误 (18 样本)                                        │  │  │
│  │  │ ...                                                                      │  │  │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌─ 异常提醒 ────────────────────────────────────────────────────────────────────┐  │
│  │  [!] 发现 2 个批改不一致问题（同一答案不同批改结果）                          │  │
│  │      [查看详情]                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌─ 优化建议 ────────────────────────────────────────────────────────────────────┐  │
│  │  1. [P0] 优化手写体识别容错 - 预计减少 30% 识别错误                          │  │
│  │  2. [P1] 完善物理公式评分逻辑 - 预计减少 20% 评分错误                        │  │
│  │  [查看全部建议]                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

#### 5.2 错误样本库页面 - 三栏布局 (error-samples.html)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  错误样本库                                              [批量操作▼] [导出] [≡折叠] │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─ 左栏（列表）300px ─┐ ┌─ 中栏（详情）自适应 ─────────┐ ┌─ 右栏（分析）350px ─┐  │
│  │                     │ │                              │ │                     │  │
│  │ [搜索框...]         │ │  ┌─ 基本信息 ─────────────┐  │ │ ┌─ LLM 分析 ──────┐ │  │
│  │ [待处理] [全部] [已 │ │  │ 作业ID: hw123          │  │ │ │ ▶ 错误分类      │ │  │
│  │                     │ │  │ 书本: 数学八上         │  │ │ │   OCR识别问题   │ │  │
│  │ ┌─────────────────┐ │ │  │ 页码: 15  题目: 3      │  │ │ │                 │ │  │
│  │ │ ● 数学八上 P15  │ │ │  └──────────────────────┘  │ │ │ ▶ 根因分析      │ │  │
│  │ │   识别错误      │ │ │                              │ │ │   手写体变体多  │ │  │
│  │ │   [待处理]      │ │ │  ┌─ 答案对比 ─────────────┐  │ │ │   ...           │ │  │
│  │ └─────────────────┘ │ │  │ 标准答案: 3.14         │  │ │ │                 │ │  │
│  │ ┌─────────────────┐ │ │  │ 学生答案: 3.14         │  │ │ │ ▶ 修复建议      │ │  │
│  │ │ ● 物理八上 P22  │ │ │  │ AI识别:   3.1H  [差异] │  │ │ │   增加容错处理  │ │  │
│  │ │   评分错误      │ │ │  └──────────────────────┘  │ │ │                 │ │  │
│  │ │   [待处理]      │ │ │                              │ │ │ ▶ 置信度: 85%   │ │  │
│  │ └─────────────────┘ │ │  ┌─ 作业图片 ─────────────┐  │ │ └─────────────────┘ │  │
│  │ ┌─────────────────┐ │ │  │                        │  │ │                     │  │
│  │ │ ● 化学八上 P8   │ │ │  │    [图片预览区域]      │  │ │ ┌─ 所属聚类 ──────┐ │  │
│  │ │   缺失题目      │ │ │  │    [点击放大]          │  │ │ │ 数学手写体识别  │ │  │
│  │ │   [已修复]      │ │ │  │                        │  │ │ │ 问题 (23 样本)  │ │  │
│  │ └─────────────────┘ │ │  └──────────────────────┘  │ │ │ [查看聚类详情]  │ │  │
│  │                     │ │                              │ │ └─────────────────┘ │  │
│  │ ...                 │ │  ┌─ 状态操作 ─────────────┐  │ │                     │  │
│  │                     │ │  │ [待处理] [处理中]      │  │ │ ┌─ 相似样本 ──────┐ │  │
│  │ [加载更多...]       │ │  │ [已修复] [已忽略]      │  │ │ │ • 数学八上 P16  │ │  │
│  │                     │ │  │                        │  │ │ │ • 数学八上 P18  │ │  │
│  │ 共 156 条           │ │  │ 备注: [输入备注...]    │  │ │ │ • 数学八下 P12  │ │  │
│  │                     │ │  └──────────────────────┘  │ │ └─────────────────┘ │  │
│  └─────────────────────┘ └──────────────────────────────┘ └─────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

#### 5.3 聚类详情页 (cluster-detail.html)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  ← 返回聚类列表                                                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─ 聚类概览 ────────────────────────────────────────────────────────────────────┐  │
│  │                                                                                │  │
│  │  数学手写体识别问题                                           [严重] 23 样本  │  │
│  │                                                                                │  │
│  │  学生手写数字和符号识别不准确，主要集中在分数、根号等复杂符号的识别上。       │  │
│  │  这类错误在数学八上教材中尤为突出，特别是第 10-20 页的计算题部分。            │  │
│  │                                                                                │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌─ LLM 分析结果 ────────────────────────────────────────────────────────────────┐  │
│  │                                                                                │  │
│  │  ▼ 根因分析                                                                   │  │
│  │    手写体变体多，OCR 模型覆盖不足。学生书写风格差异大，特别是数字 4、7、9     │  │
│  │    和字母 a、d、q 容易混淆。分数线和根号的手写形式多样，难以准确识别。        │  │
│  │                                                                                │  │
│  │  ▼ 模式洞察                                                                   │  │
│  │    错误主要集中在以下几类：                                                   │  │
│  │    1. 分数识别：分数线被识别为减号或下划线                                    │  │
│  │    2. 根号识别：根号内容提取不完整                                            │  │
│  │    3. 指数识别：上标数字被识别为普通数字                                      │  │
│  │                                                                                │  │
│  │  ▼ 通用修复建议                                                               │  │
│  │    在 Prompt 中增加手写体容错说明，明确指出常见的书写变体。建议添加示例：     │  │
│  │    "对于手写数学符号，请考虑以下变体：分数可能写成 a/b 或 a÷b..."            │  │
│  │                                                                                │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌─ 代表性样本 ──────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐               │  │
│  │  │ 数学八上 P15 Q3  │ │ 数学八上 P16 Q5  │ │ 数学八下 P12 Q2  │               │  │
│  │  │ 标准: 3/4        │ │ 标准: √2         │ │ 标准: 2³         │               │  │
│  │  │ AI识别: 3-4      │ │ AI识别: V2       │ │ AI识别: 23       │               │  │
│  │  │ [查看详情]       │ │ [查看详情]       │ │ [查看详情]       │               │  │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘               │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌─ 样本列表 ────────────────────────────────────────────────────────────────────┐  │
│  │  [批量标记▼] [导出]                                    搜索: [............]   │  │
│  │  ┌────────────────────────────────────────────────────────────────────────┐   │  │
│  │  │ □ │ 作业ID   │ 书本      │ 页码 │ 题目 │ 错误类型   │ 状态   │ 操作   │   │  │
│  │  ├────────────────────────────────────────────────────────────────────────┤   │  │
│  │  │ □ │ hw123    │ 数学八上  │ 15   │ 3    │ 识别错误   │ 待处理 │ [查看] │   │  │
│  │  │ □ │ hw124    │ 数学八上  │ 16   │ 5    │ 识别错误   │ 待处理 │ [查看] │   │  │
│  │  │ □ │ hw125    │ 数学八下  │ 12   │ 2    │ 识别错误   │ 已修复 │ [查看] │   │  │
│  │  │ ...                                                                    │   │  │
│  │  └────────────────────────────────────────────────────────────────────────┘   │  │
│  │  共 23 条  [1] [2] [3] ...                                                    │  │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 6. 分析配置管理

#### 6.1 配置 API

**GET /api/analysis/config**
```json
// Response
{
    "success": true,
    "data": {
        "llm_model": "deepseek-v3.2",
        "temperature": 0.2,
        "max_concurrent": 10,
        "request_timeout": 60,
        "max_retries": 3,
        "batch_size": 20,
        "auto_trigger": true,
        "daily_token_limit": 1000000,
        "enabled_dimensions": ["cluster", "task", "subject", "book", "question_type", "trend", "compare"],
        "cost_stats": {
            "today_tokens": 45000,
            "today_calls": 120,
            "month_tokens": 890000
        }
    }
}
```

**PUT /api/analysis/config**
```json
// Request
{
    "temperature": 0.3,
    "max_concurrent": 15,
    "request_timeout": 90,
    "auto_trigger": false,
    "daily_token_limit": 500000,
    "enabled_dimensions": ["cluster", "task", "subject"]
}
// Response
{
    "success": true,
    "message": "配置已更新"
}
```

#### 6.2 配置数据模型

```sql
CREATE TABLE IF NOT EXISTS analysis_config (
    config_key VARCHAR(50) PRIMARY KEY,
    config_value TEXT NOT NULL,
    config_type ENUM('string', 'number', 'boolean', 'json') DEFAULT 'string',
    description VARCHAR(200),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 默认配置
INSERT INTO analysis_config (config_key, config_value, config_type, description) VALUES
('llm_model', 'deepseek-v3.2', 'string', 'LLM 模型'),
('temperature', '0.2', 'number', '温度参数'),
('max_concurrent', '10', 'number', '最大并发数'),
('request_timeout', '60', 'number', '请求超时（秒）'),
('max_retries', '3', 'number', '最大重试次数'),
('batch_size', '20', 'number', '批量分析大小'),
('auto_trigger', 'true', 'boolean', '自动触发分析'),
('daily_token_limit', '1000000', 'number', '每日 token 限制'),
('enabled_dimensions', '["cluster","task","subject","book","question_type","trend","compare"]', 'json', '启用的分析维度');
```

### 7. 高级可视化数据接口

#### 7.1 桑基图数据 API

**GET /api/analysis/chart/sankey?task_id={task_id}**
```json
// Response
{
    "success": true,
    "data": {
        "nodes": [
            // 错误类型节点（左侧）
            {"id": "type_recognition", "name": "识别错误", "category": "error_type"},
            {"id": "type_grading", "name": "评分错误", "category": "error_type"},
            {"id": "type_missing", "name": "缺失题目", "category": "error_type"},
            // 根因节点（中间）
            {"id": "cause_ocr", "name": "OCR问题", "category": "root_cause"},
            {"id": "cause_logic", "name": "评分逻辑", "category": "root_cause"},
            {"id": "cause_data", "name": "数据问题", "category": "root_cause"},
            // 建议节点（右侧）
            {"id": "suggest_prompt", "name": "Prompt优化", "category": "suggestion"},
            {"id": "suggest_dataset", "name": "数据集优化", "category": "suggestion"},
            {"id": "suggest_logic", "name": "逻辑优化", "category": "suggestion"}
        ],
        "links": [
            {"source": "type_recognition", "target": "cause_ocr", "value": 45},
            {"source": "type_recognition", "target": "cause_data", "value": 10},
            {"source": "type_grading", "target": "cause_logic", "value": 38},
            {"source": "cause_ocr", "target": "suggest_prompt", "value": 35},
            {"source": "cause_ocr", "target": "suggest_dataset", "value": 20},
            {"source": "cause_logic", "target": "suggest_logic", "value": 38}
        ]
    }
}
```

#### 7.2 热力图数据 API

**GET /api/analysis/chart/heatmap?task_id={task_id}&book_id={book_id}**
```json
// Response
{
    "success": true,
    "data": {
        "book_name": "数学八上",
        "x_axis": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  // 题目索引
        "y_axis": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],  // 页码
        "data": [
            // [x, y, value] - 题目索引, 页码, 错误数
            [3, 15, 5],
            [5, 15, 3],
            [2, 16, 4],
            [7, 18, 2],
            [4, 20, 6]
        ],
        "max_value": 6,
        "total_errors": 20
    }
}
```

#### 7.3 雷达图数据 API

**GET /api/analysis/chart/radar?task_id={task_id}&dimension={subject|question_type|book}**
```json
// Response - 学科维度
{
    "success": true,
    "data": {
        "dimension": "subject",
        "indicators": [
            {"name": "数学", "max": 100},
            {"name": "物理", "max": 100},
            {"name": "化学", "max": 100},
            {"name": "生物", "max": 100},
            {"name": "英语", "max": 100}
        ],
        "series": [
            {
                "name": "当前批次",
                "values": [14, 15, 11, 8, 5]  // 错误率百分比
            },
            {
                "name": "上一批次",
                "values": [16, 18, 12, 10, 6]  // 用于对比
            }
        ]
    }
}
```

### 8. 搜索筛选增强

#### 8.1 高级搜索 API

**GET /api/analysis/samples/search**
```json
// Request Query Parameters
{
    "q": "book:数学 AND status:pending",  // 高级搜索语法
    "page": 1,
    "page_size": 20
}
// Response
{
    "success": true,
    "data": {
        "items": [...],
        "total": 45,
        "page": 1,
        "page_size": 20,
        "query_parsed": {
            "conditions": [
                {"field": "book", "operator": "contains", "value": "数学"},
                {"field": "status", "operator": "equals", "value": "pending"}
            ],
            "logic": "AND"
        },
        "highlights": {
            "sample_id_1": {"book_name": "<mark>数学</mark>八上"}
        }
    }
}
```

#### 8.2 搜索语法解析器

```python
class SearchQueryParser:
    """高级搜索语法解析器"""
    
    FIELD_MAPPING = {
        'book': 'book_name',
        'subject': 'subject_id',
        'type': 'error_type',
        'status': 'status',
        'page': 'page_num',
        'severity': 'severity',
        'cluster': 'cluster_id'
    }
    
    @classmethod
    def parse(cls, query: str) -> dict:
        """
        解析搜索语法
        
        支持格式:
        - 简单搜索: "数学"
        - 字段搜索: "book:数学"
        - 组合搜索: "book:数学 AND status:pending"
        - 括号分组: "(book:数学 OR book:物理) AND status:pending"
        - 范围搜索: "page:10-20"
        
        Returns:
            dict: {
                'conditions': [...],
                'logic': 'AND' | 'OR',
                'sql_where': str,
                'params': list
            }
        """
        pass
    
    @classmethod
    def build_sql(cls, parsed: dict) -> tuple:
        """构建 SQL WHERE 子句"""
        pass
```

#### 8.3 筛选预设 API

**GET /api/analysis/filter-presets**
```json
// Response
{
    "success": true,
    "data": {
        "system_presets": [
            {"id": "high_priority", "name": "待处理高优先级", "query": "status:pending AND severity:high"},
            {"id": "today", "name": "今日新增", "query": "created_at:today"},
            {"id": "inconsistent", "name": "批改不一致", "query": "anomaly_type:inconsistent_grading"}
        ],
        "user_presets": [
            {"id": "preset_1", "name": "数学高优先级", "query": "book:数学 AND severity:high"}
        ]
    }
}
```

**POST /api/analysis/filter-presets**
```json
// Request
{
    "name": "物理待处理",
    "query": "subject:物理 AND status:pending"
}
// Response
{
    "success": true,
    "data": {
        "id": "preset_2",
        "name": "物理待处理",
        "query": "subject:物理 AND status:pending"
    }
}
```

**DELETE /api/analysis/filter-presets/{preset_id}**

### 9. 导出报告功能

#### 9.1 导出 API

**POST /api/analysis/export**
```json
// Request
{
    "task_id": "task123",
    "format": "pdf",  // pdf | excel
    "sections": ["summary", "clusters", "samples", "suggestions"],  // 可选导出章节
    "filters": {
        "status": "pending",
        "severity": "high"
    }
}
// Response
{
    "success": true,
    "data": {
        "export_id": "exp_abc123",
        "status": "generating",
        "message": "报告生成中，预计 30 秒完成"
    }
}
```

**GET /api/analysis/export/{export_id}**
```json
// Response
{
    "success": true,
    "data": {
        "export_id": "exp_abc123",
        "status": "completed",  // generating | completed | failed
        "download_url": "/api/analysis/export/download/exp_abc123",
        "file_name": "AI分析报告_20260125.pdf",
        "file_size": 1024000,
        "expires_at": "2026-01-26 10:00:00"
    }
}
```

#### 9.2 PDF 报告结构

```
AI 智能分析报告
================

1. 执行摘要
   - LLM 生成的 3-5 句话总结
   - 关键指标卡片（错误数、错误率、待处理、已修复）

2. 错误类型分布
   - 饼图
   - 各类型数量和占比表格

3. Top 5 问题聚类
   - 聚类名称、描述、样本数、严重程度
   - 根因分析和修复建议

4. 维度分析
   - 学科分析摘要
   - 书本分析摘要
   - 题型分析摘要

5. 异常检测
   - 批改不一致问题列表
   - 严重程度和建议

6. 优化建议
   - 按优先级排列的建议列表
   - 预期效果和实施步骤

7. 附录：错误样本明细
   - 样本列表表格
```

### 10. 成本控制与限制

#### 10.1 成本统计 API

**GET /api/analysis/cost-stats**
```json
// Response
{
    "success": true,
    "data": {
        "today": {
            "token_usage": 45000,
            "api_calls": 120,
            "cost_estimate": 0.45  // 美元
        },
        "this_week": {
            "token_usage": 280000,
            "api_calls": 750,
            "cost_estimate": 2.80
        },
        "this_month": {
            "token_usage": 890000,
            "api_calls": 2300,
            "cost_estimate": 8.90
        },
        "limits": {
            "daily_token_limit": 1000000,
            "daily_remaining": 955000,
            "limit_reached": false
        }
    }
}
```

#### 10.2 成本限制处理

```python
class CostLimitHandler:
    """成本限制处理器"""
    
    @classmethod
    def check_limit(cls) -> dict:
        """
        检查是否达到成本限制
        
        Returns:
            dict: {
                can_proceed: bool,
                remaining_tokens: int,
                message: str
            }
        """
        pass
    
    @classmethod
    def notify_admin(cls, reason: str):
        """达到限制时通知管理员"""
        pass
    
    @classmethod
    def pause_analysis(cls):
        """暂停所有分析任务"""
        pass
```

### 11. 前端性能优化实现

#### 11.1 虚拟滚动组件

```javascript
class VirtualScroller {
    /**
     * 虚拟滚动实现
     * 
     * 配置:
     * - itemHeight: 单项高度（固定或估算）
     * - bufferSize: 缓冲区大小（上下各多渲染几项）
     * - containerHeight: 容器高度
     */
    constructor(options) {
        this.itemHeight = options.itemHeight || 60;
        this.bufferSize = options.bufferSize || 5;
        this.containerHeight = options.containerHeight;
        this.items = [];
        this.scrollTop = 0;
    }
    
    /**
     * 计算可见范围
     * @returns {Object} {startIndex, endIndex, offsetY}
     */
    getVisibleRange() {
        const startIndex = Math.max(0, Math.floor(this.scrollTop / this.itemHeight) - this.bufferSize);
        const visibleCount = Math.ceil(this.containerHeight / this.itemHeight);
        const endIndex = Math.min(this.items.length, startIndex + visibleCount + this.bufferSize * 2);
        const offsetY = startIndex * this.itemHeight;
        return { startIndex, endIndex, offsetY };
    }
    
    /**
     * 渲染可见项
     */
    render() {
        const { startIndex, endIndex, offsetY } = this.getVisibleRange();
        const visibleItems = this.items.slice(startIndex, endIndex);
        // 渲染 visibleItems，设置 transform: translateY(offsetY)
    }
}
```

#### 11.2 防抖节流工具

```javascript
// 防抖函数
function debounce(fn, delay = 300) {
    let timer = null;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

// 节流函数
function throttle(fn, interval = 16) {
    let lastTime = 0;
    return function(...args) {
        const now = Date.now();
        if (now - lastTime >= interval) {
            lastTime = now;
            fn.apply(this, args);
        }
    };
}

// 使用示例
const handleSearch = debounce((query) => {
    fetchSearchResults(query);
}, 300);

const handleScroll = throttle((e) => {
    updateVisibleItems(e.target.scrollTop);
}, 16);
```

#### 11.3 懒加载实现

```javascript
class LazyLoader {
    /**
     * 使用 IntersectionObserver 实现懒加载
     */
    constructor(options = {}) {
        this.rootMargin = options.rootMargin || '100px';
        this.threshold = options.threshold || 0.1;
        
        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.loadElement(entry.target);
                    this.observer.unobserve(entry.target);
                }
            });
        }, {
            rootMargin: this.rootMargin,
            threshold: this.threshold
        });
    }
    
    observe(element) {
        this.observer.observe(element);
    }
    
    loadElement(element) {
        // 图片懒加载
        if (element.dataset.src) {
            element.src = element.dataset.src;
        }
        // 图表懒加载
        if (element.dataset.chart) {
            this.initChart(element);
        }
    }
    
    initChart(element) {
        const chartType = element.dataset.chart;
        const chartData = JSON.parse(element.dataset.chartData || '{}');
        // 初始化图表
    }
}
```

### 12. Toast 通知系统

```javascript
class ToastManager {
    constructor() {
        this.container = this.createContainer();
        this.toasts = [];
    }
    
    createContainer() {
        const container = document.createElement('div');
        container.className = 'toast-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
        `;
        document.body.appendChild(container);
        return container;
    }
    
    show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-message">${message}</span>
            <button class="toast-close">&times;</button>
        `;
        
        // 样式
        const colors = {
            success: { bg: '#e3f9e5', text: '#1e7e34' },
            warning: { bg: '#fff3e0', text: '#e65100' },
            error: { bg: '#ffeef0', text: '#d73a49' },
            info: { bg: '#e3f2fd', text: '#1565c0' }
        };
        const color = colors[type] || colors.info;
        toast.style.cssText = `
            background: ${color.bg};
            color: ${color.text};
            padding: 12px 16px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
            animation: slideIn 0.3s ease-out;
        `;
        
        // 关闭按钮
        toast.querySelector('.toast-close').onclick = () => this.remove(toast);
        
        this.container.appendChild(toast);
        this.toasts.push(toast);
        
        // 自动消失
        if (duration > 0) {
            setTimeout(() => this.remove(toast), duration);
        }
        
        return toast;
    }
    
    remove(toast) {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            toast.remove();
            this.toasts = this.toasts.filter(t => t !== toast);
        }, 300);
    }
    
    success(message) { return this.show(message, 'success'); }
    warning(message) { return this.show(message, 'warning'); }
    error(message) { return this.show(message, 'error'); }
    info(message) { return this.show(message, 'info'); }
}

// 全局实例
window.toast = new ToastManager();
```

### 13. 骨架屏组件

```html
<!-- 骨架屏样式 -->
<style>
.skeleton {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
}

@keyframes skeleton-loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

.skeleton-card {
    height: 80px;
    border-radius: 8px;
    margin-bottom: 12px;
}

.skeleton-text {
    height: 16px;
    border-radius: 4px;
    margin-bottom: 8px;
}

.skeleton-text.short { width: 60%; }
.skeleton-text.medium { width: 80%; }
.skeleton-text.long { width: 100%; }

.skeleton-chart {
    height: 300px;
    border-radius: 12px;
}
</style>

<!-- 骨架屏模板 -->
<div class="skeleton-wrapper" id="skeleton-stats">
    <div class="skeleton skeleton-card"></div>
    <div class="skeleton skeleton-card"></div>
    <div class="skeleton skeleton-card"></div>
</div>

<div class="skeleton-wrapper" id="skeleton-chart">
    <div class="skeleton skeleton-chart"></div>
</div>

<div class="skeleton-wrapper" id="skeleton-list">
    <div class="skeleton skeleton-text long"></div>
    <div class="skeleton skeleton-text medium"></div>
    <div class="skeleton skeleton-text short"></div>
</div>
```

### 14. 分析进度轮询

```javascript
class AnalysisProgressPoller {
    constructor(taskId, options = {}) {
        this.taskId = taskId;
        this.interval = options.interval || 2000;  // 2秒轮询
        this.maxAttempts = options.maxAttempts || 300;  // 最多轮询 10 分钟
        this.onProgress = options.onProgress || (() => {});
        this.onComplete = options.onComplete || (() => {});
        this.onError = options.onError || (() => {});
        
        this.attempts = 0;
        this.timer = null;
    }
    
    start() {
        this.poll();
    }
    
    async poll() {
        try {
            const response = await fetch(`/api/analysis/queue`);
            const data = await response.json();
            
            // 查找当前任务
            const running = data.data.running.find(t => t.task_id === this.taskId);
            
            if (running) {
                this.onProgress({
                    progress: running.progress,
                    step: running.step,
                    estimatedTime: this.estimateRemainingTime(running.progress)
                });
                
                this.attempts++;
                if (this.attempts < this.maxAttempts) {
                    this.timer = setTimeout(() => this.poll(), this.interval);
                } else {
                    this.onError({ message: '分析超时' });
                }
            } else {
                // 检查是否完成
                const completed = data.data.recent_completed.find(t => t.task_id === this.taskId);
                if (completed) {
                    this.onComplete(completed);
                } else {
                    const failed = data.data.recent_failed.find(t => t.task_id === this.taskId);
                    if (failed) {
                        this.onError(failed);
                    } else {
                        // 还在等待中，继续轮询
                        this.timer = setTimeout(() => this.poll(), this.interval);
                    }
                }
            }
        } catch (error) {
            this.onError({ message: error.message });
        }
    }
    
    estimateRemainingTime(progress) {
        if (progress <= 0) return '计算中...';
        const elapsed = this.attempts * this.interval / 1000;
        const total = elapsed / (progress / 100);
        const remaining = total - elapsed;
        return `约 ${Math.ceil(remaining)} 秒`;
    }
    
    stop() {
        if (this.timer) {
            clearTimeout(this.timer);
            this.timer = null;
        }
    }
}

// 使用示例
const poller = new AnalysisProgressPoller('task123', {
    onProgress: ({ progress, step, estimatedTime }) => {
        updateProgressBar(progress);
        updateStepText(step);
        updateEstimatedTime(estimatedTime);
    },
    onComplete: (result) => {
        toast.success('分析完成');
        refreshAnalysisData();
    },
    onError: (error) => {
        toast.error(`分析失败: ${error.message}`);
    }
});
poller.start();
```

## Correctness Properties

### Property 1: 聚类完整性

*For any* 批量评估任务的分析，所有错误样本必须被分配到且仅分配到一个聚类中。

**Validates: Requirements 2**

### Property 2: 聚类样本数一致性

*For any* 聚类，其 sample_count 字段值必须等于该聚类下实际的错误样本数量。

**Validates: Requirements 2.3**

### Property 3: 缓存哈希一致性

*For any* 分析结果，当源数据未变化时（data_hash 相同），返回的分析结果必须与缓存结果一致。

**Validates: Requirements 15.3**

### Property 4: 并行调用独立性

*For any* 并行执行的 LLM 调用，单个请求的失败不应影响其他并行请求的执行和结果。

**Validates: Requirements 19.5**

### Property 5: 异常检测准确性

*For any* 批改不一致异常，其 inconsistency_rate 必须等于 incorrect_cases 数量除以总出现次数。

**Validates: Requirements 9.2**

### Property 6: 快速统计即时性

*For any* 快速本地统计请求，响应时间必须小于 100ms。

**Validates: Requirements 17.4**

### Property 7: 分析队列顺序性

*For any* 相同优先级的分析任务，必须按照加入队列的时间顺序执行（FIFO）。

**Validates: Requirements 16.2**

### Property 8: 样本状态有效性

*For any* 错误样本，其状态必须是 pending/analyzed/in_progress/fixed/ignored 之一。

**Validates: Requirements 11.1**

### Property 9: 建议数量限制

*For any* 分析报告，其优化建议数量不超过 5 条。

**Validates: Requirements 10.3**

### Property 10: Top 5 聚类排序

*For any* 分析报告的 Top 5 聚类，必须按严重程度和样本数量综合排序。

**Validates: Requirements 2.5**

## Error Handling

### 1. LLM 调用错误处理

```python
class LLMCallError(Exception):
    """LLM 调用错误"""
    def __init__(self, error_type: str, message: str, retry_count: int = 0):
        self.error_type = error_type  # timeout/api_error/parse_error/rate_limit
        self.message = message
        self.retry_count = retry_count
        super().__init__(message)

async def call_llm_with_retry(prompt: str, max_retries: int = 3) -> dict:
    """带重试的 LLM 调用"""
    for attempt in range(max_retries + 1):
        try:
            result = await LLMService.call_deepseek_async(prompt, timeout=60)
            if result.get('error'):
                raise LLMCallError('api_error', result['error'], attempt)
            
            # 解析 JSON 响应
            parsed = LLMService.parse_json_response(result.get('content'))
            if not parsed:
                raise LLMCallError('parse_error', '无法解析 LLM 响应为 JSON', attempt)
            
            return {'success': True, 'data': parsed, 'retry_count': attempt}
            
        except asyncio.TimeoutError:
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)  # 指数退避
                continue
            raise LLMCallError('timeout', f'LLM 请求超时（重试 {attempt} 次）', attempt)
        except LLMCallError:
            if attempt < max_retries:
                await asyncio.sleep(1)
                continue
            raise
    
    raise LLMCallError('unknown', '未知错误', max_retries)
```

### 2. 并行调用错误隔离

```python
async def parallel_analyze_clusters(clusters: List[dict]) -> List[dict]:
    """并行分析多个聚类，错误隔离"""
    semaphore = asyncio.Semaphore(10)  # 最大并发 10
    
    async def analyze_one(cluster: dict) -> dict:
        async with semaphore:
            try:
                result = await LLMAnalysisService.analyze_cluster(cluster)
                log_llm_call(cluster['cluster_id'], 'success')
                return {'success': True, 'cluster_id': cluster['cluster_id'], 'data': result}
            except LLMCallError as e:
                log_llm_call(cluster['cluster_id'], 'failed', e.error_type, e.message, e.retry_count)
                return {'success': False, 'cluster_id': cluster['cluster_id'], 'error': str(e)}
            except Exception as e:
                log_llm_call(cluster['cluster_id'], 'failed', 'unknown', str(e))
                return {'success': False, 'cluster_id': cluster['cluster_id'], 'error': str(e)}
    
    tasks = [analyze_one(c) for c in clusters]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    
    # 统计成功/失败
    success_count = sum(1 for r in results if r['success'])
    failed_count = len(results) - success_count
    
    return {
        'results': results,
        'summary': {'success': success_count, 'failed': failed_count}
    }
```

### 3. 错误日志记录

```python
def log_llm_call(target_id: str, status: str, error_type: str = None, 
                 error_message: str = None, retry_count: int = 0,
                 task_id: str = None, analysis_type: str = None,
                 duration_ms: int = None, tokens: dict = None):
    """记录 LLM 调用日志"""
    log_id = str(uuid.uuid4())[:8]
    sql = """
        INSERT INTO llm_call_logs 
        (log_id, task_id, analysis_type, target_id, status, error_type, 
         error_message, retry_count, duration_ms, prompt_tokens, 
         completion_tokens, total_tokens, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """
    AppDatabaseService.execute_insert(sql, (
        log_id, task_id, analysis_type, target_id, status, error_type,
        error_message, retry_count, duration_ms,
        tokens.get('prompt', 0) if tokens else 0,
        tokens.get('completion', 0) if tokens else 0,
        tokens.get('total', 0) if tokens else 0
    ))
```

### 4. 分析任务失败处理

```python
def handle_analysis_failure(task_id: str, error: Exception, report_id: str = None):
    """处理分析任务失败"""
    error_message = str(error)
    error_type = type(error).__name__
    
    # 更新分析结果状态
    if report_id:
        sql = """
            UPDATE analysis_results 
            SET status = 'failed', error_message = %s, updated_at = NOW()
            WHERE result_id = %s
        """
        AppDatabaseService.execute_update(sql, (error_message, report_id))
    
    # 记录自动化日志
    log_automation('ai_analysis', task_id, 'failed', f'{error_type}: {error_message}')
    
    # 从运行队列移除
    with AIAnalysisService._lock:
        if task_id in AIAnalysisService._running:
            del AIAnalysisService._running[task_id]
```

## Testing Strategy

### 1. 单元测试

```python
# tests/test_ai_analysis_enhanced.py
import pytest
from services.ai_analysis_service import AIAnalysisService
from services.llm_analysis_service import LLMAnalysisService

class TestQuickStats:
    """快速本地统计测试"""
    
    def test_quick_stats_returns_immediately(self, sample_task):
        """测试快速统计立即返回"""
        import time
        start = time.time()
        result = AIAnalysisService.get_quick_stats(sample_task['task_id'])
        duration = time.time() - start
        
        assert duration < 0.1  # 100ms 内返回
        assert 'total_errors' in result
        assert 'error_type_distribution' in result
    
    def test_quick_stats_accuracy(self, sample_task_with_errors):
        """测试快速统计准确性"""
        result = AIAnalysisService.get_quick_stats(sample_task_with_errors['task_id'])
        
        # 验证错误数与实际一致
        actual_errors = count_actual_errors(sample_task_with_errors)
        assert result['total_errors'] == actual_errors

class TestClusterAnalysis:
    """聚类分析测试"""
    
    def test_all_samples_assigned_to_cluster(self, sample_task_with_errors):
        """测试所有样本都被分配到聚类"""
        clusters = AIAnalysisService.get_clusters(sample_task_with_errors['task_id'])
        
        total_in_clusters = sum(c['sample_count'] for c in clusters['clusters'])
        total_errors = sample_task_with_errors['error_count']
        
        assert total_in_clusters == total_errors
    
    def test_cluster_sample_count_consistency(self, sample_cluster):
        """测试聚类样本数一致性"""
        cluster_id = sample_cluster['cluster_id']
        samples = AIAnalysisService.get_cluster_samples(cluster_id)
        
        assert len(samples) == sample_cluster['sample_count']
```

### 2. 属性测试

```python
# tests/test_ai_analysis_properties.py
from hypothesis import given, strategies as st, settings
import pytest

class TestAnalysisProperties:
    """分析功能属性测试"""
    
    @given(st.lists(st.dictionaries(
        keys=st.sampled_from(['error_type', 'book_name', 'page_num']),
        values=st.text(min_size=1, max_size=50)
    ), min_size=1, max_size=100))
    @settings(max_examples=50)
    def test_cluster_completeness(self, error_samples):
        """
        Property 1: 聚类完整性
        所有错误样本必须被分配到且仅分配到一个聚类中
        """
        clusters = cluster_samples(error_samples)
        
        # 验证每个样本只属于一个聚类
        sample_cluster_map = {}
        for cluster in clusters:
            for sample_idx in cluster['sample_indices']:
                assert sample_idx not in sample_cluster_map, "样本被分配到多个聚类"
                sample_cluster_map[sample_idx] = cluster['cluster_id']
        
        # 验证所有样本都被分配
        assert len(sample_cluster_map) == len(error_samples)
    
    @given(st.floats(min_value=0, max_value=1), 
           st.integers(min_value=1, max_value=100),
           st.integers(min_value=0, max_value=100))
    def test_inconsistency_rate_calculation(self, rate, correct, incorrect):
        """
        Property 5: 异常检测准确性
        不一致率 = incorrect / (correct + incorrect)
        """
        if correct + incorrect == 0:
            return
        
        calculated_rate = incorrect / (correct + incorrect)
        assert 0 <= calculated_rate <= 1
    
    @given(st.lists(st.integers(min_value=0, max_value=1000), min_size=1, max_size=20))
    def test_top5_cluster_ordering(self, sample_counts):
        """
        Property 10: Top 5 聚类排序
        必须按样本数量降序排列
        """
        sorted_counts = sorted(sample_counts, reverse=True)[:5]
        
        for i in range(len(sorted_counts) - 1):
            assert sorted_counts[i] >= sorted_counts[i + 1]
```

### 3. 集成测试

```python
# tests/test_ai_analysis_integration.py
import pytest
import asyncio

class TestAnalysisIntegration:
    """分析功能集成测试"""
    
    def test_full_analysis_flow(self, client, sample_task):
        """测试完整分析流程"""
        task_id = sample_task['task_id']
        
        # 1. 触发分析
        response = client.post(f'/api/analysis/trigger/{task_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success']
        assert data['data']['queued']
        
        # 2. 检查快速统计（立即可用）
        response = client.get(f'/api/analysis/task/{task_id}')
        assert response.status_code == 200
        data = response.get_json()['data']
        assert 'quick_stats' in data
        
        # 3. 等待 LLM 分析完成
        wait_for_analysis_complete(task_id, timeout=120)
        
        # 4. 验证完整分析结果
        response = client.get(f'/api/analysis/task/{task_id}')
        data = response.get_json()['data']
        assert data['analysis_status'] == 'completed'
        assert data['llm_analysis'] is not None
    
    def test_parallel_llm_calls(self, sample_clusters):
        """测试并行 LLM 调用"""
        async def run_parallel():
            results = await LLMAnalysisService.parallel_analyze(sample_clusters)
            return results
        
        results = asyncio.run(run_parallel())
        
        # 验证所有调用都有结果（成功或失败）
        assert len(results['results']) == len(sample_clusters)
        
        # 验证失败不影响其他调用
        success_count = results['summary']['success']
        assert success_count > 0  # 至少有一些成功
    
    def test_cache_hit(self, client, analyzed_task):
        """测试缓存命中"""
        task_id = analyzed_task['task_id']
        
        # 第一次请求
        response1 = client.get(f'/api/analysis/task/{task_id}')
        data1 = response1.get_json()['data']
        
        # 第二次请求（应该命中缓存）
        response2 = client.get(f'/api/analysis/task/{task_id}')
        data2 = response2.get_json()['data']
        
        # 验证结果一致
        assert data1['llm_analysis'] == data2['llm_analysis']
```

### 4. 前端测试

```javascript
// tests/test_analysis_ui.js
describe('AI 分析页面测试', () => {
    
    describe('快速统计展示', () => {
        it('应该在页面加载时立即显示快速统计', async () => {
            const startTime = Date.now();
            await loadAnalysisPage(taskId);
            const loadTime = Date.now() - startTime;
            
            expect(loadTime).toBeLessThan(500);
            expect(document.querySelector('.stat-card')).toBeTruthy();
        });
        
        it('应该显示骨架屏直到数据加载完成', async () => {
            const skeleton = document.querySelector('.skeleton');
            expect(skeleton).toBeTruthy();
            
            await waitForData();
            expect(document.querySelector('.skeleton')).toBeFalsy();
        });
    });
    
    describe('图表切换', () => {
        it('应该能切换到桑基图', async () => {
            await clickButton('[data-chart="sankey"]');
            expect(document.querySelector('.sankey-chart')).toBeTruthy();
        });
        
        it('应该能切换到热力图', async () => {
            await clickButton('[data-chart="heatmap"]');
            expect(document.querySelector('.heatmap-chart')).toBeTruthy();
        });
    });
    
    describe('三栏布局', () => {
        it('应该正确显示三栏布局', () => {
            const leftPanel = document.querySelector('.panel-left');
            const centerPanel = document.querySelector('.panel-center');
            const rightPanel = document.querySelector('.panel-right');
            
            expect(leftPanel).toBeTruthy();
            expect(centerPanel).toBeTruthy();
            expect(rightPanel).toBeTruthy();
        });
        
        it('右栏应该可以折叠', async () => {
            await clickButton('.collapse-right-panel');
            expect(document.querySelector('.panel-right.collapsed')).toBeTruthy();
        });
    });
    
    describe('搜索功能', () => {
        it('应该支持高级搜索语法', async () => {
            await fillInput('.search-input', 'book:数学 AND status:pending');
            await waitForSearch();
            
            const results = document.querySelectorAll('.sample-item');
            results.forEach(item => {
                expect(item.dataset.book).toContain('数学');
                expect(item.dataset.status).toBe('pending');
            });
        });
    });
});
```
