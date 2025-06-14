import os
import logging
import re
from pathlib import Path
import fitz  # PyMuPDF
import docx
import uuid
import numpy as np
import faiss
import pickle
import json
from datetime import datetime

from django.conf import settings

logger = logging.getLogger('knowledge_mgt')


class DocumentProcessor:
    """文档处理类，用于解析不同类型的文档并分块"""

    def __init__(self, chunking_method="token", chunk_size=500, similarity_threshold=0.7, overlap_size=100):
        self.chunking_method = chunking_method
        self.chunk_size = chunk_size
        self.similarity_threshold = similarity_threshold
        self.overlap_size = overlap_size
        # 文档存储目录
        self.storage_dir = os.path.join(settings.MEDIA_ROOT, 'knowledge_docs')
        os.makedirs(self.storage_dir, exist_ok=True)
        # 向量库存储目录
        self.vector_dir = os.path.join(settings.MEDIA_ROOT, 'vector_indexes')
        os.makedirs(self.vector_dir, exist_ok=True)

    def save_file(self, file, knowledge_db_id):
        """保存上传的文件"""
        # 为文件创建唯一目录
        db_dir = os.path.join(self.storage_dir, str(knowledge_db_id))
        os.makedirs(db_dir, exist_ok=True)

        # 生成唯一文件名
        filename = file.name
        file_path = os.path.join(db_dir, filename)

        # 如果文件已存在，在文件名前添加时间戳
        if os.path.exists(file_path):
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{timestamp}{ext}"
            file_path = os.path.join(db_dir, filename)

        # 保存文件
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # 获取文件信息
        file_info = {
            'filename': filename,
            'file_path': file_path,
            'file_type': os.path.splitext(filename)[1][1:].lower(),
            'file_size': os.path.getsize(file_path)
        }

        return file_info

    def process_document(self, file_path):
        """处理文档，提取文本内容"""
        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            if file_ext == '.pdf':
                return self._extract_from_pdf(file_path)
            elif file_ext in ['.docx', '.doc']:
                return self._extract_from_docx(file_path)
            elif file_ext in ['.txt', '.md']:
                return self._extract_from_text(file_path)
            else:
                logger.warning(f"不支持的文件类型: {file_ext}")
                return "不支持的文件类型"
        except Exception as e:
            logger.error(f"处理文档时出错: {str(e)}", exc_info=True)
            return f"处理文档失败: {str(e)}"

    def _extract_from_pdf(self, file_path):
        """从PDF文件中提取文本"""
        text = ""
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
            return text
        except Exception as e:
            logger.error(f"从PDF提取文本出错: {str(e)}", exc_info=True)
            raise

    def _extract_from_docx(self, file_path):
        """从Word文档中提取文本"""
        text = ""
        try:
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        except Exception as e:
            logger.error(f"从Word提取文本出错: {str(e)}", exc_info=True)
            raise

    def _extract_from_text(self, file_path):
        """从文本文件中提取文本"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as file:
                    return file.read()
            except Exception as e:
                logger.error(f"从文本文件提取内容出错: {str(e)}", exc_info=True)
                raise

    def split_text(self, text):
        """根据指定方法分割文本"""
        chunks = []

        if self.chunking_method == "token":
            chunks = self._split_by_token(text)
        elif self.chunking_method == "sentence":
            chunks = self._split_by_sentence(text)
        elif self.chunking_method == "paragraph":
            chunks = self._split_by_paragraph(text)
        elif self.chunking_method == "fixed_length":
            chunks = self._split_by_fixed_length(text)
        elif self.chunking_method == "semantic":
            chunks = self._split_by_semantic(text)
        elif self.chunking_method == "recursive":
            chunks = self._split_recursive(text)
        else:
            logger.warning(f"未实现的分块方法: {self.chunking_method}，使用Token分块")
            chunks = self._split_by_token(text)

        # 过滤空块
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        logger.info(f"使用 {self.chunking_method} 方法分割文本，生成 {len(chunks)} 个分块")
        return chunks

    def _split_by_token(self, text):
        """按Token数量分块（以字符为单位）"""
        chunks = []
        total_chars = len(text)
        start = 0

        while start < total_chars:
            end = min(start + self.chunk_size, total_chars)
            # 确保不会在单词中间截断
            if end < total_chars:
                # 尝试找到一个合适的断句点
                for i in range(min(100, end - start)):
                    if text[end - i] in ['.', '!', '?', '\n', '。', '！', '？', '；', ';']:
                        end = end - i + 1
                        break

            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end

        return chunks

    def _split_by_sentence(self, text):
        """按句子边界分块"""
        # 中英文句子分割正则表达式
        sentence_pattern = r'[.!?。！？；;]\s*'
        sentences = re.split(sentence_pattern, text)
        
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_length = len(sentence)
            
            # 如果当前句子加入后超过限制，先保存当前块
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(sentence)
            current_length += sentence_length

        # 添加最后一个块
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def _split_by_paragraph(self, text):
        """按段落边界分块"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            paragraph_length = len(paragraph)
            
            # 如果单个段落就超过限制，需要进一步分割
            if paragraph_length > self.chunk_size:
                # 先保存当前块
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # 对长段落按句子分割
                sub_chunks = self._split_by_sentence(paragraph)
                chunks.extend(sub_chunks)
                continue
            
            # 如果加入当前段落后超过限制，先保存当前块
            if current_length + paragraph_length > self.chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(paragraph)
            current_length += paragraph_length
        
        # 添加最后一个块
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            
        return chunks

    def _split_by_fixed_length(self, text):
        """按固定字符长度分块"""
        chunks = []
        total_length = len(text)
        start = 0
        
        while start < total_length:
            end = min(start + self.chunk_size, total_length)
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end
            
        return chunks

    def _split_by_semantic(self, text):
        """按语义相似度分块（简化实现）"""
        # 这里实现一个简化的语义分块
        # 实际应用中可能需要使用更复杂的NLP模型
        
        # 先按句子分割
        sentences = self._split_by_sentence(text)
        if len(sentences) <= 1:
            return sentences
            
        chunks = []
        current_chunk = [sentences[0]]
        
        for i in range(1, len(sentences)):
            # 简化的语义相似度判断：基于词汇重叠
            similarity = self._calculate_text_similarity(
                ' '.join(current_chunk), 
                sentences[i]
            )
            
            # 如果相似度低于阈值或当前块太大，开始新块
            if (similarity < self.similarity_threshold or 
                len(' '.join(current_chunk)) + len(sentences[i]) > self.chunk_size):
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentences[i]]
            else:
                current_chunk.append(sentences[i])
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks

    def _split_recursive(self, text):
        """递归分块（带重叠）"""
        chunks = []
        total_length = len(text)
        start = 0
        
        while start < total_length:
            end = min(start + self.chunk_size, total_length)
            
            # 尝试在合适的位置断开
            if end < total_length:
                for i in range(min(100, end - start)):
                    if text[end - i] in ['.', '!', '?', '\n', '。', '！', '？', '；', ';']:
                        end = end - i + 1
                        break
            
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            
            # 计算下一个起始位置（考虑重叠）
            if end < total_length:
                start = max(start + 1, end - self.overlap_size)
            else:
                break
                
        return chunks

    def _calculate_text_similarity(self, text1, text2):
        """计算两个文本的相似度（基于词汇重叠）"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0


class VectorStore:
    """向量存储类，用于管理FAISS索引"""

    def __init__(self, vector_dimension=384, index_type="Flat"):
        self.vector_dimension = vector_dimension
        self.index_type = index_type
        # 向量库存储目录
        self.vector_dir = os.path.join(settings.MEDIA_ROOT, 'vector_indexes')
        os.makedirs(self.vector_dir, exist_ok=True)

    def create_index(self, knowledge_db_id):
        """为知识库创建FAISS索引"""
        db_vector_dir = os.path.join(self.vector_dir, str(knowledge_db_id))
        os.makedirs(db_vector_dir, exist_ok=True)

        index_path = os.path.join(db_vector_dir, "faiss.index")
        mapping_path = os.path.join(db_vector_dir, "id_mapping.json")

        # 检查索引是否已存在
        if os.path.exists(index_path) and os.path.exists(mapping_path):
            logger.info(f"知识库 {knowledge_db_id} 的索引已存在")
            return True

        try:
            # 创建FAISS索引
            if self.index_type == "Flat":
                index = faiss.IndexFlatL2(self.vector_dimension)
            elif self.index_type == "IVF":
                # 为IVF创建量化器
                quantizer = faiss.IndexFlatL2(self.vector_dimension)
                # 创建IVF索引，nlist是聚类的数量
                index = faiss.IndexIVFFlat(quantizer, self.vector_dimension, 100)
                # IVF索引需要训练
                # 这里需要一些训练数据，通常实际应用中需要真实数据
                # 如果没有训练数据，这里使用随机数据
                random_data = np.random.random((100, self.vector_dimension)).astype('float32')
                index.train(random_data)
            else:
                # 默认使用Flat
                logger.warning(f"不支持的索引类型 {self.index_type}，使用默认Flat")
                index = faiss.IndexFlatL2(self.vector_dimension)

            # 保存索引
            faiss.write_index(index, index_path)

            # 创建空的ID映射
            with open(mapping_path, 'w') as f:
                json.dump({}, f)

            logger.info(f"已为知识库 {knowledge_db_id} 创建索引")
            return True
        except Exception as e:
            logger.error(f"创建索引时出错: {str(e)}", exc_info=True)
            return False

    def add_vectors(self, knowledge_db_id, chunk_ids, vectors):
        """添加向量到索引"""
        if len(chunk_ids) != len(vectors):
            logger.error("分块ID和向量数量不匹配")
            return False

        db_vector_dir = os.path.join(self.vector_dir, str(knowledge_db_id))
        index_path = os.path.join(db_vector_dir, "faiss.index")
        mapping_path = os.path.join(db_vector_dir, "id_mapping.json")

        try:
            # 检查索引是否存在
            if not os.path.exists(index_path) or not os.path.exists(mapping_path):
                self.create_index(knowledge_db_id)

            # 读取索引
            index = faiss.read_index(index_path)

            # 读取ID映射
            with open(mapping_path, 'r') as f:
                id_mapping = json.load(f)

            # 将向量添加到索引
            vectors_array = np.array(vectors).astype('float32')
            vector_ids = list(range(index.ntotal, index.ntotal + len(vectors)))

            index.add(vectors_array)

            # 更新ID映射
            for i, chunk_id in enumerate(chunk_ids):
                id_mapping[str(vector_ids[i])] = chunk_id

            # 保存更新后的索引和映射
            faiss.write_index(index, index_path)
            with open(mapping_path, 'w') as f:
                json.dump(id_mapping, f)

            logger.info(f"已将 {len(vectors)} 个向量添加到知识库 {knowledge_db_id} 的索引")
            return vector_ids
        except Exception as e:
            logger.error(f"添加向量时出错: {str(e)}", exc_info=True)
            return []

    def search(self, knowledge_db_id, query_vector, top_k=5):
        """搜索最相似的向量"""
        db_vector_dir = os.path.join(self.vector_dir, str(knowledge_db_id))
        index_path = os.path.join(db_vector_dir, "faiss.index")
        mapping_path = os.path.join(db_vector_dir, "id_mapping.json")

        if not os.path.exists(index_path) or not os.path.exists(mapping_path):
            logger.error(f"知识库 {knowledge_db_id} 的索引不存在")
            return []

        try:
            # 读取索引
            index = faiss.read_index(index_path)

            # 读取ID映射
            with open(mapping_path, 'r') as f:
                id_mapping = json.load(f)

            # 确保query_vector是正确的形状
            query_vector = np.array([query_vector]).astype('float32')
            
            # 调试信息：检查维度
            logger.debug(f"索引维度: {index.d}, 查询向量维度: {query_vector.shape[1]}, 配置维度: {self.vector_dimension}")
            
            # 检查维度是否匹配
            if query_vector.shape[1] != index.d:
                logger.error(f"维度不匹配: 查询向量维度 {query_vector.shape[1]}, 索引维度 {index.d}")
                # 如果维度不匹配，尝试调整查询向量
                if query_vector.shape[1] < index.d:
                    # 如果查询向量维度小，用零填充
                    padding = np.zeros((1, index.d - query_vector.shape[1]), dtype='float32')
                    query_vector = np.concatenate([query_vector, padding], axis=1)
                    logger.warning(f"查询向量维度过小，已用零填充到 {index.d} 维")
                else:
                    # 如果查询向量维度大，截断
                    query_vector = query_vector[:, :index.d]
                    logger.warning(f"查询向量维度过大，已截断到 {index.d} 维")

            # 搜索
            distances, indices = index.search(query_vector, top_k)

            # 获取对应的分块ID
            results = []
            for i, idx in enumerate(indices[0]):
                if idx != -1:  # -1表示无效索引
                    chunk_id = id_mapping.get(str(idx))
                    if chunk_id:
                        results.append({
                            'chunk_id': chunk_id,
                            'distance': float(distances[0][i])
                        })

            return results
        except Exception as e:
            logger.error(f"搜索向量时出错: {str(e)}", exc_info=True)
            return []

    def delete_chunks(self, knowledge_db_id, chunk_ids):
        """从索引中删除指定的分块"""
        # 注意：FAISS不支持直接删除，我们通过重建索引来实现
        db_vector_dir = os.path.join(self.vector_dir, str(knowledge_db_id))
        index_path = os.path.join(db_vector_dir, "faiss.index")
        mapping_path = os.path.join(db_vector_dir, "id_mapping.json")

        if not os.path.exists(index_path) or not os.path.exists(mapping_path):
            logger.error(f"知识库 {knowledge_db_id} 的索引不存在")
            return False

        try:
            # 读取ID映射
            with open(mapping_path, 'r') as f:
                id_mapping = json.load(f)

            # 找出要删除的向量ID
            vector_ids_to_delete = set()
            for vector_id, chunk_id in id_mapping.items():
                if chunk_id in chunk_ids:
                    vector_ids_to_delete.add(int(vector_id))

            # 读取索引
            index = faiss.read_index(index_path)

            if not vector_ids_to_delete:
                logger.info(f"没有找到要删除的分块")
                return True

            # 创建新的ID映射
            new_id_mapping = {}
            for vector_id, chunk_id in id_mapping.items():
                if int(vector_id) not in vector_ids_to_delete:
                    new_id_mapping[vector_id] = chunk_id

            # 创建新的索引并复制保留的向量
            if self.index_type == "Flat":
                new_index = faiss.IndexFlatL2(self.vector_dimension)
            else:
                # 默认使用Flat
                new_index = faiss.IndexFlatL2(self.vector_dimension)

            # 如果所有向量都被删除，直接保存空索引
            if len(new_id_mapping) == 0:
                faiss.write_index(new_index, index_path)
                with open(mapping_path, 'w') as f:
                    json.dump({}, f)
                logger.info(f"已从知识库 {knowledge_db_id} 的索引中删除所有向量")
                return True

            # 否则，重建索引
            # 这需要访问原始向量，但FAISS不直接支持
            # 实际应用中，可能需要存储原始向量或重新生成
            logger.warning("FAISS不支持直接删除，需要完整实现来重建索引")

            # 保存更新后的映射
            with open(mapping_path, 'w') as f:
                json.dump(new_id_mapping, f)

            logger.info(f"已从知识库 {knowledge_db_id} 的索引中删除 {len(vector_ids_to_delete)} 个向量")
            return True
        except Exception as e:
            logger.error(f"删除向量时出错: {str(e)}", exc_info=True)
            return False
