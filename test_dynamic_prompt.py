"""
测试动态提示词功能
验证从 data_value 构建动态提示词并识别作业图片
"""
import json
import sys
sys.path.insert(0, '.')

from services.database_service import DatabaseService
from services.config_service import ConfigService
from routes.dataset_manage import build_dynamic_prompt


def test_build_dynamic_prompt():
    """测试动态提示词构建函数"""
    print("=" * 60)
    print("测试1: 动态提示词构建函数")
    print("=" * 60)
    
    # 模拟 data_value 数据
    test_data_value = [
        {
            "index": "31",
            "tempIndex": 0,
            "bvalue": "4",
            "questionType": "objective",
            "content": "（ ）31. Running after each other at the rest time",
            "jans": "C"
        },
        {
            "index": "32",
            "tempIndex": 1,
            "bvalue": "4",
            "questionType": "objective",
            "content": "（ ）32. Making a fire in the bedroom is very dangerous",
            "jans": "E"
        },
        {
            "index": "36",
            "tempIndex": 5,
            "bvalue": "4",
            "questionType": "objective",
            "content": "36. __________",
            "jans": "stopped"
        }
    ]
    
    prompt = build_dynamic_prompt(test_data_value, subject_id=0)
    print("生成的动态提示词:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)
    
    # 验证提示词包含关键信息
    assert "31" in prompt, "提示词应包含题号31"
    assert "32" in prompt, "提示词应包含题号32"
    assert "C" in prompt, "提示词应包含标准答案C"
    assert "E" in prompt, "提示词应包含标准答案E"
    assert "stopped" in prompt, "提示词应包含标准答案stopped"
    assert "（ ）31. Running" in prompt, "提示词应包含content前15字符"
    assert "填空题" in prompt, "提示词应包含题目类型"
    
    print("✓ 动态提示词构建测试通过")
    return True


def test_get_homework_data_value():
    """测试从数据库获取 data_value"""
    print("\n" + "=" * 60)
    print("测试2: 从数据库获取 data_value")
    print("=" * 60)
    
    try:
        # 获取一条有 data_value 的作业记录
        sql = """
            SELECT h.id, h.data_value, h.homework_result, h.page_num
            FROM zp_homework h
            WHERE h.status = 3 
              AND h.data_value IS NOT NULL 
              AND h.data_value != ''
            ORDER BY h.create_time DESC
            LIMIT 1
        """
        rows = DatabaseService.execute_query(sql)
        
        if not rows:
            print("⚠ 数据库中没有找到有 data_value 的作业记录")
            return False
        
        row = rows[0]
        homework_id = row['id']
        data_value = row.get('data_value', '[]')
        homework_result = row.get('homework_result', '[]')
        
        print(f"作业ID: {homework_id}")
        print(f"页码: {row.get('page_num')}")
        
        # 解析 data_value
        data_value_items = json.loads(data_value) if data_value else []
        print(f"data_value 题目数: {len(data_value_items)}")
        
        # 解析 homework_result
        homework_result_items = json.loads(homework_result) if homework_result else []
        print(f"homework_result 题目数: {len(homework_result_items)}")
        
        if data_value_items:
            print("\ndata_value 第一题信息:")
            first_item = data_value_items[0]
            print(f"  - index: {first_item.get('index')}")
            print(f"  - tempIndex: {first_item.get('tempIndex')}")
            print(f"  - jans (标准答案): {first_item.get('jans')}")
            print(f"  - bvalue (题目类型): {first_item.get('bvalue')}")
            print(f"  - questionType: {first_item.get('questionType')}")
            content = first_item.get('content', '')
            print(f"  - content (前15字符): {content[:15] if content else ''}")
            
            # 构建动态提示词
            prompt = build_dynamic_prompt(data_value_items)
            print(f"\n动态提示词长度: {len(prompt)} 字符")
            print("✓ data_value 获取和解析测试通过")
            
            return {
                'homework_id': homework_id,
                'data_value_items': data_value_items,
                'homework_result_items': homework_result_items,
                'prompt': prompt
            }
        else:
            print("⚠ data_value 为空")
            return False
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compare_structure():
    """测试动态提示词输出结构与 homework_result 一致性"""
    print("\n" + "=" * 60)
    print("测试3: 输出结构一致性验证")
    print("=" * 60)
    
    result = test_get_homework_data_value()
    if not result:
        return False
    
    data_value_items = result['data_value_items']
    homework_result_items = result['homework_result_items']
    
    # 检查 index 和 tempIndex 是否一致
    data_value_indices = [(item.get('index'), item.get('tempIndex')) for item in data_value_items]
    homework_result_indices = [(item.get('index'), item.get('tempIndex')) for item in homework_result_items]
    
    print(f"\ndata_value 题目索引: {data_value_indices[:5]}...")
    print(f"homework_result 题目索引: {homework_result_indices[:5]}...")
    
    # 验证索引一致
    match_count = 0
    for dv_idx in data_value_indices:
        if dv_idx in homework_result_indices:
            match_count += 1
    
    match_rate = match_count / len(data_value_indices) * 100 if data_value_indices else 0
    print(f"\n索引匹配率: {match_rate:.1f}% ({match_count}/{len(data_value_indices)})")
    
    if match_rate >= 80:
        print("✓ 结构一致性测试通过")
        return True
    else:
        print("⚠ 结构一致性较低，可能存在问题")
        return False


def test_api_endpoint():
    """测试 API 端点（需要启动服务器）"""
    print("\n" + "=" * 60)
    print("测试4: API 端点测试 (需要服务器运行)")
    print("=" * 60)
    
    try:
        import requests
        
        # 获取一个有效的作业ID
        sql = """
            SELECT h.id
            FROM zp_homework h
            WHERE h.status = 3 
              AND h.data_value IS NOT NULL 
              AND h.data_value != ''
              AND h.pic_path IS NOT NULL
              AND h.pic_path != ''
            ORDER BY h.create_time DESC
            LIMIT 1
        """
        rows = DatabaseService.execute_query(sql)
        
        if not rows:
            print("⚠ 没有找到可测试的作业")
            return False
        
        homework_id = rows[0]['id']
        print(f"测试作业ID: {homework_id}")
        
        # 调用 API
        url = "http://localhost:5000/api/dataset/recognize"
        payload = {
            "homework_id": str(homework_id),
            "subject_id": 0
        }
        
        print(f"请求 URL: {url}")
        print(f"请求参数: {payload}")
        
        response = requests.post(url, json=payload, timeout=120)
        result = response.json()
        
        print(f"\n响应状态: {'成功' if result.get('success') else '失败'}")
        
        if result.get('success'):
            data = result.get('data', [])
            print(f"识别题目数: {len(data)}")
            
            if data:
                print("\n识别结果示例 (前3题):")
                for item in data[:3]:
                    print(f"  题{item.get('index')}: 学生答案={item.get('userAnswer')}, "
                          f"标准答案={item.get('answer')}, 正确={item.get('correct')}")
            
            print("✓ API 端点测试通过")
            return True
        else:
            print(f"✗ API 返回错误: {result.get('error')}")
            if result.get('raw'):
                print(f"原始响应: {result.get('raw')[:200]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        print("⚠ 无法连接到服务器，请确保服务器正在运行 (python app.py)")
        return None
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("动态提示词功能测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: 动态提示词构建
    results.append(("动态提示词构建", test_build_dynamic_prompt()))
    
    # 测试2: 数据库获取 data_value
    results.append(("数据库获取", test_get_homework_data_value() is not False))
    
    # 测试3: 结构一致性
    results.append(("结构一致性", test_compare_structure()))
    
    # 测试4: API 端点 (可选)
    api_result = test_api_endpoint()
    if api_result is not None:
        results.append(("API端点", api_result))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 测试通过")
