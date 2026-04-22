from django.urls import path
from . import views

urlpatterns = [
    path('', views.LogListView.as_view(), name='log-list'),
    path('upload/', views.LogUploadView.as_view(), name='log-upload'),
    path('<int:id>/analysis/', views.LogAnalysisView.as_view(), name='log-analysis'),
]
