"""
自动评估全流程测试
测试流程：
1. 获取作业数据 (homework_id, data_value, homework_result)
2. 使用动态提示词识别基准效果
3. 将基准效果与 AI 批改结果 (homework_result) 进行对比评估
4. 验证评估结果的准确性
"""
import json
import sys
import requests

sys.path.insert(0, '.')

from services.database_service import DatabaseService
from routes.dataset_manage import build_dynamic_prompt


BASE_URL = "http://localhost:5000"


def step1_get_homework_data():
    """步骤1: 获取作业数据"""
    print("\n" + "=" * 60)
    print("步骤1: 获取作业数据")
    print("=" * 60)
    
    sql = """
        SELECT h.id, h.data_value, h.homework_result, h.page_num, h.pic_path,
               p.book_id, b.book_name
        FROM zp_homework h
        LEFT JOIN zp_homework_publish p ON h.hw_publish_id = p.id
        LEFT JOIN zp_make_book b ON p.book_id = b.id
        WHERE h.status = 3 
          AND h.data_value IS NOT NULL AND h.data_value != ''
          AND h.homework_result IS NOT NULL AND h.homework_result != ''
          AND h.pic_path IS NOT NULL AND h.pic_path != ''
        ORDER BY h.create_time DESC
        LIMIT 1
    """
    rows = DatabaseService.execute_query(sql)
    
    if not rows:
        print("✗ 没有找到符合条件的作业数据")
        return None
    
    row = rows[0]
    homework_id = str(row['id'])
    
    # 解析数据
    data_value = json.loads(row.get('data_value', '[]'))
    homework_result = json.loads(row.get('homework_result', '[]'))
    
    print(f"作业ID: {homework_id}")
    print(f"书本: {row.get('book_name', '未知')}")
    print(f"页码: {row.get('page_num')}")
    print(f"data_value 题目数: {len(data_value)}")
    print(f"homework_result 题目数: {len(homework_result)}")
    
    return {
        'homework_id': homework_id,
        'book_id': str(row.get('book_id', '')),
        'book_name': row.get('book_name', ''),
        'page_num': row.get('page_num'),
        'data_value': data_value,
        'homework_result': homework_result
    }


def step2_recognize_baseline(homework_data):
    """步骤2: 使用动态提示词识别基准效果"""
    print("\n" + "=" * 60)
    print("步骤2: 使用动态提示词识别基准效果")
    print("=" * 60)
    
    homework_id = homework_data['homework_id']
    
    # 调用识别 API
    url = f"{BASE_URL}/api/dataset/recognize"
    payload = {
        "homework_id": homework_id,
        "subject_id": 0
    }
    
    print(f"调用识别API: {url}")
    print("请求参数:", json.dumps(payload, ensure_ascii=False))
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        result = response.json()
        
        if not result.get('success'):
            print(f"✗ 识别失败: {result.get('error')}")
            return None
        
        base_effect = result.get('data', [])
        print(f"✓ 识别成功，共 {len(base_effect)} 题")
        
        # 显示前3题
        print("\n识别结果示例 (前3题):")
        for item in base_effect[:3]:
            print(f"  题{item.get('index')}: userAnswer={item.get('userAnswer')}, "
                  f"answer={item.get('answer')}, correct={item.get('correct')}")
        
        return base_effect
        
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到服务器")
        return None
    except Exception as e:
        print(f"✗ 识别失败: {e}")
        return None


def step3_compare_evaluation(base_effect, homework_result):
    """步骤3: 对比基准效果与AI批改结果"""
    print("\n" + "=" * 60)
    print("步骤3: 对比基准效果与AI批改结果")
    print("=" * 60)
    
    # 构建 homework_result 索引
    hw_dict = {}
    for item in homework_result:
        key = (str(item.get('index', '')), item.get('tempIndex', 0))
        hw_dict[key] = item
    
    total = len(base_effect)
    match_count = 0
    mismatch_details = []
    
    print(f"\n逐题对比 (共 {total} 题):")
    print("-" * 80)
    print(f"{'题号':<6} {'基准userAnswer':<15} {'AI userAnswer':<15} {'基准correct':<12} {'AI correct':<12} {'匹配'}")
    print("-" * 80)
    
    for base_item in base_effect:
        idx = str(base_item.get('index', ''))
        temp_idx = base_item.get('tempIndex', 0)
        key = (idx, temp_idx)
        
        hw_item = hw_dict.get(key, {})
        
        base_user = str(base_item.get('userAnswer', '')).strip()
        hw_user = str(hw_item.get('userAnswer', '')).strip()
        base_correct = base_item.get('correct', '')
        hw_correct = hw_item.get('correct', '')
        
        # 判断是否匹配
        user_match = base_user.lower() == hw_user.lower()
        correct_match = base_correct == hw_correct
        is_match = user_match and correct_match
        
        if is_match:
            match_count += 1
            match_str = "✓"
        else:
            match_str = "✗"
            mismatch_details.append({
                'index': idx,
                'base_userAnswer': base_user,
                'hw_userAnswer': hw_user,
                'base_correct': base_correct,
                'hw_correct': hw_correct,
                'user_match': user_match,
                'correct_match': correct_match
            })
        
        print(f"{idx:<6} {base_user:<15} {hw_user:<15} {base_correct:<12} {hw_correct:<12} {match_str}")
    
    print("-" * 80)
    
    accuracy = match_count / total * 100 if total > 0 else 0
    print(f"\n匹配统计:")
    print(f"  总题数: {total}")
    print(f"  匹配数: {match_count}")
    print(f"  不匹配数: {total - match_count}")
    print(f"  匹配率: {accuracy:.1f}%")
    
    return {
        'total': total,
        'match_count': match_count,
        'mismatch_count': total - match_count,
        'accuracy': accuracy,
        'mismatch_details': mismatch_details
    }


