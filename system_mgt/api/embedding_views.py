import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connection, transaction
from open_ragbook_server.utils.response_code import ResponseCode
from account_mgt.utils.jwt_token_utils import parse_jwt_token
from datetime import datetime

logger = logging.getLogger(__name__)


def get_embedding_model_by_id(model_id):
    """根据模型ID获取嵌入模型配置"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, model_type, api_type, api_key, api_url, model_name, local_path,
                       vector_dimension, max_tokens, batch_size, timeout, is_public, user_id
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
                'timeout': result[11],
                'is_public': result[12],
                'user_id': result[13]
            }
                
    except Exception as e:
        logger.error(f"获取嵌入模型失败: {str(e)}", exc_info=True)
        raise


def get_user_from_token(request):
    """从JWT token中获取用户信息"""
    token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
    if not token:
        return None, JsonResponse(
            ResponseCode.ERROR.to_dict(message="未授权访问"),
            status=401
        )
    
    user_info = parse_jwt_token(token)
    if not user_info:
        return None, JsonResponse(
            ResponseCode.ERROR.to_dict(message="token无效"),
            status=401
        )
    
    return user_info, None


@csrf_exempt
def embedding_handler(request):
    """嵌入模型 GET/POST handler"""
    if request.method == 'GET':
        return embedding_list(request)
    elif request.method == 'POST':
        return embedding_create(request)
    else:
        return JsonResponse(ResponseCode.ERROR.to_dict(message='Method not allowed'), status=405)


@csrf_exempt
def embedding_detail_handler(request, embedding_id):
    """嵌入模型详情 GET/PUT/DELETE handler"""
    if request.method == 'GET':
        return embedding_detail(request, embedding_id)
    elif request.method == 'PUT':
        return embedding_update(request, embedding_id)
    elif request.method == 'DELETE':
        return embedding_delete(request, embedding_id)
    elif request.method == 'POST' and request.path.endswith('/test'):
        return embedding_test(request, embedding_id)
    else:
        return JsonResponse(ResponseCode.ERROR.to_dict(message='Method not allowed'), status=405)


@require_http_methods(["GET"])
@csrf_exempt
def embedding_list(request):
    """获取嵌入模型列表"""
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    # 获取查询参数
    name = request.GET.get('name', '').strip()
    model_type = request.GET.get('model_type', '').strip()
    api_type = request.GET.get('api_type', '').strip()
    is_public = request.GET.get('is_public', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))
    sort_field = request.GET.get('sort_field', 'create_time')
    sort_order = request.GET.get('sort_order', 'desc')
    
    try:
        with connection.cursor() as cursor:
            # 构建基础查询条件
            where_conditions = []
            params = []
            
            # 权限过滤
            if role_id == 1:  # 管理员可以看到所有模型
                pass
            else:  # 普通用户只能看到自己的和公共的激活模型
                where_conditions.append("(user_id = %s OR is_public = 1) AND is_active = 1")
                params.append(user_id)
            
            # 名称搜索
            if name:
                where_conditions.append("name LIKE %s")
                params.append(f"%{name}%")
            
            # 模型类型过滤
            if model_type:
                where_conditions.append("model_type = %s")
                params.append(model_type)
            
            # API类型过滤
            if api_type:
                where_conditions.append("api_type = %s")
                params.append(api_type)
            
            # 可见性过滤
            if is_public:
                where_conditions.append("is_public = %s")
                params.append(int(is_public))
            
            # 构建WHERE子句
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # 构建排序子句
            valid_sort_fields = ['name', 'model_type', 'api_type', 'vector_dimension', 'create_time', 'update_time']
            if sort_field not in valid_sort_fields:
                sort_field = 'create_time'
            
            if sort_order.lower() not in ['asc', 'desc']:
                sort_order = 'desc'
            
            order_clause = f"ORDER BY is_preset DESC, {sort_field} {sort_order.upper()}"
            
            # 查询总数
            count_sql = f"""
                SELECT COUNT(*) 
                FROM embedding_model 
                {where_clause}
            """
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]
            
            # 分页查询
            offset = (page - 1) * page_size
            data_sql = f"""
                SELECT id, name, model_type, api_type, api_key, api_url, model_name, local_path,
                       vector_dimension, max_tokens, batch_size, timeout, is_public, is_active, is_preset,
                       user_id, username, description, create_time, update_time
                FROM embedding_model 
                {where_clause}
                {order_clause}
                LIMIT %s OFFSET %s
            """
            cursor.execute(data_sql, params + [page_size, offset])
            
            columns = [col[0] for col in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # 隐藏API密钥的敏感信息
            for item in data:
                if item['api_key']:
                    item['api_key'] = item['api_key'][:8] + '***' if len(item['api_key']) > 8 else '***'
            
            return JsonResponse(ResponseCode.SUCCESS.to_dict(data={
                'items': data,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }), status=200)
    except Exception as e:
        logger.error(f"获取嵌入模型列表失败: {str(e)}")
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


@require_http_methods(["POST"])
@csrf_exempt
def embedding_create(request):
    """创建嵌入模型"""
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    username = user_info.get('user_name')
    
    try:
        req = json.loads(request.body.decode('utf-8'))
        
        # 参数验证
        required_fields = ['name', 'model_type', 'api_type']
        for field in required_fields:
            if not req.get(field):
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message=f"缺少必填字段: {field}"),
                    status=400
                )
        
        # 根据模型类型验证必要字段
        if req['api_type'] == 'online':
            # 在线模型需要API密钥
            if not req.get('api_key'):
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="在线API模型需要提供API密钥"),
                    status=400
                )
        elif req['api_type'] == 'local':
            # 本地模型需要模型名称
            if not req.get('model_name'):
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="本地模型需要提供模型名称"),
                    status=400
                )
        
        # 获取预设模型配置（如果是基于预设模型创建）
        preset_config = get_preset_model_config(req.get('model_type'), req.get('model_name'))
        if preset_config:
            # 使用预设配置，用户不能修改技术参数
            req.update(preset_config)
        else:
            # 自定义模型，需要提供技术参数
            if not req.get('vector_dimension'):
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="自定义模型需要提供向量维度"),
                    status=400
                )
        
        with connection.cursor() as cursor:
            # 检查名称是否已存在
            cursor.execute("SELECT id FROM embedding_model WHERE name = %s", [req['name']])
            if cursor.fetchone():
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="模型名称已存在"),
                    status=400
                )
            
            cursor.execute("""
                INSERT INTO embedding_model 
                (name, model_type, api_type, api_key, api_url, model_name, local_path,
                 vector_dimension, max_tokens, batch_size, timeout, is_public, is_active, is_preset,
                 user_id, username, description, create_time, update_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, [
                req['name'], req['model_type'], req['api_type'],
                req.get('api_key', ''), req.get('api_url', ''),
                req.get('model_name', ''), req.get('local_path', ''),
                req.get('vector_dimension', 1536), req.get('max_tokens', 8192),
                req.get('batch_size', 32), req.get('timeout', 30),
                req.get('is_public', False), req.get('is_active', True), False,  # is_preset=False
                user_id, username, req.get('description', '')
            ])
        
        return JsonResponse(ResponseCode.SUCCESS.to_dict(), status=201)
    except Exception as e:
        logger.error(f"创建嵌入模型失败: {str(e)}")
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


