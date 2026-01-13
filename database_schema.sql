-- =====================================================
-- AI批改效果分析平台 数据库设计
-- 数据库: aiuser
-- 创建时间: 2026-01-12
-- =====================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 1. 系统配置表
-- =====================================================
DROP TABLE IF EXISTS `sys_config`;
CREATE TABLE `sys_config` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `config_key` VARCHAR(100) NOT NULL COMMENT '配置键',
  `config_value` TEXT COMMENT '配置值(JSON格式)',
  `description` VARCHAR(255) DEFAULT NULL COMMENT '配置说明',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- 插入默认配置
INSERT INTO `sys_config` (`config_key`, `config_value`, `description`) VALUES
('api_key', '"c53e8d2f-a38c-442c-92a1-d4313fc39793"', '豆包API密钥'),
('api_url', '"https://ark.cn-beijing.volces.com/api/v3/chat/completions"', 'API地址'),
('deepseek_api_key', '"sk-574652694a084537a81e26bb930735ce"', 'DeepSeek API密钥'),
('qwen_api_key', '"sk-53ae9126a4f54348b71c9bdbb2db504c"', '通义千问API密钥'),
('use_ai_compare', 'false', '是否使用AI比对');

-- =====================================================
-- 2. 提示词模板表
-- =====================================================
DROP TABLE IF EXISTS `prompt_templates`;
CREATE TABLE `prompt_templates` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` VARCHAR(100) NOT NULL COMMENT '提示词名称',
  `prompt_type` VARCHAR(50) NOT NULL DEFAULT 'general' COMMENT '类型: general/recognize/compare/evaluate',
  `content` TEXT NOT NULL COMMENT '提示词内容',
  `is_default` TINYINT(1) DEFAULT 0 COMMENT '是否默认',
  `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_prompt_type` (`prompt_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='提示词模板表';

-- =====================================================
-- 3. 数据集表
-- =====================================================
DROP TABLE IF EXISTS `datasets`;
CREATE TABLE `datasets` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `dataset_id` VARCHAR(32) NOT NULL COMMENT '数据集唯一标识',
  `book_id` VARCHAR(50) DEFAULT NULL COMMENT '关联书本ID',
  `book_name` VARCHAR(200) DEFAULT NULL COMMENT '书本名称',
  `subject_id` INT DEFAULT NULL COMMENT '学科ID',
  `pages` JSON COMMENT '包含的页码列表',
  `question_count` INT DEFAULT 0 COMMENT '题目总数',
  `description` VARCHAR(500) DEFAULT NULL COMMENT '数据集描述',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dataset_id` (`dataset_id`),
  KEY `idx_book_id` (`book_id`),
  KEY `idx_subject_id` (`subject_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据集表';

-- =====================================================
-- 4. 基准效果表（数据集的题目详情）
-- =====================================================
DROP TABLE IF EXISTS `baseline_effects`;
CREATE TABLE `baseline_effects` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `dataset_id` VARCHAR(32) NOT NULL COMMENT '所属数据集ID',
  `page_num` INT NOT NULL COMMENT '页码',
  `question_index` VARCHAR(20) NOT NULL COMMENT '题号',
  `temp_index` INT DEFAULT 0 COMMENT '临时索引(页内顺序)',
  `question_type` VARCHAR(50) DEFAULT 'choice' COMMENT '题目类型',
  `answer` TEXT COMMENT '标准答案',
  `user_answer` TEXT COMMENT '用户答案',
  `is_correct` VARCHAR(10) DEFAULT NULL COMMENT '是否正确: yes/no',
  `extra_data` JSON COMMENT '扩展数据',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_dataset_page` (`dataset_id`, `page_num`),
  KEY `idx_dataset_id` (`dataset_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='基准效果表';

-- =====================================================
-- 5. 批量评估任务表
-- =====================================================
DROP TABLE IF EXISTS `batch_tasks`;
CREATE TABLE `batch_tasks` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` VARCHAR(32) NOT NULL COMMENT '任务唯一标识',
  `name` VARCHAR(200) NOT NULL COMMENT '任务名称',
  `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/running/completed/failed',
  `homework_count` INT DEFAULT 0 COMMENT '作业数量',
  `overall_accuracy` DECIMAL(5,4) DEFAULT 0 COMMENT '整体准确率',
  `total_questions` INT DEFAULT 0 COMMENT '总题目数',
  `correct_questions` INT DEFAULT 0 COMMENT '正确题目数',
  `error_distribution` JSON COMMENT '错误分布统计',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `completed_at` DATETIME DEFAULT NULL COMMENT '完成时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_id` (`task_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='批量评估任务表';

