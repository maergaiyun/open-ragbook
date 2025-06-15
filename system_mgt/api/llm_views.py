import json
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

# 使用新的工具函数
from open_ragbook_server.utils.auth_utils import (
    jwt_required, get_user_from_request, check_resource_permission,
    get_user_filter_condition, parse_json_body, validate_required_fields,
    create_error_response, create_success_response
)
from open_ragbook_server.utils.db_utils import (
    execute_query_with_params, execute_update_with_params,
    check_record_exists, get_record_by_id, get_last_insert_id
)
from open_ragbook_server.utils.response_code import ResponseCode
from account_mgt.utils.jwt_token_utils import parse_jwt_token


# 服务商 GET/POST handler
@csrf_exempt
@jwt_required()
def provider_handler(request):
    if request.method == 'GET':
        return provider_list(request)
    elif request.method == 'POST':
        return provider_create(request)
    else:
        return create_error_response('Method not allowed', 405)


# 服务商详情 GET/PUT/DELETE handler
@csrf_exempt
@jwt_required()
def provider_detail_handler(request, provider_id):
    if request.method == 'PUT':
        return provider_update(request, provider_id)
    elif request.method == 'DELETE':
        return provider_delete(request, provider_id)
    else:
        return create_error_response('Method not allowed', 405)


# 模型配置 GET/POST handler
@csrf_exempt
@jwt_required()
def model_handler(request):
    if request.method == 'GET':
        return model_list(request)
    elif request.method == 'POST':
        return model_create(request)
    else:
        return create_error_response('Method not allowed', 405)


# 模型配置详情 GET/PUT/DELETE/PATCH handler
@csrf_exempt
@jwt_required()
def model_detail_handler(request, model_id):
    if request.method == 'PUT':
        return model_update(request, model_id)
    elif request.method == 'DELETE':
        return model_delete(request, model_id)
    elif request.method == 'PATCH' and request.path.endswith('/default'):
        return model_set_default(request, model_id)
    else:
        return create_error_response('Method not allowed', 405)


# 模型测试 handler
@csrf_exempt
@jwt_required()
def model_test_handler(request, model_id):
    if request.method == 'POST':
        return model_test(request, model_id)
    else:
        return create_error_response('Method not allowed', 405)


# 服务商列表
@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def provider_list(request):
    """获取服务商列表"""
    try:
        # 获取用户过滤条件
        where_clause, params = get_user_filter_condition(request)
        
        # 构建SQL
        sql = f"""
            SELECT id, name, code, `desc`, user_id, username, create_time, update_time 
            FROM llmprovider 
            {where_clause}
            ORDER BY create_time DESC
        """
        
        data = execute_query_with_params(sql, params)
        return create_success_response(data)
        
    except Exception as e:
        return create_error_response(str(e), 500)


# 新增服务商
@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def provider_create(request):
    """创建服务商"""
    try:
        # 解析请求数据
        data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['name', 'code']
        is_valid, missing_fields = validate_required_fields(data, required_fields)
        if not is_valid:
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        username = user_info.get('user_name')
        
        name = data.get('name')
        code = data.get('code')
        desc = data.get('desc', '')
        
        # 检查同一用户下是否已存在相同的服务商标识
        if check_record_exists('llmprovider', {'code': code, 'user_id': user_id}):
            return create_error_response(f"服务商标识 '{code}' 已存在，请使用其他标识")
        
        # 检查同一用户下是否已存在相同的服务商名称
        if check_record_exists('llmprovider', {'name': name, 'user_id': user_id}):
            return create_error_response(f"服务商名称 '{name}' 已存在，请使用其他名称")
        
        # 插入数据
        sql = """
            INSERT INTO llmprovider (name, code, `desc`, user_id, username, create_time, update_time) 
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
        """
        affected_rows = execute_update_with_params(sql, [name, code, desc, user_id, username])
        
        if affected_rows > 0:
            return create_success_response(status=201)
        else:
            return create_error_response("创建失败", 500)
            
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response(str(e), 500)


