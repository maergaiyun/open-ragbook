from django.urls import path
from knowledge_mgt.api.knowledge_views import knowledge_database_list, create_knowledge_database, \
    update_knowledge_database

from knowledge_mgt.api.document_views import document_list, document_upload, document_delete, document_chunks

urlpatterns = [
    # 知识库API
    path('database/list', knowledge_database_list, name='knowledge_database_list'),
    path('database', create_knowledge_database, name='create_knowledge_database'),
    path('database/<int:db_id>', update_knowledge_database, name='update_knowledge_database'),

    # 文档管理
    path('document/list', document_list, name='document_list'),
    path('document/upload', document_upload, name='document_upload'),
    path('document/<int:doc_id>', document_delete, name='document_delete'),
    path('document/<int:doc_id>/chunks', document_chunks, name='document_chunks'),
]
