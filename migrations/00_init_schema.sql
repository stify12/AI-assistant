-- AI Grading Platform 数据库初始化脚本
-- 此文件在Docker MySQL首次启动时自动执行

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 数据集表
CREATE TABLE IF NOT EXISTS `datasets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `dataset_id` varchar(36) NOT NULL,
  `name` varchar(200) DEFAULT NULL,
  `book_id` varchar(50) DEFAULT NULL,
  `book_name` varchar(200) DEFAULT NULL,
  `subject_id` int(11) DEFAULT NULL,
  `pages` json DEFAULT NULL,
  `question_count` int(11) DEFAULT 0,
  `description` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dataset_id` (`dataset_id`),
  KEY `idx_book_id` (`book_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 基准效果表
CREATE TABLE IF NOT EXISTS `baseline_effects` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `dataset_id` varchar(36) NOT NULL,
  `page_num` int(11) NOT NULL,
  `question_index` varchar(50) NOT NULL,
  `temp_index` int(11) DEFAULT 0,
  `question_type` varchar(50) DEFAULT 'choice',
  `answer` text,
  `user_answer` text,
  `is_correct` varchar(20) DEFAULT NULL,
  `extra_data` json DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_dataset_page` (`dataset_id`, `page_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 用户表
CREATE TABLE IF NOT EXISTS `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `api_keys` json DEFAULT NULL,
  `remember_token` varchar(100) DEFAULT NULL,
  `token_expires_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 会话表
CREATE TABLE IF NOT EXISTS `chat_sessions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `session_id` varchar(36) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `session_type` varchar(20) DEFAULT 'chat',
  `title` varchar(200) DEFAULT '新对话',
  `messages` json DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 测试计划表
CREATE TABLE IF NOT EXISTS `test_plans` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `plan_id` varchar(36) NOT NULL,
  `name` varchar(200) NOT NULL,
  `description` text,
  `subject_ids` json DEFAULT NULL,
  `target_count` int(11) DEFAULT 0,
  `completed_count` int(11) DEFAULT 0,
  `status` enum('draft','active','completed','archived') DEFAULT 'draft',
  `start_date` date DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_plan_id` (`plan_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 测试计划数据集关联表
CREATE TABLE IF NOT EXISTS `test_plan_datasets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `plan_id` varchar(36) NOT NULL,
  `dataset_id` varchar(36) NOT NULL,
  `added_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_plan_dataset` (`plan_id`, `dataset_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 测试计划任务关联表
CREATE TABLE IF NOT EXISTS `test_plan_tasks` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `plan_id` varchar(36) NOT NULL,
  `task_id` varchar(36) NOT NULL,
  `added_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_plan_task` (`plan_id`, `task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 数据集合集表
CREATE TABLE IF NOT EXISTS `dataset_collections` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `collection_id` varchar(36) NOT NULL,
  `name` varchar(200) NOT NULL,
  `description` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_collection_id` (`collection_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 合集数据集关联表
CREATE TABLE IF NOT EXISTS `collection_datasets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `collection_id` varchar(36) NOT NULL,
  `dataset_id` varchar(36) NOT NULL,
  `added_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_collection_dataset` (`collection_id`, `dataset_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 错误样本库表
CREATE TABLE IF NOT EXISTS `error_samples` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `sample_id` varchar(36) NOT NULL,
  `task_id` varchar(36) NOT NULL,
  `homework_id` varchar(50) NOT NULL,
  `dataset_id` varchar(36) DEFAULT NULL,
  `book_id` varchar(50) DEFAULT NULL,
  `book_name` varchar(200) DEFAULT NULL,
  `page_num` int(11) DEFAULT NULL,
  `question_index` varchar(50) NOT NULL,
  `subject_id` int(11) DEFAULT NULL,
  `error_type` varchar(50) NOT NULL,
  `base_answer` text,
  `base_user` text,
  `hw_user` text,
  `pic_path` varchar(500) DEFAULT NULL,
  `status` enum('pending','analyzed','fixed','ignored') DEFAULT 'pending',
  `notes` text,
  `cluster_id` varchar(36) DEFAULT NULL,
  `cluster_label` varchar(100) DEFAULT NULL,
  `mark_type` varchar(32) DEFAULT NULL,
  `mark_note` text,
  `marked_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sample_id` (`sample_id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_error_type` (`error_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 异常检测日志表
CREATE TABLE IF NOT EXISTS `anomaly_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `anomaly_id` varchar(36) NOT NULL,
  `anomaly_type` varchar(50) NOT NULL,
  `severity` enum('low','medium','high','critical') DEFAULT 'medium',
  `task_id` varchar(36) DEFAULT NULL,
  `subject_id` int(11) DEFAULT NULL,
  `metric_name` varchar(50) DEFAULT NULL,
  `expected_value` decimal(10,4) DEFAULT NULL,
  `actual_value` decimal(10,4) DEFAULT NULL,
  `deviation` decimal(10,4) DEFAULT NULL,
  `threshold` decimal(10,4) DEFAULT NULL,
  `message` text,
  `is_acknowledged` tinyint(1) DEFAULT 0,
  `acknowledged_by` int(11) DEFAULT NULL,
  `acknowledged_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_anomaly_id` (`anomaly_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 错误聚类表
CREATE TABLE IF NOT EXISTS `error_clusters` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cluster_id` varchar(36) NOT NULL,
  `label` varchar(100) NOT NULL,
  `description` text,
  `error_type` varchar(50) DEFAULT NULL,
  `sample_count` int(11) DEFAULT 0,
  `representative_sample_id` varchar(36) DEFAULT NULL,
  `keywords` json DEFAULT NULL,
  `ai_generated` tinyint(1) DEFAULT 1,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cluster_id` (`cluster_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 优化建议表
CREATE TABLE IF NOT EXISTS `optimization_suggestions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `suggestion_id` varchar(36) NOT NULL,
  `title` varchar(200) NOT NULL,
  `problem_description` text,
  `affected_subjects` json DEFAULT NULL,
  `affected_question_types` json DEFAULT NULL,
  `sample_count` int(11) DEFAULT 0,
  `suggestion_content` text,
  `priority` enum('low','medium','high') DEFAULT 'medium',
  `status` enum('pending','in_progress','completed','rejected') DEFAULT 'pending',
  `ai_model` varchar(50) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_suggestion_id` (`suggestion_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 任务分配表
CREATE TABLE IF NOT EXISTS `test_plan_assignments` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `plan_id` varchar(64) NOT NULL,
  `task_id` varchar(64) NOT NULL,
  `assignee_id` varchar(64) NOT NULL,
  `assignee_name` varchar(100) DEFAULT NULL,
  `assigned_by` varchar(64) DEFAULT 'system',
  `status` enum('pending','in_progress','completed','blocked') DEFAULT 'pending',
  `assigned_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `completed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_plan_task` (`plan_id`, `task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 任务评论表
CREATE TABLE IF NOT EXISTS `test_plan_comments` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `plan_id` varchar(64) NOT NULL,
  `task_id` varchar(64) NOT NULL,
  `user_id` varchar(64) NOT NULL DEFAULT 'anonymous',
  `content` text NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_plan_task` (`plan_id`, `task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
