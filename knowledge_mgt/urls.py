from django.urls import path
from knowledge_mgt.api.knowledge_views import knowledge_database_list, create_knowledge_database, \
    update_knowledge_database, check_knowledge_database_name

from knowledge_mgt.api.document_views import document_list, document_upload, document_delete, document_chunks
from knowledge_mgt.api.recall_views import recall_test
from knowledge_mgt.api.upload_task_views import (
    create_upload_task, get_upload_tasks, get_task_status, get_queue_status
)

urlpatterns = [
    # 知识库API
    path('database/list', knowledge_database_list, name='knowledge_database_list'),
    path('database', create_knowledge_database, name='create_knowledge_database'),
    path('database/<int:db_id>', update_knowledge_database, name='update_knowledge_database'),
    path('database/check-name', check_knowledge_database_name, name='check_knowledge_database_name'),

    # 文档管理
    path('document/list', document_list, name='document_list'),
    path('document/upload', document_upload, name='document_upload'),
    path('document/<int:doc_id>', document_delete, name='document_delete'),
    path('document/<int:doc_id>/chunks', document_chunks, name='document_chunks'),
    
    # 文档上传任务管理
    path('upload/task', create_upload_task, name='create_upload_task'),
    path('upload/tasks', get_upload_tasks, name='get_upload_tasks'),
    path('upload/task/<str:task_id>/status', get_task_status, name='get_task_status'),
    path('upload/queue/status', get_queue_status, name='get_queue_status'),
    
    # 召回检索测试
    path('recall/test', recall_test, name='recall_test'),
]
