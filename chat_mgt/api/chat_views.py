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

from open_ragbook_server.utils.db_utils import dict_fetchall, execute_query_sql, execute_sql
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
def retrieve_and_chat(request):
    """知识库对话API
    
    Args:
        request: HTTP请求
        
    Returns:
        JsonResponse: 响应结果
    """
    # JWT token验证
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        data = json.loads(request.body)
        query = data.get('query')
        knowledge_id = data.get('knowledge_id')
        model_id = data.get('model_id')
        retrieve_count = data.get('retrieve_count', 3)
        similarity_threshold = data.get('similarity_threshold', 0.7)
        diversity = data.get('diversity', 0.7)
        conversation_id = data.get('conversation_id')

        # 检查必要参数
        if not query:
            return JsonResponse({'status': 'error', 'message': '查询内容不能为空'}, status=400)

        if not knowledge_id:
            return JsonResponse({'status': 'error', 'message': '请选择知识库'}, status=400)

        if not model_id:
            return JsonResponse({'status': 'error', 'message': '请选择模型'}, status=400)

        # 获取知识库和模型信息（需要检查用户权限）
        with connection.cursor() as cursor:
            # 查询知识库信息（检查用户权限）
            if role_id == 1:  # 管理员
                cursor.execute(
                    "SELECT id, name, description, vector_dimension, index_type FROM knowledge_database WHERE id = %s",
                    [knowledge_id]
                )
            else:  # 普通用户
                cursor.execute(
                    "SELECT id, name, description, vector_dimension, index_type FROM knowledge_database WHERE id = %s AND user_id = %s",
                    [knowledge_id, user_id]
                )
            
            kb_result = cursor.fetchone()
            if not kb_result:
                return JsonResponse({'status': 'error', 'message': '知识库不存在或无权限访问'}, status=404)

            knowledge_name = kb_result[1]
            vector_dimension = kb_result[3]
            index_type = kb_result[4]

            # 查询模型信息（检查用户权限）
            if role_id == 1:  # 管理员
                cursor.execute(
                    """
                    SELECT m.id, m.name, m.provider_id, m.model_type, m.api_key, m.base_url, 
                           p.name as provider_name 
                    FROM llmmodel m 
                    JOIN llmprovider p ON m.provider_id = p.id 
                    WHERE m.id = %s
                    """,
                    [model_id]
                )
            else:  # 普通用户
                cursor.execute(
                    """
                    SELECT m.id, m.name, m.provider_id, m.model_type, m.api_key, m.base_url, 
                           p.name as provider_name 
                    FROM llmmodel m 
                    JOIN llmprovider p ON m.provider_id = p.id 
                    WHERE m.id = %s AND m.user_id = %s
                    """,
                    [model_id, user_id]
                )
            
            model_result = cursor.fetchone()
            if not model_result:
                return JsonResponse({'status': 'error', 'message': '模型不存在或无权限使用'}, status=404)

            model_name = model_result[1]
            model_type = model_result[3]
            api_key = model_result[4]
            base_url = model_result[5]
            provider_name = model_result[6]

        # 获取对话历史（如果有）
        history = []
        if conversation_id:
            with connection.cursor() as cursor:
                # 查询会话信息（检查用户权限）
                cursor.execute(
                    "SELECT id, title, knowledge_base_id, model_id, user_id FROM chat_conversation WHERE id = %s AND user_id = %s",
                    [conversation_id, user_id]
                )
                conv_result = cursor.fetchone()
                if conv_result:
                    conversation_id = conv_result[0]

                    # 获取最近的几条消息作为上下文
                    cursor.execute(
                        "SELECT role, content FROM chat_message WHERE conversation_id = %s AND user_id = %s ORDER BY create_time DESC LIMIT 10",
                        [conversation_id, user_id]
                    )
                    messages_result = cursor.fetchall()

                    # 将消息逆序（最早的消息在前）
                    for role, content in reversed(messages_result):
                        history.append({"role": role, "content": content})
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
                return JsonResponse({'status': 'error', 'message': '没有加载的嵌入模型，请先在系统管理中加载嵌入模型'}, status=500)
            
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
            # 将L2距离转换为相似度分数进行过滤
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
                return JsonResponse({'status': 'error', 'message': f'没有找到相似度高于 {similarity_threshold} 的相关知识'}, status=200)
            
            # 使用过滤后的结果
            similar_chunks = filtered_chunks

            # 6. 查询对应的文档分块内容（需要检查用户权限）
            chunk_ids = [chunk['chunk_id'] for chunk in similar_chunks]
            chunk_id_placeholders = ', '.join(['%s'] * len(chunk_ids))

            with connection.cursor() as cursor:
                if role_id == 1:  # 管理员
                    cursor.execute(
                        f"""
                        SELECT c.id, c.content, d.filename, d.file_path 
                        FROM knowledge_document_chunk c
                        JOIN knowledge_document d ON c.document_id = d.id
                        WHERE c.id IN ({chunk_id_placeholders})
                        """,
                        chunk_ids
                    )
                else:  # 普通用户
                    cursor.execute(
                        f"""
                        SELECT c.id, c.content, d.filename, d.file_path 
                        FROM knowledge_document_chunk c
                        JOIN knowledge_document d ON c.document_id = d.id
                        WHERE c.id IN ({chunk_id_placeholders}) AND d.user_id = %s
                        """,
                        chunk_ids + [user_id]
                    )

                # 将查询结果转换为文档列表，并添加相似度信息
                retrieved_docs = []
                chunk_similarity_map = {chunk['chunk_id']: chunk['distance'] for chunk in similar_chunks}
                
                for row in cursor.fetchall():
                    chunk_id, content, filename, file_path = row
                    distance = chunk_similarity_map.get(chunk_id, 0.0)
                    # 将L2距离转换为相似度分数 (0-1之间，1表示最相似)
                    # 使用公式: similarity = 1 / (1 + distance)
                    similarity_score = 1.0 / (1.0 + distance) if distance >= 0 else 0.0
                    
                    retrieved_docs.append({
                        "id": chunk_id,
                        "title": filename,
                        "content": content[:1000],  # 限制内容长度
                        "source": file_path or f"文档ID: {chunk_id}",
                        "similarity_score": round(similarity_score, 4),  # 保留4位小数
                        "distance": round(distance, 4)  # 原始距离值
                    })

            if not retrieved_docs:
                return JsonResponse({'status': 'error', 'message': '无法获取分块内容'}, status=500)

        except Exception as e:
            logger.error(f"向量检索出错: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'向量检索出错: {str(e)}'}, status=500)

        # 构建给模型的提示
        context = "\n\n".join([f"标题: {doc['title']}\n内容: {doc['content']}" for doc in retrieved_docs])

        system_prompt = (
            "你是一个基于知识库的AI助手。请根据提供的知识库内容回答用户的问题。"
            "如果知识库中的信息不足以回答问题，请直接说明无法回答，不要编造信息。"
            "回答要简洁明了，有条理，并引用相关的知识来源。"
        )

        user_prompt = f"""
基于以下知识库内容回答问题：

知识库内容：
{context}

用户问题：{query}

请基于上述知识库内容回答问题。如果知识库中没有相关信息，请明确说明。
"""

        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]

        # 添加历史对话
        messages.extend(history)

        # 添加当前问题
        messages.append({"role": "user", "content": user_prompt})

        # 调用大模型
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
            
            answer = response.choices[0].message.content
            
            # 保存对话记录
            if not conversation_id:
                # 创建新的对话
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO chat_conversation (title, knowledge_base_id, knowledge_base_name, model_id, model_name, user_id, create_time, update_time)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                        """,
                        [query[:50] + "..." if len(query) > 50 else query, knowledge_id, knowledge_name, model_id, model_name, user_id]
                    )
                    conversation_id = cursor.lastrowid

            # 保存用户消息和AI回复
            with connection.cursor() as cursor:
                # 保存用户消息
                cursor.execute(
                    """
                    INSERT INTO chat_message (conversation_id, role, content, user_id, create_time)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    [conversation_id, 'user', query, user_id]
                )
                
                # 保存AI回复
                cursor.execute(
                    """
                    INSERT INTO chat_message (conversation_id, role, content, user_id, create_time)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    [conversation_id, 'assistant', answer, user_id]
                )
                
            return JsonResponse({
                'status': 'success',
                'data': {
                    'answer': answer,
                    'retrieved_docs': retrieved_docs,
                    'conversation_id': conversation_id,
                    'knowledge_name': knowledge_name,
                    'model_name': model_name,
                    'provider_name': provider_name
                }
            })

        except Exception as e:
            logger.error(f"调用大模型出错: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'调用大模型出错: {str(e)}'}, status=500)

    except Exception as e:
        logger.error(f"对话处理出错: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'对话处理出错: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def chat_history_list(request):
    """获取对话历史列表"""
    # JWT token验证
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))

        with connection.cursor() as cursor:
            # 查询总数
            cursor.execute(
                "SELECT COUNT(*) FROM chat_conversation WHERE user_id = %s",
                [user_id]
            )
            total = cursor.fetchone()[0]

            # 查询数据
            offset = (page - 1) * page_size
            cursor.execute(
                """
                SELECT c.id, c.title, c.knowledge_base_id, c.model_id, c.create_time, c.update_time,
                       k.name as knowledge_name, m.name as model_name
                FROM chat_conversation c
                LEFT JOIN knowledge_database k ON c.knowledge_base_id = k.id
                LEFT JOIN llmmodel m ON c.model_id = m.id
                WHERE c.user_id = %s
                ORDER BY c.update_time DESC
                LIMIT %s OFFSET %s
                """,
                [user_id, page_size, offset]
            )

            columns = [col[0] for col in cursor.description]
            conversations = []
            for row in cursor.fetchall():
                conv_dict = dict(zip(columns, row))
                # 格式化时间
                if conv_dict['create_time']:
                    conv_dict['create_time'] = conv_dict['create_time'].strftime('%Y-%m-%d %H:%M:%S')
                if conv_dict['update_time']:
                    conv_dict['update_time'] = conv_dict['update_time'].strftime('%Y-%m-%d %H:%M:%S')
                conversations.append(conv_dict)

        return JsonResponse({
            'status': 'success',
            'data': {
                'conversations': conversations,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
        })

    except Exception as e:
        logger.error(f"获取对话历史列表出错: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'获取对话历史列表出错: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def chat_history_detail(request, conversation_id):
    """获取对话详情"""
    # JWT token验证
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    
    try:
        with connection.cursor() as cursor:
            # 查询对话信息
            cursor.execute(
                """
                SELECT c.id, c.title, c.knowledge_base_id, c.model_id, c.create_time, c.update_time,
                       k.name as knowledge_name, m.name as model_name
                FROM chat_conversation c
                LEFT JOIN knowledge_database k ON c.knowledge_base_id = k.id
                LEFT JOIN llmmodel m ON c.model_id = m.id
                WHERE c.id = %s AND c.user_id = %s
                """,
                [conversation_id, user_id]
            )
            
            conv_result = cursor.fetchone()
            if not conv_result:
                return JsonResponse({'status': 'error', 'message': '对话不存在或无权限访问'}, status=404)

            columns = [col[0] for col in cursor.description]
            conversation = dict(zip(columns, conv_result))

            # 格式化时间
            if conversation['create_time']:
                conversation['create_time'] = conversation['create_time'].strftime('%Y-%m-%d %H:%M:%S')
            if conversation['update_time']:
                conversation['update_time'] = conversation['update_time'].strftime('%Y-%m-%d %H:%M:%S')

            # 查询消息列表
            cursor.execute(
                """
                SELECT id, role, content, create_time
                FROM chat_message
                WHERE conversation_id = %s AND user_id = %s
                ORDER BY create_time ASC
                """,
                [conversation_id, user_id]
            )
            
            messages = []
            for row in cursor.fetchall():
                msg_id, role, content, create_time = row
                messages.append({
                    'id': msg_id,
                    'role': role,
                    'content': content,
                    'create_time': create_time.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            conversation['messages'] = messages
            
        return JsonResponse({
            'status': 'success',
            'data': conversation
        })

    except Exception as e:
        logger.error(f"获取对话详情出错: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'获取对话详情出错: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def chat_history_delete(request, conversation_id):
    """删除对话"""
    # JWT token验证
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    
    try:
        with connection.cursor() as cursor:
            # 检查对话是否存在且属于当前用户
            cursor.execute(
                "SELECT id FROM chat_conversation WHERE id = %s AND user_id = %s",
                [conversation_id, user_id]
            )
            
            if not cursor.fetchone():
                return JsonResponse({'status': 'error', 'message': '对话不存在或无权限删除'}, status=404)

            # 删除对话消息
            cursor.execute(
                "DELETE FROM chat_message WHERE conversation_id = %s AND user_id = %s",
                [conversation_id, user_id]
            )

            # 删除对话
            cursor.execute(
                "DELETE FROM chat_conversation WHERE id = %s AND user_id = %s",
                [conversation_id, user_id]
            )
            
            return JsonResponse({
                'status': 'success',
                'message': '对话删除成功'
            })

    except Exception as e:
        logger.error(f"删除对话出错: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'删除对话出错: {str(e)}'}, status=500)
