"""
路由模块初始化
将所有蓝图注册到 Flask 应用
"""


def register_blueprints(app):
    """注册所有蓝图到 Flask 应用"""
    from .common import common_bp
    from .prompt_manage import prompt_manage_bp
    from .chat import chat_bp
    from .subject_grading import subject_grading_bp
    from .model_recommend import model_recommend_bp
    from .prompt_optimize import prompt_optimize_bp
    from .data_analysis import data_analysis_bp
    from .batch_evaluation import batch_evaluation_bp
    from .dataset_manage import dataset_manage_bp
    from .collection_manage import collection_manage_bp
    from .ai_eval import ai_eval_bp
    from .dashboard import dashboard_bp
    from .test_plans import test_plans_bp
    from .error_samples import error_samples_bp
    from .anomaly import anomaly_bp
    from .image_compare import image_compare_bp
    from .clustering import clustering_bp
    from .optimization import optimization_bp
    from .drilldown import drilldown_bp
    from .batch_compare import batch_compare_bp
    from .task_assignment import task_assignment_bp
    from .error_correlation import error_correlation_bp
    from .best_practice import best_practice_bp
    from .error_mark import error_mark_bp
    from .saved_filter import saved_filter_bp
    from .analysis import analysis_bp
    from .automation import automation_bp
    from .rfid_query import rfid_query_bp
    from .prompt_config import prompt_config_bp
    
    # 注册通用路由（无前缀）
    app.register_blueprint(common_bp)
    
    # 注册功能模块路由
    app.register_blueprint(prompt_manage_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(subject_grading_bp, url_prefix='/api/grading')
    app.register_blueprint(model_recommend_bp)
    app.register_blueprint(prompt_optimize_bp)
    app.register_blueprint(data_analysis_bp)
    app.register_blueprint(batch_evaluation_bp, url_prefix='/api/batch')
    app.register_blueprint(dataset_manage_bp)
    app.register_blueprint(collection_manage_bp)  # 基准合集管理（API路径已在路由中定义）
    app.register_blueprint(ai_eval_bp)
    
    # 注册测试计划看板路由（无前缀，API路径已在路由中定义）
    app.register_blueprint(dashboard_bp)
    
    # 注册测试计划路由（无前缀，API路径已在路由中定义）
    app.register_blueprint(test_plans_bp)
    
    # 注册错误样本库路由
    app.register_blueprint(error_samples_bp)
    
    # 注册异常检测路由
    app.register_blueprint(anomaly_bp)
    
    # 注册图片对比路由
    app.register_blueprint(image_compare_bp)
    
    # 注册错误聚类路由
    app.register_blueprint(clustering_bp)
    
    # 注册优化建议路由
    app.register_blueprint(optimization_bp)
    
    # 注册数据下钻路由
    app.register_blueprint(drilldown_bp)
    
    # 注册批次对比路由
    app.register_blueprint(batch_compare_bp)
    
    # 注册任务分配路由
    app.register_blueprint(task_assignment_bp)
    
    # 注册错误关联分析路由
    app.register_blueprint(error_correlation_bp)
    
    # 注册最佳实践库路由
    app.register_blueprint(best_practice_bp)
    
    # 注册错误标记路由
    app.register_blueprint(error_mark_bp)
    
    # 注册保存筛选路由
    app.register_blueprint(saved_filter_bp)
    
    # 注册 AI 分析路由
    app.register_blueprint(analysis_bp)
    
    # 注册自动化管理路由
    app.register_blueprint(automation_bp)
    
    # 注册RFID查询路由
    app.register_blueprint(rfid_query_bp)
    
    # 注册提示词配置路由
    app.register_blueprint(prompt_config_bp)
