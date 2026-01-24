-- 错误分析功能数据库表
-- 执行时间: 2026-01-24
-- 功能: US-19 错误样本库, US-26 异常检测, US-27 错误聚类, US-28 优化建议

-- 1. 错误样本库表 (US-19)
CREATE TABLE IF NOT EXISTS error_samples (
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
    status ENUM('pending', 'analyzed', 'fixed', 'ignored') DEFAULT 'pending',
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

-- 2. 异常检测日志表 (US-26)
CREATE TABLE IF NOT EXISTS anomaly_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    anomaly_id VARCHAR(36) NOT NULL UNIQUE COMMENT '异常唯一标识',
    anomaly_type VARCHAR(50) NOT NULL COMMENT '异常类型',
    severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
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


-- 3. 错误聚类表 (US-27)
CREATE TABLE IF NOT EXISTS error_clusters (
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

-- 4. 优化建议表 (US-28)
CREATE TABLE IF NOT EXISTS optimization_suggestions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    suggestion_id VARCHAR(36) NOT NULL UNIQUE COMMENT '建议唯一标识',
    title VARCHAR(200) NOT NULL COMMENT '建议标题',
    problem_description TEXT COMMENT '问题描述',
    affected_subjects JSON COMMENT '影响学科列表',
    affected_question_types JSON COMMENT '影响题型列表',
    sample_count INT DEFAULT 0 COMMENT '相关样本数',
    suggestion_content TEXT COMMENT '优化建议内容',
    priority ENUM('low', 'medium', 'high') DEFAULT 'medium',
    status ENUM('pending', 'in_progress', 'completed', 'rejected') DEFAULT 'pending',
    ai_model VARCHAR(50) COMMENT '生成模型',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优化建议表';

-- 5. 测试计划任务分配表 (US-13)
CREATE TABLE IF NOT EXISTS test_plan_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id VARCHAR(64) NOT NULL COMMENT '测试计划ID',
    task_id VARCHAR(64) NOT NULL COMMENT '任务ID',
    assignee_id VARCHAR(64) NOT NULL COMMENT '被分配人ID',
    assignee_name VARCHAR(100) COMMENT '被分配人名称',
    assigned_by VARCHAR(64) DEFAULT 'system' COMMENT '分配人',
    status ENUM('pending', 'in_progress', 'completed', 'blocked') DEFAULT 'pending',
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME COMMENT '完成时间',
    INDEX idx_plan_id (plan_id),
    INDEX idx_assignee_id (assignee_id),
    INDEX idx_status (status),
    UNIQUE KEY uk_plan_task (plan_id, task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试计划任务分配表';


-- 任务评论表 (US-13)
CREATE TABLE IF NOT EXISTS test_plan_comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id VARCHAR(64) NOT NULL,
    task_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL DEFAULT 'anonymous',
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_plan_task (plan_id, task_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 错误标记字段 (US-22)
ALTER TABLE error_samples 
ADD COLUMN IF NOT EXISTS mark_type VARCHAR(32) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS mark_note TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS marked_at DATETIME DEFAULT NULL;

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_mark_type ON error_samples(mark_type);
