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
    from .ai_eval import ai_eval_bp
    
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
    app.register_blueprint(ai_eval_bp)
