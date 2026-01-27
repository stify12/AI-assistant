-- 提示词配置版本管理表
-- 用于存储从 zpsmart.zp_config 同步的提示词配置及其版本历史

-- 提示词配置表（当前版本）
CREATE TABLE IF NOT EXISTS prompt_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键名，对应 zp_config.config_key',
    subject_id INT DEFAULT NULL COMMENT '关联学科ID',
    subject_name VARCHAR(50) DEFAULT NULL COMMENT '学科名称',
    description VARCHAR(255) DEFAULT NULL COMMENT '配置描述',
    config_value LONGTEXT COMMENT '当前提示词内容',
    content_hash VARCHAR(64) COMMENT '内容MD5哈希，用于检测变更',
    current_version INT DEFAULT 1 COMMENT '当前版本号',
    synced_at DATETIME COMMENT '最后同步时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_subject_id (subject_id),
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提示词配置表';

-- 提示词版本历史表
CREATE TABLE IF NOT EXISTS prompt_config_versions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL COMMENT '配置键名',
    version INT NOT NULL COMMENT '版本号',
    config_value LONGTEXT COMMENT '该版本的提示词内容',
    content_hash VARCHAR(64) COMMENT '内容MD5哈希',
    change_summary TEXT COMMENT '变更摘要（自动生成）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '版本创建时间',
    INDEX idx_config_key (config_key),
    INDEX idx_version (config_key, version),
    UNIQUE KEY uk_config_version (config_key, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='提示词版本历史表';

-- 批量任务关联的提示词版本
ALTER TABLE batch_tasks 
ADD COLUMN IF NOT EXISTS prompt_versions JSON DEFAULT NULL COMMENT '任务创建时使用的提示词版本信息';