def step4_call_evaluation_api(base_effect, homework_result):
    """步骤4: 调用评估API进行正式评估"""
    print("\n" + "=" * 60)
    print("步骤4: 调用评估API进行正式评估")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/grading/evaluate"
    payload = {
        "base_effect": base_effect,
        "homework_result": homework_result,
        "use_ai_compare": False
    }
    
    print(f"调用评估API: {url}")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        result = response.json()
        
        if not result.get('success'):
            print(f"✗ 评估失败: {result.get('error')}")
            return None
        
        evaluation = result.get('evaluation', {})
        
        print(f"\n评估结果:")
        print(f"  准确率: {evaluation.get('accuracy', 0) * 100:.1f}%")
        print(f"  精确率: {evaluation.get('precision', 0) * 100:.1f}%")
        print(f"  召回率: {evaluation.get('recall', 0) * 100:.1f}%")
        print(f"  F1值: {evaluation.get('f1_score', 0) * 100:.1f}%")
        print(f"  总题数: {evaluation.get('total_questions', 0)}")
        print(f"  正确数: {evaluation.get('correct_count', 0)}")
        print(f"  错误数: {evaluation.get('error_count', 0)}")
        
        # 错误分布
        error_dist = evaluation.get('error_distribution', {})
        if error_dist:
            print(f"\n错误分布:")
            for error_type, count in error_dist.items():
                if count > 0:
                    print(f"    {error_type}: {count}")
        
        # 错误详情
        errors = evaluation.get('errors', [])
        if errors:
            print(f"\n错误详情 (前5个):")
            for err in errors[:5]:
                print(f"  题{err.get('index')}: {err.get('error_type')} - {err.get('explanation', '')[:50]}")
        
        return evaluation
        
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到服务器")
        return None
    except Exception as e:
        print(f"✗ 评估失败: {e}")
        return None


def step5_verify_structure_consistency(base_effect, homework_result):
    """步骤5: 验证结构一致性"""
    print("\n" + "=" * 60)
    print("步骤5: 验证结构一致性")
    print("=" * 60)
    
    # 提取索引
    base_indices = set()
    for item in base_effect:
        key = (str(item.get('index', '')), item.get('tempIndex', 0))
        base_indices.add(key)
    
    hw_indices = set()
    for item in homework_result:
        key = (str(item.get('index', '')), item.get('tempIndex', 0))
        hw_indices.add(key)
    
    # 计算交集和差集
    common = base_indices & hw_indices
    only_in_base = base_indices - hw_indices
    only_in_hw = hw_indices - base_indices
    
    print(f"基准效果题目数: {len(base_indices)}")
    print(f"AI批改题目数: {len(hw_indices)}")
    print(f"共同题目数: {len(common)}")
    
    if only_in_base:
        print(f"\n仅在基准效果中的题目: {sorted(only_in_base)[:10]}")
    if only_in_hw:
        print(f"仅在AI批改中的题目: {sorted(only_in_hw)[:10]}")
    
    consistency = len(common) / max(len(base_indices), len(hw_indices)) * 100 if base_indices or hw_indices else 0
    print(f"\n结构一致性: {consistency:.1f}%")
    
    if consistency >= 90:
        print("✓ 结构一致性良好")
        return True
    else:
        print("⚠ 结构一致性较低，可能影响评估准确性")
        return False


def run_full_test():
    """运行完整测试流程"""
    print("=" * 60)
    print("自动评估全流程测试")
    print("=" * 60)
    
    # 步骤1: 获取作业数据
    homework_data = step1_get_homework_data()
    if not homework_data:
        return False
    
    # 步骤2: 识别基准效果
    base_effect = step2_recognize_baseline(homework_data)
    if not base_effect:
        return False
    
    homework_result = homework_data['homework_result']
    
    # 步骤3: 对比评估
    comparison = step3_compare_evaluation(base_effect, homework_result)
    
    # 步骤4: 调用评估API
    evaluation = step4_call_evaluation_api(base_effect, homework_result)
    
    # 步骤5: 验证结构一致性
    structure_ok = step5_verify_structure_consistency(base_effect, homework_result)
    
    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    print(f"1. 作业数据获取: ✓")
    print(f"2. 动态提示词识别: ✓ ({len(base_effect)} 题)")
    print(f"3. 基准效果与AI批改对比:")
    print(f"   - 匹配率: {comparison['accuracy']:.1f}%")
    print(f"   - 不匹配题数: {comparison['mismatch_count']}")
    
    if evaluation:
        print(f"4. 评估API结果:")
        print(f"   - 准确率: {evaluation.get('accuracy', 0) * 100:.1f}%")
        print(f"   - 错误数: {evaluation.get('error_count', 0)}")
    else:
        print(f"4. 评估API: ✗ 失败")
    
    print(f"5. 结构一致性: {'✓' if structure_ok else '⚠'}")
    
    # 判断测试是否通过
    success = (
        base_effect is not None and
        len(base_effect) > 0 and
        structure_ok
    )
    
    print(f"\n总体结果: {'✓ 测试通过' if success else '⚠ 测试有警告'}")
    
    return success


if __name__ == "__main__":
    try:
        success = run_full_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
