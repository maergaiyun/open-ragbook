import json
import re
from datetime import datetime

from account_mgt.utils.jwt_token_utils import *
from account_mgt.utils.pwd_utils import *
from open_ragbook_server.utils.response_code import *
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db import transaction


def validate_email(email):
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone):
    """验证手机号格式"""
    if not phone:
        return True  # 手机号可以为空
    pattern = r'^1[3-9]\d{9}$'
    return re.match(pattern, phone) is not None


def check_permission(user_role_id, required_permission):
    """检查用户权限"""
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT permissions FROM role WHERE id = %s AND status = 1
        ''', [user_role_id])
        result = cursor.fetchone()
        if not result or not result[0]:
            return False
        
        permissions = json.loads(result[0])
        return permissions.get(required_permission, False)


@require_http_methods(["POST"])
@csrf_exempt
def login(request):
    """ 登录 """
    request_data = json.loads(request.body.decode('utf-8'))
    username = request_data.get('username')
    password = request_data.get('password')
    
    with connection.cursor() as cursor:
        cursor.execute('''
                    SELECT u.id, u.username, u.email, u.real_name, u.phone, u.role_id, u.password, u.status,
                           r.name, r.description, r.permissions
                    FROM user u
                    JOIN role r ON u.role_id = r.id
                    WHERE u.username = %s AND u.status = 1 AND r.status = 1
                    LIMIT 1
                ''', [username])
        # 获取列名
        columns = [col[0] for col in cursor.description]
        # 获取查询结果
        rows = cursor.fetchall()
        # 将结果转换为字典列表
        results = []
        for row in rows:
            result_dict = dict(zip(columns, row))
            results.append(result_dict)
        
        if not results:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="账号或密码错误"),
                status=200
            )

        old_password = results[0].get("password")
        login_status = decrypt_pwd_with_fixed_salt(password, old_password)
        if not login_status:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="账号或密码错误"),
                status=200
            )
        
        # 更新最后登录时间
        cursor.execute('''
            UPDATE user SET last_login_at = %s WHERE id = %s
        ''', [datetime.now(), results[0].get('id')])
        
        user = {
            'user_id': results[0].get('id'),
            'user_name': results[0].get('username'),
            'email': results[0].get('email'),
            'real_name': results[0].get('real_name'),
            'phone': results[0].get('phone'),
            'role_id': results[0].get('role_id'),
            'role_name': results[0].get('name'),
            'role_desc': results[0].get('description'),
            'permissions': json.loads(results[0].get('permissions') or '{}'),
        }
        token = generate_jwt_token(user)

        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(data={
                "user": user,
                "token": token
            }),
            status=200
        )


@require_http_methods(["POST"])
@csrf_exempt
def register(request):
    """ 用户注册 - 只允许注册普通用户 """
    request_data = json.loads(request.body.decode('utf-8'))
    username = (request_data.get('username') or '').strip()
    password = request_data.get('password') or ''
    email = (request_data.get('email') or '').strip()
    real_name = (request_data.get('real_name') or '').strip()
    phone = (request_data.get('phone') or '').strip()
    
    # 参数验证
    if not username or len(username) < 3:
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message="用户名不能为空且长度不能少于3位"),
            status=200
        )
    
    if not password or len(password) < 6:
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message="密码不能为空且长度不能少于6位"),
            status=200
        )
    
    if email and not validate_email(email):
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message="邮箱格式不正确"),
            status=200
        )
    
    if not validate_phone(phone):
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message="手机号格式不正确"),
            status=200
        )
    
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                # 检查用户名是否已存在
                cursor.execute('SELECT id FROM user WHERE username = %s', [username])
                if cursor.fetchone():
                    return JsonResponse(
                        ResponseCode.ERROR.to_dict(message="用户名已存在"),
                        status=200
                    )
                
                # 检查邮箱是否已存在
                if email:
                    cursor.execute('SELECT id FROM user WHERE email = %s', [email])
                    if cursor.fetchone():
                        return JsonResponse(
                            ResponseCode.ERROR.to_dict(message="邮箱已被注册"),
                            status=200
                        )
                
                # 加密密码
                encrypted_password = encrypt_pwd_with_fixed_salt(password)
                
                # 插入新用户，默认角色为普通用户(role_id=2)
                cursor.execute('''
                    INSERT INTO user (username, password, email, real_name, phone, role_id, status)
                    VALUES (%s, %s, %s, %s, %s, 2, 1)
                ''', [username, encrypted_password, email or None, real_name or None, phone or None])
                
                return JsonResponse(
                    ResponseCode.SUCCESS.to_dict(message="注册成功"),
                    status=200
                )
    
    except Exception as e:
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=f"注册失败: {str(e)}"),
            status=200
        )


@require_http_methods(["GET"])
@csrf_exempt
def get_users(request):
    """ 获取用户列表 - 需要管理员权限 """
    # 从JWT token中获取用户信息
    token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
    if not token:
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message="未授权访问"),
            status=401
        )
    
    try:
        user_info = parse_jwt_token(token)
        if not user_info or not check_permission(user_info.get('role_id'), 'user_manage'):
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="权限不足"),
                status=403
            )
    except:
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message="token无效"),
            status=401
        )
    
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    search = request.GET.get('search', '').strip()
    role_id = request.GET.get('role_id', '')
    status = request.GET.get('status', '')
    
    with connection.cursor() as cursor:
        # 构建查询条件
        where_conditions = []
        params = []
        
        if search:
            where_conditions.append('(u.username LIKE %s OR u.real_name LIKE %s OR u.email LIKE %s)')
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param])
        
        if role_id:
            where_conditions.append('u.role_id = %s')
            params.append(role_id)
        
        if status != '':
            where_conditions.append('u.status = %s')
            params.append(status)
        
        where_clause = ' AND '.join(where_conditions)
        if where_clause:
            where_clause = 'WHERE ' + where_clause
        
        # 查询总数
        count_sql = f'''
            SELECT COUNT(*) FROM user u
            JOIN role r ON u.role_id = r.id
            {where_clause}
        '''
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]
        
        # 查询数据
        offset = (page - 1) * page_size
        data_sql = f'''
            SELECT u.id, u.username, u.email, u.real_name, u.phone, u.role_id, u.status,
                   u.last_login_at, u.created_at, u.updated_at,
                   r.name as role_name, r.description as role_desc
            FROM user u
            JOIN role r ON u.role_id = r.id
            {where_clause}
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        '''
        cursor.execute(data_sql, params + [page_size, offset])
        
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        users = []
        for row in rows:
            user_dict = dict(zip(columns, row))
            # 格式化时间
            if user_dict['last_login_at']:
                user_dict['last_login_at'] = user_dict['last_login_at'].strftime('%Y-%m-%d %H:%M:%S')
            if user_dict['created_at']:
                user_dict['created_at'] = user_dict['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if user_dict['updated_at']:
                user_dict['updated_at'] = user_dict['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            users.append(user_dict)
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(data={
                'users': users,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }),
            status=200
        )


@require_http_methods(["POST"])
@csrf_exempt
def create_user(request):
    """ 创建用户 - 需要管理员权限 """
    # 权限检查
    token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
    if not token:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="未授权访问"), status=401)
    
    try:
        user_info = parse_jwt_token(token)
        if not user_info or not check_permission(user_info.get('role_id'), 'user_manage'):
            return JsonResponse(ResponseCode.ERROR.to_dict(message="权限不足"), status=403)
    except:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="token无效"), status=401)
    
    request_data = json.loads(request.body.decode('utf-8'))
    username = request_data.get('username', '').strip()
    password = request_data.get('password', '')
    email = request_data.get('email', '').strip()
    real_name = request_data.get('real_name', '').strip()
    phone = request_data.get('phone', '').strip()
    role_id = request_data.get('role_id')
    status = request_data.get('status', 1)
    
    # 参数验证
    if not username or len(username) < 3:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="用户名不能为空且长度不能少于3位"), status=200)
    
    if not password or len(password) < 6:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="密码不能为空且长度不能少于6位"), status=200)
    
    if not role_id:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="请选择用户角色"), status=200)
    
    if email and not validate_email(email):
        return JsonResponse(ResponseCode.ERROR.to_dict(message="邮箱格式不正确"), status=200)
    
    if not validate_phone(phone):
        return JsonResponse(ResponseCode.ERROR.to_dict(message="手机号格式不正确"), status=200)
    
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                # 检查用户名是否已存在
                cursor.execute('SELECT id FROM user WHERE username = %s', [username])
                if cursor.fetchone():
                    return JsonResponse(ResponseCode.ERROR.to_dict(message="用户名已存在"), status=200)
                
                # 检查邮箱是否已存在
                if email:
                    cursor.execute('SELECT id FROM user WHERE email = %s', [email])
                    if cursor.fetchone():
                        return JsonResponse(ResponseCode.ERROR.to_dict(message="邮箱已被注册"), status=200)
                
                # 检查角色是否存在
                cursor.execute('SELECT id FROM role WHERE id = %s AND status = 1', [role_id])
                if not cursor.fetchone():
                    return JsonResponse(ResponseCode.ERROR.to_dict(message="角色不存在或已禁用"), status=200)
                
                # 加密密码
                encrypted_password = encrypt_pwd_with_fixed_salt(password)
                
                # 插入新用户
                cursor.execute('''
                    INSERT INTO user (username, password, email, real_name, phone, role_id, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', [username, encrypted_password, email or None, real_name or None, phone or None, role_id, status])
                
                return JsonResponse(ResponseCode.SUCCESS.to_dict(message="用户创建成功"), status=200)
    
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=f"创建失败: {str(e)}"), status=200)


