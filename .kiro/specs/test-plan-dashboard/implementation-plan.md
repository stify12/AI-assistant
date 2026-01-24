# 测试计划看板 - 详细实现方案

> 版本: 1.0 | 更新时间: 2026-01-24

## 一、架构设计原则

### 1.1 模块化设计
```
routes/                     # 路由层 - 处理HTTP请求
├── error_samples.py        # 错误样本库路由
├── image_compare.py        # 图片对比路由
├── anomaly.py              # 异常检测路由
└── optimization.py         # 优化建议路由

services/                   # 服务层 - 业务逻辑
├── error_sample_service.py # 错误样本服务
├── image_compare_service.py# 图片对比服务
├── anomaly_service.py      # 异常检测服务
├── clustering_service.py   # 错误聚类服务
└── optimization_service.py # 优化建议服务

static/js/modules/          # 前端模块
├── error-samples.js        # 错误样本库模块
├── image-compare.js        # 图片对比模块
├── anomaly-detection.js    # 异常检测模块
└── optimization.js         # 优化建议模块
```

### 1.2 代码质量标准 (NFR-34)
- 所有函数必须有文档字符串
- 参数校验（空值、类型）
- 异常捕获和友好错误信息
- 前端使用 JSDoc 注释

---

## 二、数据库表设计

### 2.1 error_samples 表 (US-19)

```sql
CREATE TABLE error_samples (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sample_id VARCHAR(36) NOT NULL UNIQUE COMMENT '样本唯一标识',
    task_id VARCHAR(36) NOT NULL COMMENT '批量任务ID',
    homework_id VARCHAR(50) NOT NULL COMMENT '作业ID',
    dataset_id VARCHAR(36) COMMENT '数据集ID',
    book_id VARCHAR(50) COMMENT '书本ID',
    book_name VARCHAR(200) COMMENT '书本名称',
    page_num INT COMMENT '页码',
    question_index VARCHAR(50) NOT NULL COMMENT '题号',
    subject_id INT COMMENT '学科ID',
    error_type VARCHAR(50) NOT NULL COMMENT '错误类型',
    base_answer TEXT COMMENT '基准答案',
    base_user TEXT COMMENT '基准用户答案',
    hw_user TEXT COMMENT 'AI识别答案',
    pic_path VARCHAR(500) COMMENT '原图路径',
    status ENUM('pending', 'analyzed', 'fixed', 'ignored') DEFAULT 'pending' COMMENT '状态',
    notes TEXT COMMENT '分析备注',
    cluster_id VARCHAR(36) COMMENT '聚类ID',
    cluster_label VARCHAR(100) COMMENT '聚类标签',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_dataset_id (dataset_id),
    INDEX idx_error_type (error_type),
    INDEX idx_status (status),
    INDEX idx_subject_id (subject_id),
    INDEX idx_cluster_id (cluster_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='错误样本库';
```

### 2.2 anomaly_logs 表 (US-26)
```sql
CREATE TABLE anomaly_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    anomaly_id VARCHAR(36) NOT NULL UNIQUE COMMENT '异常唯一标识',
    anomaly_type ENUM('accuracy_drop', 'accuracy_spike', 'error_surge', 'task_failure') 
        NOT NULL COMMENT '异常类型',
    severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium' COMMENT '严重程度',
    task_id VARCHAR(36) COMMENT '关联任务ID',
    subject_id INT COMMENT '关联学科ID',
    metric_name VARCHAR(50) COMMENT '指标名称',
    expected_value DECIMAL(10,4) COMMENT '期望值',
    actual_value DECIMAL(10,4) COMMENT '实际值',
    deviation DECIMAL(10,4) COMMENT '偏差值',
    threshold DECIMAL(10,4) COMMENT '阈值',
    message TEXT COMMENT '异常描述',
    is_acknowledged TINYINT(1) DEFAULT 0 COMMENT '是否已确认',
    acknowledged_by INT COMMENT '确认人ID',
    acknowledged_at DATETIME COMMENT '确认时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_anomaly_type (anomaly_type),
    INDEX idx_severity (severity),
    INDEX idx_task_id (task_id),
    INDEX idx_created_at (created_at),
    INDEX idx_is_acknowledged (is_acknowledged)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='异常检测日志';
```

