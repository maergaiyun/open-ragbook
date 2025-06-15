import json
import logging
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

# 使用新的工具函数
from open_ragbook_server.utils.auth_utils import (
    jwt_required, get_user_from_request, check_resource_permission,
    parse_json_body, validate_required_fields,
    create_error_response, create_success_response
)
from open_ragbook_server.utils.db_utils import (
    execute_query_with_params
)

from knowledge_mgt.utils.document_processor import VectorStore

# 获取模块日志记录器
logger = logging.getLogger('knowledge_mgt')


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def recall_test(request):
    """召回检索测试API"""
    logger.info("召回检索测试请求")
    
    try:
        # 解析请求数据
        request_data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['knowledge_id', 'query']
        is_valid, missing_fields = validate_required_fields(request_data, required_fields)
        if not is_valid:
            logger.warning(f"召回检索测试失败: 缺少必填字段 - {missing_fields}")
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        knowledge_id = request_data.get('knowledge_id')
        query = request_data.get('query')
        retrieve_count = request_data.get('retrieve_count', 5)
        similarity_threshold = request_data.get('similarity_threshold', 0.3)
        
        logger.debug(f"召回检索测试参数: knowledge_id={knowledge_id}, query='{query}', retrieve_count={retrieve_count}, similarity_threshold={similarity_threshold}")
        
        # 获取知识库信息（检查用户权限）
        kb_sql = """
            SELECT id, name, description, vector_dimension, index_type 
            FROM knowledge_database 
            WHERE id = %s
        """
        kb_params = [knowledge_id]
        
        # 普通用户只能访问自己的知识库
        if role_id != 1:
            kb_sql += " AND user_id = %s"
            kb_params.append(user_id)
        
        kb_result = execute_query_with_params(kb_sql, kb_params)
        if not kb_result:
            logger.warning(f"召回检索测试失败: 知识库{knowledge_id}不存在或无权限访问")
            return create_error_response('知识库不存在或无权限访问', 404)

        knowledge_info = kb_result[0]
        knowledge_name = knowledge_info['name']
        vector_dimension = knowledge_info['vector_dimension']
        index_type = knowledge_info['index_type']
        
        logger.info(f"开始对知识库'{knowledge_name}'进行召回检索测试")

        # 使用向量数据库进行语义检索
        try:
            # 1. 获取当前加载的本地嵌入模型
            from knowledge_mgt.utils.embeddings import local_embedding_manager
            embedding_model = local_embedding_manager.get_current_model()
            
            if embedding_model is None:
                logger.error("没有加载的嵌入模型，无法进行向量检索")
                return create_error_response('没有加载的嵌入模型，请先在系统管理中加载嵌入模型', 500)
            
            logger.debug("使用当前加载的本地嵌入模型进行向量检索")

            # 2. 将查询转换为向量
            query_vector = embedding_model.embed_text(query)

            # 获取嵌入模型的实际维度
            actual_dimension = embedding_model.get_dimension()
            logger.debug(f"嵌入模型实际维度: {actual_dimension}, 知识库配置维度: {vector_dimension}")

            # 3. 初始化向量存储，使用实际维度
            vector_store = VectorStore(vector_dimension=actual_dimension, index_type=index_type)

            # 4. 在向量数据库中搜索相似文档
            similar_chunks = vector_store.search(knowledge_id, query_vector, top_k=retrieve_count)

            # 5. 根据相似度阈值过滤结果
            filtered_chunks = []
            for chunk in similar_chunks:
                distance = chunk['distance']
                similarity_score = 1.0 / (1.0 + distance) if distance >= 0 else 0.0
                
                # 只保留相似度高于阈值的结果
                if similarity_score >= similarity_threshold:
                    chunk['similarity'] = similarity_score
                    filtered_chunks.append(chunk)
                    
            logger.info(f"检索到 {len(similar_chunks)} 个结果，过滤后保留 {len(filtered_chunks)} 个结果（相似度阈值: {similarity_threshold}）")

            # 6. 查询对应的文档分块内容（需要检查用户权限）
            results = []
            if filtered_chunks:
                chunk_ids = [chunk['chunk_id'] for chunk in filtered_chunks]
                
                # 构建IN查询的占位符
                placeholders = ','.join(['%s'] * len(chunk_ids))
                chunk_sql = f"""
                    SELECT dc.id, dc.content, d.filename, d.file_path
                    FROM knowledge_document_chunk dc
                    JOIN knowledge_document d ON dc.document_id = d.id
                    WHERE dc.id IN ({placeholders}) AND d.database_id = %s
                """
                chunk_params = chunk_ids + [knowledge_id]
                
                # 普通用户只能访问自己的文档
                if role_id != 1:
                    chunk_sql += " AND d.user_id = %s"
                    chunk_params.append(user_id)
                
                chunk_results = execute_query_with_params(chunk_sql, chunk_params)
                
                # 构建结果列表，保持原有的相似度排序
                chunk_dict = {chunk['id']: chunk for chunk in chunk_results}
                
                for filtered_chunk in filtered_chunks:
                    chunk_id = filtered_chunk['chunk_id']
                    if chunk_id in chunk_dict:
                        chunk_data = chunk_dict[chunk_id]
                        results.append({
                            'chunk_id': chunk_id,
                            'content': chunk_data['content'],
                            'filename': chunk_data['filename'],
                            'similarity': filtered_chunk['similarity'],
                            'distance': filtered_chunk['distance'],
                            'metadata': None  # 当前表结构没有metadata字段
                        })

            logger.info(f"召回检索测试完成，返回 {len(results)} 个结果")
            
            return create_success_response({
                'results': results,
                'total_found': len(similar_chunks),
                'filtered_count': len(filtered_chunks),
                'knowledge_base': knowledge_name,
                'query': query,
                'retrieve_count': retrieve_count,
                'similarity_threshold': similarity_threshold
            })

        except Exception as vector_error:
            logger.error(f"向量检索失败: {str(vector_error)}", exc_info=True)
            return create_error_response(f"向量检索失败: {str(vector_error)}", 500)

    except ValueError as e:
        logger.error(f"召回检索测试数据解析错误: {str(e)}", exc_info=True)
        return create_error_response(str(e))
    except Exception as e:
        logger.error(f"召回检索测试异常: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500) 