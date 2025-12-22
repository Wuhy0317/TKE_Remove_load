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
        """获取指定集群的命名空间列表及详细信息"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        v1 = k8s_client.get_core_client()
        
        namespaces = []
        try:
            for ns in v1.list_namespace().items:
                # 获取命名空间状态
                status = "Active"
                if ns.status and ns.status.conditions:
                    for condition in ns.status.conditions:
                        if condition.type == "Active":
                            status = condition.status
                            break
                else:
                    status = "Unknown"
                
                # 获取创建时间
                creation_time = ns.metadata.creation_timestamp.isoformat() if ns.metadata.creation_timestamp else ""
                
                namespaces.append({
                    "name": ns.metadata.name,
                    "status": status,
                    "creation_time": creation_time
                })
            return namespaces
        except Exception as e:
            print(f"获取命名空间列表失败: {e}")
            raise
    
    def get_nodes(self, cluster):
        """获取指定集群的节点列表"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        v1 = k8s_client.get_core_client()
        
        nodes = []
        try:
            node_list = v1.list_node()
            for node in node_list.items:
                # 获取节点角色
                role = "worker"
                if node.metadata.labels and "node-role.kubernetes.io/control-plane" in node.metadata.labels:
                    role = "control-plane"
                elif node.metadata.labels and "node-role.kubernetes.io/master" in node.metadata.labels:
                    role = "master"
                
                # 获取节点状态
                status = "NotReady"
                for condition in node.status.conditions:
                    if condition.type == "Ready":
                        status = condition.status
                        break
                
                # 获取节点IP
                internal_ip = ""
                for addr in node.status.addresses:
                    if addr.type == "InternalIP":
                        internal_ip = addr.address
                        break
                
                # 获取节点资源信息
                cpu_allocatable = node.status.allocatable.get("cpu", "0")
                memory_allocatable = node.status.allocatable.get("memory", "0")
                
                # 转换CPU从各种单位到核
                try:
                    if "m" in cpu_allocatable:
                        # 去掉"m"单位，转换为核
                        cpu_cores = float(cpu_allocatable.replace("m", "")) / 1000
                    elif "k" in cpu_allocatable:
                        # 去掉"k"单位，转换为核（1k = 1000，所以除以1000）
                        cpu_cores = float(cpu_allocatable.replace("k", "")) / 1000
                    else:
                        # 已经是核为单位或其他情况
                        cpu_cores = float(cpu_allocatable)
                except (ValueError, TypeError):
                    # 处理转换失败的情况
                    cpu_cores = 0.0
                
                # 转换内存从字节到GiB
                try:
                    if "Ki" in memory_allocatable:
                        memory_bytes = float(memory_allocatable.replace("Ki", "")) * 1024
                    elif "Mi" in memory_allocatable:
                        memory_bytes = float(memory_allocatable.replace("Mi", "")) * 1024 * 1024
                    elif "Gi" in memory_allocatable:
                        memory_bytes = float(memory_allocatable.replace("Gi", "")) * 1024 * 1024 * 1024
                    elif "Ti" in memory_allocatable:
                        memory_bytes = float(memory_allocatable.replace("Ti", "")) * 1024 * 1024 * 1024 * 1024
                    elif "Pi" in memory_allocatable:
                        memory_bytes = float(memory_allocatable.replace("Pi", "")) * 1024 * 1024 * 1024 * 1024 * 1024
                    else:
                        # 假设是字节单位
                        memory_bytes = float(memory_allocatable)
                    
                    # 转换为GiB并保留两位小数
                    memory_gib = round(memory_bytes / (1024 * 1024 * 1024), 2)
                except (ValueError, TypeError):
                    # 处理转换失败的情况
                    memory_gib = 0.0
                
                # 获取操作系统和Kubelet版本
                os_image = node.status.node_info.os_image
                kubelet_version = node.status.node_info.kubelet_version
                
                nodes.append({
                    "name": node.metadata.name,
                    "role": role,
                    "status": status,
                    "internal_ip": internal_ip,
                    "os_image": os_image,
                    "kubelet_version": kubelet_version,
                    "cpu_allocatable": f"{cpu_cores}核",
                    "memory_allocatable": f"{memory_gib}Gi",
                    "creation_timestamp": node.metadata.creation_timestamp.isoformat() if node.metadata.creation_timestamp else ""
                })
        except Exception as e:
            print(f"获取节点列表失败: {e}")
            raise
        
        return nodes
    
    def get_workloads(self, cluster, namespace, workload_type=None):
        """获取指定集群和命名空间的工作负载及详细信息"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        apps_v1 = k8s_client.get_apps_client()
        
        workloads = []
        
        try:
            print(f"开始获取工作负载，集群: {cluster}, 命名空间: {namespace}, 类型: {workload_type}")
            
            # 只获取Deployment、StatefulSet和DaemonSet，跳过Job和CronJob
            # 获取Deployment
            if workload_type == 'deployment' or not workload_type:
                print("获取Deployment...")
                deployments = apps_v1.list_namespaced_deployment(namespace)
                print(f"获取到 {len(deployments.items)} 个Deployment")
                for deploy in deployments.items:
                    # 获取状态
                    status = "Unknown"
                    if deploy.status.available_replicas is not None and deploy.status.available_replicas > 0:
                        status = "Available"
                    elif deploy.status.unavailable_replicas is not None and deploy.status.unavailable_replicas > 0:
                        status = "Unavailable"
                    
                    # 获取资源请求和限制
                    resources = ""
                    if deploy.spec.template.spec.containers and deploy.spec.template.spec.containers[0].resources:
                        container_resources = deploy.spec.template.spec.containers[0].resources
                        cpu_request = container_resources.requests.get('cpu', '0') if container_resources.requests else '0'
                        cpu_limit = container_resources.limits.get('cpu', '0') if container_resources.limits else '0'
                        mem_request = container_resources.requests.get('memory', '0') if container_resources.requests else '0'
                        mem_limit = container_resources.limits.get('memory', '0') if container_resources.limits else '0'
                        resources = f"cpu: {cpu_request}/{cpu_limit}, mem: {mem_request}/{mem_limit}"
                    
                    workloads.append({
                        'name': deploy.metadata.name,
                        'type': 'deployment',
                        'namespace': namespace,
                        'ready_replicas': deploy.status.ready_replicas or 0,
                        'desired_replicas': deploy.spec.replicas or 0,
                        'resources': resources,
                        'creation_time': deploy.metadata.creation_timestamp.isoformat() if deploy.metadata.creation_timestamp else ""
                    })
            
            # 获取StatefulSet
            if workload_type == 'statefulset' or not workload_type:
                print("获取StatefulSet...")
                statefulsets = apps_v1.list_namespaced_stateful_set(namespace)
                print(f"获取到 {len(statefulsets.items)} 个StatefulSet")
                for sts in statefulsets.items:
                    # 获取状态
                    status = "Unknown"
                    if sts.status.ready_replicas is not None and sts.status.ready_replicas > 0:
                        status = "Available"
                    
                    # 获取资源请求和限制
                    resources = ""
                    if sts.spec.template.spec.containers and sts.spec.template.spec.containers[0].resources:
                        container_resources = sts.spec.template.spec.containers[0].resources
                        cpu_request = container_resources.requests.get('cpu', '0') if container_resources.requests else '0'
                        cpu_limit = container_resources.limits.get('cpu', '0') if container_resources.limits else '0'
                        mem_request = container_resources.requests.get('memory', '0') if container_resources.requests else '0'
                        mem_limit = container_resources.limits.get('memory', '0') if container_resources.limits else '0'
                        resources = f"cpu: {cpu_request}/{cpu_limit}, mem: {mem_request}/{mem_limit}"
                    
                    workloads.append({
                        'name': sts.metadata.name,
                        'type': 'statefulset',
                        'namespace': namespace,
                        'ready_replicas': sts.status.ready_replicas or 0,
                        'desired_replicas': sts.spec.replicas or 0,
                        'resources': resources,
                        'creation_time': sts.metadata.creation_timestamp.isoformat() if sts.metadata.creation_timestamp else ""
                    })
            
            # 获取DaemonSet
            if workload_type == 'daemonset' or not workload_type:
                print("获取DaemonSet...")
                daemonsets = apps_v1.list_namespaced_daemon_set(namespace)
                print(f"获取到 {len(daemonsets.items)} 个DaemonSet")
                for ds in daemonsets.items:
                    # 获取状态
                    status = "Unknown"
                    if ds.status.number_ready is not None and ds.status.number_ready > 0:
                        status = "Available"
                    
                    # 获取资源请求和限制
                    resources = ""
                    if ds.spec.template.spec.containers and ds.spec.template.spec.containers[0].resources:
                        container_resources = ds.spec.template.spec.containers[0].resources
                        cpu_request = container_resources.requests.get('cpu', '0') if container_resources.requests else '0'
                        cpu_limit = container_resources.limits.get('cpu', '0') if container_resources.limits else '0'
                        mem_request = container_resources.requests.get('memory', '0') if container_resources.requests else '0'
                        mem_limit = container_resources.limits.get('memory', '0') if container_resources.limits else '0'
                        resources = f"cpu: {cpu_request}/{cpu_limit}, mem: {mem_request}/{mem_limit}"
                    
                    workloads.append({
                        'name': ds.metadata.name,
                        'type': 'daemonset',
                        'namespace': namespace,
                        'ready_replicas': ds.status.number_ready or 0,
                        'desired_replicas': ds.status.desired_number_scheduled or 0,
                        'resources': resources,
                        'creation_time': ds.metadata.creation_timestamp.isoformat() if ds.metadata.creation_timestamp else ""
                    })
        except Exception as e:
            print(f"获取工作负载列表失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        print(f"获取工作负载完成，共 {len(workloads)} 个工作负载")
        return workloads
    
    def get_pods(self, cluster, namespace, workload_type=None, workload_name=None):
        """获取指定工作负载的Pod列表或所有Pod"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        core_v1 = k8s_client.get_core_client()
        apps_v1 = k8s_client.get_apps_client()
        
        selector = ''
        
        if workload_type and workload_name:
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
        
        # 获取Pod列表
        if selector:
            pods = core_v1.list_namespaced_pod(namespace, label_selector=selector)
        else:
            # 获取所有Pod
            pods = core_v1.list_namespaced_pod(namespace)
        
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
            
            # 获取重启次数
            restart_count = 0
            if pod.status.container_statuses:
                for container_status in pod.status.container_statuses:
                    restart_count += container_status.restart_count
            
            pod_list.append({
                'name': pod.metadata.name,
                'namespace': namespace,
                'status': pod.status.phase,
                'node_ip': node_ip,
                'pod_ip': pod.status.pod_ip,
                'created_time': created_time,
                'running_time': running_time,
                'restart_count': restart_count,
                'has_removeload': has_removeload,
                'labels': pod.metadata.labels or {}
            })
        
        return pod_list
    
    def get_workload_yaml(self, cluster, namespace, name, workload_type):
        """获取指定工作负载的YAML配置"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        apps_v1 = k8s_client.get_apps_client()
        
        try:
            if workload_type == 'deployment':
                # 获取Deployment的YAML
                workload = apps_v1.read_namespaced_deployment(name, namespace)
            elif workload_type == 'statefulset':
                # 获取StatefulSet的YAML
                workload = apps_v1.read_namespaced_stateful_set(name, namespace)
            elif workload_type == 'daemonset':
                # 获取DaemonSet的YAML
                workload = apps_v1.read_namespaced_daemon_set(name, namespace)
            else:
                raise ValueError(f"不支持的工作负载类型: {workload_type}")
            
            # 使用kubernetes.client.ApiClient的serialize方法将对象转换为YAML
            api_client = kubernetes.client.ApiClient()
            workload_dict = api_client.sanitize_for_serialization(workload)
            import yaml
            return yaml.dump(workload_dict)
        except Exception as e:
            print(f"获取工作负载YAML失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
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
    
    def get_services(self, cluster, namespace, service_type=None):
        """获取指定集群和命名空间的服务列表及详细信息"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        core_v1 = k8s_client.get_core_client()
        networking_v1 = k8s_client.get_networking_client()
        
        services = []
        
        try:
            # 获取Service
            if service_type == 'service' or not service_type:
                service_list = core_v1.list_namespaced_service(namespace)
                for service in service_list.items:
                    # 获取服务状态
                    status = "Ready"
                    if service.status.load_balancer.ingress is None or len(service.status.load_balancer.ingress) == 0:
                        status = "Pending"
                    
                    # 格式化端口信息
                    ports = []
                    for port in service.spec.ports:
                        ports.append(f"{port.port}:{port.target_port}")
                    ports_str = ", ".join(ports)
                    
                    services.append({
                        'name': service.metadata.name,
                        'type': 'Service',
                        'namespace': namespace,
                        'ip': service.spec.cluster_ip,
                        'ports': ports_str,
                        'status': status,
                        'creation_time': service.metadata.creation_timestamp.isoformat() if service.metadata.creation_timestamp else ""
                    })
            
            # 获取Ingress
            if service_type == 'ingress' or not service_type:
                ingress_list = networking_v1.list_namespaced_ingress(namespace)
                for ingress in ingress_list.items:
                    # 获取Ingress状态
                    status = "Ready"
                    if not ingress.status.load_balancer.ingress:
                        status = "Pending"
                    
                    # 格式化端口信息
                    ports = []
                    for rule in ingress.spec.rules:
                        for path in rule.http.paths:
                            ports.append(f"{path.path} -> {path.backend.service.name}:{path.backend.service.port.number}")
                    ports_str = ", ".join(ports)
                    
                    # 获取Ingress IP
                    ingress_ip = "-"
                    if ingress.status.load_balancer.ingress:
                        ingress_ip = ingress.status.load_balancer.ingress[0].ip or ingress.status.load_balancer.ingress[0].hostname or "-"
                    
                    services.append({
                        'name': ingress.metadata.name,
                        'type': 'Ingress',
                        'namespace': namespace,
                        'ip': ingress_ip,
                        'ports': ports_str,
                        'status': status,
                        'creation_time': ingress.metadata.creation_timestamp.isoformat() if ingress.metadata.creation_timestamp else ""
                    })
        except Exception as e:
            print(f"获取服务与路由列表失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        return services
    
    def get_service_yaml(self, cluster, namespace, name, service_type):
        """获取指定服务或路由的YAML配置"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        
        try:
            if service_type == 'Service':
                # 获取Service的YAML
                core_v1 = k8s_client.get_core_client()
                service = core_v1.read_namespaced_service(name, namespace)
                # 使用kubernetes.client.ApiClient的serialize方法将对象转换为YAML
                api_client = kubernetes.client.ApiClient()
                service_dict = api_client.sanitize_for_serialization(service)
                import yaml
                return yaml.dump(service_dict)
            elif service_type == 'Ingress':
                # 获取Ingress的YAML
                networking_v1 = k8s_client.get_networking_client()
                ingress = networking_v1.read_namespaced_ingress(name, namespace)
                # 使用kubernetes.client.ApiClient的serialize方法将对象转换为YAML
                api_client = kubernetes.client.ApiClient()
                ingress_dict = api_client.sanitize_for_serialization(ingress)
                import yaml
                return yaml.dump(ingress_dict)
            else:
                raise ValueError(f"不支持的服务类型: {service_type}")
        except Exception as e:
            print(f"获取服务YAML失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_cluster_version(self, cluster):
        """获取指定集群的版本信息"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        version_client = k8s_client.get_version_client()
        
        try:
            version_info = version_client.get_code()
            return {
                'major': version_info.major,
                'minor': version_info.minor,
                'git_version': version_info.git_version
            }
        except Exception as e:
            print(f"Failed to get cluster version for {cluster}: {e}")
            return {
                'major': '0',
                'minor': '0',
                'git_version': 'Unknown'
            }
    
    def get_configs(self, cluster, namespace, config_type=None):
        """获取指定集群和命名空间的配置资源"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        core_v1 = k8s_client.get_core_client()
        
        configs = []
        
        try:
            # 获取ConfigMap
            if config_type == 'configmap' or not config_type:
                configmap_list = core_v1.list_namespaced_config_map(namespace)
                for configmap in configmap_list.items:
                    # 计算数据项数量
                    data_count = len(configmap.data) if configmap.data else 0
                    
                    configs.append({
                        'name': configmap.metadata.name,
                        'type': 'ConfigMap',
                        'namespace': namespace,
                        'data_count': data_count,
                        'creation_time': configmap.metadata.creation_timestamp.isoformat() if configmap.metadata.creation_timestamp else ""
                    })
            
            # 获取Secret
            if config_type == 'secret' or not config_type:
                secret_list = core_v1.list_namespaced_secret(namespace)
                for secret in secret_list.items:
                    # 计算数据项数量
                    data_count = len(secret.data) if secret.data else 0
                    
                    configs.append({
                        'name': secret.metadata.name,
                        'type': 'Secret',
                        'namespace': namespace,
                        'data_count': data_count,
                        'creation_time': secret.metadata.creation_timestamp.isoformat() if secret.metadata.creation_timestamp else ""
                    })
        except Exception as e:
            print(f"获取配置资源列表失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        return configs
    
    def get_config_yaml(self, cluster, namespace, name, config_type):
        """获取指定配置资源的YAML配置"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        core_v1 = k8s_client.get_core_client()
        
        try:
            if config_type == 'ConfigMap':
                # 获取ConfigMap的YAML
                config = core_v1.read_namespaced_config_map(name, namespace)
            elif config_type == 'Secret':
                # 获取Secret的YAML
                config = core_v1.read_namespaced_secret(name, namespace)
            else:
                raise ValueError(f"不支持的配置资源类型: {config_type}")
            
            # 使用kubernetes.client.ApiClient的serialize方法将对象转换为YAML
            api_client = kubernetes.client.ApiClient()
            config_dict = api_client.sanitize_for_serialization(config)
            import yaml
            return yaml.dump(config_dict)
        except Exception as e:
            print(f"获取配置资源YAML失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_storage(self, cluster, namespace, storage_type=None):
        """获取指定集群和命名空间的存储资源"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        core_v1 = k8s_client.get_core_client()
        storage_v1 = k8s_client.get_storage_client()
        
        storage = []
        
        try:
            # 获取PersistentVolumeClaim
            if storage_type == 'pvc' or not storage_type:
                pvc_list = core_v1.list_namespaced_persistent_volume_claim(namespace)
                for pvc in pvc_list.items:
                    # 获取容量信息
                    capacity = pvc.status.capacity.get('storage', '') if pvc.status.capacity else ''
                    
                    # 获取状态
                    status = pvc.status.phase or 'Unknown'
                    
                    storage.append({
                        'name': pvc.metadata.name,
                        'type': 'PersistentVolumeClaim',
                        'namespace': namespace,
                        'capacity': capacity,
                        'status': status,
                        'creation_time': pvc.metadata.creation_timestamp.isoformat() if pvc.metadata.creation_timestamp else ""
                    })
            
            # 获取PersistentVolume
            if storage_type == 'pv' or not storage_type:
                pv_list = core_v1.list_persistent_volume()
                for pv in pv_list.items:
                    # 获取容量信息
                    capacity = pv.spec.capacity.get('storage', '') if pv.spec.capacity else ''
                    
                    # 获取状态
                    status = pv.status.phase or 'Unknown'
                    
                    storage.append({
                        'name': pv.metadata.name,
                        'type': 'PersistentVolume',
                        'namespace': pv.spec.claim_ref.namespace if pv.spec.claim_ref else '',
                        'capacity': capacity,
                        'status': status,
                        'creation_time': pv.metadata.creation_timestamp.isoformat() if pv.metadata.creation_timestamp else ""
                    })
            
            # 获取StorageClass
            if storage_type == 'storageclass' or not storage_type:
                sc_list = storage_v1.list_storage_class()
                for sc in sc_list.items:
                    # StorageClass没有容量和命名空间，设置为空
                    storage.append({
                        'name': sc.metadata.name,
                        'type': 'StorageClass',
                        'namespace': '',
                        'capacity': '',
                        'status': 'Available',
                        'creation_time': sc.metadata.creation_timestamp.isoformat() if sc.metadata.creation_timestamp else ""
                    })
        except Exception as e:
            print(f"获取存储资源列表失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        return storage
    
    def get_storage_yaml(self, cluster, namespace, name, storage_type):
        """获取指定存储资源的YAML配置"""
        k8s_client = K8sClient(cluster, self.kubeconfig_dir)
        core_v1 = k8s_client.get_core_client()
        storage_v1 = k8s_client.get_storage_client()
        
        try:
            if storage_type == 'PersistentVolumeClaim':
                # 获取PersistentVolumeClaim的YAML
                storage_resource = core_v1.read_namespaced_persistent_volume_claim(name, namespace)
            elif storage_type == 'PersistentVolume':
                # 获取PersistentVolume的YAML
                storage_resource = core_v1.read_persistent_volume(name)
            elif storage_type == 'StorageClass':
                # 获取StorageClass的YAML
                storage_resource = storage_v1.read_storage_class(name)
            else:
                raise ValueError(f"不支持的存储资源类型: {storage_type}")
            
            # 使用kubernetes.client.ApiClient的serialize方法将对象转换为YAML
            api_client = kubernetes.client.ApiClient()
            storage_dict = api_client.sanitize_for_serialization(storage_resource)
            import yaml
            return yaml.dump(storage_dict)
        except Exception as e:
            print(f"获取存储资源YAML失败: {e}")
            import traceback
            traceback.print_exc()
            raise