# 更新服务商
@require_http_methods(["PUT"])
@csrf_exempt
@jwt_required()
def provider_update(request, provider_id):
    """更新服务商"""
    try:
        # 解析请求数据
        data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['name', 'code']
        is_valid, missing_fields = validate_required_fields(data, required_fields)
        if not is_valid:
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        name = data.get('name')
        code = data.get('code')
        desc = data.get('desc', '')
        
        # 获取记录并检查权限
        record = get_record_by_id('llmprovider', provider_id)
        if not record:
            return create_error_response("服务商不存在", 404)
        
        if not check_resource_permission(request, record['user_id']):
            return create_error_response("服务商不存在或无权限操作", 404)
        
        # 获取服务商的所属用户ID（用于唯一性检查）
        provider_user_id = record['user_id']
        
        # 检查同一用户下是否已存在相同的服务商标识（排除当前记录）
        existing_sql = "SELECT id FROM llmprovider WHERE code = %s AND user_id = %s AND id != %s"
        existing = execute_query_with_params(existing_sql, [code, provider_user_id, provider_id])
        if existing:
            return create_error_response(f"服务商标识 '{code}' 已存在，请使用其他标识")
        
        # 检查同一用户下是否已存在相同的服务商名称（排除当前记录）
        existing_sql = "SELECT id FROM llmprovider WHERE name = %s AND user_id = %s AND id != %s"
        existing = execute_query_with_params(existing_sql, [name, provider_user_id, provider_id])
        if existing:
            return create_error_response(f"服务商名称 '{name}' 已存在，请使用其他名称")
        
        # 更新数据
        sql = "UPDATE llmprovider SET name = %s, code = %s, `desc` = %s, update_time = NOW() WHERE id = %s"
        affected_rows = execute_update_with_params(sql, [name, code, desc, provider_id])
        
        if affected_rows > 0:
            return create_success_response()
        else:
            return create_error_response("更新失败", 500)
            
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response(str(e), 500)


# 删除服务商
@require_http_methods(["DELETE"])
@csrf_exempt
@jwt_required()
def provider_delete(request, provider_id):
    """删除服务商"""
    try:
        # 获取记录并检查权限
        record = get_record_by_id('llmprovider', provider_id)
        if not record:
            return create_error_response("服务商不存在", 404)
        
        if not check_resource_permission(request, record['user_id']):
            return create_error_response("服务商不存在或无权限操作", 404)
        
        # 检查是否有关联的模型配置
        models_sql = "SELECT id FROM llmmodel WHERE provider_id = %s"
        models = execute_query_with_params(models_sql, [provider_id])
        if models:
            return create_error_response("该服务商下还有模型配置，请先删除相关模型配置")
        
        # 删除服务商
        sql = "DELETE FROM llmprovider WHERE id = %s"
        affected_rows = execute_update_with_params(sql, [provider_id])
        
        if affected_rows > 0:
            return create_success_response()
        else:
            return create_error_response("删除失败", 500)
            
    except Exception as e:
        return create_error_response(str(e), 500)


# 模型配置列表
@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def model_list(request):
    """获取模型配置列表"""
    try:
        # 获取用户过滤条件
        where_clause, params = get_user_filter_condition(request)
        
        # 构建SQL
        sql = f"""
            SELECT m.id, m.provider_id, m.name, m.model_type, m.api_key, m.base_url, 
                   m.max_tokens, m.temperature, m.is_default, m.user_id, m.username, 
                   m.create_time, m.update_time, p.name as provider_name
            FROM llmmodel m
            LEFT JOIN llmprovider p ON m.provider_id = p.id
            {where_clause}
            ORDER BY m.create_time DESC
        """
        
        data = execute_query_with_params(sql, params)
        return create_success_response(data)
        
    except Exception as e:
        return create_error_response(str(e), 500)