### 2.3 optimization_suggestions 表 (US-28)
```sql
CREATE TABLE optimization_suggestions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    suggestion_id VARCHAR(36) NOT NULL UNIQUE COMMENT '建议唯一标识',
    title VARCHAR(200) NOT NULL COMMENT '建议标题',
    problem_description TEXT COMMENT '问题描述',
    affected_subjects JSON COMMENT '影响学科列表',
    affected_question_types JSON COMMENT '影响题型列表',
    sample_count INT DEFAULT 0 COMMENT '相关样本数',
    suggestion_content TEXT COMMENT '优化建议内容',
    priority ENUM('low', 'medium', 'high') DEFAULT 'medium' COMMENT '优先级',
    status ENUM('pending', 'in_progress', 'completed', 'rejected') DEFAULT 'pending' COMMENT '状态',
    ai_model VARCHAR(50) COMMENT '生成模型',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优化建议表';
```

### 2.4 error_clusters 表 (US-27)
```sql
CREATE TABLE error_clusters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cluster_id VARCHAR(36) NOT NULL UNIQUE COMMENT '聚类唯一标识',
    label VARCHAR(100) NOT NULL COMMENT '聚类标签',
    description TEXT COMMENT '聚类描述',
    error_type VARCHAR(50) COMMENT '主要错误类型',
    sample_count INT DEFAULT 0 COMMENT '样本数量',
    representative_sample_id VARCHAR(36) COMMENT '代表性样本ID',
    keywords JSON COMMENT '关键词列表',
    ai_generated TINYINT(1) DEFAULT 1 COMMENT '是否AI生成',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_error_type (error_type),
    INDEX idx_sample_count (sample_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='错误聚类表';
```

### 2.5 test_plan_assignments 表 (US-13)
```sql
CREATE TABLE test_plan_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_id VARCHAR(36) NOT NULL UNIQUE COMMENT '分配唯一标识',
    plan_id VARCHAR(36) NOT NULL COMMENT '测试计划ID',
    user_id INT NOT NULL COMMENT '用户ID',
    role ENUM('owner', 'assignee', 'reviewer') DEFAULT 'assignee' COMMENT '角色',
    status ENUM('pending', 'in_progress', 'completed') DEFAULT 'pending' COMMENT '状态',
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME COMMENT '完成时间',
    INDEX idx_plan_id (plan_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    UNIQUE KEY uk_plan_user (plan_id, user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试计划分配表';
```

---

## 三、功能模块实现方案

### 3.1 错误样本库 (US-19)

#### 后端服务: services/error_sample_service.py

```python
"""
错误样本服务模块 (US-19)

提供错误样本的收集、查询、分类和管理功能。
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from .database_service import AppDatabaseService


class ErrorSampleService:
    """错误样本服务类"""
    
    @staticmethod
    def collect_samples_from_task(task_id: str) -> Dict[str, Any]:
        """
        从批量任务中收集错误样本 (US-19.1)
        
        Args:
            task_id: 批量任务ID
            
        Returns:
            dict: {collected: int, skipped: int}
        """
        pass
    
    @staticmethod
    def get_samples(
        page: int = 1,
        page_size: int = 20,
        error_type: str = None,
        status: str = None,
        subject_id: int = None,
        cluster_id: str = None
    ) -> Dict[str, Any]:
        """
        获取错误样本列表 (US-19.2, US-19.3)
        
        支持按错误类型、状态、学科、聚类筛选。
        """
        pass
    
    @staticmethod
    def get_sample_detail(sample_id: str) -> Optional[Dict[str, Any]]:
        """获取样本详情 (US-19.3)"""
        pass
    
    @staticmethod
    def update_sample_status(
        sample_ids: List[str], 
        status: str, 
        notes: str = None
    ) -> int:
        """批量更新样本状态 (US-19.4, US-19.5)"""
        pass
    
    @staticmethod
    def export_samples(
        filters: Dict[str, Any],
        format: str = 'xlsx'
    ) -> str:
        """导出错误样本 (US-22.5)"""
        pass
```

