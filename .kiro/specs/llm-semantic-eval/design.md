# LLM 语义级评估设计文档

## 一、背景与目标

### 1.1 当前问题

现有的规则评估（`do_evaluation` 函数）存在以下局限性：

| 问题 | 示例 | 影响 |
|-----|------|-----|
| 字符串匹配死板 | "3/4" vs "0.75" 被判为不同 | 误判等价答案 |
| 数学表达式等价性 | "x+1" vs "1+x" 被判为不同 | 误判正确答案 |
| 无法识别部分正确 | 答案部分对、部分错 | 评估粒度粗 |
| 语义理解缺失 | 无法理解答案实际含义 | 漏判等价表达 |

### 1.2 优化目标

1. **提升评估准确性** - 通过 LLM 语义理解，识别等价表达
2. **精准定位问题** - 区分识别能力和判断能力的问题
3. **检测 AI 幻觉** - 识别 AI "脑补"答案的情况
4. **结构化输出** - 评估结果清晰易懂，便于分析

## 二、核心设计

### 2.1 评估维度

```
┌─────────────────────────────────────────────────────────┐
│                    AI 批改效果评估                       │
├─────────────────────────────────────────────────────────┤
│  1. 识别能力                                            │
│     ├─ 字面一致性：AI 识别结果与人工标注是否相同         │
│     └─ 语义等价性：不同表达是否数学/语义等价             │
│                                                         │
│  2. 判断能力                                            │
│     └─ 对错判断：AI 判断结果与人工标注是否一致           │
│                                                         │
│  3. 幻觉检测                                            │
│     └─ AI 是否将错误答案"脑补"成正确答案                │
└─────────────────────────────────────────────────────────┘
```

### 2.2 错误分类体系

| 错误类型 | 识别 | 判断 | 严重程度 | 说明 |
|---------|------|------|---------|------|
| 完全正确 | ✓ | ✓ | none | AI 批改完全正确 |
| 语义等价 | ≈ | ✓ | low | 字面不同但语义等价 |
| 识别正确-判断错误 | ✓ | ✗ | high | 识别对但判断错 |
| 识别错误-判断正确 | ✗ | ✓ | medium | 识别错但判断碰巧对 |
| 识别错误-判断错误 | ✗ | ✗ | high | 识别和判断都错 |
| AI 幻觉 | 脑补 | ✓ | critical | 最严重，AI 自行"修正"答案 |

### 2.3 严重程度定义

| 级别 | 英文 | 说明 | 处理建议 |
|-----|------|------|---------|
| none | 无 | 完全正确 | 无需处理 |
| low | 轻微 | 格式差异，不影响结果 | 可忽略 |
| medium | 中等 | 识别有偏差但判断正确 | 关注 |
| high | 严重 | 判断错误 | 需修复 |
| critical | 致命 | AI 幻觉 | 紧急修复 |

## 三、评估流程

### 3.1 三阶段评估流程

```
┌─────────────────────────────────────────────────────────┐
│                    评估流程                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  阶段1: 规则预筛（快速）                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • 字符串标准化比较                               │   │
│  │ • 输出：明确匹配 / 明确不匹配 / 不确定           │   │
│  │ • 明确的结果直接输出，不确定的进入阶段2          │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓                               │
│  阶段2: LLM 语义评估（精准）                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • 仅处理规则评估"不确定"的题目                   │   │
│  │ • 调用 DeepSeek 进行语义级分析                   │   │
│  │ • 支持批量评估（每批 10-20 题）                  │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓                               │
│  阶段3: 结果汇总（分析）                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • 合并规则评估 + LLM 评估结果                    │   │
│  │ • 计算能力评分和错误分布                         │   │
│  │ • 生成改进建议                                   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 3.2 规则预筛逻辑

```python
def rule_based_precheck(base_item, ai_item):
    """
    规则预筛：快速判断明确的匹配/不匹配情况
    返回: (certainty, result)
    - certainty: 'high' | 'low'
    - result: 预判结果
    """
    base_user = normalize(base_item['userAnswer'])
    ai_user = normalize(ai_item['userAnswer'])
    base_correct = base_item['correct']
    ai_correct = ai_item['correct']
    
    # 情况1: 完全一致 → 明确匹配
    if base_user == ai_user and base_correct == ai_correct:
        return ('high', {'verdict': 'PASS', 'error_type': '完全正确'})
    
    # 情况2: 判断不一致 → 明确不匹配
    if base_correct != ai_correct:
        return ('high', {'verdict': 'FAIL', 'error_type': '判断不一致'})
    
    # 情况3: 用户答案不一致但判断一致 → 需要 LLM 判断语义等价性
    return ('low', None)
