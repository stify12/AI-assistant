-- AI 智能数据分析功能数据库表
-- 创建时间: 2026-01-24

-- 分析报告表
CREATE TABLE IF NOT EXISTS analysis_reports (
    report_id VARCHAR(36) PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL,
    status ENUM('pending', 'analyzing', 'completed', 'failed') DEFAULT 'pending',
    summary JSON COMMENT '摘要信息',
    drill_down_data JSON COMMENT '层级分析数据',
    error_patterns JSON COMMENT '错误模式列表',
    root_causes JSON COMMENT '根因分析结果',
    suggestions JSON COMMENT '优化建议列表',
    error_message TEXT COMMENT '错误信息（失败时）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    duration_seconds INT COMMENT '分析耗时（秒）',
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 自动化任务日志表
CREATE TABLE IF NOT EXISTS automation_logs (
    log_id VARCHAR(36) PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL COMMENT '任务类型: ai_analysis|daily_report|stats_snapshot',
    related_id VARCHAR(36) COMMENT '关联的任务ID',
    status ENUM('started', 'completed', 'failed') NOT NULL,
    message TEXT,
    duration_seconds INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_type (task_type),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