#### 路由: routes/error_samples.py
```python
"""错误样本库路由模块"""
from flask import Blueprint, request, jsonify
from services.error_sample_service import ErrorSampleService

error_samples_bp = Blueprint('error_samples', __name__)

@error_samples_bp.route('/api/error-samples', methods=['GET'])
def get_samples():
    """获取错误样本列表"""
    pass

@error_samples_bp.route('/api/error-samples/<sample_id>', methods=['GET'])
def get_sample_detail(sample_id):
    """获取样本详情"""
    pass

@error_samples_bp.route('/api/error-samples/batch-status', methods=['PUT'])
def batch_update_status():
    """批量更新状态"""
    pass

@error_samples_bp.route('/api/error-samples/collect', methods=['POST'])
def collect_from_task():
    """从任务收集样本"""
    pass

@error_samples_bp.route('/api/error-samples/export', methods=['POST'])
def export_samples():
    """导出样本"""
    pass
```

#### 前端模块: static/js/modules/error-samples.js
```javascript
/**
 * 错误样本库模块 (US-19)
 * @module ErrorSamples
 */

/**
 * 错误样本API
 */
export const ErrorSamplesAPI = {
    /**
     * 获取样本列表
     * @param {Object} params - 查询参数
     * @returns {Promise<Object>}
     */
    getSamples: (params) => {
        const query = new URLSearchParams(params).toString();
        return fetch(`/api/error-samples?${query}`).then(r => r.json());
    },
    
    /**
     * 获取样本详情
     * @param {string} sampleId - 样本ID
     * @returns {Promise<Object>}
     */
    getDetail: (sampleId) => 
        fetch(`/api/error-samples/${sampleId}`).then(r => r.json()),
    
    /**
     * 批量更新状态
     * @param {string[]} sampleIds - 样本ID列表
     * @param {string} status - 新状态
     * @param {string} notes - 备注
     * @returns {Promise<Object>}
     */
    batchUpdateStatus: (sampleIds, status, notes) =>
        fetch('/api/error-samples/batch-status', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sample_ids: sampleIds, status, notes })
        }).then(r => r.json()),
    
    /**
     * 从任务收集样本
     * @param {string} taskId - 任务ID
     * @returns {Promise<Object>}
     */
    collectFromTask: (taskId) =>
        fetch('/api/error-samples/collect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: taskId })
        }).then(r => r.json()),
    
    /**
     * 导出样本
     * @param {Object} filters - 筛选条件
     * @param {string} format - 导出格式
     * @returns {Promise<Object>}
     */
    export: (filters, format = 'xlsx') =>
        fetch('/api/error-samples/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filters, format })
        }).then(r => r.json())
};

/**
 * 渲染错误样本列表
 * @param {Array} samples - 样本数据
 * @param {HTMLElement} container - 容器元素
 */
export function renderSampleList(samples, container) {
    // 实现列表渲染
}

/**
 * 渲染样本详情弹窗
 * @param {Object} sample - 样本数据
 */
export function showSampleDetail(sample) {
    // 实现详情弹窗
}
```

---

### 3.2 图片对比查看 (US-23)

#### 后端服务: services/image_compare_service.py
```python
"""
图片对比服务模块 (US-23)

提供作业图片与识别结果的对比查看功能。
"""
from typing import Optional, Dict, Any, List

from .database_service import AppDatabaseService, DatabaseService
from .config_service import ConfigService


class ImageCompareService:
    """图片对比服务类"""
    
    @staticmethod
    def get_homework_image(homework_id: str) -> Optional[Dict[str, Any]]:
        """
        获取作业图片信息 (US-23.1)
        
        Args:
            homework_id: 作业ID
            
        Returns:
            dict: {
                homework_id, pic_url, homework_result,
                base_answer, ai_answer, errors
            }
        """
        pass
    
    @staticmethod
    def get_task_images(
        task_id: str, 
        page: int = 1, 
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        获取任务下所有作业图片列表
        
        用于切换上一题/下一题 (US-23.5)
        """
        pass
    
    @staticmethod
    def get_error_regions(
        homework_id: str,
        errors: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        计算错误区域坐标 (US-23.3)
        
        用于在图片上高亮标记错误位置。
        """
        pass
```

