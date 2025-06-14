from django.urls import path
from chat_mgt.api.chat_views import (
    retrieve_and_chat,
    chat_history_list,
    chat_history_detail,
    chat_history_delete
)

urlpatterns = [
    # 知识库对话API
    path('retrieve-and-chat', retrieve_and_chat, name='retrieve_and_chat'),
    
    # 聊天历史API
    path('history/list', chat_history_list, name='chat_history_list'),
    path('history/<int:conversation_id>', chat_history_detail, name='chat_history_detail'),
    path('history/<int:conversation_id>/delete', chat_history_delete, name='chat_history_delete'),
] 