-- =====================================================
-- 6. 批量任务作业项表
-- =====================================================
DROP TABLE IF EXISTS `batch_task_items`;
CREATE TABLE `batch_task_items` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` VARCHAR(32) NOT NULL COMMENT '所属任务ID',
  `homework_id` BIGINT NOT NULL COMMENT '作业ID(来源数据库)',
  `student_id` VARCHAR(50) DEFAULT NULL COMMENT '学生ID',
  `student_name` VARCHAR(100) DEFAULT NULL COMMENT '学生姓名',
  `homework_name` VARCHAR(200) DEFAULT NULL COMMENT '作业名称',
  `book_id` VARCHAR(50) DEFAULT NULL COMMENT '书本ID',
  `book_name` VARCHAR(200) DEFAULT NULL COMMENT '书本名称',
  `page_num` INT DEFAULT NULL COMMENT '页码',
  `pic_path` VARCHAR(500) DEFAULT NULL COMMENT '图片路径',
  `homework_result` LONGTEXT COMMENT 'AI批改结果JSON',
  `matched_dataset` VARCHAR(32) DEFAULT NULL COMMENT '匹配的数据集ID',
  `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/matched/evaluating/completed/failed',
  `accuracy` DECIMAL(5,4) DEFAULT NULL COMMENT '准确率',
  `total_questions` INT DEFAULT 0 COMMENT '题目数',
  `correct_count` INT DEFAULT 0 COMMENT '正确数',
  `error_count` INT DEFAULT 0 COMMENT '错误数',
  `evaluation_result` JSON COMMENT '评估结果详情',
  `error_message` VARCHAR(500) DEFAULT NULL COMMENT '错误信息',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_homework_id` (`homework_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='批量任务作业项表';

