"""
执行数据库迁移 - 创建基准合集相关表
"""
from services.database_service import AppDatabaseService

def run_migration():
    """执行迁移"""
    print("开始执行数据库迁移...")
    
    # 创建 dataset_collections 表
    sql1 = """
    CREATE TABLE IF NOT EXISTS dataset_collections (
        id INT AUTO_INCREMENT PRIMARY KEY,
        collection_id VARCHAR(32) NOT NULL UNIQUE COMMENT '合集唯一标识',
        name VARCHAR(255) NOT NULL COMMENT '合集名称',
        description TEXT COMMENT '合集描述',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_collection_id (collection_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='基准合集表'
    """
    
    # 创建 collection_datasets 表
    sql2 = """
    CREATE TABLE IF NOT EXISTS collection_datasets (
        id INT AUTO_INCREMENT PRIMARY KEY,
        collection_id VARCHAR(32) NOT NULL COMMENT '合集ID',
        dataset_id VARCHAR(32) NOT NULL COMMENT '数据集ID',
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uk_collection_dataset (collection_id, dataset_id),
        INDEX idx_collection_id (collection_id),
        INDEX idx_dataset_id (dataset_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合集-数据集关联表'
    """
    
    try:
        AppDatabaseService.execute_update(sql1)
        print("创建 dataset_collections 表成功")
    except Exception as e:
        print(f"创建 dataset_collections 表: {e}")
    
    try:
        AppDatabaseService.execute_update(sql2)
        print("创建 collection_datasets 表成功")
    except Exception as e:
        print(f"创建 collection_datasets 表: {e}")
    
    # 验证表是否创建成功
    tables = AppDatabaseService.execute_query("SHOW TABLES LIKE 'dataset_collections'")
    if tables:
        print("验证: dataset_collections 表存在")
    else:
        print("警告: dataset_collections 表不存在")
    
    tables = AppDatabaseService.execute_query("SHOW TABLES LIKE 'collection_datasets'")
    if tables:
        print("验证: collection_datasets 表存在")
    else:
        print("警告: collection_datasets 表不存在")
    
    print("迁移完成!")

if __name__ == "__main__":
    run_migration()
