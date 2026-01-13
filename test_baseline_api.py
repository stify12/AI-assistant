"""
测试基准效果API的脚本
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_save_baseline():
    """测试保存基准效果"""
    print("测试保存基准效果...")
    
    data = {
        "homework_name": "测试作业",
        "page_num": "1",
        "subject_id": 0,
        "base_effect": [
            {
                "index": "1",
                "answer": "A",
                "userAnswer": "A",
                "correct": "yes",
                "tempIndex": 0
            },
            {
                "index": "2",
                "answer": "B",
                "userAnswer": "C",
                "correct": "no",
                "tempIndex": 1
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/grading/save-baseline", json=data)
    result = response.json()
    
    print(f"状态: {result.get('success')}")
    if result.get('success'):
        print(f"保存路径: {result.get('filepath')}")
    else:
        print(f"错误: {result.get('error')}")
    
    return result.get('success')


def test_load_baseline():
    """测试加载基准效果"""
    print("\n测试加载基准效果...")
    
    data = {
        "homework_name": "测试作业",
        "page_num": "1"
    }
    
    response = requests.post(f"{BASE_URL}/api/grading/load-baseline", json=data)
    result = response.json()
    
    print(f"状态: {result.get('success')}")
    if result.get('success'):
        print(f"基准效果题目数: {len(result.get('base_effect', []))}")
        print(f"创建时间: {result.get('created_at')}")
        print(f"基准效果内容: {json.dumps(result.get('base_effect'), ensure_ascii=False, indent=2)}")
    else:
        print(f"错误: {result.get('error')}")
    
    return result.get('success')


if __name__ == "__main__":
    print("=" * 50)
    print("基准效果API测试")
    print("=" * 50)
    
    # 测试保存
    save_success = test_save_baseline()
    
    # 测试加载
    if save_success:
        load_success = test_load_baseline()
        
        if load_success:
            print("\n✓ 所有测试通过！")
        else:
            print("\n✗ 加载测试失败")
    else:
        print("\n✗ 保存测试失败")
    
    print("=" * 50)
