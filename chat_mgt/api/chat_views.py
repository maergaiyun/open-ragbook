import json
import logging
import openai
from datetime import datetime
from django.conf import settings
from django.db import connection, transaction
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from open_ragbook_server.utils.auth_utils import (
    jwt_required, get_user_from_request, check_resource_permission,
    get_user_filter_condition, parse_json_body, validate_required_fields,
    create_error_response, create_success_response
)
from open_ragbook_server.utils.db_utils import (
    execute_query_with_params, execute_update_with_params,
    check_record_exists, get_record_by_id, get_last_insert_id,
    dict_fetchall, execute_query_sql, execute_sql
)
from knowledge_mgt.utils.document_processor import VectorStore
from account_mgt.utils.jwt_token_utils import parse_jwt_token

logger = logging.getLogger(__name__)


def get_user_from_token(request):
    """从JWT token中获取用户信息"""
    token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
    if not token:
        return None, JsonResponse({'status': 'error', 'message': '未授权访问'}, status=401)
    
    user_info = parse_jwt_token(token)
    if not user_info:
        return None, JsonResponse({'status': 'error', 'message': 'token无效'}, status=401)
    
    return user_info, None


@csrf_exempt
@require_http_methods(["POST"])
@jwt_required()
def retrieve_and_chat(request):
    """知识库对话API"""
    try:
        # 解析请求数据
        data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['query', 'knowledge_id', 'model_id']
        is_valid, missing_fields = validate_required_fields(data, required_fields)
        if not is_valid:
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        query = data.get('query')
        knowledge_id = data.get('knowledge_id')
        model_id = data.get('model_id')
        retrieve_count = data.get('retrieve_count', 3)
        similarity_threshold = data.get('similarity_threshold', 0.7)
        diversity = data.get('diversity', 0.7)
        conversation_id = data.get('conversation_id')

        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')

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
            return create_error_response('知识库不存在或无权限访问', 404)

        knowledge_info = kb_result[0]
        knowledge_name = knowledge_info['name']
        vector_dimension = knowledge_info['vector_dimension']
        index_type = knowledge_info['index_type']

        # 获取模型信息（检查用户权限）
        model_sql = """
            SELECT m.id, m.name, m.provider_id, m.model_type, m.api_key, m.base_url, 
                   m.is_public, m.created_by, p.name as provider_name 
            FROM llmmodel m 
            JOIN llmprovider p ON m.provider_id = p.id 
            WHERE m.id = %s
        """
        model_params = [model_id]
        
        # 普通用户只能使用公共模型和自己创建的模型
        if role_id != 1:
            model_sql += " AND (m.is_public = 1 OR m.created_by = %s)"
            model_params.append(user_id)
        
        model_result = execute_query_with_params(model_sql, model_params)
        if not model_result:
            return create_error_response('模型不存在或无权限使用', 404)

        model_info = model_result[0]
        model_name = model_info['name']
        model_type = model_info['model_type']
        api_key = model_info['api_key']
        base_url = model_info['base_url']
        provider_name = model_info['provider_name']

        # 获取对话历史（如果有）
        history = []
        if conversation_id:
            # 查询会话信息（检查用户权限）
            conv_sql = """
                SELECT id, title, knowledge_base_id, model_id, user_id 
                FROM chat_conversation 
                WHERE id = %s AND user_id = %s
            """
            conv_result = execute_query_with_params(conv_sql, [conversation_id, user_id])
            
            if conv_result:
                conversation_id = conv_result[0]['id']

                # 获取最近的几条消息作为上下文
                msg_sql = """
                    SELECT role, content 
                    FROM chat_message 
                    WHERE conversation_id = %s AND user_id = %s 
                    ORDER BY create_time DESC LIMIT 10
                """
                messages_result = execute_query_with_params(msg_sql, [conversation_id, user_id])

                # 将消息逆序（最早的消息在前）
                for msg in reversed(messages_result):
                    history.append({"role": msg['role'], "content": msg['content']})
            else:
                # 会话不存在，创建新会话
                conversation_id = None

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
                    filtered_chunks.append(chunk)
                    
            logger.info(f"检索到 {len(similar_chunks)} 个结果，过滤后保留 {len(filtered_chunks)} 个结果（相似度阈值: {similarity_threshold}）")

            # 6. 如果没有找到相似的文档分块，返回错误
            if not filtered_chunks:
                return create_error_response(f'没有找到相似度高于 {similarity_threshold} 的相关知识')
            
            # 使用过滤后的结果
            similar_chunks = filtered_chunks

            # 6. 查询对应的文档分块内容（需要检查用户权限）
            chunk_ids = [chunk['chunk_id'] for chunk in similar_chunks]
            
            if chunk_ids:
                # 构建IN查询的占位符
                placeholders = ','.join(['%s'] * len(chunk_ids))
                chunk_sql = f"""
                    SELECT dc.id, dc.content, d.filename, d.file_path
                    FROM knowledge_document_chunk dc
                    JOIN knowledge_document d ON dc.document_id = d.id
                    WHERE dc.id IN ({placeholders}) AND d.database_id = %s
                """
                chunk_params = chunk_ids + [knowledge_id]
                
                # 权限检查：管理员可以访问所有文档，普通用户只能访问自己知识库中的文档
                if role_id != 1:
                    # 普通用户需要检查知识库所有权，而不是文档所有权
                    # 如果用户有权限访问知识库，就可以访问其中的所有文档
                    kb_owner_sql = "SELECT user_id FROM knowledge_database WHERE id = %s"
                    kb_owner_result = execute_query_with_params(kb_owner_sql, [knowledge_id])
                    if kb_owner_result and kb_owner_result[0]['user_id'] != user_id:
                        # 用户不是知识库所有者，无权访问
                        logger.warning(f"用户 {user_id} 无权访问知识库 {knowledge_id} 中的文档")
                        return create_error_response('无权限访问该知识库中的文档', 403)
                
                chunk_results = execute_query_with_params(chunk_sql, chunk_params)
                
                # 检查查询结果
                if not chunk_results:
                    logger.warning(f"未能查询到文档分块内容，chunk_ids: {chunk_ids}")
                    return create_error_response('未能获取文档内容，请检查数据完整性', 500)
                
                # 构建上下文
                context_parts = []
                for chunk_result in chunk_results:
                    content = chunk_result['content']
                    filename = chunk_result['filename']
                    context_parts.append(f"来源：{filename}\n内容：{content}")

                context = "\n\n".join(context_parts)
                
                if not context.strip():
                    logger.warning("构建的上下文为空")
                    return create_error_response('检索到的文档内容为空', 500)

                # 7. 构建提示词
                system_prompt = f"""你是一个基于知识库的智能助手。请根据以下知识库内容回答用户的问题。

知识库名称：{knowledge_name}
检索到的相关内容：
{context}

请注意：
1. 请基于提供的知识库内容进行回答
2. 如果知识库内容不足以回答问题，请明确说明
3. 回答要准确、简洁、有条理
4. 可以适当引用知识库中的具体内容"""

                # 8. 构建消息列表
                messages = [{"role": "system", "content": system_prompt}]
                
                # 添加历史对话
                messages.extend(history)
                
                # 添加当前用户问题
                messages.append({"role": "user", "content": query})

                # 9. 调用LLM生成回答
                try:
                    client = openai.OpenAI(
                        api_key=api_key,
                        base_url=base_url if base_url else None
                    )
                    
                    response = client.chat.completions.create(
                        model=model_type,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=2000
                    )
                    
                    assistant_response = response.choices[0].message.content
                    
                    # 10. 保存对话记录
                    with transaction.atomic():
                        # 如果没有会话ID，创建新会话
                        if not conversation_id:
                            conv_title = query[:50] + "..." if len(query) > 50 else query
                            conv_sql = """
                                INSERT INTO chat_conversation 
                                (title, knowledge_base_id, knowledge_base_name, model_id, model_name, user_id, username, create_time, update_time)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                            """
                            username = user_info.get('user_name', '')
                            affected_rows = execute_update_with_params(conv_sql, [conv_title, knowledge_id, knowledge_name, model_id, model_name, user_id, username])
                            if affected_rows <= 0:
                                logger.error("创建会话失败")
                                return create_error_response("创建会话失败", 500)
                            
                            conversation_id = get_last_insert_id()
                            logger.info(f"创建新会话，ID: {conversation_id}")
                            
                            if not conversation_id:
                                logger.error("获取会话ID失败")
                                return create_error_response("获取会话ID失败", 500)

                        # 验证会话是否存在
                        conv_check_sql = "SELECT id FROM chat_conversation WHERE id = %s AND user_id = %s"
                        conv_check_result = execute_query_with_params(conv_check_sql, [conversation_id, user_id])
                        if not conv_check_result:
                            logger.error(f"会话ID {conversation_id} 不存在或无权限访问")
                            return create_error_response("会话不存在或无权限访问", 404)

                        # 保存用户消息
                        user_msg_sql = """
                            INSERT INTO chat_message 
                            (conversation_id, role, content, user_id, create_time)
                            VALUES (%s, %s, %s, %s, NOW())
                        """
                        user_affected = execute_update_with_params(user_msg_sql, [conversation_id, 'user', query, user_id])
                        if user_affected <= 0:
                            logger.error(f"保存用户消息失败, conversation_id: {conversation_id}")
                            return create_error_response("保存用户消息失败", 500)

                        # 保存助手回复
                        assistant_msg_sql = """
                            INSERT INTO chat_message 
                            (conversation_id, role, content, user_id, create_time)
                            VALUES (%s, %s, %s, %s, NOW())
                        """
                        assistant_affected = execute_update_with_params(assistant_msg_sql, [conversation_id, 'assistant', assistant_response, user_id])
                        if assistant_affected <= 0:
                            logger.error(f"保存助手消息失败, conversation_id: {conversation_id}")
                            return create_error_response("保存助手消息失败", 500)

                        # 更新会话的最后更新时间
                        update_conv_sql = "UPDATE chat_conversation SET update_time = NOW() WHERE id = %s"
                        execute_update_with_params(update_conv_sql, [conversation_id])

                    # 11. 构建检索到的文档信息
                    retrieved_docs = []
                    for chunk in similar_chunks:
                        chunk_id = chunk['chunk_id']
                        # 查找对应的文档内容
                        for chunk_data in chunk_results:
                            if chunk_data['id'] == chunk_id:
                                retrieved_docs.append({
                                    'content': chunk_data['content'],
                                    'source': chunk_data['file_path'] or chunk_data['filename'],
                                    'title': chunk_data['filename'],
                                    'similarity_score': 1.0 / (1.0 + chunk['distance']) if chunk['distance'] >= 0 else 0.0
                                })
                                break

                    # 12. 返回结果
                    return create_success_response({
                        'answer': assistant_response,
                        'conversation_id': conversation_id,
                        'retrieved_docs': retrieved_docs,
                        'knowledge_base': knowledge_name,
                        'model': model_name,
                        'provider': provider_name
                    })

                except Exception as llm_error:
                    logger.error(f"LLM调用失败: {str(llm_error)}")
                    return create_error_response(f"模型调用失败: {str(llm_error)}", 500)
            else:
                return create_error_response('没有找到相关的文档内容')

        except Exception as vector_error:
            logger.error(f"向量检索失败: {str(vector_error)}")
            return create_error_response(f"向量检索失败: {str(vector_error)}", 500)

    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        logger.error(f"对话处理异常: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@csrf_exempt
@require_http_methods(["GET"])
@jwt_required()
def chat_history_list(request):
    """获取对话历史列表"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        # 获取分页参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        # 查询对话列表
        sql = """
            SELECT 
                c.id, 
                c.title, 
                c.knowledge_base_id, 
                c.model_id, 
                c.create_time, 
                c.update_time,
                kb.name as knowledge_base_name,
                m.name as model_name
            FROM chat_conversation c
            LEFT JOIN knowledge_database kb ON c.knowledge_base_id = kb.id
            LEFT JOIN llmmodel m ON c.model_id = m.id
            WHERE c.user_id = %s
            ORDER BY c.update_time DESC
            LIMIT %s OFFSET %s
        """
        
        offset = (page - 1) * page_size
        conversations = execute_query_with_params(sql, [user_id, page_size, offset])
        
        # 获取总数
        count_sql = "SELECT COUNT(*) as total FROM chat_conversation WHERE user_id = %s"
        count_result = execute_query_with_params(count_sql, [user_id])
        total = count_result[0]['total'] if count_result else 0
        
        return create_success_response({
            'conversations': conversations,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        })
        
    except Exception as e:
        logger.error(f"获取对话历史列表异常: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@csrf_exempt
@require_http_methods(["GET"])
@jwt_required()
def chat_history_detail(request, conversation_id):
    """获取对话详情"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        # 查询会话信息
        conv_sql = """
            SELECT 
                c.id, 
                c.title, 
                c.knowledge_base_id, 
                c.model_id, 
                c.create_time, 
                c.update_time,
                kb.name as knowledge_base_name,
                m.name as model_name
            FROM chat_conversation c
            LEFT JOIN knowledge_database kb ON c.knowledge_base_id = kb.id
            LEFT JOIN llmmodel m ON c.model_id = m.id
            WHERE c.id = %s AND c.user_id = %s
        """
        
        conv_result = execute_query_with_params(conv_sql, [conversation_id, user_id])
        if not conv_result:
            return create_error_response('对话不存在或无权限访问', 404)
        
        conversation = conv_result[0]
        
        # 查询消息列表
        msg_sql = """
            SELECT id, role, content, create_time
            FROM chat_message
            WHERE conversation_id = %s AND user_id = %s
            ORDER BY create_time ASC
        """
        
        messages = execute_query_with_params(msg_sql, [conversation_id, user_id])
        
        return create_success_response({
            'conversation': conversation,
            'messages': messages
        })
        
    except Exception as e:
        logger.error(f"获取对话详情异常: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@csrf_exempt
@require_http_methods(["DELETE"])
@jwt_required()
def chat_history_delete(request, conversation_id):
    """删除对话"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        # 检查会话是否存在且属于当前用户
        conv_record = get_record_by_id('chat_conversation', conversation_id)
        if not conv_record:
            return create_error_response('对话不存在', 404)
        
        if conv_record['user_id'] != user_id:
            return create_error_response('对话不存在或无权限操作', 404)
        
        # 删除对话及相关消息
        with transaction.atomic():
            # 删除消息
            msg_sql = "DELETE FROM chat_message WHERE conversation_id = %s AND user_id = %s"
            execute_update_with_params(msg_sql, [conversation_id, user_id])
            
            # 删除会话
            conv_sql = "DELETE FROM chat_conversation WHERE id = %s AND user_id = %s"
            affected_rows = execute_update_with_params(conv_sql, [conversation_id, user_id])
            
            if affected_rows > 0:
                return create_success_response()
            else:
                return create_error_response('删除失败', 500)
        
    except Exception as e:
        logger.error(f"删除对话异常: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)
