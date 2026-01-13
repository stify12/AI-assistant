# Implementation Plan

## 1. 项目基础设置

- [ ] 1.1 创建批量评估页面路由和模板
  - 在app.py中添加 /batch-evaluation 路由
  - 创建 templates/batch-evaluation.html 模板文件
  - 创建 static/css/batch-evaluation.css 样式文件
  - 创建 static/js/batch-evaluation.js 脚本文件
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 1.2 在学科评估页面添加批量评估入口
  - 修改 templates/subject-grading.html 添加入口按钮
  - _Requirements: 1.1_

## 2. 图书数据API实现

- [ ] 2.1 实现获取图书列表API
  - 创建 GET /api/batch/books 接口
  - 从zp_make_book表查询图书数据
  - 按subject_id分组返回
  - 处理书名中文转换
  - _Requirements: 2.1, 2.2_

- [ ] 2.2 编写图书数据API属性测试
  - **Property 1: 图书数据按学科分组正确性**
  - **Validates: Requirements 2.1**

- [ ] 2.3 实现获取书本页码列表API
  - 创建 GET /api/batch/books/{book_id}/pages 接口
  - 从zp_book_chapter表查询章节和页码
  - 返回章节分组和全部页码列表
  - _Requirements: 2.3_

- [ ] 2.4 编写页码列表API属性测试
  - **Property 2: 页码归属正确性**
  - **Validates: Requirements 2.3**

## 3. 数据集管理功能

- [ ] 3.1 创建数据集存储目录和数据结构
  - 创建 datasets/ 目录用于存储数据集JSON文件
  - 定义数据集文件命名规则和结构
  - _Requirements: 3.3_

- [ ] 3.2 实现数据集CRUD API
  - 创建 GET /api/batch/datasets 接口（列表查询）
  - 创建 POST /api/batch/datasets 接口（创建数据集）
  - 创建 DELETE /api/batch/datasets/{id} 接口（删除数据集）
  - _Requirements: 3.2, 3.3, 3.4, 3.5_

- [ ] 3.3 编写数据集管理属性测试
  - **Property 3: 数据集保存round-trip**
  - **Property 4: 数据集列表字段完整性**
  - **Property 5: 数据集删除正确性**
  - **Validates: Requirements 3.3, 3.4, 3.5**

## 4. 数据集自动识别功能

- [x] 4.1 实现检查页码可用作业图片API
  - 创建 GET /api/batch/datasets/available-homework 接口
  - 查询指定book_id和page_num在指定时间范围内的作业图片
  - 返回可用作业列表（homework_id, student_name, pic_path, create_time）
  - _Requirements: 3.6_

- [x] 4.2 实现数据集页码自动识别基准效果API
  - 创建 POST /api/batch/datasets/auto-recognize 接口
  - 根据book_id和page_num查找最近的作业图片
  - 调用AI视觉模型识别作业图片生成基准效果
  - 返回识别结果和来源作业信息
  - _Requirements: 3.7, 3.8_

- [ ] 4.3 编写数据集自动识别属性测试
  - **Property 17: 可用作业时间范围过滤正确性**
  - **Property 18: 自动识别结果格式正确性**
  - **Validates: Requirements 3.6, 3.7, 3.8**

- [x] 4.4 前端实现数据集页码自动识别交互
  - 在数据集编辑弹窗中为每个页码显示「自动识别」按钮
  - 点击按钮时检查是否有可用作业图片
  - 调用自动识别API获取基准效果
  - 以模块化卡片形式展示识别结果供用户编辑
  - _Requirements: 3.6, 3.7, 3.8, 3.9_

## 5. Checkpoint - 确保所有测试通过
- [ ] 5. Ensure all tests pass, ask the user if questions arise.

## 6. 批量评估任务管理

- [ ] 6.1 创建任务存储目录和数据结构
  - 创建 batch_tasks/ 目录用于存储任务JSON文件
  - 定义任务文件命名规则和结构
  - _Requirements: 4.5_

- [ ] 6.2 实现任务CRUD API
  - 创建 GET /api/batch/tasks 接口（任务列表）
  - 创建 POST /api/batch/tasks 接口（创建任务）
  - 创建 GET /api/batch/tasks/{id} 接口（任务详情）
  - 创建 DELETE /api/batch/tasks/{id} 接口（删除任务）
  - _Requirements: 4.1, 4.4, 4.5, 9.1, 9.2, 9.3_