# 新增模型配置
@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def model_create(request):
    """创建模型配置"""
    try:
        # 解析请求数据
        data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['provider_id', 'name', 'model_type', 'api_key', 'base_url']
        is_valid, missing_fields = validate_required_fields(data, required_fields)
        if not is_valid:
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        username = user_info.get('user_name')
        
        provider_id = data.get('provider_id')
        name = data.get('name')
        model_type = data.get('model_type')
        api_key = data.get('api_key')
        base_url = data.get('base_url')
        max_tokens = data.get('max_tokens', 4096)
        temperature = data.get('temperature', 0.7)
        is_default = data.get('is_default', False)
        
        # 检查服务商是否存在且有权限
        provider = get_record_by_id('llmprovider', provider_id)
        if not provider:
            return create_error_response("服务商不存在")
        
        if not check_resource_permission(request, provider['user_id']):
            return create_error_response("无权限使用该服务商")
        
        # 检查同一用户下是否已存在相同的模型名称
        if check_record_exists('llmmodel', {'name': name, 'user_id': user_id}):
            return create_error_response(f"模型名称 '{name}' 已存在，请使用其他名称")
        
        # 如果设置为默认，先取消其他默认模型
        if is_default:
            sql = "UPDATE llmmodel SET is_default = 0 WHERE user_id = %s"
            execute_update_with_params(sql, [user_id])
        
        # 插入数据
        sql = """
            INSERT INTO llmmodel 
            (provider_id, name, model_type, api_key, base_url, max_tokens, temperature, is_default, user_id, username, create_time, update_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        params = [provider_id, name, model_type, api_key, base_url, max_tokens, temperature, is_default, user_id, username]
        
        affected_rows = execute_update_with_params(sql, params)
        if affected_rows > 0:
            return create_success_response(status=201)
        else:
            return create_error_response("创建失败", 500)
            
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response(str(e), 500)


# 更新模型配置
@require_http_methods(["PUT"])
@csrf_exempt
@jwt_required()
def model_update(request, model_id):
    """更新模型配置"""
    try:
        # 解析请求数据
        data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['name', 'model_type', 'api_key', 'base_url']
        is_valid, missing_fields = validate_required_fields(data, required_fields)
        if not is_valid:
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        # 获取记录并检查权限
        record = get_record_by_id('llmmodel', model_id)
        if not record:
            return create_error_response("模型配置不存在", 404)
        
        if not check_resource_permission(request, record['user_id']):
            return create_error_response("模型配置不存在或无权限操作", 404)
        
        name = data.get('name')
        model_type = data.get('model_type')
        api_key = data.get('api_key')
        base_url = data.get('base_url')
        max_tokens = data.get('max_tokens', 4096)
        temperature = data.get('temperature', 0.7)
        is_default = data.get('is_default', False)
        
        # 检查同一用户下是否已存在相同的模型名称（排除当前记录）
        model_user_id = record['user_id']
        existing_sql = "SELECT id FROM llmmodel WHERE name = %s AND user_id = %s AND id != %s"
        existing = execute_query_with_params(existing_sql, [name, model_user_id, model_id])
        if existing:
            return create_error_response(f"模型名称 '{name}' 已存在，请使用其他名称")
        
        # 如果设置为默认，先取消其他默认模型
        if is_default:
            sql = "UPDATE llmmodel SET is_default = 0 WHERE user_id = %s AND id != %s"
            execute_update_with_params(sql, [model_user_id, model_id])
        
        # 更新数据
        sql = """
            UPDATE llmmodel 
            SET name = %s, model_type = %s, api_key = %s, base_url = %s, 
                max_tokens = %s, temperature = %s, is_default = %s, update_time = NOW()
            WHERE id = %s
        """
        params = [name, model_type, api_key, base_url, max_tokens, temperature, is_default, model_id]
        
        affected_rows = execute_update_with_params(sql, params)
        if affected_rows > 0:
            return create_success_response()
        else:
            return create_error_response("更新失败", 500)
            
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response(str(e), 500)


# 删除模型配置
@require_http_methods(["DELETE"])
@csrf_exempt
@jwt_required()
def model_delete(request, model_id):
    """删除模型配置"""
    try:
        # 获取记录并检查权限
        record = get_record_by_id('llmmodel', model_id)
        if not record:
            return create_error_response("模型配置不存在", 404)
        
        if not check_resource_permission(request, record['user_id']):
            return create_error_response("模型配置不存在或无权限操作", 404)
        
        # 删除模型配置
        sql = "DELETE FROM llmmodel WHERE id = %s"
        affected_rows = execute_update_with_params(sql, [model_id])
        
        if affected_rows > 0:
            return create_success_response()
        else:
            return create_error_response("删除失败", 500)
            
    except Exception as e:
        return create_error_response(str(e), 500)


# 设置默认模型
@require_http_methods(["PATCH"])
@csrf_exempt
@jwt_required()
def model_set_default(request, model_id):
    """设置默认模型"""
    try:
        # 获取记录并检查权限
        record = get_record_by_id('llmmodel', model_id)
        if not record:
            return create_error_response("模型配置不存在", 404)
        
        if not check_resource_permission(request, record['user_id']):
            return create_error_response("模型配置不存在或无权限操作", 404)
        
        user_id = record['user_id']
        
        # 先取消所有默认模型
        sql = "UPDATE llmmodel SET is_default = 0 WHERE user_id = %s"
        execute_update_with_params(sql, [user_id])
        
        # 设置当前模型为默认
        sql = "UPDATE llmmodel SET is_default = 1 WHERE id = %s"
        affected_rows = execute_update_with_params(sql, [model_id])
        
        if affected_rows > 0:
            return create_success_response()
        else:
            return create_error_response("设置失败", 500)
            
    except Exception as e:
        return create_error_response(str(e), 500)


# 测试模型连接
@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def model_test(request, model_id):
    """测试模型连接"""
    try:
        # 解析请求数据
        data = parse_json_body(request)
        prompt = data.get('prompt', '你好')
        
        # 获取记录并检查权限
        record = get_record_by_id('llmmodel', model_id)
        if not record:
            return create_error_response("模型配置不存在", 404)
        
        if not check_resource_permission(request, record['user_id']):
            return create_error_response("模型配置不存在或无权限操作", 404)
        
        # TODO: 这里应该实现实际的模型测试逻辑
        # 目前返回模拟响应
        test_response = {
            "response": f"这是对提示词 '{prompt}' 的模拟响应",
            "model_info": {
                "name": record['name'],
                "model_type": record['model_type'],
                "base_url": record['base_url']
            }
        }
        
        return create_success_response(test_response)
        
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response(str(e), 500)
