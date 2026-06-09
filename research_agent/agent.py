"""
AI调研员 - 核心Agent引擎

协调整个调研流程：
1. 需求解析 → 生成调研提纲和数据采集计划
2. 数据采集 → 联网搜索 + API + 用户上传文件解析
3. 数据清洗 → 去重、过滤、校验、冲突检测
4. 智能分析 → 自动匹配分析模型生成洞察
5. 报告生成 → 标准化调研报告输出
6. 迭代优化 → 基于用户反馈修改报告

依赖：
- ModelService: LLM调用
- SearchService: 联网搜索
- DataCleanService: 数据清洗
- ReportService: 报告生成
- StorageService: 任务存储
"""

import re
import json
import uuid
import time
from typing import List, Dict, Any, Optional, Callable, Generator
from datetime import datetime

from .models import (
    ResearchTask, TaskStatus, ResearchOutline, OutlineItem,
    CollectedData, DataSource, DataSourceType, CredibilityLevel,
    AnalysisResult, AnalysisModelType, ResearchReport, ReportFormat,
    TaskProgress
)
from .services import (
    ModelService, SearchService, DataCleanService,
    FileParseService, ReportService, StorageService
)
from .prompts import (
    SYSTEM_PROMPT, PARSE_REQUIREMENT_PROMPT, SEARCH_QUERY_PROMPT,
    DATA_CLEANING_PROMPT, ANALYSIS_PROMPT, ANALYSIS_MODEL_PROMPTS,
    REPORT_GENERATION_PROMPT, ITERATION_PROMPT, USER_DATA_ANALYSIS_PROMPT
)
from .analysis_models import recommend_models, prepare_analysis_data, MODEL_INFO


