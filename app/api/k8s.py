from flask import Blueprint, request, jsonify, current_app, send_from_directory, session
from app.services.k8s_service import K8sService
from app.utils.cluster_manager import ClusterManager
from app.utils.auth_manager import AuthManager
import os
from functools import wraps

# 创建蓝图
k8s_bp = Blueprint('k8s', __name__)

# 集群管理器
cluster_manager = ClusterManager()

# 认证管理器
auth_manager = AuthManager()

# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

# 权限验证装饰器
def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session or not session['logged_in']:
                return jsonify({'success': False, 'message': '请先登录'}), 401
            
            username = session['username']
            
            # 从URL参数中获取集群名称
            cluster = kwargs.get('cluster')  # 集群名称通常是URL的第一个参数
            
            if not auth_manager.check_permission(username, permission, cluster):
                # 根据cluster参数返回不同的错误信息
                if cluster:
                    return jsonify({'success': False, 'message': '您当前没有该集群权限，请联系管理员。'}), 403
                else:
                    return jsonify({'success': False, 'message': '权限不足'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 管理后台权限验证装饰器
def admin_required(f):
    return permission_required('admin')(f)

@k8s_bp.route('/clusters', methods=['GET'])
@login_required
def get_clusters():
    """获取用户有权限访问的集群"""
    username = session['username']
    all_clusters = cluster_manager.get_clusters()
    user = auth_manager.get_user(username)
    
    # 创建K8sService实例来获取集群版本
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    k8s_service = K8sService(kubeconfig_dir)
    
    # 筛选用户有权限的集群并添加版本信息
    accessible_clusters = []
    
    # 全局管理员或没有集群限制的用户可以访问所有集群
    if user['permissions'].get('admin', False) or not user['permissions'].get('clusters'):
        for cluster in all_clusters:
            cluster_name = cluster['name']
            # 获取集群版本信息
            version_info = k8s_service.get_cluster_version(cluster_name)
            accessible_clusters.append({
                'name': cluster_name, 
                'display_name': cluster['display_name'],
                'version': version_info['git_version']
            })
    else:
        # 检查每个集群是否在用户的访问列表中
        for cluster in all_clusters:
            cluster_name = cluster['name']
            if cluster_name in user['permissions']['clusters']:
                # 获取集群版本信息
                version_info = k8s_service.get_cluster_version(cluster_name)
                accessible_clusters.append({
                    'name': cluster_name, 
                    'display_name': cluster['display_name'],
                    'version': version_info['git_version']
                })
    
    return jsonify(accessible_clusters)

# 管理后台API端点
@k8s_bp.route('/admin/clusters', methods=['GET'])
@admin_required
def admin_get_clusters():
    """管理后台获取所有集群配置"""
    clusters = cluster_manager.get_clusters()
    return jsonify(clusters)

@k8s_bp.route('/admin/clusters/<cluster_name>', methods=['GET'])
@admin_required
def admin_get_cluster(cluster_name):
    """管理后台获取单个集群配置"""
    cluster = cluster_manager.get_cluster(cluster_name)
    if cluster:
        return jsonify(cluster)
    return jsonify({'error': '集群不存在'}), 404

@k8s_bp.route('/admin/clusters', methods=['POST'])
@admin_required
def admin_add_cluster():
    """管理后台添加集群配置"""
    data = request.get_json()
    cluster_name = data.get('name')
    display_name = data.get('display_name')
    kubeconfig_content = data.get('kubeconfig_content')
    
    if not all([cluster_name, display_name, kubeconfig_content]):
        return jsonify({'success': False, 'message': '缺少必填字段'}), 400
    
    success, message = cluster_manager.add_cluster(cluster_name, display_name, kubeconfig_content)
    
    if success:
        # 记录操作日志
        current_user = session.get('username', 'unknown')
        auth_manager.log_manager.add_operation_log(
            current_user, 
            'add_cluster', 
            f'cluster/{cluster_name}',
            f'display_name={display_name}'
        )
    
    return jsonify({'success': success, 'message': message})

@k8s_bp.route('/admin/clusters/<cluster_name>', methods=['PUT'])
@admin_required
def admin_update_cluster(cluster_name):
    """管理后台更新集群配置"""
    data = request.get_json()
    display_name = data.get('display_name')
    kubeconfig_content = data.get('kubeconfig_content')
    
    if not any([display_name, kubeconfig_content]):
        return jsonify({'success': False, 'message': '至少需要提供一个更新字段'}), 400
    
    success, message = cluster_manager.update_cluster(cluster_name, display_name, kubeconfig_content)
    
    if success:
        # 记录操作日志
        current_user = session.get('username', 'unknown')
        details = []
        if display_name:
            details.append(f'display_name={display_name}')
        if kubeconfig_content:
            details.append('kubeconfig_updated')
        
        auth_manager.log_manager.add_operation_log(
            current_user, 
            'update_cluster', 
            f'cluster/{cluster_name}',
            ', '.join(details)
        )
    
    return jsonify({'success': success, 'message': message})

@k8s_bp.route('/admin/clusters/<cluster_name>', methods=['DELETE'])
@admin_required
def admin_delete_cluster(cluster_name):
    """管理后台删除集群配置"""
    success, message = cluster_manager.delete_cluster(cluster_name)
    
    if success:
        # 记录操作日志
        current_user = session.get('username', 'unknown')
        auth_manager.log_manager.add_operation_log(
            current_user, 
            'delete_cluster', 
            f'cluster/{cluster_name}'
        )
    
    return jsonify({'success': success, 'message': message})

# 管理后台页面路由
@k8s_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # 使用AuthManager验证用户名和密码
    if auth_manager.verify_password(username, password):
        # 设置会话
        session['logged_in'] = True
        session['username'] = username
        return jsonify({'success': True, 'message': '登录成功'})
    else:
        return jsonify({'success': False, 'message': '用户名或密码错误'})

@k8s_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    # 记录登出日志
    username = session.get('username', 'unknown')
    auth_manager.log_manager.add_logout_log(username)
    
    # 清除会话
    session.clear()
    return jsonify({'success': True, 'message': '登出成功'})

@k8s_bp.route('/current-user', methods=['GET'])
@login_required
def get_current_user():
    """获取当前登录用户信息"""
    username = session.get('username')
    user = auth_manager.get_user(username)
    if user:
        # 移除密码哈希字段
        user_copy = user.copy()
        if 'password_hash' in user_copy:
            del user_copy['password_hash']
        return jsonify(user_copy)
    return jsonify({'error': '用户不存在'}), 404

# 用户管理API
@k8s_bp.route('/admin/users', methods=['GET'])
@admin_required
def admin_get_users():
    """获取所有用户信息"""
    users = auth_manager.get_users()
    return jsonify(users)

@k8s_bp.route('/admin/users/<username>', methods=['GET'])
@admin_required
def admin_get_user(username):
    """获取单个用户信息"""
    user = auth_manager.get_user(username)
    if user:
        # 移除密码哈希字段
        user_copy = user.copy()
        if 'password_hash' in user_copy:
            del user_copy['password_hash']
        return jsonify(user_copy)
    return jsonify({'error': '用户不存在'}), 404

@k8s_bp.route('/admin/users', methods=['POST'])
@admin_required
def admin_add_user():
    """添加用户"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    permissions = data.get('permissions', {})
    
    if not all([username, password]):
        return jsonify({'success': False, 'message': '缺少必填字段'}), 400
    
    # 确保权限结构符合新格式
    if 'clusters' not in permissions:
        permissions['clusters'] = {}  # 初始化集群权限
    
    success, message = auth_manager.add_user(username, password, permissions)
    
    if success:
        # 记录操作日志
        current_user = session.get('username', 'unknown')
        auth_manager.log_manager.add_operation_log(
            current_user, 
            'add_user', 
            f'user/{username}',
            f'permissions={permissions}'
        )
    
    return jsonify({'success': success, 'message': message})

@k8s_bp.route('/admin/users/<username>', methods=['PUT'])
@admin_required
def admin_update_user(username):
    """更新用户信息"""
    data = request.get_json()
    password = data.get('password')
    permissions = data.get('permissions')
    
    success, message = auth_manager.update_user(username, password, permissions)
    
    if success:
        # 记录操作日志
        current_user = session.get('username', 'unknown')
        details = []
        if password:
            details.append('password_updated')
        if permissions:
            details.append(f'permissions={permissions}')
        
        auth_manager.log_manager.add_operation_log(
            current_user, 
            'update_user', 
            f'user/{username}',
            ', '.join(details)
        )
    
    return jsonify({'success': success, 'message': message})

@k8s_bp.route('/admin/users/<username>', methods=['DELETE'])
@admin_required
def admin_delete_user(username):
    """删除用户"""
    success, message = auth_manager.delete_user(username)
    
    if success:
        # 记录操作日志
        current_user = session.get('username', 'unknown')
        auth_manager.log_manager.add_operation_log(
            current_user, 
            'delete_user', 
            f'user/{username}'
        )
    
    return jsonify({'success': success, 'message': message})

@k8s_bp.route('/admin/logs', methods=['GET'])
@admin_required
def admin_get_logs():
    """获取操作日志"""
    action = request.args.get('action')
    logs = auth_manager.log_manager.get_logs(action=action)
    return jsonify(logs)

@k8s_bp.route('/admin')
@admin_required
def admin_index():
    """管理后台首页"""
    return send_from_directory('../static', 'admin.html')

@k8s_bp.route('/<cluster>/namespaces', methods=['GET'])
@login_required
@permission_required('read')
def get_namespaces(cluster):
    """获取指定集群的命名空间"""
    import traceback
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    k8s_service = K8sService(kubeconfig_dir)
    try:
        namespaces = k8s_service.get_namespaces(cluster)
        return jsonify(namespaces)
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        stack_trace = traceback.format_exc()
        print(f"Error in get_namespaces: {error_msg}")
        print(f"Stack trace: {stack_trace}")
        return jsonify({'success': False, 'message': error_msg}), 500

@k8s_bp.route('/<cluster>/nodes', methods=['GET'])
@login_required
@permission_required('read')
def get_nodes(cluster):
    """获取指定集群的节点列表"""
    import traceback
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    k8s_service = K8sService(kubeconfig_dir)
    try:
        nodes = k8s_service.get_nodes(cluster)
        return jsonify(nodes)
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        stack_trace = traceback.format_exc()
        print(f"Error in get_nodes: {error_msg}")
        print(f"Stack trace: {stack_trace}")
        return jsonify({'success': False, 'message': error_msg}), 500

@k8s_bp.route('/<cluster>/<namespace>/workloads', methods=['GET'])
@login_required
@permission_required('read')
def get_workloads(cluster, namespace):
    """获取指定集群和命名空间的工作负载"""
    import traceback
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    workload_type = request.args.get('type')
    k8s_service = K8sService(kubeconfig_dir)
    try:
        workloads = k8s_service.get_workloads(cluster, namespace, workload_type)
        return jsonify(workloads)
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        stack_trace = traceback.format_exc()
        print(f"Error in get_workloads: {error_msg}")
        print(f"Stack trace: {stack_trace}")
        return jsonify({'success': False, 'message': error_msg}), 500

@k8s_bp.route('/<cluster>/<namespace>/pods', methods=['GET'])
@login_required
@permission_required('read')
def get_all_pods(cluster, namespace):
    """获取指定命名空间下的所有Pod"""
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    k8s_service = K8sService(kubeconfig_dir)
    try:
        pods = k8s_service.get_pods(cluster, namespace)
        return jsonify(pods)
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        stack_trace = traceback.format_exc()
        print(f"Error in get_all_pods: {error_msg}")
        print(f"Stack trace: {stack_trace}")
        return jsonify({'success': False, 'message': error_msg}), 500

@k8s_bp.route('/<cluster>/<namespace>/<workload_type>/<workload_name>/pods', methods=['GET'])
@login_required
@permission_required('read')
def get_workload_pods(cluster, namespace, workload_type, workload_name):
    """获取指定工作负载的Pod列表"""
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    k8s_service = K8sService(kubeconfig_dir)
    try:
        pods = k8s_service.get_pods(cluster, namespace, workload_type, workload_name)
        return jsonify(pods)
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        stack_trace = traceback.format_exc()
        print(f"Error in get_workload_pods: {error_msg}")
        print(f"Stack trace: {stack_trace}")
        return jsonify({'success': False, 'message': error_msg}), 500

@k8s_bp.route('/<cluster>/<namespace>/<workload_type>/<name>/yaml', methods=['GET'])
@login_required
@permission_required('read')
def get_workload_yaml(cluster, namespace, workload_type, name):
    """获取指定工作负载的YAML配置"""
    import traceback
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    k8s_service = K8sService(kubeconfig_dir)
    try:
        yaml_content = k8s_service.get_workload_yaml(cluster, namespace, name, workload_type)
        return yaml_content, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        stack_trace = traceback.format_exc()
        print(f"Error in get_workload_yaml: {error_msg}")
        print(f"Stack trace: {stack_trace}")
        return jsonify({'success': False, 'message': error_msg}), 500

@k8s_bp.route('/<cluster>/<namespace>/pods/<pod_name>/remove-load', methods=['POST'])
@login_required
@permission_required('write')
def remove_load(cluster, namespace, pod_name):
    """踢出Pod负载"""
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    k8s_service = K8sService(kubeconfig_dir)
    try:
        result = k8s_service.remove_load(cluster, namespace, pod_name)
        # 记录操作日志
        username = session.get('username', 'unknown')
        auth_manager.log_manager.add_operation_log(
            username, 
            'remove_load', 
            f'pod/{namespace}/{pod_name}',
            f'cluster={cluster}'
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@k8s_bp.route('/<cluster>/<namespace>/pods/<pod_name>/restore-traffic', methods=['POST'])
@login_required
@permission_required('write')
def restore_traffic(cluster, namespace, pod_name):
    """恢复Pod流量"""
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    k8s_service = K8sService(kubeconfig_dir)
    try:
        result = k8s_service.restore_traffic(cluster, namespace, pod_name)
        # 记录操作日志
        username = session.get('username', 'unknown')
        auth_manager.log_manager.add_operation_log(
            username, 
            'restore_traffic', 
            f'pod/{namespace}/{pod_name}',
            f'cluster={cluster}'
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@k8s_bp.route('/<cluster>/<namespace>/services', methods=['GET'])
@login_required
@permission_required('read')
def get_services(cluster, namespace):
    """获取指定集群和命名空间的服务与路由列表"""
    import traceback
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    service_type = request.args.get('type')
    k8s_service = K8sService(kubeconfig_dir)
    try:
        services = k8s_service.get_services(cluster, namespace, service_type)
        return jsonify(services)
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        stack_trace = traceback.format_exc()
        print(f"Error in get_services: {error_msg}")
        print(f"Stack trace: {stack_trace}")
        return jsonify({'success': False, 'message': error_msg}), 500

@k8s_bp.route('/<cluster>/<namespace>/services/<service_type>/<name>/yaml', methods=['GET'])
@login_required
@permission_required('read')
def get_service_yaml(cluster, namespace, service_type, name):
    """获取指定服务或路由的YAML配置"""
    import traceback
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    k8s_service = K8sService(kubeconfig_dir)
    try:
        yaml_content = k8s_service.get_service_yaml(cluster, namespace, name, service_type)
        return yaml_content, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        stack_trace = traceback.format_exc()
        print(f"Error in get_service_yaml: {error_msg}")
        print(f"Stack trace: {stack_trace}")
        return jsonify({'success': False, 'message': error_msg}), 500

@k8s_bp.route('/<cluster>/<namespace>/configs', methods=['GET'])
@login_required
@permission_required('read')
def get_configs(cluster, namespace):
    """获取指定集群和命名空间的配置资源"""
    import traceback
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    k8s_service = K8sService(kubeconfig_dir)
    try:
        config_type = request.args.get('type')
        configs = k8s_service.get_configs(cluster, namespace, config_type)
        return jsonify(configs)
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        stack_trace = traceback.format_exc()
        print(f"Error in get_configs: {error_msg}")
        print(f"Stack trace: {stack_trace}")
        return jsonify({'success': False, 'message': error_msg}), 500

@k8s_bp.route('/<cluster>/<namespace>/configs/<config_type>/<name>/yaml', methods=['GET'])
@login_required
@permission_required('read')
def get_config_yaml(cluster, namespace, config_type, name):
    """获取指定配置资源的YAML配置"""
    import traceback
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    k8s_service = K8sService(kubeconfig_dir)
    try:
        yaml_content = k8s_service.get_config_yaml(cluster, namespace, name, config_type)
        return yaml_content, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        stack_trace = traceback.format_exc()
        print(f"Error in get_config_yaml: {error_msg}")
        print(f"Stack trace: {stack_trace}")
        return jsonify({'success': False, 'message': error_msg}), 500

@k8s_bp.route('/<cluster>/<namespace>/storage', methods=['GET'])
@login_required
@permission_required('read')
def get_storage(cluster, namespace):
    """获取指定集群和命名空间的存储资源"""
    import traceback
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    k8s_service = K8sService(kubeconfig_dir)
    try:
        storage_type = request.args.get('type')
        storage = k8s_service.get_storage(cluster, namespace, storage_type)
        return jsonify(storage)
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        stack_trace = traceback.format_exc()
        print(f"Error in get_storage: {error_msg}")
        print(f"Stack trace: {stack_trace}")
        return jsonify({'success': False, 'message': error_msg}), 500

@k8s_bp.route('/<cluster>/<namespace>/storage/<storage_type>/<name>/yaml', methods=['GET'])
@login_required
@permission_required('read')
def get_storage_yaml(cluster, namespace, storage_type, name):
    """获取指定存储资源的YAML配置"""
    import traceback
    kubeconfig_dir = current_app.config['KUBECONFIG_DIR']
    k8s_service = K8sService(kubeconfig_dir)
    try:
        yaml_content = k8s_service.get_storage_yaml(cluster, namespace, name, storage_type)
        return yaml_content, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        stack_trace = traceback.format_exc()
        print(f"Error in get_storage_yaml: {error_msg}")
        print(f"Stack trace: {stack_trace}")
        return jsonify({'success': False, 'message': error_msg}), 500
