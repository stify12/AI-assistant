#!/usr/bin/env python3
"""测试数据库存储模式下的数据集匹配"""
import json
from services.storage_service import StorageService
from services.database_service import AppDatabaseService

print("=" * 60)
print("测试数据库存储模式下的数据集匹配")
print("=" * 60)

# 测试数据
test_book_id = "1998967464626053121"
test_pages = [2, 3, 4, 5]

print(f"\n测试书本ID: {test_book_id}")
print(f"测试页码: {test_pages}")

# 加载所有数据集
print("\n加载数据集...")
datasets = []
for filename in StorageService.list_datasets():
    ds = StorageService.load_dataset(filename[:-5] if filename.endswith('.json') else filename)
    if ds:
        datasets.append(ds)

print(f"找到 {len(datasets)} 个数据集")

# 按页码数量排序
datasets.sort(key=lambda ds: len(ds.get('pages', [])), reverse=True)

print("\n数据集列表（按页码数量排序）:")
for ds in datasets:
    ds_id = ds.get('dataset_id')
    ds_book_id = str(ds.get('book_id', '')) if ds.get('book_id') else ''
    ds_pages = ds.get('pages', [])
    base_effects = ds.get('base_effects', {})
    
    print(f"  {ds_id}:")
    print(f"    book_id: {ds_book_id}")
    print(f"    pages: {ds_pages}")
    print(f"    base_effects keys: {list(base_effects.keys())}")

# 测试匹配逻辑
print(f"\n测试匹配逻辑（book_id={test_book_id}）:")
for page_num in test_pages:
    page_num_int = int(page_num)
    matched_dataset = None
    
    for ds in datasets:
        ds_book_id = str(ds.get('book_id', '')) if ds.get('book_id') else ''
        ds_pages = ds.get('pages', [])
        base_effects = ds.get('base_effects', {})
        
        if ds_book_id == test_book_id and page_num_int is not None:
            # 检查数据集的 pages 数组
            page_in_pages = page_num_int in ds_pages or str(page_num_int) in [str(p) for p in ds_pages]
            # 检查数据集的 base_effects 是否包含该页码的数据
            page_in_effects = str(page_num_int) in base_effects
            
            if page_in_pages and page_in_effects:
                matched_dataset = ds.get('dataset_id')
                break
    
    if matched_dataset:
        print(f"  第{page_num}页 → {matched_dataset} ✅")
    else:
        print(f"  第{page_num}页 → 未匹配 ❌")

print("\n" + "=" * 60)
