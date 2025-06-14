import jwt
from open_ragbook_server import settings
from datetime import datetime


def generate_jwt_token(user):
    """ 生成jwt_token """
    payload = {
        'user_id': user.get('user_id'),
        'user_name': user.get('user_name'),
        'role_id': user.get('role_id'),
        'role_name': user.get('role_name'),
        'role_desc': user.get('role_desc'),
        'exp': datetime.utcnow() + settings.JWT_CONF.get("ACCESS_TOKEN_LIFETIME"),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def parse_jwt_token(token):
    """ 解密jwt_token """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except Exception:
        return None


def validate_jwt_token(token):
    """ 验证jwt_token """
    payload = parse_jwt_token(token)
    if payload is None:
        raise Exception("无效的令牌")
    return payload
