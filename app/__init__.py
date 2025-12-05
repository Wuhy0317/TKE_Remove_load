from flask import Flask, session, redirect, url_for
from flask_cors import CORS
import os
from app.config.config import Config

def create_app():
    """创建Flask应用实例"""
    app = Flask(__name__, static_folder='../static', static_url_path='/')
    
    # 配置CORS
    CORS(app)
    
    # 应用配置
    app.config['KUBECONFIG_DIR'] = Config.KUBECONFIG_DIR
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    
    # 创建kubeconfig目录（如果不存在）
    if not os.path.exists(app.config['KUBECONFIG_DIR']):
        os.makedirs(app.config['KUBECONFIG_DIR'])
    
    # 登录验证装饰器
    def login_required(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session or not session['logged_in']:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    
    # 登录路由
    @app.route('/login')
    def login():
        return app.send_static_file('login.html')
    
    # 主页面路由，需要登录
    @app.route('/')
    @login_required
    def index():
        return app.send_static_file('index.html')
    
    # 注册蓝图
    from app.api import k8s_bp
    app.register_blueprint(k8s_bp, url_prefix='/api')
    
    return app
