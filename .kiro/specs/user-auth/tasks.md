# Implementation Plan

- [x] 1. 数据库表结构更新




  - [ ] 1.1 创建 users 表
    - 创建用户表，包含 id, username, password_hash, api_keys, remember_token, token_expires_at 等字段


    - 更新 database_schema.sql 文件
    - _Requirements: 1.1, 5.1_
  - [ ] 1.2 更新现有表添加 user_id 字段
    - 为 chat_sessions 表添加 user_id 字段




    - 为 prompt_templates 表添加 user_id 字段
    - 为 knowledge_tasks 表添加 user_id 字段
    - 为 model_stats 表添加 user_id 字段
    - _Requirements: 4.4, 9.3, 11.1, 12.1_

- [ ] 2. 后端认证服务实现
  - [ ] 2.1 创建 AuthService 认证服务
    - 创建 services/auth_service.py
    - 实现 hash_password 和 verify_password 方法（使用 werkzeug.security）
    - 实现 login_or_register 方法（自动注册逻辑）
    - 实现 create_remember_token 和 verify_remember_token 方法
    - 实现 invalidate_remember_token 方法
    - 实现 get_user_api_keys 和 save_user_api_keys 方法
    - _Requirements: 1.1, 1.2, 1.3, 5.1, 5.2, 7.1, 7.4, 8.1, 8.2, 8.3, 8.4_
  - [ ]* 2.2 编写属性测试：自动注册创建有效用户
    - **Property 1: Auto-registration creates valid user**
    - **Validates: Requirements 1.1**
  - [x]* 2.3 编写属性测试：正确密码登录成功




    - **Property 2: Login with correct password succeeds**
    - **Validates: Requirements 1.2**
  - [ ]* 2.4 编写属性测试：错误密码登录失败
    - **Property 3: Login with wrong password fails**
    - **Validates: Requirements 1.3**


  - [ ]* 2.5 编写属性测试：密码不以明文存储
    - **Property 7: Password is never stored in plaintext**
    - **Validates: Requirements 5.1**

- [ ] 3. 认证路由和中间件
  - [ ] 3.1 创建认证路由
    - 创建 routes/auth.py
    - 实现 POST /api/auth/login 登录/自动注册接口
    - 实现 POST /api/auth/logout 登出接口

    - 实现 GET /api/auth/status 获取登录状态接口
    - 实现 GET/POST /api/auth/api-keys API密钥管理接口




    - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.1, 7.1, 7.2, 7.4_
  - [ ] 3.2 实现认证装饰器
    - 创建 login_required 装饰器
    - 创建 get_current_user 辅助函数
    - 在 app.py 中配置 Flask Session
    - _Requirements: 6.1, 6.2, 6.3_
  - [ ]* 3.3 编写属性测试：登出销毁会话
    - **Property 4: Logout destroys session**
    - **Validates: Requirements 3.1**




  - [ ]* 3.4 编写属性测试：未认证请求返回401
    - **Property 6: Unauthenticated requests return 401**
    - **Validates: Requirements 6.1**

- [ ] 4. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.



- [ ] 5. 记住登录功能
  - [ ] 5.1 实现记住登录Token机制
    - 在登录时根据 remember_me 参数创建持久化Token




    - 设置 HttpOnly Cookie 存储Token
    - 实现自动恢复会话逻辑
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [ ]* 5.2 编写属性测试：记住Token恢复会话
    - **Property 8: Remember token enables session restoration**
    - **Validates: Requirements 8.2**

  - [ ]* 5.3 编写属性测试：登出使Token失效
    - **Property 9: Logout invalidates remember token**




    - **Validates: Requirements 8.4**

