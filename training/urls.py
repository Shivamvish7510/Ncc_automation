from django.urls import path
from . import views

urlpatterns = [
    path('', views.training_list, name='training_list'),
    path('create/', views.training_create, name='training_create'),
    path('<int:pk>/', views.training_detail, name='training_detail'),
    path('<int:pk>/update/', views.training_update, name='training_update'),
    path('<int:pk>/enroll/', views.training_enroll, name='training_enroll'),
    path('<int:pk>/enrollments/', views.training_enrollments, name='training_enrollments'),
    path('<int:pk>/assess/', views.training_assess, name='training_assess'),
    path('my-trainings/', views.cadet_trainings_view, name='cadet_trainings'),
]