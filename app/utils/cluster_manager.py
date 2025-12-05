import json
import os

class ClusterManager:
    """集群配置管理类"""
    
    def __init__(self, config_file=None):
        """初始化集群管理器"""
        self.config_file = config_file or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'cluster_configs.json'
        )
        self._init_config_file()
    
    def _init_config_file(self):
        """初始化配置文件"""
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def get_clusters(self):
        """获取所有集群配置，包括现有kubeconfig文件"""
        # 从配置文件读取集群配置
        with open(self.config_file, 'r', encoding='utf-8') as f:
            clusters = json.load(f)
        
        # 检查是否已有配置，如果没有，尝试导入现有kubeconfig文件
        if not clusters:
            # 获取现有kubeconfig文件目录
            kubeconfig_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'kubeconfigs'
            )
            
            # 导入现有kubeconfig文件
            if os.path.exists(kubeconfig_dir):
                for filename in os.listdir(kubeconfig_dir):
                    file_path = os.path.join(kubeconfig_dir, filename)
                    if os.path.isfile(file_path):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                kubeconfig_content = f.read()
                            
                            # 添加到集群配置中
                            new_cluster = {
                                'name': filename,
                                'display_name': filename,
                                'kubeconfig_content': kubeconfig_content
                            }
                            clusters.append(new_cluster)
                        except Exception as e:
                            print(f"Failed to import kubeconfig file {filename}: {e}")
                
                # 如果导入了集群配置，保存到配置文件
                if clusters:
                    with open(self.config_file, 'w', encoding='utf-8') as f:
                        json.dump(clusters, f, ensure_ascii=False, indent=2)
        
        return clusters
    
    def add_cluster(self, cluster_name, display_name, kubeconfig_content):
        """添加集群配置"""
        clusters = self.get_clusters()
        
        # 检查集群名是否已存在
        for cluster in clusters:
            if cluster['name'] == cluster_name:
                return False, '集群名已存在'
        
        # 添加新集群
        new_cluster = {
            'name': cluster_name,
            'display_name': display_name,
            'kubeconfig_content': kubeconfig_content
        }
        clusters.append(new_cluster)
        
        # 保存配置
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(clusters, f, ensure_ascii=False, indent=2)
        
        return True, '集群添加成功'
    
    def update_cluster(self, cluster_name, display_name=None, kubeconfig_content=None):
        """更新集群配置"""
        clusters = self.get_clusters()
        
        # 查找集群
        for cluster in clusters:
            if cluster['name'] == cluster_name:
                if display_name is not None:
                    cluster['display_name'] = display_name
                if kubeconfig_content is not None:
                    cluster['kubeconfig_content'] = kubeconfig_content
                
                # 保存配置
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(clusters, f, ensure_ascii=False, indent=2)
                
                return True, '集群更新成功'
        
        return False, '集群不存在'
    
    def delete_cluster(self, cluster_name):
        """删除集群配置"""
        clusters = self.get_clusters()
        
        # 查找并删除集群
        cluster_found = False
        for i, cluster in enumerate(clusters):
            if cluster['name'] == cluster_name:
                del clusters[i]
                cluster_found = True
                break
        
        if not cluster_found:
            return False, '集群不存在'
        
        # 保存配置
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(clusters, f, ensure_ascii=False, indent=2)
        
        # 删除kubeconfigs目录中的对应文件
        kubeconfig_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'kubeconfigs'
        )
        kubeconfig_file = os.path.join(kubeconfig_dir, cluster_name)
        if os.path.exists(kubeconfig_file):
            try:
                os.remove(kubeconfig_file)
            except Exception as e:
                print(f"Failed to delete kubeconfig file {kubeconfig_file}: {e}")
        
        return True, '集群删除成功'
    
    def get_cluster(self, cluster_name):
        """获取单个集群配置"""
        clusters = self.get_clusters()
        
        for cluster in clusters:
            if cluster['name'] == cluster_name:
                return cluster
        
        return None
