import json
import logging
import os
import uuid
import threading
import time
from datetime import datetime
from django.db import connection, transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from open_ragbook_server.utils.response_code import *
from open_ragbook_server.utils.auth_utils import (
    jwt_required, get_user_from_request,
    parse_json_body, validate_required_fields,
    create_error_response, create_success_response
)
from open_ragbook_server.utils.db_utils import execute_query_with_params
from knowledge_mgt.utils.document_processor import DocumentProcessor, VectorStore

# 获取模块日志记录器
logger = logging.getLogger('knowledge_mgt')

# 全局任务处理锁，确保同时只有一个任务在处理
task_processing_lock = threading.Lock()
current_processing_task = None

# 队列状态缓存
queue_status_cache = {
    'data': None,
    'last_update': 0,
    'cache_duration': 5  # 缓存5秒
}


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def create_upload_task(request):
    """创建文档上传任务"""
    try:
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        username = user_info.get('user_name')

        # 获取表单数据
        database_id = request.POST.get('database_id')
        chunking_method = request.POST.get('chunking_method', 'token')
        chunk_size = int(request.POST.get('chunk_size', 500))
        similarity_threshold = float(request.POST.get('similarity_threshold', 0.7))
        overlap_size = int(request.POST.get('overlap_size', 100))
        custom_delimiter = request.POST.get('custom_delimiter', '\n\n')
        window_size = int(request.POST.get('window_size', 3))
        step_size = int(request.POST.get('step_size', 1))
        min_chunk_size = int(request.POST.get('min_chunk_size', 50))
        max_chunk_size = int(request.POST.get('max_chunk_size', 2000))
        file = request.FILES.get('file')

        # 验证参数
        if not database_id or not file:
            return create_error_response("缺少必要参数", 400)

        # 验证文件格式
        file_extension = os.path.splitext(file.name)[1].lower()
        if file_extension != '.txt':
            return create_error_response("只支持上传 .txt 格式的文件", 400)

        # 验证文件大小
        max_size = 5 * 1024 * 1024  # 5MB
        if file.size > max_size:
            return create_error_response("文件大小不能超过 5MB", 400)

        # 验证知识库是否存在
        kb_sql = "SELECT id, name FROM knowledge_database WHERE id = %s"
        kb_params = [database_id]
        
        # 普通用户只能访问自己的知识库
        if user_info.get('role_id') != 1:
            kb_sql += " AND user_id = %s"
            kb_params.append(user_id)
        
        kb_result = execute_query_with_params(kb_sql, kb_params)
        if not kb_result:
            return create_error_response('知识库不存在或无权限访问', 404)

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 保存文件
        document_processor = DocumentProcessor()
        file_info = document_processor.save_file(file, database_id)
        
        # 创建上传任务记录
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO document_upload_task 
                (task_id, user_id, username, database_id, filename, file_path, file_size,
                 chunking_method, chunk_size, similarity_threshold, overlap_size,
                 custom_delimiter, window_size, step_size, min_chunk_size, max_chunk_size,
                 status, progress)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                task_id, user_id, username, database_id, file_info['filename'], 
                file_info['file_path'], file_info['file_size'],
                chunking_method, chunk_size, similarity_threshold, overlap_size,
                custom_delimiter, window_size, step_size, min_chunk_size, max_chunk_size,
                'pending', 0
            ])

        logger.info(f"创建文档上传任务: {task_id}, 文件: {file_info['filename']}")

        # 启动异步处理任务
        threading.Thread(target=process_upload_task, args=(task_id,), daemon=True).start()

        return create_success_response({
            "task_id": task_id,
            "filename": file_info['filename'],
            "status": "pending"
        })

    except Exception as e:
        logger.error(f"创建上传任务失败: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def get_upload_tasks(request):
    """获取用户的上传任务列表"""
    try:
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')

        # 构建查询SQL
        sql = """
            SELECT t.task_id, t.filename, t.status, t.progress, t.error_message,
                   t.chunk_count, t.created_at, t.updated_at, t.started_at, t.completed_at,
                   k.name as database_name
            FROM document_upload_task t
            LEFT JOIN knowledge_database k ON t.database_id = k.id
        """
        params = []

        # 普通用户只能看自己的任务
        if role_id != 1:
            sql += " WHERE t.user_id = %s"
            params.append(user_id)

        sql += " ORDER BY t.created_at DESC LIMIT 50"

        tasks = execute_query_with_params(sql, params)

        # 格式化时间字段
        for task in tasks:
            for time_field in ['created_at', 'updated_at', 'started_at', 'completed_at']:
                if task[time_field]:
                    task[time_field] = task[time_field].strftime("%Y-%m-%d %H:%M:%S")

        return create_success_response({"tasks": tasks})

    except Exception as e:
        logger.error(f"获取上传任务列表失败: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def get_task_status(request, task_id):
    """获取特定任务的状态"""
    try:
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')

        # 构建查询SQL
        sql = """
            SELECT task_id, filename, status, progress, error_message, chunk_count,
                   created_at, updated_at, started_at, completed_at, document_id
            FROM document_upload_task
            WHERE task_id = %s
        """
        params = [task_id]

        # 普通用户只能查看自己的任务
        if role_id != 1:
            sql += " AND user_id = %s"
            params.append(user_id)

        tasks = execute_query_with_params(sql, params)
        if not tasks:
            return create_error_response('任务不存在或无权限访问', 404)

        task = tasks[0]

        # 格式化时间字段
        for time_field in ['created_at', 'updated_at', 'started_at', 'completed_at']:
            if task[time_field]:
                task[time_field] = task[time_field].strftime("%Y-%m-%d %H:%M:%S")

        return create_success_response({"task": task})

    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


def process_upload_task(task_id):
    """处理上传任务的后台函数"""
    global current_processing_task
    
    # 获取任务处理锁
    with task_processing_lock:
        current_processing_task = task_id
        logger.info(f"开始处理上传任务: {task_id}")
        
        try:
            # 更新任务状态为处理中
            update_task_status(task_id, 'processing', 0, started_at=datetime.now())
            
            # 获取任务详情
            task_info = get_task_info(task_id)
            if not task_info:
                logger.error(f"任务 {task_id} 不存在")
                return
            
            # 初始化文档处理器
            document_processor = DocumentProcessor(
                chunking_method=task_info['chunking_method'],
                chunk_size=task_info['chunk_size'],
                similarity_threshold=task_info['similarity_threshold'],
                overlap_size=task_info['overlap_size'],
                custom_delimiter=task_info['custom_delimiter'],
                window_size=task_info['window_size'],
                step_size=task_info['step_size'],
                min_chunk_size=task_info['min_chunk_size'],
                max_chunk_size=task_info['max_chunk_size']
            )
            
            # 更新进度：开始处理文档
            update_task_status(task_id, 'processing', 10)
            
            # 处理文档内容
            doc_text = document_processor.process_document(task_info['file_path'])
            if not doc_text or doc_text.startswith("处理文档失败"):
                raise Exception(f"处理文档内容失败: {doc_text}")
            
            # 更新进度：文档处理完成
            update_task_status(task_id, 'processing', 30)
            
            # 文本分块
            chunks = document_processor.split_text(doc_text)
            chunk_count = len(chunks)
            
            if chunk_count == 0:
                raise Exception("文档分块失败，未生成有效分块")
            
            # 更新进度：分块完成
            update_task_status(task_id, 'processing', 50)
            
            # 获取嵌入模型
            from knowledge_mgt.utils.embeddings import local_embedding_manager
            embedding_model = local_embedding_manager.get_current_model()
            
            if embedding_model is None:
                raise Exception("没有加载的嵌入模型，请先在系统管理中加载嵌入模型")
            
            # 获取知识库信息
            kb_info = get_knowledge_database_info(task_info['database_id'])
            if not kb_info:
                raise Exception("知识库不存在")
            
            # 更新进度：开始生成向量
            update_task_status(task_id, 'processing', 60)
            
            # 初始化向量存储
            actual_dimension = embedding_model.get_dimension()
            vector_store = VectorStore(vector_dimension=actual_dimension, index_type=kb_info['index_type'])
            
            # 开始数据库事务
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
                        task_info['database_id'], task_info['filename'], task_info['file_path'],
                        'txt', task_info['file_size'],
                        task_info['chunking_method'], task_info['chunk_size'], 
                        task_info['similarity_threshold'], task_info['overlap_size'],
                        chunk_count, task_info['user_id'], task_info['username']
                    ])
                    
                    cursor.execute("SELECT LAST_INSERT_ID()")
                    document_id = cursor.fetchone()[0]
                
                # 更新进度：文档记录创建完成
                update_task_status(task_id, 'processing', 70)
                
                # 2. 添加文档分块记录
                chunk_ids = []
                for i, chunk_text in enumerate(chunks):
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO knowledge_document_chunk 
                            (document_id, database_id, chunk_index, content)
                            VALUES (%s, %s, %s, %s)
                        """, [document_id, task_info['database_id'], i, chunk_text])
                        
                        cursor.execute("SELECT LAST_INSERT_ID()")
                        chunk_id = cursor.fetchone()[0]
                        chunk_ids.append(chunk_id)
                
                # 更新进度：分块记录创建完成
                update_task_status(task_id, 'processing', 80)
                
                # 3. 生成向量并存储
                vector_store.create_index(task_info['database_id'])
                vectors = embedding_model.embed_texts(chunks)
                vector_ids = vector_store.add_vectors(task_info['database_id'], chunk_ids, vectors)
                
                # 更新进度：向量生成完成
                update_task_status(task_id, 'processing', 90)
                
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
                    """, [task_info['database_id']])
                
                # 更新任务状态为完成
                update_task_status(task_id, 'completed', 100, 
                                 completed_at=datetime.now(), 
                                 chunk_count=chunk_count,
                                 document_id=document_id)
                
                logger.info(f"任务 {task_id} 处理完成，生成文档ID: {document_id}, 分块数: {chunk_count}")
                
        except Exception as e:
            logger.error(f"处理任务 {task_id} 失败: {str(e)}", exc_info=True)
            update_task_status(task_id, 'failed', error_message=str(e))
        
        finally:
            current_processing_task = None