#### 前端模块: static/js/modules/image-compare.js
```javascript
/**
 * 图片对比模块 (US-23)
 * @module ImageCompare
 */

/**
 * 图片对比查看器类
 */
export class ImageCompareViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.currentIndex = 0;
        this.images = [];
        this.scale = 1;
        this.position = { x: 0, y: 0 };
        this.isDragging = false;
    }
    
    /**
     * 加载图片数据
     * @param {string} taskId - 任务ID
     */
    async loadImages(taskId) {
        // 加载任务下所有图片
    }
    
    /**
     * 显示指定索引的图片
     * @param {number} index - 图片索引
     */
    showImage(index) {
        // 显示图片和识别结果
    }
    
    /**
     * 缩放图片 (US-23.2)
     * @param {number} delta - 缩放增量
     */
    zoom(delta) {
        this.scale = Math.max(0.5, Math.min(3, this.scale + delta));
        this.updateTransform();
    }
    
    /**
     * 拖拽图片 (US-23.2)
     */
    enableDrag() {
        // 实现拖拽功能
    }
    
    /**
     * 高亮错误区域 (US-23.3)
     * @param {Array} errors - 错误列表
     */
    highlightErrors(errors) {
        // 在图片上绘制红色边框
    }
    
    /**
     * 切换上一题 (US-23.5)
     */
    prev() {
        if (this.currentIndex > 0) {
            this.showImage(--this.currentIndex);
        }
    }
    
    /**
     * 切换下一题 (US-23.5)
     */
    next() {
        if (this.currentIndex < this.images.length - 1) {
            this.showImage(++this.currentIndex);
        }
    }
}
```

---

### 3.3 异常检测 (US-26)

#### 后端服务: services/anomaly_service.py

```python
"""
异常检测服务模块 (US-26)

提供准确率异常自动检测和告警功能。
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import statistics

from .database_service import AppDatabaseService


class AnomalyService:
    """异常检测服务类"""
    
    # 默认阈值：2个标准差
    DEFAULT_THRESHOLD_SIGMA = 2.0
    
    @staticmethod
    def detect_accuracy_anomaly(
        task_id: str,
        threshold_sigma: float = None
    ) -> Optional[Dict[str, Any]]:
        """
        检测准确率异常 (US-26.1)
        
        计算历史准确率的均值和标准差，
        判断当前任务准确率是否偏离均值超过阈值。
        
        Args:
            task_id: 批量任务ID
            threshold_sigma: 阈值（标准差倍数），默认2
            
        Returns:
            dict: 异常信息，无异常返回 None
        """
        pass
    
    @staticmethod
    def detect_error_surge(
        task_id: str,
        error_type: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        检测错误激增
        
        某类错误数量突然增加时触发告警。
        """
        pass
    
    @staticmethod
    def get_anomaly_logs(
        page: int = 1,
        page_size: int = 20,
        anomaly_type: str = None,
        severity: str = None,
        is_acknowledged: bool = None
    ) -> Dict[str, Any]:
        """获取异常日志列表 (US-26.5)"""
        pass
    
    @staticmethod
    def acknowledge_anomaly(
        anomaly_id: str,
        user_id: int
    ) -> bool:
        """确认异常"""
        pass
    
    @staticmethod
    def set_threshold(threshold_sigma: float) -> None:
        """设置异常阈值 (US-26.3)"""
        pass
    
    @staticmethod
    def _calculate_statistics(values: List[float]) -> Dict[str, float]:
        """
        计算统计值
        
        Returns:
            dict: {mean, std, min, max}
        """
        if not values or len(values) < 2:
            return {'mean': 0, 'std': 0, 'min': 0, 'max': 0}
        
        return {
            'mean': statistics.mean(values),
            'std': statistics.stdev(values),
            'min': min(values),
            'max': max(values)
        }
```

---

### 3.4 错误聚类 (US-27)

