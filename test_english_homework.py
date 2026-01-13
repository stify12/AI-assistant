"""
测试英语作业的自动评估流程
使用之前测试过的作业ID: 2010597520016715777
"""
import json
import sys
import requests

sys.path.insert(0, '.')

from services.database_service import DatabaseService

BASE_URL = "http://localhost:5000"


def test_english_homework():
    """测试英语作业评估"""
    homework_id = "2010597520016715777"
    
    print("=" * 70)
    print(f"测试英语作业评估 (ID: {homework_id})")
    print("=" * 70)
    
    # 1. 获取作业数据
    print("\n1. 获取作业数据...")
    sql = """
        SELECT h.id, h.data_value, h.homework_result, h.page_num
        FROM zp_homework h
        WHERE h.id = %s
    """
    rows = DatabaseService.execute_query(sql, (homework_id,))
    
    if not rows:
        print("✗ 作业不存在")
        return False
    
    row = rows[0]
    homework_result = json.loads(row.get('homework_result', '[]'))
    print(f"   homework_result 题目数: {len(homework_result)}")
    
    # 2. 调用动态提示词识别
    print("\n2. 调用动态提示词识别...")
    url = f"{BASE_URL}/api/dataset/recognize"
    response = requests.post(url, json={"homework_id": homework_id, "subject_id": 0}, timeout=120)
    result = response.json()
    
    if not result.get('success'):
        print(f"✗ 识别失败: {result.get('error')}")
        return False
    
    base_effect = result.get('data', [])
    print(f"   识别题目数: {len(base_effect)}")
    
    # 3. 对比结构
    print("\n3. 结构对比...")
    base_indices = {(item.get('index'), item.get('tempIndex')) for item in base_effect}
    hw_indices = {(item.get('index'), item.get('tempIndex')) for item in homework_result}
    
    common = base_indices & hw_indices
    print(f"   共同题目: {len(common)}/{len(base_indices)}")
    
    # 4. 逐题对比
    print("\n4. 逐题对比:")
    print("-" * 90)
    print(f"{'题号':<6} {'基准userAnswer':<20} {'AI userAnswer':<20} {'基准correct':<10} {'AI correct':<10} {'匹配'}")
    print("-" * 90)
    
    hw_dict = {(str(item.get('index')), item.get('tempIndex')): item for item in homework_result}
    
    match_count = 0
    for base_item in base_effect:
        idx = str(base_item.get('index', ''))
        temp_idx = base_item.get('tempIndex', 0)
        key = (idx, temp_idx)
        
        hw_item = hw_dict.get(key, {})
        
        base_user = str(base_item.get('userAnswer', '')).strip()[:18]
        hw_user = str(hw_item.get('userAnswer', '')).strip()[:18]
        base_correct = base_item.get('correct', '')
        hw_correct = hw_item.get('correct', '')
        
        # 简单匹配
        user_match = base_user.lower() == hw_user.lower()
        correct_match = base_correct == hw_correct
        is_match = user_match and correct_match
        
        if is_match:
            match_count += 1
            match_str = "✓"
        else:
            match_str = "✗"
        
        print(f"{idx:<6} {base_user:<20} {hw_user:<20} {base_correct:<10} {hw_correct:<10} {match_str}")
    
    print("-" * 90)
    
    accuracy = match_count / len(base_effect) * 100 if base_effect else 0
    print(f"\n匹配率: {accuracy:.1f}% ({match_count}/{len(base_effect)})")
    
    # 5. 调用评估API
    print("\n5. 调用评估API...")
    eval_url = f"{BASE_URL}/api/grading/evaluate"
    eval_response = requests.post(eval_url, json={
        "base_effect": base_effect,
        "homework_result": homework_result,
        "use_ai_compare": False
    }, timeout=60)
    eval_result = eval_response.json()
    
    if eval_result.get('success'):
        evaluation = eval_result.get('evaluation', {})
        print(f"   准确率: {evaluation.get('accuracy', 0) * 100:.1f}%")
        print(f"   正确数: {evaluation.get('correct_count', 0)}")
        print(f"   错误数: {evaluation.get('error_count', 0)}")
        
        error_dist = evaluation.get('error_distribution', {})
        if any(v > 0 for v in error_dist.values()):
            print(f"   错误分布:")
            for k, v in error_dist.items():
                if v > 0:
                    print(f"      {k}: {v}")
    else:
        print(f"✗ 评估失败: {eval_result.get('error')}")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    test_english_homework()
