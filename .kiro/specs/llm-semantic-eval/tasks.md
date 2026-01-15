# LLM 语义级评估 - 实现任务

## 已完成

- [x] 1. 创建设计文档
  - 定义评估维度和错误分类体系
  - 设计提示词模板
  - 设计 API 接口
  - _Requirements: 语义评估核心逻辑_

- [x] 2. 实现语义评估服务
  - [x] 2.1 创建 `services/semantic_eval_service.py`
  - [x] 2.2 实现规则预筛逻辑 `rule_based_precheck`
  - [x] 2.3 实现单题语义评估 `evaluate_single`
  - [x] 2.4 实现批量语义评估 `evaluate_batch`
  - [x] 2.5 实现汇总报告生成 `_generate_summary`
  - _Requirements: 语义评估服务层_

- [x] 3. 更新 API 路由
  - [x] 3.1 添加单题语义评估 API `/api/ai-eval/semantic`
  - [x] 3.2 添加批量语义评估 API `/api/ai-eval/semantic-batch`
  - [x] 3.3 添加评估报告 API `/api/ai-eval/report`
  - [x] 3.4 添加基准效果对比 API `/api/ai-eval/compare-with-base`
  - _Requirements: API 接口层_

- [x] 4. 编写测试
  - [x] 4.1 规则预筛测试
  - [x] 4.2 汇总报告测试
  - [x] 4.3 属性测试（hypothesis）
  - _Requirements: 测试覆盖_

- [x] 5. 集成到批量评估模块
  - [x] 5.1 在 `batch_evaluation.py` 中添加语义评估 API
    - `/tasks/<task_id>/semantic-evaluate` - 批量任务语义评估（SSE）
    - `/tasks/<task_id>/semantic-report` - 获取语义评估报告
    - `/evaluate-single-semantic` - 单题语义评估
  - [x] 5.2 重写 `do_ai_compare_batch()` 使用 `SemanticEvalService`
  - [x] 5.3 添加 `convert_semantic_to_batch_result()` 转换函数
  - [x] 5.4 清理旧的 `convert_batch_ai_compare()` 残留代码
  - [ ] 5.5 更新前端 UI 支持语义评估模式（待实现）
  - _Requirements: 模块集成_

- [x] 6. 提示词配置化
  - [x] 6.1 将提示词模板移到 `prompts.json`
  - [x] 6.2 服务层支持从配置加载提示词
  - [ ] 6.3 支持提示词版本管理（待实现）
  - _Requirements: 配置管理_

## 待完成

- [ ] 7. 前端 UI 集成
  - [ ] 7.1 批量评估页面添加"语义评估"按钮
  - [ ] 7.2 显示语义评估进度和结果
  - [ ] 7.3 语义评估报告可视化展示
  - _Requirements: 用户界面_

## 文件清单

| 文件 | 状态 | 说明 |
|-----|------|-----|
| `.kiro/specs/llm-semantic-eval/design.md` | 已创建 | 设计文档 |
| `services/semantic_eval_service.py` | 已更新 | 语义评估服务（支持配置化提示词）|
| `routes/ai_eval.py` | 已更新 | AI 评估 API |
| `routes/batch_evaluation.py` | 已更新 | 批量评估集成语义评估 |
| `prompts.json` | 已更新 | 添加语义评估提示词模板 |
| `tests/test_semantic_eval.py` | 已创建 | 测试文件（11 passed）|

## API 清单

| API | 方法 | 说明 | 模块 |
|-----|------|-----|------|
| `/api/ai-eval/semantic` | POST | 单题语义评估 | ai_eval |
| `/api/ai-eval/semantic-batch` | POST | 批量语义评估 | ai_eval |
| `/api/ai-eval/report` | POST | 生成评估报告 | ai_eval |
| `/api/ai-eval/compare-with-base` | POST | 与基准效果对比 | ai_eval |
| `/tasks/<task_id>/semantic-evaluate` | POST | 批量任务语义评估（SSE）| batch_evaluation |
| `/tasks/<task_id>/semantic-report` | GET | 获取语义评估报告 | batch_evaluation |
| `/evaluate-single-semantic` | POST | 单题语义评估 | batch_evaluation |

## 提示词配置

提示词已移至 `prompts.json`，支持以下 key：

| Key | 说明 |
|-----|------|
| `semantic_eval_system` | 语义评估系统提示词 |
| `semantic_eval_template` | 单题评估模板 |
| `batch_eval_template` | 批量评估模板 |
| `summary_report_template` | 汇总报告模板 |
