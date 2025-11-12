from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('officer/', views.officer_dashboard_view, name='officer_dashboard'),
    path('cadet/', views.cadet_dashboard_view, name='cadet_dashboard'),
    
    path('cadets/', views.cadet_list_view, name='cadet_list'),
    path('cadets/create/', views.cadet_create_view, name='cadet_create'),
    path('cadets/<int:pk>/', views.cadet_detail_view, name='cadet_detail'),
    path('cadets/<int:pk>/update/', views.cadet_update_view, name='cadet_update'),
    path('cadets/<int:pk>/delete/', views.cadet_delete_view, name='cadet_delete'),
]