- [x] 6. 更新现有服务支持用户隔离


  - [ ] 6.1 更新 SessionService 支持用户关联
    - 修改 save_chat_session 方法，添加 user_id 参数


    - 修改 get_chat_sessions 方法，按 user_id 过滤
    - 更新 AppDatabaseService 相关方法
    - _Requirements: 4.1, 4.2, 4.4_

  - [x]* 6.2 编写属性测试：聊天记录用户隔离

    - **Property 5: Chat records are user-isolated**
    - **Validates: Requirements 4.2**
  - [ ] 6.3 更新知识点任务服务支持用户关联
    - 修改 knowledge_agent 模块，添加 user_id 支持

    - _Requirements: 12.1, 12.2_
  - [ ]* 6.4 编写属性测试：知识点任务用户隔离
    - **Property 13: Knowledge tasks are user-isolated**

    - **Validates: Requirements 12.2**

- [x] 7. API密钥管理

  - [ ] 7.1 实现用户API密钥存储和加载
    - 修改设置保存逻辑，将API密钥存储到用户账号
    - 登录时自动加载用户的API密钥配置
    - 更新 LLMService 使用用户配置的API密钥

    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 7.2 编写属性测试：API密钥用户关联
    - **Property 10: API keys are user-specific**
    - **Validates: Requirements 7.1, 7.2**



- [ ] 8. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. 前端登录弹窗实现
  - [ ] 9.1 创建登录弹窗HTML结构
    - 在 index.html 中添加登录弹窗 Modal

    - 包含用户名、密码输入框和记住登录复选框
    - 深色主题样式，圆角设计
    - _Requirements: 13.1, 13.3_
  - [x] 9.2 添加登录弹窗CSS样式

    - 在 index.css 中添加登录弹窗样式
    - 居中显示、平滑动画、现代化输入框
    - _Requirements: 13.3_
  - [ ] 9.3 实现登录弹窗JavaScript逻辑
    - 在 index.js 中添加登录弹窗控制逻辑
    - 实现打开/关闭弹窗、表单提交、错误显示
    - 点击外部或ESC关闭弹窗
    - _Requirements: 13.1, 13.2, 13.4_

- [ ] 10. 前端头像按钮实现
  - [ ] 10.1 添加头像按钮到顶部栏
    - 在 index.html 顶部栏右侧添加头像按钮
    - 未登录显示默认头像图标
    - 已登录显示用户名首字母
    - _Requirements: 2.1, 2.3_
  - [ ] 10.2 实现头像下拉菜单
    - 添加下拉菜单HTML结构
    - 显示用户名和登出选项
    - _Requirements: 2.4, 3.1_
  - [ ] 10.3 添加头像按钮CSS样式
    - 现代化圆形头像样式
    - 下拉菜单样式
    - _Requirements: 2.1, 2.3_
  - [ ] 10.4 实现头像按钮JavaScript逻辑
    - 点击打开登录弹窗或下拉菜单
    - 登录状态检查和UI更新
    - 登出功能
    - _Requirements: 2.2, 2.4, 3.1, 3.2_

- [ ] 11. 其他页面认证集成
  - [ ] 11.1 更新其他页面添加登录状态检查
    - 在 compare.html, subject-grading.html 等页面添加登录检查
    - 添加头像按钮到所有页面
    - _Requirements: 4.3, 6.1_

- [ ] 12. 提示词模板用户关联
  - [ ] 12.1 更新提示词模板服务支持用户关联
    - 修改 prompt_templates 相关方法，添加 user_id 支持
    - 系统模板对所有用户可见，用户模板仅创建者可见
    - _Requirements: 11.1, 11.2, 11.3_
  - [ ]* 12.2 编写属性测试：提示词模板所有权验证
    - **Property 12: Prompt templates respect ownership**
    - **Validates: Requirements 11.3**

- [ ] 13. 数据集公有化验证
  - [ ]* 13.1 编写属性测试：数据集跨用户共享
    - **Property 11: Datasets are shared across users**
    - **Validates: Requirements 10.1, 10.2, 10.3**

- [ ] 14. Final Checkpoint - 确保所有测试通过

  - Ensure all tests pass, ask the user if questions arise.

