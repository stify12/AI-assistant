"""
AI调研员 - 智能分析模型

包含标准化分析框架的实现：
- SWOT分析
- 波特五力模型
- PEST分析
- 用户分层模型
- 市场规模估算
- 竞争格局分析
- 自动模型推荐引擎
"""

from typing import List, Dict, Any, Optional
from .models import AnalysisModelType, AnalysisResult, CollectedData


# ============ 分析模型推荐引擎 ============

# 行业关键词 → 推荐分析模型的映射
INDUSTRY_MODEL_MAP = {
    # 消费类行业
    "消费": [AnalysisModelType.SWOT, AnalysisModelType.USER_SEGMENTATION, AnalysisModelType.COMPETITIVE],
    "零售": [AnalysisModelType.PORTER_FIVE, AnalysisModelType.USER_SEGMENTATION, AnalysisModelType.COMPETITIVE],
    "电商": [AnalysisModelType.COMPETITIVE, AnalysisModelType.USER_SEGMENTATION, AnalysisModelType.MARKET_SIZE],
    
    # 科技类行业
    "科技": [AnalysisModelType.PEST, AnalysisModelType.PORTER_FIVE, AnalysisModelType.COMPETITIVE],
    "ai": [AnalysisModelType.PEST, AnalysisModelType.MARKET_SIZE, AnalysisModelType.COMPETITIVE],
    "人工智能": [AnalysisModelType.PEST, AnalysisModelType.MARKET_SIZE, AnalysisModelType.COMPETITIVE],
    "互联网": [AnalysisModelType.PORTER_FIVE, AnalysisModelType.COMPETITIVE, AnalysisModelType.USER_SEGMENTATION],
    "软件": [AnalysisModelType.SWOT, AnalysisModelType.COMPETITIVE, AnalysisModelType.MARKET_SIZE],
    
    # 教育行业
    "教育": [AnalysisModelType.PEST, AnalysisModelType.USER_SEGMENTATION, AnalysisModelType.MARKET_SIZE],
    "培训": [AnalysisModelType.COMPETITIVE, AnalysisModelType.USER_SEGMENTATION, AnalysisModelType.SWOT],
    
    # 金融行业
    "金融": [AnalysisModelType.PEST, AnalysisModelType.PORTER_FIVE, AnalysisModelType.SWOT],
    "银行": [AnalysisModelType.PORTER_FIVE, AnalysisModelType.SWOT, AnalysisModelType.PEST],
    "保险": [AnalysisModelType.SWOT, AnalysisModelType.COMPETITIVE, AnalysisModelType.PEST],
    
    # 医疗健康
    "医疗": [AnalysisModelType.PEST, AnalysisModelType.MARKET_SIZE, AnalysisModelType.PORTER_FIVE],
    "健康": [AnalysisModelType.MARKET_SIZE, AnalysisModelType.USER_SEGMENTATION, AnalysisModelType.PEST],
    "医药": [AnalysisModelType.PORTER_FIVE, AnalysisModelType.PEST, AnalysisModelType.COMPETITIVE],
    
    # 制造业
    "制造": [AnalysisModelType.PORTER_FIVE, AnalysisModelType.SWOT, AnalysisModelType.PEST],
    "新能源": [AnalysisModelType.PEST, AnalysisModelType.MARKET_SIZE, AnalysisModelType.COMPETITIVE],
    "汽车": [AnalysisModelType.PORTER_FIVE, AnalysisModelType.COMPETITIVE, AnalysisModelType.PEST],
    
    # 房地产
    "房地产": [AnalysisModelType.PEST, AnalysisModelType.MARKET_SIZE, AnalysisModelType.SWOT],
    "物业": [AnalysisModelType.COMPETITIVE, AnalysisModelType.SWOT, AnalysisModelType.USER_SEGMENTATION],
    
    # 默认
    "default": [AnalysisModelType.SWOT, AnalysisModelType.PEST, AnalysisModelType.MARKET_SIZE],
}

# 分析模型的中文名称和描述
MODEL_INFO = {
    AnalysisModelType.SWOT: {
        "name": "SWOT分析",
        "description": "分析优势(Strengths)、劣势(Weaknesses)、机会(Opportunities)、威胁(Threats)",
        "icon": "📊",
        "best_for": "企业或行业的内外部综合评估"
    },
    AnalysisModelType.PORTER_FIVE: {
        "name": "波特五力分析",
        "description": "分析供应商议价能力、购买者议价能力、新进入者威胁、替代品威胁、行业内竞争",
        "icon": "⚔️",
        "best_for": "行业竞争强度和盈利能力评估"
    },
    AnalysisModelType.PEST: {
        "name": "PEST分析",
        "description": "分析政治(Political)、经济(Economic)、社会(Social)、技术(Technological)宏观环境",
        "icon": "🌍",
        "best_for": "宏观环境与政策影响分析"
    },
    AnalysisModelType.USER_SEGMENTATION: {
        "name": "用户分层分析",
        "description": "按人口特征、行为特征、需求特征、价值分层进行用户画像分析",
        "icon": "👥",
        "best_for": "目标用户群体识别和需求洞察"
    },
    AnalysisModelType.MARKET_SIZE: {
        "name": "市场规模估算",
        "description": "基于TAM/SAM/SOM框架估算市场规模、增长率和驱动因素",
        "icon": "📈",
        "best_for": "市场机会评估和投资决策"
    },
    AnalysisModelType.COMPETITIVE: {
        "name": "竞争格局分析",
        "description": "分析主要竞争者、市场份额、竞争策略和差异化定位",
        "icon": "🏆",
        "best_for": "竞争态势判断和策略制定"
    },
}


