# K8s Pod负载管理工具

一个基于Flask和Kubernetes API的K8s Pod负载管理工具，支持多集群管理、用户认证、权限控制和Pod负载踢出/恢复功能。

## 功能特性

### 核心功能
- ✅ **多集群管理**：支持管理多个Kubernetes集群
- ✅ **Pod负载管理**：支持踢出Pod负载和恢复流量
- ✅ **节点IP显示**：显示真实节点IP而非节点名称
- ✅ **Pod信息展示**：显示Pod名称、状态、节点IP、Pod IP、创建时间、运行时间等
- ✅ **集群名称映射**：支持自定义集群显示名称

### 认证与权限
- ✅ **用户认证**：基于用户名密码的认证机制
- ✅ **权限管理**：支持三级权限（admin、read、write）
- ✅ **集群级权限**：支持基于集群的访问控制
- ✅ **操作日志**：记录用户操作日志
- ✅ **自动登出**：10分钟不活动自动登出

### 管理功能
- ✅ **集群管理**：添加、编辑、删除集群配置
- ✅ **用户管理**：添加、编辑、删除用户，配置权限
- ✅ **日志管理**：查看操作日志

### 部署支持
- ✅ **Docker支持**：提供Dockerfile，支持容器化部署
- ✅ **Kubernetes支持**：提供K8s部署文件
- ✅ **配置持久化**：支持配置文件持久化存储

## 项目结构

```
.
├── app/                  # 应用主目录
│   ├── __init__.py       # 应用初始化
│   ├── api/              # API路由
│   │   ├── __init__.py
│   │   └── k8s.py        # K8s相关API
│   ├── config/           # 配置文件
│   │   └── config.py     # 应用配置
│   ├── services/         # 业务逻辑层
│   │   └── k8s_service.py # K8s服务
│   └── utils/            # 工具类
│       ├── auth_manager.py   # 认证管理器
│       ├── cluster_manager.py # 集群管理器
│       ├── k8s_client.py      # K8s客户端
│       └── log_manager.py     # 日志管理器
├── config/               # 配置文件目录
│   ├── auth_config.json  # 用户认证配置
│   ├── cluster_configs.json # 集群配置
│   └── logs.json         # 操作日志
├── static/               # 静态资源
│   ├── admin.html        # 管理后台页面
│   ├── index.html        # 主页面
│   └── login.html        # 登录页面
├── kubeconfigs/          # Kubeconfig文件目录
├── app.py                # 应用入口
├── Dockerfile            # Docker构建文件
├── deployment.yaml       # Kubernetes部署文件
├── requirements.txt      # 依赖列表
└── README.md             # 项目文档
```

## 安装与部署

### 1. 本地安装

#### 环境要求
- Python 3.11+
- pip

#### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd k8s-pod-manager
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 启动应用
```bash
python app.py
```

4. 访问应用
```
http://localhost:5000
```

### 2. Docker部署

1. 构建镜像
```bash
docker build -t k8s-pod-manager:latest .
```

2. 运行容器
```bash
docker run -d -p 5000:5000 --name k8s-pod-manager \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/kubeconfigs:/app/kubeconfigs \
  k8s-pod-manager:latest
```

### 3. Kubernetes部署

1. 应用部署
```bash
kubectl apply -f deployment.yaml
```

2. 访问应用
```
http://<node-ip>:30007
```

## 使用说明

### 1. 登录系统

- 访问 `http://localhost:5000`
- 使用默认用户名密码登录：
  - 管理员：admin/admin123
  - 普通用户：user/user123

### 2. 添加集群

1. 登录管理员账号
2. 点击"集群管理后台"进入管理页面
3. 切换到"集群管理"标签
4. 点击"添加集群"按钮
5. 填写集群名称、显示名称和Kubeconfig内容
6. 点击"保存"按钮

### 3. 管理Pod负载

1. 从集群下拉列表中选择一个集群
2. 选择命名空间和工作负载
3. 在Pod列表中，点击"踢出负载"按钮将Pod从负载均衡中移除
4. 点击"恢复流量"按钮将Pod重新加入负载均衡

### 4. 用户管理

1. 登录管理员账号
2. 进入管理后台，切换到"用户管理"标签
3. 点击"添加用户"按钮添加新用户
4. 设置用户名、密码和权限
5. 点击"保存"按钮

## 配置说明

### 1. 应用配置（app/config/config.py）

- `LOAD_LABEL`：负载标签名称（默认：`load`）
- `LOAD_DONE_VALUE`：踢出负载后的值（默认：`done`）
- `LOAD_ONLINE_VALUE`：恢复流量后的值（默认：`online`）

### 2. 用户配置（config/auth_config.json）

```json
[
  {
    "username": "admin",
    "password_hash": "...",
    "permissions": {
      "admin": true,
      "read": true,
      "write": true,
      "clusters": {}
    }
  }
]
```

