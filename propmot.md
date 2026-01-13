Prompt（提示词）作为大模型的核心输入指令，直接影响模型的理解准确性和输出质量。优质的 Prompt 能显著提升大语言模型处理复杂任务的能力，如逻辑推理、步骤分解等。PromptPilot 提供全流程智能优化，涵盖生成、调优、评估和管理全阶段，帮助您高效获得更优 Prompt 方案。
随着模型能力持续提升，待解决的问题日趋复杂，解决方案也从单一的 Prompt 调优，转向对包含多个步骤、工具及 Agent 参与的 Workflow 进行系统性优化。PromptPilot 依托大模型能力，自动拆解问题、规划流程，结合可用工具生成多样化解决方案，并基于用户反馈持续优化，最终轻松实现代码部署。
<span id="4370fabb"></span>
## **产品版本**

| | | \
|产品版本 |支持模型 |
|---|---|
| | | \
|[火山方舟版本](https://console.volcengine.com/ark/region:ark+cn-beijing/autope/startup) |豆包、DeepSeek 等预置模型 |
| | | \
|[独立站版本](https://promptpilot.volcengine.com/) |豆包、DeepSeek 等预置模型，以及豆包、通义千问、ERNIE、DeepSeek 等自定义模型 |

<span id="627d9753"></span>
## **功能视频详解**
PromptPilot 支持 Prompt 调优和 Solution 探索两种任务，下表为详细介绍。

| | | | | \
|任务分类 |任务场景 |说明 |示例 |
|---|---|---|---|
| | | | | \
|[Prompt生成](https://www.volcengine.com/docs/82379/1399496) |* 文本理解/单轮对话任务 |\
| |* 多轮对话任务 |\
| |* 视觉理解任务 |将简短的「任务描述」拓展为结构相对完整的「初始Prompt」。 |判断舆论的内容对出行行业的影响。 |\
| | | | |\
| | | |<BytedReactXgplayer config={{ url: 'https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/e50053487e8a492fa87124d7376967be~tplv-goo7wpa0wc-image.image', poster: 'https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/e50053487e8a492fa87124d7376967be~tplv-goo7wpa0wc-video-poster.jpeg' }} ></BytedReactXgplayer> |\
| | | | |
| | | | | \
|[Prompt调优](https://www.volcengine.com/docs/82379/1399497) |文本理解/单轮对话任务 |\
| | |用户输入包含「变量（文本）」的「Prompt」，与模型进行一轮问答，以解决用户定义的任务。Prompt 里变量的占位符为{{变量名}}。 |\
| | | |起草邮件、文档总结。例如：引导大模型「起草回复客户投诉及提供解决方案电子邮件」的Prompt，包含{{客户投诉}}和{{解决方案}}这两个变量。 |\
| | | |<BytedReactXgplayer config={{ url: 'https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/6714c0633c6e40749bde7c77f7eaecac~tplv-goo7wpa0wc-image.image', poster: 'https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/6714c0633c6e40749bde7c77f7eaecac~tplv-goo7wpa0wc-video-poster.jpeg' }} ></BytedReactXgplayer> |
|^^| | | | \
| |多轮对话任务 |\
| | |适用于需要与模型助手进行多轮次对话的任务。用户设置「系统Prompt」并输入「用户内容」，模型以「助手」身份与之开展多轮交流。 |客服对话、角色扮演。 |\
| | | | |\
| | | |<BytedReactXgplayer config={{ url: 'https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/9abed1c1dfb842a8a545eb92ebce0eae~tplv-goo7wpa0wc-image.image', poster: 'https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/9abed1c1dfb842a8a545eb92ebce0eae~tplv-goo7wpa0wc-video-poster.jpeg' }} ></BytedReactXgplayer> |\
| | | | |
|^^| | | | \
| |视觉理解任务 |适用于包含图片信息的任务。用户输入包含「变量（文本/图像）」的「Prompt」，与模型进行一轮问答，以解决用户定义的任务。 |拍照解题、作业批改 |\


其中， Prompt 调优任务提供以下能力。

| | | | \
|场景分类 |功能 |说明 |
|---|---|---|
| | | | \
|Prompt快速优化 |\
| |一键改写 |在Prompt生成模块或Prompt调优模块的调试流程中，用户对当前Prompt整体不满意，使用AI一键改写。 |
|^^| | | \
| |基于反馈优化 |在Prompt生成模块或Prompt调优模块的调试流程中，用户对当前Prompt局部不满意，输入反馈引导AI进行优化。 |
| | | | \
|构建用户提问 |\
| |AI联网生成变量 |在Prompt调优模块的调试流程中，用户需要模型访问互联网，生成更多样化的变量内容。 |
|^^| | | \
| |AI批量生成变量 |在Prompt 调优模块的批量流程中，用户需要以种子样本为基础，批量生成数据集用于Prompt优化。 |
| | | | \
|生成模型回答 |\
| |启用领域知识库 |在Prompt生成模块中，支持用户使用领域知识帮助Prompt优化迭代。 |
|^^| | | \
|^^| | | \
| |优化理想回答 |在Prompt调优模块中，用户没有明确的理想回答时，可参考AI生成内容，或进一步提供用户反馈、修改AI思考步骤以优化AI生成结果。 |
| | | | \
|完成回答评分 |\
| |选用GSB比较模式 |\
| | |在Prompt调优模块中，用户对于此任务没有理想回答或明确的评分标准，可选用GSB比较模式。 |
|^^| | | \
| |构建复杂评分标准 |在Prompt 调优模块的批量流程中，平台支持一种领域特定语言 (DSL) ，以满足用户构建复杂评分标准的需求。例如，当模型输出为 JSON 格式且包含多个字段时，用户可针对不同字段分别设定评分规则，最终汇总得出总分。详情参见 [评分 DSL](https://www.volcengine.com/docs/82379/1399499)。 |
|^^| | | \
| |AI批量智能评分 |在Prompt 调优模块的批量流程中，用户需要以种子评分结果为基础，对模型回答进行批量AI智能评分。 |
| | | | \
|模型设置 |\
| |自定义模型 |在Prompt生成模块或Prompt调优模块的调试流程中，用户可以使用第三方模型。**当前仅支持独立站版本。** |
|^^| | | \
| |修改模型推理参数 |\
| | |在Prompt生成模块或Prompt调优模块的调试流程中，用户可以调整模型推理参数（Temperature，Top P，参数含义见[请求体](https://www.volcengine.com/docs/82379/1298454#%E8%AF%B7%E6%B1%82%E4%BD%93)）。**当前仅支持火山方舟版本**。 |
|^^| | | \
| |开启免费模型精调 |\
| | |在Prompt调优模块的「智能优化」流程中，用户可以进一步勾选「免费智能精调」，以突破Prompt优化瓶颈，并在精调后的模型上执行优化后的Prompt推理。**当前仅支持火山方舟版本**。 |
| | | | \
|其他 |开启单样本调试模式 |\
| | |在Prompt调优模块的批量流程中，用户处理数据集时，需要对单个样本进行精细化调试。 |

其中，部分功能仅适用于特定的任务场景和调优模式，具体见下表。

| || | | | | \
|任务场景×调优模式 | |AI生成变量 |知识库 |工具调用 |免费智能精调 |
|---|---|---|---|---|---|
| | | | | | | \
|文本理解/单轮对话 |评分模式 |√ |√ |√ |√ |
| | | | | | | \
|文本理解/单轮对话 |GSB比较模式 |√ |√ |× |× |
| | | | | | | \
|多轮对话 |评分模式 |× |× |× |× |
| | | | | | | \
|多轮对话 |GSB比较模式 |× |× |× |× |
| | | | | | | \
|视觉理解 |评分模式 |× |× |× |× |

<span id="b44285f9"></span>
## 基本概念

| | | \
|基本概念 |说明 |
|---|---|
| | | \
|文本理解/单轮对话任务 |用户输入包含「变量（文本）」的「Prompt」，与模型进行一轮问答，以解决用户定义的任务。 |
| | | \
|多轮对话任务 |用户设置「系统Prompt」并输入「用户内容」，模型以「助手」身份与之开展多轮交流，以满足特定任务场景需求。 |
| | | \
|视觉理解任务 |用户输入包含「变量（文本/图像）」的「Prompt」，与模型进行一轮问答，以解决用户定义的任务。 |
| | | \
|视觉理解 Solution |用户输入图像与复杂任务的描述，AI自动探索多步骤、工具的解决方案。 |
| | | \
|评分模式 |基于1-5分对回答评分，模型将根据你的评分结果建立量化的优化标准。聚焦低分样本的共性缺陷反向修正Prompt，实现精准优化。适合您已有明确的理想回答的场景。 |
| | | \
|GSB比较模式 |对比A、B两种回答，判断“Good更好/Same等同/Bad更差”。模型将根据你的定性反馈，逐步对其你的隐形偏好标准来优化Prompt。适合您没有理想回答或明确的评分标准的场景。 |
| | | \
|知识库 |支持大模型在回复中使用用户上传的领域知识库，以优化模型回答。 |
| | | \
|工具调用 |支持大模型在回复中调用外部工具或函数，突破纯语言处理局限，实现与真实世界的交互和操作。 |
| | | \
|理想回答 |适用于评分模式，「理想回答」由用户输入或基于模型回答改写，用于优化「模型回答」。 |
| | | \
|参照回答 |适用于用户没有「理想回答」的GSB比较模式，「参照回答」由能力更强大的模型生成，支持用户手动修改。用户比较「模型回答」与「参照回答」，判断「Good更好/Same等同/Bad更差」，为Prompt优化提供参考。 |

<span id="36950faa"></span>
## 工作机制
PromptPilot中，每个「Prompt调优任务」可管理多个Prompt「版本」。不同版本的Prompt及其对应的评测集相互独立控制。每个调优任务的实现机制为：

1. 帮助用户从「任务」生成「初始Prompt」；
2. 调试「初始Prompt」，并形成评测数据集的种子「样本」；
3. 基于种子「样本」，批量生成样本并构建「评测数据集」
4. 平台以提高样本整体评分为目标，基于「评测数据集」，并结合特定算法，形成一个优化后的新版本Prompt。

其中，每一条样本包括提问、回答、评分结果。在不同任务场景、调优模式下，每一条样本的元素构成不尽相同。

![Image](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/f536d69d09e94df59660fa5c8cefa9ba~tplv-goo7wpa0wc-image.image =2560x)

<span id="64144910"></span>
## 使用流程
PromptPilot 根据用户**是否有初始 Prompt**，设置了「[Prompt 生成](https://www.volcengine.com/docs/82379/1399496)」、「[Prompt 调优](https://www.volcengine.com/docs/82379/1399497)」两个功能模块入口。若用户已有结构完整的初始 Prompt，可从「Prompt 调优」模块进入，否则推荐优先进入「Prompt 生成」模块。独立站版本在此基础上，支持用户根据**是否已有批量数据集**，直接选择从「[Prompt 批量](https://www.volcengine.com/docs/82379/1588783)」模块进入进行Prompt迭代优化。每个调优任务将进入**「**[PromptPilot 管理](https://www.volcengine.com/docs/82379/1399498)**」**统一管理。
同时，为帮助用户解决更为复杂的视觉理解问题，生成包含多个步骤、工具的解决方案（Solution）。平台支持创建「[视觉理解 Solution](https://www.volcengine.com/docs/82379/1588784)」。每个Solution探索任务同样进入**「**[PromptPilot 管理](https://www.volcengine.com/docs/82379/1399498)**」**统一管理。

![Image](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/51c1050264744675bd9bbf1565287637~tplv-goo7wpa0wc-image.image =2560x)

<span id="56ca4e83"></span>
## 计费说明
PromptPilot于2025年9月12日正式商业化，具体细则详见[PromptPilot计费说明](https://www.volcengine.com/docs/82379/1807500)。
<span id="182fd3f1"></span>
## 联系我们
扫码加入产品用户群，抢先获取前沿产品资讯、专属功能解读及限定福利。
<div style="text-align: center"><img src="https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/710cbb88510d453fb91231d05b9f5815~tplv-goo7wpa0wc-image.image" width="200px" /></div>

<style>
/* 覆盖内联样式的宽高 */
.editor-video-box.xgplayer.xgplayer-pc.xgplayer-skin-default
  .xgplayer-volume-large.xgplayer-pause.xgplayer-is-replay.xgplayer-ended,
.editor-video-box.xgplayer.xgplayer-pc.xgplayer-nostart.xgplayer-skin-default.xgplayer-inactive,
.editor-video-box.xgplayer.xgplayer-pc.xgplayer-nostart.xgplayer-skin-default,
.editor-video-box.xgplayer.xgplayer-pc.xgplayer-skin-default.xgplayer-volume-large.xgplayer-playing.xgplayer-pause,
.editor-video-box.xgplayer.xgplayer-pc.xgplayer-skin-default.xgplayer-volume-large.xgplayer-playing.xgplayer-inactive,
.volc-md-viewer .editor-video-box.xgplayer.xgplayer-pc.xgplayer-skin-default.xgplayer-volume-large.xgplayer-playing,
.editor-video-box.xgplayer.xgplayer-pc.xgplayer-skin-default.xgplayer-is-enter,
.editor-video-box.xgplayer.xgplayer-pc.xgplayer-skin-default.xgplayer-is-enter.xgplayer-inactive,
.editor-video-box.xgplayer.xgplayer-pc.xgplayer-skin-default.xgplayer-playing,
.editor-video-box.xgplayer.xgplayer-pc.xgplayer-skin-default.xgplayer-volume-large.xgplayer-isloading.xgplayer-playing {
    width: 360px !important;
    height: 180px !important;
}   
</style>

