import json
import openai
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from open_ragbook_server.utils.response_code import ResponseCode
from account_mgt.utils.jwt_token_utils import parse_jwt_token


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


# 服务商 GET/POST handler
@csrf_exempt
def provider_handler(request):
    if request.method == 'GET':
        return provider_list(request)
    elif request.method == 'POST':
        return provider_create(request)
    else:
        return JsonResponse(ResponseCode.ERROR.to_dict(message='Method not allowed'), status=405)


# 服务商详情 GET/PUT/DELETE handler
@csrf_exempt
def provider_detail_handler(request, provider_id):
    if request.method == 'PUT':
        return provider_update(request, provider_id)
    elif request.method == 'DELETE':
        return provider_delete(request, provider_id)
    else:
        return JsonResponse(ResponseCode.ERROR.to_dict(message='Method not allowed'), status=405)


# 模型配置 GET/POST handler
@csrf_exempt
def model_handler(request):
    if request.method == 'GET':
        return model_list(request)
    elif request.method == 'POST':
        return model_create(request)
    else:
        return JsonResponse(ResponseCode.ERROR.to_dict(message='Method not allowed'), status=405)


# 模型配置详情 GET/PUT/DELETE/PATCH handler
@csrf_exempt
def model_detail_handler(request, model_id):
    if request.method == 'PUT':
        return model_update(request, model_id)
    elif request.method == 'DELETE':
        return model_delete(request, model_id)
    elif request.method == 'PATCH' and request.path.endswith('/default'):
        return model_set_default(request, model_id)
    else:
        return JsonResponse(ResponseCode.ERROR.to_dict(message='Method not allowed'), status=405)


# 模型测试 handler
@csrf_exempt
def model_test_handler(request, model_id):
    if request.method == 'POST':
        return model_test(request, model_id)
    else:
        return JsonResponse(ResponseCode.ERROR.to_dict(message='Method not allowed'), status=405)


# 服务商列表
@require_http_methods(["GET"])
@csrf_exempt
def provider_list(request):
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        with connection.cursor() as cursor:
            # 管理员可以看到所有服务商，普通用户只能看到自己的
            if role_id == 1:  # 管理员
                cursor.execute(
                    "SELECT id, name, code, `desc`, user_id, username, create_time, update_time FROM llmprovider ORDER BY create_time DESC")
            else:  # 普通用户
                cursor.execute(
                    "SELECT id, name, code, `desc`, user_id, username, create_time, update_time FROM llmprovider WHERE user_id = %s ORDER BY create_time DESC", [user_id])
            
            columns = [col[0] for col in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return JsonResponse(ResponseCode.SUCCESS.to_dict(data=data), status=200)
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


# 新增服务商
@require_http_methods(["POST"])
@csrf_exempt
def provider_create(request):
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    username = user_info.get('user_name')
    
    try:
        req = json.loads(request.body.decode('utf-8'))
        name = req.get('name')
        code = req.get('code')
        desc = req.get('desc', '')
        
        if not name or not code:
            return JsonResponse(ResponseCode.ERROR.to_dict(message="服务商名称和标识为必填项"), status=400)
        
        with connection.cursor() as cursor:
            # 检查同一用户下是否已存在相同的服务商标识
            cursor.execute(
                "SELECT id FROM llmprovider WHERE code = %s AND user_id = %s", 
                [code, user_id]
            )
            if cursor.fetchone():
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message=f"服务商标识 '{code}' 已存在，请使用其他标识"), 
                    status=400
                )
            
            # 检查同一用户下是否已存在相同的服务商名称
            cursor.execute(
                "SELECT id FROM llmprovider WHERE name = %s AND user_id = %s", 
                [name, user_id]
            )
            if cursor.fetchone():
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message=f"服务商名称 '{name}' 已存在，请使用其他名称"), 
                    status=400
                )
            
            cursor.execute(
                "INSERT INTO llmprovider (name, code, `desc`, user_id, username, create_time, update_time) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())",
                [name, code, desc, user_id, username])
        return JsonResponse(ResponseCode.SUCCESS.to_dict(), status=201)
    except Exception as e:
        print(e)
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