def update_task_status(task_id, status, progress=None, error_message=None, 
                      started_at=None, completed_at=None, chunk_count=None, document_id=None):
    """更新任务状态"""
    try:
        with connection.cursor() as cursor:
            # 构建更新SQL
            update_fields = ["status = %s", "updated_at = NOW()"]
            params = [status]
            
            if progress is not None:
                update_fields.append("progress = %s")
                params.append(progress)
            
            if error_message is not None:
                update_fields.append("error_message = %s")
                params.append(error_message)
            
            if started_at is not None:
                update_fields.append("started_at = %s")
                params.append(started_at)
            
            if completed_at is not None:
                update_fields.append("completed_at = %s")
                params.append(completed_at)
            
            if chunk_count is not None:
                update_fields.append("chunk_count = %s")
                params.append(chunk_count)
            
            if document_id is not None:
                update_fields.append("document_id = %s")
                params.append(document_id)
            
            params.append(task_id)
            
            sql = f"UPDATE document_upload_task SET {', '.join(update_fields)} WHERE task_id = %s"
            cursor.execute(sql, params)
            
            # 清除队列状态缓存
            queue_status_cache['data'] = None
            queue_status_cache['last_update'] = 0
            
    except Exception as e:
        logger.error(f"更新任务状态失败: {str(e)}", exc_info=True)


