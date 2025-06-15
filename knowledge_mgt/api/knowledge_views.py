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

# 获取模块日志记录器
logger = logging.getLogger('knowledge_mgt')


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def knowledge_database_list(request):
    """获取知识库列表 - 只显示当前用户的知识库"""
    logger.info("查询知识库列表")
    
    try:
        # 获取用户过滤条件
        where_clause, params = get_user_filter_condition(request)
        
        # 构建SQL
        sql = f"""
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
            {where_clause}
            ORDER BY create_time DESC
        """
        
        # 执行查询
        data = execute_query_with_params(sql, params)
        
        logger.info(f"查询到 {len(data)} 条知识库记录")
        return create_success_response({
            "data": data,
            "total_records": len(data)
        })
        
    except Exception as e:
        logger.error(f"查询知识库列表出错: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@require_http_methods(["POST"])
@csrf_exempt
@jwt_required()
def create_knowledge_database(request):
    """创建知识库"""
    logger.info("创建知识库请求")
    
    try:
        # 解析请求数据
        request_data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['name', 'embedding_model_id', 'index_type']
        is_valid, missing_fields = validate_required_fields(request_data, required_fields)
        if not is_valid:
            logger.warning(f"创建知识库失败: 缺少必填字段 - {missing_fields}")
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        # 获取用户信息
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        username = user_info.get('user_name')
        
        name = request_data.get('name')
        description = request_data.get('description', '')
        embedding_model_id = request_data.get('embedding_model_id')
        vector_dimension = request_data.get('vector_dimension', 384)
        index_type = request_data.get('index_type')
        
        logger.debug(f"=== 创建知识库后端调试信息 ===")
        logger.debug(f"接收到的原始数据: {request_data}")
        logger.debug(f"user_id: {user_id}, username: {username}")
        logger.debug(f"==============================")
        
        # 检查知识库名称是否已存在（同一用户下不能重名）
        if check_record_exists('knowledge_database', {'name': name, 'user_id': user_id}):
            logger.warning(f"创建知识库失败: 用户{username}的名称'{name}'已存在")
            return create_error_response("知识库名称已存在")
        
        # 插入数据
        sql = """
            INSERT INTO knowledge_database 
            (name, description, embedding_model_id, vector_dimension, index_type, doc_count, user_id, username)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = [name, description, embedding_model_id, vector_dimension, index_type, 0, user_id, username]
        
        logger.debug(f"准备执行SQL插入，参数: {params}")
        
        affected_rows = execute_update_with_params(sql, params)
        if affected_rows > 0:
            new_id = get_last_insert_id()
            logger.info(f"成功创建知识库: ID={new_id}, 名称={name}, embedding_model_id={embedding_model_id}")
            return create_success_response({"id": new_id}, 201)
        else:
            return create_error_response("创建失败", 500)
            
    except ValueError as e:
        logger.error(f"创建知识库数据解析错误: {str(e)}", exc_info=True)
        return create_error_response(str(e))
    except Exception as e:
        logger.error(f"创建知识库异常: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@csrf_exempt
@jwt_required()
def update_knowledge_database(request, db_id):
    """更新或删除知识库"""
    
    if request.method == 'PUT':
        return _update_knowledge_database(request, db_id)
    elif request.method == 'DELETE':
        return _delete_knowledge_database(request, db_id)
    else:
        return create_error_response("不支持的请求方法", 405)


def _update_knowledge_database(request, db_id):
    """更新知识库"""
    logger.info(f"更新知识库请求: ID={db_id}")
    
    try:
        # 解析请求数据
        request_data = parse_json_body(request)
        
        # 验证必填字段
        required_fields = ['name']
        is_valid, missing_fields = validate_required_fields(request_data, required_fields)
        if not is_valid:
            logger.warning(f"更新知识库失败: ID={db_id}, 缺少必填字段")
            return create_error_response(f"缺少必填字段: {', '.join(missing_fields)}")
        
        name = request_data.get('name')
        description = request_data.get('description', '')
        
        # 获取记录并检查权限
        record = get_record_by_id('knowledge_database', db_id)
        if not record:
            logger.warning(f"更新知识库失败: ID={db_id} 不存在")
            return create_error_response("知识库不存在", 404)
        
        if not check_resource_permission(request, record['user_id']):
            logger.warning(f"更新知识库失败: ID={db_id} 无权限")
            return create_error_response("知识库不存在或无权限操作", 404)
        
        # 检查名称是否与其他知识库冲突（同一用户下）
        db_user_id = record['user_id']
        existing_sql = "SELECT id FROM knowledge_database WHERE name = %s AND id != %s AND user_id = %s"
        existing = execute_query_with_params(existing_sql, [name, db_id, db_user_id])
        if existing:
            logger.warning(f"更新知识库失败: ID={db_id}, 名称'{name}'已存在")
            return create_error_response("知识库名称已存在")
        
        # 更新知识库
        sql = "UPDATE knowledge_database SET name = %s, description = %s WHERE id = %s"
        affected_rows = execute_update_with_params(sql, [name, description, db_id])
        
        if affected_rows > 0:
            logger.info(f"成功更新知识库: ID={db_id}, 名称={name}")
            return create_success_response()
        else:
            return create_error_response("更新失败", 500)
            
    except ValueError as e:
        logger.error(f"更新知识库数据解析错误: ID={db_id}, 错误={str(e)}", exc_info=True)
        return create_error_response(str(e))
    except Exception as e:
        logger.error(f"更新知识库异常: ID={db_id}, 错误={str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


def _delete_knowledge_database(request, db_id):
    """删除知识库"""
    logger.info(f"删除知识库请求: ID={db_id}")
    
    try:
        # 获取记录并检查权限
        record = get_record_by_id('knowledge_database', db_id)
        if not record:
            logger.warning(f"删除知识库失败: ID={db_id} 不存在")
            return create_error_response("知识库不存在", 404)
        
        if not check_resource_permission(request, record['user_id']):
            logger.warning(f"删除知识库失败: ID={db_id} 无权限")
            return create_error_response("知识库不存在或无权限操作", 404)
        
        # 删除知识库
        sql = "DELETE FROM knowledge_database WHERE id = %s"
        affected_rows = execute_update_with_params(sql, [db_id])
        
        if affected_rows > 0:
            logger.info(f"成功删除知识库: ID={db_id}")
            return create_success_response()
        else:
            return create_error_response("删除失败", 500)
            
    except Exception as e:
        logger.error(f"删除知识库异常: ID={db_id}, 错误={str(e)}", exc_info=True)
        return create_error_response(str(e), 500)


@require_http_methods(["GET"])
@csrf_exempt
@jwt_required()
def check_knowledge_database_name(request):
    """检查知识库名称在当前用户下是否已存在"""
    logger.info("检查知识库名称唯一性")
    
    try:
        user_info = get_user_from_request(request)
        user_id = user_info.get('user_id')
        name = request.GET.get('name', '').strip()
        
        if not name:
            return create_error_response("知识库名称不能为空")
        
        # 检查当前用户是否已有同名知识库
        exists = check_record_exists('knowledge_database', {'name': name, 'user_id': user_id})
        
        logger.info(f"检查知识库名称'{name}'，用户ID={user_id}，是否存在={exists}")
        return create_success_response({"exists": exists})
        
    except Exception as e:
        logger.error(f"检查知识库名称异常: {str(e)}", exc_info=True)
        return create_error_response(str(e), 500)
