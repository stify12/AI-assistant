-- 每日统计缓存表
CREATE TABLE IF NOT EXISTS `daily_statistics` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `stat_date` DATE NOT NULL COMMENT '统计日期',
    `subject_id` INT COMMENT '学科ID，NULL表示全部',
    `task_count` INT DEFAULT 0 COMMENT '任务数',
    `homework_count` INT DEFAULT 0 COMMENT '作业数',
    `question_count` INT DEFAULT 0 COMMENT '题目数',
    `correct_count` INT DEFAULT 0 COMMENT '正确数',
    `accuracy` DECIMAL(5,4) DEFAULT 0 COMMENT '准确率',
    `error_distribution` JSON COMMENT '错误类型分布',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_date_subject` (`stat_date`, `subject_id`),
    INDEX `idx_stat_date` (`stat_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日统计缓存表';

-- 测试日报表
CREATE TABLE IF NOT EXISTS `daily_reports` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `report_id` VARCHAR(36) NOT NULL UNIQUE COMMENT '日报唯一标识',
    `report_date` DATE NOT NULL COMMENT '日报日期',
    `task_completed` INT DEFAULT 0 COMMENT '完成任务数',
    `task_planned` INT DEFAULT 0 COMMENT '计划任务数',
    `accuracy` DECIMAL(5,4) DEFAULT 0 COMMENT '当日准确率',
    `accuracy_change` DECIMAL(5,4) DEFAULT 0 COMMENT '准确率变化（与昨日对比）',
    `accuracy_week_change` DECIMAL(5,4) DEFAULT 0 COMMENT '准确率变化（与上周同日对比）',
    `top_errors` JSON COMMENT '主要错误类型 Top 5',
    `new_error_types` JSON COMMENT '今日新增错误类型',
    `high_freq_errors` JSON COMMENT '高频错误题目',
    `tomorrow_plan` JSON COMMENT '明日计划任务列表',
    `anomalies` JSON COMMENT '异常情况列表',
    `model_version` VARCHAR(100) COMMENT '当日使用的AI模型版本',
    `ai_summary` TEXT COMMENT 'AI生成的总结',
    `raw_content` TEXT COMMENT '完整日报内容（Markdown）',
    `generated_by` ENUM('auto', 'manual') DEFAULT 'auto' COMMENT '生成方式',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY `uk_report_date` (`report_date`),
    INDEX `idx_report_date` (`report_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试日报表';
