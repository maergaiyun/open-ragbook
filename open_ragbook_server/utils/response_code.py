from enum import Enum


class ResponseCode(Enum):
    SUCCESS = (200, "Success")
    WARNING = (300, "Warning")
    ERROR = (500, "Error")
    NOT_FOUND = (404, "Not Found")
    FORBIDDEN = (403, "Forbidden")
    BAD_REQUEST = (400, "Bad Request")
    UNAUTHORIZED = (401, "Not Authorized")

    def __init__(self, code, message):
        self._code = code
        self._message = message

    @property
    def code(self):
        return self._code

    @property
    def message(self):
        return self._message

    def to_dict(self, data=None, message=None):
        """
        将枚举状态转换为统一格式的字典响应格式，支持自定义消息.

        :param data: 附加的响应数据，可以为空
        :param message: 自定义的响应消息，如果为空则使用默认消息
        :return: 字典格式的响应对象，包含 code, message, data
        """
        return {
            "code": self.code,
            "message": message or self.message,
            "data": data or {}
        }
