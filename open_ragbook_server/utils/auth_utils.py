"""
认证和权限工具模块
提供JWT验证装饰器和权限检查函数，减少重复代码
"""
import json
import logging
from functools import wraps
from django.http import JsonResponse
from account_mgt.utils.jwt_token_utils import parse_jwt_token
from open_ragbook_server.utils.response_code import ResponseCode

logger = logging.getLogger(__name__)


def jwt_required(admin_only=False):
    """
    JWT认证装饰器
    
    Args:
        admin_only (bool): 是否只允许管理员访问，默认False
    
    Returns:
        装饰器函数
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 提取JWT token
            token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
            if not token:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="未授权访问"),
                    status=401
                )
            
            # 验证token
            user_info = parse_jwt_token(token)
            if not user_info:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="token无效"),
                    status=401
                )
            
            # 检查管理员权限
            if admin_only and user_info.get('role_id') != 1:
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="需要管理员权限"),
                    status=403
                )
            
            # 将用户信息添加到request对象中
            request.user_info = user_info
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def get_user_from_request(request):
    """
    从request中获取用户信息
    
    Args:
        request: Django request对象
    
    Returns:
        dict: 用户信息字典，包含user_id, user_name, role_id等
    """
    return getattr(request, 'user_info', None)


def check_resource_permission(request, resource_user_id):
    """
    检查用户是否有权限操作指定资源
    管理员可以操作所有资源，普通用户只能操作自己的资源
    
    Args:
        request: Django request对象
        resource_user_id: 资源所属的用户ID
    
    Returns:
        bool: 是否有权限
    """
    user_info = get_user_from_request(request)
    if not user_info:
        return False
    
    user_id = user_info.get('user_id')
    role_id = user_info.get('role_id')
    
    # 管理员可以操作所有资源
    if role_id == 1:
        return True
    
    # 普通用户只能操作自己的资源
    return user_id == resource_user_id


def get_user_filter_condition(request):
    """
    根据用户角色获取数据过滤条件
    管理员返回空条件（查看所有），普通用户返回user_id过滤条件
    
    Args:
        request: Django request对象
    
    Returns:
        tuple: (where_clause, params) SQL WHERE子句和参数
    """
    user_info = get_user_from_request(request)
    if not user_info:
        return "", []
    
    role_id = user_info.get('role_id')
    user_id = user_info.get('user_id')
    
    if role_id == 1:  # 管理员
        return "", []
    else:  # 普通用户
        return "WHERE user_id = %s", [user_id]


def parse_json_body(request):
    """
    解析请求体中的JSON数据
    
    Args:
        request: Django request对象
    
    Returns:
        dict: 解析后的JSON数据
    
    Raises:
        ValueError: JSON解析失败
    """
    try:
        return json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"JSON解析失败: {str(e)}")


def validate_required_fields(data, required_fields):
    """
    验证必填字段
    
    Args:
        data (dict): 要验证的数据
        required_fields (list): 必填字段列表
    
    Returns:
        tuple: (is_valid, missing_fields)
    """
    missing_fields = []
    for field in required_fields:
        if not data.get(field):
            missing_fields.append(field)
    
    return len(missing_fields) == 0, missing_fields


def create_error_response(message, status=400):
    """
    创建错误响应
    
    Args:
        message (str): 错误消息
        status (int): HTTP状态码
    
    Returns:
        JsonResponse: 错误响应
    """
    return JsonResponse(
        ResponseCode.ERROR.to_dict(message=message),
        status=status
    )


def create_success_response(data=None, status=200):
    """
    创建成功响应
    
    Args:
        data: 响应数据
        status (int): HTTP状态码
    
    Returns:
        JsonResponse: 成功响应
    """
    return JsonResponse(
        ResponseCode.SUCCESS.to_dict(data=data),
        status=status
    ) 