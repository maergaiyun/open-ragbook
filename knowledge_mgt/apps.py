from django.apps import AppConfig
import logging
import torch


class KnowledgeMgtConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'knowledge_mgt'
    
    def ready(self):
        """应用启动时执行的初始化方法"""
        logger = logging.getLogger('knowledge_mgt')
        logger.info("知识库管理应用启动...")
        
        # 检查GPU可用性
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            device_names = [torch.cuda.get_device_name(i) for i in range(device_count)]
            logger.info(f"系统可用GPU数量: {device_count}, 设备: {', '.join(device_names)}")
        else:
            logger.info("系统未检测到可用GPU，将使用CPU进行计算")
        
        logger.info("嵌入模型管理器已初始化，支持按需加载本地模型")
        logger.info("本地嵌入模型将在首次使用时按需加载，同时只能加载一个本地模型")
