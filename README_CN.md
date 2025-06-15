# Open RAGBook

[英文](./README_EN.md) | 中文

一个基于RAG（Retrieval-Augmented Generation）技术的智能知识管理系统，支持多种大语言模型和嵌入模型的集成与管理。

## 版本信息

**当前版本**: v0.0.1-beta

## 项目简介

Open RAGBook 是一个现代化的知识管理平台，通过RAG技术将传统的文档管理与AI问答能力相结合，为用户提供智能化的知识检索和问答体验。

## 主要功能

### 核心功能
- **智能问答**: 基于知识库内容的AI问答系统
- **文档管理**: 支持多种格式文档的上传、解析和管理
- **知识库管理**: 灵活的知识库创建、编辑和权限控制
- **向量检索**: 高效的语义检索和相似度匹配

### 模型管理
- **大语言模型管理**: 支持OpenAI、百度、智谱AI等多种LLM服务商
- **嵌入模型管理**: 支持在线API和本地部署的嵌入模型
- **模型配置**: 灵活的模型参数配置和性能优化
- **模型测试**: 内置模型连接测试和性能评估

### 系统管理
- **用户权限管理**: 基于角色的访问控制
- **系统监控**: 服务器资源监控和模型状态管理
- **配置管理**: 系统参数和环境配置管理

## 技术架构

### 前端技术栈
- **框架**: Vue 3 + Composition API
- **UI组件**: Element Plus
- **构建工具**: Vite
- **状态管理**: Pinia
- **路由管理**: Vue Router

### 后端技术栈
- **框架**: Django + Django REST Framework
- **数据库**: SQLite/PostgreSQL/MySQL
- **向量数据库**: 支持多种向量存储方案
- **AI集成**: 支持多种LLM和嵌入模型API

## 快速开始

### 环境要求
- Node.js >= 22.0.0
- Python >= 3.12
- Git

### 安装步骤

#### 方法一：自动安装（推荐）

1. **克隆项目**
```bash
git clone https://gitee.com/maergaiyun/open-ragbook.git
cd open-ragbook
```

2. **安装前端依赖**
```bash
cd open_ragbook_ui
npm install
```

3. **自动安装后端依赖**

**Windows用户**:
```bash
cd ../
# 双击运行或在命令行中执行
install.bat
```

**Linux/macOS用户**:
```bash
cd ../
# 给脚本执行权限
chmod +x install.sh
# 运行安装脚本
./install.sh
```

**手动运行安装脚本**:
```bash
cd ../
# 升级pip
python -m pip install --upgrade pip
# 运行安装脚本
python install_requirements.py
```

#### 方法二：手动安装

1. **克隆项目**
```bash
git clone https://gitee.com/maergaiyun/open-ragbook.git
cd open-ragbook
```

2. **安装前端依赖**
```bash
cd open_ragbook_ui
npm install
```

3. **安装后端依赖**
```bash
cd ../
# 安装基础依赖
pip install -r requirements.txt

# 根据您的系统选择PyTorch版本：

# CPU版本
pip install torch==2.7.1+cpu torchaudio==2.7.1+cpu torchvision==0.22.1+cpu --index-url https://download.pytorch.org/whl/cpu

# 或GPU版本（如果有NVIDIA GPU）
pip install torch==2.5.1+cu121 torchaudio==2.5.1+cu121 torchvision==0.20.1+cu121 GPUtil==1.4.0 --index-url https://download.pytorch.org/whl/cu121
```

### 依赖安装说明

本项目提供了依赖安装工具，可以根据您的系统GPU情况自动选择合适的PyTorch版本。

#### 系统要求
- Python 3.12 或更高版本
- pip (Python包管理器)

#### 安装过程
1. **基础依赖安装**: 安装所有通用依赖包
2. **GPU检测**: 自动检测系统是否有NVIDIA GPU
3. **PyTorch安装**: 根据GPU情况选择合适版本
   - 有GPU: 安装CUDA版本 (torch==2.5.1+cu121)
   - 无GPU: 安装CPU版本 (torch==2.7.1+cpu)
4. **安装验证**: 验证所有依赖是否正确安装

#### 故障排除

**常见问题**:

1. **Python版本过低**
   - 确保使用Python 3.12或更高版本
   - 运行 `python --version` 检查版本

