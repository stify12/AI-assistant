"""测试数据分析工作流"""
import requests
import json
import time

BASE_URL = 'http://127.0.0.1:5000'

def test_workflow():
    print("=" * 50)
    print("测试数据分析工作流 (DeepSeek V3)")
    print("=" * 50)
    
    # 1. 创建任务
    print("\n1. 创建分析任务...")
    resp = requests.post(f'{BASE_URL}/api/analysis/tasks', json={
        'name': '测试任务',
        'description': '测试DeepSeek V3模型'
    })
    task = resp.json()
    task_id = task['task_id']
    print(f"   任务创建成功: {task_id}")
    
    # 2. 上传文件
    print("\n2. 上传测试文件...")
    with open('test_data.xlsx', 'rb') as f:
        resp = requests.post(
            f'{BASE_URL}/api/analysis/tasks/{task_id}/files',
            files={'files': ('test_data.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        )
    result = resp.json()
    print(f"   上传结果: {len(result.get('uploaded', []))} 个文件")
    
    # 3. 启动工作流
    print("\n3. 启动工作流...")
    resp = requests.post(f'{BASE_URL}/api/analysis/tasks/{task_id}/workflow/start')
    print(f"   工作流状态: {resp.json()}")
    
    # 4. 执行解析步骤
    print("\n4. 执行数据解析步骤...")
    resp = requests.post(f'{BASE_URL}/api/analysis/tasks/{task_id}/workflow/step/parse', stream=True)
    for line in resp.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                if data != '[DONE]':
                    try:
                        result = json.loads(data)
                        if result.get('filename'):
                            print(f"   解析完成: {result['filename']} - {result['status']}")
                        if result.get('step_completed'):
                            print(f"   步骤完成: {result['step_completed']}")
                    except:
                        pass
    
    # 5. 执行分析步骤
    print("\n5. 执行内容分析步骤...")
    resp = requests.post(f'{BASE_URL}/api/analysis/tasks/{task_id}/workflow/step/analyze', stream=True)
    for line in resp.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                if data != '[DONE]':
                    try:
                        result = json.loads(data)
                        if result.get('filename'):
                            print(f"   分析完成: {result['filename']} - {result['status']}")
                        if result.get('step_completed'):
                            print(f"   步骤完成: {result['step_completed']}")
                    except:
                        pass
    
    # 6. 执行模板生成步骤
    print("\n6. 执行模板生成步骤...")
    resp = requests.post(f'{BASE_URL}/api/analysis/tasks/{task_id}/workflow/step/template')
    result = resp.json()
    if result.get('template'):
        print(f"   模板生成成功")
        template = result['template']
        if isinstance(template, dict) and template.get('title'):
            print(f"   报告标题: {template.get('title')}")
    
    # 7. 执行报告编写步骤
    print("\n7. 执行报告编写步骤...")
    resp = requests.post(f'{BASE_URL}/api/analysis/tasks/{task_id}/workflow/step/report')
    result = resp.json()
    if result.get('report'):
        print(f"   报告生成成功")
        report = result['report']
        content = report.get('content', '')
        print(f"   报告长度: {len(content)} 字符")
        print(f"   报告预览: {content[:200]}...")
    
    # 8. 获取最终状态
    print("\n8. 获取任务最终状态...")
    resp = requests.get(f'{BASE_URL}/api/analysis/tasks/{task_id}')
    task = resp.json()
    print(f"   任务状态: {task.get('status')}")
    print(f"   工作流当前步骤: {task.get('workflow_state', {}).get('current_step')}")
    
    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)
    
    return task_id

if __name__ == '__main__':
    test_workflow()
