"""
AI调研员 - 完整调研流程端到端测试

测试输入：2026年国内AI应用教育市场消费调研
测试步骤：创建任务 → 需求解析 → 数据采集 → 数据清洗 → 智能分析 → 报告生成
"""

import json
import time
import requests

BASE_URL = "http://127.0.0.1:5000"
TASK_ID = None


def step(name, func):
    """执行测试步骤并打印结果"""
    print(f"\n{'='*60}")
    print(f"  步骤: {name}")
    print(f"{'='*60}")
    try:
        result = func()
        print(f"  ✓ {name} 完成")
        return result
    except Exception as e:
        print(f"  ✗ {name} 失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_create_task():
    """步骤1: 创建调研任务"""
    global TASK_ID
    resp = requests.post(f"{BASE_URL}/api/research-agent/tasks", json={
        "query": "2026年国内AI应用教育市场消费调研",
        "industry": "AI教育",
        "scope": "国内市场，2024-2026年",
        "llm_model": "deepseek-v3.2"
    }, timeout=30)
    data = resp.json()
    assert data["success"], f"创建失败: {data.get('error')}"
    TASK_ID = data["task"]["task_id"]
    print(f"  Task ID: {TASK_ID}")
    print(f"  Query: {data['task']['query']}")
    return data


def test_parse_requirement():
    """步骤2: 解析调研需求，生成提纲"""
    resp = requests.post(f"{BASE_URL}/api/research-agent/parse", json={
        "task_id": TASK_ID
    }, timeout=120)
    data = resp.json()
    assert data["success"], f"解析失败: {data.get('error')}"
    
    outline = data["outline"]
    print(f"  标题: {outline.get('title', 'N/A')}")
    print(f"  目标: {outline.get('objective', 'N/A')[:100]}")
    print(f"  范围: {outline.get('scope', 'N/A')[:100]}")
    print(f"  章节数: {len(outline.get('items', []))}")
    
    for i, item in enumerate(outline.get("items", []), 1):
        print(f"    {i}. {item.get('title', 'N/A')}")
        for sub in item.get("sub_items", []):
            print(f"       - {sub.get('title', 'N/A')}")
    
    print(f"  采集计划: {len(outline.get('collection_plan', []))}项")
    
    # 推荐分析模型
    recs = data.get("recommended_models", [])
    print(f"  推荐分析模型: {[r['name'] for r in recs]}")
    
    return data


def test_collect_data():
    """步骤3: 数据采集（联网搜索）"""
    print("  正在联网搜索，可能需要1-2分钟...")
    resp = requests.post(f"{BASE_URL}/api/research-agent/collect", json={
        "task_id": TASK_ID,
        "max_queries": 8  # 测试时限制搜索量
    }, timeout=300)
    data = resp.json()
    assert data["success"], f"采集失败: {data.get('error')}"
    
    count = data.get("collected_count", 0)
    collected = data.get("collected_data", [])
    
    print(f"  采集数据量: {count}条")
    
    # 统计来源可信度
    cred_stats = {}
    for item in collected:
        cred = item.get("source", {}).get("credibility", "unknown")
        cred_stats[cred] = cred_stats.get(cred, 0) + 1
    print(f"  可信度分布: {cred_stats}")
    
    # 展示前3条数据
    for i, item in enumerate(collected[:3], 1):
        print(f"  [{i}] {item.get('title', 'N/A')[:60]}")
        print(f"      来源: {item.get('source', {}).get('name', 'N/A')[:40]}")
        print(f"      可信度: {item.get('source', {}).get('credibility', 'N/A')}")
    
    return data


def test_clean_data():
    """步骤4: 数据清洗"""
    resp = requests.post(f"{BASE_URL}/api/research-agent/clean", json={
        "task_id": TASK_ID
    }, timeout=180)
    data = resp.json()
    assert data["success"], f"清洗失败: {data.get('error')}"
    
    count = data.get("cleaned_count", 0)
    cleaned = data.get("cleaned_data", [])
    
    print(f"  清洗后数据量: {count}条")
    
    # 统计
    verified = sum(1 for d in cleaned if d.get("is_verified"))
    conflicting = sum(1 for d in cleaned if d.get("is_conflicting"))
    print(f"  已校验: {verified}条")
    print(f"  数据冲突: {conflicting}条")
    
    return data


def test_analyze():
    """步骤5: 智能分析"""
    resp = requests.post(f"{BASE_URL}/api/research-agent/analyze", json={
        "task_id": TASK_ID,
        "model_types": ["swot", "pest", "market_size"]
    }, timeout=300)
    data = resp.json()
    assert data["success"], f"分析失败: {data.get('error')}"
    
    results = data.get("analysis_results", [])
    print(f"  分析结果: {len(results)}项")
    
    for result in results:
        model_name = result.get("title", result.get("model_type", "unknown"))
        content_len = len(result.get("content", ""))
        citations = len(result.get("source_citations", []))
        charts = len(result.get("chart_suggestions", []))
        
        print(f"  [{result.get('model_type', 'N/A')}] {model_name}")
        print(f"    内容长度: {content_len}字")
        print(f"    数据引用: {citations}条")
        print(f"    图表建议: {charts}条")
        
        # 展示内容片段
        content = result.get("content", "")
        if content:
            preview = content[:200].replace("\n", " ")
            print(f"    预览: {preview}...")
        
        # 可信度说明
        note = result.get("confidence_note", "")
        if note:
            print(f"    可信度: {note[:100]}")
    
    return data


def test_generate_report():
    """步骤6: 生成调研报告"""
    resp = requests.post(f"{BASE_URL}/api/research-agent/generate-report", json={
        "task_id": TASK_ID,
        "format": "markdown"
    }, timeout=300)
    data = resp.json()
    assert data["success"], f"报告生成失败: {data.get('error')}"
    
    report = data.get("report", {})
    print(f"  报告标题: {report.get('title', 'N/A')}")
    print(f"  版本: v{report.get('version', 1)}")
    print(f"  章节数: {len(report.get('sections', []))}")
    
    # 执行摘要
    summary = report.get("summary", "")
    if summary:
        print(f"  执行摘要: {summary[:200]}...")
    
    # 章节列表
    for i, section in enumerate(report.get("sections", []), 1):
        title = section.get("title", "")
        content_len = len(section.get("content", ""))
        print(f"    {i}. {title} ({content_len}字)")
    
    # 附录
    appendix = report.get("appendix", [])
    if appendix:
        print(f"  附录: {len(appendix)}项")
    
    # 完整报告内容长度
    full_content = report.get("content", "")
    print(f"  报告总字数: {len(full_content)}字")
    
    # 反幻觉检查：检查是否有来源标注
    has_source_ref = "[来源" in full_content or "来源：" in full_content or "[来源：" in full_content
    has_warning = "⚠" in full_content or "暂无公开数据" in full_content or "仅供参考" in full_content
    print(f"  反幻觉检查:")
    print(f"    包含来源标注: {has_source_ref}")
    print(f"    包含不确定标注: {has_warning}")
    
    # 保存报告到本地
    if full_content:
        with open("test_report_output.md", "w", encoding="utf-8") as f:
            f.write(full_content)
        print(f"  报告已保存到 test_report_output.md")
    
    return data


def test_task_summary():
    """最终: 获取任务完整状态"""
    resp = requests.get(f"{BASE_URL}/api/research-agent/tasks/{TASK_ID}", timeout=30)
    data = resp.json()
    assert data["success"]
    
    task = data["task"]
    print(f"  状态: {task.get('status', 'N/A')}")
    print(f"  总Token消耗: {task.get('total_tokens_used', 0):,}")
    print(f"  采集数据: {len(task.get('collected_data', []))}条")
    print(f"  清洗数据: {len(task.get('cleaned_data', []))}条")
    print(f"  分析结果: {len(task.get('analysis_results', []))}项")
    print(f"  报告版本: v{task.get('report', {}).get('version', 'N/A')}")


# ============ 运行测试 ============

if __name__ == "__main__":
    start_time = time.time()
    
    print("\n" + "=" * 60)
    print("  AI调研员 - 完整流程端到端测试")
    print("  输入: 2026年国内AI应用教育市场消费调研")
    print("=" * 60)
    
    step("1. 创建调研任务", test_create_task)
    step("2. 解析调研需求", test_parse_requirement)
    step("3. 联网数据采集", test_collect_data)
    step("4. 数据清洗校验", test_clean_data)
    step("5. 智能分析（SWOT/PEST/市场规模）", test_analyze)
    step("6. 生成调研报告", test_generate_report)
    step("最终状态汇总", test_task_summary)
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"  全流程测试完成！耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
    print(f"{'='*60}")