# 更新服务商
@require_http_methods(["PUT"])
@csrf_exempt
def provider_update(request, provider_id):
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        req = json.loads(request.body.decode('utf-8'))
        name = req.get('name')
        code = req.get('code')
        desc = req.get('desc', '')
        
        if not name or not code:
            return JsonResponse(ResponseCode.ERROR.to_dict(message="服务商名称和标识为必填项"), status=400)
        
        with connection.cursor() as cursor:
            # 检查权限：管理员可以操作所有，普通用户只能操作自己的
            if role_id == 1:  # 管理员
                cursor.execute("SELECT user_id FROM llmprovider WHERE id = %s", [provider_id])
            else:  # 普通用户
                cursor.execute("SELECT user_id FROM llmprovider WHERE id = %s AND user_id = %s", [provider_id, user_id])
            
            result = cursor.fetchone()
            if not result:
                return JsonResponse(ResponseCode.ERROR.to_dict(message="服务商不存在或无权限操作"), status=404)
            
            # 获取服务商的所属用户ID（用于唯一性检查）
            provider_user_id = result[0]
            
            # 检查同一用户下是否已存在相同的服务商标识（排除当前记录）
            cursor.execute(
                "SELECT id FROM llmprovider WHERE code = %s AND user_id = %s AND id != %s", 
                [code, provider_user_id, provider_id]
            )
            if cursor.fetchone():
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message=f"服务商标识 '{code}' 已存在，请使用其他标识"), 
                    status=400
                )
            
            # 检查同一用户下是否已存在相同的服务商名称（排除当前记录）
            cursor.execute(
                "SELECT id FROM llmprovider WHERE name = %s AND user_id = %s AND id != %s", 
                [name, provider_user_id, provider_id]
            )
            if cursor.fetchone():
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message=f"服务商名称 '{name}' 已存在，请使用其他名称"), 
                    status=400
                )
            
            cursor.execute("UPDATE llmprovider SET name=%s, code=%s, `desc`=%s, update_time=NOW() WHERE id=%s",
                           [name, code, desc, provider_id])
        return JsonResponse(ResponseCode.SUCCESS.to_dict(), status=200)
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


# 删除服务商
@require_http_methods(["DELETE"])
@csrf_exempt
def provider_delete(request, provider_id):
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        with connection.cursor() as cursor:
            # 检查权限：管理员可以操作所有，普通用户只能操作自己的
            if role_id == 1:  # 管理员
                cursor.execute("SELECT id FROM llmprovider WHERE id = %s", [provider_id])
            else:  # 普通用户
                cursor.execute("SELECT id FROM llmprovider WHERE id = %s AND user_id = %s", [provider_id, user_id])
            
            if not cursor.fetchone():
                return JsonResponse(ResponseCode.ERROR.to_dict(message="服务商不存在或无权限操作"), status=404)
            
            cursor.execute("DELETE FROM llmprovider WHERE id=%s", [provider_id])
        return JsonResponse(ResponseCode.SUCCESS.to_dict(), status=200)
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)



# 模型配置列表
@require_http_methods(["GET"])
@csrf_exempt
def model_list(request):
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        provider_id = request.GET.get('provider_id')
        
        # 管理员可以看到所有模型，普通用户只能看到自己的
        if role_id == 1:  # 管理员
            sql = "SELECT m.id, m.provider_id, m.name, m.model_type, m.api_key, m.base_url, m.max_tokens, m.temperature, m.is_default, m.user_id, m.username, m.create_time, m.update_time, p.name as provider_name FROM llmmodel m LEFT JOIN llmprovider p ON m.provider_id=p.id"
            params = []
            if provider_id:
                sql += " WHERE m.provider_id=%s"
                params.append(provider_id)
        else:  # 普通用户
            sql = "SELECT m.id, m.provider_id, m.name, m.model_type, m.api_key, m.base_url, m.max_tokens, m.temperature, m.is_default, m.user_id, m.username, m.create_time, m.update_time, p.name as provider_name FROM llmmodel m LEFT JOIN llmprovider p ON m.provider_id=p.id WHERE m.user_id = %s"
            params = [user_id]
            if provider_id:
                sql += " AND m.provider_id=%s"
                params.append(provider_id)
        
        sql += " ORDER BY m.create_time DESC"
        
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return JsonResponse(ResponseCode.SUCCESS.to_dict(data=data), status=200)
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


# 新增模型配置
@require_http_methods(["POST"])
@csrf_exempt
def model_create(request):
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    username = user_info.get('user_name')
    role_id = user_info.get('role_id')
    
    try:
        req = json.loads(request.body.decode('utf-8'))
        provider_id = req['provider_id']
        
        with connection.cursor() as cursor:
            # 检查服务商是否存在且用户有权限使用
            if role_id == 1:  # 管理员
                cursor.execute("SELECT id FROM llmprovider WHERE id = %s", [provider_id])
            else:  # 普通用户
                cursor.execute("SELECT id FROM llmprovider WHERE id = %s AND user_id = %s", [provider_id, user_id])
            
            if not cursor.fetchone():
                return JsonResponse(ResponseCode.ERROR.to_dict(message="服务商不存在或无权限使用"), status=404)
            
            cursor.execute(
                "INSERT INTO llmmodel (provider_id, name, model_type, api_key, base_url, max_tokens, temperature, is_default, user_id, username, create_time, update_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())",
                [provider_id, req['name'], req['model_type'], req['api_key'], req.get('base_url', ''),
                 req.get('max_tokens', 4096), req.get('temperature', 0.7), req.get('is_default', False), user_id, username])
        return JsonResponse(ResponseCode.SUCCESS.to_dict(), status=201)
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