@require_http_methods(["PUT"])
@csrf_exempt
def update_user(request, user_id):
    """ 更新用户信息 - 需要管理员权限 """
    # 权限检查
    token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
    if not token:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="未授权访问"), status=401)
    
    try:
        user_info = parse_jwt_token(token)
        if not user_info or not check_permission(user_info.get('role_id'), 'user_manage'):
            return JsonResponse(ResponseCode.ERROR.to_dict(message="权限不足"), status=403)
    except:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="token无效"), status=401)
    
    request_data = json.loads(request.body.decode('utf-8'))
    username = request_data.get('username', '').strip()
    email = request_data.get('email', '').strip()
    real_name = request_data.get('real_name', '').strip()
    phone = request_data.get('phone', '').strip()
    role_id = request_data.get('role_id')
    status = request_data.get('status')
    password = request_data.get('password', '')
    
    # 参数验证
    if not username or len(username) < 3:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="用户名不能为空且长度不能少于3位"), status=200)
    
    if email and not validate_email(email):
        return JsonResponse(ResponseCode.ERROR.to_dict(message="邮箱格式不正确"), status=200)
    
    if not validate_phone(phone):
        return JsonResponse(ResponseCode.ERROR.to_dict(message="手机号格式不正确"), status=200)
    
    if password and len(password) < 6:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="密码长度不能少于6位"), status=200)
    
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                # 检查用户是否存在
                cursor.execute('SELECT id FROM user WHERE id = %s', [user_id])
                if not cursor.fetchone():
                    return JsonResponse(ResponseCode.ERROR.to_dict(message="用户不存在"), status=200)
                
                # 检查用户名是否被其他用户使用
                cursor.execute('SELECT id FROM user WHERE username = %s AND id != %s', [username, user_id])
                if cursor.fetchone():
                    return JsonResponse(ResponseCode.ERROR.to_dict(message="用户名已存在"), status=200)
                
                # 检查邮箱是否被其他用户使用
                if email:
                    cursor.execute('SELECT id FROM user WHERE email = %s AND id != %s', [email, user_id])
                    if cursor.fetchone():
                        return JsonResponse(ResponseCode.ERROR.to_dict(message="邮箱已被注册"), status=200)
                
                # 检查角色是否存在
                if role_id:
                    cursor.execute('SELECT id FROM role WHERE id = %s AND status = 1', [role_id])
                    if not cursor.fetchone():
                        return JsonResponse(ResponseCode.ERROR.to_dict(message="角色不存在或已禁用"), status=200)
                
                # 构建更新SQL
                update_fields = []
                params = []
                
                update_fields.append('username = %s')
                params.append(username)
                
                update_fields.append('email = %s')
                params.append(email or None)
                
                update_fields.append('real_name = %s')
                params.append(real_name or None)
                
                update_fields.append('phone = %s')
                params.append(phone or None)
                
                if role_id is not None:
                    update_fields.append('role_id = %s')
                    params.append(role_id)
                
                if status is not None:
                    update_fields.append('status = %s')
                    params.append(status)
                
                if password:
                    encrypted_password = encrypt_pwd_with_fixed_salt(password)
                    update_fields.append('password = %s')
                    params.append(encrypted_password)
                
                params.append(user_id)
                
                # 执行更新
                cursor.execute(f'''
                    UPDATE user SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', params)
                
                return JsonResponse(ResponseCode.SUCCESS.to_dict(message="用户更新成功"), status=200)
    
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=f"更新失败: {str(e)}"), status=200)


@require_http_methods(["DELETE"])
@csrf_exempt
def delete_user(request, user_id):
    """ 删除用户 - 需要管理员权限 """
    # 权限检查
    token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
    if not token:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="未授权访问"), status=401)
    
    try:
        user_info = parse_jwt_token(token)
        if not user_info or not check_permission(user_info.get('role_id'), 'user_manage'):
            return JsonResponse(ResponseCode.ERROR.to_dict(message="权限不足"), status=403)
    except:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="token无效"), status=401)
    
    try:
        with connection.cursor() as cursor:
            # 检查用户是否存在
            cursor.execute('SELECT id, role_id FROM user WHERE id = %s', [user_id])
            user = cursor.fetchone()
            if not user:
                return JsonResponse(ResponseCode.ERROR.to_dict(message="用户不存在"), status=200)
            
            # 不能删除管理员账户
            if user[1] == 1:  # role_id = 1 是管理员
                return JsonResponse(ResponseCode.ERROR.to_dict(message="不能删除管理员账户"), status=200)
            
            # 不能删除自己
            if int(user_id) == user_info.get('user_id'):
                return JsonResponse(ResponseCode.ERROR.to_dict(message="不能删除自己的账户"), status=200)
            
            # 删除用户
            cursor.execute('DELETE FROM user WHERE id = %s', [user_id])
            
            return JsonResponse(ResponseCode.SUCCESS.to_dict(message="用户删除成功"), status=200)
    
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=f"删除失败: {str(e)}"), status=200)


@require_http_methods(["GET"])
@csrf_exempt
def get_roles(request):
    """ 获取角色列表 """
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT id, name, description, permissions, status
            FROM role
            WHERE status = 1
            ORDER BY id
        ''')
        
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        roles = []
        for row in rows:
            role_dict = dict(zip(columns, row))
            if role_dict['permissions']:
                role_dict['permissions'] = json.loads(role_dict['permissions'])
            roles.append(role_dict)
        
        return JsonResponse(
            ResponseCode.SUCCESS.to_dict(data={'roles': roles}),
            status=200
        )


