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
│   ├── index.html        # 主页面（含管理功能）
│   └── login.html        # 登录页面
├── app.py                # 应用入口
├── cookies.txt           # Cookies存储文件
├── Dockerfile            # Docker构建文件
├── deployment.yaml       # Kubernetes部署文件
├── requirements.txt      # 依赖列表
├── user_cookies.txt      # 用户Cookies存储文件
└── README.md             # 项目文档
```

## 安装与部署

### 1. 本地安装

#### 环境要求
- Python 3.11+
- pip 23.0+

#### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd TKE_Remove_load
```

2. 创建并激活虚拟环境（推荐）
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境（macOS/Linux）
source venv/bin/activate

# 激活虚拟环境（Windows）
# venv\Scripts\activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

#### 主要依赖
- Flask 3.0.3：Web框架
- kubernetes 29.0.0：Kubernetes API客户端
- python-dotenv 1.0.1：环境变量管理
- flask-cors 4.0.1：跨域资源共享支持

4. 启动应用
```bash
# 在虚拟环境中
python app.py

# 或直接使用python3
python3 app.py
```

5. 访问应用
```
http://localhost:5000
```

6. 退出虚拟环境
```bash
deactivate
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
  -e FLASK_ENV=production \
  k8s-pod-manager:latest
```

### 3. Kubernetes部署

1. 应用部署
```bash
kubectl apply -f deployment.yaml
```

2. 部署说明
- 部署包含一个Pod实例，使用NodePort服务暴露在30007端口
- 配置文件使用PersistentVolumeClaim持久化存储
- 包含默认的ConfigMap配置，用于初始启动

3. 访问应用
```
http://<node-ip>:30007
```

4. 自定义配置
- 可以通过修改deployment.yaml中的环境变量来自定义配置
- 可以通过更新ConfigMap来修改初始配置

## 使用说明

### 1. 登录系统

- 访问 `http://localhost:5000` 或 `http://<node-ip>:30007`（Kubernetes部署）
- 使用默认用户名密码登录：
  - 管理员：admin/admin123
  - 普通用户：user/user123

### 2. 添加集群

1. 登录管理员账号
2. 在主页面右上角点击"管理后台"进入管理页面
3. 切换到"集群管理"标签
4. 点击"添加集群"按钮
5. 填写集群名称、显示名称和Kubeconfig内容
6. 点击"保存"按钮，系统会自动验证Kubeconfig的有效性

### 3. 管理Pod负载

1. 从集群下拉列表中选择一个集群
2. 选择命名空间和工作负载类型（Deployment、StatefulSet等）
3. 选择具体的工作负载
4. 在Pod列表中，点击"踢出负载"按钮将Pod从负载均衡中移除
5. 点击"恢复流量"按钮将Pod重新加入负载均衡
6. 查看Pod状态、节点IP、运行时间等详细信息

### 4. 用户管理

1. 登录管理员账号
2. 进入管理后台，切换到"用户管理"标签
3. 点击"添加用户"按钮添加新用户
4. 设置用户名、密码和权限级别（admin、read、write）
5. 配置集群级权限（可选）
6. 点击"保存"按钮

### 5. 日志管理

1. 登录管理员账号
2. 进入管理后台，切换到"日志管理"标签
3. 查看操作日志，包括：
   - 用户登录/登出记录
   - Pod负载管理操作
   - 集群管理操作
   - 用户管理操作
4. 根据时间范围和操作类型筛选日志

### 6. 集群监控

- 实时查看集群中所有Pod的状态
- 监控Pod的运行时间和创建时间
- 快速识别异常状态的Pod
- 查看Pod所在的真实节点IP

## 配置说明

### 1. 应用配置（app/config/config.py）

| 配置项 | 说明 | 默认值 |
|---------|------|--------|
| `KUBECONFIG_DIR` | Kubeconfig文件存储目录 | `kubeconfigs` |
| `DEBUG` | Flask调试模式 | `True` |
| `SECRET_KEY` | Flask密钥，用于加密会话 | `dev-secret-key` |
| `API_PREFIX` | API路由前缀 | `/api` |
| `LOAD_LABEL` | 负载标签名称，用于标识Pod是否接收流量 | `load` |
| `LOAD_ONLINE_VALUE` | 正常接收流量的标签值 | `online` |
| `LOAD_DONE_VALUE` | 踢出负载后的标签值 | `done` |

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

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/login` | 用户登录，返回用户信息和权限 | 公开 |
| POST | `/api/logout` | 用户登出，清除会话 | 已登录 |
| GET | `/api/current-user` | 获取当前用户信息和权限 | 已登录 |

### 2. 集群相关

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| GET | `/api/clusters` | 获取集群列表 | 已登录 |
| GET | `/api/{cluster}/namespaces` | 获取指定集群的命名空间列表 | 已登录 |
| GET | `/api/{cluster}/{namespace}/workload-types` | 获取工作负载类型列表 | 已登录 |
| GET | `/api/{cluster}/{namespace}/workloads` | 获取指定命名空间的工作负载列表 | 已登录 |
| GET | `/api/{cluster}/{namespace}/{workload_type}/{workload_name}/pods` | 获取指定工作负载的Pod列表 | 已登录 |

### 3. Pod操作

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/{cluster}/{namespace}/pods/{pod_name}/remove-load` | 踢出Pod负载，设置load标签为done | write |
| POST | `/api/{cluster}/{namespace}/pods/{pod_name}/restore-traffic` | 恢复Pod流量，设置load标签为online | write |

