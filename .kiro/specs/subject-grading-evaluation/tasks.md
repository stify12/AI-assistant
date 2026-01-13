# Implementation Plan

## AI学科批改评估系统 - 任务清单

- [x] 1. 项目基础设置
  - [x] 1.1 创建页面路由和模板文件
    - 在app.py中添加/subject-grading路由
    - 创建templates/subject-grading.html
    - 创建static/css/subject-grading.css
    - 创建static/js/subject-grading.js
    - 更新index.html导航链接（替换原compare链接）
    - _Requirements: 2.1_

  - [x] 1.2 配置MySQL数据库连接
    - 在config.json中添加MySQL连接配置
    - 创建数据库连接工具函数
    - 测试数据库连接
    - _Requirements: 1.1_

- [x] 2. 后端API开发
  - [x] 2.1 实现获取批改数据API
    - 创建 /api/grading/homework GET接口
    - 实现按subject_id和时间范围查询zp_homework表
    - 返回status=3的批改记录列表
    - 解析homework_result JSON并计算题目数量
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ]* 2.2 编写属性测试：学科数据查询正确性
    - **Property 1: 学科数据查询正确性**
    - **Validates: Requirements 1.1, 2.2**

  - [x] 2.3 实现图片识别基准效果API
    - 创建 /api/grading/recognize POST接口
    - 调用Vision模型识别图片中的答案
    - 生成标准BaseEffect JSON格式
    - 处理识别失败情况
    - _Requirements: 3.1, 3.2_

  - [x] 2.4 实现DeepSeek评估对比API
    - 创建 /api/grading/evaluate POST接口
    - 调用DeepSeek进行基准效果与AI批改结果对比
    - 计算准确率、精确率、召回率、F1值
    - 分类错误类型（识别错误/判断错误/格式错误/其他错误）
    - 生成结构化评估报告
    - _Requirements: 5.1, 5.2, 5.3, 7.1, 7.2, 7.3_

  - [ ]* 2.5 编写属性测试：评估准确率计算正确性
    - **Property 7: 评估准确率计算正确性**
    - **Validates: Requirements 5.3, 6.1**

  - [ ]* 2.6 编写属性测试：错误分类完整性
    - **Property 8: 错误分类完整性**
    - **Validates: Requirements 7.3**

- [x] 3. Checkpoint - 确保所有后端测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. 前端页面开发
  - [x] 4.1 实现学科Tab组件
    - 创建4个学科Tab（英语、语文、数学、物理）
    - 实现Tab切换逻辑
    - 保持Tab状态
    - 应用Apple风格黑白简约设计
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ]* 4.2 编写属性测试：Tab切换状态保持
    - **Property 2: Tab切换状态保持**
    - **Validates: Requirements 2.2, 2.3**

  - [x] 4.3 实现批改数据列表组件
    - 展示从数据库获取的批改记录表格
    - 显示ID、学生ID、页码、创建时间、题目数量
    - 支持点击选择记录
    - 展示选中记录的详细JSON数据
    - 处理空状态和错误状态
    - _Requirements: 1.2, 1.3, 1.4, 1.5_

  - [x] 4.4 实现图片上传和识别功能
    - 创建图片上传区域（拖拽/点击上传）
    - 显示上传预览
    - 调用识别API获取基准效果
    - 处理识别失败情况
    - _Requirements: 3.1, 3.2, 3.4_

  - [x] 4.5 实现基准效果模块化编辑器
    - 以卡片形式展示每道题
    - 支持编辑answer、correct、userAnswer、mainAnswer字段
    - 支持添加新题目（自动分配index和tempIndex）
    - 支持删除题目（自动重排题号）
    - 实时同步数据
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 4.6 编写属性测试：基准效果编辑同步
    - **Property 3: 基准效果编辑同步**
    - **Validates: Requirements 3.3**

  - [ ]* 4.7 编写属性测试：题目卡片数量一致性
    - **Property 4: 题目卡片数量一致性**
    - **Validates: Requirements 4.1**

  - [ ]* 4.8 编写属性测试：题号自动分配正确性
    - **Property 5: 题号自动分配正确性**
    - **Validates: Requirements 4.3**

  - [ ]* 4.9 编写属性测试：题号重排正确性
    - **Property 6: 题号重排正确性**
    - **Validates: Requirements 4.4**