- [ ] 6.3 实现作业任务查询（用于任务创建）
  - 查询zp_homework表status=3的记录
  - 支持按学科、时间范围筛选
  - _Requirements: 4.2, 4.3_

- [ ] 6.4 编写任务管理属性测试
  - **Property 6: 作业任务状态过滤正确性**
  - **Property 7: 任务作业数量一致性**
  - **Property 8: 任务ID唯一性**
  - **Property 14: 历史任务排序正确性**
  - **Property 15: 任务加载round-trip**
  - **Property 16: 任务删除正确性**
  - **Validates: Requirements 4.2, 4.4, 4.5, 9.1, 9.2, 9.3**

## 7. 基准效果自动匹配

- [ ] 7.1 实现基准效果匹配逻辑
  - 在任务创建时自动匹配数据集
  - 根据book_id和page_num查找匹配的数据集
  - 更新homework_item的matched_dataset字段
  - _Requirements: 5.1, 5.2_

- [ ] 7.2 编写基准效果匹配属性测试
  - **Property 9: 基准效果匹配正确性**
  - **Validates: Requirements 5.1, 5.2**

## 8. Checkpoint - 确保所有测试通过
- [ ] 8. Ensure all tests pass, ask the user if questions arise.

## 9. 批量评估执行

- [ ] 9.1 实现批量评估执行API
  - 创建 POST /api/batch/tasks/{id}/evaluate 接口
  - 实现SSE流式返回评估进度
  - 依次评估每个作业任务
  - 复用现有evaluate_grading评估逻辑
  - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [ ] 9.2 实现自动识别基准效果功能
  - 对未匹配数据集的作业调用AI识别
  - 复用现有auto_recognize_from_db逻辑
  - _Requirements: 5.3, 5.4_

- [ ] 9.3 实现单个作业评估详情API
  - 创建 GET /api/batch/tasks/{id}/homework/{hw_id} 接口
  - 返回详细评估结果
  - _Requirements: 6.4_

- [ ] 9.4 编写批量评估属性测试
  - **Property 10: 准确率计算正确性**
  - **Property 11: 任务完成状态正确性**
  - **Validates: Requirements 6.2, 6.5**

## 9A. 题目类型分类统计功能

- [x] 9A.1 实现题目类型分类工具函数


  - 创建 classify_question_type() 函数
  - 根据 questionType 字段判断客观题/主观题
  - 根据 bvalue 字段判断选择题/非选择题
  - _Requirements: 12.1, 12.2, 12.3_



- [x] 9A.2 编写题目类型分类属性测试

  - **Property 17: 题目类型分类正确性**
  - **Validates: Requirements 12.2, 12.3**

- [x] 9A.3 实现题目类型统计计算函数


  - 创建 calculate_type_statistics() 函数

  - 计算主观题/客观题准确率
  - 计算选择题/非选择题准确率
  - _Requirements: 12.4, 12.5, 12.6_



- [x] 9A.4 编写题目类型统计属性测试

  - **Property 18: 题目类型统计计算正确性**


  - **Validates: Requirements 12.4, 12.5, 12.6**



- [x] 9A.5 修改数据集创建逻辑读取题目类型


  - 从 zp_homework.data_value 解析 questionType 和 bvalue
  - 保存到基准效果数据中


  - _Requirements: 12.7_



- [x] 9A.6 编写数据集题目类型保存属性测试


  - **Property 19: 数据集题目类型字段保存正确性**
  - **Validates: Requirements 12.7**




- [x] 9A.7 修改评估比对逻辑添加题目类型标注


  - 在比对结果中添加 question_category 字段
  - 标注每道题的主观/客观、选择/非选择类型
  - _Requirements: 12.8_

- [x] 9A.8 编写评估结果题目类型标注属性测试


  - **Property 20: 评估结果题目类型标注正确性**
  - **Validates: Requirements 12.8**

- [x] 9A.9 修改一键AI评估逻辑支持分类统计


  - 在 batch_ai_evaluate API 中集成题目类型统计
  - 在 overall_report 中添加 by_question_type 字段
  - _Requirements: 6.6, 6.7_

- [x] 9A.10 编写一键AI评估分类统计属性测试



  - **Property 21: 一键AI评估分类统计完整性**
  - **Validates: Requirements 6.6, 6.7**

