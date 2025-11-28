from django.urls import path
from . import views_face_recognition as face_views

urlpatterns = [
    # Face registration
    path('face/register/', face_views.face_registration_view, name='face_register'),
    path('face/register/<int:cadet_id>/', face_views.face_registration_view, name='register_cadet_face'),
    
    # Face management
    path('face/manage/', face_views.face_management_view, name='face_management'),
    path('face/<int:cadet_id>/delete/', face_views.delete_face_encoding, name='delete_face_encoding'),
    
    # Face attendance
    path('session/face/<int:session_id>/', face_views.face_attendance_view, name='face_attendance'),
    path('session/<int:session_id>/process-face/', face_views.process_face_attendance, name='process_face_attendance'),
    
    # Attendance logs
    path('session/<int:session_id>/logs/', face_views.attendance_logs_view, name='attendance_logs'),
]