#### 后端服务: services/clustering_service.py
```python
"""
错误聚类服务模块 (US-27)

使用AI对相似错误进行自动聚类分析。
"""
import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from .database_service import AppDatabaseService
from .llm_service import LLMService


class ClusteringService:
    """错误聚类服务类"""
    
    @staticmethod
    def cluster_errors(
        error_type: str = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        对错误样本进行聚类 (US-27.1)
        
        使用 DeepSeek 分析错误样本的相似性，
        自动生成聚类标签。
        
        Args:
            error_type: 限定错误类型
            limit: 最大样本数
            
        Returns:
            dict: {
                clusters: [{cluster_id, label, sample_count, samples}],
                total_samples: int
            }
        """
        pass
    
    @staticmethod
    def get_clusters(
        error_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        获取聚类列表 (US-27.2)
        
        Returns:
            list: 聚类列表，包含样本数量和代表性样本
        """
        pass
    
    @staticmethod
    def get_cluster_samples(
        cluster_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取聚类下的样本列表 (US-27.3)"""
        pass
    
    @staticmethod
    def merge_clusters(
        cluster_ids: List[str],
        new_label: str
    ) -> str:
        """合并聚类 (US-27.4)"""
        pass
    
    @staticmethod
    def split_cluster(
        cluster_id: str,
        sample_ids: List[str],
        new_label: str
    ) -> str:
        """拆分聚类 (US-27.4)"""
        pass
    
    @staticmethod
    def update_cluster_label(
        cluster_id: str,
        label: str
    ) -> bool:
        """更新聚类标签 (US-27.5)"""
        pass
    
    @staticmethod
    def _generate_cluster_prompt(samples: List[Dict]) -> str:
        """生成聚类分析的 Prompt"""
        return f"""请分析以下错误样本，将相似的错误归类，并为每个类别生成简短的标签。

错误样本：
{json.dumps(samples, ensure_ascii=False, indent=2)}

请返回JSON格式：
{{
    "clusters": [
        {{
            "label": "聚类标签",
            "description": "聚类描述",
            "sample_indices": [0, 1, 2]
        }}
    ]
}}"""
```

---

### 3.5 优化建议 (US-28)

#### 后端服务: services/optimization_service.py
```python
"""
优化建议服务模块 (US-28)

使用AI分析错误样本，生成针对性的优化建议。
"""
import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from .database_service import AppDatabaseService
from .llm_service import LLMService


class OptimizationService:
    """优化建议服务类"""
    
    @staticmethod
    def generate_suggestions(
        sample_ids: List[str] = None,
        error_type: str = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        生成优化建议 (US-28.1, US-28.2)
        
        AI分析错误样本，识别主要问题并生成优化方案。
        
        Args:
            sample_ids: 指定样本ID列表
            error_type: 限定错误类型
            limit: 最大样本数
            
        Returns:
            dict: {
                suggestions: [{
                    title, problem_description,
                    affected_subjects, affected_question_types,
                    suggestion_content, priority
                }],
                analyzed_samples: int
            }
        """
        pass
    
    @staticmethod
    def get_suggestions(
        status: str = None,
        priority: str = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取优化建议列表 (US-28.5)"""
        pass
    
    @staticmethod
    def update_suggestion_status(
        suggestion_id: str,
        status: str
    ) -> bool:
        """更新建议状态 (US-28.3)"""
        pass
    
    @staticmethod
    def export_suggestions(
        suggestion_ids: List[str] = None,
        format: str = 'md'
    ) -> str:
        """导出优化建议报告 (US-28.4)"""
        pass
    
    @staticmethod
    def _generate_optimization_prompt(
        samples: List[Dict],
        error_distribution: Dict[str, int]
    ) -> str:
        """生成优化建议的 Prompt"""
        return f"""请分析以下AI批改错误样本，识别主要问题并提供优化建议。

错误类型分布：
{json.dumps(error_distribution, ensure_ascii=False)}

错误样本（Top 5）：
{json.dumps(samples[:5], ensure_ascii=False, indent=2)}

请返回JSON格式：
{{
    "suggestions": [
        {{
            "title": "问题标题",
            "problem_description": "问题描述",
            "affected_subjects": [3, 4],
            "affected_question_types": ["填空题", "选择题"],
            "suggestion_content": "具体优化建议",
            "priority": "high"
        }}
    ]
}}"""
```

---

### 3.6 多维度数据下钻 (US-21)

#### 后端服务: 扩展 dashboard_service.py
```python
@staticmethod
def get_drilldown_data(
    level: str,
    parent_id: str = None,
    filters: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    获取下钻数据 (US-21)
    
    支持下钻路径：总体 → 学科 → 书本 → 页码 → 题目
    
    Args:
        level: 当前层级 overall|subject|book|page|question
        parent_id: 父级ID
        filters: 筛选条件
        
    Returns:
        dict: {
            level, parent_id, breadcrumb,
            data: [{id, name, accuracy, question_count, error_count}],
            summary: {total_accuracy, total_questions}
        }
    """
    pass
```

