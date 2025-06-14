import re
import json
from types import SimpleNamespace
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse

from account_mgt.utils.jwt_token_utils import validate_jwt_token
from open_ragbook_server.utils.response_code import ResponseCode

class JWTAuthMiddleware(MiddlewareMixin):
    """JWT认证中间件"""

    # 不需要JWT认证的URL路径列表（使用正则表达式）
    EXEMPT_URLS = [
        r'^admin/',  # Django管理界面
        r'^api/v1/account/login$',  # 登录接口
        r'^api/v1/account/register$',  # 注册接口
        # 可以添加更多免认证的路径
    ]

    def process_view(self, request, view_func, view_args, view_kwargs):
        # 检查请求路径是否在豁免列表中
        path = request.path_info.lstrip('/')
        for exempt_url in self.EXEMPT_URLS:
            if re.match(exempt_url, path):
                return None  # 允许请求继续处理

        # 检查JWT认证头
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            response_data = ResponseCode.UNAUTHORIZED.to_dict(message="未授权，请先登录")
            return HttpResponse(
                json.dumps(response_data),
                content_type='application/json',
                status=401
            )

        # 验证JWT令牌
        token = auth_header.split(' ')[1]
        try:
            payload = validate_jwt_token(token)
            user = SimpleNamespace(
                id=payload.get('user_id'),
                username=payload.get('user_name'),
                role_id=payload.get('role_id'),
                role_name=payload.get('role_name'),
                is_authenticated=True,
                is_active=True
            )
            # 将用户信息附加到请求对象中，供视图函数使用
            request.user = user
        except Exception as e:
            response_data = ResponseCode.UNAUTHORIZED.to_dict(message="授权已过期，请重新登录")
            return HttpResponse(
                json.dumps(response_data),
                content_type='application/json',
                status=401
            )

        # 允许请求继续处理
        return None