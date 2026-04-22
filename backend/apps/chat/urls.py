from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.ChatSessionListCreateView.as_view(), name='chat-session-list'),
    path('sessions/<uuid:id>/', views.ChatSessionDetailView.as_view(), name='chat-session-detail'),
    path('sessions/<uuid:session_id>/messages/', views.MessageListCreateView.as_view(), name='chat-message-list'),
]