### 4. 管理后台API

#### 集群管理

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| GET | `/api/admin/clusters` | 获取集群列表（管理） | admin |
| POST | `/api/admin/clusters` | 添加集群（管理） | admin |
| PUT | `/api/admin/clusters/{cluster_name}` | 更新集群（管理） | admin |
| DELETE | `/api/admin/clusters/{cluster_name}` | 删除集群（管理） | admin |

#### 用户管理

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| GET | `/api/admin/users` | 获取用户列表（管理） | admin |
| POST | `/api/admin/users` | 添加用户（管理） | admin |
| PUT | `/api/admin/users/{username}` | 更新用户（管理） | admin |
| DELETE | `/api/admin/users/{username}` | 删除用户（管理） | admin |

#### 日志管理

| 方法 | 端点 | 描述 | 权限 |
|------|------|------|------|
| GET | `/api/admin/logs` | 获取操作日志（管理） | admin |
| GET | `/api/admin/logs?start_time=xxx&end_time=xxx` | 根据时间范围获取日志 | admin |
| GET | `/api/admin/logs?action=remove-load` | 根据操作类型获取日志 | admin |

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

### v1.0.0 (当前版本)
- ✅ **核心功能**：
  - 多集群管理支持
  - Pod负载踢出和恢复功能
  - 实时Pod信息展示
  - 节点IP显示
- ✅ **认证与权限**：
  - 基于用户名密码的认证
  - 三级权限模型（admin、read、write）
  - 集群级权限控制
  - 操作日志记录
- ✅ **部署支持**：
  - Docker容器化部署
  - Kubernetes原生部署
  - 配置持久化
- ✅ **管理功能**：
  - 集群管理
  - 用户管理
  - 操作日志查看

## 贡献指南

### 开发流程

1. **Fork项目**：在GitHub上Fork项目到自己的仓库
2. **克隆代码**：将Fork的仓库克隆到本地
3. **创建分支**：创建一个新的特性分支
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **开发代码**：实现新功能或修复bug，遵循代码风格规范
5. **测试代码**：确保代码可以正常运行，没有语法错误
6. **提交代码**：
   ```bash
   git add .
   git commit -m "Add: 新功能描述"
   ```
7. **推送分支**：将分支推送到GitHub
   ```bash
   git push origin feature/your-feature-name
   ```
8. **创建Pull Request**：在GitHub上创建Pull Request，描述你的更改

### 代码规范

- 遵循PEP 8规范
- 使用4空格缩进
- 代码中添加必要的注释
- 使用类型提示
- 确保代码可读性

### 测试要求

- 确保所有功能正常工作
- 测试边界情况
- 确保API端点正常响应
- 测试权限控制逻辑

## 故障排除

### 1. 应用无法启动

**可能原因**：
- Python版本不兼容
- 依赖包未正确安装
- 端口被占用

**解决方案**：
- 确保使用Python 3.11+
- 重新安装依赖：`pip install -r requirements.txt`
- 检查端口5000是否被占用，或修改端口号

### 2. 无法连接到Kubernetes集群

**可能原因**：
- Kubeconfig配置错误
- 网络连接问题
- 集群认证失败

**解决方案**：
- 检查Kubeconfig内容是否正确
- 确保网络可以访问集群API服务器
- 验证Kubeconfig的认证信息

### 3. Pod负载管理不生效

**可能原因**：
- Service标签选择器未配置load标签
- Pod没有load标签
- 权限不足

**解决方案**：
- 检查Service的标签选择器，确保包含`load: online`
- 确保Pod被正确标记了load标签
- 检查用户是否有write权限

## 许可证

MIT License

## 联系方式

如有问题或建议，请通过以下方式联系：

- 项目地址：<repository-url>
- 问题反馈：<issue-url>

---

**K8s Pod负载管理工具** - 简化Kubernetes集群的Pod负载管理
