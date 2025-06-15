# Open RAGBook

English | [中文](README_CN.md)

An intelligent knowledge management system based on RAG (Retrieval-Augmented Generation) technology, supporting integration and management of multiple large language models and embedding models.

## Version Information

**Current Version**: v0.0.1-beta

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
pip install -r requirements-gpu.txt
```

4. **Configure Environment**
```bash
# Copy configuration file
cp .env.dev .env
# Edit configuration file, modify database connection and other necessary information
# Main configurations needed:
# - Database connection information (DATABASE_URL)
# - API key configuration
```

5. **Initialize Database**
```bash
python manage.py migrate
python manage.py createsuperuser
```

6. **Start Services**

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
└── requirements.txt        # Python dependencies
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

### v0.0.1-beta (2024-12-19)
- Initial version release
- Implemented basic RAG Q&A functionality
- Support for multiple large language model integration
- Implemented embedding model management
- Completed user permission system
- Implemented knowledge base management functionality 