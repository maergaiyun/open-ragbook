import json
import logging
import os
from django.db import connection, transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from open_ragbook_server.utils.response_code import *
from open_ragbook_server.utils.db_utils import fetch_paginated_data, dict_fetchall
from knowledge_mgt.utils.document_processor import DocumentProcessor, VectorStore
from knowledge_mgt.utils.embeddings import EmbeddingModel

# 获取模块日志记录器
logger = logging.getLogger('knowledge_mgt')


@require_http_methods(["GET"])
@csrf_exempt
def document_list(request):
    """获取文档列表"""
    try:
        # 从请求中获取查询参数
        database_id = request.GET.get('database_id')
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))

        if not database_id:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="缺少必要参数: database_id"),
                status=400
            )

        # 查询条件
        conditions = {"database_id": database_id}

        # 查询文档
        total_records, documents = fetch_paginated_data(
            table_name="knowledge_document",
            conditions=conditions,
            order_by="create_time DESC",
            page=page,
            page_size=page_size
        )

        logger.info(f"查询知识库 {database_id} 的文档列表，共 {total_records} 条记录")

        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(data={
                "data": documents,
                "total_records": total_records
            }),
            status=200
        )
    except Exception as e:
        logger.error(f"查询文档列表出错: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=str(e)),
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
def document_chunks(request, doc_id):
    """获取文档的分块列表"""
    try:
        # 从请求中获取查询参数
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))

        # 先查询文档是否存在
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, database_id, filename 
                FROM knowledge_document 
                WHERE id = %s
            """, [doc_id])

            document = cursor.fetchone()
            if not document:
                logger.warning(f"查询分块列表失败: 文档 {doc_id} 不存在")
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="文档不存在"),
                    status=404
                )

            document_info = {
                "id": document[0],
                "database_id": document[1],
                "filename": document[2]
            }

        # 查询分块总数
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM knowledge_document_chunk 
                WHERE document_id = %s
            """, [doc_id])

            total_chunks = cursor.fetchone()[0]

        # 查询分块列表
        offset = (page - 1) * page_size
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, chunk_index, content, vector_id, create_time 
                FROM knowledge_document_chunk 
                WHERE document_id = %s 
                ORDER BY chunk_index 
                LIMIT %s OFFSET %s
            """, [doc_id, page_size, offset])

            chunks = [
                {
                    "id": row[0],
                    "chunk_index": row[1],
                    "content": row[2],
                    "vector_id": row[3],
                    "create_time": row[4].strftime("%Y-%m-%d %H:%M:%S") if row[4] else None
                }
                for row in cursor.fetchall()
            ]

        logger.info(f"查询文档 {doc_id} 的分块列表，共 {total_chunks} 个分块")

        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(data={
                "document": document_info,
                "chunks": chunks,
                "total_chunks": total_chunks
            }),
            status=200
        )
    except Exception as e:
        logger.error(f"查询文档分块列表出错: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=str(e)),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
def document_upload(request):
    """上传并处理文档"""
    try:
        # 获取表单数据
        database_id = request.POST.get('database_id')
        chunking_method = request.POST.get('chunking_method', 'token')
        chunk_size = int(request.POST.get('chunk_size', 500))
        similarity_threshold = float(request.POST.get('similarity_threshold', 0.7))
        overlap_size = int(request.POST.get('overlap_size', 100))
        file = request.FILES.get('file')

        # 验证参数
        if not database_id or not file:
            logger.warning("上传文档失败: 缺少必要参数")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="缺少必要参数"),
                status=400
            )

        # 验证文件格式 - 只支持txt
        file_extension = os.path.splitext(file.name)[1].lower()
        if file_extension != '.txt':
            logger.warning(f"上传文档失败: 不支持的文件格式 {file_extension}")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="只支持上传 .txt 格式的文件"),
                status=400
            )

        # 验证文件大小 - 不超过5MB
        max_size = 5 * 1024 * 1024  # 5MB
        if file.size > max_size:
            logger.warning(f"上传文档失败: 文件大小超限 {file.size} bytes")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="文件大小不能超过 5MB"),
                status=400
            )

        # 获取用户信息
        user_id = request.user.id if hasattr(request, 'user') and hasattr(request.user, 'id') else None
        username = request.user.username if hasattr(request, 'user') and hasattr(request.user, 'username') else None

        if not user_id or not username:
            logger.warning(f"无法获取用户信息: user_id={user_id}, username={username}")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="无法获取用户信息"),
                status=401
            )

        # 查询知识库信息
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT name, vector_dimension, index_type 
                FROM knowledge_database 
                WHERE id = %s
            """, [database_id])

            db_info = cursor.fetchone()
            if not db_info:
                logger.warning(f"上传文档失败: 知识库 {database_id} 不存在")
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="知识库不存在"),
                    status=404
                )

            db_name, vector_dimension, index_type = db_info

        # 初始化文档处理器
        document_processor = DocumentProcessor(
            chunking_method=chunking_method, 
            chunk_size=chunk_size,
            similarity_threshold=similarity_threshold,
            overlap_size=overlap_size
        )

        # 保存文件
        file_info = document_processor.save_file(file, database_id)
        logger.info(f"保存文件: {file_info['filename']}")

        # 处理文档内容
        doc_text = document_processor.process_document(file_info['file_path'])
        if not doc_text or doc_text.startswith("处理文档失败"):
            logger.error(f"处理文档内容失败: {file_info['filename']}")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message=f"处理文档内容失败: {doc_text}"),
                status=500
            )

        # 文本分块
        chunks = document_processor.split_text(doc_text)
        chunk_count = len(chunks)

        if chunk_count == 0:
            logger.warning(f"文档分块失败，未生成有效分块: {file_info['filename']}")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="文档分块失败，未生成有效分块"),
                status=500
            )

        logger.info(f"文档 {file_info['filename']} 分割为 {chunk_count} 个分块")

        # 获取当前加载的本地嵌入模型
        from knowledge_mgt.utils.embeddings import local_embedding_manager
        embedding_model = local_embedding_manager.get_current_model()
        
        if embedding_model is None:
            logger.error("没有加载的嵌入模型，无法处理文档")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="没有加载的嵌入模型，请先在系统管理中加载嵌入模型"),
                status=500
            )

        # 获取嵌入模型的实际维度
        actual_dimension = embedding_model.get_dimension()
        logger.debug(f"嵌入模型实际维度: {actual_dimension}, 知识库配置维度: {vector_dimension}")

        # 初始化向量存储，使用实际维度
        vector_store = VectorStore(vector_dimension=actual_dimension, index_type=index_type)

        # 开始事务
        with transaction.atomic():
            # 1. 添加文档记录
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO knowledge_document 
                    (database_id, filename, file_path, file_type, file_size, 
                     chunking_method, chunk_size, similarity_threshold, overlap_size, 
                     chunk_count, user_id, username)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    database_id, file_info['filename'], file_info['file_path'],
                    file_info['file_type'], file_info['file_size'],
                    chunking_method, chunk_size, similarity_threshold, overlap_size,
                    chunk_count, user_id, username
                ])

                # 获取新插入的文档ID
                cursor.execute("SELECT LAST_INSERT_ID()")
                document_id = cursor.fetchone()[0]

            # 2. 添加文档分块记录
            chunk_ids = []
            for i, chunk_text in enumerate(chunks):
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO knowledge_document_chunk 
                        (document_id, database_id, chunk_index, content)
                        VALUES (%s, %s, %s, %s)
                    """, [document_id, database_id, i, chunk_text])

                    # 获取分块ID
                    cursor.execute("SELECT LAST_INSERT_ID()")
                    chunk_id = cursor.fetchone()[0]
                    chunk_ids.append(chunk_id)

            # 3. 生成向量并存储
            # 创建或获取向量库
            vector_store.create_index(database_id)

            # 生成向量
            vectors = embedding_model.embed_texts(chunks)

            # 添加到向量库
            vector_ids = vector_store.add_vectors(database_id, chunk_ids, vectors)

            # 4. 更新分块的向量ID
            if vector_ids:
                for i, chunk_id in enumerate(chunk_ids):
                    vector_id = i if i < len(vector_ids) else None
                    if vector_id is not None:
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                UPDATE knowledge_document_chunk 
                                SET vector_id = %s
                                WHERE id = %s
                            """, [str(vector_id), chunk_id])

            # 5. 更新知识库的文档数量
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE knowledge_database 
                    SET doc_count = doc_count + 1
                    WHERE id = %s
                """, [database_id])

        logger.info(f"文档 {file_info['filename']} 上传处理完成，ID={document_id}")

        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(data={
                "document_id": document_id,
                "chunk_count": chunk_count
            }),
            status=201
        )
    except Exception as e:
        logger.error(f"上传处理文档失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=str(e)),
            status=500
        )


@require_http_methods(["DELETE"])
@csrf_exempt
def document_delete(request, doc_id):
    """删除文档"""
    try:
        # 查询文档信息
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT database_id, file_path 
                FROM knowledge_document 
                WHERE id = %s
            """, [doc_id])

            doc_info = cursor.fetchone()
            if not doc_info:
                logger.warning(f"删除文档失败: 文档 {doc_id} 不存在")
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="文档不存在"),
                    status=404
                )

            database_id, file_path = doc_info

        # 查询所有分块ID
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id FROM knowledge_document_chunk 
                WHERE document_id = %s
            """, [doc_id])

            chunk_ids = [row[0] for row in cursor.fetchall()]

        # 开始事务
        with transaction.atomic():
            # 1. 从向量库中删除向量
            if chunk_ids:
                vector_store = VectorStore()
                vector_store.delete_chunks(database_id, chunk_ids)

            # 2. 删除文档分块记录
            with connection.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM knowledge_document_chunk 
                    WHERE document_id = %s
                """, [doc_id])

            # 3. 删除文档记录
            with connection.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM knowledge_document 
                    WHERE id = %s
                """, [doc_id])

            # 4. 更新知识库的文档数量
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE knowledge_database 
                    SET doc_count = GREATEST(doc_count - 1, 0)
                    WHERE id = %s
                """, [database_id])

        # 删除文件
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"已删除文件: {file_path}")

        logger.info(f"已删除文档: ID={doc_id}, 删除了 {len(chunk_ids)} 个分块")

        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(),
            status=200
        )
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=str(e)),
            status=500
        )
