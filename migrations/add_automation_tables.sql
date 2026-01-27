-- =====================================================
-- 自动化调度相关表
-- 创建时间: 2026-01-26
-- =====================================================

-- =====================================================
-- 30. 自动化任务执行日志表
-- =====================================================
DROP TABLE IF EXISTS `automation_logs`;
CREATE TABLE `automation_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `log_id` VARCHAR(36) NOT NULL UNIQUE COMMENT '日志唯一标识',
    `task_type` VARCHAR(50) NOT NULL COMMENT '任务类型: test_plan, daily_report, stats_snapshot, ai_analysis',
    `related_id` VARCHAR(36) COMMENT '关联ID（计划ID/任务ID等）',
    `status` ENUM('pending', 'running', 'completed', 'failed', 'skipped') DEFAULT 'pending' COMMENT '执行状态',
    `message` TEXT COMMENT '执行消息/错误信息',
    `details` JSON COMMENT '详细信息',
    `duration_seconds` INT COMMENT '执行耗时（秒）',
    `retry_count` INT DEFAULT 0 COMMENT '重试次数',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `completed_at` DATETIME COMMENT '完成时间',
    INDEX `idx_task_type` (`task_type`),
    INDEX `idx_related_id` (`related_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='自动化任务执行日志表';

-- =====================================================
-- 31. 自动化任务配置表
-- =====================================================
DROP TABLE IF EXISTS `automation_configs`;
CREATE TABLE `automation_configs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `task_type` VARCHAR(50) NOT NULL UNIQUE COMMENT '任务类型',
    `name` VARCHAR(100) NOT NULL COMMENT '任务名称',
    `description` VARCHAR(500) COMMENT '任务描述',
    `trigger_type` ENUM('cron', 'event', 'manual') DEFAULT 'cron' COMMENT '触发类型',
    `cron_expression` VARCHAR(100) COMMENT 'Cron表达式',
    `enabled` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    `config` JSON COMMENT '任务配置',
    `last_run_at` DATETIME COMMENT '上次执行时间',
    `next_run_at` DATETIME COMMENT '下次执行时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_enabled` (`enabled`),
    INDEX `idx_trigger_type` (`trigger_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='自动化任务配置表';

-- 插入默认任务配置
INSERT INTO `automation_configs` (`task_type`, `name`, `description`, `trigger_type`, `cron_expression`, `enabled`) VALUES
('daily_report', '日报自动生成', '每天18:00自动生成测试日报', 'cron', '0 18 * * *', 1),
('stats_snapshot', '统计快照', '每天00:00保存统计数据快照', 'cron', '0 0 * * *', 1),
('ai_analysis', 'AI数据分析', '批量评估完成后自动分析错误模式', 'event', NULL, 1);

-- =====================================================
-- 完成提示
-- =====================================================
-- 新增 2 张表：
-- 30. automation_logs - 自动化任务执行日志表
-- 31. automation_configs - 自动化任务配置表