2. **pip版本过旧**
   - 运行 `python -m pip install --upgrade pip` 升级pip

3. **网络连接问题**
   - 使用国内镜像源：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/`

4. **GPU检测错误**
   - 确保安装了NVIDIA驱动
   - 运行 `nvidia-smi` 检查GPU状态

5. **CUDA版本不匹配**
   - 检查CUDA版本：`nvcc --version`
   - 根据CUDA版本选择对应的PyTorch版本

**验证安装**:
```python
import torch
print(f"PyTorch版本: {torch.__version__}")
print(f"CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU数量: {torch.cuda.device_count()}")
    print(f"当前GPU: {torch.cuda.get_device_name(0)}")
```

### 配置环境

4. **配置环境**
```bash
# 复制配置文件
cp .env.dev .env
# 编辑配置文件，修改数据库连接配置和其他必要信息
# 主要需要配置：
# - 数据库连接信息（DATABASE_URL）
# - API密钥配置
```

5. **初始化数据库**
```bash
python manage.py migrate
python manage.py createsuperuser
```

6. **启动服务**

前端开发服务器:
```bash
cd open_ragbook_ui
npm run dev
```

后端服务器:
```bash
python manage.py runserver
```

## 配置说明

### 模型配置
系统支持多种大语言模型和嵌入模型的配置：

- **在线API模型**: 需要配置相应的API密钥
- **本地部署模型**: 需要指定模型路径和服务地址
- **模型参数**: 支持温度、最大Token数等参数调整

### 系统配置
- 数据库连接配置
- 向量数据库配置
- 文件存储配置
- 日志配置

## 使用指南

### 创建知识库
1. 登录系统后进入知识库管理页面
2. 点击"新建知识库"按钮
3. 填写知识库基本信息
4. 选择合适的嵌入模型
5. 配置访问权限

### 上传文档
1. 进入目标知识库
2. 点击"上传文档"
3. 选择支持的文档格式
4. 等待文档解析和向量化处理

### 智能问答
1. 选择知识库
2. 在问答界面输入问题
3. 系统将基于知识库内容生成答案

## 开发指南

### 项目结构
```
open-ragbook/
├── open_ragbook_ui/          # 前端项目
│   ├── src/
│   │   ├── components/       # 公共组件
│   │   ├── views/           # 页面组件
│   │   ├── router/          # 路由配置
│   │   └── axios/           # API接口
├── system_mgt/              # 后端系统管理模块
├── knowledge_mgt/           # 知识管理模块
├── chat_mgt/               # 对话管理模块
├── requirements.txt        # Python基础依赖
├── install_requirements.py # 依赖安装脚本
├── install.bat             # Windows安装脚本
└── install.sh              # Linux/macOS安装脚本
```

### 代码规范
- 前端遵循Vue 3官方风格指南
- 后端遵循Django最佳实践
- 使用ESLint和Prettier进行代码格式化
- 提交信息遵循Conventional Commits规范

## 部署说明

### 生产环境部署
1. 构建前端项目
2. 配置Web服务器（Nginx/Apache）
3. 配置数据库
4. 设置环境变量
5. 启动后端服务

### Docker部署
```bash
# 构建镜像
docker build -t open-ragbook .

# 运行容器
docker run -d -p 8000:8000 open-ragbook
```

## 贡献指南

欢迎提交Issue和Pull Request来帮助改进项目。

### 提交流程
1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交Issue
- 发送邮件
- 项目讨论区

### 微信交流群

扫码加入微信交流群，与其他开发者交流使用经验：

![微信群二维码](./docs/images/wechat-group-qr.jpg)

*群二维码会定期更新，如二维码过期请联系作者*

### 联系作者

如需技术支持或商务合作，可直接联系作者：

![作者微信二维码](./docs/images/author-wechat-qr.jpg)

*添加时请备注：Open RAGBook*

## 更新日志

### v0.0.1-beta (2024-12-19)
- 初始版本发布
- 实现基础的RAG问答功能
- 支持多种大语言模型集成
- 实现嵌入模型管理
- 完成用户权限系统
- 实现知识库管理功能

---

**注意**: 首次安装可能需要较长时间，特别是下载PyTorch等大型包时，请耐心等待。 