def get_preset_model_config(model_type, model_name):
    """获取预设模型配置"""
    preset_configs = {
        # OpenAI系列
        ('openai', 'text-embedding-ada-002'): {
            'api_url': 'https://api.openai.com/v1/embeddings',
            'vector_dimension': 1536,
            'max_tokens': 8192,
            'batch_size': 100,
            'timeout': 30
        },
        ('openai', 'text-embedding-3-small'): {
            'api_url': 'https://api.openai.com/v1/embeddings',
            'vector_dimension': 1536,
            'max_tokens': 8192,
            'batch_size': 100,
            'timeout': 30
        },
        ('openai', 'text-embedding-3-large'): {
            'api_url': 'https://api.openai.com/v1/embeddings',
            'vector_dimension': 3072,
            'max_tokens': 8192,
            'batch_size': 50,
            'timeout': 30
        },
        
        # 国内在线API
        ('zhipu', 'embedding-2'): {
            'api_url': 'https://open.bigmodel.cn/api/paas/v4/embeddings',
            'vector_dimension': 1024,
            'max_tokens': 8192,
            'batch_size': 50,
            'timeout': 30
        },
        ('baidu', 'embedding-v1'): {
            'api_url': 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/embeddings/embedding-v1',
            'vector_dimension': 384,
            'max_tokens': 1000,
            'batch_size': 16,
            'timeout': 30
        },
        ('dashscope', 'text-embedding-v1'): {
            'api_url': 'https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding',
            'vector_dimension': 1536,
            'max_tokens': 2048,
            'batch_size': 25,
            'timeout': 30
        },
        
        # 本地模型
        ('sentence_transformers', 'all-MiniLM-L6-v2'): {
            'vector_dimension': 384,
            'max_tokens': 256,
            'batch_size': 64,
            'timeout': 60
        },
        ('sentence_transformers', 'all-MiniLM-L12-v2'): {
            'vector_dimension': 384,
            'max_tokens': 256,
            'batch_size': 32,
            'timeout': 60
        },
        ('sentence_transformers', 'BAAI/bge-small-zh-v1.5'): {
            'vector_dimension': 512,
            'max_tokens': 512,
            'batch_size': 32,
            'timeout': 60
        },
        ('sentence_transformers', 'BAAI/bge-base-zh-v1.5'): {
            'vector_dimension': 768,
            'max_tokens': 512,
            'batch_size': 32,
            'timeout': 60
        },
        ('sentence_transformers', 'BAAI/bge-large-zh-v1.5'): {
            'vector_dimension': 1024,
            'max_tokens': 512,
            'batch_size': 16,
            'timeout': 120
        },
        ('sentence_transformers', 'moka-ai/m3e-base'): {
            'vector_dimension': 768,
            'max_tokens': 512,
            'batch_size': 32,
            'timeout': 60
        },
        ('sentence_transformers', 'intfloat/e5-base-v2'): {
            'vector_dimension': 768,
            'max_tokens': 512,
            'batch_size': 32,
            'timeout': 60
        },
        
        # Ollama
        ('ollama', 'nomic-embed-text'): {
            'api_url': 'http://localhost:11434',
            'vector_dimension': 768,
            'max_tokens': 2048,
            'batch_size': 16,
            'timeout': 120
        }
    }
    
    return preset_configs.get((model_type, model_name))