```

## 四、提示词设计

### 4.1 单题语义评估提示词

```
【角色定义】
你是 AI 批改效果评估专家，专门分析 AI 批改系统的识别能力和判断能力。
你的任务是对比「人工标注的基准效果」和「AI 批改结果」，精准定位 AI 的问题所在。

【评估背景】
- 学科：{{subject}}
- 题型：{{question_type}}
- 题号：{{index}}

【数据对比】
┌─────────────┬────────────────────┬────────────────────┐
│    项目      │   基准效果(人工)    │    AI批改结果       │
├─────────────┼────────────────────┼────────────────────┤
│  标准答案    │ {{standard_answer}}                      │
├─────────────┼────────────────────┼────────────────────┤
│  学生答案    │ {{base_user_answer}} │ {{ai_user_answer}} │
├─────────────┼────────────────────┼────────────────────┤
│  判断结果    │ {{base_correct}}    │ {{ai_correct}}     │
└─────────────┴────────────────────┴────────────────────┘

【评估任务】
请从以下三个维度分析 AI 批改效果：

1️⃣ 识别能力分析
   - AI 识别的学生答案是否与人工识别一致？
   - 如果不一致，是完全错误还是语义等价？
   - 语义等价示例：3/4 ≈ 0.75、x+1 ≈ 1+x、ABC ≈ A,B,C

2️⃣ 判断能力分析
   - AI 的对错判断是否与人工判断一致？
   - 如果不一致，AI 判断的依据可能是什么？

3️⃣ 幻觉检测
   - 是否存在 AI 幻觉？（学生答错，但 AI 把答案"脑补"成标准答案）
   - 幻觉特征：base_correct=no + ai_user_answer≈standard_answer

【输出格式】
严格按以下 JSON 格式输出，不要输出其他内容：

{
  "verdict": "PASS|FAIL",
  "verdict_cn": "通过|不通过",
  
  "recognition": {
    "status": "一致|语义等价|不一致",
    "base": "人工识别的答案",
    "ai": "AI识别的答案",
    "diff_type": "无差异|格式差异|内容差异|完全错误",
    "detail": "具体差异说明"
  },
  
  "judgment": {
    "status": "一致|不一致",
    "base": "yes/no",
    "ai": "yes/no",
    "detail": "判断差异说明"
  },
  
  "hallucination": {
    "detected": true/false,
    "detail": "幻觉说明，无则为空"
  },
  
  "error_type": "完全正确|识别正确-判断错误|识别错误-判断正确|识别错误-判断错误|语义等价|AI幻觉",
  "severity": "none|low|medium|high|critical",
  "severity_cn": "无|轻微|中等|严重|致命",
  
  "summary": "一句话总结评估结果",
  "suggestion": "改进建议（如有）"
}

【严重程度定义】
- none: 完全正确
- low: 格式差异，不影响结果
- medium: 识别有偏差但判断正确
- high: 判断错误
- critical: AI幻觉（最严重）
```

### 4.2 批量评估提示词

```
【角色定义】
你是 AI 批改效果评估专家，需要批量分析多道题目的 AI 批改效果。

【评估数据】
学科：{{subject}}
题型：{{question_type}}

以下是需要评估的题目列表（JSON 格式）：
{{questions_json}}

【评估要求】
对每道题目进行独立评估，重点关注：
1. 识别是否一致或语义等价
2. 判断是否正确
3. 是否存在 AI 幻觉

【输出格式】
输出 JSON 数组，每个元素对应一道题：
[
  {
    "index": "题号",
    "verdict": "PASS|FAIL",
    "error_type": "完全正确|识别正确-判断错误|识别错误-判断正确|识别错误-判断错误|语义等价|AI幻觉",
    "severity": "none|low|medium|high|critical",
    "recognition_status": "一致|语义等价|不一致",
    "judgment_status": "一致|不一致",
    "hallucination": true/false,
    "summary": "一句话总结"
  }
]
```

### 4.3 汇总报告提示词

```
【角色定义】
你是 AI 批改效果分析师，需要根据逐题评估结果生成整体分析报告。

【评估数据】
{{evaluation_results_json}}

【分析要求】
请从以下维度生成分析报告：

1. 整体表现：通过率、准确率、各类错误分布
2. 能力分析：识别能力评分、判断能力评分、幻觉率
3. 问题定位：主要问题类型、高频错误模式
4. 改进建议：针对性优化方向

