# 需求文档：作业图片预处理工具

## 简介

作业图片预处理工具是 AI 批改效果分析平台的独立功能页面，旨在通过 OpenCV 图像处理技术对作业图片进行预处理（去噪、增强对比度、倾斜矫正、二值化等），以提高豆包视觉 LLM 对手写作业的识别准确率。用户可上传作业图片，选择处理步骤，预览处理前后对比效果，并直接调用 LLM 视觉模型进行识别测试对比。

## 术语表

- **Image_Preprocess_Service**: 后端图片预处理服务，封装 OpenCV 图像处理流水线
- **Processing_Pipeline**: 图片处理流水线，由多个可配置的处理步骤组成
- **Processing_Step**: 单个图像处理步骤（如灰度转换、去噪、对比度增强等）
- **CLAHE**: 自适应直方图均衡化（Contrast Limited Adaptive Histogram Equalization），用于增强图像对比度
- **LLM_Vision_Service**: 豆包视觉大模型服务，通过 LLMService.call_vision_model() 调用
- **Preview_Panel**: 前端对比预览面板，展示处理前后的图片效果
- **Super_Resolution_Module**: OpenCV DNN 超分辨率模块，使用预训练模型（EDSR）对低分辨率图片进行智能高清放大

## 需求

### 需求 1：图片上传

**用户故事：** 作为测试人员，我希望上传作业图片，以便对图片进行预处理和识别测试。

#### 验收标准

1. WHEN 用户选择一张 JPG 或 PNG 格式的图片文件，THE Image_Preprocess_Service SHALL 接受该文件并返回上传成功状态
2. WHEN 用户上传的文件格式不是 JPG 或 PNG，THE Image_Preprocess_Service SHALL 拒绝该文件并返回明确的格式错误提示
3. WHEN 用户上传的文件大小超过 10MB，THE Image_Preprocess_Service SHALL 拒绝该文件并返回文件过大的错误提示
4. WHEN 图片上传成功，THE Preview_Panel SHALL 在左侧显示原始图片预览

### 需求 2：图片处理流水线

**用户故事：** 作为测试人员，我希望对上传的作业图片执行多种预处理操作，以便提高 LLM 视觉识别的准确率。

#### 验收标准

1. THE Processing_Pipeline SHALL 支持以下处理步骤：灰度转换、去噪（高斯模糊）、对比度增强（CLAHE）、倾斜矫正、自适应二值化、边缘裁剪、智能高清化（超分辨率放大）
2. WHEN 用户提交处理请求且所有步骤均启用，THE Processing_Pipeline SHALL 按照固定顺序依次执行：智能高清化 → 灰度转换 → 去噪 → 对比度增强 → 倾斜矫正 → 二值化 → 边缘裁剪
3. WHEN 处理流水线执行完成，THE Image_Preprocess_Service SHALL 返回最终处理后的图片数据以及每个已执行步骤的中间结果图片（均为 base64 编码）
4. WHEN 处理流水线中任一步骤执行失败，THE Image_Preprocess_Service SHALL 跳过该步骤并继续执行后续步骤，同时在响应中标注失败步骤的警告信息

### 需求 3：处理步骤可配置

**用户故事：** 作为测试人员，我希望选择性地启用或禁用各处理步骤，以便找到最佳的预处理组合。

#### 验收标准

1. THE Preview_Panel SHALL 为每个处理步骤提供独立的开关控件
2. WHEN 用户禁用某个处理步骤，THE Processing_Pipeline SHALL 跳过该步骤并继续执行其余已启用的步骤
3. WHEN 用户修改步骤配置后点击处理按钮，THE Image_Preprocess_Service SHALL 仅执行已启用的步骤并返回处理结果

### 需求 8：处理参数自定义

**用户故事：** 作为测试人员，我希望自定义每个处理步骤的参数（如去噪强度、CLAHE 参数、二值化阈值等），以便精细调优预处理效果。

#### 验收标准