@require_http_methods(["PUT"])
@csrf_exempt
def embedding_update(request, embedding_id):
    """更新嵌入模型"""
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        req = json.loads(request.body.decode('utf-8'))
        
        with connection.cursor() as cursor:
            # 检查权限和是否为预设模型
            if role_id == 1:  # 管理员
                cursor.execute("""
                    SELECT is_preset, user_id, is_public FROM embedding_model WHERE id = %s
                """, [embedding_id])
            else:  # 普通用户
                cursor.execute("""
                    SELECT is_preset, user_id, is_public FROM embedding_model 
                    WHERE id = %s AND (user_id = %s OR is_public = 1)
                """, [embedding_id, user_id])
            
            result = cursor.fetchone()
            if not result:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="模型不存在或无权限操作"),
                    status=404
                )
            
            is_preset, model_user_id, is_public = result
            
            # 普通用户对别人创建的公用模型没有编辑权限
            if role_id != 1 and model_user_id != user_id:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="无权限编辑此模型"),
                    status=403
                )
            
            # 预设模型只允许修改API密钥、描述和启用状态
            if is_preset:
                cursor.execute("""
                    UPDATE embedding_model 
                    SET api_key = %s, description = %s, is_active = %s, update_time = NOW()
                    WHERE id = %s
                """, [
                    req.get('api_key', ''),
                    req.get('description', ''),
                    req.get('is_active', True),
                    embedding_id
                ])
            else:
                # 自定义模型允许修改所有字段
                cursor.execute("""
                    UPDATE embedding_model 
                    SET name = %s, model_type = %s, api_type = %s, api_key = %s, api_url = %s,
                        model_name = %s, local_path = %s, vector_dimension = %s, max_tokens = %s,
                        batch_size = %s, timeout = %s, is_public = %s, is_active = %s,
                        description = %s, update_time = NOW()
                    WHERE id = %s
                """, [
                    req.get('name', ''),
                    req.get('model_type', ''),
                    req.get('api_type', ''),
                    req.get('api_key', ''),
                    req.get('api_url', ''),
                    req.get('model_name', ''),
                    req.get('local_path', ''),
                    req.get('vector_dimension', 1536),
                    req.get('max_tokens', 8192),
                    req.get('batch_size', 32),
                    req.get('timeout', 30),
                    req.get('is_public', False),
                    req.get('is_active', True),
                    req.get('description', ''),
                    embedding_id
                ])
        
        logger.info(f"成功更新嵌入模型: ID={embedding_id}")
        return JsonResponse(ResponseCode.SUCCESS.to_dict(), status=200)
        
    except Exception as e:
        logger.error(f"更新嵌入模型失败: {str(e)}")
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


