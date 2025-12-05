from app.utils.k8s_client import K8sClient
from app.config.config import Config
import os
import glob
import kubernetes.client

class K8sService:
    """Kubernetes服务层，处理业务逻辑"""
    
    def __init__(self, kubeconfig_dir):
        """
        初始化K8s服务
        
        Args:
            kubeconfig_dir: kubeconfig文件目录
        """
        self.kubeconfig_dir = kubeconfig_dir
    
    def get_namespaces(self, cluster):
        """获取指定集群的命名空间"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        v1 = k8s_client.get_core_client()
        
        namespaces = []
        for ns in v1.list_namespace().items:
            namespaces.append(ns.metadata.name)
        return namespaces
    
    def get_workloads(self, cluster, namespace, workload_type=None):
        """获取指定集群和命名空间的工作负载"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        apps_v1 = k8s_client.get_apps_client()
        
        workloads = []
        
        # 获取Deployment
        if workload_type == 'deployment' or not workload_type:
            for deploy in apps_v1.list_namespaced_deployment(namespace).items:
                workloads.append({
                    'name': deploy.metadata.name,
                    'type': 'deployment',
                    'replicas': deploy.status.available_replicas or 0
                })
        
        # 获取StatefulSet
        if workload_type == 'statefulset' or not workload_type:
            for sts in apps_v1.list_namespaced_stateful_set(namespace).items:
                workloads.append({
                    'name': sts.metadata.name,
                    'type': 'statefulset',
                    'replicas': sts.status.ready_replicas or 0
                })
        
        # 获取DaemonSet
        if workload_type == 'daemonset' or not workload_type:
            for ds in apps_v1.list_namespaced_daemon_set(namespace).items:
                workloads.append({
                    'name': ds.metadata.name,
                    'type': 'daemonset',
                    'replicas': ds.status.number_ready or 0
                })
        
        return workloads
    
    def get_pods(self, cluster, namespace, workload_type, workload_name):
        """获取指定工作负载的Pod列表"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        core_v1 = k8s_client.get_core_client()
        apps_v1 = k8s_client.get_apps_client()
        
        selector = ''
        # 根据工作负载类型获取选择器
        if workload_type == 'deployment':
            deploy = apps_v1.read_namespaced_deployment(workload_name, namespace)
            selector = ','.join([f'{k}={v}' for k, v in deploy.spec.selector.match_labels.items()])
        elif workload_type == 'statefulset':
            sts = apps_v1.read_namespaced_stateful_set(workload_name, namespace)
            selector = ','.join([f'{k}={v}' for k, v in sts.spec.selector.match_labels.items()])
        elif workload_type == 'daemonset':
            ds = apps_v1.read_namespaced_daemon_set(workload_name, namespace)
            selector = ','.join([f'{k}={v}' for k, v in ds.spec.selector.match_labels.items()])
        
        if not selector:
            return []
        
        # 获取Pod列表
        pods = core_v1.list_namespaced_pod(namespace, label_selector=selector)
        pod_list = []
        for pod in pods.items:
            # 判断是否已踢出负载：load标签值为done表示已踢出
            has_removeload = pod.metadata.labels and Config.LOAD_LABEL in pod.metadata.labels and pod.metadata.labels[Config.LOAD_LABEL] == Config.LOAD_DONE_VALUE
            
            # 获取真实的节点IP地址
            node_ip = pod.spec.node_name  # 默认使用节点名称
            try:
                # 读取节点信息
                node = core_v1.read_node(pod.spec.node_name)
                # 遍历节点地址，找到InternalIP
                for addr in node.status.addresses:
                    if addr.type == 'InternalIP':
                        node_ip = addr.address
                        break
            except Exception as e:
                print(f"Failed to get node IP for {pod.spec.node_name}: {e}")
            
            import datetime
            
            # 获取创建时间，并转换为UTC+8时间
            created_time = '-'            
            if pod.metadata.creation_timestamp:
                # Kubernetes API返回的是UTC时间，需要转换为UTC+8
                utc_time = pod.metadata.creation_timestamp
                # 设置时区为UTC+8
                utc8_time = utc_time + datetime.timedelta(hours=8)
                created_time = utc8_time.strftime('%Y-%m-%d %H:%M:%S')            
            
            # 计算运行时间
            running_time = '-'            
            if pod.status.start_time:
                start_time = pod.status.start_time
                current_time = datetime.datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.datetime.now()
                delta = current_time - start_time
                # 格式化运行时间为 天:时:分:秒
                days = delta.days
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                running_time = f'{days}d {hours}h {minutes}m {seconds}s'            
            
            pod_list.append({
                'name': pod.metadata.name,
                'status': pod.status.phase,
                'node_ip': node_ip,
                'pod_ip': pod.status.pod_ip,
                'created_time': created_time,
                'running_time': running_time,
                'has_removeload': has_removeload,
                'labels': pod.metadata.labels or {}
            })
        
        return pod_list
    
    def remove_load(self, cluster, namespace, pod_name):
        """踢出Pod负载"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        core_v1 = k8s_client.get_core_client()
        
        # 使用Strategic Merge Patch修改标签：将load:online改为load:done
        body = {
            "metadata": {
                "labels": {
                    Config.LOAD_LABEL: Config.LOAD_DONE_VALUE
                }
            }
        }
        
        # 更新Pod
        core_v1.patch_namespaced_pod(
            pod_name, 
            namespace, 
            body=body
        )
        
        return {
            'success': True,
            'message': f'Pod {pod_name} 已踢出负载'
        }
    
    def restore_traffic(self, cluster, namespace, pod_name):
        """恢复Pod流量"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        core_v1 = k8s_client.get_core_client()
        
        # 使用Strategic Merge Patch修改标签：将load:done改回load:online
        body = {
            "metadata": {
                "labels": {
                    Config.LOAD_LABEL: Config.LOAD_ONLINE_VALUE
                }
            }
        }
        
        # 更新Pod
        core_v1.patch_namespaced_pod(
            pod_name, 
            namespace, 
            body=body
        )
        
        return {
            'success': True,
            'message': f'Pod {pod_name} 已恢复流量'
        }
