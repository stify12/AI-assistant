-- AI 智能分析功能增强 - 数据库表结构
-- 创建时间: 2026-01-25
-- 版本: 2.0 (增强版)

-- ============================================
-- 1. 分析结果表 (analysis_results)
-- 存储各类型的 LLM 分析结果，支持缓存
-- ============================================
CREATE TABLE IF NOT EXISTS analysis_results (
    result_id VARCHAR(36) PRIMARY KEY,
    analysis_type ENUM('sample', 'cluster', 'task', 'subject', 'book', 'question_type', 'trend', 'compare') NOT NULL COMMENT '分析类型',
    target_id VARCHAR(100) NOT NULL COMMENT '分析目标ID（task_id/cluster_id/subject_name等）',
    task_id VARCHAR(36) COMMENT '关联的批量评估任务ID',
    analysis_data JSON NOT NULL COMMENT 'LLM 分析结果（JSON格式）',
    data_hash VARCHAR(64) NOT NULL COMMENT '源数据哈希值（用于缓存判断）',
    status ENUM('pending', 'analyzing', 'completed', 'failed') DEFAULT 'pending' COMMENT '分析状态',
    token_usage INT DEFAULT 0 COMMENT 'LLM token 消耗量',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type_target (analysis_type, target_id),
    INDEX idx_task_id (task_id),
    INDEX idx_data_hash (data_hash),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 2. 错误样本表 (error_samples)
-- 存储批量评估中的错误样本
-- ============================================
CREATE TABLE IF NOT EXISTS error_samples (
    sample_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL COMMENT '批量评估任务ID',
    cluster_id VARCHAR(36) COMMENT '所属聚类ID',
    homework_id VARCHAR(36) NOT NULL COMMENT '作业ID',
    book_name VARCHAR(100) COMMENT '书本名称',
    page_num INT COMMENT '页码',
    question_index INT COMMENT '题目索引',
    subject_id INT COMMENT '学科ID',
    error_type VARCHAR(50) COMMENT '错误类型',
    ai_answer TEXT COMMENT 'AI 识别/判断的答案',
    expected_answer TEXT COMMENT '期望的正确答案',
    base_user TEXT COMMENT '学生原始答案（用于不一致检测）',
    status ENUM('pending', 'analyzed', 'in_progress', 'fixed', 'ignored') DEFAULT 'pending' COMMENT '处理状态',
    llm_insight JSON COMMENT 'LLM 分析结果',
    note TEXT COMMENT '处理备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_cluster_id (cluster_id),
    INDEX idx_status (status),
    INDEX idx_base_user (base_user(100)),
    INDEX idx_error_type (error_type),
    INDEX idx_subject_id (subject_id),
    INDEX idx_book_name (book_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 3. 错误聚类表 (error_clusters)
-- 存储错误样本的聚类信息
-- ============================================
CREATE TABLE IF NOT EXISTS error_clusters (
    cluster_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL COMMENT '批量评估任务ID',
    cluster_key VARCHAR(200) NOT NULL COMMENT '聚类键（error_type_book_page_range）',
    cluster_name VARCHAR(200) COMMENT 'LLM 生成的聚类名称',
    cluster_description TEXT COMMENT 'LLM 生成的聚类描述',
    root_cause TEXT COMMENT 'LLM 分析的根因',
    severity ENUM('critical', 'high', 'medium', 'low') DEFAULT 'medium' COMMENT '严重程度',
    sample_count INT DEFAULT 0 COMMENT '样本数量',
    common_fix TEXT COMMENT 'LLM 生成的通用修复建议',
    pattern_insight TEXT COMMENT 'LLM 生成的模式洞察',
    representative_samples JSON COMMENT '代表性样本ID列表',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_severity (severity),
    UNIQUE KEY uk_task_cluster (task_id, cluster_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 4. 异常检测表 (analysis_anomalies)
-- 存储检测到的异常模式
-- ============================================
CREATE TABLE IF NOT EXISTS analysis_anomalies (
    anomaly_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL COMMENT '批量评估任务ID',
    anomaly_type ENUM('inconsistent_grading', 'recognition_unstable', 'continuous_error', 'batch_missing') NOT NULL COMMENT '异常类型',
    severity ENUM('critical', 'high', 'medium', 'low') DEFAULT 'medium' COMMENT '严重程度',
    base_user_answer TEXT COMMENT '学生原始答案',
    correct_cases JSON COMMENT '正确批改的作业列表',
    incorrect_cases JSON COMMENT '错误批改的作业列表',
    inconsistency_rate DECIMAL(5,4) COMMENT '不一致率',
    description TEXT COMMENT 'LLM 生成的异常描述',
    suggested_action TEXT COMMENT 'LLM 生成的改进建议',
    status ENUM('open', 'investigating', 'resolved', 'ignored') DEFAULT 'open' COMMENT '处理状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_type (anomaly_type),
    INDEX idx_severity (severity),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 5. LLM 调用日志表 (llm_call_logs)
-- 记录所有 LLM API 调用
-- ============================================
CREATE TABLE IF NOT EXISTS llm_call_logs (
    log_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) COMMENT '关联的任务ID',
    analysis_type VARCHAR(50) COMMENT '分析类型',
    target_id VARCHAR(100) COMMENT '分析目标',
    model VARCHAR(50) DEFAULT 'deepseek-v3.2' COMMENT '使用的模型',
    prompt_tokens INT DEFAULT 0 COMMENT 'Prompt token 数',
    completion_tokens INT DEFAULT 0 COMMENT '生成 token 数',
    total_tokens INT DEFAULT 0 COMMENT '总 token 数',
    duration_ms INT COMMENT '耗时（毫秒）',
    retry_count INT DEFAULT 0 COMMENT '重试次数',
    status ENUM('success', 'failed', 'timeout') NOT NULL COMMENT '调用状态',
    error_type VARCHAR(50) COMMENT '错误类型：timeout/api_error/parse_error/other',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_error_type (error_type),
    INDEX idx_model (model)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 6. 分析配置表 (analysis_config)
-- 存储分析相关的配置项
-- ============================================
CREATE TABLE IF NOT EXISTS analysis_config (
    config_key VARCHAR(50) PRIMARY KEY,
    config_value TEXT NOT NULL COMMENT '配置值',
    config_type ENUM('string', 'number', 'boolean', 'json') DEFAULT 'string' COMMENT '值类型',
    description VARCHAR(200) COMMENT '配置说明',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入默认配置
INSERT INTO analysis_config (config_key, config_value, config_type, description) VALUES
('llm_model', 'deepseek-v3.2', 'string', 'LLM 分析使用的模型'),
('temperature', '0.2', 'number', 'LLM 温度参数'),
('max_concurrent', '10', 'number', '最大并行调用数'),
('request_timeout', '60', 'number', '单次请求超时时间（秒）'),
('max_retries', '3', 'number', '最大重试次数'),
('batch_size', '5', 'number', '批量分析时每批数量'),
('auto_trigger', 'true', 'boolean', '是否自动触发分析'),
('daily_token_limit', '1000000', 'number', '每日 token 限制'),
('enabled_dimensions', '["subject","book","question_type","trend","compare"]', 'json', '启用的分析维度')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 7. 筛选预设表 (filter_presets)
-- 存储用户的筛选预设
-- ============================================
CREATE TABLE IF NOT EXISTS filter_presets (
    preset_id VARCHAR(36) PRIMARY KEY,
    preset_name VARCHAR(100) NOT NULL COMMENT '预设名称',
    preset_type ENUM('system', 'user') DEFAULT 'user' COMMENT '预设类型',
    query_string TEXT NOT NULL COMMENT '筛选查询字符串',
    user_id VARCHAR(36) COMMENT '用户ID（系统预设为空）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_preset_type (preset_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入系统预设
INSERT INTO filter_presets (preset_id, preset_name, preset_type, query_string) VALUES
('sys_pending', '待处理样本', 'system', 'status:pending'),
('sys_high_severity', '高严重度', 'system', 'severity:high OR severity:critical'),
('sys_ocr_error', 'OCR识别错误', 'system', 'error_type:识别错误-判断错误'),
('sys_scoring_error', '评分逻辑错误', 'system', 'error_type:识别正确-判断错误'),
('sys_missing', '缺失题目', 'system', 'error_type:缺失题目')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 8. 导出任务表 (export_tasks)
-- 存储报告导出任务
-- ============================================
CREATE TABLE IF NOT EXISTS export_tasks (
    export_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL COMMENT '关联的分析任务ID',
    export_format ENUM('pdf', 'excel') NOT NULL COMMENT '导出格式',
    sections JSON COMMENT '导出的章节',
    filters JSON COMMENT '筛选条件',
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending' COMMENT '导出状态',
    file_name VARCHAR(200) COMMENT '文件名',
    file_path VARCHAR(500) COMMENT '文件路径',
    file_size INT COMMENT '文件大小（字节）',
    error_message TEXT COMMENT '错误信息',
    expires_at DATETIME COMMENT '过期时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
