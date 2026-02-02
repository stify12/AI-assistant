-- 迁移脚本: 为 baseline_effects 表添加测试用例生成相关字段
-- 执行时间: 2026-01-30
-- 说明: 支持 AI 自动生成基准效果功能

-- 添加 tags 字段（测试标签数组）
ALTER TABLE `baseline_effects` 
ADD COLUMN `tags` JSON DEFAULT NULL COMMENT '测试标签数组' AFTER `is_correct`;

-- 添加 max_score 字段（题目总分）
ALTER TABLE `baseline_effects` 
ADD COLUMN `max_score` DECIMAL(5,2) DEFAULT NULL COMMENT '题目总分' AFTER `tags`;

-- 添加 score 字段（判断分值）
ALTER TABLE `baseline_effects` 
ADD COLUMN `score` DECIMAL(5,2) DEFAULT NULL COMMENT '判断分值' AFTER `max_score`;

-- 添加 fill_guide 字段（填写指导）
ALTER TABLE `baseline_effects` 
ADD COLUMN `fill_guide` VARCHAR(500) DEFAULT NULL COMMENT '填写指导' AFTER `score`;

-- 示例数据格式:
-- tags: ["完全正确", "基准"] 或 ["字符混淆", "8/0混淆"]
-- max_score: 10.00
-- score: 10.00
-- fill_guide: "工整书写数字8，笔画清晰"