#### 前端模块: static/js/modules/drilldown.js
```javascript
/**
 * 数据下钻模块 (US-21)
 * @module Drilldown
 */

/**
 * 下钻层级定义
 */
const DRILLDOWN_LEVELS = ['overall', 'subject', 'book', 'page', 'question'];

/**
 * 下钻导航器类
 */
export class DrilldownNavigator {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.currentLevel = 'overall';
        this.breadcrumb = [];
        this.filters = {};
    }
    
    /**
     * 加载当前层级数据
     */
    async loadData() {
        const parentId = this.breadcrumb.length > 0 
            ? this.breadcrumb[this.breadcrumb.length - 1].id 
            : null;
        
        const response = await fetch('/api/dashboard/drilldown', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                level: this.currentLevel,
                parent_id: parentId,
                filters: this.filters
            })
        }).then(r => r.json());
        
        if (response.success) {
            this.renderData(response.data);
            this.renderBreadcrumb();
        }
    }
    
    /**
     * 下钻到下一层级 (US-21.1)
     * @param {string} id - 当前项ID
     * @param {string} name - 当前项名称
     */
    drillDown(id, name) {
        const currentIndex = DRILLDOWN_LEVELS.indexOf(this.currentLevel);
        if (currentIndex < DRILLDOWN_LEVELS.length - 1) {
            this.breadcrumb.push({ level: this.currentLevel, id, name });
            this.currentLevel = DRILLDOWN_LEVELS[currentIndex + 1];
            this.loadData();
        }
    }
    
    /**
     * 返回上层 (US-21.3)
     * @param {number} targetIndex - 目标层级索引
     */
    goBack(targetIndex) {
        if (targetIndex < this.breadcrumb.length) {
            this.breadcrumb = this.breadcrumb.slice(0, targetIndex);
            this.currentLevel = targetIndex === 0 
                ? 'overall' 
                : DRILLDOWN_LEVELS[DRILLDOWN_LEVELS.indexOf(this.breadcrumb[targetIndex - 1].level) + 1];
            this.loadData();
        }
    }
    
    /**
     * 渲染面包屑导航 (US-21.3)
     */
    renderBreadcrumb() {
        // 实现面包屑渲染
    }
    
    /**
     * 渲染数据列表 (US-21.2)
     */
    renderData(data) {
        // 实现数据渲染
    }
    
    /**
     * 导出当前层级数据 (US-21.5)
     */
    async exportData() {
        // 实现导出功能
    }
}
```

---

## 四、前端UI组件设计

### 4.1 错误样本列表组件

```html
<!-- 错误样本列表区域 -->
<div class="section error-samples-section">
    <div class="section-header">
        <h3>错误样本库</h3>
        <div class="section-actions">
            <select id="errorTypeFilter" onchange="filterSamples()">
                <option value="">全部类型</option>
                <option value="识别错误-判断错误">识别错误-判断错误</option>
                <option value="识别正确-判断错误">识别正确-判断错误</option>
                <option value="缺失题目">缺失题目</option>
                <option value="AI识别幻觉">AI识别幻觉</option>
            </select>
            <select id="statusFilter" onchange="filterSamples()">
                <option value="">全部状态</option>
                <option value="pending">待分析</option>
                <option value="analyzed">已分析</option>
                <option value="fixed">已修复</option>
            </select>
            <button class="btn btn-secondary" onclick="exportSamples()">导出</button>
        </div>
    </div>
    
    <!-- 批量操作栏 -->
    <div class="batch-actions" id="batchActions" style="display: none;">
        <span class="selected-count">已选择 <span id="selectedCount">0</span> 项</span>
        <button class="btn btn-sm" onclick="batchMarkAnalyzed()">标记已分析</button>
        <button class="btn btn-sm" onclick="batchMarkFixed()">标记已修复</button>
        <button class="btn btn-sm btn-danger" onclick="batchIgnore()">忽略</button>
    </div>
    
    <!-- 样本列表 -->
    <div class="sample-list" id="sampleList">
        <!-- 动态渲染 -->
    </div>
    
    <!-- 分页 -->
    <div class="pagination" id="samplePagination"></div>
</div>
```

