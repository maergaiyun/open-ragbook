# Open RAGBook

English | [Chinese](README.md)

An intelligent knowledge management system based on RAG (Retrieval-Augmented Generation) technology, supporting integration and management of multiple large language models and embedding models.

## Version Information

**Current Version**: v0.0.1

## Online Demo

**Demo URL**: [http://115.120.244.180:8080/](http://115.120.244.180:8080/)

*Demo environment is for experience only, please do not upload sensitive information*

## Project Introduction

Open RAGBook is a modern knowledge management platform that combines traditional document management with AI Q&A capabilities through RAG technology, providing users with intelligent knowledge retrieval and Q&A experience.

## Key Features

### Core Functions
- **Intelligent Q&A**: AI Q&A system based on knowledge base content
- **Document Management**: Upload, parsing and management of multiple format documents
- **Knowledge Base Management**: Flexible knowledge base creation, editing and permission control
- **Vector Retrieval**: Efficient semantic retrieval and similarity matching

### Model Management
- **Large Language Model Management**: Support for multiple LLM service providers like OpenAI, Baidu, Zhipu AI, etc.
- **Embedding Model Management**: Support for online API and locally deployed embedding models
- **Model Configuration**: Flexible model parameter configuration and performance optimization
- **Model Testing**: Built-in model connection testing and performance evaluation

### System Management
- **User Permission Management**: Role-based access control
- **System Monitoring**: Server resource monitoring and model status management
- **Configuration Management**: System parameters and environment configuration management

## Technical Architecture

### Frontend Tech Stack
- **Framework**: Vue 3 + Composition API
- **UI Components**: Element Plus
- **Build Tool**: Vite
- **State Management**: Pinia
- **Routing**: Vue Router

### Backend Tech Stack
- **Framework**: Django + Django REST Framework
- **Database**: SQLite/PostgreSQL/MySQL
- **Vector Database**: Support for multiple vector storage solutions
- **AI Integration**: Support for multiple LLM and embedding model APIs

## Quick Start

### Environment Requirements
- Node.js >= 22.0.0
- Python >= 3.12
- Git

### Installation Steps

#### Method 1: Automatic Installation (Recommended)

1. **Clone Project**
```bash
git clone https://gitee.com/maergaiyun/open-ragbook.git
cd open-ragbook
```

2. **Install Frontend Dependencies**
```bash
cd open_ragbook_ui
npm install
```

3. **Automatic Backend Dependencies Installation**

**Windows Users**:
```bash
cd ../
# Double-click to run or execute in command line
install.bat
```

**Linux/macOS Users**:
```bash
cd ../
# Give script execution permission
chmod +x install.sh
# Run installation script
./install.sh
```

**Manual Script Execution**:
```bash
cd ../
# Upgrade pip
python -m pip install --upgrade pip
# Run installation script
python install_requirements.py
```

#### Method 2: Manual Installation

1. **Clone Project**
```bash
git clone https://gitee.com/maergaiyun/open-ragbook.git
cd open-ragbook
```

2. **Install Frontend Dependencies**
```bash
cd open_ragbook_ui
npm install
```

3. **Install Backend Dependencies**
```bash
cd ../
# Install basic dependencies
pip install -r requirements.txt

# Choose PyTorch version based on your system:

# CPU version
pip install torch==2.7.1+cpu torchaudio==2.7.1+cpu torchvision==0.22.1+cpu --index-url https://download.pytorch.org/whl/cpu

# Or GPU version (if you have NVIDIA GPU)
pip install torch==2.5.1+cu121 torchaudio==2.5.1+cu121 torchvision==0.20.1+cu121 GPUtil==1.4.0 --index-url https://download.pytorch.org/whl/cu121
```

### Dependencies Installation Guide

This project provides dependency installation tools that can automatically select the appropriate PyTorch version based on your system's GPU situation.

#### System Requirements
- Python 3.12 or higher
- pip (Python package manager)

#### Installation Process
1. **Basic Dependencies Installation**: Install all common dependency packages
2. **GPU Detection**: Automatically detect if the system has NVIDIA GPU
3. **PyTorch Installation**: Choose appropriate version based on GPU situation
   - With GPU: Install CUDA version (torch==2.5.1+cu121)
   - Without GPU: Install CPU version (torch==2.7.1+cpu)
4. **Installation Verification**: Verify all dependencies are correctly installed

#### Troubleshooting

**Common Issues**:

1. **Python Version Too Low**
   - Ensure using Python 3.12 or higher
   - Run `python --version` to check version

2. **pip Version Too Old**
   - Run `python -m pip install --upgrade pip` to upgrade pip

3. **Network Connection Issues**
   - Use domestic mirror source: `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/`

4. **GPU Detection Error**
   - Ensure NVIDIA drivers are installed
   - Run `nvidia-smi` to check GPU status

5. **CUDA Version Mismatch**
   - Check CUDA version: `nvcc --version`
   - Choose corresponding PyTorch version based on CUDA version

**Verify Installation**:
```python
import torch
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU Count: {torch.cuda.device_count()}")
    print(f"Current GPU: {torch.cuda.get_device_name(0)}")
```

### Environment Configuration

1. **Configure Environment**

```bash
# Copy configuration file
cp .env.dev .env
# Edit configuration file, modify database connection and other necessary information
# Main configurations needed:
# - Database connection information (DATABASE_URL)
# - API key configuration
```

2. **Start Services**

Frontend development server:
```bash
cd open_ragbook_ui
npm run dev
```

Backend server:
```bash
python manage.py runserver
```

## Configuration Guide

### Model Configuration
The system supports configuration of multiple large language models and embedding models:

- **Online API Models**: Require configuration of corresponding API keys
- **Locally Deployed Models**: Need to specify model path and service address
- **Model Parameters**: Support adjustment of temperature, max tokens and other parameters

### System Configuration
- Database connection configuration
- Vector database configuration
- File storage configuration
- Logging configuration

## User Guide

### Creating Knowledge Base
1. Login to the system and go to knowledge base management page
2. Click "Create Knowledge Base" button
3. Fill in basic knowledge base information
4. Select appropriate embedding model
5. Configure access permissions

### Uploading Documents
1. Enter target knowledge base
2. Click "Upload Document"
3. Select supported document formats
4. Wait for document parsing and vectorization processing

### Intelligent Q&A
1. Select knowledge base
2. Enter questions in the Q&A interface
3. System will generate answers based on knowledge base content

## Development Guide

### Project Structure
```
open-ragbook/
├── open_ragbook_ui/          # Frontend project
│   ├── src/
│   │   ├── components/       # Common components
│   │   ├── views/           # Page components
│   │   ├── router/          # Route configuration
│   │   └── axios/           # API interfaces
├── system_mgt/              # Backend system management module
├── knowledge_mgt/           # Knowledge management module
├── chat_mgt/               # Chat management module
├── requirements.txt        # Python basic dependencies
├── install_requirements.py # Dependencies installation script
├── install.bat             # Windows installation script
└── install.sh              # Linux/macOS installation script
```

### Code Standards
- Frontend follows Vue 3 official style guide
- Backend follows Django best practices
- Use ESLint and Prettier for code formatting
- Commit messages follow Conventional Commits specification

## Deployment Guide

### Production Environment Deployment
1. Build frontend project
2. Configure web server (Nginx/Apache)
3. Configure database
4. Set environment variables
5. Start backend service

### Docker Deployment
```bash
# Build image
docker build -t open-ragbook .

# Run container
docker run -d -p 8000:8000 open-ragbook
```

## Contributing

Welcome to submit Issues and Pull Requests to help improve the project.

### Submission Process
1. Fork the project
2. Create feature branch
3. Submit changes
4. Create Pull Request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Contact

If you have questions or suggestions, please contact us through:

- Submit Issue
- Send email
- Project discussion area

### WeChat Community

Scan the QR code to join our WeChat community and exchange experiences with other developers:

![WeChat Group QR Code](./docs/images/wechat-group-qr.jpg)

*Group QR code will be updated regularly. If the QR code expires, please contact the author*

### Contact Author

For technical support or business cooperation, you can directly contact the author:

![Author WeChat QR Code](./docs/images/author-wechat-qr.jpg)

*Please note: Open RAGBook when adding*

## Changelog

### v0.0.1 (2025-06-15)
- **Official Release**
- **New Features**:
  - Recall retrieval testing: Support vector retrieval quality testing and parameter tuning
  - Document upload queue system: Support batch document upload and progress monitoring
  - Professional chunking methods: Added chapter chunking, semantic chunking, sliding window chunking and other strategies
  - Custom delimiter chunking: Support user-defined delimiters for document chunking
- **Optimizations**:
  - Refactored API code, reduced duplicate code by 60%+
  - Optimized document chunking algorithms, improved chunking quality
  - Enhanced user interface, improved user experience
  - Optimized error handling and user prompts
- **Bug Fixes**:
  - Fixed knowledge base name uniqueness check issue
  - Fixed user information retrieval issue during document upload
  - Fixed frontend error message display issue
- **Documentation Updates**:
  - Improved installation documentation and troubleshooting guide
  - Optimized dependency installation process
  - Added online demo address

### v0.0.1-beta (2025-05-30)
- Initial version release
- Implemented basic RAG Q&A functionality
- Support for multiple large language model integration
- Implemented embedding model management
- Completed user permission system
- Implemented knowledge base management functionality

---

**Note**: Initial installation may take a long time, especially when downloading large packages like PyTorch. Please be patient. 