# 更新模型配置
@require_http_methods(["PUT"])
@csrf_exempt
def model_update(request, model_id):
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        req = json.loads(request.body.decode('utf-8'))
        with connection.cursor() as cursor:
            # 检查权限：管理员可以操作所有，普通用户只能操作自己的
            if role_id == 1:  # 管理员
                cursor.execute("SELECT id FROM llmmodel WHERE id = %s", [model_id])
            else:  # 普通用户
                cursor.execute("SELECT id FROM llmmodel WHERE id = %s AND user_id = %s", [model_id, user_id])
            
            if not cursor.fetchone():
                return JsonResponse(ResponseCode.ERROR.to_dict(message="模型不存在或无权限操作"), status=404)
            
            cursor.execute(
                "UPDATE llmmodel SET name=%s, model_type=%s, api_key=%s, base_url=%s, max_tokens=%s, temperature=%s, is_default=%s, update_time=NOW() WHERE id=%s",
                [req['name'], req['model_type'], req['api_key'], req.get('base_url', ''), req.get('max_tokens', 4096),
                 req.get('temperature', 0.7), req.get('is_default', False), model_id])
        return JsonResponse(ResponseCode.SUCCESS.to_dict(), status=200)
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


# 删除模型配置
@require_http_methods(["DELETE"])
@csrf_exempt
def model_delete(request, model_id):
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        with connection.cursor() as cursor:
            # 检查权限：管理员可以操作所有，普通用户只能操作自己的
            if role_id == 1:  # 管理员
                cursor.execute("SELECT id FROM llmmodel WHERE id = %s", [model_id])
            else:  # 普通用户
                cursor.execute("SELECT id FROM llmmodel WHERE id = %s AND user_id = %s", [model_id, user_id])
            
            if not cursor.fetchone():
                return JsonResponse(ResponseCode.ERROR.to_dict(message="模型不存在或无权限操作"), status=404)
            
            cursor.execute("DELETE FROM llmmodel WHERE id=%s", [model_id])
        return JsonResponse(ResponseCode.SUCCESS.to_dict(), status=200)
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


# 设为默认模型
@require_http_methods(["PATCH"])
@csrf_exempt
def model_set_default(request, model_id):
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        with connection.cursor() as cursor:
            # 检查权限：管理员可以操作所有，普通用户只能操作自己的
            if role_id == 1:  # 管理员
                cursor.execute("SELECT provider_id FROM llmmodel WHERE id = %s", [model_id])
            else:  # 普通用户
                cursor.execute("SELECT provider_id FROM llmmodel WHERE id = %s AND user_id = %s", [model_id, user_id])
            
            result = cursor.fetchone()
            if not result:
                return JsonResponse(ResponseCode.ERROR.to_dict(message="模型不存在或无权限操作"), status=404)
            
            provider_id = result[0]
            
            # 先将同用户同服务商下的 is_default 设为 False
            if role_id == 1:  # 管理员可以操作所有
                cursor.execute(
                    "UPDATE llmmodel SET is_default = 0 WHERE provider_id = %s",
                    [provider_id])
            else:  # 普通用户只能操作自己的
                cursor.execute(
                    "UPDATE llmmodel SET is_default = 0 WHERE provider_id = %s AND user_id = %s",
                    [provider_id, user_id])
            
            # 再将指定模型设为默认
            cursor.execute("UPDATE llmmodel SET is_default = 1 WHERE id = %s", [model_id])
        return JsonResponse(ResponseCode.SUCCESS.to_dict(), status=200)
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=str(e)), status=500)


# 模型测试
@require_http_methods(["POST"])
@csrf_exempt
def model_test(request, model_id):
    user_info, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    try:
        req = json.loads(request.body.decode('utf-8'))
        test_message = req.get('prompt', 'Hello, this is a test message.')
        with connection.cursor() as cursor:
            # 检查权限：管理员可以测试所有，普通用户只能测试自己的
            if role_id == 1:  # 管理员
                cursor.execute(
                    "SELECT name, model_type, api_key, base_url, max_tokens, temperature FROM llmmodel WHERE id = %s",
                    [model_id])
            else:  # 普通用户
                cursor.execute(
                    "SELECT name, model_type, api_key, base_url, max_tokens, temperature FROM llmmodel WHERE id = %s AND user_id = %s",
                    [model_id, user_id])
            
            result = cursor.fetchone()
            if not result:
                return JsonResponse(ResponseCode.ERROR.to_dict(message="模型不存在或无权限操作"), status=404)
            
            name, model_type, api_key, base_url, max_tokens, temperature = result
            
            # 测试模型连接
            client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url if base_url else None
            )
            
            response = client.chat.completions.create(
                model=model_type,
                messages=[{"role": "user", "content": test_message}],
                max_tokens=min(max_tokens, 100),  # 测试时限制token数量
                temperature=temperature
            )
            return JsonResponse(ResponseCode.SUCCESS.to_dict(data={
                "response": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }), status=200)
            
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=f"模型测试失败: {str(e)}"), status=500)