### 3. 集群配置（config/cluster_configs.json）

```json
[
  {
    "name": "cluster-1",
    "display_name": "开发集群",
    "kubeconfig_content": "apiVersion: v1\nclusters: [...]"
  }
]
```

## API文档

### 1. 认证相关

- `POST /api/login`：用户登录
- `POST /api/logout`：用户登出
- `GET /api/current-user`：获取当前用户信息

### 2. 集群相关

- `GET /api/clusters`：获取集群列表
- `GET /api/{cluster}/namespaces`：获取命名空间列表
- `GET /api/{cluster}/{namespace}/workloads`：获取工作负载列表
- `GET /api/{cluster}/{namespace}/{workload_type}/{workload_name}/pods`：获取Pod列表

### 3. Pod操作

- `POST /api/{cluster}/{namespace}/pods/{pod_name}/remove-load`：踢出负载
- `POST /api/{cluster}/{namespace}/pods/{pod_name}/restore-traffic`：恢复流量

### 4. 管理后台API

- `GET /api/admin/clusters`：获取集群列表（管理）
- `POST /api/admin/clusters`：添加集群（管理）
- `PUT /api/admin/clusters/{cluster_name}`：更新集群（管理）
- `DELETE /api/admin/clusters/{cluster_name}`：删除集群（管理）
- `GET /api/admin/users`：获取用户列表（管理）
- `POST /api/admin/users`：添加用户（管理）
- `PUT /api/admin/users/{username}`：更新用户（管理）
- `DELETE /api/admin/users/{username}`：删除用户（管理）

## 负载管理原理

该工具通过修改Pod的标签来实现负载管理：

1. **踢出负载**：将Pod的`load`标签设置为`done`
2. **恢复流量**：将Pod的`load`标签设置为`online`

需要确保Kubernetes集群中的负载均衡器（如Service）配置了相应的标签选择器，只将`load: online`的Pod包含在负载均衡中。

## 权限模型

1. **管理员权限**：
   - 拥有所有集群的所有权限
   - 可以管理用户和集群
   - 可以查看操作日志

2. **读写权限**：
   - 可以查看所有集群和Pod信息
   - 可以执行踢出负载和恢复流量操作

3. **只读权限**：
   - 只能查看集群和Pod信息
   - 不能执行操作

4. **集群级权限**：
   - 可以配置用户只能访问特定集群
   - 基于集群名称进行权限控制

## 开发说明

### 开发环境设置

1. 安装开发依赖
```bash
pip install -r requirements.txt
```

2. 启动开发服务器
```bash
flask run --debug
```

3. 访问开发服务器
```
http://localhost:5000
```

### 代码风格

- 使用4空格缩进
- 遵循PEP 8规范
- 使用类型提示
- 编写清晰的注释

## 监控与日志

### 1. 操作日志

- 登录日志：记录用户登录成功/失败情况
- 操作日志：记录用户执行的操作，包括踢出负载、恢复流量、添加用户、管理集群等
- 日志存储在`config/logs.json`文件中

### 2. 错误处理

- 全局错误处理机制
- 友好的错误提示
- 详细的错误日志记录

## 安全考虑

1. **密码安全**：
   - 使用SHA-256哈希存储密码
   - 禁止明文传输密码

2. **权限控制**：
   - 基于角色的访问控制
   - 细粒度的权限检查
   - 集群级别的访问控制

3. **会话管理**：
   - 安全的会话机制
   - 自动登出功能
   - 会话超时控制

4. **输入验证**：
   - 严格的输入验证
   - 防止SQL注入和XSS攻击
   - 限制请求大小和频率

## 常见问题

### 1. 为什么无法删除集群？

**原因**：集群配置被删除后，系统会自动从`kubeconfigs`目录重新导入。

**解决方案**：同时删除`kubeconfigs`目录中的对应文件。

### 2. 如何修改默认用户名密码？

**方法**：
1. 登录管理后台
2. 进入用户管理页面
3. 编辑对应的用户
4. 设置新密码
5. 保存修改

### 3. 如何配置负载均衡器识别load标签？

**示例**：在Service的标签选择器中添加`load: online`条件

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: my-app
    load: online
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
```

## 版本历史

- v1.0.0：初始版本
  - 支持多集群管理
  - 支持Pod负载踢出和恢复
  - 支持用户认证和权限管理
  - 提供Web管理界面
  - 支持Docker和Kubernetes部署

## 贡献指南

1. Fork项目
2. 创建特性分支
3. 提交代码
4. 创建Pull Request

## 许可证

MIT License

## 联系方式

如有问题或建议，请通过以下方式联系：

- 项目地址：<repository-url>
- 问题反馈：<issue-url>

---

**K8s Pod负载管理工具** - 简化Kubernetes集群的Pod负载管理
