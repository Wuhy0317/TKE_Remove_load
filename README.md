# TKE_Remove_load

一个用于在K8s集群内管理Pod负载的工具，通过增删Pod标签实现踢出和恢复负载的功能。

## 功能特点

- 支持多个K8s集群管理
- 可视化界面操作，简单易用
- 支持选择集群、命名空间、工作负载类型、工作负载
- 支持踢出Pod负载（添加`removeload: yes`标签）
- 支持恢复Pod流量（移除`removeload`标签）
- 实时显示Pod状态和是否已踢出负载

## 技术栈

- **后端**：Python、Flask、Kubernetes Python Client
- **前端**：HTML、CSS、JavaScript

## 目录结构

```
TKE_Remove_load/
├── app/                 # 应用核心代码
│   ├── api/            # API路由层
│   │   ├── __init__.py
│   │   └── k8s.py      # K8s相关API路由
│   ├── config/         # 配置文件
│   │   └── config.py   # 应用配置
│   ├── services/       # 业务逻辑层
│   │   └── k8s_service.py  # K8s服务逻辑
│   ├── utils/          # 工具类
│   │   └── k8s_client.py   # K8s客户端工具
│   └── __init__.py     # 应用初始化
├── kubeconfigs/        # K8s集群配置文件目录
├── static/             # 静态资源
│   └── index.html      # 前端页面
├── app.py              # 应用入口
└── requirements.txt    # 依赖项
```

## 安装和使用

### 1. 准备K8s集群配置文件

将各个K8s集群的kube-config文件放入`kubeconfigs`目录，文件名格式为`<cluster_name>.yaml`或`<cluster_name>.yml`。

### 2. 安装依赖

```bash
pip3 install -r requirements.txt --break-system-packages
```

### 3. 运行应用

```bash
python3 app.py
```

### 4. 访问应用

在浏览器中访问：http://127.0.0.1:5000

## 使用说明

1. **选择集群**：从下拉菜单中选择要操作的K8s集群
2. **选择命名空间**：选择要操作的命名空间
3. **选择工作负载类型**：可选全部类型、Deployment、StatefulSet或DaemonSet
4. **选择工作负载**：选择要操作的具体工作负载
5. **查看Pod列表**：显示该工作负载下的所有Pod
6. **踢出负载**：点击对应Pod的"踢出负载"按钮，添加`removeload: yes`标签
7. **恢复流量**：点击对应Pod的"恢复流量"按钮，移除`removeload`标签

## 实现原理

1. 当需要踢出Pod负载时，向Pod添加标签`removeload: yes`
2. Service通过标签选择器匹配Pod，当Pod添加了`removeload: yes`标签后，与Service的标签选择器不匹配
3. Service自动从Endpoints中移除该Pod，实现踢出负载的目的
4. 恢复流量时，移除Pod的`removeload`标签，使Pod重新匹配Service的标签选择器
5. Service自动将Pod添加回Endpoints，恢复流量

## 注意事项

1. 确保kube-config文件具有足够的权限操作Pod标签
2. 建议在测试环境中先进行测试，再在生产环境中使用
3. 该工具仅负责管理Pod标签，不直接操作Service
4. 确保Service的标签选择器不包含`removeload`标签

## 开发说明

### 项目架构

- **API层**：处理HTTP请求和响应，调用服务层处理业务逻辑
- **服务层**：实现核心业务逻辑，调用工具类与K8s API交互
- **工具层**：封装K8s API调用，提供简洁的接口
- **配置层**：集中管理应用配置

### 扩展建议

1. 添加用户认证和授权机制
2. 支持更多工作负载类型
3. 添加日志记录功能
4. 支持批量操作Pod
5. 添加监控和告警功能

## 许可证

MIT License
