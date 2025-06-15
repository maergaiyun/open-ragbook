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
    """获取服务商列表（包含公共服务商和用户自己的服务商）"""
    try:
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 构建SQL - 获取公共服务商和用户自己的服务商
        if role_id == 1:  # 管理员可以看到所有服务商
            sql = """
                SELECT id, name, code, `desc`, user_id, username, create_time, update_time,
                       is_public, created_by, created_at, updated_at
                FROM llmprovider 
                ORDER BY is_public DESC, create_time DESC
            """
            params = []
        else:  # 普通用户只能看到公共服务商和自己的服务商
            sql = """
                SELECT id, name, code, `desc`, user_id, username, create_time, update_time,
                       is_public, created_by, created_at, updated_at
                FROM llmprovider 
                WHERE is_public = 1 OR created_by = %s
                ORDER BY is_public DESC, create_time DESC
            """
            params = [user_id]
        
        data = execute_query_with_params(sql, params)
        
        # 为每个服务商添加权限信息
        for provider in data:
            provider['can_edit'] = (role_id == 1 or provider['created_by'] == user_id)
            provider['can_delete'] = (role_id == 1 or provider['created_by'] == user_id)
        
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
        is_public = data.get('is_public', False)  # 是否为公共服务商
        
        # 检查全局是否已存在相同的服务商标识（公共服务商需要全局唯一）
        if is_public:
            if check_record_exists('llmprovider', {'code': code}):
                return create_error_response(f"服务商标识 '{code}' 已存在，请使用其他标识")
            if check_record_exists('llmprovider', {'name': name}):
                return create_error_response(f"服务商名称 '{name}' 已存在，请使用其他名称")
        else:
            # 私有服务商只需要在用户范围内唯一
            if check_record_exists('llmprovider', {'code': code, 'created_by': user_id}):
                return create_error_response(f"服务商标识 '{code}' 已存在，请使用其他标识")
            if check_record_exists('llmprovider', {'name': name, 'created_by': user_id}):
                return create_error_response(f"服务商名称 '{name}' 已存在，请使用其他名称")
        
        # 插入数据
        sql = """
            INSERT INTO llmprovider (name, code, `desc`, user_id, username, is_public, created_by, create_time, update_time) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        affected_rows = execute_update_with_params(sql, [name, code, desc, user_id, username, is_public, user_id])
        
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
        is_public = data.get('is_public', False)
        
        # 获取记录并检查权限
        record = get_record_by_id('llmprovider', provider_id)
        if not record:
            return create_error_response("服务商不存在", 404)
        
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 检查权限：管理员或创建者可以修改
        if role_id != 1 and record.get('created_by') != user_id:
            return create_error_response("无权限修改此服务商", 403)
        
        # 只有当名称或标识发生变化时才检查唯一性
        name_changed = record.get('name') != name
        code_changed = record.get('code') != code
        
        if name_changed or code_changed:
            # 检查唯一性
            if is_public:
                # 公共服务商需要全局唯一
                if code_changed:
                    existing_sql = "SELECT id FROM llmprovider WHERE code = %s AND id != %s"
                    existing = execute_query_with_params(existing_sql, [code, provider_id])
                    if existing:
                        return create_error_response(f"服务商标识 '{code}' 已存在，请使用其他标识")
                
                if name_changed:
                    existing_sql = "SELECT id FROM llmprovider WHERE name = %s AND id != %s"
                    existing = execute_query_with_params(existing_sql, [name, provider_id])
                    if existing:
                        return create_error_response(f"服务商名称 '{name}' 已存在，请使用其他名称")
            else:
                # 私有服务商在用户范围内唯一
                created_by = record.get('created_by')
                if code_changed:
                    existing_sql = "SELECT id FROM llmprovider WHERE code = %s AND created_by = %s AND id != %s"
                    existing = execute_query_with_params(existing_sql, [code, created_by, provider_id])
                    if existing:
                        return create_error_response(f"服务商标识 '{code}' 已存在，请使用其他标识")
                
                if name_changed:
                    existing_sql = "SELECT id FROM llmprovider WHERE name = %s AND created_by = %s AND id != %s"
                    existing = execute_query_with_params(existing_sql, [name, created_by, provider_id])
                    if existing:
                        return create_error_response(f"服务商名称 '{name}' 已存在，请使用其他名称")
        
        # 更新数据
        sql = "UPDATE llmprovider SET name = %s, code = %s, `desc` = %s, is_public = %s, update_time = NOW() WHERE id = %s"
        affected_rows = execute_update_with_params(sql, [name, code, desc, is_public, provider_id])
        
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
        
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 检查权限：管理员或创建者可以删除
        if role_id != 1 and record.get('created_by') != user_id:
            return create_error_response("无权限删除此服务商", 403)
        
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
    """获取模型配置列表（包含公共模型和用户自己的模型）"""
    try:
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 构建SQL - 获取公共模型和用户自己的模型
        if role_id == 1:  # 管理员可以看到所有模型
            sql = """
                SELECT m.id, m.provider_id, m.name, m.model_type, m.api_key, m.base_url, 
                       m.max_tokens, m.temperature, m.is_default, m.user_id, m.username, 
                       m.create_time, m.update_time, m.is_public, m.created_by, m.created_at, m.updated_at,
                       p.name as provider_name
                FROM llmmodel m
                LEFT JOIN llmprovider p ON m.provider_id = p.id
                ORDER BY m.is_public DESC, m.create_time DESC
            """
            params = []
        else:  # 普通用户只能看到公共模型和自己的模型
            sql = """
                SELECT m.id, m.provider_id, m.name, m.model_type, m.api_key, m.base_url, 
                       m.max_tokens, m.temperature, m.is_default, m.user_id, m.username, 
                       m.create_time, m.update_time, m.is_public, m.created_by, m.created_at, m.updated_at,
                       p.name as provider_name
                FROM llmmodel m
                LEFT JOIN llmprovider p ON m.provider_id = p.id
                WHERE m.is_public = 1 OR m.created_by = %s
                ORDER BY m.is_public DESC, m.create_time DESC
            """
            params = [user_id]
        
        data = execute_query_with_params(sql, params)
        
        # 为每个模型添加权限信息
        for model in data:
            model['can_edit'] = (role_id == 1 or model['created_by'] == user_id)
            model['can_delete'] = (role_id == 1 or model['created_by'] == user_id)
        
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
        is_public = data.get('is_public', False)  # 是否为公共模型
        
        # 检查服务商是否存在且有权限
        provider = get_record_by_id('llmprovider', provider_id)
        if not provider:
            return create_error_response("服务商不存在")
        
        # 检查是否有权限使用该服务商（公共服务商或自己创建的服务商）
        role_id = user_info.get('role_id')
        if role_id != 1 and not provider.get('is_public') and provider.get('created_by') != user_id:
            return create_error_response("无权限使用该服务商")
        
        # 检查模型名称唯一性
        if is_public:
            # 公共模型需要全局唯一
            if check_record_exists('llmmodel', {'name': name}):
                return create_error_response(f"模型名称 '{name}' 已存在，请使用其他名称")
        else:
            # 私有模型在用户范围内唯一
            if check_record_exists('llmmodel', {'name': name, 'created_by': user_id}):
                return create_error_response(f"模型名称 '{name}' 已存在，请使用其他名称")
        
        # 如果设置为默认，先取消其他默认模型
        if is_default:
            if is_public:
                # 公共默认模型：取消所有默认模型
                sql = "UPDATE llmmodel SET is_default = 0"
                execute_update_with_params(sql, [])
            else:
                # 私有默认模型：只取消用户自己的默认模型
                sql = "UPDATE llmmodel SET is_default = 0 WHERE created_by = %s"
                execute_update_with_params(sql, [user_id])
        
        # 插入数据
        sql = """
            INSERT INTO llmmodel 
            (provider_id, name, model_type, api_key, base_url, max_tokens, temperature, is_default, 
             user_id, username, is_public, created_by, create_time, update_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """
        params = [provider_id, name, model_type, api_key, base_url, max_tokens, temperature, is_default, 
                 user_id, username, is_public, user_id]
        
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
        
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 检查权限：管理员或创建者可以修改
        if role_id != 1 and record.get('created_by') != user_id:
            return create_error_response("无权限修改此模型配置", 403)
        
        name = data.get('name')
        model_type = data.get('model_type')
        api_key = data.get('api_key')
        base_url = data.get('base_url')
        max_tokens = data.get('max_tokens', 4096)
        temperature = data.get('temperature', 0.7)
        is_default = data.get('is_default', False)
        is_public = data.get('is_public', record.get('is_public', False))
        
        # 只有当名称发生变化时才检查唯一性
        name_changed = record.get('name') != name
        
        if name_changed:
            # 检查模型名称唯一性
            if is_public:
                # 公共模型需要全局唯一
                existing_sql = "SELECT id FROM llmmodel WHERE name = %s AND id != %s"
                existing = execute_query_with_params(existing_sql, [name, model_id])
                if existing:
                    return create_error_response(f"模型名称 '{name}' 已存在，请使用其他名称")
            else:
                # 私有模型在用户范围内唯一
                created_by = record.get('created_by')
                existing_sql = "SELECT id FROM llmmodel WHERE name = %s AND created_by = %s AND id != %s"
                existing = execute_query_with_params(existing_sql, [name, created_by, model_id])
                if existing:
                    return create_error_response(f"模型名称 '{name}' 已存在，请使用其他名称")
        
        # 如果设置为默认，先取消其他默认模型
        if is_default:
            if is_public:
                # 公共默认模型：取消所有默认模型
                sql = "UPDATE llmmodel SET is_default = 0 WHERE id != %s"
                execute_update_with_params(sql, [model_id])
            else:
                # 私有默认模型：只取消用户自己的默认模型
                created_by = record.get('created_by')
                sql = "UPDATE llmmodel SET is_default = 0 WHERE created_by = %s AND id != %s"
                execute_update_with_params(sql, [created_by, model_id])
        
        # 更新数据
        sql = """
            UPDATE llmmodel 
            SET name = %s, model_type = %s, api_key = %s, base_url = %s, 
                max_tokens = %s, temperature = %s, is_default = %s, is_public = %s, update_time = NOW()
            WHERE id = %s
        """
        params = [name, model_type, api_key, base_url, max_tokens, temperature, is_default, is_public, model_id]
        
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
        
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 检查权限：管理员或创建者可以删除
        if role_id != 1 and record.get('created_by') != user_id:
            return create_error_response("无权限删除此模型配置", 403)
        
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
        
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 检查权限：管理员或创建者可以设置默认
        if role_id != 1 and record.get('created_by') != user_id:
            return create_error_response("无权限设置此模型为默认", 403)
        
        is_public = record.get('is_public', False)
        
        # 根据模型类型取消其他默认模型
        if is_public:
            # 公共默认模型：取消所有默认模型
            sql = "UPDATE llmmodel SET is_default = 0 WHERE id != %s"
            execute_update_with_params(sql, [model_id])
        else:
            # 私有默认模型：只取消用户自己的默认模型
            created_by = record.get('created_by')
            sql = "UPDATE llmmodel SET is_default = 0 WHERE created_by = %s AND id != %s"
            execute_update_with_params(sql, [created_by, model_id])
        
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
    import openai
    import time
    
    try:
        # 解析请求数据
        data = parse_json_body(request)
        prompt = data.get('prompt', '你好，请简单介绍一下你自己。')
        
        # 获取记录并检查权限
        record = get_record_by_id('llmmodel', model_id)
        if not record:
            return create_error_response("模型配置不存在", 404)
        
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')
        
        # 检查权限：管理员、创建者或公共模型都可以测试
        if role_id != 1 and record.get('created_by') != user_id and not record.get('is_public'):
            return create_error_response("无权限测试此模型配置", 403)
        
        # 获取模型配置
        api_key = record.get('api_key')
        base_url = record.get('base_url')
        model_type = record.get('model_type')
        max_tokens = record.get('max_tokens', 2000)
        temperature = record.get('temperature', 0.7)
        
        if not api_key:
            return create_error_response("模型配置缺少API密钥")
        
        if not base_url:
            return create_error_response("模型配置缺少API地址")
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 创建OpenAI客户端
            client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            
            # 构建消息
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # 调用模型API
            response = client.chat.completions.create(
                model=model_type,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 计算响应时间
            response_time = (time.time() - start_time) * 1000
            
            # 提取响应内容
            assistant_response = response.choices[0].message.content
            
            # 构建测试结果
            test_response = {
                "success": True,
                "response": assistant_response,
                "model_info": {
                    "name": record['name'],
                    "model_type": model_type,
                    "base_url": base_url,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                "performance": {
                    "response_time_ms": round(response_time, 1),
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                "test_prompt": prompt
            }
            
            return create_success_response(test_response)
            
        except openai.AuthenticationError as e:
            return create_error_response(f"API密钥认证失败: {str(e)}")
        except openai.RateLimitError as e:
            return create_error_response(f"API调用频率限制: {str(e)}")
        except openai.APIConnectionError as e:
            return create_error_response(f"API连接失败: {str(e)}")
        except openai.APIError as e:
            return create_error_response(f"API调用错误: {str(e)}")
        except Exception as api_error:
            return create_error_response(f"模型调用失败: {str(api_error)}")
        
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response(f"测试失败: {str(e)}", 500)