def get_task_info(task_id):
    """获取任务信息"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT task_id, user_id, username, database_id, filename, file_path, file_size,
                       chunking_method, chunk_size, similarity_threshold, overlap_size,
                       custom_delimiter, window_size, step_size, min_chunk_size, max_chunk_size
                FROM document_upload_task
                WHERE task_id = %s
            """, [task_id])
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
            
    except Exception as e:
        logger.error(f"获取任务信息失败: {str(e)}", exc_info=True)
        return None


def get_knowledge_database_info(database_id):
    """获取知识库信息"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, vector_dimension, index_type
                FROM knowledge_database
                WHERE id = %s
            """, [database_id])
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'vector_dimension': row[2],
                    'index_type': row[3]
                }
            return None
            
    except Exception as e:
        logger.error(f"获取知识库信息失败: {str(e)}", exc_info=True)
        return None


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def get_queue_status(request):
    """获取队列状态（带缓存优化）"""
    try:
        current_time = time.time()
        
        # 检查缓存是否有效
        if (queue_status_cache['data'] is not None and 
            current_time - queue_status_cache['last_update'] < queue_status_cache['cache_duration']):
            return create_success_response(queue_status_cache['data'])
        
        with connection.cursor() as cursor:
            # 获取队列统计信息
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
                    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_count,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count
                FROM document_upload_task
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            
            stats = cursor.fetchone()
            
            # 获取当前处理的任务
            current_task = None
            if current_processing_task:
                cursor.execute("""
                    SELECT task_id, filename, progress, started_at
                    FROM document_upload_task
                    WHERE task_id = %s
                """, [current_processing_task])
                
                task_row = cursor.fetchone()
                if task_row:
                    current_task = {
                        'task_id': task_row[0],
                        'filename': task_row[1],
                        'progress': task_row[2],
                        'started_at': task_row[3].strftime("%Y-%m-%d %H:%M:%S") if task_row[3] else None
                    }
        
        # 构建响应数据
        response_data = {
            "queue_stats": {
                "pending": stats[0] or 0,
                "processing": stats[1] or 0,
                "completed": stats[2] or 0,
                "failed": stats[3] or 0
            },
            "current_task": current_task
        }
        
        # 更新缓存
        queue_status_cache['data'] = response_data
        queue_status_cache['last_update'] = current_time
        
        return create_success_response(response_data)
        
    except Exception as e:
        logger.error(f"获取队列状态失败: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500) 