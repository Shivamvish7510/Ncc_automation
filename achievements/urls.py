from django.urls import path
from . import views

urlpatterns = [
    path('', views.achievement_list, name='achievement_list'),
    path('create/', views.achievement_create, name='achievement_create'),
    path('<int:pk>/', views.achievement_detail, name='achievement_detail'),
    path('<int:pk>/update/', views.achievement_update, name='achievement_update'),
    path('<int:pk>/verify/', views.achievement_verify, name='achievement_verify'),
    path('my-achievements/', views.cadet_achievements_view, name='cadet_achievements'),
]