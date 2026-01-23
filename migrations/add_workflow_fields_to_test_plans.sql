-- =====================================================
-- 测试计划表工作流字段迁移脚本
-- 用途: 为 test_plans 表添加自动化工作流相关字段
-- 创建时间: 2026-01-23
-- 执行方式: 在服务器 MySQL 中执行此脚本
-- 数据库: aiuser
-- =====================================================

USE aiuser;

-- =====================================================
-- 方式一: 直接执行 ALTER TABLE (推荐)
-- 如果字段已存在会报错，可忽略错误继续执行
-- =====================================================

-- 添加 task_keyword 字段
-- 任务名称关键字，用于匹配 zp_homework_publish.content
ALTER TABLE test_plans 
ADD COLUMN `task_keyword` VARCHAR(200) 
    COMMENT '任务名称关键字，用于匹配 zp_homework_publish.content'
    AFTER `assignee_id`;

-- 添加 keyword_match_type 字段
-- 匹配类型: exact=精确, fuzzy=模糊, regex=正则
ALTER TABLE test_plans 
ADD COLUMN `keyword_match_type` ENUM('exact', 'fuzzy', 'regex') 
    DEFAULT 'fuzzy' 
    COMMENT '匹配类型: exact=精确, fuzzy=模糊, regex=正则'
    AFTER `task_keyword`;

-- 添加 matched_publish_ids 字段
-- 匹配到的发布ID列表
ALTER TABLE test_plans 
ADD COLUMN `matched_publish_ids` JSON 
    COMMENT '匹配到的发布ID列表'
    AFTER `keyword_match_type`;

-- 添加 workflow_status 字段
-- 工作流各步骤状态
ALTER TABLE test_plans 
ADD COLUMN `workflow_status` JSON 
    COMMENT '工作流各步骤状态'
    AFTER `matched_publish_ids`;

-- 添加 auto_execute 字段
-- 是否自动执行（批改完成后自动评估）
ALTER TABLE test_plans 
ADD COLUMN `auto_execute` TINYINT(1) 
    DEFAULT 0 
    COMMENT '是否自动执行（批改完成后自动评估）'
    AFTER `workflow_status`;

-- 添加 grading_threshold 字段
-- 批改完成度阈值（百分比），达到后触发评估
ALTER TABLE test_plans 
ADD COLUMN `grading_threshold` INT 
    DEFAULT 100 
    COMMENT '批改完成度阈值（百分比），达到后触发评估'
    AFTER `auto_execute`;

-- =====================================================
-- 验证字段添加成功
-- =====================================================
-- 执行以下命令查看表结构:
-- DESCRIBE test_plans;

-- =====================================================
-- 回滚脚本 (如需回滚，执行以下语句)
-- =====================================================
-- ALTER TABLE test_plans DROP COLUMN IF EXISTS task_keyword;
-- ALTER TABLE test_plans DROP COLUMN IF EXISTS keyword_match_type;
-- ALTER TABLE test_plans DROP COLUMN IF EXISTS matched_publish_ids;
-- ALTER TABLE test_plans DROP COLUMN IF EXISTS workflow_status;
-- ALTER TABLE test_plans DROP COLUMN IF EXISTS auto_execute;
-- ALTER TABLE test_plans DROP COLUMN IF EXISTS grading_threshold;

-- =====================================================
-- workflow_status JSON 结构示例
-- =====================================================
-- {
--   "dataset": {
--     "status": "completed",  // not_started | in_progress | completed
--     "dataset_id": "b3b0395e",
--     "dataset_name": "袁崇焕中学_P97-98_20260123",
--     "question_count": 45,
--     "completed_at": "2026-01-23T10:30:00"
--   },
--   "homework_match": {
--     "status": "in_progress",
--     "matched_publish": [
--       {
--         "publish_id": "2014529620268871681",
--         "content": "不同手写p97-98",
--         "total_homework": 42,
--         "graded_count": 17,
--         "grading_progress": 40.5
--       }
--     ],
--     "total_homework": 42,
--     "total_graded": 17,
--     "grading_progress": 40.5,
--     "last_checked": "2026-01-23T10:35:00"
--   },
--   "evaluation": {
--     "status": "not_started",
--     "task_id": null,
--     "accuracy": null,
--     "started_at": null,
--     "completed_at": null
--   },
--   "report": {
--     "status": "not_started",
--     "report_id": null,
--     "generated_at": null
--   }
-- }