### 4.2 图片对比查看器组件
```html
<!-- 图片对比弹窗 -->
<div class="modal" id="imageCompareModal">
    <div class="modal-content modal-large">
        <div class="modal-header">
            <h3>图片对比查看</h3>
            <button class="close-btn" onclick="closeImageCompare()">&times;</button>
        </div>
        
        <div class="image-compare-container">
            <!-- 左侧：原图 -->
            <div class="image-panel">
                <div class="panel-header">原图</div>
                <div class="image-wrapper" id="originalImageWrapper">
                    <img id="originalImage" src="" alt="原图" />
                    <!-- 错误区域高亮层 -->
                    <div class="error-highlights" id="errorHighlights"></div>
                </div>
            </div>
            
            <!-- 右侧：识别结果 -->
            <div class="result-panel">
                <div class="panel-header">识别结果</div>
                <div class="result-content" id="recognitionResult">
                    <!-- 动态渲染识别结果 -->
                </div>
            </div>
        </div>
        
        <!-- 底部信息栏 -->
        <div class="compare-info-bar">
            <div class="answer-info">
                <div class="info-item">
                    <span class="label">基准答案:</span>
                    <span class="value" id="baseAnswer">-</span>
                </div>
                <div class="info-item">
                    <span class="label">AI答案:</span>
                    <span class="value" id="aiAnswer">-</span>
                </div>
                <div class="info-item">
                    <span class="label">错误类型:</span>
                    <span class="value tag tag-error" id="errorType">-</span>
                </div>
            </div>
            
            <!-- 导航按钮 -->
            <div class="nav-buttons">
                <button class="btn btn-secondary" id="prevBtn" onclick="prevImage()">
                    上一题
                </button>
                <span class="nav-info">
                    <span id="currentIndex">1</span> / <span id="totalCount">10</span>
                </span>
                <button class="btn btn-secondary" id="nextBtn" onclick="nextImage()">
                    下一题
                </button>
            </div>
        </div>
        
        <!-- 缩放控制 -->
        <div class="zoom-controls">
            <button onclick="zoomOut()">-</button>
            <span id="zoomLevel">100%</span>
            <button onclick="zoomIn()">+</button>
            <button onclick="resetZoom()">重置</button>
        </div>
    </div>
</div>
```

### 4.3 异常检测面板组件
```html
<!-- 异常检测面板 -->
<div class="section anomaly-section">
    <div class="section-header">
        <h3>异常检测</h3>
        <div class="section-actions">
            <label>
                阈值:
                <input type="number" id="anomalyThreshold" value="2" 
                       min="1" max="5" step="0.5" style="width: 60px;" />
                σ
            </label>
            <button class="btn btn-sm" onclick="saveThreshold()">保存</button>
        </div>
    </div>
    
    <!-- 异常统计 -->
    <div class="anomaly-stats">
        <div class="stat-card">
            <div class="stat-value" id="unacknowledgedCount">0</div>
            <div class="stat-label">待确认</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="todayAnomalyCount">0</div>
            <div class="stat-label">今日异常</div>
        </div>
    </div>
    
    <!-- 异常列表 -->
    <div class="anomaly-list" id="anomalyList">
        <!-- 动态渲染 -->
    </div>
</div>
```

---

## 五、CSS样式设计

### 5.1 错误样本列表样式
```css
/* 错误样本列表 */
.sample-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.sample-item {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    background: #f5f5f7;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.15s ease;
}

.sample-item:hover {
    background: #e5e5e5;
}

.sample-item.selected {
    background: #e3f2fd;
    border: 1px solid #1565c0;
}

.sample-checkbox {
    margin-right: 12px;
}

.sample-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.sample-title {
    font-weight: 500;
    color: #1d1d1f;
}

.sample-meta {
    font-size: 12px;
    color: #86868b;
}

.sample-error-type {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
}

.sample-error-type.high {
    background: #ffeef0;
    color: #d73a49;
}

.sample-error-type.medium {
    background: #fff3e0;
    color: #e65100;
}

.sample-error-type.low {
    background: #e3f9e5;
    color: #1e7e34;
}

/* 批量操作栏 */
.batch-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: #e3f2fd;
    border-radius: 8px;
    margin-bottom: 12px;
}

.selected-count {
    font-weight: 500;
    color: #1565c0;
}
```

