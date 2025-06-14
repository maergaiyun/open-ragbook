from account_mgt.api import views
from django.urls import path

urlpatterns = [
    path('login', views.login),
    path('register', views.register),
    path('users', views.get_users),
    path('users/create', views.create_user),
    path('users/<int:user_id>/update', views.update_user),
    path('users/<int:user_id>/delete', views.delete_user),
    path('roles', views.get_roles),
    path('profile', views.get_profile),
    path('profile/update', views.update_profile),
]