@require_http_methods(["GET"])
@csrf_exempt
def get_profile(request):
    """ 获取个人信息 """
    # 权限检查
    token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
    if not token:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="未授权访问"), status=401)
    
    try:
        user_info = parse_jwt_token(token)
        if not user_info:
            return JsonResponse(ResponseCode.ERROR.to_dict(message="token无效"), status=401)
    except:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="token无效"), status=401)
    
    user_id = user_info.get('user_id')
    
    try:
        with connection.cursor() as cursor:
            cursor.execute('''
                SELECT u.id, u.username, u.email, u.real_name, u.phone, u.role_id, u.status,
                       u.last_login_at, u.created_at, u.updated_at,
                       r.name as role_name, r.description as role_desc
                FROM user u
                JOIN role r ON u.role_id = r.id
                WHERE u.id = %s
            ''', [user_id])
            
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            
            if not row:
                return JsonResponse(ResponseCode.ERROR.to_dict(message="用户不存在"), status=404)
            
            user_dict = dict(zip(columns, row))
            # 格式化时间
            if user_dict['last_login_at']:
                user_dict['last_login_at'] = user_dict['last_login_at'].strftime('%Y-%m-%d %H:%M:%S')
            if user_dict['created_at']:
                user_dict['created_at'] = user_dict['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if user_dict['updated_at']:
                user_dict['updated_at'] = user_dict['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            
            # 移除敏感信息
            user_dict.pop('password', None)
            
            return JsonResponse(
                ResponseCode.SUCCESS.to_dict(data=user_dict),
                status=200
            )
    
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=f"获取个人信息失败: {str(e)}"), status=200)


