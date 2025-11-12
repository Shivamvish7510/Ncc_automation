from django.urls import path
from . import views

urlpatterns = [
    path('', views.unit_list, name='unit_list'),
    path('create/', views.unit_create, name='unit_create'),
    path('<int:pk>/update/', views.unit_update, name='unit_update'),
    path('<int:pk>/delete/', views.unit_delete, name='unit_delete'),
]