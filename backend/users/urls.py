"""
URL configuration for users app.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('api/users/', views.UserListView.as_view(), name='user-list'),
    path('api/users/<str:user_id>/', views.UserDetailView.as_view(), name='user-detail'),
]