@require_http_methods(["PUT"])
@csrf_exempt
def update_profile(request):
    """ 更新个人信息 """
    # 权限检查
    token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
    if not token:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="未授权访问"), status=401)
    
    try:
        user_info = parse_jwt_token(token)
        if not user_info:
            return JsonResponse(ResponseCode.ERROR.to_dict(message="token无效"), status=401)
    except:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="token无效"), status=401)
    
    user_id = user_info.get('user_id')
    
    request_data = json.loads(request.body.decode('utf-8'))
    username = request_data.get('username', '').strip()
    email = request_data.get('email', '').strip()
    real_name = request_data.get('real_name', '').strip()
    phone = request_data.get('phone', '').strip()
    old_password = request_data.get('old_password', '')
    new_password = request_data.get('new_password', '')
    
    # 参数验证
    if not username or len(username) < 3:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="用户名不能为空且长度不能少于3位"), status=200)
    
    if email and not validate_email(email):
        return JsonResponse(ResponseCode.ERROR.to_dict(message="邮箱格式不正确"), status=200)
    
    if not validate_phone(phone):
        return JsonResponse(ResponseCode.ERROR.to_dict(message="手机号格式不正确"), status=200)
    
    if new_password and len(new_password) < 6:
        return JsonResponse(ResponseCode.ERROR.to_dict(message="新密码长度不能少于6位"), status=200)
    
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                # 获取当前用户信息
                cursor.execute('SELECT username, password FROM user WHERE id = %s', [user_id])
                current_user = cursor.fetchone()
                if not current_user:
                    return JsonResponse(ResponseCode.ERROR.to_dict(message="用户不存在"), status=200)
                
                old_username = current_user[0]
                current_password = current_user[1]
                
                # 如果要修改密码，需要验证旧密码
                if new_password:
                    if not old_password:
                        return JsonResponse(ResponseCode.ERROR.to_dict(message="修改密码需要提供当前密码"), status=200)
                    
                    if not decrypt_pwd_with_fixed_salt(old_password, current_password):
                        return JsonResponse(ResponseCode.ERROR.to_dict(message="当前密码不正确"), status=200)
                
                # 检查用户名是否被其他用户使用
                cursor.execute('SELECT id FROM user WHERE username = %s AND id != %s', [username, user_id])
                if cursor.fetchone():
                    return JsonResponse(ResponseCode.ERROR.to_dict(message="用户名已存在"), status=200)
                
                # 检查邮箱是否被其他用户使用
                if email:
                    cursor.execute('SELECT id FROM user WHERE email = %s AND id != %s', [email, user_id])
                    if cursor.fetchone():
                        return JsonResponse(ResponseCode.ERROR.to_dict(message="邮箱已被注册"), status=200)
                
                # 构建更新SQL
                update_fields = []
                params = []
                
                update_fields.append('username = %s')
                params.append(username)
                
                update_fields.append('email = %s')
                params.append(email or None)
                
                update_fields.append('real_name = %s')
                params.append(real_name or None)
                
                update_fields.append('phone = %s')
                params.append(phone or None)
                
                if new_password:
                    encrypted_password = encrypt_pwd_with_fixed_salt(new_password)
                    update_fields.append('password = %s')
                    params.append(encrypted_password)
                
                params.append(user_id)
                
                # 执行更新
                cursor.execute(f'''
                    UPDATE user SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', params)
                
                # 如果用户名发生了变化，需要同步更新其他表中的用户名
                if username != old_username:
                    # 更新嵌入模型表
                    cursor.execute('UPDATE embedding_model SET username = %s WHERE user_id = %s', [username, user_id])
                    
                    # 更新大模型服务商表
                    cursor.execute('UPDATE llmprovider SET username = %s WHERE user_id = %s', [username, user_id])
                    
                    # 更新大模型配置表
                    cursor.execute('UPDATE llmmodel SET username = %s WHERE user_id = %s', [username, user_id])
                    
                    # 更新知识库表
                    cursor.execute('UPDATE knowledge_database SET username = %s WHERE user_id = %s', [username, user_id])
                    
                    # 更新知识库文档表
                    cursor.execute('UPDATE knowledge_document SET username = %s WHERE user_id = %s', [username, user_id])
                    
                    # 更新聊天对话表
                    cursor.execute('UPDATE chat_conversation SET username = %s WHERE user_id = %s', [username, user_id])
                
                return JsonResponse(ResponseCode.SUCCESS.to_dict(message="个人信息更新成功"), status=200)
    
    except Exception as e:
        return JsonResponse(ResponseCode.ERROR.to_dict(message=f"更新失败: {str(e)}"), status=200)