1. THE Preview_Panel SHALL 为每个处理步骤提供参数调节控件（滑块或数值输入框）
2. WHEN 用户调整去噪步骤参数，THE Preview_Panel SHALL 允许设置高斯模糊核大小（范围 3-15，奇数，默认 5）
3. WHEN 用户调整对比度增强参数，THE Preview_Panel SHALL 允许设置 CLAHE 的 clipLimit（范围 1.0-10.0，默认 2.0）和 tileGridSize（范围 2-16，默认 8）
4. WHEN 用户调整二值化参数，THE Preview_Panel SHALL 允许设置自适应阈值的 blockSize（范围 3-99，奇数，默认 11）和常数 C（范围 0-20，默认 2）
5. WHEN 用户提交处理请求，THE Image_Preprocess_Service SHALL 使用用户指定的参数值执行对应的处理步骤
6. IF 用户提交的参数值超出有效范围，THEN THE Image_Preprocess_Service SHALL 将参数修正为最近的有效值并在响应中标注修正信息

### 需求 4：处理前后对比预览

**用户故事：** 作为测试人员，我希望直观地对比处理前后的图片效果，以便评估预处理的改善程度。

#### 验收标准

1. WHEN 图片处理完成，THE Preview_Panel SHALL 以左右并排方式同时展示原始图片和处理后图片
2. WHEN 用户查看对比预览，THE Preview_Panel SHALL 在图片上方分别标注"原始图片"和"处理后图片"标签
3. WHEN 处理流水线执行完成，THE Image_Preprocess_Service SHALL 返回每个已启用步骤的中间结果图片（base64 编码）
4. WHEN 用户点击某个处理步骤名称，THE Preview_Panel SHALL 在右侧展示该步骤执行后的中间结果图片，方便逐步查看每一步的效果变化
5. THE Preview_Panel SHALL 提供步骤缩略图列表，展示每个已执行步骤的缩略预览，用户可点击切换查看

### 需求 5：LLM 视觉识别测试

**用户故事：** 作为测试人员，我希望对原始图片和处理后图片分别调用 LLM 视觉模型进行识别，以便量化预处理对识别准确率的提升效果。

#### 验收标准

1. WHEN 用户点击"识别测试"按钮，THE LLM_Vision_Service SHALL 分别对原始图片和处理后图片调用豆包视觉模型进行识别
2. WHEN 两次识别均完成，THE Preview_Panel SHALL 并排展示原始图片识别结果和处理后图片识别结果
3. WHILE LLM 视觉模型正在识别中，THE Preview_Panel SHALL 显示加载状态指示器，告知用户识别正在进行
4. IF LLM 视觉模型调用失败，THEN THE Preview_Panel SHALL 显示具体的错误信息并允许用户重试

### 需求 6：页面路由与导航

**用户故事：** 作为测试人员，我希望通过侧边栏导航访问图片预处理工具页面，以便快速使用该功能。

#### 验收标准

1. THE Image_Preprocess_Service SHALL 在 `/image-preprocess` 路由下提供独立页面
2. THE Preview_Panel SHALL 在平台侧边栏工具区域添加"图片预处理"导航链接
3. WHEN 用户点击侧边栏中的"图片预处理"链接，THE Preview_Panel SHALL 导航到 `/image-preprocess` 页面

### 需求 7：图片处理步骤的幂等性

**用户故事：** 作为测试人员，我希望对同一张图片多次执行相同的处理配置能得到一致的结果，以便可靠地对比不同配置的效果。

#### 验收标准

1. WHEN 用户对同一张图片使用相同的步骤配置多次执行处理，THE Processing_Pipeline SHALL 每次返回相同的处理结果

### 需求 9：智能高清化处理

**用户故事：** 作为测试人员，我希望对低分辨率或模糊的作业图片进行智能高清化放大，以便提升手写文字的清晰度和 LLM 识别准确率。

#### 验收标准

1. WHEN 用户启用智能高清化步骤，THE Super_Resolution_Module SHALL 使用 OpenCV DNN 超分辨率模块（EDSR 模型）对图片进行 2 倍放大
2. WHEN 智能高清化执行完成，THE Processing_Pipeline SHALL 对放大后的图片应用锐化处理（Unsharp Mask）以增强文字边缘清晰度
3. IF 超分辨率模型文件不存在或加载失败，THEN THE Image_Preprocess_Service SHALL 回退到 OpenCV 双三次插值（INTER_CUBIC）进行 2 倍放大，并在响应中标注回退警告
4. WHEN 用户调整智能高清化参数，THE Preview_Panel SHALL 允许设置放大倍数（2x 或 4x，默认 2x）和锐化强度（范围 0.0-2.0，默认 0.5）
