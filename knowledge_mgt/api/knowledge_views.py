import json
import logging
from datetime import datetime

from account_mgt.utils.jwt_token_utils import *
from account_mgt.utils.pwd_utils import *
from open_ragbook_server.utils.response_code import *
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

# 获取模块日志记录器
logger = logging.getLogger('knowledge_mgt')


@require_http_methods(["GET"])
@csrf_exempt
def knowledge_database_list(request):
    """获取知识库列表 - 只显示当前用户的知识库"""
    logger.info("查询知识库列表")

    # JWT token验证
    token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
    if not token:
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message="未授权访问"),
            status=401
        )

    try:
        user_info = parse_jwt_token(token)
        if not user_info:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="token无效"),
                status=401
            )

        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')

        with connection.cursor() as cursor:
            # 管理员可以看到所有知识库，普通用户只能看到自己的
            if role_id == 1:  # 管理员
                cursor.execute('''
                    SELECT 
                        id, 
                        name, 
                        description as `desc`, 
                        embedding_model_id,
                        vector_dimension, 
                        index_type, 
                        doc_count, 
                        username, 
                        create_time, 
                        update_time
                    FROM knowledge_database
                    ORDER BY create_time DESC
                ''')
            else:
                # 普通用户
                cursor.execute('''
                    SELECT 
                        id, 
                        name, 
                        description as `desc`, 
                        embedding_model_id,
                        vector_dimension, 
                        index_type, 
                        doc_count, 
                        username, 
                        create_time, 
                        update_time
                    FROM knowledge_database
                    WHERE user_id = %s
                    ORDER BY create_time DESC
                ''', [user_id])

            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            print(rows)
            data = []
            for row in rows:
                data.append(dict(zip(columns, row)))

            logger.info(f"查询到 {len(data)} 条知识库记录")
            return JsonResponse(
                ResponseCode.SUCCESS.to_dict(data={
                    "data": data,
                    "total_records": len(data)
                }),
                status=200
            )
    except Exception as e:
        logger.error(f"查询知识库列表出错: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=str(e)),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
def create_knowledge_database(request):
    """创建知识库"""
    logger.info("创建知识库请求")

    # JWT token验证
    token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
    if not token:
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message="未授权访问"),
            status=401
        )

    try:
        user_info = parse_jwt_token(token)
        if not user_info:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="token无效"),
                status=401
            )

        user_id = user_info.get('user_id')
        username = user_info.get('user_name')

        request_data = json.loads(request.body.decode('utf-8'))
        name = request_data.get('name')
        description = request_data.get('description', '')
        embedding_model_id = request_data.get('embedding_model_id')
        vector_dimension = request_data.get('vector_dimension', 384)
        index_type = request_data.get('index_type')

        logger.debug(f"=== 创建知识库后端调试信息 ===")
        logger.debug(f"接收到的原始数据: {request_data}")
        logger.debug(f"解析后的参数:")
        logger.debug(f"  name: {name} (类型: {type(name)})")
        logger.debug(f"  description: {description} (类型: {type(description)})")
        logger.debug(f"  embedding_model_id: {embedding_model_id} (类型: {type(embedding_model_id)})")
        logger.debug(f"  vector_dimension: {vector_dimension} (类型: {type(vector_dimension)})")
        logger.debug(f"  index_type: {index_type} (类型: {type(index_type)})")
        logger.debug(f"  user_id: {user_id}, username: {username}")
        logger.debug(f"==============================")

        if not user_id or not username:
            logger.warning(f"无法获取用户信息: user_id={user_id}, username={username}")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="无法获取用户信息"),
                status=401
            )

        # 检查必填字段
        if not name or not index_type or not embedding_model_id:
            logger.warning(f"创建知识库失败: 必填字段缺失 - name={name}, embedding_model_id={embedding_model_id}, index_type={index_type}")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="名称、嵌入模型和索引类型为必填项"),
                status=400
            )

        # 检查知识库名称是否已存在（同一用户下不能重名）
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM knowledge_database WHERE name = %s AND user_id = %s", [name, user_id])
            if cursor.fetchone():
                logger.warning(f"创建知识库失败: 用户{username}的名称'{name}'已存在")
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message="知识库名称已存在"),
                    status=400
                )

            # 创建知识库 - 使用数据库的默认时间戳
            logger.debug(f"准备执行SQL插入，参数: name={name}, description={description}, embedding_model_id={embedding_model_id}, vector_dimension={vector_dimension}, index_type={index_type}, user_id={user_id}, username={username}")
            
            cursor.execute('''
                INSERT INTO knowledge_database 
                (name, description, embedding_model_id, vector_dimension, index_type, doc_count, user_id, username)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', [name, description, embedding_model_id, vector_dimension, index_type, 0, user_id, username])

            # 获取新创建的知识库ID
            cursor.execute("SELECT LAST_INSERT_ID()")
            new_id = cursor.fetchone()[0]
            
            # 验证插入结果
            cursor.execute("SELECT * FROM knowledge_database WHERE id = %s", [new_id])
            inserted_row = cursor.fetchone()
            logger.debug(f"插入后的数据: {inserted_row}")

            logger.info(f"成功创建知识库: ID={new_id}, 名称={name}, embedding_model_id={embedding_model_id}")
            return JsonResponse(
                ResponseCode.SUCCESS.to_dict(data={"id": new_id}),
                status=201
            )
    except Exception as e:
        logger.error(f"创建知识库异常: {str(e)}", exc_info=True)
        print("创建知识库异常:", str(e))
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=str(e)),
            status=500
        )


@csrf_exempt
def update_knowledge_database(request, db_id):
    """更新或删除知识库"""
    # JWT token验证
    token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
    if not token:
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message="未授权访问"),
            status=401
        )

    try:
        user_info = parse_jwt_token(token)
        if not user_info:
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="token无效"),
                status=401
            )

        user_id = user_info.get('user_id')
        role_id = user_info.get('role_id')

        if request.method == 'PUT':
            logger.info(f"更新知识库请求: ID={db_id}")
            try:
                request_data = json.loads(request.body.decode('utf-8'))
                name = request_data.get('name')
                description = request_data.get('description')

                # 检查必填字段
                if not name or not description:
                    logger.warning(f"更新知识库失败: ID={db_id}, 名称或描述为空")
                    return JsonResponse(
                        ResponseCode.ERROR.to_dict(message="名称和描述为必填项"),
                        status=400
                    )

                with connection.cursor() as cursor:
                    # 检查知识库是否存在且用户有权限操作
                    if role_id == 1:  # 管理员可以操作所有知识库
                        cursor.execute("SELECT id, user_id FROM knowledge_database WHERE id = %s", [db_id])
                    else:  # 普通用户只能操作自己的知识库
                        cursor.execute("SELECT id, user_id FROM knowledge_database WHERE id = %s AND user_id = %s", [db_id, user_id])

                    result = cursor.fetchone()
                    if not result:
                        logger.warning(f"更新知识库失败: ID={db_id} 不存在或无权限")
                        return JsonResponse(
                            ResponseCode.ERROR.to_dict(message="知识库不存在或无权限操作"),
                            status=404
                        )

                    # 检查名称是否与其他知识库冲突（同一用户下）
                    db_user_id = result[1]
                    cursor.execute("SELECT id FROM knowledge_database WHERE name = %s AND id != %s AND user_id = %s", 
                                 [name, db_id, db_user_id])
                    if cursor.fetchone():
                        logger.warning(f"更新知识库失败: ID={db_id}, 名称'{name}'已存在")
                        return JsonResponse(
                            ResponseCode.ERROR.to_dict(message="知识库名称已存在"),
                            status=400
                        )

                    # 更新知识库 - update_time会自动更新
                    cursor.execute('''
                        UPDATE knowledge_database 
                        SET name = %s, description = %s
                        WHERE id = %s
                    ''', [name, description, db_id])

                    logger.info(f"成功更新知识库: ID={db_id}, 名称={name}")
                    return JsonResponse(
                        ResponseCode.SUCCESS.to_dict(),
                        status=200
                    )
            except Exception as e:
                logger.error(f"更新知识库异常: ID={db_id}, 错误={str(e)}", exc_info=True)
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message=str(e)),
                    status=500
                )

        elif request.method == 'DELETE':
            """删除知识库"""
            logger.info(f"删除知识库请求: ID={db_id}")
            try:
                with connection.cursor() as cursor:
                    # 检查知识库是否存在且用户有权限操作
                    if role_id == 1:  # 管理员可以操作所有知识库
                        cursor.execute("SELECT id FROM knowledge_database WHERE id = %s", [db_id])
                    else:  # 普通用户只能操作自己的知识库
                        cursor.execute("SELECT id FROM knowledge_database WHERE id = %s AND user_id = %s", [db_id, user_id])

                    if not cursor.fetchone():
                        logger.warning(f"删除知识库失败: ID={db_id} 不存在或无权限")
                        return JsonResponse(
                            ResponseCode.ERROR.to_dict(message="知识库不存在或无权限操作"),
                            status=404
                        )

                    # 删除知识库
                    cursor.execute("DELETE FROM knowledge_database WHERE id = %s", [db_id])

                    logger.info(f"成功删除知识库: ID={db_id}")
                    return JsonResponse(
                        ResponseCode.SUCCESS.to_dict(),
                        status=200
                    )
            except Exception as e:
                logger.error(f"删除知识库异常: ID={db_id}, 错误={str(e)}", exc_info=True)
                return JsonResponse(
                    ResponseCode.ERROR.to_dict(message=str(e)),
                    status=500
                )
        else:
            logger.warning(f"不支持的请求方法: {request.method}")
            return JsonResponse(
                ResponseCode.ERROR.to_dict(message="不支持的请求方法"),
                status=405
            )
    except Exception as e:
        logger.error(f"处理知识库请求异常: {str(e)}", exc_info=True)
        return JsonResponse(
            ResponseCode.ERROR.to_dict(message=str(e)),
            status=500
        )