-- =====================================================
-- 7. 评估错误详情表
-- =====================================================
DROP TABLE IF EXISTS `evaluation_errors`;
CREATE TABLE `evaluation_errors` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_item_id` INT UNSIGNED NOT NULL COMMENT '所属任务项ID',
  `question_index` VARCHAR(20) NOT NULL COMMENT '题号',
  `error_type` VARCHAR(50) NOT NULL COMMENT '错误类型',
  `severity` VARCHAR(20) DEFAULT 'medium' COMMENT '严重程度: high/medium/low',
  `base_answer` TEXT COMMENT '基准标准答案',
  `base_user_answer` TEXT COMMENT '基准用户答案',
  `base_correct` VARCHAR(10) DEFAULT NULL COMMENT '基准判断结果',
  `ai_answer` TEXT COMMENT 'AI标准答案',
  `ai_user_answer` TEXT COMMENT 'AI用户答案',
  `ai_correct` VARCHAR(10) DEFAULT NULL COMMENT 'AI判断结果',
  `explanation` TEXT COMMENT '错误说明',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_task_item_id` (`task_item_id`),
  KEY `idx_error_type` (`error_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评估错误详情表';

-- =====================================================
-- 8. Prompt优化任务表
-- =====================================================
DROP TABLE IF EXISTS `prompt_tasks`;
CREATE TABLE `prompt_tasks` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` VARCHAR(32) NOT NULL COMMENT '任务唯一标识',
  `name` VARCHAR(200) NOT NULL COMMENT '任务名称',
  `original_prompt` TEXT COMMENT '原始提示词',
  `optimized_prompt` TEXT COMMENT '优化后提示词',
  `test_data` JSON COMMENT '测试数据',
  `test_results` JSON COMMENT '测试结果',
  `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_id` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Prompt优化任务表';

-- =====================================================
-- 9. 数据分析任务表
-- =====================================================
DROP TABLE IF EXISTS `analysis_tasks`;
CREATE TABLE `analysis_tasks` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` VARCHAR(32) NOT NULL COMMENT '任务唯一标识',
  `name` VARCHAR(200) NOT NULL COMMENT '任务名称',
  `description` TEXT COMMENT '任务描述',
  `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/running/completed/failed',
  `workflow_state` JSON COMMENT '工作流状态',
  `results` JSON COMMENT '分析结果',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_id` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据分析任务表';

-- =====================================================
-- 10. 分析任务文件表
-- =====================================================
DROP TABLE IF EXISTS `analysis_files`;
CREATE TABLE `analysis_files` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` VARCHAR(32) NOT NULL COMMENT '所属任务ID',
  `file_id` VARCHAR(100) NOT NULL COMMENT '文件唯一标识',
  `filename` VARCHAR(255) NOT NULL COMMENT '原始文件名',
  `file_path` VARCHAR(500) DEFAULT NULL COMMENT '存储路径',
  `file_size` INT DEFAULT 0 COMMENT '文件大小(字节)',
  `status` VARCHAR(20) DEFAULT 'uploaded' COMMENT '状态',
  `parse_result` JSON COMMENT '解析结果',
  `analysis_result` JSON COMMENT '分析结果',
  `upload_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分析任务文件表';

-- =====================================================
-- 11. 会话记录表
-- =====================================================
DROP TABLE IF EXISTS `chat_sessions`;
CREATE TABLE `chat_sessions` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `session_id` VARCHAR(64) NOT NULL COMMENT '会话唯一标识',
  `session_type` VARCHAR(20) DEFAULT 'chat' COMMENT '会话类型: chat/analysis',
  `title` VARCHAR(200) DEFAULT '新对话' COMMENT '会话标题',
  `messages` JSON COMMENT '消息记录',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_session_id` (`session_id`),
  KEY `idx_session_type` (`session_type`),
  KEY `idx_updated_at` (`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话记录表';

-- =====================================================
-- 12. 知识库文档表
-- =====================================================
DROP TABLE IF EXISTS `knowledge_documents`;
CREATE TABLE `knowledge_documents` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `doc_id` VARCHAR(32) NOT NULL COMMENT '文档唯一标识',
  `filename` VARCHAR(255) NOT NULL COMMENT '文件名',
  `file_path` VARCHAR(500) DEFAULT NULL COMMENT '存储路径',
  `file_type` VARCHAR(50) DEFAULT NULL COMMENT '文件类型',
  `file_size` INT DEFAULT 0 COMMENT '文件大小',
  `content` LONGTEXT COMMENT '文档内容',
  `chunk_count` INT DEFAULT 0 COMMENT '分块数量',
  `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending/processing/ready/failed',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_doc_id` (`doc_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库文档表';

-- =====================================================
-- 13. 知识库任务表
-- =====================================================
DROP TABLE IF EXISTS `knowledge_tasks`;
CREATE TABLE `knowledge_tasks` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `task_id` VARCHAR(32) NOT NULL COMMENT '任务唯一标识',
  `query` TEXT NOT NULL COMMENT '用户查询',
  `doc_ids` JSON COMMENT '关联文档ID列表',
  `result` JSON COMMENT '查询结果',
  `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_id` (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库任务表';

-- =====================================================
-- 14. 模型调用统计表
-- =====================================================
DROP TABLE IF EXISTS `model_stats`;
CREATE TABLE `model_stats` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `model_name` VARCHAR(100) NOT NULL COMMENT '模型名称',
  `call_date` DATE NOT NULL COMMENT '调用日期',
  `call_count` INT DEFAULT 0 COMMENT '调用次数',
  `total_tokens` BIGINT DEFAULT 0 COMMENT '总Token数',
  `avg_latency` DECIMAL(10,2) DEFAULT 0 COMMENT '平均延迟(ms)',
  `success_count` INT DEFAULT 0 COMMENT '成功次数',
  `fail_count` INT DEFAULT 0 COMMENT '失败次数',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_date` (`model_name`, `call_date`),
  KEY `idx_call_date` (`call_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型调用统计表';

-- =====================================================
-- 15. 操作日志表
-- =====================================================
DROP TABLE IF EXISTS `operation_logs`;
CREATE TABLE `operation_logs` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `operation_type` VARCHAR(50) NOT NULL COMMENT '操作类型',
  `module` VARCHAR(50) DEFAULT NULL COMMENT '模块名称',
  `description` VARCHAR(500) DEFAULT NULL COMMENT '操作描述',
  `request_data` JSON COMMENT '请求数据',
  `response_data` JSON COMMENT '响应数据',
  `ip_address` VARCHAR(50) DEFAULT NULL COMMENT 'IP地址',
  `user_agent` VARCHAR(500) DEFAULT NULL COMMENT '用户代理',
  `duration` INT DEFAULT 0 COMMENT '耗时(ms)',
  `status` VARCHAR(20) DEFAULT 'success' COMMENT '状态: success/fail',
  `error_message` TEXT COMMENT '错误信息',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_operation_type` (`operation_type`),
  KEY `idx_module` (`module`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作日志表';

-- =====================================================
-- 16. 导出记录表
-- =====================================================
DROP TABLE IF EXISTS `export_records`;
CREATE TABLE `export_records` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `export_id` VARCHAR(32) NOT NULL COMMENT '导出唯一标识',
  `export_type` VARCHAR(50) NOT NULL COMMENT '导出类型: report/data/analysis',
  `filename` VARCHAR(255) NOT NULL COMMENT '文件名',
  `file_path` VARCHAR(500) DEFAULT NULL COMMENT '文件路径',
  `file_size` INT DEFAULT 0 COMMENT '文件大小',
  `related_id` VARCHAR(32) DEFAULT NULL COMMENT '关联ID(任务ID等)',
  `status` VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
  `download_count` INT DEFAULT 0 COMMENT '下载次数',
  `expires_at` DATETIME DEFAULT NULL COMMENT '过期时间',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_export_id` (`export_id`),
  KEY `idx_export_type` (`export_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='导出记录表';

SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================
-- 完成提示
-- =====================================================
-- 数据库表创建完成！
-- 共创建 16 张表：
-- 1. sys_config - 系统配置
-- 2. prompt_templates - 提示词模板
-- 3. datasets - 数据集
-- 4. baseline_effects - 基准效果
-- 5. batch_tasks - 批量评估任务
-- 6. batch_task_items - 批量任务作业项
-- 7. evaluation_errors - 评估错误详情
-- 8. prompt_tasks - Prompt优化任务
-- 9. analysis_tasks - 数据分析任务
-- 10. analysis_files - 分析任务文件
-- 11. chat_sessions - 会话记录
-- 12. knowledge_documents - 知识库文档
-- 13. knowledge_tasks - 知识库任务
-- 14. model_stats - 模型调用统计
-- 15. operation_logs - 操作日志
-- 16. export_records - 导出记录
