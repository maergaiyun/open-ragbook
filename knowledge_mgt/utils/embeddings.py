import logging
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from django.db import connection

logger = logging.getLogger('knowledge_mgt')

class EmbeddingModel:
    """文本嵌入模型"""
    
    def __init__(self, model_name="all-MiniLM-L6-v2", model_config=None):
        self.model_name = model_name
        self.model_config = model_config or {}
        self.model = None
        self.is_loaded = False
        
    def load_model(self):
        """加载模型到内存"""
        if self.is_loaded:
            logger.info(f"模型 {self.model_name} 已经加载")
            return
            
        try:
            # 检测是否有可用的GPU
            if torch.cuda.is_available():
                device = "cuda"
                device_name = torch.cuda.get_device_name(0)
                logger.info(f"检测到GPU: {device_name}，将使用GPU加载模型")
            else:
                device = "cpu"
                logger.info("未检测到GPU，将使用CPU加载模型")
            
            # 检查模型路径是否存在
            model_path = self.model_config.get('local_path') or self.model_name
            
            # 如果是本地路径，检查路径是否存在
            if self.model_config.get('local_path'):
                import os
                if not os.path.exists(model_path):
                    raise FileNotFoundError(f"指定的模型路径不存在: {model_path}")
                logger.info(f"使用本地模型路径: {model_path}")
            else:
                logger.info(f"使用模型名称: {model_path}")
            
            # 使用指定设备加载模型，不自动下载
            self.model = SentenceTransformer(model_path, device=device, cache_folder=None)
            self.is_loaded = True
            logger.info(f"成功加载嵌入模型: {model_path} 到设备: {device}")
        except Exception as e:
            logger.error(f"加载嵌入模型失败: {str(e)}", exc_info=True)
            raise
    
    def unload_model(self):
        """卸载模型释放内存"""
        if self.model is not None:
            del self.model
            self.model = None
            self.is_loaded = False
            # 清理GPU缓存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info(f"已卸载嵌入模型: {self.model_name}")
    
    def embed_text(self, text):
        """为单个文本生成嵌入向量"""
        if not self.is_loaded:
            raise RuntimeError(f"模型 {self.model_name} 尚未加载，请先调用 load_model()")
            
        if not text or not text.strip():
            logger.warning("嵌入空文本")
            return np.zeros(self.get_dimension())
        
        try:
            vector = self.model.encode(text)
            return vector.tolist()
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {str(e)}", exc_info=True)
            return np.zeros(self.get_dimension()).tolist()
    
    def embed_texts(self, texts):
        """为多个文本生成嵌入向量"""
        if not self.is_loaded:
            raise RuntimeError(f"模型 {self.model_name} 尚未加载，请先调用 load_model()")
            
        if not texts:
            logger.warning("嵌入空文本列表")
            return []
        
        # 过滤空文本
        filtered_texts = [text for text in texts if text and text.strip()]
        
        if not filtered_texts:
            return []
        
        try:
            vectors = self.model.encode(filtered_texts)
            return vectors.tolist()
        except Exception as e:
            logger.error(f"批量生成嵌入向量失败: {str(e)}", exc_info=True)
            return [np.zeros(self.get_dimension()).tolist() for _ in filtered_texts]
    
    def get_dimension(self):
        """获取嵌入向量的维度"""
        if not self.is_loaded:
            # 如果模型未加载，从配置中获取维度
            return self.model_config.get('vector_dimension', 384)
        return self.model.get_sentence_embedding_dimension()
    
    def get_device(self):
        """获取模型当前运行的设备"""
        if not self.is_loaded:
            return "未加载"
        return self.model.device.type

