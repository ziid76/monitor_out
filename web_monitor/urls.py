from django.urls import path
from . import views

app_name = 'web_monitor'

urlpatterns = [
    path('manager/auth/', views.ManagerAuthView.as_view(), name='manager_auth'),
    path('manager/logout/', views.ManagerLogoutView.as_view(), name='manager_logout'),
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('target/add/', views.TargetCreateView.as_view(), name='target_add'),
    path('target/<int:pk>/', views.TargetDetailView.as_view(), name='target_detail'),
    path('target/<int:pk>/update/', views.TargetUpdateView.as_view(), name='target_update'),
    path('target/<int:pk>/delete/', views.TargetDeleteView.as_view(), name='target_delete'),
    path('logs/', views.LogListView.as_view(), name='log_list'),
    path('run-command/<str:command_name>/', views.RunCommandView.as_view(), name='run_command'),
    path('target/<int:pk>/view-last-response/', views.ViewLastResponseView.as_view(), name='view_last_response'),
    path('log/<int:pk>/view-pinned-response/', views.ViewPinnedResponseView.as_view(), name='view_pinned_response'),
    path('log/<int:pk>/pin-response/', views.PinResponseView.as_view(), name='pin_response'),
    path('fetch-recipients/', views.FetchRecipientsView.as_view(), name='fetch_recipients'),
    path('add-recipient/', views.AddRecipientView.as_view(), name='add_recipient'),
    path('embed/', views.EmbedDashboardView.as_view(), name='embed_dashboard'),
    path('api/dashboard_data/', views.api_dashboard_data, name='api_dashboard_data'),
]
