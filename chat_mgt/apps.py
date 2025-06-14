from django.apps import AppConfig
import logging


class ChatMgtConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat_mgt'
    
    def ready(self):
        """应用启动时执行的初始化方法"""
        logger = logging.getLogger(__name__)
        logger.info("聊天管理应用启动...")
        logger.info("聊天应用将根据知识库配置按需使用嵌入模型")