def _extract_json(text: str) -> Any:
    """从LLM响应中安全提取JSON"""
    # 尝试直接解析
    text = text.strip()
    if text.startswith('```'):
        # 移除代码块标记
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 尝试提取JSON对象
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # 尝试提取JSON数组
    json_match = re.search(r'\[[\s\S]*\]', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    raise ValueError(f"无法从响应中提取JSON")


class ResearchAgent:
    """
    AI调研员核心引擎
    
    用法示例：
        agent = ResearchAgent()
        task = agent.create_task("2026年国内AI教育市场调研")
        
        # 步骤1：解析需求
        outline = agent.parse_requirement(task)
        
        # 步骤2：采集数据
        data = agent.collect_data(task)
        
        # 步骤3：清洗数据
        cleaned = agent.clean_data(task)
        
        # 步骤4：智能分析
        analysis = agent.run_analysis(task, ["swot", "pest"])
        
        # 步骤5：生成报告
        report = agent.generate_report(task)
        
        # 步骤6：迭代优化
        agent.iterate_report(task, "请补充政策分析部分")
    """
    
    def __init__(self, config_path: str = "config.json", llm_model: str = "deepseek-v3.2", user_id: int = None):
        """
        初始化AI调研员
        
        Args:
            config_path: 配置文件路径
            llm_model: 默认使用的LLM模型
            user_id: 用户ID（用于从数据库获取API密钥）
        """
        self.user_id = user_id
        self.model_service = ModelService(config_path, user_id=user_id)
        self.search_service = SearchService()
        self.data_clean_service = DataCleanService()
        self.file_parse_service = FileParseService()
        self.report_service = ReportService()
        self.storage_service = StorageService()
        
        self.llm_model = llm_model
        self.progress_callback: Optional[Callable[[TaskProgress], None]] = None
    
    def set_progress_callback(self, callback: Callable[[TaskProgress], None]):
        """设置进度回调"""
        self.progress_callback = callback
    
    def _emit_progress(self, task_id: str, step: int, total: int, status: str, message: str):
        """发送进度更新"""
        if self.progress_callback:
            progress = TaskProgress(
                task_id=task_id,
                current_step=step,
                total_steps=total,
                status=status,
                message=message,
                progress_percent=(step / total * 100) if total > 0 else 0
            )
            self.progress_callback(progress)
    
    # ============ 步骤1：创建任务 & 解析需求 ============
    
    def create_task(self, query: str, industry: str = "", scope: str = "") -> ResearchTask:
        """
        创建调研任务
        
        Args:
            query: 用户输入的调研需求（自然语言）
            industry: 调研行业（可选，可自动识别）
            scope: 调研范围（可选）
            
        Returns:
            ResearchTask 对象
        """
        task = ResearchTask(
            query=query,
            industry=industry,
            scope=scope,
            llm_model=self.llm_model
        )
        self.storage_service.save_task(task)
        return task
    
    def parse_requirement(self, task: ResearchTask) -> ResearchOutline:
        """
        解析调研需求，生成结构化提纲和采集计划
        
        Args:
            task: 调研任务
            
        Returns:
            调研提纲
        """
        task.status = TaskStatus.PARSING
        self._emit_progress(task.task_id, 1, 6, "parsing", "正在解析调研需求，生成调研提纲...")
        
        # 构建行业上下文
        industry_context = ""
        if task.industry:
            industry_context = f"【行业领域】{task.industry}"
        if task.scope:
            industry_context += f"\n【调研范围】{task.scope}"
        
        # 调用LLM解析需求
        prompt = PARSE_REQUIREMENT_PROMPT.format(
            query=task.query,
            industry_context=industry_context
        )
        
        response_text, usage = self.model_service.call_llm(
            self.llm_model, SYSTEM_PROMPT, prompt,
            temperature=0.3, max_tokens=4096
        )
        
        task.total_tokens_used += usage.get("total_tokens", 0)
        
        # 解析LLM响应
        try:
            result = _extract_json(response_text)
        except ValueError:
            # 解析失败时创建基础提纲
            result = {
                "title": f"{task.query} - 行业调研报告",
                "objective": task.query,
                "scope": task.scope or "国内市场",
                "methodology": "桌面研究 + 公开数据分析",
                "items": [
                    {"title": "行业概览", "description": "行业基本情况", "data_requirements": ["行业定义", "发展历程"], "data_sources": ["公开报告"]},
                    {"title": "市场分析", "description": "市场规模与趋势", "data_requirements": ["市场规模", "增长率"], "data_sources": ["统计数据"]},
                    {"title": "竞争格局", "description": "主要玩家与竞争态势", "data_requirements": ["头部企业", "市场份额"], "data_sources": ["企业财报"]},
                    {"title": "发展趋势", "description": "未来发展方向", "data_requirements": ["技术趋势", "政策方向"], "data_sources": ["行业报告"]},
                ],
                "collection_plan": [],
                "recommended_models": ["swot", "pest", "market_size"]
            }
        
        # 构建调研提纲对象
        outline = ResearchOutline(
            title=result.get("title", task.query),
            objective=result.get("objective", task.query),
            scope=result.get("scope", ""),
            methodology=result.get("methodology", ""),
            items=[OutlineItem.from_dict(item) for item in result.get("items", [])],
            collection_plan=result.get("collection_plan", [])
        )
        
        # 自动识别行业（如果未指定）
        if not task.industry:
            task.industry = result.get("title", "").split("行业")[0] if "行业" in result.get("title", "") else ""
        
        task.outline = outline
        self.storage_service.save_task(task)
        
        self._emit_progress(task.task_id, 1, 6, "parsed", 
                           f"调研提纲已生成：{len(outline.items)}个章节，{len(outline.collection_plan)}项采集计划")
        
        return outline
    
    # ============ 步骤2：数据采集 ============
    
    def collect_data(self, task: ResearchTask, max_queries: int = 15) -> List[CollectedData]:
        """
        执行数据采集（联网搜索 + 页面内容抓取）
        
        Args:
            task: 调研任务
            max_queries: 最大搜索查询数
            
        Returns:
            采集到的数据列表
        """
        if not task.outline:
            raise ValueError("请先执行parse_requirement生成调研提纲")
        
        task.status = TaskStatus.COLLECTING
        self._emit_progress(task.task_id, 2, 6, "collecting", "正在生成搜索关键词...")
        
        # 1. 生成搜索关键词
        search_queries = self._generate_search_queries(task)
        
        # 2. 执行搜索
        all_collected = []
        total_queries = min(len(search_queries), max_queries)
        
        for i, sq in enumerate(search_queries[:max_queries]):
            dimension = sq.get("dimension", "")
            queries = sq.get("queries", [])
            
            self._emit_progress(
                task.task_id, 2, 6, "collecting",
                f"正在搜索: {dimension} ({i + 1}/{total_queries})"
            )
            
            for query in queries:
                try:
                    results = self.search_service.search(query, max_results=5)
                    
                    for result in results:
                        # 尝试抓取页面内容
                        page_content = ""
                        if result.get("url"):
                            page_content = self.search_service.fetch_page_content(
                                result["url"], max_length=3000
                            )
                        
                        content = result.get("snippet", "")
                        if page_content and not page_content.startswith("["):
                            content = page_content[:3000]
                        
                        collected = CollectedData(
                            title=result.get("title", ""),
                            content=content,
                            source=DataSource(
                                source_type=DataSourceType.WEB_SEARCH,
                                name=result.get("title", ""),
                                url=result.get("url", ""),
                                publisher="",
                                credibility=DataCleanService.assess_credibility(
                                    result.get("title", ""), result.get("url", "")
                                )
                            ),
                            tags=[dimension] if dimension else []
                        )
                        all_collected.append(collected)
                        
                except Exception as e:
                    print(f"[ResearchAgent] 搜索失败 '{query}': {e}")
                    continue
                
                # 控制请求频率，避免被封
                time.sleep(0.5)
        
        task.collected_data = all_collected
        self.storage_service.save_task(task)
        
        self._emit_progress(task.task_id, 2, 6, "collected",
                           f"数据采集完成：共采集 {len(all_collected)} 条数据")
        
        return all_collected
    
    def _generate_search_queries(self, task: ResearchTask) -> List[Dict]:
        """使用LLM生成搜索关键词"""
        if not task.outline:
            return []
        
        # 收集所有数据维度
        dimensions = []
        for item in task.outline.items:
            for req in item.data_requirements:
                dimensions.append(f"- {item.title}: {req}")
            for sub in item.sub_items:
                for req in sub.data_requirements:
                    dimensions.append(f"- {sub.title}: {req}")
        
        prompt = SEARCH_QUERY_PROMPT.format(
            title=task.outline.title,
            objective=task.outline.objective,
            scope=task.outline.scope,
            dimensions="\n".join(dimensions)
        )
        
        try:
            response_text, usage = self.model_service.call_llm(
                self.llm_model, SYSTEM_PROMPT, prompt,
                temperature=0.2, max_tokens=2048
            )
            task.total_tokens_used += usage.get("total_tokens", 0)
            
            result = _extract_json(response_text)
            return result.get("search_queries", [])
        except Exception as e:
            print(f"[ResearchAgent] 生成搜索关键词失败: {e}")
            # 回退：使用提纲标题作为搜索词
            return [
                {"dimension": item.title, "queries": [f"{task.outline.title} {item.title}"]}
                for item in task.outline.items
            ]
    
    def add_uploaded_data(self, task: ResearchTask, filepath: str, filename: str) -> List[CollectedData]:
        """
        处理用户上传的文件，提取数据并加入任务
        
        Args:
            task: 调研任务
            filepath: 文件路径
            filename: 原始文件名
            
        Returns:
            提取的数据列表
        """
        # 解析文件内容
        file_content = self.file_parse_service.parse_file(filepath)
        
        if file_content.startswith("["):
            # 解析失败
            return []
        
        # 使用LLM分析文件内容，提取与调研相关的数据
        title = task.outline.title if task.outline else task.query
        prompt = USER_DATA_ANALYSIS_PROMPT.format(
            title=title,
            file_content=file_content[:8000]
        )
        
        try:
            response_text, usage = self.model_service.call_llm(
                self.llm_model, SYSTEM_PROMPT, prompt,
                temperature=0.2, max_tokens=4096
            )
            task.total_tokens_used += usage.get("total_tokens", 0)
            
            result = _extract_json(response_text)
            extracted = result.get("extracted_data", [])
            
            collected_list = []
            for item in extracted:
                source_data = item.get("source", {})
                collected = CollectedData(
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    source=DataSource(
                        source_type=DataSourceType.USER_UPLOAD,
                        name=f"用户上传: {filename}",
                        publisher=source_data.get("publisher", "用户提供"),
                        credibility=CredibilityLevel.MEDIUM
                    ),
                    tags=item.get("tags", []),
                    is_verified=True
                )
                collected_list.append(collected)
            
            # 记录上传文件
            task.uploaded_files.append({
                "filename": filename,
                "filepath": filepath,
                "extracted_count": len(collected_list)
            })
            
            task.collected_data.extend(collected_list)
            self.storage_service.save_task(task)
            
            return collected_list
            
        except Exception as e:
            print(f"[ResearchAgent] 文件分析失败: {e}")
            # 回退：直接作为原始数据
            collected = CollectedData(
                title=filename,
                content=file_content[:5000],
                source=DataSource(
                    source_type=DataSourceType.USER_UPLOAD,
                    name=f"用户上传: {filename}",
                    credibility=CredibilityLevel.MEDIUM
                ),
                tags=["用户上传"],
                is_verified=True
            )
            task.collected_data.append(collected)
            self.storage_service.save_task(task)
            return [collected]
    
    # ============ 步骤3：数据清洗 ============
    
    def clean_data(self, task: ResearchTask) -> List[CollectedData]:
        """
        清洗采集到的数据：去重、过滤、校验、冲突检测
        
        Args:
            task: 调研任务
            
        Returns:
            清洗后的数据列表
        """
        if not task.collected_data:
            raise ValueError("没有可清洗的数据，请先执行collect_data")
        
        task.status = TaskStatus.CLEANING
        self._emit_progress(task.task_id, 3, 6, "cleaning", 
                           f"正在清洗 {len(task.collected_data)} 条数据...")
        
        # 1. 过滤广告/营销内容
        filtered = [
            d for d in task.collected_data
            if not DataCleanService.is_spam_content(d.content)
        ]
        spam_count = len(task.collected_data) - len(filtered)
        
        # 2. 去重
        unique_data = DataCleanService.deduplicate(filtered)
        dup_count = len(filtered) - len(unique_data)
        
        # 3. 使用LLM进行深度清洗（针对大量数据，分批处理）
        if len(unique_data) > 5:
            try:
                cleaned = self._llm_clean_data(task, unique_data)
                if cleaned:
                    unique_data = cleaned
            except Exception as e:
                print(f"[ResearchAgent] LLM清洗失败，使用基础清洗结果: {e}")
        
        # 4. 冲突检测
        conflicts = DataCleanService.detect_conflicts(unique_data)
        for conflict in conflicts:
            for data_id in conflict.get("data_ids", []):
                for item in unique_data:
                    if item.id == data_id:
                        item.is_conflicting = True
                        item.conflict_note = conflict.get("description", "")
        
        task.cleaned_data = unique_data
        self.storage_service.save_task(task)
        
        self._emit_progress(task.task_id, 3, 6, "cleaned",
                           f"数据清洗完成：过滤广告{spam_count}条，去重{dup_count}条，"
                           f"剩余{len(unique_data)}条有效数据，发现{len(conflicts)}处数据冲突")
        
        return unique_data
    
    def _llm_clean_data(self, task: ResearchTask, data_list: List[CollectedData]) -> Optional[List[CollectedData]]:
        """使用LLM进行深度数据清洗"""
        # 准备数据文本（限制长度）
        raw_data_text = ""
        for i, item in enumerate(data_list[:30]):  # 最多处理30条
            raw_data_text += f"\n--- 数据 {i + 1} (ID: {item.id}) ---\n"
            raw_data_text += f"标题: {item.title}\n"
            raw_data_text += f"内容: {item.content[:500]}\n"
            raw_data_text += f"来源: {item.source.name} ({item.source.url})\n"
            raw_data_text += f"标签: {', '.join(item.tags)}\n"
        
        title = task.outline.title if task.outline else task.query
        prompt = DATA_CLEANING_PROMPT.format(
            title=title,
            raw_data=raw_data_text
        )
        
        response_text, usage = self.model_service.call_llm(
            self.llm_model, SYSTEM_PROMPT, prompt,
            temperature=0.1, max_tokens=8192
        )
        task.total_tokens_used += usage.get("total_tokens", 0)
        
        result = _extract_json(response_text)
        cleaned_items = result.get("cleaned_data", [])
        
        if not cleaned_items:
            return None
        
        # 转换为CollectedData对象
        cleaned_list = []
        for item_data in cleaned_items:
            cleaned_list.append(CollectedData.from_dict(item_data))
        
        return cleaned_list
    
    # ============ 步骤4：智能分析 ============
    
    def run_analysis(self, task: ResearchTask, 
                     model_types: List[str] = None) -> List[AnalysisResult]:
        """
        执行智能分析
        
        Args:
            task: 调研任务
            model_types: 分析模型类型列表（如 ["swot", "pest"]）
                        为空时自动推荐
            
        Returns:
            分析结果列表
        """
        data_source = task.cleaned_data if task.cleaned_data else task.collected_data
        if not data_source:
            raise ValueError("没有可分析的数据")
        
        task.status = TaskStatus.ANALYZING
        
        # 自动推荐分析模型
        if not model_types:
            recommendations = recommend_models(task.query, task.industry)
            model_types = [r["model_type"] for r in recommendations[:3]]
        
        total_models = len(model_types)
        results = []
        
        for i, model_type_str in enumerate(model_types):
            try:
                model_type = AnalysisModelType(model_type_str)
            except ValueError:
                continue
            
            model_info = MODEL_INFO.get(model_type, {})
            model_name = model_info.get("name", model_type_str)
            
            self._emit_progress(task.task_id, 4, 6, "analyzing",
                               f"正在执行{model_name} ({i + 1}/{total_models})...")
            
            try:
                result = self._run_single_analysis(task, model_type, data_source)
                results.append(result)
            except Exception as e:
                print(f"[ResearchAgent] {model_name}分析失败: {e}")
                results.append(AnalysisResult(
                    model_type=model_type,
                    title=f"{model_name}（分析失败）",
                    content=f"分析过程中出现错误: {str(e)}",
                    confidence_note="⚠️ 分析未完成"
                ))
        
        task.analysis_results = results
        self.storage_service.save_task(task)
        
        self._emit_progress(task.task_id, 4, 6, "analyzed",
                           f"智能分析完成：已完成 {len(results)} 项分析")
        
        return results
    
    def _run_single_analysis(self, task: ResearchTask, model_type: AnalysisModelType,
                             data_source: List[CollectedData]) -> AnalysisResult:
        """执行单个分析模型"""
        model_info = MODEL_INFO.get(model_type, {})
        model_name = model_info.get("name", model_type.value)
        
        # 准备分析数据
        verified_data = prepare_analysis_data(data_source, model_type)
        
        # 获取模型专用提示词
        model_specific = ANALYSIS_MODEL_PROMPTS.get(model_type.value, "请进行综合分析。")
        
        title = task.outline.title if task.outline else task.query
        prompt = ANALYSIS_PROMPT.format(
            title=title,
            model_name=model_name,
            model_type=model_type.value,
            verified_data=verified_data[:6000],
            model_specific_prompt=model_specific
        )
        
        response_text, usage = self.model_service.call_llm(
            self.llm_model, SYSTEM_PROMPT, prompt,
            temperature=0.3, max_tokens=4096
        )
        task.total_tokens_used += usage.get("total_tokens", 0)
        
        result_data = _extract_json(response_text)
        
        return AnalysisResult(
            model_type=model_type,
            title=result_data.get("title", f"{model_name}分析结果"),
            content=result_data.get("content", ""),
            source_citations=result_data.get("source_citations", []),
            chart_suggestions=result_data.get("chart_suggestions", []),
            confidence_note=result_data.get("confidence_note", "")
        )
    
    # ============ 步骤5：报告生成 ============
    
    def generate_report(self, task: ResearchTask, 
                        format: str = "markdown") -> ResearchReport:
        """
        生成调研报告
        
        Args:
            task: 调研任务
            format: 输出格式 ("markdown" / "word" / "ppt_outline")
            
        Returns:
            调研报告对象
        """
        task.status = TaskStatus.GENERATING
        self._emit_progress(task.task_id, 5, 6, "generating", "正在生成调研报告...")
        
        # 准备数据
        data_source = task.cleaned_data if task.cleaned_data else task.collected_data
        
        outline_text = ""
        if task.outline:
            for item in task.outline.items:
                outline_text += f"\n### {item.title}\n{item.description}\n"
                for sub in item.sub_items:
                    outline_text += f"  - {sub.title}: {sub.description}\n"
        
        verified_data_text = ""
        for item in data_source[:20]:
            verified_data_text += f"\n**{item.title}**\n"
            verified_data_text += f"{item.content[:500]}\n"
            verified_data_text += f"[来源: {item.source.name}, 可信度: {item.source.credibility.value}]\n"
        
        analysis_text = ""
        for result in task.analysis_results:
            analysis_text += f"\n### {result.title}\n"
            analysis_text += result.content[:2000]
            analysis_text += "\n"
        
        # 调用LLM生成报告
        title = task.outline.title if task.outline else task.query
        objective = task.outline.objective if task.outline else task.query
        
        prompt = REPORT_GENERATION_PROMPT.format(
            title=title,
            objective=objective,
            outline=outline_text,
            verified_data=verified_data_text[:6000],
            analysis_results=analysis_text[:4000]
        )
        
        response_text, usage = self.model_service.call_llm(
            self.llm_model, SYSTEM_PROMPT, prompt,
            temperature=0.4, max_tokens=8192
        )
        task.total_tokens_used += usage.get("total_tokens", 0)
        
        try:
            result_data = _extract_json(response_text)
        except ValueError:
            # 如果JSON解析失败，直接使用文本作为报告内容
            result_data = {
                "title": title,
                "summary": "",
                "sections": [{"title": "调研报告", "content": response_text}],
                "appendix": []
            }
        
        # 构建报告对象
        report = ResearchReport(
            title=result_data.get("title", title),
            summary=result_data.get("summary", ""),
            sections=result_data.get("sections", []),
            appendix=result_data.get("appendix", []),
            format=ReportFormat(format) if format in ["markdown", "word", "ppt_outline"] else ReportFormat.MARKDOWN,
            version=1
        )
        
        # 生成完整Markdown内容
        report.content = self.report_service.generate_markdown(report)
        
        task.report = report
        task.status = TaskStatus.COMPLETED
        self.storage_service.save_task(task)
        
        self._emit_progress(task.task_id, 5, 6, "generated",
                           f"报告生成完成：{len(report.sections)}个章节")
        
        return report
    
    # ============ 步骤6：迭代优化 ============
    
    def iterate_report(self, task: ResearchTask, feedback: str) -> ResearchReport:
        """
        基于用户反馈迭代优化报告
        
        Args:
            task: 调研任务
            feedback: 用户修改意见
            
        Returns:
            更新后的报告
        """
        if not task.report:
            raise ValueError("还没有生成报告，请先执行generate_report")
        
        task.status = TaskStatus.ITERATING
        self._emit_progress(task.task_id, 6, 6, "iterating", "正在根据反馈优化报告...")
        
        current_version = task.report.version
        
        prompt = ITERATION_PROMPT.format(
            version=current_version,
            current_report=task.report.content[:8000],
            feedback=feedback
        )
        
        response_text, usage = self.model_service.call_llm(
            self.llm_model, SYSTEM_PROMPT, prompt,
            temperature=0.3, max_tokens=8192
        )
        task.total_tokens_used += usage.get("total_tokens", 0)
        
        try:
            result_data = _extract_json(response_text)
        except ValueError:
            result_data = {
                "title": task.report.title,
                "summary": task.report.summary,
                "sections": [{"title": "更新后的报告", "content": response_text}],
                "appendix": task.report.appendix,
                "change_log": feedback
            }
        
        # 保存迭代历史
        task.iteration_history.append({
            "version": current_version,
            "feedback": feedback,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "change_log": result_data.get("change_log", "")
        })
        
        # 更新报告
        new_report = ResearchReport(
            id=task.report.id,
            title=result_data.get("title", task.report.title),
            summary=result_data.get("summary", task.report.summary),
            sections=result_data.get("sections", task.report.sections),
            appendix=result_data.get("appendix", task.report.appendix),
            format=task.report.format,
            version=current_version + 1
        )
        new_report.content = self.report_service.generate_markdown(new_report)
        
        task.report = new_report
        task.status = TaskStatus.COMPLETED
        self.storage_service.save_task(task)
        
        self._emit_progress(task.task_id, 6, 6, "iterated",
                           f"报告已更新至 v{new_report.version}")
        
        return new_report
    
    # ============ 流式执行全流程 ============
    
    def run_full_pipeline_stream(self, task: ResearchTask,
                                  model_types: List[str] = None) -> Generator:
        """
        流式执行完整调研流程，逐步返回进度和结果
        
        Yields:
            dict: 各阶段进度和结果
        """
        try:
            # 阶段1：解析需求
            yield {"type": "stage", "stage": "parsing", "message": "正在解析调研需求..."}
            outline = self.parse_requirement(task)
            yield {
                "type": "stage_done", "stage": "parsing",
                "result": outline.to_dict(),
                "message": f"提纲生成完成：{len(outline.items)}个章节"
            }
            
            # 阶段2：数据采集
            yield {"type": "stage", "stage": "collecting", "message": "正在采集数据..."}
            collected = self.collect_data(task)
            yield {
                "type": "stage_done", "stage": "collecting",
                "result": {"count": len(collected)},
                "message": f"采集完成：{len(collected)}条数据"
            }
            
            # 阶段3：数据清洗
            yield {"type": "stage", "stage": "cleaning", "message": "正在清洗数据..."}
            cleaned = self.clean_data(task)
            yield {
                "type": "stage_done", "stage": "cleaning",
                "result": {"count": len(cleaned)},
                "message": f"清洗完成：{len(cleaned)}条有效数据"
            }
            
            # 阶段4：智能分析
            yield {"type": "stage", "stage": "analyzing", "message": "正在智能分析..."}
            analysis = self.run_analysis(task, model_types)
            yield {
                "type": "stage_done", "stage": "analyzing",
                "result": [a.to_dict() for a in analysis],
                "message": f"分析完成：{len(analysis)}项分析"
            }
            
            # 阶段5：生成报告
            yield {"type": "stage", "stage": "generating", "message": "正在生成报告..."}
            report = self.generate_report(task)
            yield {
                "type": "stage_done", "stage": "generating",
                "result": report.to_dict(),
                "message": "报告生成完成"
            }
            
            # 完成
            yield {
                "type": "done",
                "task_id": task.task_id,
                "message": "调研全流程完成",
                "total_tokens": task.total_tokens_used
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "message": f"调研流程出错: {str(e)}",
                "stage": task.status.value
            }
    
    # ============ 导出功能 ============
    
    def export_report(self, task: ResearchTask, format: str = "markdown",
                      output_dir: str = "exports") -> str:
        """
        导出调研报告
        
        Args:
            task: 调研任务
            format: 导出格式
            output_dir: 输出目录
            
        Returns:
            导出文件路径
        """
        if not task.report:
            raise ValueError("还没有生成报告")
        
        os.makedirs(output_dir, exist_ok=True)
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', task.report.title)[:50]
        
        if format == "word":
            output_path = os.path.join(output_dir, f"research_{task.task_id}_{safe_title}.docx")
            return self.report_service.generate_word(task.report, output_path)
        
        elif format == "ppt_outline":
            output_path = os.path.join(output_dir, f"research_{task.task_id}_{safe_title}_ppt.md")
            ppt_content = self.report_service.generate_ppt_outline(task.report)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(ppt_content)
            return output_path
        
        else:  # markdown
            output_path = os.path.join(output_dir, f"research_{task.task_id}_{safe_title}.md")
            md_content = self.report_service.generate_markdown(task.report)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            return output_path
