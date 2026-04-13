from django.urls import path
from . import views

app_name = 'web_monitor'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('target/add/', views.TargetCreateView.as_view(), name='target_add'),
    path('target/<int:pk>/', views.TargetDetailView.as_view(), name='target_detail'),
    path('target/<int:pk>/update/', views.TargetUpdateView.as_view(), name='target_update'),
    path('logs/', views.LogListView.as_view(), name='log_list'),
    path('run-command/<str:command_name>/', views.RunCommandView.as_view(), name='run_command'),
    path('task-status/', views.PeriodicTaskStatusView.as_view(), name='task_status'),
    path('target/<int:pk>/view-last-response/', views.ViewLastResponseView.as_view(), name='view_last_response'),
    path('log/<int:pk>/view-pinned-response/', views.ViewPinnedResponseView.as_view(), name='view_pinned_response'),
    path('log/<int:pk>/pin-response/', views.PinResponseView.as_view(), name='pin_response'),
]
