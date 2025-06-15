import os
import logging
import time
import queue
import threading

import pymysql
from dotenv import load_dotenv
from django.db import connection

from open_ragbook_server.utils.common_utils import rows_datetime_format

logger = logging.getLogger('myapp')

# 使用单例模式来管理连接池
_mysql_pool = None


class MySQLConnectionPool:
    def __init__(self, host, port, user, password, db, min_connections=2, max_connections=10, timeout=30):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.timeout = timeout
        self.pool = queue.Queue(maxsize=max_connections)
        self.lock = threading.Lock()

        # 初始化连接池
        self._initialize_pool()

    def _initialize_pool(self):
        """初始化数据库连接池，创建最小连接数的数据库连接"""
        for _ in range(self.min_connections):
            conn = self._create_connection()
            self.pool.put(conn)

    def _create_connection(self):
        """创建一个数据库连接"""
        try:
            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.db
            )
            return conn
        except Exception as e:
            return None

    def get_connection(self):
        """从连接池中获取一个连接"""
        try:
            conn = self.pool.get(timeout=self.timeout)
            if not conn.open:
                # 如果连接失效，重新创建一个新的连接
                conn = self._create_connection()
            return conn
        except queue.Empty:
            return None

    def release_connection(self, conn):
        """将连接放回连接池"""
        if conn:
            self.pool.put(conn)

    def close_all_connections(self):
        """关闭连接池中的所有连接"""
        with self.lock:
            while not self.pool.empty():
                conn = self.pool.get()
                if conn:
                    conn.close()


def get_mysql_pool():
    """获取数据库连接池（单例）"""
    global _mysql_pool
    if _mysql_pool is None:
        load_dotenv()

        host = os.getenv('MYSQL_HOST')
        port = int(os.getenv('MYSQL_PORT', 3306))  # 默认 3306
        user = os.getenv('MYSQL_USER')
        password = os.getenv('MYSQL_PASSWORD')
        db = os.getenv('MYSQL_DB')
        min_connections = int(os.getenv('MYSQL_MIN_CONNECTIONS', 10))
        max_connections = int(os.getenv('MYSQL_MAX_CONNECTIONS', 10))
        _mysql_pool = MySQLConnectionPool(
            host=host,
            port=port,
            user=user,
            password=password,
            db=db,
            min_connections=min_connections,
            max_connections=max_connections
        )

    return _mysql_pool


def dict_fetchall(cursor):
    """ 将游标的查询结果转换为字典格式 """
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_max_id(table_name, field_name):
    """
    使用原生SQL获取指定表中的最大ID值。

    :param table_name: 表名（字符串）
    :param field_name: 字段名
    :return: 最大ID值，如果表为空则返回0
    """
    try:
        with connection.cursor() as cursor:
            # 编写SQL语句，使用MAX函数获取某个字段最大值
            sql = f"SELECT MAX({field_name}) FROM {table_name}"
            cursor.execute(sql)
            result = cursor.fetchone()[0]
            return 0 if not result else result
    except Exception as e:
        logger.error(e, exc_info=True)
        return 0


def execute_query_sql(sql, is_format=True):
    """
    执行传入的SQL语句，并返回查询结果。

    :param sql: 要执行的SQL语句（字符串）
    :param is_format: 是否格式化返回
    :return: 查询结果集，如果出现数据库操作错误则返回None。
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            if is_format:
                result = dict_fetchall(cursor)  # 将结果转换为字典列表形式
            else:
                result = cursor.fetchall()
            return result
    except Exception as e:
        logger.error(e, exc_info=True)
        return []


def execute_sql(sql):
    """
    执行传入的SQL语句，仅返回执行是否成功。

    :param sql: 要执行的SQL语句（字符串）
    :return: 布尔值，True 表示执行成功，False 表示执行失败。
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            connection.commit()  # 提交事务，确保数据变更生效
            return True
    except Exception as e:
        logger.error(e, exc_info=True)
        return False


