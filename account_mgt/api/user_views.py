import json
import logging
from datetime import datetime

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
from account_mgt.utils.pwd_utils import hash_password, verify_password

# 获取模块日志记录器
logger = logging.getLogger('account_mgt')


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def user_list(request):
    """获取用户列表 - 管理员可以看到所有用户，普通用户只能看到自己"""
    logger.info("查询用户列表")
    
    try:
        # 获取用户过滤条件
        where_clause, params = get_user_filter_condition(request)
        
        # 构建SQL
        sql = f"""
            SELECT 
                u.id, 
                u.username, 
                u.email, 
                u.role_id, 
                u.is_active, 
                u.create_time, 
                u.update_time,
                r.name as role_name
            FROM user u
            LEFT JOIN role r ON u.role_id = r.id
            {where_clause}
            ORDER BY u.create_time DESC
        """
        
        # 执行查询
        data = execute_query_with_params(sql, params)
        
        logger.info(f"查询到 {len(data)} 条用户记录")
        return create_success_response({
            "data": data,
            "total_records": len(data)
        })
        
    except Exception as e:
        logger.error(f"查询用户列表出错: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def create_user(request):
    """创建用户 - 只有管理员可以创建用户"""
    logger.info("创建用户请求")
    
    try:
        # 检查是否为管理员
        user_info = get_user_from_request(request)
        if user_info.get('role_id') != 1:
            logger.warning(f"非管理员用户尝试创建用户: {user_info.get('user_name')}")
            return create_error_response("只有管理员可以创建用户", 403)
        
        # 解析请求数据
        request_data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['username', 'email', 'password', 'role_id']
        is_valid, missing_fields = validate_required_fields(request_data, required_fields)
        if not is_valid:
            logger.warning(f"创建用户失败: 缺少必填字段 - {missing_fields}")
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        username = request_data.get('username')
        email = request_data.get('email')
        password = request_data.get('password')
        role_id = request_data.get('role_id')
        is_active = request_data.get('is_active', True)
        
        # 检查用户名是否已存在
        if check_record_exists('user', {'username': username}):
            logger.warning(f"创建用户失败: 用户名'{username}'已存在")
            return create_error_response("用户名已存在")
        
        # 检查邮箱是否已存在
        if check_record_exists('user', {'email': email}):
            logger.warning(f"创建用户失败: 邮箱'{email}'已存在")
            return create_error_response("邮箱已存在")
        
        # 检查角色是否存在
        if not check_record_exists('role', {'id': role_id}):
            logger.warning(f"创建用户失败: 角色ID'{role_id}'不存在")
            return create_error_response("指定的角色不存在")
        
        # 加密密码
        hashed_password = hash_password(password)
        
        # 插入数据
        sql = """
            INSERT INTO user (username, email, password, role_id, is_active)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = [username, email, hashed_password, role_id, is_active]
        
        affected_rows = execute_update_with_params(sql, params)
        if affected_rows > 0:
            new_id = get_last_insert_id()
            logger.info(f"成功创建用户: ID={new_id}, 用户名={username}")
            return create_success_response({"id": new_id}, 201)
        else:
            return create_error_response("创建失败", 500)
            
    except ValueError as e:
        logger.error(f"创建用户数据解析错误: {str(e)}", exc_info=True)
        return create_error_response(str(e))
    except Exception as e:
        logger.error(f"创建用户异常: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@csrf_exempt
@jwt_required()
def update_user(request, user_id):
    """更新或删除用户"""
    
    if request.method == 'PUT':
        return _update_user(request, user_id)
    elif request.method == 'DELETE':
        return _delete_user(request, user_id)
    else:
        return create_error_response("不支持的请求方法", 405)


def _update_user(request, user_id):
    """更新用户"""
    logger.info(f"更新用户请求: ID={user_id}")
    
    try:
        # 解析请求数据
        request_data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['username', 'email', 'role_id']
        is_valid, missing_fields = validate_required_fields(request_data, required_fields)
        if not is_valid:
            logger.warning(f"更新用户失败: ID={user_id}, 缺少必填字段")
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        username = request_data.get('username')
        email = request_data.get('email')
        role_id = request_data.get('role_id')
        is_active = request_data.get('is_active', True)
        password = request_data.get('password')  # 可选，如果提供则更新密码
        
        # 获取记录并检查权限
        record = get_record_by_id('user', user_id)
        if not record:
            logger.warning(f"更新用户失败: ID={user_id} 不存在")
            return create_error_response("用户不存在", 404)
        
        # 检查权限：管理员可以更新所有用户，普通用户只能更新自己
        current_user = get_user_from_request(request)
        if current_user.get('role_id') != 1 and current_user.get('user_id') != int(user_id):
            logger.warning(f"更新用户失败: ID={user_id} 无权限")
            return create_error_response("用户不存在或无权限操作", 404)
        
        # 检查用户名是否与其他用户冲突
        existing_sql = "SELECT id FROM user WHERE username = %s AND id != %s"
        existing = execute_query_with_params(existing_sql, [username, user_id])
        if existing:
            logger.warning(f"更新用户失败: ID={user_id}, 用户名'{username}'已存在")
            return create_error_response("用户名已存在")
        
        # 检查邮箱是否与其他用户冲突
        existing_sql = "SELECT id FROM user WHERE email = %s AND id != %s"
        existing = execute_query_with_params(existing_sql, [email, user_id])
        if existing:
            logger.warning(f"更新用户失败: ID={user_id}, 邮箱'{email}'已存在")
            return create_error_response("邮箱已存在")
        
        # 检查角色是否存在
        if not check_record_exists('role', {'id': role_id}):
            logger.warning(f"更新用户失败: ID={user_id}, 角色ID'{role_id}'不存在")
            return create_error_response("指定的角色不存在")
        
        # 构建更新SQL
        if password:
            # 如果提供了密码，则更新密码
            hashed_password = hash_password(password)
            sql = """
                UPDATE user 
                SET username = %s, email = %s, password = %s, role_id = %s, is_active = %s
                WHERE id = %s
            """
            params = [username, email, hashed_password, role_id, is_active, user_id]
        else:
            # 不更新密码
            sql = """
                UPDATE user 
                SET username = %s, email = %s, role_id = %s, is_active = %s
                WHERE id = %s
            """
            params = [username, email, role_id, is_active, user_id]
        
        affected_rows = execute_update_with_params(sql, params)
        
        if affected_rows > 0:
            logger.info(f"成功更新用户: ID={user_id}, 用户名={username}")
            return create_success_response()
        else:
            return create_error_response("更新失败", 500)
            
    except ValueError as e:
        logger.error(f"更新用户数据解析错误: ID={user_id}, 错误={str(e)}", exc_info=True)
        return create_error_response(str(e))
    except Exception as e:
        logger.error(f"更新用户异常: ID={user_id}, 错误={str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


def _delete_user(request, user_id):
    """删除用户 - 只有管理员可以删除用户"""
    logger.info(f"删除用户请求: ID={user_id}")
    
    try:
        # 检查是否为管理员
        user_info = get_user_from_request(request)
        if user_info.get('role_id') != 1:
            logger.warning(f"非管理员用户尝试删除用户: {user_info.get('user_name')}")
            return create_error_response("只有管理员可以删除用户", 403)
        
        # 获取记录
        record = get_record_by_id('user', user_id)
        if not record:
            logger.warning(f"删除用户失败: ID={user_id} 不存在")
            return create_error_response("用户不存在", 404)
        
        # 不能删除自己
        if user_info.get('user_id') == int(user_id):
            logger.warning(f"管理员尝试删除自己: ID={user_id}")
            return create_error_response("不能删除自己")
        
        # 检查是否有关联数据（知识库、模型配置等）
        # 这里可以根据需要添加更多的关联检查
        knowledge_sql = "SELECT id FROM knowledge_database WHERE user_id = %s LIMIT 1"
        knowledge = execute_query_with_params(knowledge_sql, [user_id])
        if knowledge:
            return create_error_response("该用户还有关联的知识库，请先删除相关数据")
        
        # 删除用户
        sql = "DELETE FROM user WHERE id = %s"
        affected_rows = execute_update_with_params(sql, [user_id])
        
        if affected_rows > 0:
            logger.info(f"成功删除用户: ID={user_id}")
            return create_success_response()
        else:
            return create_error_response("删除失败", 500)
            
    except Exception as e:
        logger.error(f"删除用户异常: ID={user_id}, 错误={str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def role_list(request):
    """获取角色列表"""
    logger.info("查询角色列表")
    
    try:
        sql = "SELECT id, name, description FROM role ORDER BY id"
        data = execute_query_with_params(sql, [])
        
        logger.info(f"查询到 {len(data)} 条角色记录")
        return create_success_response(data)
        
    except Exception as e:
        logger.error(f"查询角色列表出错: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def change_password(request):
    """修改密码"""
    logger.info("修改密码请求")
    
    try:
        # 解析请求数据
        request_data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['old_password', 'new_password']
        is_valid, missing_fields = validate_required_fields(request_data, required_fields)
        if not is_valid:
            logger.warning("修改密码失败: 缺少必填字段")
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        old_password = request_data.get('old_password')
        new_password = request_data.get('new_password')
        
        # 获取当前用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        # 获取用户当前密码
        user_record = get_record_by_id('user', user_id)
        if not user_record:
            logger.warning(f"修改密码失败: 用户ID={user_id} 不存在")
            return create_error_response("用户不存在", 404)
        
        # 验证旧密码
        if not verify_password(old_password, user_record['password']):
            logger.warning(f"修改密码失败: 用户ID={user_id} 旧密码错误")
            return create_error_response("旧密码错误")
        
        # 加密新密码
        hashed_new_password = hash_password(new_password)
        
        # 更新密码
        sql = "UPDATE user SET password = %s WHERE id = %s"
        affected_rows = execute_update_with_params(sql, [hashed_new_password, user_id])
        
        if affected_rows > 0:
            logger.info(f"成功修改密码: 用户ID={user_id}")
            return create_success_response()
        else:
            return create_error_response("修改失败", 500)
            
    except ValueError as e:
        logger.error(f"修改密码数据解析错误: {str(e)}", exc_info=True)
        return create_error_response(str(e))
    except Exception as e:
        logger.error(f"修改密码异常: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def user_profile(request):
    """获取当前用户信息"""
    logger.info("获取用户信息请求")
    
    try:
        # 获取当前用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        
        # 查询用户详细信息
        sql = """
            SELECT 
                u.id, 
                u.username, 
                u.email, 
                u.role_id, 
                u.is_active, 
                u.create_time, 
                u.update_time,
                r.name as role_name
            FROM user u
            LEFT JOIN role r ON u.role_id = r.id
            WHERE u.id = %s
        """
        
        data = execute_query_with_params(sql, [user_id])
        if not data:
            logger.warning(f"获取用户信息失败: 用户ID={user_id} 不存在")
            return create_error_response("用户不存在", 404)
        
        user_data = data[0]
        # 移除密码字段（如果有的话）
        user_data.pop('password', None)
        
        logger.info(f"成功获取用户信息: 用户ID={user_id}")
        return create_success_response(user_data)
        
    except Exception as e:
        logger.error(f"获取用户信息异常: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500) 