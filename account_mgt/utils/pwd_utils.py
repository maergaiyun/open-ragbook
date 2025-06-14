import bcrypt
from open_ragbook_server.settings import SECRET_KEY


def encrypt_pwd_with_fixed_salt(pwd):
    """ 密码加密 """

    # 使用固定的盐值哈希密码
    _password = bcrypt.hashpw((pwd + SECRET_KEY).encode('utf-8'), bcrypt.gensalt())

    return _password.decode()


def decrypt_pwd_with_fixed_salt(new_pwd, old_pwd):
    """ 密码解密 """
    return bcrypt.checkpw((new_pwd + SECRET_KEY).encode('utf-8'), old_pwd.encode())


if __name__ == '__main__':
    # print(encrypt_pwd_with_fixed_salt("admin"))
    print(decrypt_pwd_with_fixed_salt("admin", "$2b$12$ZAfqXbGX0lLf6Xkvb92PiOzQqhfMfwcOreX24Z1BzujvsifRsWwFO"))
