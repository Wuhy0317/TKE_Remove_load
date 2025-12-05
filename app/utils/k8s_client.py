from kubernetes.config import load_kube_config
import kubernetes.client
import os

class K8sClient:
    """Kubernetes客户端工具类"""
    
    def __init__(self, cluster_display_name, kubeconfig_dir=None):
        """
        初始化K8s客户端
        
        Args:
            cluster_display_name: 集群显示名称
            kubeconfig_dir: kubeconfig文件目录（保留兼容）
        """
        from app.utils.cluster_manager import ClusterManager
        self.cluster_display_name = cluster_display_name
        self.cluster_manager = ClusterManager()
        
        # 获取集群配置
        clusters = self.cluster_manager.get_clusters()
        # 先尝试按name匹配，再尝试按display_name匹配
        self.cluster = next((c for c in clusters if c['name'] == cluster_display_name), None)
        if not self.cluster:
            self.cluster = next((c for c in clusters if c['display_name'] == cluster_display_name), None)
        
        if not self.cluster:
            raise ValueError(f'Cluster not found: {cluster_display_name}')
        
        # 将kubeconfig内容写入临时文件
        import tempfile
        self.temp_config_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        self.temp_config_file.write(self.cluster['kubeconfig_content'])
        self.temp_config_file.close()
        
        self.config_file = self.temp_config_file.name
    
    def _get_client(self, client_type):
        """获取指定类型的Kubernetes客户端"""
        if not self.config_file:
            raise FileNotFoundError(f'Kubeconfig file not found for cluster: {self.cluster_name}')
        
        # 加载kubeconfig
        load_kube_config(self.config_file)
        
        # 创建配置对象并禁用SSL验证
        configuration = kubernetes.client.Configuration.get_default_copy()
        configuration.verify_ssl = False
        
        # 根据客户端类型返回对应实例，使用禁用SSL验证的配置
        if client_type == 'core':
            return kubernetes.client.CoreV1Api(kubernetes.client.ApiClient(configuration))
        elif client_type == 'apps':
            return kubernetes.client.AppsV1Api(kubernetes.client.ApiClient(configuration))
        else:
            raise ValueError(f'Unknown client type: {client_type}')
    
    def get_core_client(self):
        """获取CoreV1Api客户端"""
        return self._get_client('core')
    
    def get_apps_client(self):
        """获取AppsV1Api客户端"""
        return self._get_client('apps')
    
    def get_config_file(self):
        """获取kubeconfig文件路径"""
        return self.config_file