- [x] 5. Checkpoint - 确保前端基础功能测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. 评估功能和可视化开发
  - [x] 6.1 实现评估触发和结果展示
    - 创建"开始评估"按钮
    - 调用评估API
    - 显示加载状态
    - 处理评估错误
    - _Requirements: 5.1, 5.4_

  - [x] 6.2 实现统计卡片组件
    - 显示准确率、精确率、召回率、F1值
    - 显示正确数、错误数、总题数
    - 应用高亮样式
    - _Requirements: 6.1_

  - [x] 6.3 实现错误题目明细表格
    - 展示错误题目详情（题号、基准效果、AI结果、错误类型）
    - 支持点击高亮对比
    - _Requirements: 6.2, 6.3_

  - [x] 6.4 实现准确率折线图
    - 使用Chart.js绑制折线图
    - 展示批次准确率变化趋势
    - 支持缩放和导出
    - _Requirements: 6.4_

  - [x] 6.5 实现错误类型饼图
    - 展示识别错误/判断错误/格式错误/其他错误分布
    - 支持点击查看详情
    - _Requirements: 6.5_

  - [x] 6.6 实现评分偏差热力图
    - 展示题目×批次维度的偏差分布
    - 使用颜色深浅表示偏差程度
    - _Requirements: 6.6_

  - [x] 6.7 实现学科准确率柱状图
    - 展示多学科准确率对比
    - 支持切换维度
    - _Requirements: 6.7_

  - [x] 6.8 实现题目正确率条形图
    - 展示每题正确率排名
    - 高亮低正确率题目
    - _Requirements: 6.7_

  - [x] 6.9 实现多维能力雷达图
    - 展示准确率/精确率/召回率/F1值/一致性
    - 支持多记录对比
    - _Requirements: 6.8_

  - [x] 6.10 实现批改耗时箱线图
    - 展示响应时间分布
    - 标注异常值
    - _Requirements: 6.7_

  - [x] 6.11 实现错误趋势面积图
    - 展示错误数量随时间变化
    - 分类型堆叠显示
    - _Requirements: 6.7_

  - [x] 6.12 实现图表交互功能
    - 支持图表缩放
    - 支持导出PNG/SVG
    - 支持维度切换
    - _Requirements: 6.7_

- [x] 7. 历史记录功能
  - [x] 7.1 实现评估记录保存功能
    - 创建保存按钮
    - 将评估结果存储到localStorage
    - 生成唯一记录ID
    - _Requirements: 8.1, 8.2_

  - [ ]* 7.2 编写属性测试：评估记录保存round-trip
    - **Property 9: 评估记录保存round-trip**
    - **Validates: Requirements 8.2**

  - [x] 7.3 实现历史记录列表
    - 展示历史评估记录
    - 按学科和时间筛选
    - 支持查看详情
    - 支持删除记录
    - _Requirements: 8.3_

  - [ ]* 7.4 编写属性测试：历史记录筛选正确性
    - **Property 10: 历史记录筛选正确性**
    - **Validates: Requirements 8.3**

  - [x] 7.5 实现多记录对比功能
    - 支持选择多条记录


    - 在同一图表中对比展示
    - _Requirements: 6.8_

- [x] 8. Checkpoint - 确保所有功能测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. 页面样式和交互优化
  - [x] 9.1 应用Apple风格设计
    - 黑白简约配色
    - 圆角卡片设计
    - 平滑过渡动画
    - 响应式布局
    - _Requirements: 2.1_

  - [x] 9.2 实现加载状态和错误处理UI
    - 加载遮罩和spinner
    - 错误提示toast
    - 重试按钮
    - _Requirements: 1.4, 3.4, 5.4, 7.4_

  - [x] 9.3 实现图片预览功能
    - 点击放大预览
    - 固定预览面板
    - _Requirements: 3.1_

- [ ] 10. 清理和文档
  - [ ] 10.1 删除旧的compare页面相关代码
    - 删除templates/compare.html
    - 删除static/js/compare.js
    - 删除static/css/compare.css
    - 更新app.py中的路由
    - _Requirements: N/A_

  - [x] 10.2 更新导航链接
    - 将index.html中的"对比分析"链接改为"学科批改评估"
    - 更新链接地址为/subject-grading
    - _Requirements: 2.1_

- [ ] 11. Final Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.