# 全局本地嵌入模型管理器
class LocalEmbeddingManager:
    """本地嵌入模型管理器 - 单例模式，同时只能加载一个本地模型"""
    
    _instance = None
    _current_model = None
    _current_model_id = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalEmbeddingManager, cls).__new__(cls)
        return cls._instance
    
    def get_current_model(self):
        """获取当前加载的模型"""
        return self._current_model
    
    def get_current_model_id(self):
        """获取当前加载的模型ID"""
        return self._current_model_id
    
    def load_model(self, model_id, model_config):
        """加载指定的本地模型"""
        # 如果已经加载了相同的模型，直接返回
        if self._current_model_id == model_id and self._current_model is not None:
            logger.info(f"模型 {model_id} 已经加载")
            return self._current_model
        
        # 卸载当前模型
        if self._current_model is not None:
            logger.info(f"卸载当前模型 {self._current_model_id}")
            self._current_model.unload_model()
            self._current_model = None
            self._current_model_id = None
        
        # 加载新模型
        try:
            model_name = model_config.get('model_name') or model_config.get('local_path', 'all-MiniLM-L6-v2')
            embedding_model = EmbeddingModel(model_name=model_name, model_config=model_config)
            embedding_model.load_model()
            
            self._current_model = embedding_model
            self._current_model_id = model_id
            
            logger.info(f"成功加载本地嵌入模型 {model_id}: {model_name}")
            return embedding_model
        except Exception as e:
            logger.error(f"加载本地嵌入模型失败: {str(e)}", exc_info=True)
            raise
    
    def unload_current_model(self):
        """卸载当前模型"""
        if self._current_model is not None:
            logger.info(f"卸载当前模型 {self._current_model_id}")
            self._current_model.unload_model()
            self._current_model = None
            self._current_model_id = None

# 全局管理器实例
local_embedding_manager = LocalEmbeddingManager()

def get_embedding_model_by_id(model_id):
    """根据模型ID获取嵌入模型实例"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, model_type, api_type, api_key, api_url, model_name, local_path,
                       vector_dimension, max_tokens, batch_size, timeout
                FROM embedding_model 
                WHERE id = %s AND is_active = 1
            """, [model_id])
            
            result = cursor.fetchone()
            if not result:
                logger.error(f"嵌入模型不存在或已禁用: {model_id}")
                return None
            
            return {
                'id': result[0],
                'name': result[1],
                'model_type': result[2],
                'api_type': result[3],
                'api_key': result[4],
                'api_url': result[5],
                'model_name': result[6],
                'local_path': result[7],
                'vector_dimension': result[8],
                'max_tokens': result[9],
                'batch_size': result[10],
                'timeout': result[11]
            }
                
    except Exception as e:
        logger.error(f"获取嵌入模型失败: {str(e)}", exc_info=True)
        raise

def get_default_embedding_model():
    """获取默认嵌入模型"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id FROM embedding_model 
                WHERE is_default = 1 AND is_active = 1
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            if result:
                return get_embedding_model_by_id(result[0])
            else:
                logger.warning("未找到默认嵌入模型")
                return None
                
    except Exception as e:
        logger.error(f"获取默认嵌入模型失败: {str(e)}", exc_info=True)
        return None

def unload_local_embedding_model():
    """卸载当前本地嵌入模型"""
    local_embedding_manager.unload_current_model()

def get_current_local_model_info():
    """获取当前加载的本地模型信息"""
    current_model = local_embedding_manager.get_current_model()
    current_model_id = local_embedding_manager.get_current_model_id()
    
    if current_model is None:
        return None
    
    return {
        'model_id': current_model_id,
        'model_name': current_model.model_name,
        'is_loaded': current_model.is_loaded,
        'dimension': current_model.get_dimension(),
        'device': current_model.get_device()
    }

# 兼容性函数 - 保持向后兼容
def get_embedding_model(model_name="all-MiniLM-L6-v2"):
    """获取嵌入模型实例（兼容性函数）"""
    logger.warning("get_embedding_model() 已废弃，请使用 get_embedding_model_by_id()")
    # 尝试获取默认模型
    return get_default_embedding_model()

def initialize_embedding_model(model_name="all-MiniLM-L6-v2"):
    """初始化嵌入模型（兼容性函数）"""
    logger.warning("initialize_embedding_model() 已废弃，系统不再自动预加载模型")
    return None 