def fetch_paginated_data(table_name, conditions=None, order_by=None, page=1, page_size=20):
    """
    通用分页查询函数，支持条件查询和分页。

    :param table_name: 表名（字符串）
    :param conditions: 查询条件（字典类型，key 为列名，value 为列值）
    :param order_by: 排序字段
    :param page: 页码（默认为 1）
    :param page_size: 每页记录数（默认为 20）
    :return: (total_records, rows) 总记录数和当前页的数据
    """
    # 初始条件: 1=1 保证 SQL 语法正确
    where_conditions = ["1=1"]
    params = []

    # 动态拼接条件
    if conditions:
        for key, value in conditions.items():
            if isinstance(value, str):
                where_conditions.append(f"{key} LIKE %s")
                params.append(f"%{value}%")
            else:
                where_conditions.append(f"{key} = %s")
                params.append(value)

    # 拼接最终的 WHERE 子句
    where_str = "WHERE " + " AND ".join(where_conditions)

    # 计算分页偏移量
    offset = (page - 1) * page_size
    limit = page_size

    with connection.cursor() as cursor:
        # 查询总记录数
        count_query = f"SELECT COUNT(*) FROM {table_name} {where_str}"
        cursor.execute(count_query, params)
        total_records = cursor.fetchone()[0]

        # 查询当前页的数据
        if order_by:
            order_by = " order by " + order_by
            select_query = f"SELECT * FROM {table_name} {where_str} {order_by} LIMIT %s OFFSET %s"
        else:
            select_query = f"SELECT * FROM {table_name} {where_str} LIMIT %s OFFSET %s"

        params.extend([limit, offset])  # 添加分页参数
        cursor.execute(select_query, params)
        rows = dict_fetchall(cursor)
        rows = rows_datetime_format(rows)
        return total_records, rows


def batch_insert_data(table_name, field_names, data_list):
    """
    通用批量插入数据函数，支持向指定表中批量插入多条数据。

    :param table_name: 表名（字符串）
    :param field_names: 字段名列表（例如：['name', 'age', 'gender']）
    :param data_list: 要插入的数据列表，每条数据是对应字段的值组成的列表，例如：
                      [['张三', 20, '男'], ['李四', 22, '女']]
    :return: 插入成功的行数
    """
    if not field_names or not data_list:
        return 0

    # 拼接字段名部分，用逗号分隔
    fields_str = ", ".join(field_names)

    # 占位符部分，根据要插入的字段数量生成对应数量的占位符，如 (%s, %s, %s)
    placeholders = ", ".join(["%s"] * len(field_names))
    # 构造完整的插入语句
    insert_sql = f"INSERT INTO {table_name} ({fields_str}) VALUES ({placeholders})"

    with connection.cursor() as cursor:
        # 批量执行插入操作
        cursor.executemany(insert_sql, data_list)
        return cursor.rowcount


def update_data(table_name, data, where_conditions):
    """
    批量更新指定表中的数据。

    :param table_name: 要更新数据的表名（字符串）
    :param data: 包含更新数据的字典，键为字段名，值为对应字段要更新的值，格式如{"字段名": "字段值"}
    :param where_conditions: 用于指定更新的条件，格式为字典类型，键为列名，值为列值，如{"id": 1}，表示更新满足此条件的记录
    :return: 如果更新成功返回True，出现错误返回False。
    """

    try:
        with connection.cursor() as cursor:
            set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
            where_str = ""
            where_params = []
            if where_conditions:
                where_conditions_list = []
                for key, value in where_conditions.items():
                    where_conditions_list.append(f"{key} = %s")
                    where_params.append(value)
                where_str = "WHERE " + " AND ".join(where_conditions_list)
            update_sql = f"UPDATE {table_name} SET {set_clause} {where_str}"
            values = list(data.values()) + where_params
            cursor.execute(update_sql, values)
            connection.commit()
            return True
    except Exception as e:
        logger.error(e, exc_info=True)
    return False


def insert_or_update_data(table_name, data, where_conditions):
    """
    插入或更新指定表中的数据。

    :param table_name: 表名（字符串）
    :param data: 包含插入或更新数据的字典，键为字段名，值为对应字段的值，格式如{"字段名": "字段值"}
    :param where_conditions: 用于指定判断记录是否存在的条件，格式为字典类型，键为列名，值为列值，
                              如{"id": 1}，表示查询满足此条件的记录。
    :return: 如果操作成功返回True，出现错误返回False。
    """
    try:
        with connection.cursor() as cursor:
            # 构造条件查询语句
            where_str = ""
            where_params = []
            if where_conditions:
                where_conditions_list = []
                for key, value in where_conditions.items():
                    where_conditions_list.append(f"{key} = %s")
                    where_params.append(value)
                where_str = "WHERE " + " AND ".join(where_conditions_list)

            # 检查记录是否存在
            check_sql = f"SELECT COUNT(*) FROM {table_name} {where_str}"
            cursor.execute(check_sql, where_params)
            count = cursor.fetchone()[0]

            if count > 0:
                # 构造更新语句
                set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
                update_sql = f"UPDATE {table_name} SET {set_clause} {where_str}"
                update_values = list(data.values()) + where_params
                cursor.execute(update_sql, update_values)
            else:
                # 构造插入语句
                columns = ", ".join(data.keys())
                placeholders = ", ".join(["%s"] * len(data))
                insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                cursor.execute(insert_sql, list(data.values()))

            connection.commit()
            return True
    except Exception as e:
        logger.error(e, exc_info=True)
    return False


