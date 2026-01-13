"""
数据集迁移脚本
将 datasets/ 和 baseline_effects/ 目录下的 JSON 文件迁移到数据库
"""
import os
import json
import uuid
from datetime import datetime
from services.database_service import AppDatabaseService


def migrate_baseline_effects():
    """迁移 baseline_effects/ 目录下的旧格式数据"""
    effects_dir = 'baseline_effects'
    
    if not os.path.exists(effects_dir):
        print(f"目录 {effects_dir} 不存在")
        return
    
    json_files = [f for f in os.listdir(effects_dir) if f.endswith('.json')]
    
    if not json_files:
        print("baseline_effects/ 目录下没有JSON文件")
        return
    
    print(f"\n找到 {len(json_files)} 个基准效果文件")
    
    # 按 homework_name 分组
    grouped = {}
    for filename in json_files:
        filepath = os.path.join(effects_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            homework_name = data.get('homework_name', '')
            if not homework_name:
                continue
            
            if homework_name not in grouped:
                grouped[homework_name] = {
                    'subject_id': data.get('subject_id', 0),
                    'pages': {}
                }
            
            page_num = data.get('page_num')
            if page_num:
                grouped[homework_name]['pages'][page_num] = data.get('base_effect', [])
        except Exception as e:
            print(f"  读取失败 {filename}: {e}")
    
    # 为每个分组创建数据集
    for homework_name, group_data in grouped.items():
        pages = sorted(group_data['pages'].keys())
        if not pages:
            continue
        
        # 检查是否已存在同名数据集
        existing = AppDatabaseService.execute_query(
            "SELECT dataset_id FROM datasets WHERE book_name = %s", (homework_name,)
        )
        if existing:
            print(f"  跳过 {homework_name}: 已存在")
            continue
        
        dataset_id = str(uuid.uuid4())[:8]
        question_count = sum(len(effects) for effects in group_data['pages'].values())
        
        # 创建数据集
        AppDatabaseService.create_dataset(
            dataset_id=dataset_id,
            book_id=None,
            pages=pages,
            book_name=homework_name,
            subject_id=group_data['subject_id'],
            question_count=question_count
        )
        
        # 保存基准效果
        for page_num, effects in group_data['pages'].items():
            formatted = []
            for effect in effects:
                formatted.append({
                    'index': effect.get('index', ''),
                    'tempIndex': effect.get('tempIndex', 0),
                    'type': 'choice',
                    'answer': effect.get('answer', ''),
                    'userAnswer': effect.get('userAnswer', ''),
                    'correct': effect.get('correct', ''),
                    'questionType': 'objective',
                    'bvalue': '4'
                })
            AppDatabaseService.save_baseline_effects(dataset_id, int(page_num), formatted)
        
        print(f"  创建数据集: {homework_name} -> {dataset_id} ({question_count} 题, {len(pages)} 页)")


def migrate_datasets():
    """迁移所有数据集JSON文件到数据库"""
    datasets_dir = 'datasets'
    
    if not os.path.exists(datasets_dir):
        print(f"目录 {datasets_dir} 不存在")
        return
    
    json_files = [f for f in os.listdir(datasets_dir) if f.endswith('.json')]
    
    if not json_files:
        print("没有找到需要迁移的JSON文件")
        return
    
    print(f"找到 {len(json_files)} 个数据集文件需要迁移")
    
    success_count = 0
    error_count = 0
    
    for filename in json_files:
        dataset_id = filename[:-5]  # 去掉 .json 后缀
        filepath = os.path.join(datasets_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查数据库中是否已存在
            existing = AppDatabaseService.get_dataset(dataset_id)
            if existing:
                print(f"  更新 {dataset_id}: 重新导入基准效果...")
                # 删除旧的基准效果，重新导入
                AppDatabaseService.execute_update(
                    "DELETE FROM baseline_effects WHERE dataset_id = %s", (dataset_id,)
                )
            
            # 计算题目数量
            base_effects = data.get('base_effects', {})
            question_count = 0
            for page_data in base_effects.values():
                if isinstance(page_data, list):
                    question_count += len(page_data)
            
            if existing:
                # 只更新基准效果
                pass
            else:
                # 创建数据集记录
                AppDatabaseService.create_dataset(
                    dataset_id=dataset_id,
                    book_id=data.get('book_id'),
                    pages=data.get('pages', []),
                    book_name=data.get('book_name'),
                    subject_id=data.get('subject_id'),
                    question_count=question_count
                )
            
            # 保存基准效果
            for page_num, effects in base_effects.items():
                if isinstance(effects, list) and len(effects) > 0:
                    # 转换字段格式，保留questionType和bvalue
                    formatted_effects = []
                    for effect in effects:
                        formatted_effects.append({
                            'index': effect.get('index', ''),
                            'tempIndex': effect.get('tempIndex', 0),
                            'type': effect.get('questionType', effect.get('type', 'choice')),
                            'answer': effect.get('answer', ''),
                            'userAnswer': effect.get('userAnswer', ''),
                            'correct': effect.get('correct', ''),
                            'questionType': effect.get('questionType', 'objective'),
                            'bvalue': effect.get('bvalue', '4')
                        })
                    AppDatabaseService.save_baseline_effects(dataset_id, int(page_num), formatted_effects)
            
            print(f"  迁移成功: {dataset_id} ({question_count} 题)")
            success_count += 1
            
        except Exception as e:
            print(f"  迁移失败 {dataset_id}: {str(e)}")
            error_count += 1
    
    print(f"\n迁移完成: 成功 {success_count}, 失败 {error_count}")


def verify_migration():
    """验证迁移结果"""
    print("\n验证迁移结果...")
    
    datasets = AppDatabaseService.get_datasets()
    print(f"数据库中共有 {len(datasets)} 个数据集")
    
    for ds in datasets:
        effects = AppDatabaseService.get_baseline_effects(ds['dataset_id'])
        pages = ds['pages']
        if isinstance(pages, str):
            pages = json.loads(pages)
        print(f"  - {ds['dataset_id']}: book_id={ds['book_id']}, pages={pages}, effects={len(effects)}")


if __name__ == '__main__':
    print("=" * 50)
    print("数据集迁移工具")
    print("=" * 50)
    
    migrate_datasets()
    migrate_baseline_effects()
    verify_migration()