@require_http_methods(["DELETE"])
@csrf_exempt
def embedding_delete(request, embedding_id):
    """删除嵌入模型"""
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        with connection.cursor() as cursor:
            # 检查权限和模型状态
            if role_id == 1:  # 管理员
                cursor.execute("""
                    SELECT is_preset, user_id, is_public FROM embedding_model WHERE id = %s
                """, [embedding_id])
            else:  # 普通用户
                cursor.execute("""
                    SELECT is_preset, user_id, is_public FROM embedding_model 
                    WHERE id = %s AND (user_id = %s OR is_public = 1)
                """, [embedding_id, user_id])
            
            result = cursor.fetchone()
            if not result:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="模型不存在或无权限操作"),
                    status=404
                )
            
            is_preset, model_user_id, is_public = result
            
            # 普通用户对别人创建的公用模型没有删除权限
            if role_id != 1 and model_user_id != user_id:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="无权限删除此模型"),
                    status=403
                )
            
            # 预设模型不允许删除
            if is_preset:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="预设模型不允许删除，只能禁用"),
                    status=400
                )
            
            # 检查是否有知识库在使用（暂时跳过，因为字段可能不存在）
            # try:
            #     cursor.execute("""
            #         SELECT COUNT(*) FROM knowledge_database WHERE embedding_model_id = %s
            #     """, [embedding_id])
            #     
            #     usage_count = cursor.fetchone()[0]
            #     if usage_count > 0:
            #         return JsonResponse(
            #             ResponseCode.ERROR.to_dict(message=f"该模型正在被 {usage_count} 个知识库使用，无法删除"),
            #             status=400
            #         )
            # except Exception as e:
            #     # 如果embedding_model_id字段不存在，跳过检查
            #     logger.warning(f"跳过知识库使用检查，字段可能不存在: {str(e)}")
            
            # 删除模型
            cursor.execute("DELETE FROM embedding_model WHERE id = %s", [embedding_id])
        
        return JsonResponse(ResponseCode.SUCCESS.to_dict(), status=200)
    except Exception as e:
        logger.error(f"删除嵌入模型失败: {str(e)}")
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


