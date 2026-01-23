-- 基准合集功能数据库迁移
-- 执行时间: 2026-01-23

-- 基准合集表
CREATE TABLE IF NOT EXISTS dataset_collections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    collection_id VARCHAR(32) NOT NULL UNIQUE COMMENT '合集唯一标识',
    name VARCHAR(255) NOT NULL COMMENT '合集名称',
    description TEXT COMMENT '合集描述',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_collection_id (collection_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基准合集表';

-- 合集-数据集关联表
CREATE TABLE IF NOT EXISTS collection_datasets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    collection_id VARCHAR(32) NOT NULL COMMENT '合集ID',
    dataset_id VARCHAR(32) NOT NULL COMMENT '数据集ID',
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_collection_dataset (collection_id, dataset_id),
    INDEX idx_collection_id (collection_id),
    INDEX idx_dataset_id (dataset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合集-数据集关联表';
