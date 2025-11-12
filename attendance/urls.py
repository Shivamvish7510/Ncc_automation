from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.attendance_session_list, name='attendance_session_list'),
    path('sessions/create/', views.attendance_session_create, name='attendance_session_create'),
    path('sessions/<int:pk>/', views.attendance_session_detail, name='attendance_session_detail'),
    path('mark/<int:session_id>/', views.mark_attendance, name='mark_attendance'),
    path('my-attendance/', views.cadet_attendance_view, name='cadet_attendance'),
]