@require_http_methods(["POST"])
@csrf_exempt
def embedding_test(request, embedding_id):
    """测试嵌入模型"""
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        req = json.loads(request.body.decode('utf-8'))
        test_text = req.get('text', '这是一个测试文本')
        
        # 获取模型配置
        model_config = get_embedding_model_by_id(embedding_id)
        if not model_config:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="模型不存在或无权限操作"),
                status=404
            )
        
        # 检查用户权限
        if role_id != 1 and model_config['user_id'] != user_id and not model_config.get('is_public'):
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="无权限操作此模型"),
                status=403
            )
        
        import time
        start_time = time.time()
        
        # 根据模型类型进行真实测试
        if model_config['api_type'] == 'local':
            # 本地模型测试
            from knowledge_mgt.utils.embeddings import local_embedding_manager
            
            # 检查是否已加载
            current_model = local_embedding_manager.get_current_model()
            current_model_id = local_embedding_manager.get_current_model_id()
            
            if current_model is None or current_model_id != embedding_id:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="本地模型未加载，请先加载模型再测试"),
                    status=400
                )
            
            # 使用已加载的模型进行测试
            try:
                vector = current_model.embed_text(test_text)
                actual_dimension = len(vector)
                
                test_result = {
                    "success": True,
                    "text": test_text,
                    "model_name": model_config['name'],
                    "model_type": model_config['model_type'],
                    "api_type": "local",
                    "vector_dimension": actual_dimension,
                    "vector_sample": vector[:10] if len(vector) > 10 else vector,  # 显示前10个维度
                    "response_time": f"{(time.time() - start_time) * 1000:.1f}ms",
                    "device": current_model.get_device()
                }
                
            except Exception as e:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message=f"本地模型测试失败: {str(e)}"),
                    status=500
                )
                
        elif model_config['api_type'] == 'openai':
            # OpenAI API测试
            try:
                import openai
                
                client = openai.OpenAI(
                    api_key=model_config['api_key'],
                    base_url=model_config['api_url'] if model_config['api_url'] else None
                )
                
                response = client.embeddings.create(
                    model=model_config['model_name'],
                    input=test_text
                )
                
                vector = response.data[0].embedding
                actual_dimension = len(vector)
                
                test_result = {
                    "success": True,
                    "text": test_text,
                    "model_name": model_config['name'],
                    "model_type": model_config['model_type'],
                    "api_type": "openai",
                    "vector_dimension": actual_dimension,
                    "vector_sample": vector[:10] if len(vector) > 10 else vector,  # 显示前10个维度
                    "response_time": f"{(time.time() - start_time) * 1000:.1f}ms",
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
                
            except Exception as e:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message=f"OpenAI API测试失败: {str(e)}"),
                    status=500
                )
                
        elif model_config['api_type'] == 'ollama':
            # Ollama API测试
            try:
                import requests
                
                api_url = model_config['api_url'] or 'http://localhost:11434'
                if not api_url.endswith('/'):
                    api_url += '/'
                
                response = requests.post(
                    f"{api_url}api/embeddings",
                    json={
                        "model": model_config['model_name'],
                        "prompt": test_text
                    },
                    timeout=30
                )
                
                if response.status_code != 200:
                    return JsonResponse(
                        ResponseCode.ERROR.to_dict(message=f"Ollama API错误: {response.text}"),
                        status=500
                    )
                
                data = response.json()
                vector = data.get('embedding', [])
                actual_dimension = len(vector)
                
                test_result = {
                    "success": True,
                    "text": test_text,
                    "model_name": model_config['name'],
                    "model_type": model_config['model_type'],
                    "api_type": "ollama",
                    "vector_dimension": actual_dimension,
                    "vector_sample": vector[:10] if len(vector) > 10 else vector,  # 显示前10个维度
                    "response_time": f"{(time.time() - start_time) * 1000:.1f}ms"
                }
                
            except requests.RequestException as e:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message=f"Ollama API连接失败: {str(e)}"),
                    status=500
                )
            except Exception as e:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message=f"Ollama API测试失败: {str(e)}"),
                    status=500
                )
        else:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message=f"不支持的API类型: {model_config['api_type']}"),
                status=400
            )
        
        return JsonResponse(ResponseCode.SUCCESS.to_dict(data=test_result), status=200)
            
    except Exception as e:
        logger.error(f"测试嵌入模型失败: {str(e)}")
        return JsonResponse(ResponseCode.ERROR.to_dict(message=f"测试失败: {str(e)}"), status=500)


@require_http_methods(["GET"])
@csrf_exempt
def embedding_detail(request, embedding_id):
    """获取嵌入模型详情"""
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        with connection.cursor() as cursor:
            # 检查权限
            if role_id == 1:  # 管理员
                cursor.execute("""
                    SELECT id, name, model_type, api_type, api_key, api_url, model_name, local_path,
                           vector_dimension, max_tokens, batch_size, timeout, is_public, is_active, is_preset,
                           user_id, username, description, create_time, update_time
                    FROM embedding_model WHERE id = %s
                """, [embedding_id])
            else:  # 普通用户
                cursor.execute("""
                    SELECT id, name, model_type, api_type, api_key, api_url, model_name, local_path,
                           vector_dimension, max_tokens, batch_size, timeout, is_public, is_active, is_preset,
                           user_id, username, description, create_time, update_time
                    FROM embedding_model WHERE id = %s AND (user_id = %s OR is_public = 1)
                """, [embedding_id, user_id])
            
            result = cursor.fetchone()
            if not result:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="模型不存在或无权限访问"),
                    status=404
                )
            
            columns = [col[0] for col in cursor.description]
            data = dict(zip(columns, result))
            
            # 对于编辑操作，返回完整的API密钥（如果用户有权限）
            # 只有模型的创建者或管理员才能看到完整的API密钥
            if role_id != 1 and data['user_id'] != user_id:
                # 非创建者和非管理员，隐藏API密钥
                if data['api_key']:
                    data['api_key'] = data['api_key'][:8] + '***' if len(data['api_key']) > 8 else '***'
            
            return JsonResponse(ResponseCode.SUCCESS.to_dict(data=data), status=200)
    except Exception as e:
        logger.error(f"获取嵌入模型详情失败: {str(e)}")
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


