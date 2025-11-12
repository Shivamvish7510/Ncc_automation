from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('<int:pk>/', views.notification_detail, name='notification_detail'),
    path('<int:pk>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('mark-all-read/', views.notification_mark_all_read, name='notification_mark_all_read'),
    path('<int:pk>/delete/', views.notification_delete, name='notification_delete'),
    path('send-bulk/', views.send_bulk_notification, name='send_bulk_notification'),
    path('bulk-history/', views.bulk_notification_history, name='bulk_notification_history'),
]