def recommend_models(query: str, industry: str = "") -> List[Dict[str, Any]]:
    """
    根据调研需求自动推荐最适合的分析模型
    
    Args:
        query: 用户调研需求文本
        industry: 行业名称
        
    Returns:
        推荐的分析模型列表，包含名称、描述和推荐理由
    """
    text = f"{query} {industry}".lower()
    
    # 匹配行业关键词
    matched_models = set()
    for keyword, models in INDUSTRY_MODEL_MAP.items():
        if keyword == "default":
            continue
        if keyword.lower() in text:
            for model in models:
                matched_models.add(model)
    
    # 如果没有匹配到，使用默认
    if not matched_models:
        matched_models = set(INDUSTRY_MODEL_MAP["default"])
    
    # 根据调研需求补充特定模型
    if any(kw in text for kw in ["市场规模", "市场空间", "市场容量", "投资"]):
        matched_models.add(AnalysisModelType.MARKET_SIZE)
    if any(kw in text for kw in ["竞争", "对手", "竞品", "份额"]):
        matched_models.add(AnalysisModelType.COMPETITIVE)
    if any(kw in text for kw in ["用户", "消费者", "客户", "画像"]):
        matched_models.add(AnalysisModelType.USER_SEGMENTATION)
    if any(kw in text for kw in ["政策", "法规", "监管", "合规"]):
        matched_models.add(AnalysisModelType.PEST)
    
    # 构建推荐结果
    recommendations = []
    for model_type in matched_models:
        info = MODEL_INFO.get(model_type, {})
        recommendations.append({
            "model_type": model_type.value,
            "name": info.get("name", model_type.value),
            "description": info.get("description", ""),
            "icon": info.get("icon", "📊"),
            "best_for": info.get("best_for", ""),
            "recommended": True
        })
    
    return recommendations


def get_all_models() -> List[Dict[str, Any]]:
    """获取所有可用的分析模型信息"""
    models = []
    for model_type, info in MODEL_INFO.items():
        models.append({
            "model_type": model_type.value,
            "name": info["name"],
            "description": info["description"],
            "icon": info["icon"],
            "best_for": info["best_for"]
        })
    return models


def prepare_analysis_data(collected_data: List[CollectedData], 
                          model_type: AnalysisModelType) -> str:
    """
    为指定分析模型准备数据摘要
    
    根据分析模型类型，从采集数据中筛选和组织最相关的数据
    
    Args:
        collected_data: 清洗后的数据列表
        model_type: 分析模型类型
        
    Returns:
        格式化的数据摘要文本
    """
    if not collected_data:
        return "暂无已验证数据"
    
    # 根据模型类型筛选相关标签
    model_tags = {
        AnalysisModelType.SWOT: ["优势", "劣势", "机会", "威胁", "竞争", "市场", "技术", "品牌"],
        AnalysisModelType.PORTER_FIVE: ["供应商", "采购", "竞争", "替代品", "进入壁垒", "市场份额"],
        AnalysisModelType.PEST: ["政策", "法规", "经济", "GDP", "社会", "技术", "创新"],
        AnalysisModelType.USER_SEGMENTATION: ["用户", "消费者", "画像", "需求", "行为", "年龄", "收入"],
        AnalysisModelType.MARKET_SIZE: ["市场规模", "增长率", "营收", "投资", "融资", "估值"],
        AnalysisModelType.COMPETITIVE: ["竞争", "市场份额", "对手", "竞品", "排名", "头部"],
    }
    
    relevant_tags = model_tags.get(model_type, [])
    
    # 组织数据
    lines = []
    for item in collected_data:
        # 检查是否与分析模型相关
        is_relevant = not relevant_tags  # 如果没有特定标签要求，全部数据都相关
        for tag in item.tags:
            if any(rt in tag for rt in relevant_tags):
                is_relevant = True
                break
        
        # 也检查内容关键词
        if not is_relevant:
            for rt in relevant_tags:
                if rt in item.content:
                    is_relevant = True
                    break
        
        if is_relevant or not relevant_tags:
            source_info = f"[来源: {item.source.name}"
            if item.source.publisher:
                source_info += f", {item.source.publisher}"
            if item.source.publish_date:
                source_info += f", {item.source.publish_date}"
            source_info += f", 可信度: {item.source.credibility.value}]"
            
            lines.append(f"### {item.title}")
            lines.append(item.content[:1000])
            lines.append(source_info)
            lines.append("")
    
    if not lines:
        # 如果筛选后没有数据，使用所有数据
        for item in collected_data[:20]:
            lines.append(f"### {item.title}")
            lines.append(item.content[:500])
            lines.append(f"[来源: {item.source.name}]")
            lines.append("")
    
    return "\n".join(lines)