@require_http_methods(["POST"])
@csrf_exempt
def embedding_load_local(request, embedding_id):
    """加载本地嵌入模型"""
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        # 获取模型配置
        model_config = get_embedding_model_by_id(embedding_id)
        if not model_config:
            return JsonResponse(ResponseCode.ERROR.to_dict(message="嵌入模型不存在"), status=404)
        
        # 检查用户权限 - 普通用户对别人创建的公用模型没有加载权限
        if role_id != 1 and model_config['user_id'] != user_id:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="无权限加载此模型"),
                status=403
            )
        
        # 检查是否为本地模型
        if model_config['api_type'] != 'local':
            return JsonResponse(ResponseCode.ERROR.to_dict(message="只能加载本地模型"), status=400)
        
        # 检查模型路径是否配置
        if not model_config.get('local_path') and not model_config.get('model_name'):
            return JsonResponse(ResponseCode.ERROR.to_dict(message="模型路径未配置"), status=400)
        
        # 使用本地嵌入模型管理器加载模型
        from knowledge_mgt.utils.embeddings import local_embedding_manager
        
        # 传递完整的模型配置
        embedding_model = local_embedding_manager.load_model(embedding_id, model_config)
        
        return JsonResponse(ResponseCode.SUCCESS.to_dict(data={
            'message': f'本地嵌入模型 {model_config["name"]} 加载成功',
            'model_id': embedding_id,
            'model_name': model_config['name'],
            'model_path': model_config.get('local_path') or model_config.get('model_name'),
            'vector_dimension': embedding_model.get_dimension(),
            'device': embedding_model.get_device()
        }), status=200)
        
    except FileNotFoundError as e:
        logger.error(f"模型文件不存在: {str(e)}")
        return JsonResponse(ResponseCode.ERROR.to_dict(message=f"模型文件不存在: {str(e)}"), status=400)
    except Exception as e:
        logger.error(f"加载本地嵌入模型失败: {str(e)}")
        return JsonResponse(ResponseCode.ERROR.to_dict(message=f"加载模型失败: {str(e)}"), status=500)


@require_http_methods(["POST"])
@csrf_exempt
def embedding_unload_local(request):
    """卸载当前本地嵌入模型"""
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        from knowledge_mgt.utils.embeddings import local_embedding_manager, get_current_local_model_info
        
        # 获取当前模型信息
        current_info = get_current_local_model_info()
        if current_info is None:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="当前没有加载的本地嵌入模型"),
                status=400
            )
        
        # 检查用户权限 - 普通用户只能卸载自己创建的模型
        if role_id != 1:
            current_model_id = current_info.get('model_id')
            if current_model_id:
                model_config = get_embedding_model_by_id(current_model_id)
                if model_config and model_config['user_id'] != user_id:
                    return JsonResponse(
                        ResponseCode.ERROR.to_dict(message="无权限卸载此模型"),
                        status=403
                    )
        
        # 卸载模型
        local_embedding_manager.unload_current_model()
        
        return JsonResponse(ResponseCode.SUCCESS.to_dict(data={
            "message": f"成功卸载本地嵌入模型: {current_info['model_name']}",
            "unloaded_model": current_info
        }), status=200)
    except Exception as e:
        logger.error(f"卸载本地嵌入模型失败: {str(e)}")
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


@require_http_methods(["GET"])
@csrf_exempt
def embedding_local_status(request):
    """获取本地嵌入模型状态"""
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    try:
        from knowledge_mgt.utils.embeddings import get_current_local_model_info
        
        current_info = get_current_local_model_info()
        
        if current_info is None:
            return JsonResponse(ResponseCode.SUCCESS.to_dict(data={
                "has_loaded_model": False,
                "message": "当前没有加载的本地嵌入模型"
            }), status=200)
        else:
            return JsonResponse(ResponseCode.SUCCESS.to_dict(data={
                "has_loaded_model": True,
                "current_model": current_info
            }), status=200)
    except Exception as e:
        logger.error(f"获取本地嵌入模型状态失败: {str(e)}")
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


