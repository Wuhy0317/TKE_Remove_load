import os

class Config:
    """应用配置类"""
    # Kubeconfig目录
    KUBECONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'kubeconfigs')
    
    # Flask配置
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # API配置
    API_PREFIX = '/api'
    
    # 标签配置
    LOAD_LABEL = 'load'  # 现有标签名
    LOAD_ONLINE_VALUE = 'online'  # 正常流量值
    LOAD_DONE_VALUE = 'done'  # 踢出负载值
