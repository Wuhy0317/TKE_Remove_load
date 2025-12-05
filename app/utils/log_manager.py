import json
import os
from datetime import datetime

class LogManager:
    """日志管理类"""
    
    def __init__(self, log_file=None):
        """初始化日志管理器"""
        self.log_file = log_file or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config',
            'logs.json'
        )
        self._init_log_file()
    
    def _init_log_file(self):
        """初始化日志文件"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def _read_logs(self):
        """读取所有日志"""
        with open(self.log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _write_logs(self, logs):
        """写入日志"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    
    def add_log(self, username, action, resource=None, details=None):
        """添加日志记录"""
        logs = self._read_logs()
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'username': username,
            'action': action,
            'resource': resource,
            'details': details
        }
        
        logs.append(log_entry)
        # 只保留最近1000条日志
        if len(logs) > 1000:
            logs = logs[-1000:]
        
        self._write_logs(logs)
    
    def add_login_log(self, username, success, details=None):
        """添加登录日志"""
        action = 'login_success' if success else 'login_failed'
        self.add_log(username, action, details=details)
    
    def add_logout_log(self, username):
        """添加登出日志"""
        self.add_log(username, 'logout')
    
    def add_operation_log(self, username, action, resource, details=None):
        """添加操作日志"""
        self.add_log(username, action, resource, details)
    
    def get_logs(self, limit=None, action=None):
        """获取日志记录"""
        logs = self._read_logs()
        
        if action:
            logs = [log for log in logs if log['action'] == action]
        
        if limit:
            logs = logs[-limit:]
        
        return logs