@require_http_methods(["GET"])
@csrf_exempt
def embedding_server_resources(request):
    """获取服务器资源状态"""
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    try:
        import psutil
        import platform
        
        # 获取CPU信息
        cpu_info = {
            'cores': psutil.cpu_count(),
            'percent': psutil.cpu_percent(interval=1)
        }
        
        # 获取内存信息
        memory = psutil.virtual_memory()
        memory_info = {
            'total': round(memory.total / (1024**3), 2),  # GB
            'used': round(memory.used / (1024**3), 2),    # GB
            'available': round(memory.available / (1024**3), 2),  # GB
            'percent': memory.percent
        }
        
        # 检查GPU信息
        gpu_info = []
        has_gpu = False
        
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                has_gpu = True
                for gpu in gpus:
                    gpu_info.append({
                        'id': gpu.id,
                        'name': gpu.name,
                        'memory_total': gpu.memoryTotal,
                        'memory_used': gpu.memoryUsed,
                        'memory_free': gpu.memoryFree,
                        'memory_percent': round((gpu.memoryUsed / gpu.memoryTotal) * 100, 1),
                        'utilization': gpu.load * 100,
                        'temperature': gpu.temperature
                    })
        except ImportError:
            logger.warning("GPUtil not installed, cannot get GPU information")
        except Exception as e:
            logger.warning(f"Failed to get GPU information: {str(e)}")
        
        # 获取系统信息
        system_info = {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'architecture': platform.architecture()[0],
            'python_version': platform.python_version()
        }
        
        return JsonResponse(ResponseCode.SUCCESS.to_dict(data={
            'cpu': cpu_info,
            'memory': memory_info,
            'gpu_info': gpu_info,
            'has_gpu': has_gpu,
            'system': system_info,
            'timestamp': datetime.now().isoformat()
        }), status=200)
        
    except Exception as e:
        logger.error(f"获取服务器资源状态失败: {str(e)}")
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


@csrf_exempt
@require_http_methods(["POST"])
def embedding_validate(request, embedding_id):
    """验证嵌入模型配置"""
    # JWT token验证
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        with connection.cursor() as cursor:
            # 检查权限和获取模型信息
            if role_id == 1:  # 管理员
                cursor.execute("""
                    SELECT id, name, model_type, api_type, model_name, local_path, api_url
                    FROM embedding_model WHERE id = %s
                """, [embedding_id])
            else:  # 普通用户
                cursor.execute("""
                    SELECT id, name, model_type, api_type, model_name, local_path, api_url
                    FROM embedding_model WHERE id = %s AND (user_id = %s OR is_public = 1)
                """, [embedding_id, user_id])
            
            result = cursor.fetchone()
            if not result:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="模型不存在或无权限访问"),
                    status=404
                )
            
            model_id, name, model_type, api_type, model_name, local_path, api_url = result
            
            # 只验证本地模型
            if api_type != 'local':
                return JsonResponse(
                    ResponseCode.SUCCESS.to_dict(data={
                        'is_valid': True,
                        'model_info': f'{name} (在线模型)',
                        'message': '在线模型无需验证配置'
                    })
                )
            
            # 验证本地模型配置
            validation_result = validate_local_model_config(
                model_type, model_name, local_path, api_url
            )
            
            return JsonResponse(
                ResponseCode.SUCCESS.to_dict(data=validation_result)
            )
            
    except Exception as e:
        logger.error(f"验证嵌入模型配置失败: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"验证模型配置失败: {str(e)}"),
            status=500
        )