## 10. 总体报告生成

- [ ] 10.1 实现总体报告生成逻辑
  - 计算总体准确率
  - 按书本、页码、题型统计
  - 汇总错误分布
  - _Requirements: 7.1, 7.2_

- [ ] 10.2 实现AI分析报告API
  - 创建 POST /api/batch/tasks/{id}/ai-report 接口
  - 调用DeepSeek生成分析报告
  - _Requirements: 7.3, 7.4_

- [ ] 10.3 编写总体报告属性测试
  - **Property 12: 总体报告统计正确性**
  - **Validates: Requirements 7.1, 7.2**

## 11. Excel导出功能

- [ ] 11.1 实现Excel导出API
  - 创建 GET /api/batch/tasks/{id}/export 接口
  - 生成总体概览工作表
  - 生成明细数据工作表
  - 使用openpyxl库生成Excel文件
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 11.2 在Excel总体概览中添加题目类型分类统计
  - 添加客观题准确率、主观题准确率
  - 添加选择题准确率、非选择题准确率
  - _Requirements: 8.4_

- [x] 11.3 在Excel明细数据中添加题目类型标注
  - 添加是否客观题列
  - 添加是否选择题列
  - 添加选择题类型列（单选/多选）
  - _Requirements: 8.5_

- [ ] 11.4 编写Excel导出属性测试
  - **Property 13: Excel工作表完整性**
  - **Property 22: Excel导出分类统计完整性**
  - **Validates: Requirements 8.2, 8.3, 8.4, 8.5**

## 12. Checkpoint - 确保所有测试通过
- [ ] 12. Ensure all tests pass, ask the user if questions arise.

## 13. 前端页面实现 - 基础框架

- [ ] 13.1 实现批量评估页面基础布局
  - 实现顶部Tab切换（任务管理/数据集管理）
  - 实现左右分栏布局
  - 应用黑白简洁风格
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 11.1_

- [ ] 13.2 实现任务管理视图
  - 左侧：历史任务列表
  - 右侧：任务详情面板
  - 新建任务按钮
  - _Requirements: 11.2_

- [ ] 13.3 实现数据集管理视图
  - 左侧：图书列表（按学科分组）
  - 右侧：书本详情和页码列表
  - _Requirements: 11.3_

## 14. 前端页面实现 - 弹窗组件

- [ ] 14.1 实现新建任务弹窗
  - 作业任务多选列表
  - 筛选条件（学科、时间范围）
  - 已选数量统计
  - _Requirements: 4.1, 4.3, 11.4_

- [ ] 14.2 实现数据集编辑弹窗
  - 页码选择
  - 基准效果编辑器（复用现有组件）
  - _Requirements: 3.1, 3.2, 11.4_

- [ ] 14.3 实现评估详情抽屉
  - 单个作业详细评估结果
  - 与单次评估页面一致的展示
  - _Requirements: 6.4, 11.5_

## 15. 前端页面实现 - 功能集成

- [ ] 15.1 实现任务列表和详情交互
  - 加载历史任务列表
  - 点击任务显示详情
  - 删除任务功能
  - _Requirements: 9.1, 9.2, 9.3_

- [ ] 15.2 实现图书和数据集交互
  - 加载图书列表
  - 点击图书显示页码
  - 数据集CRUD操作
  - _Requirements: 2.1, 2.3, 3.1, 3.4, 3.5_

- [ ] 15.3 实现批量评估执行交互
  - 启动评估按钮
  - 进度条显示
  - 实时更新准确率
  - _Requirements: 6.1, 6.2_

- [ ] 15.4 实现总体报告展示
  - 统计卡片
  - 按维度统计表格
  - AI分析报告展示
  - _Requirements: 7.1, 7.2, 7.4_

- [x] 15.5 实现题目类型分类统计展示
  - 在总体报告中显示主观题/客观题准确率
  - 在总体报告中显示选择题/非选择题准确率
  - 在单个作业详情中显示分类统计
  - _Requirements: 12.4, 12.5, 12.6_

- [ ] 15.6 实现Excel导出交互
  - 导出按钮
  - 下载文件
  - _Requirements: 8.1, 8.6_

## 16. Final Checkpoint - 确保所有测试通过
- [ ] 16. Ensure all tests pass, ask the user if questions arise.

