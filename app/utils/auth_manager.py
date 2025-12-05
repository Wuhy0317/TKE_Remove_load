import json
import os
import hashlib
from .log_manager import LogManager

class AuthManager:
    """认证和权限管理类"""
    
    def __init__(self, config_file=None):
        """初始化认证管理器"""
        self.config_file = config_file or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config',
            'auth_config.json'
        )
        self.log_manager = LogManager()
        self._init_config_file()
    
    def _init_config_file(self):
        """初始化配置文件"""
        if not os.path.exists(self.config_file):
            # 初始化默认用户
            default_users = [
                {
                    'username': 'admin',
                    'password_hash': self._hash_password('admin123'),
                    'permissions': {
                        'admin': True,  # 全局管理员权限
                        'read': True,   # 全局读权限
                        'write': True,  # 全局写权限
                        'clusters': {}  # 可访问的集群列表
                    }
                },
                {
                    'username': 'user',
                    'password_hash': self._hash_password('user123'),
                    'permissions': {
                        'admin': False,
                        'read': True,   # 全局读权限
                        'write': False, # 全局写权限
                        'clusters': {}  # 可访问的集群列表
                    }
                }
            ]
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_users, f, ensure_ascii=False, indent=2)
    
    def _hash_password(self, password):
        """密码哈希处理"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def get_users(self):
        """获取所有用户信息"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        # 不返回密码哈希
        for user in users:
            del user['password_hash']
        return users
    
    def get_user(self, username):
        """获取单个用户信息"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        for user in users:
            if user['username'] == username:
                return user
        return None
    
    def add_user(self, username, password, permissions):
        """添加用户"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        # 检查用户名是否已存在
        for user in users:
            if user['username'] == username:
                return False, '用户名已存在'
        
        # 添加新用户
        new_user = {
            'username': username,
            'password_hash': self._hash_password(password),
            'permissions': permissions
        }
        users.append(new_user)
        
        # 保存配置
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        
        return True, '用户添加成功'
    
    def update_user(self, username, password=None, permissions=None):
        """更新用户信息"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        # 查找用户
        for user in users:
            if user['username'] == username:
                # 更新密码
                if password:
                    user['password_hash'] = self._hash_password(password)
                # 更新权限
                if permissions:
                    user['permissions'].update(permissions)
                
                # 保存配置
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(users, f, ensure_ascii=False, indent=2)
                
                return True, '用户更新成功'
        
        return False, '用户不存在'
    
    def delete_user(self, username):
        """删除用户"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        # 查找并删除用户
        for i, user in enumerate(users):
            if user['username'] == username:
                del users[i]
                
                # 保存配置
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(users, f, ensure_ascii=False, indent=2)
                
                return True, '用户删除成功'
        
        return False, '用户不存在'
    
    def verify_password(self, username, password):
        """验证密码"""
        user = self.get_user(username)
        if user and user['password_hash'] == self._hash_password(password):
            self.log_manager.add_login_log(username, True)
            return True
        self.log_manager.add_login_log(username, False)
        return False
    
    def check_permission(self, username, permission, cluster=None):
        """检查用户权限，支持基于集群的权限检查
        
        权限模型：
        1. 全局管理员拥有所有权限
        2. 普通用户：
           a. 需要全局 read/write 权限
           b. 需要在集群的访问列表中
           c. 集群字段是可访问的集群名称列表
        
        Args:
            username: 用户名
            permission: 权限类型（read, write, admin）
            cluster: 集群名称（可选）
            
        Returns:
            bool: 是否拥有该权限
        """
        user = self.get_user(username)
        if not user:
            return False
        
        # 全局管理员拥有所有权限
        if 'admin' in user['permissions'] and user['permissions']['admin']:
            return True
        
        # 检查全局权限
        if permission not in user['permissions'] or not user['permissions'][permission]:
            return False
        
        # 如果需要集群权限，检查用户是否可以访问该集群
        if cluster:
            # 检查集群访问列表
            if 'clusters' not in user['permissions'] or cluster not in user['permissions']['clusters']:
                return False
        
        return True