def insert_data(table_name, columns, values, is_pk=False):
    """
    通用的插入数据函数

    :param table_name: 表名 (字符串)
    :param columns: 字段名列表 (列表)
    :param values: 字段值列表 (列表)
    :param is_pk: 是否返回主键id标记
    :return: 插入结果（成功或异常信息）
    """
    result = {"message": "", "data": {}, "code": 200}
    try:
        if len(columns) != len(values):
            raise ValueError("字段名和字段值数量不匹配！")

        # 构建动态 SQL 语句
        column_str = ", ".join(columns)  # 将字段名用逗号拼接
        placeholder_str = ", ".join(["%s"] * len(values))  # 构建占位符 (%s, %s, ...)
        sql = f"INSERT INTO {table_name} ({column_str}) VALUES ({placeholder_str})"
        # 执行 SQL
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            logger.info(sql)
            if is_pk:
                cursor.execute("SELECT LAST_INSERT_ID()")
                last_insert_id = cursor.fetchone()[0]
                result.update({
                    "data": {"pk_id": last_insert_id}
                })
        return result
    except Exception as e:
        logging.error(e, exc_info=True)
        result.update({
            "message": str(e),
            "code": 500
        })
        return result


def execute_query_with_params(sql, params=None):
    """
    执行带参数的查询SQL，返回字典格式结果
    
    :param sql: SQL语句
    :param params: 参数列表
    :return: 查询结果列表
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or [])
            return dict_fetchall(cursor)
    except Exception as e:
        logger.error(f"执行查询失败: {sql}, 参数: {params}, 错误: {e}", exc_info=True)
        return []


def execute_update_with_params(sql, params=None):
    """
    执行带参数的更新SQL（INSERT/UPDATE/DELETE）
    
    :param sql: SQL语句
    :param params: 参数列表
    :return: 影响的行数，失败返回-1
    """
    try:
        with connection.cursor() as cursor:
            affected_rows = cursor.execute(sql, params or [])
            return affected_rows
    except Exception as e:
        logger.error(f"执行更新失败: {sql}, 参数: {params}, 错误: {e}", exc_info=True)
        return -1


def check_record_exists(table_name, conditions):
    """
    检查记录是否存在
    
    :param table_name: 表名
    :param conditions: 条件字典 {column: value}
    :return: bool
    """
    where_clauses = []
    params = []
    
    for column, value in conditions.items():
        where_clauses.append(f"{column} = %s")
        params.append(value)
    
    sql = f"SELECT 1 FROM {table_name} WHERE {' AND '.join(where_clauses)} LIMIT 1"
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"检查记录存在性失败: {sql}, 参数: {params}, 错误: {e}", exc_info=True)
        return False


def get_record_by_id(table_name, record_id, id_column='id'):
    """
    根据ID获取单条记录
    
    :param table_name: 表名
    :param record_id: 记录ID
    :param id_column: ID列名，默认为'id'
    :return: 记录字典或None
    """
    sql = f"SELECT * FROM {table_name} WHERE {id_column} = %s"
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, [record_id])
            result = cursor.fetchone()
            if result:
                columns = [col[0] for col in cursor.description]
                return dict(zip(columns, result))
            return None
    except Exception as e:
        logger.error(f"根据ID获取记录失败: {sql}, ID: {record_id}, 错误: {e}", exc_info=True)
        return None


def get_last_insert_id():
    """
    获取最后插入的ID
    
    :return: 最后插入的ID
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT LAST_INSERT_ID()")
            return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"获取最后插入ID失败: {e}", exc_info=True)
        return None