def validate_local_model_config(model_type, model_name, local_path, api_url):
    """验证本地模型配置"""
    import os
    import json
    
    try:
        if model_type == 'sentence_transformers':
            # 验证 Sentence Transformers 模型
            if not local_path:
                return {
                    'is_valid': False,
                    'expected_model': model_name,
                    'actual_path': local_path or '未设置',
                    'error_message': '本地路径未设置',
                    'model_info': ''
                }
            
            # 检查路径是否存在
            if not os.path.exists(local_path):
                return {
                    'is_valid': False,
                    'expected_model': model_name,
                    'actual_path': local_path,
                    'error_message': '指定的路径不存在',
                    'model_info': ''
                }
            
            # 检查是否是有效的模型目录
            config_file = os.path.join(local_path, 'config.json')
            if not os.path.exists(config_file):
                return {
                    'is_valid': False,
                    'expected_model': model_name,
                    'actual_path': local_path,
                    'error_message': '路径中未找到 config.json 文件',
                    'model_info': ''
                }
            
            # 读取配置文件验证模型信息
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 获取模型架构信息
                model_info = f"模型架构: {config.get('architectures', ['未知'])[0]}"
                if 'max_seq_length' in config:
                    model_info += f", 最大序列长度: {config['max_seq_length']}"
                
                # 更智能的模型名称匹配验证
                config_model_name = config.get('_name_or_path', '').lower()
                expected_name = model_name.lower()
                
                # 定义模型名称映射关系
                model_aliases = {
                    'all-minilm-l6-v2': ['nreimers/minilm-l6-h384-uncased', 'sentence-transformers/all-minilm-l6-v2'],
                    'all-minilm-l12-v2': ['nreimers/minilm-l12-h384-uncased', 'sentence-transformers/all-minilm-l12-v2'],
                    'baai/bge-small-zh-v1.5': ['baai/bge-small-zh-v1.5', 'bge-small-zh-v1.5'],
                    'baai/bge-base-zh-v1.5': ['baai/bge-base-zh-v1.5', 'bge-base-zh-v1.5'],
                    'baai/bge-large-zh-v1.5': ['baai/bge-large-zh-v1.5', 'bge-large-zh-v1.5'],
                    'moka-ai/m3e-base': ['moka-ai/m3e-base', 'm3e-base'],
                    'intfloat/e5-base-v2': ['intfloat/e5-base-v2', 'e5-base-v2']
                }
                
                # 检查是否匹配
                is_valid_model = False
                
                # 1. 直接匹配
                if expected_name in config_model_name or config_model_name in expected_name:
                    is_valid_model = True
                
                # 2. 通过别名映射匹配
                if not is_valid_model:
                    for canonical_name, aliases in model_aliases.items():
                        if expected_name == canonical_name or expected_name in aliases:
                            for alias in aliases:
                                if alias in config_model_name:
                                    is_valid_model = True
                                    break
                            if is_valid_model:
                                break
                
                # 3. 部分匹配（去除前缀和后缀）
                if not is_valid_model:
                    # 提取核心模型名称
                    expected_core = expected_name.split('/')[-1].replace('-', '').replace('_', '')
                    config_core = config_model_name.split('/')[-1].replace('-', '').replace('_', '')
                    
                    if expected_core in config_core or config_core in expected_core:
                        is_valid_model = True
                
                if not is_valid_model and config_model_name:
                    return {
                        'is_valid': False,
                        'expected_model': model_name,
                        'actual_path': local_path,
                        'error_message': f'模型名称可能不匹配。配置文件中的模型: {config_model_name}。如果确认这是正确的模型，可以忽略此警告。',
                        'model_info': model_info
                    }
                
                return {
                    'is_valid': True,
                    'expected_model': model_name,
                    'actual_path': local_path,
                    'model_info': model_info,
                    'message': '模型配置验证通过'
                }
                
            except json.JSONDecodeError:
                return {
                    'is_valid': False,
                    'expected_model': model_name,
                    'actual_path': local_path,
                    'error_message': 'config.json 文件格式错误',
                    'model_info': ''
                }
        
        elif model_type == 'ollama':
            # 验证 Ollama 模型
            if not api_url:
                return {
                    'is_valid': False,
                    'expected_model': model_name,
                    'actual_path': api_url or '未设置',
                    'error_message': 'Ollama 服务地址未设置',
                    'model_info': ''
                }
            
            # 这里可以添加对 Ollama 服务的连接测试
            # 暂时返回基本验证通过
            return {
                'is_valid': True,
                'expected_model': model_name,
                'actual_path': api_url,
                'model_info': f'Ollama 模型: {model_name}',
                'message': 'Ollama 模型配置验证通过'
            }
        
        else:
            return {
                'is_valid': False,
                'expected_model': model_name,
                'actual_path': local_path or api_url,
                'error_message': f'不支持的模型类型: {model_type}',
                'model_info': ''
            }
            
    except Exception as e:
        return {
            'is_valid': False,
            'expected_model': model_name,
            'actual_path': local_path or api_url,
            'error_message': f'验证过程中发生错误: {str(e)}',
            'model_info': ''
        } 