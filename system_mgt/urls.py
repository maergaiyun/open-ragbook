from django.urls import path
from system_mgt.api import llm_views, embedding_views

urlpatterns = [
    # 服务商
    path('llm/providers', llm_views.provider_handler, name='llm_provider_handler'),
    path('llm/providers/<int:provider_id>', llm_views.provider_detail_handler, name='llm_provider_detail_handler'),
    
    # 模型配置
    path('llm/models', llm_views.model_handler, name='llm_model_handler'),
    path('llm/models/<int:model_id>', llm_views.model_detail_handler, name='llm_model_detail_handler'),
    path('llm/models/<int:model_id>/default', llm_views.model_set_default, name='llm_model_set_default'),
    path('llm/models/<int:model_id>/test', llm_views.model_test_handler, name='llm_model_test_handler'),
    
    # 嵌入模型配置
    path('embedding/models', embedding_views.embedding_handler, name='embedding_handler'),
    path('embedding/models/<int:embedding_id>', embedding_views.embedding_detail_handler, name='embedding_detail_handler'),
    path('embedding/models/<int:embedding_id>/test', embedding_views.embedding_test, name='embedding_test'),
    path('embedding/models/<int:embedding_id>/validate', embedding_views.embedding_validate, name='embedding_validate'),
    
    # 本地嵌入模型管理
    path('embedding/models/<int:embedding_id>/load', embedding_views.embedding_load_local, name='embedding_load_local'),
    path('embedding/local/unload', embedding_views.embedding_unload_local, name='embedding_unload_local'),
    path('embedding/local/status', embedding_views.embedding_local_status, name='embedding_local_status'),
    path('embedding/server/resources', embedding_views.embedding_server_resources, name='embedding_server_resources'),
] 