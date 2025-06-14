import os

from dotenv import load_dotenv

load_dotenv()

# 文件资料库目录
FILE_DB_PATH = os.getenv('FILE_DB_PATH', '/volume1/HZWJ')
EMPLOYEE_FILE_DB_PATH = os.path.join(FILE_DB_PATH, "员工资料库")