### 5.2 图片对比查看器样式
```css
/* 图片对比容器 */
.image-compare-container {
    display: flex;
    gap: 16px;
    height: 500px;
}

.image-panel, .result-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    border: 1px solid #e5e5e5;
    border-radius: 8px;
    overflow: hidden;
}

.panel-header {
    padding: 12px 16px;
    background: #f5f5f7;
    font-weight: 500;
    border-bottom: 1px solid #e5e5e5;
}

.image-wrapper {
    flex: 1;
    position: relative;
    overflow: auto;
    background: #fafafa;
}

.image-wrapper img {
    max-width: none;
    cursor: grab;
    transition: transform 0.1s ease;
}

.image-wrapper img:active {
    cursor: grabbing;
}

/* 错误高亮层 */
.error-highlights {
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: none;
}

.error-highlight {
    position: absolute;
    border: 2px solid #d73a49;
    background: rgba(215, 58, 73, 0.1);
    border-radius: 4px;
}

/* 底部信息栏 */
.compare-info-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    background: #f5f5f7;
    border-top: 1px solid #e5e5e5;
}

.answer-info {
    display: flex;
    gap: 24px;
}

.info-item {
    display: flex;
    align-items: center;
    gap: 8px;
}

.info-item .label {
    color: #86868b;
    font-size: 13px;
}

.info-item .value {
    font-weight: 500;
}

/* 导航按钮 */
.nav-buttons {
    display: flex;
    align-items: center;
    gap: 12px;
}

.nav-info {
    color: #86868b;
    font-size: 13px;
}

/* 缩放控制 */
.zoom-controls {
    position: absolute;
    bottom: 80px;
    right: 20px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.zoom-controls button {
    width: 28px;
    height: 28px;
    border: 1px solid #d2d2d7;
    border-radius: 4px;
    background: #fff;
    cursor: pointer;
}

.zoom-controls button:hover {
    background: #f5f5f7;
}
```

---

## 六、API接口设计

### 6.1 错误样本库 API
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/error-samples | 获取样本列表 |
| GET | /api/error-samples/:id | 获取样本详情 |
| PUT | /api/error-samples/batch-status | 批量更新状态 |
| POST | /api/error-samples/collect | 从任务收集样本 |
| POST | /api/error-samples/export | 导出样本 |

### 6.2 图片对比 API
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/image-compare/:homework_id | 获取作业图片信息 |
| GET | /api/image-compare/task/:task_id | 获取任务下所有图片 |

### 6.3 异常检测 API
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/anomaly/logs | 获取异常日志 |
| POST | /api/anomaly/detect | 手动触发检测 |
| PUT | /api/anomaly/:id/acknowledge | 确认异常 |
| PUT | /api/anomaly/threshold | 设置阈值 |

### 6.4 错误聚类 API
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/clusters | 获取聚类列表 |
| POST | /api/clusters/analyze | 执行聚类分析 |
| GET | /api/clusters/:id/samples | 获取聚类样本 |
| POST | /api/clusters/merge | 合并聚类 |
| POST | /api/clusters/split | 拆分聚类 |
| PUT | /api/clusters/:id/label | 更新标签 |

### 6.5 优化建议 API
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/optimization/suggestions | 获取建议列表 |
| POST | /api/optimization/generate | 生成优化建议 |
| PUT | /api/optimization/:id/status | 更新建议状态 |
| POST | /api/optimization/export | 导出建议报告 |

### 6.6 数据下钻 API
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/dashboard/drilldown | 获取下钻数据 |
| POST | /api/dashboard/drilldown/export | 导出当前层级数据 |

---

## 七、实现步骤

### 第一阶段：基础设施 (1-2天)
1. 创建数据库表 (error_samples, anomaly_logs, error_clusters, optimization_suggestions)
2. 创建服务层基础类
3. 注册路由蓝图

### 第二阶段：错误样本库 (2-3天)
1. 实现 ErrorSampleService
2. 实现错误样本路由
3. 实现前端列表和详情UI
4. 实现批量操作功能

### 第三阶段：图片对比 (1-2天)
1. 实现 ImageCompareService
2. 实现图片对比路由
3. 实现前端对比查看器
4. 实现缩放和拖拽功能

### 第四阶段：异常检测 (1-2天)
1. 实现 AnomalyService
2. 实现异常检测路由
3. 实现前端异常面板
4. 集成到批量评估流程

### 第五阶段：高级分析 (2-3天)
1. 实现错误聚类功能
2. 实现优化建议生成
3. 实现数据下钻功能
4. 完善导出功能

---

## 八、测试计划

### 8.1 单元测试
- 服务层方法测试
- 数据库操作测试
- AI调用Mock测试

### 8.2 集成测试
- API端点测试
- 前后端联调测试

### 8.3 性能测试
- 大数据量列表加载
- 图片加载性能
- AI分析响应时间