【输出格式】
{
  "overview": {
    "total": 总题数,
    "passed": 通过数,
    "failed": 失败数,
    "pass_rate": 通过率百分比,
    "accuracy": 准确率百分比
  },
  
  "error_distribution": {
    "完全正确": 数量,
    "语义等价": 数量,
    "识别正确-判断错误": 数量,
    "识别错误-判断正确": 数量,
    "识别错误-判断错误": 数量,
    "AI幻觉": 数量
  },
  
  "severity_distribution": {
    "none": 数量,
    "low": 数量,
    "medium": 数量,
    "high": 数量,
    "critical": 数量
  },
  
  "capability_scores": {
    "recognition": 0-100,
    "judgment": 0-100,
    "overall": 0-100
  },
  
  "hallucination_rate": 幻觉率百分比,
  
  "top_issues": [
    {"issue": "问题描述", "count": 出现次数, "impact": "影响说明"}
  ],
  
  "recommendations": ["改进建议1", "改进建议2"],
  
  "conclusion": "整体结论（2-3句话）"
}
```

## 五、API 设计

### 5.1 单题语义评估

```
POST /api/ai-eval/semantic
Content-Type: application/json

Request:
{
  "subject": "数学",
  "question_type": "填空题",
  "index": "1",
  "standard_answer": "3/4",
  "base_user_answer": "0.75",
  "base_correct": "yes",
  "ai_user_answer": "0.75",
  "ai_correct": "yes"
}

Response:
{
  "verdict": "PASS",
  "verdict_cn": "通过",
  "recognition": {...},
  "judgment": {...},
  "hallucination": {...},
  "error_type": "语义等价",
  "severity": "low",
  "severity_cn": "轻微",
  "summary": "AI 识别结果与人工标注语义等价，判断正确",
  "suggestion": ""
}
```

### 5.2 批量语义评估

```
POST /api/ai-eval/semantic-batch
Content-Type: application/json

Request:
{
  "subject": "数学",
  "question_type": "填空题",
  "items": [
    {
      "index": "1",
      "standard_answer": "...",
      "base_user_answer": "...",
      "base_correct": "yes",
      "ai_user_answer": "...",
      "ai_correct": "yes"
    }
  ],
  "eval_model": "deepseek-v3.2"
}

Response:
{
  "results": [...],
  "summary": {...}
}
```

### 5.3 评估报告生成

```
POST /api/ai-eval/report
Content-Type: application/json

Request:
{
  "evaluation_results": [...]
}

Response:
{
  "overview": {...},
  "error_distribution": {...},
  "capability_scores": {...},
  "recommendations": [...],
  "conclusion": "..."
}
```

## 六、数据结构

### 6.1 评估结果结构

```python
class SemanticEvalResult:
    verdict: str           # "PASS" | "FAIL"
    verdict_cn: str        # "通过" | "不通过"
    recognition: dict      # 识别分析
    judgment: dict         # 判断分析
    hallucination: dict    # 幻觉检测
    error_type: str        # 错误类型
    severity: str          # 严重程度
    severity_cn: str       # 严重程度中文
    summary: str           # 一句话总结
    suggestion: str        # 改进建议
```

### 6.2 汇总报告结构

```python
class EvalSummaryReport:
    overview: dict              # 整体概览
    error_distribution: dict    # 错误分布
    severity_distribution: dict # 严重程度分布
    capability_scores: dict     # 能力评分
    hallucination_rate: float   # 幻觉率
    top_issues: list            # 主要问题
    recommendations: list       # 改进建议
    conclusion: str             # 整体结论
```

## 七、配置设计

在 `prompts.json` 中添加评估提示词配置：

```json
{
  "ai_eval_prompts": {
    "semantic_single": {
      "name": "单题语义评估",
      "system": "你是 AI 批改效果评估专家...",
      "template": "【评估背景】..."
    },
    "semantic_batch": {
      "name": "批量语义评估",
      "system": "...",
      "template": "..."
    },
    "summary_report": {
      "name": "汇总报告",
      "system": "...",
      "template": "..."
    }
  }
}
```

## 八、实现计划

1. **服务层** - `services/semantic_eval_service.py`
   - 规则预筛逻辑
   - LLM 调用封装
   - 结果解析和合并

2. **路由层** - 更新 `routes/ai_eval.py`
   - 新增语义评估 API
   - 新增批量评估 API
   - 新增报告生成 API

3. **配置层** - 更新 `prompts.json`
   - 添加评估提示词配置

4. **测试** - `tests/test_semantic_eval.py`
   - 单题评估测试
   - 批量评估测试
   - 边界情况测试
